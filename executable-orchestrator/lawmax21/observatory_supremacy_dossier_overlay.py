"""Deterministic final supremacy dossier for the National Legal Observatory.

The model-assisted public case is useful prose but cannot be the authority for its own citations.
This overlay runs after every semantic, systems, distributed, scale, formal, interoperability,
cross-model, prior-art, novelty and genome-realization campaign. At INDEPENDENT_AUDIT it rebuilds a
machine-checkable dossier from persisted runtime bytes, hashes every load-bearing artifact, enumerates
the complete measured frontier and records explicit falsifiers and proof boundaries. The independent
audit is then rewritten to include the dossier hash before its signed state-machine transition.
"""
from __future__ import annotations

import glob
import json
import os
from types import MethodType

from . import observatory_escalation as escalation
from . import observatory_protocol
from .canonical import atomic_write_json, read_json, sha256_file, utc
from .handlers import A

SUPREMACY_KEY = "supremacy_dossier_verified"
CLAIM_LEVEL = "EVIDENCE_SUPPORTED_SUPREMACY_WITHIN_SIGNED_PROTOCOL_AND_TESTED_BOUNDS"


def _runtime_path(ctx, relative):
    path = os.path.abspath(os.path.join(
        ctx.runtime, *str(relative).replace("\\", "/").split("/")))
    runtime = os.path.abspath(ctx.runtime)
    if path != runtime and not path.startswith(runtime + os.sep):
        raise RuntimeError("supremacy dossier evidence escapes runtime: " + str(relative))
    return path


def _evidence(ctx, path, *, require_pass=False, label=None):
    path = os.path.abspath(path)
    runtime = os.path.abspath(ctx.runtime)
    if path != runtime and not path.startswith(runtime + os.sep):
        raise RuntimeError("supremacy dossier path escapes runtime: " + path)
    if not os.path.isfile(path):
        raise RuntimeError("supremacy dossier evidence missing: " + path)
    relative = os.path.relpath(path, ctx.runtime).replace("\\", "/")
    row = {"label": label or os.path.basename(path),
           "path": relative, "sha256": sha256_file(path),
           "bytes": os.path.getsize(path)}
    try:
        parsed = read_json(path)
    except Exception:
        parsed = None
    if isinstance(parsed, dict):
        row["status"] = parsed.get("status")
        row["passed"] = parsed.get("passed")
        row["candidate_id"] = parsed.get("candidate_id")
    if require_pass:
        if not isinstance(parsed, dict):
            raise RuntimeError(relative + ": passing JSON evidence required")
        if parsed.get("status") not in ("PASS", "OK") \
                or parsed.get("passed", True) is not True:
            raise RuntimeError(relative + ": evidence is not passing")
    return row, parsed


def _latest(paths, expression):
    import re
    rows = []
    pattern = re.compile(expression)
    for path in paths:
        match = pattern.search(os.path.basename(path))
        if match:
            rows.append((int(match.group(1)), path))
    return [path for _number, path in sorted(rows)]


def _required_crown_evidence(ctx, incumbent):
    reports = A(ctx, "reports", "x")[:-1]
    architecture = A(ctx, "architecture", "x")[:-1]
    evidence = []
    parsed = {}

    def add(path, key, require_pass=True):
        row, obj = _evidence(ctx, path, require_pass=require_pass, label=key)
        evidence.append(row); parsed[key] = obj

    add(A(ctx, "reports", f"systems-crown-{incumbent}.json"), "durable_crown")
    add(A(ctx, "reports", f"distributed-crown-{incumbent}.json"), "distributed_crown")
    add(A(ctx, "reports", f"scale-crown-{incumbent}.json"), "scale_crown")
    add(A(ctx, "reports", f"cross-model-crown-{incumbent}.json"), "cross_model_crown")
    add(A(ctx, "architecture", f"genome-realization-crown-{incumbent}.json"),
        "genome_realization_crown")

    formal = sorted(glob.glob(os.path.join(
        reports, f"formal-crown-{incumbent}-*.json")))
    interoperability = sorted(glob.glob(os.path.join(
        reports, f"interoperability-crown-{incumbent}-*.json")))
    if len(formal) != 2 or len(interoperability) != 2:
        raise RuntimeError("supremacy dossier requires two formal and two interoperability crowns")
    for index, path in enumerate(formal, 1):
        add(path, f"formal_crown_{index}")
    for index, path in enumerate(interoperability, 1):
        add(path, f"interoperability_crown_{index}")

    formal_digests = {
        parsed[f"formal_crown_{index}"].get("behavioral_digest")
        for index in (1, 2)}
    interop_digests = {
        parsed[f"interoperability_crown_{index}"].get("semantic_digest")
        for index in (1, 2)}
    if len(formal_digests) != 1 or None in formal_digests:
        raise RuntimeError("supremacy dossier: formal crowns disagree")
    if len(interop_digests) != 1 or None in interop_digests:
        raise RuntimeError("supremacy dossier: interoperability crowns disagree")
    genome = parsed["genome_realization_crown"]
    if genome.get("consensus") is not True \
            or genome.get("all_axes_realized") is not True \
            or genome.get("auditor_citation_maps_independent") is not True:
        raise RuntimeError("supremacy dossier: executable genome crown is incomplete")
    return evidence, parsed


