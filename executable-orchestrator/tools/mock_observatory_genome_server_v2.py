#!/usr/bin/env python3
"""Final zero-cost mock extension for executable genome-realization auditors.

The mock can cite only symbols, INV-* IDs and evidence paths present in the supplied production
context. The trusted overlay validates every citation again. This exercises control flow and
fail-closed binding; it does not certify architecture quality and is never used by production.
"""
import importlib.util
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
BASE_PATH = os.path.join(HERE, "mock_observatory_genome_server.py")
SPEC = importlib.util.spec_from_file_location("observatory_genome_mock_v1", BASE_PATH)
base = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(base)
ORIGINAL_ANSWER = base.answer

AXES = [
    "canonical_authority_seat", "evidence_primitive", "identity_model",
    "state_derivation_model", "temporal_model", "normative_effect_model",
    "consistency_commit_model", "replication_distribution_model",
    "trusted_core_topology", "provenance_proof_model", "publication_topology",
    "governance_evolution_model", "scaling_partition_model"]
REQUIRED_GROUPS = {
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
GROUP_ARTIFACTS = {
    "semantic": ("semantic",),
    "systems": ("systems",),
    "distributed": ("distributed",),
    "scale": ("scale",),
    "formal": ("formal_A", "formal_B"),
    "interoperability": ("interoperability_A", "interoperability_B"),
    "executable": ("semantic", "systems", "distributed", "scale",
                   "interoperability_A", "interoperability_B"),
}


def _root_module():
    node = base
    seen = set()
    while hasattr(node, "base") and id(node) not in seen:
        seen.add(id(node)); node = node.base
    return node


ROOT = _root_module()


def _context_json(prompt, label, default):
    fn = getattr(ROOT, "context_json", None)
    if callable(fn):
        try:
            value = fn(prompt, label)
            return default if value is None else value
        except Exception:
            pass
    return default


def _context_text(prompt, label):
    fn = getattr(ROOT, "context_text", None)
    if callable(fn):
        try:
            value = fn(prompt, label)
            if value:
                return str(value).strip()
        except Exception:
            pass
    pattern = re.compile(
        r"(?:^|\n)" + re.escape(label) + r"\s*\n[-=]+\s*\n(.*?)(?=\n[A-Z][A-Z0-9 _/-]+\s*\n[-=]+|\Z)",
        re.S)
    match = pattern.search(prompt)
    return match.group(1).strip() if match else ""


def _candidate_id(prompt, census):
    explicit = _context_text(prompt, "CANDIDATE ID").splitlines()
    if explicit and explicit[0].strip():
        return explicit[0].strip().strip('"')
    semantic = census.get("semantic") or {}
    path = str(semantic.get("path") or "")
    stem = os.path.splitext(os.path.basename(path))[0]
    if stem:
        return stem
    ticket = re.search(r"OBS-GENOME-REALIZATION-[^:]+-[AB]::([^\s]+)", prompt)
    return ticket.group(1) if ticket else "UNKNOWN-CANDIDATE"


def _symbol(census, group, used):
    for artifact in GROUP_ARTIFACTS[group]:
        symbols = list((census.get(artifact) or {}).get("symbols") or [])
        preferred = [name for name in symbols
                     if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", str(name))
                     and not str(name).startswith("__")]
        for name in preferred + symbols:
            key = (artifact, str(name))
            if key not in used and re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", str(name)):
                used.add(key)
                return artifact, str(name)
    raise RuntimeError("no supplied AST symbol exists for required group " + group)


def genome_audit(prompt, role):
    genome = _context_json(prompt, "CONTROLLED GENOME", {})
    formalization = _context_json(prompt, "FORMALIZATION", {})
    census = _context_json(prompt, "AST SOURCE CENSUS", {})
    evidence_rows = _context_json(prompt, "PERSISTED EVIDENCE CATALOG", [])
    candidate_id = _candidate_id(prompt, census)
    invariant_ids = []
    for row in formalization.get("invariant_set") or []:
        value = (row.get("id") or row.get("invariant_id")) if isinstance(row, dict) else row
        if value and str(value) not in invariant_ids:
            invariant_ids.append(str(value))
    evidence_refs = [str(row.get("path")) for row in evidence_rows
                     if isinstance(row, dict) and row.get("path")]
    if not invariant_ids or not evidence_refs:
        raise RuntimeError("genome mock received no real invariants/evidence")

    reviews = []
    for index, axis in enumerate(AXES):
        value = genome.get(axis) or {}
        class_name = str(value.get("class") or "")
        if not class_name:
            raise RuntimeError("controlled genome omits " + axis)
        used = set(); citations = []
        for group in REQUIRED_GROUPS[axis]:
            artifact, symbol = _symbol(census, group, used)
            citations.append({
                "artifact": artifact,
                "symbol": symbol,
                "reason": (f"The supplied AST census exposes {symbol} in {artifact}; the trusted "
                           f"validator will reproduce this citation for {axis}.")})
        reviews.append({
            "axis": axis,
            "class": class_name,
            "realized": True,
            "source_symbols": citations,
            "invariant_ids": invariant_ids[:min(3, len(invariant_ids))],
            "evidence_refs": [evidence_refs[index % len(evidence_refs)]],
            "removal_failure": (
                f"Removing the cited implementation seat for {axis} would make the declared "
                f"controlled class {class_name} unrepresented in executable evidence."),
            "falsifier": (
                f"The claim is falsified if any cited symbol, invariant or evidence path is absent, "
                f"or if removing it leaves all measured {axis} behavior unchanged."),
            "blockers": []})
    tag = role.rsplit("-", 1)[-1]
    return {
        "auditor_id": "GENOME-REALIZATION-" + tag,
        "candidate_id": candidate_id,
        "axis_reviews": reviews,
        "overall_pass": True,
        "architecture_level_blockers": [],
        "summary": (
            "Zero-cost control response cites only supplied AST symbols, invariant identifiers and "
            "persisted evidence paths; the trusted validator independently checks every citation.")}


def answer(prompt):
    match = re.search(r"^ROLE:\s*(.+)$", prompt, re.M)
    role = match.group(1).strip() if match else "unknown"
    if role.startswith("genome-realization-auditor-"):
        return genome_audit(prompt, role)
    return ORIGINAL_ANSWER(prompt)


def _propagate():
    node = base; seen = set()
    while id(node) not in seen:
        seen.add(id(node)); node.answer = answer
        if not hasattr(node, "base"):
            break
        node = node.base
    return node


ROOT = _propagate()


if __name__ == "__main__":
    ROOT.main()
