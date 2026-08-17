#!/usr/bin/env python3
"""Route the authoritative causal E2E through the complete genome-aware localhost provider.

The readable core proof starts ``mock_observatory_protocol_server.py``. Genome realization and causal
ablation require the final extension chain in ``mock_observatory_genome_server.py``. This wrapper
rewrites only that one localhost-provider command and passes every evaluator, Git and owner-signature
subprocess through unchanged. Real-provider endpoints are never affected.
"""
from __future__ import annotations

import os

import prove_complete_observatory_protocol_causal_hardened as base

PROVIDER_ROUTING_FILE = (
    "executable-orchestrator/tools/"
    "prove_complete_observatory_protocol_causal_provider_hardened.py")
base.CAUSAL_FILES.add(PROVIDER_ROUTING_FILE)
base.CORE.REQUIRED_PROTOCOL_FILES.add(PROVIDER_ROUTING_FILE)
_ORIGINAL_POPEN = base.CORE.subprocess.Popen


def _genome_provider_popen(command, *args, **kwargs):
    if isinstance(command, (list, tuple)):
        values = list(command)
        for index, value in enumerate(values):
            if os.path.basename(str(value)) == \
                    "mock_observatory_protocol_server.py":
                values[index] = os.path.join(
                    os.path.dirname(str(value)),
                    "mock_observatory_genome_server.py")
                break
        command = values
    return _ORIGINAL_POPEN(command, *args, **kwargs)


base.CORE.subprocess.Popen = _genome_provider_popen
main = base.main
sha256_file = base.sha256_file

__all__ = ["main", "sha256_file"]


if __name__ == "__main__":
    import sys
    sys.exit(main())
