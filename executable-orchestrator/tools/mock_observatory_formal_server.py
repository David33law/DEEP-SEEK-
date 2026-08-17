#!/usr/bin/env python3
"""Formal-model extension of the Observatory zero-cost mock stack.

Adds two source-distinct, behaviorally equivalent, controlled-genome-labelled formal models and a
revision response. The real bounded arena supplies hidden randomized traces and compares behavioral
digests; this mock only calibrates the production control path.
"""
import importlib.util
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
BASE_PATH = os.path.join(HERE, "mock_observatory_scale_server.py")
SPEC = importlib.util.spec_from_file_location("observatory_scale_mock", BASE_PATH)
base = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(base)
ORIGINAL_ANSWER = base.answer
ROOT = os.path.dirname(os.path.dirname(HERE))
REFERENCE = os.path.join(ROOT, "benchmark", "observatory_formal_reference_candidate.py")

CONSTANTS = {
    "canonical_authority_seat": "CANONICAL_AUTHORITY_SEAT",
    "state_derivation_model": "STATE_DERIVATION_MODEL",
    "temporal_model": "TEMPORAL_MODEL",
    "normative_effect_model": "NORMATIVE_EFFECT_MODEL",
    "consistency_commit_model": "CONSISTENCY_COMMIT_MODEL",
    "replication_distribution_model": "REPLICATION_DISTRIBUTION_MODEL",
    "trusted_core_topology": "TRUSTED_CORE_TOPOLOGY",
}


def _original_module():
    return base.base.base.base


def _reference_source(prompt, role):
    source = open(REFERENCE, encoding="utf-8").read()
    expected = _original_module().context_json(
        prompt, "EXPECTED CONTROLLED FORMAL MANIFEST") or {}
    for axis, constant in CONSTANTS.items():
        value = str(expected.get(axis) or {
            "canonical_authority_seat": "evidence_set",
            "state_derivation_model": "replay_reducer",
            "temporal_model": "bitemporal_intervals",
            "normative_effect_model": "typed_directive_interpreter",
            "consistency_commit_model": "single_writer_sequence",
            "replication_distribution_model": "single_primary_read_replicas",
            "trusted_core_topology": "state_machine_kernel",
        }[axis])
        source = re.sub(
            rf'^{constant}\s*=\s*["\'][^"\']+["\']',
            f'{constant} = {value!r}', source, count=1, flags=re.M)
    marker = re.sub(r"[^A-Za-z0-9_-]+", "-", role)
    source += (
        "\n\n# zero-cost independent formal-model marker\n"
        "def _formal_model_implementation_marker():\n"
        f"    return {marker!r}\n")
    return source


def formal_answer(prompt, role):
    return {
        "candidate_id": "FORMAL-MOCK",
        "family": "formal-control-proof",
        "mechanism": "pure bounded transition reference with hidden exhaustive traces",
        "rationale": (
            "Calibrates independent source diversity, controlled-manifest fidelity, exhaustive trace "
            "execution, revision and behavioral-digest agreement."),
        "files": [{"path": "formal_candidate.py",
                   "content": _reference_source(prompt, role)}],
    }


def answer(prompt):
    match = re.search(r"^ROLE:\s*(.+)$", prompt, re.M)
    role = match.group(1).strip() if match else "unknown"
    if role.startswith("formal-model-builder-") or role == "formal-model-reviser":
        return formal_answer(prompt, role)
    return ORIGINAL_ANSWER(prompt)


base.answer = answer
base.base.answer = answer
base.base.base.answer = answer
base.base.base.base.answer = answer


if __name__ == "__main__":
    base.base.base.base.main()
