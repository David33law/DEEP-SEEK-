#!/usr/bin/env python3
"""Output-bounded entrypoint for the distributed Observatory fault arena.

Whole-process crash evidence requires the actual named candidate container to die through the
container runtime while the submitted distributed admission has not yet produced an operation reply,
and that container must be absent before recovery begins. The crash event count is an explicit
owner-bound v2 argument rather than a hidden function of the normal large-history workload.

The wrapper also verifies declared authority files and measures the 1000-event healthy baseline
separately from the later fault campaign. The actual crash injector uses explicit UTF-8 stdin
transport so candidate/legal Unicode is independent of the Windows active code page.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import uuid

import bounded_subprocess
import observatory_distributed_arena as base

bounded_subprocess.install(base.subprocess)

_ORIGINAL_SESSION = base._session
_ORIGINAL_MANIFEST = base._manifest
_ORIGINAL_EVENTS = base._events
_BASELINE = {"elapsed_seconds": None, "events": None}
_CRASH_EVENTS = None
_CRASH = {
    "actual_container_kill_required": True,
    "mid_operation_kill_required": True,
    "container_started": False,
    "workload_delivered": False,
    "events_delivered": 0,
    "operation_reply_observed_before_kill": None,
    "mid_operation_kill_verified": False,
    "runtime_kill_returncode": None,
    "runtime_kill_succeeded": False,
    "container_absent_before_recovery": False,
    "cli_process_kill_counts_as_evidence": False,
}


def _consume_crash_events(argv):
    try:
        index = argv.index("--crash-events")
        value = int(argv[index + 1])
    except (ValueError, IndexError) as exc:
        raise RuntimeError(
            "distributed v2 requires explicit --crash-events from owner workload policy") from exc
    if value < 1000:
        raise RuntimeError("distributed v2 crash workload must contain at least 1000 events")
    del argv[index:index + 2]
    return value


def _events(n, seed, prefix="DIST"):
    if prefix == "CRASHLOAD":
        if _CRASH_EVENTS is None:
            raise RuntimeError("distributed crash workload was not owner-bound")
        n = int(_CRASH_EVENTS)
    return _ORIGINAL_EVENTS(n, seed, prefix)


def _inside(root, relative):
    root = os.path.abspath(root)
    path = os.path.abspath(os.path.join(
        root, *str(relative).replace("\\", "/").split("/")))
    if path == root or not path.startswith(root + os.sep):
        raise RuntimeError("distributed authority path escapes cluster root: " + str(relative))
    return path


def _manifest(runtime, source, cluster_dir, expected_replication, expected_commit):
    manifest = _ORIGINAL_MANIFEST(
        runtime, source, cluster_dir, expected_replication, expected_commit)
    cluster_files = manifest.get("cluster_authority_files")
    if not isinstance(cluster_files, list) or not cluster_files:
        raise RuntimeError("cluster_manifest requires cluster_authority_files")
    declared = []
    for relative in cluster_files:
        parts = str(relative).replace("\\", "/").split("/")
        if os.path.isabs(str(relative)) or ".." in parts:
            raise RuntimeError("cluster authority files must be relative cluster paths")
        path = _inside(cluster_dir, relative)
        if not os.path.isfile(path):
            raise RuntimeError("declared cluster authority file does not exist: " + str(relative))
        declared.append(os.path.realpath(path))
    for node_id, files in (manifest.get("node_authority_files") or {}).items():
        for relative in files:
            path = _inside(cluster_dir, relative)
            if not os.path.isfile(path):
                raise RuntimeError(
                    f"declared node authority file does not exist: {node_id}/{relative}")
            declared.append(os.path.realpath(path))
    if len(declared) != len(set(declared)):
        raise RuntimeError("distributed manifest aliases authority files")
    return manifest


def _is_baseline(commands):
    if _BASELINE["elapsed_seconds"] is not None or not commands:
        return False
    first = commands[0] if isinstance(commands[0], dict) else {}
    events = first.get("events") if first.get("op") == "ingest_batch" else None
    if not isinstance(events, list) or len(events) != 1000:
        return False
    if not events or not str(events[0].get("source_id", "")).startswith("DIST-"):
        return False
    operations = [row.get("op") for row in commands if isinstance(row, dict)]
    return operations[:5] == [
        "ingest_batch", "integrity", "roots", "publication_roots", "close"]


def _timed_session(runtime, source, cluster_dir, commands,
                   timeout=240, allow_errors=False):
    baseline = _is_baseline(commands)
    started = time.monotonic() if baseline else None
    result = _ORIGINAL_SESSION(
        runtime, source, cluster_dir, commands,
        timeout=timeout, allow_errors=allow_errors)
    if baseline:
        elapsed = time.monotonic() - started
        _BASELINE["elapsed_seconds"] = elapsed
        _BASELINE["events"] = len(commands[0]["events"])
    return result


def _named_argv(runtime, cluster_dir, name):
    argv = list(base._argv(runtime, cluster_dir))
    try:
        index = argv.index("run") + 1
    except ValueError as exc:
        raise RuntimeError("distributed crash injector cannot locate container run command") from exc
    argv[index:index] = ["--name", name]
    return argv


def _crash_body(source, events):
    return "\n".join((
        json.dumps({"candidate_source": source, "node_ids": base.NODE_IDS},
                   ensure_ascii=False),
        json.dumps({"op": "ingest_batch", "node_id": "n1", "events": events},
                   ensure_ascii=False),
    )) + "\n"


def _inspect(runtime, name):
    result = subprocess.run(
        [runtime, "inspect", "-f", "{{.State.Running}}", name],
        capture_output=True, text=True, timeout=15)
    if result.returncode != 0:
        return None
    return (result.stdout or "").strip().lower() == "true"


def _wait_running(runtime, name, process, timeout=30.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        state = _inspect(runtime, name)
        if state is True:
            return True
        if process.poll() is not None:
            return False
        time.sleep(0.05)
    return False


def _wait_absent(runtime, name, timeout=30.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _inspect(runtime, name) is None:
            return True
        time.sleep(0.05)
    return _inspect(runtime, name) is None


def _force_remove(runtime, name):
    subprocess.run(
        [runtime, "rm", "-f", name], capture_output=True,
        text=True, timeout=30)
    return _wait_absent(runtime, name, timeout=15.0)


def _safe_crash_process(runtime, source, cluster_dir, events, delay=0.015):
    os.makedirs(cluster_dir, exist_ok=True)
    _CRASH["events_delivered"] = len(events)
    name = "obs-dist-crash-" + uuid.uuid4().hex
    with tempfile.TemporaryFile(mode="w+b") as output:
        process = subprocess.Popen(
            _named_argv(runtime, cluster_dir, name),
            stdin=subprocess.PIPE,
            stdout=output,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="strict")
        try:
            started = _wait_running(runtime, name, process)
            _CRASH["container_started"] = bool(started)
            if not started:
                return False

            try:
                process.stdin.write(_crash_body(source, events))
                process.stdin.flush()
                _CRASH["workload_delivered"] = True
            except (BrokenPipeError, OSError, UnicodeError):
                return False

            time.sleep(max(0.0, float(delay)))
            if _inspect(runtime, name) is not True:
                return False

            reply_observed = os.fstat(output.fileno()).st_size > 0
            _CRASH["operation_reply_observed_before_kill"] = bool(reply_observed)
            if reply_observed:
                return False
            _CRASH["mid_operation_kill_verified"] = True

            kill = subprocess.run(
                [runtime, "kill", name], capture_output=True,
                text=True, timeout=30)
            _CRASH["runtime_kill_returncode"] = int(kill.returncode)
            _CRASH["runtime_kill_stdout_tail"] = (kill.stdout or "")[-1000:]
            _CRASH["runtime_kill_stderr_tail"] = (kill.stderr or "")[-1000:]
            _CRASH["runtime_kill_succeeded"] = kill.returncode == 0

            try:
                process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                try:
                    process.kill()
                except OSError:
                    pass
                process.wait(timeout=15)

            absent = _wait_absent(runtime, name, timeout=30.0)
            if not absent:
                absent = _force_remove(runtime, name)
            _CRASH["container_absent_before_recovery"] = bool(absent)
            return bool(
                started
                and _CRASH["workload_delivered"] is True
                and _CRASH["events_delivered"] == int(_CRASH_EVENTS)
                and _CRASH["mid_operation_kill_verified"] is True
                and _CRASH["runtime_kill_succeeded"] is True
                and absent)
        finally:
            if process.stdin is not None:
                try:
                    process.stdin.close()
                except OSError:
                    pass
            if _inspect(runtime, name) is not None:
                _force_remove(runtime, name)
            if process.poll() is None:
                try:
                    process.kill()
                except OSError:
                    pass
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    pass


def _out_argument():
    try:
        index = sys.argv.index("--out")
        return os.path.abspath(sys.argv[index + 1])
    except (ValueError, IndexError):
        return None


def _rewrite_receipt(path):
    elapsed = _BASELINE.get("elapsed_seconds")
    events = _BASELINE.get("events")
    if not path or not os.path.isfile(path) or not elapsed or not events:
        raise RuntimeError("distributed v2 could not bind a measured baseline throughput receipt")
    with open(path, encoding="utf-8") as handle:
        report = json.load(handle)
    campaign_elapsed = report.get("elapsed_seconds")
    report["requested_crash_events"] = int(_CRASH_EVENTS)
    report["campaign_elapsed_seconds"] = campaign_elapsed
    report["baseline_elapsed_seconds"] = float(elapsed)
    report["baseline_events"] = int(events)
    report["events_per_second_baseline"] = float(events) / max(float(elapsed), 1e-9)
    report["transport_encoding"] = "utf-8"
    report["throughput_measurement"] = (
        "first healthy 1000-event baseline session including canonical integrity, root, publication "
        "and close verification; excludes later injected fault campaigns")
    report["whole_process_crash_evidence"] = dict(_CRASH)
    crash_test = (report.get("tests") or {}).get("whole_process_crash_recovery")
    crash_complete = all((
        _CRASH.get("container_started") is True,
        _CRASH.get("workload_delivered") is True,
        int(_CRASH.get("events_delivered", 0)) == int(_CRASH_EVENTS),
        _CRASH.get("operation_reply_observed_before_kill") is False,
        _CRASH.get("mid_operation_kill_verified") is True,
        _CRASH.get("runtime_kill_succeeded") is True,
        _CRASH.get("container_absent_before_recovery") is True,
    ))
    if crash_test is True and not crash_complete:
        report["status"] = "FAIL"
        report["passed"] = False
        report.setdefault("tests", {})["whole_process_crash_recovery"] = False
        report["reason"] = "whole-process crash lacked signed mid-operation container-kill evidence"
    temporary = path + ".v2.tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=1, sort_keys=True)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    return report


def main():
    global _CRASH_EVENTS
    _CRASH_EVENTS = _consume_crash_events(sys.argv)
    base._events = _events
    base._manifest = _manifest
    base._session = _timed_session
    base._crash_process = _safe_crash_process
    code = base.main()
    report = _rewrite_receipt(_out_argument())
    if report.get("status") != "PASS" or report.get("passed") is not True:
        code = 1
    print(json.dumps({
        "distributed_v2_receipt_rewrite": "PASS",
        "requested_crash_events": report["requested_crash_events"],
        "baseline_events": report["baseline_events"],
        "baseline_elapsed_seconds": report["baseline_elapsed_seconds"],
        "events_per_second_baseline": report["events_per_second_baseline"],
        "campaign_elapsed_seconds": report["campaign_elapsed_seconds"],
        "whole_process_crash_recovery": (report.get("tests") or {}).get(
            "whole_process_crash_recovery"),
        "whole_process_crash_evidence": report.get("whole_process_crash_evidence"),
        "transport_encoding": report.get("transport_encoding"),
    }, ensure_ascii=True, indent=1, sort_keys=True))
    return code


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(json.dumps({"status": "FAIL", "passed": False,
                          "reason": str(exc)}, ensure_ascii=True, indent=1))
        sys.exit(1)
