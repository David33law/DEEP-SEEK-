#!/usr/bin/env python3
"""Hardening layer for the authoritative protocol-v5 zero-cost E2E proof.

Forces the production container backend, verifies unbounded real-provider search and stagnation
escalation, streaming formal crowns, source-bound and cross-auditor-independent genome evidence, and
the foundational deterministic supremacy dossier including CP1 identity, CP2 quarantine, signed log,
budget and owner-gate subject hashes. It never contacts the real DeepSeek endpoint.
"""
from __future__ import annotations

import glob
import json
import os

import prove_complete_observatory_protocol as base

GENOME_CONDITIONS = {
    "genome_realization_proven",
    "genome_realization_replication_passed",
    "genome_realization_crown_passed",
}
DOSSIER_CONDITION = "supremacy_dossier_verified"
DOSSIER_CLAIM = (
    "EVIDENCE_SUPPORTED_SUPREMACY_WITHIN_SIGNED_PROTOCOL_AND_TESTED_BOUNDS")
base.EXPECTED_NEW_CONDITIONS.update(GENOME_CONDITIONS | {DOSSIER_CONDITION})
base.REQUIRED_PROTOCOL_FILES.update({
    "profiles/national-observatory/GENOME-REALIZATION-CONTRACT.md",
    "profiles/national-observatory/SUPREMACY-CONTRACT.md",
    "private-evaluator/evaluator/observatory_formal_arena_v3.py",
    "executable-orchestrator/orchestrator.py",
    "executable-orchestrator/lawmax21/observatory_launcher.py",
    "executable-orchestrator/lawmax21/observatory_build_schema_hardening.py",
    "executable-orchestrator/lawmax21/observatory_semantic_evidence_binding_hardening.py",
    "executable-orchestrator/lawmax21/observatory_formal_streaming_routing.py",
    "executable-orchestrator/lawmax21/observatory_genome_realization_overlay.py",
    "executable-orchestrator/lawmax21/observatory_genome_auditor_diversity_hardening.py",
    "executable-orchestrator/lawmax21/observatory_genome_evidence_binding_hardening.py",
    "executable-orchestrator/lawmax21/observatory_genome_cross_auditor_hardening.py",
    "executable-orchestrator/lawmax21/observatory_supremacy_dossier_hardening.py",
    "executable-orchestrator/lawmax21/observatory_supremacy_dossier_overlay.py",
    "executable-orchestrator/lawmax21/observatory_setup_v4.py",
    "executable-orchestrator/lawmax21/observatory_preflight_v5.py",
    "executable-orchestrator/tools/mock_observatory_protocol_server.py",
    "executable-orchestrator/tools/mock_observatory_genome_server.py",
    "executable-orchestrator/tools/prove_observatory_protocol_static_v3.py",
    "executable-orchestrator/tools/prove_complete_observatory_protocol_v3.py",
})

_original_py = base.py
_original_verify = base.verify_protocol


def _container_py(path, *args, cwd=None, env=None, timeout=28800):
    values = list(args)
    if os.path.basename(path) == "run_observatory.py" and "--backend" in values:
        index = values.index("--backend")
        if index + 1 >= len(values):
            raise RuntimeError("proof runner has malformed --backend argument")
        values[index + 1] = "container"
    return _original_py(path, *values, cwd=cwd, env=env, timeout=timeout)


