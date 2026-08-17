#!/usr/bin/env python3
"""Output-bounded entrypoint for the durable Observatory systems arena."""
import json
import subprocess
import sys
import time

import bounded_subprocess
import observatory_systems_arena as base

bounded_subprocess.install(base.subprocess)


def _safe_crash(runtime, source, state_dir, events, delay=0.01):
    process = subprocess.Popen(
        base._argv(runtime, state_dir), stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, text=True)
    try:
        process.stdin.write(base._body(source, [{"op": "ingest_batch", "events": events}]))
        process.stdin.flush()
    except (BrokenPipeError, OSError):
        pass
    time.sleep(delay)
    observed = process.poll() is None
    if observed:
        try:
            process.kill()
        except OSError:
            pass
    try:
        process.wait(timeout=15)
    except subprocess.TimeoutExpired:
        process.kill(); process.wait()
    return observed


base._crash = _safe_crash

if __name__ == "__main__":
    try:
        sys.exit(base.main())
    except Exception as exc:
        print(json.dumps({"status": "FAIL", "passed": False,
                          "reason": str(exc)}, ensure_ascii=False, indent=1))
        sys.exit(1)
