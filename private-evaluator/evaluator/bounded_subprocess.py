"""Bounded replacement for ``subprocess.run`` used by untrusted-candidate evaluators.

Container isolation stops filesystem/network/process capabilities inside the candidate, but an
untrusted candidate can still flood its already-open stdout/stderr pipes and exhaust the trusted
parent. This helper streams both pipes, kills immediately at the declared cap, and never buffers
unbounded output. Text-mode transport defaults to strict UTF-8: host locale is irrelevant and invalid
byte sequences are never silently replaced inside trusted evaluator evidence.
"""
from __future__ import annotations

import subprocess
import threading

_ORIGINAL_POPEN = subprocess.Popen
PIPE = subprocess.PIPE


class OutputLimitExceeded(RuntimeError):
    pass


def run_bounded(args, *, input=None, stdin=None, capture_output=False,
                timeout=None, check=False, text=False, encoding=None, errors=None,
                stdout=None, stderr=None, max_stdout_bytes=32 * 1024 * 1024,
                max_stderr_bytes=4 * 1024 * 1024, **kwargs):
    if capture_output:
        if stdout is not None or stderr is not None:
            raise ValueError("stdout/stderr may not be used with capture_output")
        stdout, stderr = PIPE, PIPE
    if input is not None:
        if stdin is not None:
            raise ValueError("stdin and input may not both be supplied")
        stdin = PIPE
    requested_text = bool(text or encoding is not None or kwargs.pop("universal_newlines", False))
    codec = encoding or "utf-8"
    codec_errors = errors or "strict"
    kwargs.pop("text", None); kwargs.pop("encoding", None); kwargs.pop("errors", None)
    process = _ORIGINAL_POPEN(args, stdin=stdin, stdout=stdout, stderr=stderr,
                              text=False, **kwargs)
    state = {"stdout": bytearray(), "stderr": bytearray(),
             "stdout_over": False, "stderr_over": False}

    def reader(stream, key, limit):
        if stream is None:
            return
        while True:
            try:
                chunk = stream.read(65536)
            except OSError:
                break
            if not chunk:
                break
            target = state[key]
            remaining = limit - len(target)
            if remaining > 0:
                target.extend(chunk[:remaining])
            if len(chunk) > remaining:
                state[key + "_over"] = True
                try:
                    process.kill()
                except OSError:
                    pass
                while True:
                    try:
                        if not stream.read(65536):
                            break
                    except OSError:
                        break
                break

    readers = []
    if stdout == PIPE:
        readers.append(threading.Thread(
            target=reader, args=(process.stdout, "stdout", max_stdout_bytes), daemon=True))
    if stderr == PIPE:
        readers.append(threading.Thread(
            target=reader, args=(process.stderr, "stderr", max_stderr_bytes), daemon=True))
    for thread in readers:
        thread.start()

    writer = None
    if input is not None:
        payload = input.encode(codec, codec_errors) if isinstance(input, str) else bytes(input)

        def write_input():
            try:
                process.stdin.write(payload); process.stdin.close()
            except (BrokenPipeError, OSError):
                pass

        writer = threading.Thread(target=write_input, daemon=True); writer.start()
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill(); process.wait()
        raise
    finally:
        if writer is not None:
            writer.join(timeout=5)
        for thread in readers:
            thread.join(timeout=5)
    if state["stdout_over"] or state["stderr_over"]:
        which = "stdout" if state["stdout_over"] else "stderr"
        limit = max_stdout_bytes if state["stdout_over"] else max_stderr_bytes
        raise OutputLimitExceeded(
            f"child exceeded bounded {which} limit of {limit} bytes")
    out = bytes(state["stdout"]) if stdout == PIPE else None
    err = bytes(state["stderr"]) if stderr == PIPE else None
    if requested_text:
        out = out.decode(codec, codec_errors) if out is not None else None
        err = err.decode(codec, codec_errors) if err is not None else None
    completed = subprocess.CompletedProcess(args, process.returncode, out, err)
    if check and process.returncode:
        raise subprocess.CalledProcessError(process.returncode, args,
                                            output=out, stderr=err)
    return completed


def install(subprocess_module):
    subprocess_module.run = run_bounded
    return subprocess_module
