#!/usr/bin/env python3
"""Interoperability-role extension of the complete Observatory zero-cost mock stack."""
import importlib.util
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
BASE_PATH = os.path.join(HERE, "mock_observatory_formal_server.py")
SPEC = importlib.util.spec_from_file_location("observatory_formal_mock", BASE_PATH)
base = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(base)
ORIGINAL_ANSWER = base.answer
ROOT = os.path.dirname(os.path.dirname(HERE))
REFERENCE = os.path.join(ROOT, "benchmark",
                         "observatory_interoperability_reference_candidate.py")
CONSTANTS = {
    "identity_model": "IDENTITY_MODEL",
    "temporal_model": "TEMPORAL_MODEL",
    "normative_effect_model": "NORMATIVE_EFFECT_MODEL",
    "provenance_proof_model": "PROVENANCE_PROOF_MODEL",
    "publication_topology": "PUBLICATION_TOPOLOGY",
}


def _original_module():
    return base.base.base.base.base


def _reference_source(prompt, role):
    source = open(REFERENCE, encoding="utf-8").read()
    expected = _original_module().context_json(
        prompt, "EXPECTED CONTROLLED INTEROPERABILITY MANIFEST") or {}
    defaults = {"identity_model": "composite_identity",
                "temporal_model": "bitemporal_intervals",
                "normative_effect_model": "typed_directive_interpreter",
                "provenance_proof_model": "provenance_graph",
                "publication_topology": "compiled_read_only_projections"}
    for axis, constant in CONSTANTS.items():
        value = str(expected.get(axis) or defaults[axis])
        source = re.sub(rf'^{constant}\s*=\s*["\'][^"\']+["\']',
                        f'{constant} = {value!r}', source, count=1, flags=re.M)
    marker = re.sub(r"[^A-Za-z0-9_-]+", "-", role)
    source += ("\n\n# zero-cost interoperability implementation marker\n"
               "def _interoperability_variant_marker():\n"
               f"    return {marker!r}\n")
    return source


def interop_answer(prompt, role):
    return {"candidate_id": "INTEROP-MOCK", "family": "interop-control-proof",
            "mechanism": "bounded one-root legal-interoperability projection",
            "rationale": "Calibrates independent projection implementations and hidden conformance.",
            "files": [{"path": "interoperability_candidate.py",
                       "content": _reference_source(prompt, role)}]}


def answer(prompt):
    match = re.search(r"^ROLE:\s*(.+)$", prompt, re.M)
    role = match.group(1).strip() if match else "unknown"
    if role.startswith("interoperability-builder-") or role == "interoperability-reviser":
        return interop_answer(prompt, role)
    return ORIGINAL_ANSWER(prompt)


base.answer = answer
base.base.answer = answer
base.base.base.answer = answer
base.base.base.base.answer = answer
base.base.base.base.base.answer = answer


if __name__ == "__main__":
    base.base.base.base.base.main()
