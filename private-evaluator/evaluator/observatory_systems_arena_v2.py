#!/usr/bin/env python3
"""Output-bounded entrypoint for the durable Observatory systems arena.

The forced-crash trial kills the actual candidate container through the selected container runtime,
not merely the local Docker/Podman CLI process. A unique named container is verified running, receives
the crash workload, is killed by the runtime, and is confirmed absent before the same durable state
directory is reopened. The final report carries the complete crash receipt; CLI death alone can never
earn crash evidence.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import uuid

import bounded_subprocess
import observatory_systems_arena as base

bounded_subprocess.install(base.subprocess)

_CRASH = {
    "actual_container_kill_required": True,
    "container_started": False,
    "workload_delivered": False,
    "runtime_kill_returncode": None,
    "runtime_kill_succeeded": False,
    "container_absent_before_recovery": False,
    "cli_process_kill_counts_as_evidence": False,
}


def _named_argv(runtime, state_dir, name):
    argv = list(base._argv(runtime, state_dir))
    try:
        index = argv.index("run") + 1
    except ValueError as exc:
        raise RuntimeError(
            "durable crash injector cannot locate container run command") from exc
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


def _safe_crash(runtime, source, state_dir, events, delay=0.01):
    os.makedirs(state_dir, exist_ok=True)
    name = "obs-sys-crash-" + uuid.uuid4().hex
    process = subprocess.Popen(
        _named_argv(runtime, state_dir, name),
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True)
    try:
        started = _wait_running(runtime, name, process)
        _CRASH["container_started"] = bool(started)
        if not started:
            return False

        try:
            process.stdin.write(base._body(source, [
                {"op": "ingest_batch", "events": events}]))
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


def _bind_crash_receipt(path):
    if not path or not os.path.isfile(path):
        raise RuntimeError("durable v2 evaluator produced no report to bind crash evidence")
    with open(path, encoding="utf-8") as handle:
        report = json.load(handle)
    report["whole_process_crash_evidence"] = dict(_CRASH)
    tests = report.setdefault("tests", {})
    if tests.get("crash_was_actually_observed") is True and not all((
            _CRASH.get("container_started") is True,
            _CRASH.get("workload_delivered") is True,
            _CRASH.get("runtime_kill_succeeded") is True,
            _CRASH.get("container_absent_before_recovery") is True)):
        tests["crash_was_actually_observed"] = False
        tests["crash_restart_integrity"] = False
        report["status"] = "FAIL"
        report["passed"] = False
        report["reason"] = "durable crash lacked actual-container kill evidence"
    temporary = path + ".v2.tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=1, sort_keys=True)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    return report


def main():
    base._crash = _safe_crash
    code = base.main()
    report = _bind_crash_receipt(_out_argument())
    if report.get("status") != "PASS" or report.get("passed") is not True:
        code = 1
    print(json.dumps({
        "durable_v2_crash_receipt": "PASS",
        "crash_was_actually_observed": (report.get("tests") or {}).get(
            "crash_was_actually_observed"),
        "crash_restart_integrity": (report.get("tests") or {}).get(
            "crash_restart_integrity"),
        "whole_process_crash_evidence": report.get(
            "whole_process_crash_evidence"),
    }, ensure_ascii=False, indent=1, sort_keys=True))
    return code


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(json.dumps({"status": "FAIL", "passed": False,
                          "reason": str(exc)}, ensure_ascii=False, indent=1))
        sys.exit(1)
