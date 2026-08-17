#!/usr/bin/env python3
"""Scale-role extension of the Observatory zero-cost mock.

Imports the distributed/meta/prior-art mock stack and adds controlled-genome-labelled
``scale_candidate.py`` implementations. Perspective markers create source-level diversity while the
real scale arena performs restart, rebuild, recovery, partition-balance and publication checks.
"""
import importlib.util
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
BASE_PATH = os.path.join(HERE, "mock_observatory_distributed_server.py")
SPEC = importlib.util.spec_from_file_location("observatory_distributed_mock", BASE_PATH)
base = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(base)
ORIGINAL_ANSWER = base.answer
ROOT = os.path.dirname(os.path.dirname(HERE))
REFERENCE = os.path.join(ROOT, "benchmark", "observatory_scale_reference_candidate.py")


def _reference_source(prompt, role):
    source = open(REFERENCE, encoding="utf-8").read()
    expected = base.base.base.context_json(
        prompt, "EXPECTED CONTROLLED SCALING GENOME") or {}
    model = str(expected.get("scaling_partition_model") or "source_sharding")
    marker = re.sub(r"[^A-Za-z0-9_-]+", "-", role)
    source = source.replace(
        'SCALING_PARTITION_MODEL = "source_sharding"',
        f'SCALING_PARTITION_MODEL = {model!r}')
    source += (
        "\n\n# zero-cost scale implementation-search marker\n"
        "def _scale_implementation_variant_marker():\n"
        f"    return {marker!r}\n")
    return source


def scale_answer(prompt, role):
    return {
        "candidate_id": "SCALE-MOCK",
        "family": "scale-control-proof",
        "mechanism": "genome-labelled deterministic sharded scale reference",
        "rationale": (
            "Calibrates real scale implementation diversity, large-history ingestion, restart, "
            "checkpoint recovery, rebuild and crown paths."),
        "files": [{"path": "scale_candidate.py",
                   "content": _reference_source(prompt, role)}],
    }


def answer(prompt):
    match = re.search(r"^ROLE:\s*(.+)$", prompt, re.M)
    role = match.group(1).strip() if match else "unknown"
    if role.startswith("scale-systems-builder-") or role == "scale-systems-reviser":
        return scale_answer(prompt, role)
    return ORIGINAL_ANSWER(prompt)


base.answer = answer
base.base.answer = answer
base.base.base.answer = answer


if __name__ == "__main__":
    base.base.base.main()
