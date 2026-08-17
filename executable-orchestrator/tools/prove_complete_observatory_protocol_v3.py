#!/usr/bin/env python3
"""Compatibility entrypoint: final proof authority is protocol-v5 causal closure."""
import sys
from prove_complete_observatory_protocol_v5 import main


if __name__ == "__main__":
    sys.exit(main())
