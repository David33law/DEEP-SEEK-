#!/usr/bin/env python3
"""Complete local provider for the owner-signed Observatory protocol v5.

This imports the semantic/distributed/scale/formal/interoperability mock stack and extends only the
roles needed to prove the production control plane: evidence-bound prior-art review and executable
controlled-genome realization. Every genome citation is selected from AST definitions, INV-* IDs and
passing evidence paths supplied by the runner; the trusted validator independently rechecks them.
The provider proves control flow and fail-closed binding, never architecture quality or endorsement.
"""
from __future__ import annotations

import importlib.util
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
BASE_PATH = os.path.join(HERE, "mock_observatory_interoperability_server.py")
SPEC = importlib.util.spec_from_file_location("observatory_interop_mock", BASE_PATH)
base = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(base)
ORIGINAL_ANSWER = base.answer

AXES = [
    "canonical_authority_seat", "evidence_primitive", "identity_model",
    "state_derivation_model", "temporal_model", "normative_effect_model",
    "consistency_commit_model", "replication_distribution_model",
    "trusted_core_topology", "provenance_proof_model", "publication_topology",
    "governance_evolution_model", "scaling_partition_model"]
GENOME_REQUIRED = {
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
GENOME_ARTIFACT = {
    "semantic": "semantic", "formal": "formal_A",
    "interoperability": "interoperability_A",
    "distributed": "distributed", "scale": "scale", "systems": "systems"}


def _deepest(module):
    seen = set()
    while hasattr(module, "base") and id(module) not in seen:
        seen.add(id(module)); module = module.base
    return module


def _context_json(prompt, label):
    return _deepest(base).context_json(prompt, label)


def _proposal(root, family):
    genome = root.genome("G05", 8, "prior-art-impact-compiler")
    return root.proposal(
        family,
        "Compile typed normative impacts into proof-bound ELI-compatible projections from one canonical legal state",
        genome)


def _evidence_refs(prompt):
    frontier = _context_json(prompt, "measured independent frontier") or []
    refs = []
    for row in frontier if isinstance(frontier, list) else []:
        for evidence in row.get("persisted_evidence_refs") or []:
            path = evidence.get("path") if isinstance(evidence, dict) else None
            if isinstance(path, str) and path not in refs:
                refs.append(path)
    return refs[:12]


def prior_art_critic(prompt, role):
    root = _deepest(base)
    manifest = _context_json(prompt, "owner-signed public prior-art manifest") or {}
    sources = manifest.get("sources") or []
    tag = role[len("prior-art-critic-"):]
    refs = _evidence_refs(prompt)
    if not refs:
        raise RuntimeError(
            "prior-art mock received no persisted frontier evidence references")
    challenger_id = "PA-ELI-IMPACT-COMPILER"
    reviews = []
    for source in sources:
        source_id = source.get("source_id")
        if tag == "legal-interoperability" \
                and source_id == "EU-ELI-IMPACT-1.0":
            reviews.append({
                "source_id": source_id,
                "disposition": "MISSING",
                "reasoning": (
                    "The control proof creates one constructible gap: the frontier must build and "
                    "measure a typed ELI-impact compiler projection instead of treating the standard "
                    "as passive metadata or a second authority seat."),
                "evidence_refs": [], "gap_kind": "architecture",
                "required_action": (
                    "Construct and measure the complete impact-compiler challenger."),
                "challenger_ids": [challenger_id]})
        else:
            reviews.append({
                "source_id": source_id,
                "disposition": "SATISFIED",
                "reasoning": (
                    "For zero-cost control calibration, the persisted frontier evidence below is "
                    "sufficient to exercise the production evidence verifier. This is not a claim "
                    "that the mock architecture satisfies the external source."),
                "evidence_refs": refs[:3], "gap_kind": "none",
                "required_action": (
                    "No additional mock action; production remains evidence-bound."),
                "challenger_ids": []})
    challengers = []
    if tag == "legal-interoperability" and any(
            row.get("source_id") == "EU-ELI-IMPACT-1.0" for row in sources):
        challengers.append({
            "challenger_id": challenger_id,
            "source_ids": ["EU-ELI-IMPACT-1.0", "OASIS-LEGALRULEML-1.0"],
            "attacked_assumption": (
                "The current frontier may implement external impact/rule standards only as loose "
                "metadata instead of deterministic proof-bound compiler targets."),
            "falsifiable_gain": (
                "The challenger preserves canonical effect semantics while producing validated "
                "impact projections without an independently writable standard-shaped truth seat."),
            "introduced_cost": (
                "A larger versioned projection/compiler surface and additional conformance evidence."),
            "proposal": _proposal(
                root, "prior-art-ELI-impact-compiler-family")})
    return {"critic_id": f"PRIOR-ART-{tag}", "source_reviews": reviews,
            "challengers": challengers, "protocol_blockers": [], "unresolved": []}


def _candidate_id(prompt):
    match = re.search(
        r"OBS-GENOME-REALIZATION-[A-Za-z0-9_.-]+-[AB]::"
        r"([A-Za-z0-9_.:-]+)", prompt)
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


def _definition(census, artifact):
    row = (census or {}).get(artifact) or {}
    definitions = [
        str(value) for value in row.get("definitions") or []
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", str(value))
        and not str(value).startswith("__")]
    if not definitions:
        raise RuntimeError(
            "genome-realization mock has no AST definition for " + artifact)
    preferred = [
        value for value in definitions
        if value.startswith((
            "open_", "state", "query", "project", "publish", "ingest",
            "transition", "recover", "integrity", "apply", "replay",
            "manifest", "commit", "append", "read", "write"))]
    return (preferred or definitions)[0]


def _evidence_by_group(catalog):
    grouped = {}
    for row in catalog or []:
        if not isinstance(row, dict):
            continue
        path, group = row.get("path"), row.get("group")
        if isinstance(path, str) and isinstance(group, str):
            grouped.setdefault(group, [])
            if path not in grouped[group]:
                grouped[group].append(path)
    if not grouped:
        raise RuntimeError(
            "genome-realization mock received no grouped evidence catalog")
    return grouped


def genome_realization(prompt, role):
    genome = _context_json(prompt, "CONTROLLED GENOME") or {}
    census = _context_json(prompt, "AST SOURCE CENSUS") or {}
    formalization = _context_json(prompt, "FORMALIZATION") or {}
    evidence = _evidence_by_group(
        _context_json(prompt, "PERSISTED EVIDENCE CATALOG") or [])
    invariant_ids = _invariants(formalization)
    candidate_id = _candidate_id(prompt)
    reviews = []
    for index, axis in enumerate(AXES):
        value = genome.get(axis) or {}
        controlled_class = value.get("class") if isinstance(value, dict) else None
        if not controlled_class:
            raise RuntimeError(
                "genome-realization mock received no class for " + axis)
        citations, evidence_refs, seen = [], [], set()
        for group in GENOME_REQUIRED[axis]:
            artifact = GENOME_ARTIFACT[group]
            symbol = _definition(census, artifact)
            key = (artifact, symbol)
            if key not in seen:
                seen.add(key)
                citations.append({
                    "artifact": artifact, "symbol": symbol,
                    "reason": (
                        f"The persisted {artifact} AST definition {symbol} is the executable "
                        f"citation supplied for controlled axis {axis} in the control proof.")})
            paths = evidence.get(group) or []
            if not paths:
                raise RuntimeError(
                    f"genome-realization mock has no evidence for group {group}")
            if paths[0] not in evidence_refs:
                evidence_refs.append(paths[0])
        reviews.append({
            "axis": axis, "class": str(controlled_class), "realized": True,
            "source_symbols": citations,
            "invariant_ids": [invariant_ids[index % len(invariant_ids)]],
            "evidence_refs": evidence_refs,
            "removal_failure": (
                f"Removing the cited definitions or measured evidence would leave "
                f"{axis}={controlled_class} without the source/evidence groups required by the "
                "trusted validator."),
            "falsifier": (
                f"A missing AST definition, unknown invariant, absent evidence hash or executable "
                f"report inconsistent with {axis}={controlled_class} falsifies this claim."),
            "blockers": []})
    return {
        "auditor_id": "GENOME-MOCK-" + role.rsplit("-", 1)[-1],
        "candidate_id": candidate_id, "axis_reviews": reviews,
        "overall_pass": True, "architecture_level_blockers": [],
        "summary": (
            "Every controlled axis is bound only to AST definitions, formalization invariants and "
            "grouped persisted evidence supplied by the runner; the trusted validator rechecks all "
            "citations and their source hashes.")}


def answer(prompt):
    match = re.search(r"^ROLE:\s*(.+)$", prompt, re.M)
    role = match.group(1).strip() if match else "unknown"
    if role.startswith("genome-realization-auditor-"):
        return genome_realization(prompt, role)
    if role.startswith("prior-art-critic-"):
        return prior_art_critic(prompt, role)
    return ORIGINAL_ANSWER(prompt)


def _install_answer(module):
    seen = set()
    while id(module) not in seen:
        seen.add(id(module)); module.answer = answer
        if not hasattr(module, "base"):
            break
        module = module.base
    return module


root = _install_answer(base)

if __name__ == "__main__":
    root.main()
