#!/usr/bin/env python3
"""Complete zero-cost provider for the owner-signed Observatory protocol.

This imports the full semantic/distributed/scale/formal/interoperability mock stack and changes only
the prior-art critic so every SATISFIED conclusion cites evidence paths actually present in the
current disposable run. It proves control flow and fail-closed evidence binding, never architecture
quality or external endorsement.
"""
import importlib.util
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
BASE_PATH = os.path.join(HERE, "mock_observatory_interoperability_server.py")
SPEC = importlib.util.spec_from_file_location("observatory_interop_mock", BASE_PATH)
base = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(base)
ORIGINAL_ANSWER = base.answer


def _deepest(module):
    seen = set()
    while hasattr(module, "base") and id(module) not in seen:
        seen.add(id(module)); module = module.base
    return module


def _context_json(prompt, label):
    root = _deepest(base)
    return root.context_json(prompt, label)


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
    # Fail loudly in the mock if the production frontier context does not expose persisted evidence;
    # inventing a path would defeat the hardening this mock exists to prove.
    if not refs:
        raise RuntimeError("prior-art mock received no persisted frontier evidence references")
    challenger_id = "PA-ELI-IMPACT-COMPILER"
    reviews = []
    for source in sources:
        sid = source.get("source_id")
        if tag == "legal-interoperability" and sid == "EU-ELI-IMPACT-1.0":
            reviews.append({
                "source_id": sid, "disposition": "MISSING",
                "reasoning": (
                    "The control proof deliberately creates one constructible gap: the frontier "
                    "must build and measure a typed ELI-impact compiler projection rather than treat "
                    "the standard as passive metadata or a second authority seat."),
                "evidence_refs": [], "gap_kind": "architecture",
                "required_action": "Construct and measure the complete impact-compiler challenger.",
                "challenger_ids": [challenger_id]})
        else:
            reviews.append({
                "source_id": sid, "disposition": "SATISFIED",
                "reasoning": (
                    "For zero-cost control calibration, the persisted frontier evidence referenced "
                    "below is sufficient to exercise the production evidence verifier. This is not "
                    "a claim that the mock architecture actually satisfies the external source."),
                "evidence_refs": refs[:3], "gap_kind": "none",
                "required_action": "No additional mock action; production remains evidence-bound.",
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
            "proposal": _proposal(root, "prior-art-ELI-impact-compiler-family")})
    return {"critic_id": f"PRIOR-ART-{tag}", "source_reviews": reviews,
            "challengers": challengers, "protocol_blockers": [], "unresolved": []}


def answer(prompt):
    match = re.search(r"^ROLE:\s*(.+)$", prompt, re.M)
    role = match.group(1).strip() if match else "unknown"
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
