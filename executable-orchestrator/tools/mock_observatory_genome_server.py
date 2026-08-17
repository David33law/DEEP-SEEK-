#!/usr/bin/env python3
"""Final zero-cost provider for protocol v5 causal genome realization.

The provider may cite only AST definitions, INV-* IDs and exact-source passing evidence supplied by
the production runner. Auditor A and B use different artifacts/perspectives and different preferred
load-bearing definitions. The trusted validators still reproduce every citation, enforce definition
diversity and independently run causal ablations plus inert controls. This calibrates control flow;
it never proves architecture quality.
"""
from __future__ import annotations

import importlib.util
import os
import re
from collections import Counter

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

# Auditors use the two independently generated formal and interoperability programs rather than
# merely choosing different function names inside one file.
ARTIFACT_BY_AUDITOR = {
    "A": {
        "semantic": "semantic", "formal": "formal_A",
        "interoperability": "interoperability_A",
        "distributed": "distributed", "scale": "scale", "systems": "systems"},
    "B": {
        "semantic": "semantic", "formal": "formal_B",
        "interoperability": "interoperability_B",
        "distributed": "distributed", "scale": "scale", "systems": "systems"},
}

# Ordered candidates are functions/classes known to be called by the corresponding signed reference
# arena. The chooser verifies the definition is actually present in the supplied AST census and
# limits reuse to four axes, so a stale name or generic entrypoint cannot pass.
PREFERRED = {
    "semantic": {
        "canonical_authority_seat": {
            "A": ("replay", "_state"), "B": ("_state", "replay")},
        "evidence_primitive": {
            "A": ("ingest", "_semantic_key"),
            "B": ("_semantic_key", "ingest")},
        "identity_model": {
            "A": ("state_at", "link_jurisprudence", "_state"),
            "B": ("link_jurisprudence", "state_at", "_state")},
        "state_derivation_model": {
            "A": ("_state", "replay"), "B": ("replay", "_state")},
        "temporal_model": {
            "A": ("_applicable", "_time_le", "_state"),
            "B": ("_time_le", "_applicable", "_state")},
        "normative_effect_model": {
            "A": ("apply_change", "_state"),
            "B": ("_state", "apply_change")},
        "provenance_proof_model": {
            "A": ("provenance", "_state"),
            "B": ("_state", "provenance")},
        "publication_topology": {
            "A": ("publish", "_state"), "B": ("_state", "publish")},
        "governance_evolution_model": {
            "A": ("register_change_handler", "apply_change"),
            "B": ("apply_change", "register_change_handler")},
    },
    "formal": {
        "canonical_authority_seat": {
            "A": ("state_root", "_authority_view"),
            "B": ("_authority_view", "state_root")},
        "evidence_primitive": {
            "A": ("initial_state", "transition"),
            "B": ("transition", "initial_state")},
        "identity_model": {
            "A": ("query", "transition"), "B": ("transition", "query")},
        "state_derivation_model": {
            "A": ("state_root", "transition"),
            "B": ("transition", "state_root")},
        "temporal_model": {
            "A": ("query", "transition"), "B": ("transition", "query")},
        "normative_effect_model": {
            "A": ("query", "transition"), "B": ("transition", "query")},
        "consistency_commit_model": {
            "A": ("transition", "state_root"),
            "B": ("state_root", "transition")},
        "replication_distribution_model": {
            "A": ("model_manifest", "transition"),
            "B": ("transition", "model_manifest")},
        "trusted_core_topology": {
            "A": ("_authority_view", "model_manifest", "transition"),
            "B": ("model_manifest", "transition", "_authority_view")},
        "governance_evolution_model": {
            "A": ("transition", "model_manifest"),
            "B": ("model_manifest", "transition")},
    },
    "interoperability": {
        "identity_model": {
            "A": ("_common", "project"), "B": ("project", "_common")},
        "temporal_model": {
            "A": ("_common", "_eli", "_lrml"),
            "B": ("_eli", "_lrml", "_common")},
        "normative_effect_model": {
            "A": ("_impacts", "_eli", "_akn", "_lrml"),
            "B": ("_lrml", "_akn", "_eli", "_impacts")},
        "provenance_proof_model": {
            "A": ("_prov", "project"), "B": ("project", "_prov")},
        "publication_topology": {
            "A": ("project", "_linked", "_eli"),
            "B": ("_linked", "_eli", "project")},
    },
    "distributed": {
        "consistency_commit_model": {
            "A": ("submit", "_safe_group", "_quorum", "_persist"),
            "B": ("_safe_group", "submit", "_quorum", "_persist")},
        "replication_distribution_model": {
            "A": ("heal", "_sync_node", "roots", "integrity"),
            "B": ("_sync_node", "heal", "integrity", "roots")},
    },
    "scale": {
        "scaling_partition_model": {
            "A": ("ingest_batch", "_partition_index", "partition_roots"),
            "B": ("_partition_index", "partition_roots", "ingest_batch")},
    },
    "systems": {
        "trusted_core_topology": {
            "A": ("open_system", "DurableSystem", "_open_with_recovery"),
            "B": ("DurableSystem", "_open_with_recovery", "open_system")},
    },
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


def _definitions(census, artifact):
    row = (census or {}).get(artifact) or {}
    values = [
        str(value) for value in row.get("definitions") or []
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", str(value))
        and not str(value).startswith("__")]
    if not values:
        raise RuntimeError(
            "genome-realization mock has no AST definition for " + artifact)
    return list(dict.fromkeys(values))


def _choose_definition(census, artifact, group, axis, auditor, usage):
    available = _definitions(census, artifact)
    preferred = list((
        PREFERRED.get(group, {}).get(axis, {}).get(auditor, ())))
    candidates = [value for value in preferred if value in available]
    if not candidates:
        # Fail closed in production would be appropriate. The local provider also fails loudly when
        # a signed reference interface changes, rather than inventing a plausible generic citation.
        raise RuntimeError(
            f"genome-realization mock has no known load-bearing definition for "
            f"{auditor}/{axis}/{group}/{artifact}; available={available[:40]}")
    below_limit = [
        value for value in candidates
        if usage[(artifact, value)] < 4]
    pool = below_limit or candidates
    selected = min(
        pool, key=lambda value: (usage[(artifact, value)], candidates.index(value)))
    usage[(artifact, selected)] += 1
    return selected


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
    auditor = role.rsplit("-", 1)[-1]
    if auditor not in ARTIFACT_BY_AUDITOR:
        raise RuntimeError("unknown genome auditor profile: " + auditor)
    auditor_offset = 0 if auditor == "A" else 3
    usage = Counter()
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
        for group in REQUIRED[axis]:
            artifact = ARTIFACT_BY_AUDITOR[auditor][group]
            symbol = _choose_definition(
                census, artifact, group, axis, auditor, usage)
            key = (artifact, symbol)
            if key not in seen_citations:
                seen_citations.add(key)
                citations.append({
                    "artifact": artifact,
                    "symbol": symbol,
                    "reason": (
                        f"The persisted {artifact} AST definition {symbol} "
                        f"is invoked by the signed {group} evaluator and is "
                        f"the causal citation for controlled axis {axis}. ")})
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
                f"Renaming the complete cited definition set while leaving "
                f"its call sites intact must make the signed evaluator for "
                f"{axis}={controlled_class} fail; an inert-definition control "
                "must continue to pass."),
            "falsifier": (
                f"A passing source-bound mutant, failing inert control, "
                f"missing definition, stale evidence hash or executable "
                f"report inconsistent with {axis}={controlled_class} "
                "falsifies this realization claim."),
            "blockers": []})
    return {
        "auditor_id": "GENOME-MOCK-" + auditor,
        "candidate_id": candidate_id,
        "axis_reviews": reviews,
        "overall_pass": True,
        "architecture_level_blockers": [],
        "summary": (
            "Every controlled axis is bound to an auditor-specific known "
            "load-bearing AST definition, a formalization invariant and an "
            "exact-source passing evidence receipt. The trusted harness "
            "rechecks citations and performs independent causal ablation.")}


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
