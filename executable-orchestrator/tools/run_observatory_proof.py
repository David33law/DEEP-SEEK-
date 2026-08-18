#!/usr/bin/env python3
"""Stable compatibility entrypoint for the authoritative Observatory proof.

The retired prove_complete_observatory_protocol_v3 seat and inherited
prove_complete_observatory_protocol_v5 seat remain protocol-history/static compatibility markers;
execution always enters prove_complete_observatory_protocol_v6, which strictly extends v5 with
static-v7 and independently reverified actual-container fault evidence.
"""
import sys
from prove_complete_observatory_protocol_v6 import main


if __name__ == "__main__":
    sys.exit(main())
