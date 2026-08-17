#!/usr/bin/env python3
"""Distributed-role extension of the Observatory zero-cost mock.

Imports the complete meta/prior-art/implementation mock and adds architecture-genome-labelled
``distributed_candidate.py`` responses. Source markers vary with implementation perspective so the
production distributed-diversity gate is actually exercised. This is control-plane calibration only.
"""
import importlib.util
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
BASE_PATH = os.path.join(HERE, "mock_observatory_meta_server.py")
SPEC = importlib.util.spec_from_file_location("observatory_meta_mock", BASE_PATH)
base = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(base)
ORIGINAL_ANSWER = base.answer
ROOT = os.path.dirname(os.path.dirname(HERE))
REFERENCE = os.path.join(ROOT, "benchmark", "observatory_distributed_reference_candidate.py")


def _reference_source(prompt, role):
    source = open(REFERENCE, encoding="utf-8").read()
    expected = base.base.context_json(
        prompt, "EXPECTED CONTROLLED DISTRIBUTED GENOME") or {}
    replication = str(expected.get(
        "replication_distribution_model") or "single_primary_read_replicas")
    commit = str(expected.get(
        "consistency_commit_model") or "single_writer_sequence")
    marker = re.sub(r"[^A-Za-z0-9_-]+", "-", role)
    source = source.replace(
        'REPLICATION_MODEL = "single_primary_read_replicas"',
        f'REPLICATION_MODEL = {replication!r}')
    source = source.replace(
        'COMMIT_MODEL = "single_writer_sequence"',
        f'COMMIT_MODEL = {commit!r}')
    if replication == "bft_consensus" or commit == "quorum_certificate":
        source = source.replace('"byzantine_faults": 0', '"byzantine_faults": 1')
    source += (
        "\n\n# zero-cost distributed implementation-search marker\n"
        "def _distributed_implementation_variant_marker():\n"
        f"    return {marker!r}\n")
    return source


def distributed_answer(prompt, role):
    return {
        "candidate_id": "DISTRIBUTED-MOCK",
        "family": "distributed-control-proof",
        "mechanism": "genome-labelled bounded distributed reference implementation",
        "rationale": (
            "Calibrates the real distributed builder/reviser, controlled-genome fidelity, "
            "implementation-diversity, partition, crash, corruption and crown paths."),
        "files": [{"path": "distributed_candidate.py",
                   "content": _reference_source(prompt, role)}],
    }


def answer(prompt):
    match = re.search(r"^ROLE:\s*(.+)$", prompt, re.M)
    role = match.group(1).strip() if match else "unknown"
    if role.startswith("distributed-systems-builder-") \
            or role == "distributed-systems-reviser":
        return distributed_answer(prompt, role)
    return ORIGINAL_ANSWER(prompt)


# The active HTTP Handler is defined in the original mock module. The meta wrapper already replaced
# that module's global answer once; replace it again here so distributed roles reach this extension.
base.answer = answer
base.base.answer = answer


if __name__ == "__main__":
    base.base.main()
