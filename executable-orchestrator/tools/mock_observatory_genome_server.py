#!/usr/bin/env python3
"""Final zero-cost provider for protocol v5, including executable genome realization.

The response uses only AST symbols, INV-* IDs and persisted evidence paths actually supplied by the
production runner. The trusted validator independently reproduces every citation, so invented
symbols or evidence would make the proof fail. This calibrates control flow, not architecture quality.
"""
import importlib.util
import re
import os

HERE = os.path.dirname(os.path.abspath(__file__))
BASE_PATH = os.path.join(HERE, "mock_observatory_protocol_server.py")
SPEC = importlib.util.spec_from_file_location("observatory_protocol_mock", BASE_PATH)
base = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(base)
ORIGINAL_ANSWER = base.answer

AXES = [
    "canonical_authority_seat", "evidence_primitive", "identity_model",
    "state_derivation_model", "temporal_model", "normative_effect_model",
    "consistency_commit_model", "replication_distribution_model",
    "trusted_core_topology", "provenance_proof_model", "publication_topology",
    "governance_evolution_model", "scaling_partition_model"]
REQUIRED = {
    "canonical_authority_seat": ("semantic", "formal"),
    "evidence_primitive": ("semantic", "formal"),
    "identity_model": ("semantic", "formal", "interoperability"),
    "state_derivation_model": ("semantic", "formal"),
    "temporal_model": ("semantic", "formal", "interoperability"),
    "normative_effect_model": ("semantic", "formal", "interoperability"),
    "consistency_commit_model": ("distributed", "formal"),
    "replication_distribution_model": ("distributed", "formal"),
    "trusted_core_topology": ("formal", "executable"),
    "provenance_proof_model": ("semantic", "interoperability"),
    "publication_topology": ("semantic", "interoperability"),
    "governance_evolution_model": ("semantic", "formal"),
    "scaling_partition_model": ("scale",),
}
ARTIFACT = {
    "semantic": "semantic", "formal": "formal_A",
    "interoperability": "interoperability_A", "distributed": "distributed",
    "scale": "scale", "executable": "systems"}


def _deepest(module):
    seen = set()
    while hasattr(module, "base") and id(module) not in seen:
        seen.add(id(module)); module = module.base
    return module


def _context(prompt, label):
    return _deepest(base).context_json(prompt, label)


def _candidate_id(prompt):
    match = re.search(
        r"OBS-GENOME-REALIZATION-[A-Za-z0-9_.-]+-[AB]::([A-Za-z0-9_.:-]+)",
        prompt)
    if not match:
        match = re.search(r"GENOME-REALIZATION[^\n]*::([A-Za-z0-9_.:-]+)", prompt)
    if not match:
        raise RuntimeError("genome-realization mock could not recover candidate ID")
    return match.group(1)


def _invariants(formalization):
    result = []
    for row in (formalization or {}).get("invariant_set") or []:
        value = ((row.get("id") or row.get("invariant_id"))
                 if isinstance(row, dict) else row)
        if value and str(value) not in result:
            result.append(str(value))
    if not result:
        raise RuntimeError("genome-realization mock received no INV-* IDs")
    return result


def _symbol(census, artifact):
    row = (census or {}).get(artifact) or {}
    symbols = [str(value) for value in row.get("symbols") or []
               if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", str(value))
               and not str(value).startswith("__")]
    if not symbols:
        raise RuntimeError("genome-realization mock has no AST symbol for " + artifact)
    preferred = [value for value in symbols
                 if value.startswith(("open_", "state", "query", "project", "publish",
                                      "ingest", "transition", "recover", "integrity"))]
    return (preferred or symbols)[0]


def _evidence_paths(catalog):
    paths = []
    for row in catalog or []:
        path = row.get("path") if isinstance(row, dict) else None
        if isinstance(path, str) and path not in paths:
            paths.append(path)
    if not paths:
        raise RuntimeError("genome-realization mock received no persisted evidence paths")
    return paths[:4]


def realization_answer(prompt, role):
    genome = _context(prompt, "CONTROLLED GENOME") or {}
    census = _context(prompt, "AST SOURCE CENSUS") or {}
    formalization = _context(prompt, "FORMALIZATION") or {}
    evidence = _evidence_paths(_context(prompt, "PERSISTED EVIDENCE CATALOG") or [])
    invariant_ids = _invariants(formalization)
    candidate_id = _candidate_id(prompt)
    reviews = []
    for index, axis in enumerate(AXES):
        value = genome.get(axis) or {}
        controlled_class = value.get("class") if isinstance(value, dict) else None
        if not controlled_class:
            raise RuntimeError("genome-realization mock received no class for " + axis)
        citations = []
        seen = set()
        for group in REQUIRED[axis]:
            artifact = ARTIFACT[group]
            symbol = _symbol(census, artifact)
            key = (artifact, symbol)
            if key in seen:
                continue
            seen.add(key)
            citations.append({
                "artifact": artifact, "symbol": symbol,
                "reason": (
                    f"The persisted {artifact} AST symbol {symbol} is the executable witness used "
                    f"by the zero-cost control proof for controlled axis {axis}.")})
        reviews.append({
            "axis": axis, "class": str(controlled_class), "realized": True,
            "source_symbols": citations,
            "invariant_ids": [invariant_ids[index % len(invariant_ids)]],
            "evidence_refs": [evidence[index % len(evidence)]],
            "removal_failure": (
                f"Removing the cited mechanism would make the {axis} class unrepresented in the "
                "candidate source/evidence chain and the trusted citation validator would reject it."),
            "falsifier": (
                f"A missing AST symbol, unknown invariant, absent evidence hash or executable report "
                f"showing behavior inconsistent with {axis}={controlled_class} falsifies this claim."),
            "blockers": []})
    return {
        "auditor_id": "GENOME-MOCK-" + role.rsplit("-", 1)[-1],
        "candidate_id": candidate_id, "axis_reviews": reviews,
        "overall_pass": True, "architecture_level_blockers": [],
        "summary": (
            "Every controlled axis is bound to citations supplied by the production AST census, "
            "formalization and persisted evidence catalog; the trusted validator rechecks them.")}


def answer(prompt):
    match = re.search(r"^ROLE:\s*(.+)$", prompt, re.M)
    role = match.group(1).strip() if match else "unknown"
    if role.startswith("genome-realization-auditor-"):
        return realization_answer(prompt, role)
    return ORIGINAL_ANSWER(prompt)


def _install(module):
    seen = set()
    while id(module) not in seen:
        seen.add(id(module)); module.answer = answer
        if not hasattr(module, "base"):
            break
        module = module.base
    return module


root = _install(base)

if __name__ == "__main__":
    root.main()