def _read(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _verify_genome_report(path, label, incumbent):
    if not os.path.isfile(path):
        raise RuntimeError(f"{label}: genome-realization report missing: {path}")
    report = _read(path)
    if report.get("status") != "PASS" or report.get("passed") is not True \
            or report.get("consensus") is not True \
            or report.get("all_axes_realized") is not True \
            or report.get("candidate_id") != incumbent:
        raise RuntimeError(f"{label}: genome-realization report did not pass")
    if report.get("auditor_citation_maps_independent") is not True \
            or int(report.get("auditor_citation_map_differing_count", 0)) < 4:
        raise RuntimeError(f"{label}: genome citation maps are not independent")
    auditors = report.get("auditors") or []
    if len(auditors) != 2 \
            or len({row.get("auditor_id") for row in auditors}) != 2 \
            or len({row.get("logical_id") for row in auditors}) != 2 \
            or len({row.get("report_sha256") for row in auditors}) != 2:
        raise RuntimeError(f"{label}: genome auditors are not independent")
    for auditor in auditors:
        axes = auditor.get("validated_axes") or []
        if len(axes) != 13:
            raise RuntimeError(f"{label}: auditor did not validate thirteen axes")
        for axis in axes:
            diversity = axis.get("auditor_definition_diversity") or {}
            if axis.get("source_bound_evidence") is not True \
                    or not axis.get("verified_symbols") \
                    or not axis.get("verified_invariant_ids") \
                    or not axis.get("verified_evidence"):
                raise RuntimeError(
                    f"{label}/{axis.get('axis')}: executable proof is incomplete")
            if int(diversity.get("unique_definition_citations", 0)) < 8 \
                    or int(diversity.get("maximum_axes_per_definition", 99)) > 4:
                raise RuntimeError(
                    f"{label}/{axis.get('axis')}: definition map is too generic")
    return report


def _evidence_map(runtime, dossier):
    rows = dossier.get("evidence_index") or []
    if len(rows) < 30:
        raise RuntimeError("supremacy dossier evidence index is unexpectedly small")
    result = {}
    runtime_root = os.path.abspath(runtime)
    for row in rows:
        relative, digest = row.get("path"), row.get("sha256")
        if not isinstance(relative, str) or not relative or relative in result:
            raise RuntimeError("dossier contains missing or duplicate evidence path")
        absolute = os.path.abspath(os.path.join(
            runtime, *relative.replace("\\", "/").split("/")))
        if absolute != runtime_root and not absolute.startswith(runtime_root + os.sep):
            raise RuntimeError("dossier evidence escapes runtime: " + relative)
        if not os.path.isfile(absolute) or base.sha256_file(absolute) != digest:
            raise RuntimeError("dossier evidence hash mismatch: " + relative)
        result[relative] = row
    return result


def _verify_gate_binding(runtime, evidence, gate, subject_relative, binding):
    subject_path = os.path.join(
        runtime, *subject_relative.replace("\\", "/").split("/"))
    subject_sha = base.sha256_file(subject_path)
    approval_relative = f"gates/{gate}.approval.json"
    if subject_relative not in evidence or approval_relative not in evidence:
        raise RuntimeError(gate + ": dossier omits subject or approval evidence")
    if evidence[subject_relative]["sha256"] != subject_sha:
        raise RuntimeError(gate + ": indexed subject hash drift")
    approval_path = os.path.join(runtime, *approval_relative.split("/"))
    approval = _read(approval_path)
    payload = approval.get("payload") or {}
    if payload.get("gate") != gate \
            or payload.get("decision") != "APPROVE" \
            or payload.get("subject_sha256") != subject_sha:
        raise RuntimeError(gate + ": persisted approval payload is not subject-bound")
    if binding.get("approval_path") != approval_relative \
            or binding.get("subject_sha256") != subject_sha \
            or binding.get("decision") != "APPROVE":
        raise RuntimeError(gate + ": dossier foundation binding disagrees with approval")


def _verify_dossier(repo, runtime, audit, incumbent, conditions, supremacy,
                    mission, source_head):
    path = os.path.join(runtime, "architecture", "OMEGA-SUPREMACY-DOSSIER.json")
    if not os.path.isfile(path):
        raise RuntimeError("deterministic supremacy dossier is missing")
    dossier = _read(path)
    if dossier.get("status") != "PASS" or dossier.get("verified") is not True \
            or dossier.get("claim_level") != DOSSIER_CLAIM \
            or dossier.get("candidate_id") != incumbent \
            or dossier.get("third_party_endorsement_claimed") is not False:
        raise RuntimeError("deterministic supremacy dossier identity/claim failed")
    if len(dossier.get("falsifiers") or []) < 3:
        raise RuntimeError("supremacy dossier is not sufficiently falsifiable")
    evidence = _evidence_map(runtime, dossier)

    protocol = dossier.get("protocol") or {}
    decisions_path = os.path.join(repo, "OWNER-DECISIONS.signed.json")
    if protocol.get("version") != mission.get("protocol_version") \
            or protocol.get("bundle_sha256") != mission.get(
                "research_protocol_bundle_sha256") \
            or protocol.get("runner_head") != source_head \
            or protocol.get("runner_tree") != mission.get("runner_tree") \
            or protocol.get("signed_decisions_sha256") != base.sha256_file(decisions_path):
        raise RuntimeError("supremacy dossier protocol/decision identity mismatch")

    foundation = dossier.get("foundation") or {}
    for key in (
            "protocol_preflight_ok",
            "cp1_reused_without_repository_archaeology_calls",
            "prior_cp2_quarantined_until_independent_frontier",
            "hidden_bank_committed",
            "signed_event_log_verified",
            "provider_budget_within_owner_ceiling"):
        if foundation.get(key) is not True:
            raise RuntimeError("supremacy dossier foundation is false: " + key)
    if int(foundation.get("signed_event_log_events_before_audit", 0)) < 10:
        raise RuntimeError("dossier signed event-log evidence is implausibly small")
    if int(foundation.get("provider_ledger_entries", 0)) < 1:
        raise RuntimeError("dossier provider ledger has no settled local calls")
    bindings = foundation.get("owner_gate_subject_bindings") or {}
    _verify_gate_binding(
        runtime, evidence, "GATE-ARCH-V0", "gates/v0_subject.json",
        bindings.get("GATE-ARCH-V0") or {})
    _verify_gate_binding(
        runtime, evidence, "GATE-ARCH-V1", "gates/v1_subject.json",
        bindings.get("GATE-ARCH-V1") or {})
    _verify_gate_binding(
        runtime, evidence, "GATE-MIGRATION", "architecture/migration_plan.json",
        bindings.get("GATE-MIGRATION") or {})

    search = dossier.get("search_closure") or {}
    original = search.get("conditions") or {}
    if DOSSIER_CONDITION in original \
            or not original \
            or any(value is not True for value in original.values()):
        raise RuntimeError("dossier did not reproduce pre-dossier closure")
    if conditions.get(DOSSIER_CONDITION) is not True \
            or supremacy.get(DOSSIER_CONDITION) is not True:
        raise RuntimeError("terminal proof does not carry dossier condition")

    receipt = (audit.get("campaigns") or {}).get("supremacy_dossier") or {}
    expected_receipt = {
        "verified": True,
        "path": "architecture/OMEGA-SUPREMACY-DOSSIER.json",
        "sha256": base.sha256_file(path),
        "claim_level": DOSSIER_CLAIM,
        "candidate_id": incumbent,
    }
    if receipt != expected_receipt or audit.get("supremacy_dossier") != receipt:
        raise RuntimeError("independent audit does not exactly bind the dossier")
    return dossier


def _verify(repo, runtime, source_head, preflight, launch):
    verified = _original_verify(repo, runtime, source_head, preflight, launch)
    if (preflight.get("container_backend") or {}).get("backend") != "container":
        raise RuntimeError("full E2E did not exercise production container isolation")

    mission = preflight.get("signed_mission") or {}
    if mission.get("protocol_version") != "OBSERVATORY-OMEGA-RESEARCH-PROTOCOL-5":
        raise RuntimeError("E2E is not bound to protocol v5")
    for flag in (
            "executable_genome_realization_required",
            "strict_executable_source_schema_required",
            "bounded_candidate_output_required",
            "terminal_negative_proof_required",
            "unbounded_production_rounds_required",
            "stagnation_escalates_search_required",
            "deterministic_supremacy_dossier_required"):
        if mission.get(flag) is not True:
            raise RuntimeError("signed mission flag missing: " + flag)
    if mission.get("production_max_rounds") != 0 \
            or mission.get("stagnation_response") != \
            "continue-successor-radical-novelty-meta-search":
        raise RuntimeError("signed production search policy is satisficeable")
    round_policy = preflight.get("round_policy") or {}
    if round_policy.get("max_rounds") != 0 \
            or round_policy.get("unbounded") is not True \
            or round_policy.get("finite_cap_allowed_for_real_provider") is not False:
        raise RuntimeError("preflight did not prove unbounded production rounds")

    mission_files = set(mission.get("research_protocol_files") or [])
    missing = sorted(base.REQUIRED_PROTOCOL_FILES - mission_files)
    if missing:
        raise RuntimeError("signed protocol omitted final routes: " + ", ".join(missing))

    incumbent = verified["incumbent"]
    formal_paths = glob.glob(os.path.join(
        runtime, "reports", f"formal-crown-{incumbent}-*.json"))
    if len(formal_paths) != 2 or any(
            _read(path).get("behavioral_digest_mode") !=
            "ordered-length-delimited-stream-v1" for path in formal_paths):
        raise RuntimeError("streaming formal crown evidence is incomplete")

    architecture = os.path.join(runtime, "architecture")
    genome_reports = {
        label: _verify_genome_report(os.path.join(
            architecture, f"genome-realization-{label}-{incumbent}.json"),
            label, incumbent)
        for label in ("qualification", "replication", "crown")}

    summary = verified["summary"]
    conditions = (summary.get("escalation") or {}).get("conditions") or {}
    supremacy = (summary.get("escalation") or {}).get("supremacy") or {}
    for condition in GENOME_CONDITIONS | {DOSSIER_CONDITION}:
        if conditions.get(condition) is not True \
                or supremacy.get(condition) is not True:
            raise RuntimeError("terminal proof lacks: " + condition)

    audit = verified["audit"]
    campaign = (audit.get("campaigns") or {}).get(
        "controlled_genome_realization") or {}
    if audit.get("proof_mode") is not True \
            or (audit.get("workload_policy") or {}).get("proof_mode") is not True \
            or campaign.get("qualification") is not True \
            or campaign.get("replication") is not True \
            or campaign.get("crown") is not True \
            or campaign.get("auditors") != 2 \
            or campaign.get("axes") != 13:
        raise RuntimeError("independent audit did not reproduce genome closure")

    dossier = _verify_dossier(
        repo, runtime, audit, incumbent, conditions, supremacy,
        mission, source_head)
    verified.update({
        "exact_candidate_backend": "container",
        "unbounded_production_round_policy_verified": True,
        "stagnation_escalation_policy_verified": True,
        "streaming_formal_crown_verified": True,
        "supremacy_dossier_verified": {
            "path": "architecture/OMEGA-SUPREMACY-DOSSIER.json",
            "sha256": base.sha256_file(os.path.join(
                architecture, "OMEGA-SUPREMACY-DOSSIER.json")),
            "claim_level": dossier["claim_level"],
            "evidence_items": len(dossier.get("evidence_index") or []),
            "falsifiers": len(dossier.get("falsifiers") or []),
            "foundation_verified": True,
        },
        "genome_realization_verified": {
            label: {
                "genome_sha256": report.get("genome_sha256"),
                "contract_sha256": report.get("contract_sha256"),
                "auditors": 2, "axes_per_auditor": 13,
                "source_bound": True, "definition_diversity": True,
                "cross_auditor_citation_map_independence": True,
                "differing_axis_maps": report.get(
                    "auditor_citation_map_differing_count"),
            } for label, report in genome_reports.items()},
    })
    return verified


base.py = _container_py
base.verify_protocol = _verify
main = base.main
sha256_file = base.sha256_file

__all__ = ["main", "sha256_file"]


if __name__ == "__main__":
    import sys
    sys.exit(main())
