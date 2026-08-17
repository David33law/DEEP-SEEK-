#!/usr/bin/env python3
"""Final zero-cost provider for protocol v5, including executable genome realization.

The response uses only AST definitions, INV-* IDs and persisted evidence paths actually supplied by
the production runner. The trusted validator independently reproduces every citation, so invented
symbols, stale evidence or generic one-entrypoint mappings make the proof fail. This calibrates
control flow, not architecture quality.
"""
import importlib.util
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
BASE_PATH = os.path.join(HERE, "mock_observatory_protocol_server.py")
SPEC = importlib.util.spec_from_file_location(
    "observatory_protocol_mock", BASE_PATH)
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
    "trusted_core_topology": ("formal", "systems"),
    "provenance_proof_model": ("semantic", "interoperability"),
    "publication_topology": ("semantic", "interoperability"),
    "governance_evolution_model": ("semantic", "formal"),
    "scaling_partition_model": ("scale",),
}
ARTIFACT = {
    "semantic": "semantic",
    "formal": "formal_A",
    "interoperability": "interoperability_A",
    "distributed": "distributed",
    "scale": "scale",
    "systems": "systems",
}


def _deepest(module):
    seen = set()
    while hasattr(module, "base") and id(module) not in seen:
        seen.add(id(module))
        module = module.base
    return module


def _context(prompt, label):
    return _deepest(base).context_json(prompt, label)


def _candidate_id(prompt):
    match = re.search(
        r"OBS-GENOME-REALIZATION-[A-Za-z0-9_.-]+-[AB]::"
        r"([A-Za-z0-9_.:-]+)",
        prompt)
    if not match:
        match = re.search(
            r"GENOME-REALIZATION[^\n]*::([A-Za-z0-9_.:-]+)", prompt)
    if not match:
        raise RuntimeError(
            "genome-realization mock could not recover candidate ID")
    return match.group(1)


def _invariants(formalization):
    result = []
    for row in (formalization or {}).get("invariant_set") or []:
        value = ((row.get("id") or row.get("invariant_id"))
                 if isinstance(row, dict) else row)
        if value and str(value) not in result:
            result.append(str(value))
    if not result:
        raise RuntimeError(
            "genome-realization mock received no INV-* IDs")
    return result


def _definitions(census, artifact):
    row = (census or {}).get(artifact) or {}
    values = [
        str(value) for value in row.get("definitions") or []
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", str(value))
        and not str(value).startswith("__")]
    if not values:
        raise RuntimeError(
            "genome-realization mock has no AST definition for " + artifact)
    preferred = [
        value for value in values
        if value.startswith((
            "open_", "state", "query", "project", "publish", "ingest",
            "transition", "recover", "integrity", "apply", "replay",
            "manifest", "commit", "append", "read", "write"))]
    return list(dict.fromkeys(preferred + values))


def _definition(census, artifact, index):
    definitions = _definitions(census, artifact)
    return definitions[index % len(definitions)]


def _evidence_by_group(catalog):
    grouped = {}
    for row in catalog or []:
        if not isinstance(row, dict):
            continue
        path = row.get("path")
        group = row.get("group")
        if isinstance(path, str) and isinstance(group, str):
            grouped.setdefault(group, [])
            if path not in grouped[group]:
                grouped[group].append(path)
    if not grouped:
        raise RuntimeError(
            "genome-realization mock received no persisted evidence catalog")
    return grouped


def realization_answer(prompt, role):
    genome = _context(prompt, "CONTROLLED GENOME") or {}
    census = _context(prompt, "AST SOURCE CENSUS") or {}
    formalization = _context(prompt, "FORMALIZATION") or {}
    evidence = _evidence_by_group(
        _context(prompt, "PERSISTED EVIDENCE CATALOG") or [])
    invariant_ids = _invariants(formalization)
    candidate_id = _candidate_id(prompt)
    auditor_offset = 0 if role.endswith("-A") else 3
    reviews = []
    for index, axis in enumerate(AXES):
        value = genome.get(axis) or {}
        controlled_class = (
            value.get("class") if isinstance(value, dict) else None)
        if not controlled_class:
            raise RuntimeError(
                "genome-realization mock received no class for " + axis)
        citations = []
        evidence_refs = []
        seen_citations = set()
        for group_index, group in enumerate(REQUIRED[axis]):
            artifact = ARTIFACT[group]
            symbol = _definition(
                census, artifact, index + group_index + auditor_offset)
            key = (artifact, symbol)
            if key not in seen_citations:
                seen_citations.add(key)
                citations.append({
                    "artifact": artifact,
                    "symbol": symbol,
                    "reason": (
                        f"The persisted {artifact} AST definition {symbol} "
                        f"is the executable citation supplied for controlled "
                        f"axis {axis} in the zero-cost control proof.")})
            paths = evidence.get(group) or []
            if not paths:
                raise RuntimeError(
                    "genome-realization mock has no persisted evidence "
                    f"for required group {group}")
            selected = paths[(index + auditor_offset) % len(paths)]
            if selected not in evidence_refs:
                evidence_refs.append(selected)
        reviews.append({
            "axis": axis,
            "class": str(controlled_class),
            "realized": True,
            "source_symbols": citations,
            "invariant_ids": [
                invariant_ids[(index + auditor_offset) % len(invariant_ids)]],
            "evidence_refs": evidence_refs,
            "removal_failure": (
                f"Removing the cited definitions or measured evidence "
                f"would leave {axis}={controlled_class} without the "
                "source/evidence groups required by the trusted validator."),
            "falsifier": (
                f"A missing AST definition, unknown invariant, absent "
                f"evidence hash or executable report inconsistent with "
                f"{axis}={controlled_class} falsifies this claim."),
            "blockers": []})
    return {
        "auditor_id": "GENOME-MOCK-" + role.rsplit("-", 1)[-1],
        "candidate_id": candidate_id,
        "axis_reviews": reviews,
        "overall_pass": True,
        "architecture_level_blockers": [],
        "summary": (
            "Every controlled axis is bound only to diversified definitions, "
            "formalization invariants and grouped persisted evidence "
            "supplied by the production runner; the trusted validator "
            "rechecks every citation and rejects generic collapse.")}


def answer(prompt):
    match = re.search(r"^ROLE:\s*(.+)$", prompt, re.M)
    role = match.group(1).strip() if match else "unknown"
    if role.startswith("genome-realization-auditor-"):
        return realization_answer(prompt, role)
    return ORIGINAL_ANSWER(prompt)


def _install(module):
    seen = set()
    while id(module) not in seen:
        seen.add(id(module))
        module.answer = answer
        if not hasattr(module, "base"):
            break
        module = module.base
    return module


root = _install(base)

if __name__ == "__main__":
    root.main()
