#!/usr/bin/env python3
"""Causal-aware final localhost provider for the Observatory zero-cost proof.

Imports the complete genome-aware provider and removes the only calibration citation that is not
exercised by the hidden semantic scenario: extension registration itself. Governance is instead tied
to ``apply_change``, which is executed repeatedly and therefore must fail its auditor-specific causal
ablation. All other citations remain selected from known signed-reference call paths and are still
validated and ablated by the trusted runner.
"""
from __future__ import annotations

import importlib.util
import os

HERE = os.path.dirname(os.path.abspath(__file__))
BASE_PATH = os.path.join(HERE, "mock_observatory_genome_server.py")
SPEC = importlib.util.spec_from_file_location(
    "observatory_genome_mock", BASE_PATH)
base = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(base)

base.PREFERRED["semantic"]["governance_evolution_model"] = {
    "A": ("apply_change",),
    "B": ("apply_change",),
}

# Fail immediately if a future reference-provider refactor silently restores a dead calibration
# citation. Production auditors remain unrestricted; this assertion applies only to the zero-cost
# local reference stack.
for auditor, values in base.PREFERRED["semantic"][
        "governance_evolution_model"].items():
    if values != ("apply_change",):
        raise RuntimeError(
            "causal mock governance citation drift for auditor " + auditor)


if __name__ == "__main__":
    base.root.main()
