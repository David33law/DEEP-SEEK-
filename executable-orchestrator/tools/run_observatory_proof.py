#!/usr/bin/env python3
"""Stable compatibility entrypoint for the authoritative Observatory protocol-v5 proof."""
import sys
from prove_complete_observatory_protocol_v3 import main


if __name__ == "__main__":
    sys.exit(main())
