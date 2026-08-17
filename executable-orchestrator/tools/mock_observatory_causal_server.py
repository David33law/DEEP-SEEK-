#!/usr/bin/env python3
"""Causal-aware final localhost provider for the Observatory zero-cost proof.

Imports the complete genome-aware provider and replaces calibration citations that are either not
exercised or do not expose the claimed axis in their own AST bodies. Every replacement is a function
or class exercised by the signed reference arenas and contains axis-relevant source vocabulary, so
trusted causal attribution can distinguish a real axis failure from a generic crash. Production
auditors remain unrestricted.
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

OVERRIDES = {
    ("semantic", "governance_evolution_model"): {
        "A": ("apply_change",),
        "B": ("apply_change",),
    },
    ("formal", "consistency_commit_model"): {
        "A": ("transition",),
        "B": ("transition",),
    },
    ("formal", "replication_distribution_model"): {
        "A": ("model_manifest",),
        "B": ("model_manifest",),
    },
    ("formal", "trusted_core_topology"): {
        "A": ("model_manifest",),
        "B": ("model_manifest",),
    },
    ("interoperability", "identity_model"): {
        "A": ("_common",),
        "B": ("_eli",),
    },
    ("interoperability", "provenance_proof_model"): {
        "A": ("_prov",),
        "B": ("_prov",),
    },
    ("distributed", "replication_distribution_model"): {
        "A": ("heal",),
        "B": ("integrity",),
    },
}
for (group, axis), values in OVERRIDES.items():
    base.PREFERRED[group][axis] = values

# Fail immediately if a future reference-provider refactor silently restores a dead or semantically
# ungrounded calibration citation. The trusted AST/evaluator/ablation validators remain authoritative.
for (group, axis), expected in OVERRIDES.items():
    actual = base.PREFERRED[group][axis]
    if actual != expected:
        raise RuntimeError(
            f"causal mock citation drift for {group}/{axis}: {actual!r}")


if __name__ == "__main__":
    base.root.main()
