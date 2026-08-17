#!/usr/bin/env python3
"""Contract-rich extension of the zero-cost Observatory mock.

The base mock continues to exercise the existing production roles. This wrapper adds responses for
mechanical coverage, meta-search, taxonomy consensus and independent dry-wave closure. It deliberately
injects one controlled ``other`` claim through G96 so the authoritative proof traverses the real
taxonomy-adjudication and deferred-normalization path. It proves control flow and schema binding,
never architecture quality.
"""
import importlib.util
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
BASE_PATH = os.path.join(HERE, "mock_observatory_server.py")
SPEC = importlib.util.spec_from_file_location("observatory_base_mock", BASE_PATH)
base = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(base)
ORIGINAL_ANSWER = base.answer


def _axis(axis, cls, tag):
    return {"class": cls,
            "detail": f"{tag} selects controlled class {cls} for {axis} to satisfy a mechanical search obligation."}


def _targeted_seed(code, index, obligation):
    genome = base.genome("G01", index, f"targeted-{code}-{index}")
    required = obligation.get("required_classes")
    if isinstance(required, list):
        for item in required:
            axis, cls = item.get("axis"), item.get("class")
            if axis in base.OPTIONS and cls in base.OPTIONS[axis]:
                genome[axis] = _axis(axis, cls, f"targeted-{code}-{index}")
    elif obligation.get("kind") == "axis_class":
        axis, cls = obligation["axis"], obligation["class"]
        genome[axis] = _axis(axis, cls, f"targeted-{code}-{index}")
    elif obligation.get("kind") == "pair":
        axis, cls = obligation["axis"], obligation["class"]
        other, other_cls = obligation["counterpart_axis"], obligation["counterpart_class"]
        genome[axis] = _axis(axis, cls, f"targeted-{code}-{index}")
        genome[other] = _axis(other, other_cls, f"targeted-{code}-{index}")
    pivot = base.GENOME_FIELDS[(index + len(code)) % len(base.GENOME_FIELDS)]
    if not ((obligation.get("axis") == pivot)
            or (obligation.get("counterpart_axis") == pivot)
            or any(x.get("axis") == pivot for x in (required or []))):
        values = base.OPTIONS[pivot]
        cls = values[(index * 3 + len(code)) % len(values)]
        genome[pivot] = _axis(pivot, cls, f"targeted-{code}-{index}")
    return genome


def targeted_lineage(prompt):
    obligations = base.context_json(prompt, "targeted obligations") or []
    match = re.search(r"lineage\s+([A-Za-z0-9_-]+)/([A-Za-z0-9_-]+)", prompt)
    code = match.group(1) if match else "T00"
    name = match.group(2) if match else "targeted"
    candidates = []
    count = max(6, len(obligations))
    for index in range(1, count + 1):
        obligation = obligations[(index - 1) % len(obligations)] if obligations else {}
        genome = _targeted_seed(code, index, obligation)
        candidates.append({
            "seed_id": f"S{index}",
            "family": f"{code}-targeted-architecture-{index}",
            "thesis": (
                f"Targeted whole-system architecture {code}/{index} exists to exercise the exact "
                "mechanical coverage or meta-search obligation supplied by the production runner."),
            "genome": genome,
            "mechanisms": [
                f"{code}/{index} obligation-specific authority mechanism",
                f"{code}/{index} deterministic temporal and normative-effect mechanism",
                f"{code}/{index} proof-bound publication and recovery mechanism",
            ],
            "decisive_advantages": [
                f"{code}/{index} closes a mechanically named search gap",
                f"{code}/{index} remains executable and falsifiable in both arenas",
            ],
            "assumptions": [
                f"{code}/{index} assumes its selected controlled classes are mission-compatible",
                f"{code}/{index} assumes deterministic evidence is sufficient for trusted transitions",
            ],
            "failure_modes": [
                f"{code}/{index} fails if the target class combination cannot preserve canonical identity",
                f"{code}/{index} fails if durable reconstruction diverges under fault injection",
            ],
            "why_not_higher": (
                "This targeted seed has not yet survived blueprint expansion, formalization, semantic "
                "replay, durable fault injection, recombination or closure audit."),
        })
    return {
        "lineage": f"{code}/{name}",
        "candidates": candidates[:10],
        "rejected": [
            {"idea": f"{code}-rename-only", "reason": "Renaming an attempted class vector creates no structural novelty."},
            {"idea": f"{code}-unmeasurable", "reason": "A proposal without executable falsifiers cannot discharge the targeted obligation."},
        ],
        "finalist_ids": ["S1", "S2"],
        "exhaustion_note": (
            "The returned seeds literally exercise the supplied controlled-class obligations and "
            "remain subject to executable selection; no quality or supremacy claim is made."),
    }


