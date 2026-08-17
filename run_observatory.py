#!/usr/bin/env python3
"""Stable CLI entrypoint for the National Legal Observatory research protocol."""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
ORCH = os.path.join(ROOT, "executable-orchestrator")
if ORCH not in sys.path:
    sys.path.insert(0, ORCH)

from lawmax21.observatory_launcher_v2 import main


if __name__ == "__main__":
    sys.exit(main())
