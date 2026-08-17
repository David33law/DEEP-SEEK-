#!/usr/bin/env python3
"""Stable compatibility entrypoint for the authoritative causal protocol-v5 proof.

The retired prove_complete_observatory_protocol_v3 seat is retained only as an inherited static
compatibility marker; execution always enters prove_complete_observatory_protocol_v5.
"""
import sys
from prove_complete_observatory_protocol_v5 import main


if __name__ == "__main__":
    sys.exit(main())
