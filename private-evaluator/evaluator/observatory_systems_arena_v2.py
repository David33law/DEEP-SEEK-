#!/usr/bin/env python3
"""Output-bounded entrypoint for the durable Observatory systems arena.

A forced crash counts only when the actual uniquely named candidate container is killed by the
container runtime while the submitted durable operation has not yet produced a reply, and that
container is confirmed absent before reopening the same state directory. Killing only the local CLI,
or killing an idle container after the operation completed, cannot earn crash evidence.

Every declared authority/recovery file is also validated before fault injection: paths must be
relative, remain inside the state directory, exist, and not alias one another.
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
import observatory_systems_arena as base

bounded_subprocess.install(base.subprocess)

_ORIGINAL_MANIFEST = base._manifest
_CRASH = {
    "actual_container_kill_required": True,
    "mid_operation_kill_required": True,
    "container_started": False,
    "workload_delivered": False,
    "operation_reply_observed_before_kill": None,
    "mid_operation_kill_verified": False,
    "runtime_kill_returncode": None,
    "runtime_kill_succeeded": False,
    "container_absent_before_recovery": False,
    "cli_process_kill_counts_as_evidence": False,
}
_MANIFEST = {
    "authority_files_verified": False,
    "recovery_files_verified": False,
    "declared_authority_files": [],
    "declared_recovery_files": [],
}


def _inside(root, relative):
    root = os.path.abspath(root)
    parts = str(relative).replace("\\", "/").split("/")
    if os.path.isabs(str(relative)) or ".." in parts:
        raise RuntimeError("durable manifest path must be relative: " + str(relative))
    path = os.path.abspath(os.path.join(root, *parts))
    if path == root or not path.startswith(root + os.sep):
        raise RuntimeError("durable manifest path escapes state directory: " + str(relative))
    return path


def _safe_manifest(runtime, source, state_dir):
    manifest = _ORIGINAL_MANIFEST(runtime, source, state_dir)
    authority = manifest.get("authority_files") or []
    recovery = manifest.get("recovery_files") or []
    if not isinstance(authority, list) or not authority:
        raise RuntimeError("durability_manifest requires authority_files")
    if not isinstance(recovery, list):
        raise RuntimeError("durability_manifest recovery_files must be a list when present")
    seen = set()
    for label, rows in (("authority", authority), ("recovery", recovery)):
        for relative in rows:
            path = _inside(state_dir, relative)
            real = os.path.realpath(path)
            if not os.path.isfile(path):
                raise RuntimeError(
                    f"declared durable {label} file does not exist: {relative}")
            if real in seen:
                raise RuntimeError(
                    f"durable manifest aliases authority/recovery file: {relative}")
            seen.add(real)
    _MANIFEST.update({
        "authority_files_verified": True,
        "recovery_files_verified": True,
        "declared_authority_files": [str(x) for x in authority],
        "declared_recovery_files": [str(x) for x in recovery],
    })
    return manifest


def _named_argv(runtime, state_dir, name):
    argv = list(base._argv(runtime, state_dir))
    try:
        index = argv.index("run") + 1
    except ValueError as exc:
        raise RuntimeError(
            "durable crash injector cannot locate container run command") from exc
    argv[index:index] = ["--name", name]
    return argv


def _crash_body(source, events):
    # Deliberately omit the normal ``quit`` command.  If ingest completes quickly the candidate
    # remains alive waiting for another request, letting the trusted host distinguish an idle
    # post-operation kill from a genuine mid-operation kill by observing whether a reply appeared.
    return "\n".join((
        json.dumps({"candidate_source": source}, ensure_ascii=False),
        json.dumps({"op": "ingest_batch", "events": events}, ensure_ascii=False),
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


def _safe_crash(runtime, source, state_dir, events, delay=0.01):
    os.makedirs(state_dir, exist_ok=True)
    name = "obs-sys-crash-" + uuid.uuid4().hex
    with tempfile.TemporaryFile(mode="w+b") as output:
        process = subprocess.Popen(
            _named_argv(runtime, state_dir, name),
            stdin=subprocess.PIPE,
            stdout=output,
            stderr=subprocess.DEVNULL,
            text=True)
        try:
            started = _wait_running(runtime, name, process)
            _CRASH["container_started"] = bool(started)
            if not started:
                return False

            try:
                process.stdin.write(_crash_body(source, events))
                process.stdin.flush()
                _CRASH["workload_delivered"] = True
            except (BrokenPipeError, OSError):
                return False

            time.sleep(max(0.0, float(delay)))
            if _inspect(runtime, name) is not True:
                return False

            reply_observed = os.fstat(output.fileno()).st_size > 0
            _CRASH["operation_reply_observed_before_kill"] = bool(reply_observed)
            if reply_observed:
                # The durable operation already replied.  Killing the now-idle container is cleanup,
                # not evidence of crash atomicity.
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
                # Only the runtime kill above is evidence. Local CLI termination is cleanup.
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


def _bind_receipt(path):
    if not path or not os.path.isfile(path):
        raise RuntimeError("durable v2 evaluator produced no report to bind evidence")
    with open(path, encoding="utf-8") as handle:
        report = json.load(handle)
    report["whole_process_crash_evidence"] = dict(_CRASH)
    report["durable_manifest_evidence"] = dict(_MANIFEST)
    tests = report.setdefault("tests", {})
    crash_complete = all((
        _CRASH.get("container_started") is True,
        _CRASH.get("workload_delivered") is True,
        _CRASH.get("operation_reply_observed_before_kill") is False,
        _CRASH.get("mid_operation_kill_verified") is True,
        _CRASH.get("runtime_kill_succeeded") is True,
        _CRASH.get("container_absent_before_recovery") is True,
    ))
    manifest_complete = bool(
        _MANIFEST.get("authority_files_verified") is True
        and _MANIFEST.get("recovery_files_verified") is True)
    if (tests.get("crash_was_actually_observed") is True and not crash_complete) \
            or not manifest_complete:
        tests["crash_was_actually_observed"] = False
        tests["crash_restart_integrity"] = False
        report["status"] = "FAIL"
        report["passed"] = False
        report["reason"] = (
            "durable v2 evidence incomplete: mid-operation container death or declared-file proof")
    temporary = path + ".v2.tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=1, sort_keys=True)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    return report


def main():
    base._manifest = _safe_manifest
    base._crash = _safe_crash
    code = base.main()
    report = _bind_receipt(_out_argument())
    if report.get("status") != "PASS" or report.get("passed") is not True:
        code = 1
    print(json.dumps({
        "durable_v2_receipt": "PASS",
        "crash_was_actually_observed": (report.get("tests") or {}).get(
            "crash_was_actually_observed"),
        "crash_restart_integrity": (report.get("tests") or {}).get(
            "crash_restart_integrity"),
        "whole_process_crash_evidence": report.get(
            "whole_process_crash_evidence"),
        "durable_manifest_evidence": report.get("durable_manifest_evidence"),
    }, ensure_ascii=False, indent=1, sort_keys=True))
    return code


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(json.dumps({"status": "FAIL", "passed": False,
                          "reason": str(exc)}, ensure_ascii=False, indent=1))
        sys.exit(1)
