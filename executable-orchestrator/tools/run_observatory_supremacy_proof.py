#!/usr/bin/env python3
"""Compatibility entrypoint: the former standalone supremacy proof delegates to protocol-v6.

The historical independent implementation is retired so there is one proof authority and no stale
parallel control plane. All supremacy, causal, calibration, fault and import-closure evidence is
therefore reached through ``prove_complete_observatory_protocol_v6``.
"""
import sys
from prove_complete_observatory_protocol_v6 import main


if __name__ == "__main__":
    sys.exit(main())
