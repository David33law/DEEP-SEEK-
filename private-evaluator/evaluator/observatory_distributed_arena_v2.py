#!/usr/bin/env python3
"""Output-bounded entrypoint for the distributed Observatory fault arena.

The whole-process crash injector kills the candidate container itself, not merely the local
``docker``/``podman`` CLI client. A named ephemeral container is created for the crash trial, killed
through the container runtime, and verified absent before recovery begins. This prevents an orphaned
writer from continuing to mutate the shared cluster directory while the recovery container is being
evaluated.

This wrapper also corrects the distributed throughput receipt. The base arena historically divided
1000 baseline events by the elapsed time of the *entire* fault campaign. The trusted v2 entrypoint
now measures the first 1000-event healthy baseline session directly and rewrites only the throughput
fields after the base campaign has produced its report. Campaign elapsed time remains separately
preserved.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import uuid

import bounded_subprocess
import observatory_distributed_arena as base

bounded_subprocess.install(base.subprocess)

_ORIGINAL_SESSION = base._session
_ORIGINAL_MANIFEST = base._manifest
_BASELINE = {"elapsed_seconds": None, "events": None}
_CRASH = {
    "actual_container_kill_required": True,
    "container_started": False,
    "workload_delivered": False,
    "runtime_kill_returncode": None,
    "runtime_kill_succeeded": False,
    "container_absent_before_recovery": False,
    "cli_process_kill_counts_as_evidence": False,
}


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
    """Crash the actual candidate container and prove that no writer survives."""
    os.makedirs(cluster_dir, exist_ok=True)
    name = "obs-dist-crash-" + uuid.uuid4().hex
    process = subprocess.Popen(
        _named_argv(runtime, cluster_dir, name),
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True)
    started = False
    killed = False
    absent = False
    try:
        started = _wait_running(runtime, name, process)
        _CRASH["container_started"] = bool(started)
        if not started:
            return False

        try:
            process.stdin.write(base._body(source, [
                {"op": "ingest_batch", "node_id": "n1", "events": events}]))
            process.stdin.flush()
            _CRASH["workload_delivered"] = True
        except (BrokenPipeError, OSError):
            return False

        time.sleep(max(0.0, float(delay)))
        if _inspect(runtime, name) is not True:
            return False

        kill = subprocess.run(
            [runtime, "kill", name], capture_output=True,
            text=True, timeout=30)
        _CRASH["runtime_kill_returncode"] = int(kill.returncode)
        _CRASH["runtime_kill_stdout_tail"] = (kill.stdout or "")[-1000:]
        _CRASH["runtime_kill_stderr_tail"] = (kill.stderr or "")[-1000:]
        killed = kill.returncode == 0
        _CRASH["runtime_kill_succeeded"] = bool(killed)

        try:
            process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            # Runtime kill is the evidence-producing action. Killing the local CLI here is cleanup
            # only and can never make the crash trial pass by itself.
            try:
                process.kill()
            except OSError:
                pass
            process.wait(timeout=15)

        absent = _wait_absent(runtime, name, timeout=30.0)
        if not absent:
            absent = _force_remove(runtime, name)
        _CRASH["container_absent_before_recovery"] = bool(absent)
        return bool(started and killed and absent)
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
    report["campaign_elapsed_seconds"] = campaign_elapsed
    report["baseline_elapsed_seconds"] = float(elapsed)
    report["baseline_events"] = int(events)
    report["events_per_second_baseline"] = float(events) / max(float(elapsed), 1e-9)
    report["throughput_measurement"] = (
        "first healthy 1000-event baseline session including canonical integrity, root, publication "
        "and close verification; excludes later injected fault campaigns")
    report["whole_process_crash_evidence"] = dict(_CRASH)
    crash_test = (report.get("tests") or {}).get("whole_process_crash_recovery")
    if crash_test is True and not all((
            _CRASH.get("container_started") is True,
            _CRASH.get("workload_delivered") is True,
            _CRASH.get("runtime_kill_succeeded") is True,
            _CRASH.get("container_absent_before_recovery") is True)):
        report["status"] = "FAIL"
        report["passed"] = False
        report.setdefault("tests", {})["whole_process_crash_recovery"] = False
        report["reason"] = "whole-process crash lacked actual-container kill evidence"
    temporary = path + ".v2.tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=1, sort_keys=True)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    return report


def main():
    base._manifest = _manifest
    base._session = _timed_session
    base._crash_process = _safe_crash_process
    code = base.main()
    report = _rewrite_receipt(_out_argument())
    if report.get("status") != "PASS" or report.get("passed") is not True:
        code = 1
    print(json.dumps({
        "distributed_v2_receipt_rewrite": "PASS",
        "baseline_events": report["baseline_events"],
        "baseline_elapsed_seconds": report["baseline_elapsed_seconds"],
        "events_per_second_baseline": report["events_per_second_baseline"],
        "campaign_elapsed_seconds": report["campaign_elapsed_seconds"],
        "whole_process_crash_recovery": (report.get("tests") or {}).get(
            "whole_process_crash_recovery"),
        "whole_process_crash_evidence": report.get("whole_process_crash_evidence"),
    }, ensure_ascii=False, indent=1, sort_keys=True))
    return code


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(json.dumps({"status": "FAIL", "passed": False,
                          "reason": str(exc)}, ensure_ascii=False, indent=1))
        sys.exit(1)
