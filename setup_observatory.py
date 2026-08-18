#!/usr/bin/env python3
"""Stable CLI entrypoint for the National Legal Observatory owner ceremony."""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
ORCH = os.path.join(ROOT, "executable-orchestrator")
if ORCH not in sys.path:
    sys.path.insert(0, ORCH)

from lawmax21.observatory_setup_v5 import main


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print("\nOBSERVATORY SETUP: FAIL")
        print(str(exc))
        sys.exit(1)