def ontology_lineage(prompt):
    obj = base.lineage_answer(prompt)
    # Exercise a real taxonomy challenge. The two independent mock adjudicators below map this
    # deliberately vague `other` choice to the already-controlled hybrid authority class.
    first = obj["candidates"][0]
    first["genome"]["canonical_authority_seat"] = {
        "class": "other",
        "detail": (
            "A rhetorically novel authority seat is proposed without a distinct falsifiable behavior; "
            "the taxonomy adjudicators must determine whether it is merely the existing hybrid class."),
    }
    return obj


def meta_critic(prompt, tag):
    return {
        "critic_id": f"META-{tag}",
        "protocol_strengths": [
            "The protocol separates structural class identity from free-form prose.",
            "The protocol constructs candidates and measures both semantic and durable behavior.",
            "The protocol requires active novelty waves, lower bounds and independent destroyers.",
        ],
        "blind_spots": [],
        "attainable_improvements": [],
        "dynamic_directives": [],
        "taxonomy_observations": [],
        "supports_current_protocol": True,
    }


def taxonomy_adjudicator(prompt):
    claim = base.context_json(prompt, "taxonomy claim") or {}
    claim_id = claim.get("claim_id", "0" * 64)
    raw = str(claim.get("claim") or "")
    if raw.startswith("other:"):
        axis = raw.split(":", 1)[1]
        mapped = "hybrid"
    else:
        axis = "canonical_authority_seat"
        mapped = "hybrid"
    return {
        "claim_id": claim_id,
        "decision": "NON_DISTINCT",
        "mapped_axis": axis,
        "mapped_class": mapped,
        "argument": (
            "The supplied claim names no behavior outside the existing hybrid controlled class; its "
            "authority, commit and verification consequences remain fully expressible there."),
        "falsifier": (
            "A concrete invariant or executable fault result that cannot be represented by the hybrid "
            "class would falsify this non-distinction decision and require a signed taxonomy extension."),
    }


def closure_auditor(prompt, tag):
    facts = base.context_json(prompt, "mechanical closure facts") or {}
    required = [
        "fixed_miners_complete", "meta_critics_complete", "mechanical_coverage_complete",
        "backlog_empty", "unresolved_empty", "taxonomy_clear",
        "prior_cp2_direct_blind", "no_new_genome",
    ]
    normalized = {key: bool(facts.get(key)) for key in required}
    blockers = [f"mechanical fact is false: {key}" for key, value in normalized.items() if not value]
    return {
        "auditor_id": f"CLOSURE-{tag}",
        "supports_dry_wave": not blockers,
        "verified_facts": normalized,
        "blockers": blockers,
        "reason": (
            "Dry-wave support follows the supplied persisted mechanical facts; the mock does not "
            "substitute an architecture-quality judgment for production evidence."),
    }


def answer(prompt):
    role_match = re.search(r"^ROLE:\s*(.+)$", prompt, re.M)
    role = role_match.group(1).strip() if role_match else "unknown"
    if role == "architecture-search-independent" and base.context_text(prompt, "targeted obligations"):
        return targeted_lineage(prompt)
    if role == "architecture-search-independent" and re.search(
            r"lineage\s+G96/ontology-and-taxonomy-challenge", prompt):
        return ontology_lineage(prompt)
    if role.startswith("novelty-meta-search-critic-"):
        return meta_critic(prompt, role.rsplit("-", 1)[-1])
    if role.startswith("taxonomy-adjudicator-"):
        return taxonomy_adjudicator(prompt)
    if role.startswith("novelty-closure-auditor-"):
        return closure_auditor(prompt, role.rsplit("-", 1)[-1])
    return ORIGINAL_ANSWER(prompt)


base.answer = answer


if __name__ == "__main__":
    base.main()
