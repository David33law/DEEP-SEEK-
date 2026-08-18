#!/usr/bin/env python3
"""Output-bounded entrypoint for the distributed Observatory fault arena.

The whole-process crash injector must kill the candidate container itself, not merely the local
``docker``/``podman`` CLI client.  A named ephemeral container is therefore created for the crash
trial, killed through the container runtime, and verified absent before recovery begins.  This
prevents an orphaned writer from continuing to mutate the shared cluster directory while the
recovery container is being evaluated.
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
    """Crash the actual candidate container and prove that no writer survives.

    Returning ``True`` means all of the following happened: the named candidate container reached
    running state, the crash workload was delivered, the runtime successfully killed that container,
    and the container was absent before the subsequent recovery session could start.  Killing only
    the CLI process never earns crash evidence.
    """
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
        if not started:
            return False

        try:
            process.stdin.write(base._body(source, [
                {"op": "ingest_batch", "node_id": "n1", "events": events}]))
            process.stdin.flush()
        except (BrokenPipeError, OSError):
            return False

        # The input line has been delivered to the running container.  Give the candidate a small
        # deterministic window to enter the durable batch path, then kill the container itself.
        time.sleep(max(0.0, float(delay)))
        if _inspect(runtime, name) is not True:
            return False

        kill = subprocess.run(
            [runtime, "kill", name], capture_output=True,
            text=True, timeout=30)
        killed = kill.returncode == 0

        try:
            process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            # At this point the container kill has already been attempted.  Killing the local CLI is
            # only cleanup and cannot by itself make the crash trial pass.
            try:
                process.kill()
            except OSError:
                pass
            process.wait(timeout=15)

        absent = _wait_absent(runtime, name, timeout=30.0)
        if not absent:
            absent = _force_remove(runtime, name)
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


base._crash_process = _safe_crash_process

if __name__ == "__main__":
    try:
        sys.exit(base.main())
    except Exception as exc:
        print(json.dumps({"status": "FAIL", "passed": False,
                          "reason": str(exc)}, ensure_ascii=False, indent=1))
        sys.exit(1)