def _search_evidence(ctx):
    architecture = A(ctx, "architecture", "x")[:-1]
    candidates = A(ctx, "candidates", "x")[:-1]
    frontier = A(ctx, "frontier", "x")[:-1]
    evidence = []

    def add(path, label):
        row, obj = _evidence(ctx, path, label=label)
        evidence.append(row)
        return obj

    forest = add(A(ctx, "architecture", "search_forest.json"), "search_forest")
    proposals = add(A(ctx, "architecture", "proposals.json"), "complete_proposals")
    built = add(A(ctx, "candidates", "built.json"), "built_candidates")
    implementation = add(A(ctx, "candidates", "implementation-search.json"),
                         "implementation_search")
    holdout = add(A(ctx, "reports", "final_holdout.json"), "final_holdout")
    hesa = add(A(ctx, "frontier", "hesa_candidate.json"), "hesa_selection")
    lower = add(A(ctx, "architecture", "lower_bounds.json"), "lower_bounds")
    destroyers = add(A(ctx, "architecture", "final_destroyers.json"), "final_destroyers")
    public_case = add(A(ctx, "architecture", "SUPREMACY-CASE.json"),
                      "model_assisted_supremacy_case")
    migration = add(A(ctx, "architecture", "migration_plan.json"), "migration_plan")

    prior_paths = _latest(glob.glob(os.path.join(
        architecture, "prior-art-round*.json")), r"round(\d+)")
    if not prior_paths:
        raise RuntimeError("supremacy dossier: prior-art campaign missing")
    prior = add(prior_paths[-1], "authoritative_prior_art_closure")

    novelty_paths = _latest(glob.glob(os.path.join(
        architecture, "novelty-wave-r*.json")), r"r(\d+)")
    meta_paths = _latest(glob.glob(os.path.join(
        architecture, "meta-search-wave-r*.json")), r"r(\d+)")
    if len(novelty_paths) < 3 or len(meta_paths) < 3:
        raise RuntimeError("supremacy dossier: three final novelty/meta waves required")
    final_novelty = []
    final_meta = []
    for index, path in enumerate(novelty_paths[-3:], 1):
        obj = add(path, f"final_dry_novelty_wave_{index}")
        ledger = obj.get("ledger_wave") or {}
        if ledger.get("dry") is not True \
                or ledger.get("methods_complete") is not True \
                or ledger.get("backlog_count") != 0 \
                or ledger.get("unresolved_count") != 0:
            raise RuntimeError("supremacy dossier: final novelty wave is not dry")
        final_novelty.append(obj)
    for index, path in enumerate(meta_paths[-3:], 1):
        obj = add(path, f"final_meta_search_wave_{index}")
        if len(obj.get("meta_critics") or []) != 2 \
                or len(obj.get("closure_auditors") or []) != 2 \
                or (obj.get("coverage_after") or {}).get("complete") is not True:
            raise RuntimeError("supremacy dossier: final meta-search wave is incomplete")
        final_meta.append(obj)

    if (forest.get("summary") or {}).get("prior_cp2_visible") is not False \
            or proposals.get("prior_cp2_visible") is not False:
        raise RuntimeError("supremacy dossier: independent search was CP2-contaminated")
    if len(proposals.get("proposals") or []) < 12:
        raise RuntimeError("supremacy dossier: fewer than twelve structural finalists")
    if built.get("complete_blueprint_handoff") is not True \
            or built.get("formalization_handoff") is not True:
        raise RuntimeError("supremacy dossier: blueprint/formalization handoff failed")
    if lower.get("closed") is not True:
        raise RuntimeError("supremacy dossier: lower-bound campaign remains open")
    if destroyers.get("survived") is not True:
        raise RuntimeError("supremacy dossier: finalist did not survive destroyers")
    if public_case.get("mechanically_supported") is not True \
            or public_case.get("third_party_endorsement_claimed") is not False:
        raise RuntimeError("supremacy dossier: public case is unsupported")
    if prior.get("all_sources_assessed") is not True \
            or prior.get("challengers_measured") is not True \
            or prior.get("no_blockers") is not True:
        raise RuntimeError("supremacy dossier: prior-art closure is incomplete")
    return evidence, {
        "forest": forest, "proposals": proposals, "built": built,
        "implementation": implementation, "holdout": holdout,
        "hesa": hesa, "lower": lower, "destroyers": destroyers,
        "public_case": public_case, "migration": migration,
        "prior_art": prior, "final_novelty": final_novelty,
        "final_meta": final_meta,
    }


