#!/usr/bin/env python3
"""Stable compatibility entrypoint for the authoritative Observatory proof.

The retired prove_complete_observatory_protocol_v3 seat and inherited
prove_complete_observatory_protocol_v5 seat remain protocol-history/static compatibility markers;
execution always enters prove_complete_observatory_protocol_v6, which strictly extends v5 through
static-v8: inherited static-v7 fault closure plus independently executed cwd/PYTHONPATH import closure.

This entrypoint is intentionally independent of the caller's current working directory and
PYTHONPATH. The repository's executable-orchestrator directory is installed before importing any
proof wrapper so the ``lawmax21`` package is available throughout the authoritative import chain.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ORCH = os.path.dirname(HERE)
LAWMAX_PACKAGE = os.path.join(ORCH, "lawmax21", "__init__.py")
if not os.path.isfile(LAWMAX_PACKAGE):
    raise RuntimeError("authoritative proof cannot locate lawmax21 package: " + LAWMAX_PACKAGE)
if ORCH not in sys.path:
    sys.path.insert(0, ORCH)

from prove_complete_observatory_protocol_v6 import main


if __name__ == "__main__":
    sys.exit(main())
