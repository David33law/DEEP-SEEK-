#!/usr/bin/env python3
"""Compatibility entrypoint: historical protocol-v2 command delegates to final protocol-v6 authority."""
import sys
from prove_complete_observatory_protocol_v6 import main


if __name__ == "__main__":
    sys.exit(main())