def _owner_gate_evidence(ctx):
    evidence = []
    for gate in ("GATE-ARCH-V0", "GATE-ARCH-V1", "GATE-MIGRATION"):
        path = A(ctx, "gates", f"{gate}.approval.json")
        row, _obj = _evidence(ctx, path, label=gate + "_approval")
        evidence.append(row)
    return evidence


def _alternatives(ctx, incumbent):
    rows = []
    for candidate_id, member in sorted(ctx.frontier.report().items()):
        rows.append({
            "candidate_id": candidate_id,
            "is_incumbent": candidate_id == incumbent,
            "status": member.get("status"),
            "reason": member.get("reason"),
            "mechanism": member.get("mechanism"),
            "declared_altitude": member.get("declared_altitude"),
            "dimension_vector": member.get("dimension_vector"),
            "evidence_refs": member.get("evidence_refs"),
        })
    if len(rows) < 2:
        raise RuntimeError("supremacy dossier requires at least two measured architectures")
    if sum(1 for row in rows if row["is_incumbent"]) != 1:
        raise RuntimeError("supremacy dossier incumbent is absent or duplicated")
    return rows


def _build_dossier(ctx, original_conditions):
    incumbent = ctx.esc.s.get("incumbent")
    if not incumbent or incumbent not in ctx.candidates:
        raise RuntimeError("supremacy dossier has no incumbent candidate")
    prerequisites = original_conditions()
    unmet = sorted(key for key, value in prerequisites.items() if value is not True)
    if unmet:
        raise RuntimeError(
            "supremacy dossier prerequisites are incomplete: " + ", ".join(unmet))
    if not ctx.esc.axioms_upheld():
        raise RuntimeError("supremacy dossier: target axiom violation remains")
    if ctx.esc.untried_families():
        raise RuntimeError("supremacy dossier: untried families remain")

    crown_evidence, crowns = _required_crown_evidence(ctx, incumbent)
    search_evidence, search = _search_evidence(ctx)
    gate_evidence = _owner_gate_evidence(ctx)
    decisions_path = os.path.join(ctx.root, "OWNER-DECISIONS.signed.json")
    mission = ctx.decisions.d.get("D09_ROW0_TARGET") or {}
    if mission.get("protocol_version") != observatory_protocol.PROTOCOL_VERSION:
        raise RuntimeError("supremacy dossier: signed mission protocol mismatch")
    if mission.get("research_protocol_bundle_sha256") != \
            observatory_protocol.protocol_bundle_sha256(ctx.root):
        raise RuntimeError("supremacy dossier: signed protocol bundle drift")

    candidate = ctx.candidates[incumbent]
    public_case = search["public_case"]
    falsifiers = list(public_case.get("falsifiers") or [])
    if len(falsifiers) < 3:
        raise RuntimeError("supremacy dossier requires at least three falsifiers")
    fixed_limitations = [
        "The claim is relative to the owner-signed protocol, public prior-art manifest, controlled genome taxonomy, hidden evaluator corpora and exact bounded workloads; a new constructible family or stronger counterexample reopens the tournament.",
        "Bounded formal exploration is not an unbounded theorem about every future implementation or deployment.",
        "Local container scale and distributed campaigns do not claim an untested geographical production topology.",
        "No endorsement by Elon Musk, xAI, SpaceX, standards bodies or source authors is asserted.",
    ]
    dossier = {
        "status": "PASS",
        "verified": True,
        "claim_level": CLAIM_LEVEL,
        "candidate_id": incumbent,
        "generated_utc": utc(),
        "protocol": {
            "version": observatory_protocol.PROTOCOL_VERSION,
            "bundle_sha256": mission["research_protocol_bundle_sha256"],
            "runner_head": mission.get("runner_head"),
            "runner_tree": mission.get("runner_tree"),
            "signed_decisions_sha256": sha256_file(decisions_path),
            "target": mission.get("target"),
        },
        "architecture_identity": {
            "family": candidate.get("family"),
            "mechanism": candidate.get("mechanism"),
            "genome_sha256": candidate.get("genome_sha256"),
            "blueprint_sha256": candidate.get("blueprint_sha256"),
            "formalization_sha256": candidate.get("formalization_sha256"),
            "semantic_source_sha256": __import__("hashlib").sha256(
                candidate["source"].encode("utf-8")).hexdigest(),
        },
        "selection_explanation": {
            "architecture_thesis": public_case.get("architecture_thesis"),
            "why_first_principles_frontier_team_would_choose":
                public_case.get("why_frontier_team_would_choose"),
            "load_bearing_mechanisms": public_case.get("load_bearing_mechanisms"),
            "destroyed_families_model_summary": public_case.get("destroyed_families"),
            "model_assisted_only": True,
            "mechanical_authority": "evidence_index + measured_frontier + terminal_conditions",
        },
        "measured_frontier": _alternatives(ctx, incumbent),
        "search_closure": {
            "conditions": prerequisites,
            "supremacy_summary_before_dossier": ctx.esc.supremacy_summary(),
            "search_forest_summary": search["forest"].get("summary"),
            "structural_finalists": len(search["proposals"].get("proposals") or []),
            "prior_art_sources": search["prior_art"].get("source_count"),
            "final_dry_novelty_waves": 3,
            "final_meta_search_waves": 3,
            "untried_families": [],
            "axioms_upheld": True,
        },
        "crown_summary": {
            "durable": crowns["durable_crown"].get("status"),
            "distributed": crowns["distributed_crown"].get("status"),
            "scale": crowns["scale_crown"].get("status"),
            "formal_behavioral_digest": crowns["formal_crown_1"].get("behavioral_digest"),
            "interoperability_semantic_digest": crowns["interoperability_crown_1"].get("semantic_digest"),
            "cross_model": crowns["cross_model_crown"].get("status"),
            "genome_realization": crowns["genome_realization_crown"].get("status"),
        },
        "evidence_index": search_evidence + crown_evidence + gate_evidence,
        "falsifiers": falsifiers,
        "limitations": list(dict.fromkeys(
            list(public_case.get("limitations") or []) + fixed_limitations)),
        "third_party_endorsement_claimed": False,
    }
    if any(not row.get("sha256") for row in dossier["evidence_index"]):
        raise RuntimeError("supremacy dossier contains unhashed evidence")
    path = A(ctx, "architecture", "OMEGA-SUPREMACY-DOSSIER.json")
    atomic_write_json(path, dossier)
    return path, dossier


