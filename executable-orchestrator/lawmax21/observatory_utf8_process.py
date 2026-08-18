"""Canonical locale-independent trusted subprocess seat for Observatory orchestration.

The Observatory transmits source code, legal fixtures and diagnostics containing arbitrary Unicode.
Trusted parent semantics must therefore never depend on the host locale or Windows active code page.
All text-mode Python/evaluator subprocesses routed through this module use strict UTF-8 stdin/stdout
and explicitly force UTF-8 mode in the child environment.
"""
from __future__ import annotations

import os
import subprocess

ENCODING = "utf-8"


def child_env(env=None):
    """Return a copy of *env* with deterministic Python UTF-8 text I/O."""
    result = dict(os.environ if env is None else env)
    result["PYTHONIOENCODING"] = ENCODING
    result["PYTHONUTF8"] = "1"
    return result


def run(command, *, env=None, **kwargs):
    """Run a trusted text subprocess with strict UTF-8 transport.

    Callers retain control of capture_output/stdin/timeout/cwd/check. Byte-mode calls should use the
    stdlib subprocess module directly; this seat is intentionally only for text protocol processes.
    """
    if kwargs.pop("text", True) is not True:
        raise ValueError("Observatory UTF-8 process seat requires text=True")
    requested_encoding = kwargs.pop("encoding", ENCODING)
    requested_errors = kwargs.pop("errors", "strict")
    if str(requested_encoding).lower().replace("_", "-") != ENCODING \
            or requested_errors != "strict":
        raise ValueError("Observatory trusted text transport must be strict UTF-8")
    return subprocess.run(
        command,
        text=True,
        encoding=ENCODING,
        errors="strict",
        env=child_env(env),
        **kwargs)


__all__ = ["ENCODING", "child_env", "run"]