def install(ctx, handlers):
    if getattr(ctx.esc, "_supremacy_dossier_installed", False):
        return dict(handlers)
    out = dict(handlers)
    original_conditions = ctx.esc._supremacy_conditions
    original_summary = ctx.esc.supremacy_summary

    def conditions(self):
        result = original_conditions()
        dossier = self._sup().setdefault("final_dossier", {})
        result[SUPREMACY_KEY] = bool(dossier.get("verified"))
        return result

    def summary(self):
        result = original_summary()
        dossier = self._sup().setdefault("final_dossier", {})
        result[SUPREMACY_KEY] = bool(dossier.get("verified"))
        result["supremacy_dossier_path"] = dossier.get("path")
        result["supremacy_dossier_sha256"] = dossier.get("sha256")
        result["supremacy_dossier_claim_level"] = dossier.get("claim_level")
        return result

    ctx.esc._supremacy_conditions = MethodType(conditions, ctx.esc)
    ctx.esc.supremacy_summary = MethodType(summary, ctx.esc)
    ctx.esc._supremacy_dossier_installed = True
    if SUPREMACY_KEY not in escalation.SUPREMACY_KEYS:
        escalation.SUPREMACY_KEYS.append(SUPREMACY_KEY)
    schema = escalation.OBSERVATORY_PROOF_SCHEMA
    for seat in (schema["properties"]["conditions"],
                 schema["properties"]["supremacy"]):
        if SUPREMACY_KEY not in seat["required"]:
            seat["required"].append(SUPREMACY_KEY)
        seat["properties"][SUPREMACY_KEY] = {"type": "boolean"}

    original_audit = out["INDEPENDENT_AUDIT"]

    def independent_audit(machine):
        audit_path = original_audit(machine)
        audit = read_json(audit_path)
        dossier_path, dossier = _build_dossier(ctx, original_conditions)
        relative = os.path.relpath(dossier_path, ctx.runtime).replace("\\", "/")
        receipt = {
            "verified": True,
            "path": relative,
            "sha256": sha256_file(dossier_path),
            "claim_level": dossier["claim_level"],
            "candidate_id": dossier["candidate_id"],
        }
        ctx.esc._sup()["final_dossier"] = dict(receipt)
        ctx.esc._flush()
        conditions_now = ctx.esc._supremacy_conditions()
        summary_now = ctx.esc.supremacy_summary()
        audit["supremacy_conditions"] = conditions_now
        audit["unmet_supremacy_conditions"] = sorted(
            key for key, value in conditions_now.items() if value is not True)
        audit["supremacy_summary"] = summary_now
        audit.setdefault("campaigns", {})["supremacy_dossier"] = receipt
        audit["supremacy_dossier"] = receipt
        atomic_write_json(audit_path, audit)
        return audit_path

    out["INDEPENDENT_AUDIT"] = independent_audit
    return out
