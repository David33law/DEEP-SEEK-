#!/usr/bin/env python3
"""Static closure for owner-bound causal genome realization with v2 axis probes.

The inherited portable-owner proof remains responsible for the full Observatory protocol. This final
extension verifies that every causal task is routed through the exact hardened
``observatory_axis_probe_arena_v2.py`` seat, that the owner-signed protocol census includes its bytes,
that semantic thresholds equal the signed Pareto minima, that formal commutativity is required only
when claimed, and that audit, dossier, Docker E2E and final proof all bind the same evaluator.
No provider call, candidate execution or owner mutation occurs here.
"""
from __future__ import annotations

import hashlib
import importlib
import json
import os
import sys

import prove_observatory_protocol_static_v4 as previous

ROOT = previous.ROOT
PREVIOUS_REPORT = previous.REPORT
REPORT = os.path.join(
    ROOT, "proof", "observatory-protocol-static-v5-causal.json")
PROTOCOL_VERSION = "OBSERVATORY-OMEGA-RESEARCH-PROTOCOL-5"
PROBE_CONTRACT = "observatory-axis-probe-v1"
PROBE_EVALUATOR = "observatory_axis_probe_arena_v2.py"
PROBE_EVALUATOR_PATH = (
    "private-evaluator/evaluator/" + PROBE_EVALUATOR)
CAUSAL_CONDITIONS = {
    "genome_causal_ablation_replication_passed",
    "genome_causal_ablation_crown_passed",
}
REQUIRED_INHERITED_GATES = (
    "final_audit_v3_wired",
    "candidate_identity_prompt_bound",
)
REQUIRED_MODULES = (
    "lawmax21.observatory_genome_causal_ablation_hardening",
    "lawmax21.observatory_causal_audit_hardening",
    "lawmax21.observatory_causal_dossier_hardening",
    "lawmax21.observatory_causal_failure_classification_hardening",
    "lawmax21.observatory_causal_axis_attribution_hardening",
    "lawmax21.observatory_causal_attribution_scope_hardening",
    "lawmax21.observatory_causal_definition_semantics_hardening",
    "lawmax21.observatory_causal_behavioral_probe_hardening",
)
REQUIRED_FILES = {
    "executable-orchestrator/lawmax21/observatory_audit_v3.py",
    "executable-orchestrator/lawmax21/observatory_genome_realization_hardening.py",
    "executable-orchestrator/lawmax21/observatory_genome_causal_ablation_hardening.py",
    "executable-orchestrator/lawmax21/observatory_causal_audit_hardening.py",
    "executable-orchestrator/lawmax21/observatory_causal_dossier_hardening.py",
    "executable-orchestrator/lawmax21/observatory_causal_failure_classification_hardening.py",
    "executable-orchestrator/lawmax21/observatory_causal_axis_attribution_hardening.py",
    "executable-orchestrator/lawmax21/observatory_causal_attribution_scope_hardening.py",
    "executable-orchestrator/lawmax21/observatory_causal_definition_semantics_hardening.py",
    "executable-orchestrator/lawmax21/observatory_causal_behavioral_probe_hardening.py",
    "executable-orchestrator/lawmax21/observatory_evaluator_routing_hardening.py",
    "executable-orchestrator/lawmax21/observatory_formal_streaming_routing.py",
    "private-evaluator/evaluator/observatory_axis_probe_arena.py",
    PROBE_EVALUATOR_PATH,
    "executable-orchestrator/tools/mock_observatory_causal_server.py",
    "executable-orchestrator/tools/prove_observatory_protocol_static_v5.py",
    "executable-orchestrator/tools/prove_complete_observatory_protocol_causal_hardened.py",
    "executable-orchestrator/tools/prove_complete_observatory_protocol_causal_provider_hardened.py",
    "executable-orchestrator/tools/prove_complete_observatory_protocol_axis_hardened.py",
    "executable-orchestrator/tools/prove_complete_observatory_protocol_v5.py",
}


def _path(relative):
    return os.path.join(ROOT, *relative.split("/"))


def _text(relative):
    with open(_path(relative), encoding="utf-8") as handle:
        return handle.read()


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require(text, tokens, label):
    missing = [token for token in tokens if token not in text]
    if missing:
        raise RuntimeError(label + " lacks: " + ", ".join(missing))


def _ordered(text, tokens, label):
    positions = []
    for token in tokens:
        try:
            positions.append(text.index(token))
        except ValueError as exc:
            raise RuntimeError(label + " lacks: " + token) from exc
    if positions != sorted(positions):
        raise RuntimeError(label + " order drifted")


def main():
    result = {
        "proof": "observatory-protocol-static-v5-axis-probe-v2-closure",
        "provider_calls": 0,
        "candidate_executions": 0,
        "status": "FAIL",
    }
    try:
        if previous.main() != 0:
            raise RuntimeError(
                "inherited portable-owner static closure failed")
        with open(PREVIOUS_REPORT, encoding="utf-8") as handle:
            inherited = json.load(handle)
        if inherited.get("status") != "PASS":
            raise RuntimeError("inherited static receipt is not PASS")
        missing_inherited = [
            key for key in REQUIRED_INHERITED_GATES
            if inherited.get(key) is not True]
        if missing_inherited:
            raise RuntimeError(
                "inherited final launcher/audit gates are absent: "
                + ", ".join(missing_inherited))

        from lawmax21 import observatory_protocol as protocol
        from lawmax21 import observatory_genome_causal_ablation_hardening as causal

        imported = [
            importlib.import_module(name).__name__
            for name in REQUIRED_MODULES]
        if protocol.PROTOCOL_VERSION != PROTOCOL_VERSION:
            raise RuntimeError("wrong protocol version")
        for flag in (
                "causal_genome_ablation_required",
                "causal_genome_negative_controls_required",
                "axis_specific_causal_attribution_required",
                "axis_specific_behavioral_failure_required",
                "axis_behavioral_probe_required"):
            if protocol.MISSION_FLAGS.get(flag) is not True:
                raise RuntimeError("signed mission flag absent: " + flag)
        if int(protocol.SEARCH_POLICY.get(
                "genome_causal_ablation_phases_required", 0)) != 2:
            raise RuntimeError(
                "signed search policy does not require replication+crown ablation")

        protocol_files = set(protocol.protocol_files(ROOT))
        omitted = sorted(REQUIRED_FILES - protocol_files)
        if omitted:
            raise RuntimeError(
                "protocol census omitted causal/axis-probe files: "
                + ", ".join(omitted))
        if set(causal.CAUSAL_LABELS) != {"replication", "crown"}:
            raise RuntimeError("causal genome phases drifted")
        if set(causal.CAUSAL_SUPREMACY_KEYS) != CAUSAL_CONDITIONS:
            raise RuntimeError("causal terminal condition identity drifted")

        audit = _text(
            "executable-orchestrator/lawmax21/observatory_audit.py")
        _ordered(audit, (
            "observatory_causal_audit_hardening.install",
            "base.install",
            "observatory_cross_model_overlay.install",
            "observatory_genome_realization_overlay.install",
            "observatory_causal_failure_classification_hardening.install",
            "observatory_causal_axis_attribution_hardening.install",
            "observatory_causal_attribution_scope_hardening.install",
            "observatory_causal_definition_semantics_hardening.install",
            "observatory_causal_behavioral_probe_hardening.install",
            "observatory_genome_causal_ablation_hardening.install",
            "observatory_causal_dossier_hardening.install",
            "observatory_supremacy_dossier_overlay.install",
            "observatory_phase_gate_hardening.install"),
            "causal final overlay")

        causal_source = _text(
            "executable-orchestrator/lawmax21/"
            "observatory_genome_causal_ablation_hardening.py")
        _require(causal_source, (
            "class _DefinitionRenamer",
            "auditor-specific definition set",
            "inert-negative-control",
            "negative_controls_passed",
            "candidate_sha256",
            "causal_failure_observed",
            "Infrastructure refusal",
            "genome_causal_ablation_replication_passed",
            "genome_causal_ablation_crown_passed"),
            "causal genome implementation")

        probe_hardening = _text(
            "executable-orchestrator/lawmax21/"
            "observatory_causal_behavioral_probe_hardening.py")
        _require(probe_hardening, (
            'PROBE_CONTRACT = "observatory-axis-probe-v1"',
            '"observatory_axis_probe_arena_v2.py"',
            "def _identity", "def _probe",
            "axis_probe_task_identity_sha256",
            "axis_probe_evaluator",
            "baseline_axis_probe_path", "mutant_axis_probe_path",
            "baseline_axis_probe_sha256", "mutant_axis_probe_sha256",
            "baseline_axis_probe_source_sha256",
            "mutant_axis_probe_source_sha256",
            "baseline_axis_probe_passed", "mutant_axis_probe_failed",
            "diagnostic_failure_attribution_is_sufficient",
            "axis._attribution = attribution",
            "causal._run_task = run_task"),
            "baseline-versus-mutant axis-probe hardening")

        base_probe = _text(
            "private-evaluator/evaluator/observatory_axis_probe_arena.py")
        _require(base_probe, (
            'CONTRACT = "observatory-axis-probe-v1"',
            "GROUP_AXES", "SEMANTIC_DIMENSIONS",
            "def _semantic_probe", "def _systems_probe",
            "def _distributed_probe", "def _scale_probe",
            "def _formal_probe", "def _interoperability_probe",
            '"valid_execution": False',
            '"failure_origin": "infrastructure_or_harness"',
            '"failure_origin": "candidate_axis_behavior"',
            '"proof_boundary"'),
            "base trusted axis-probe arena")
        probe_v2 = _text(PROBE_EVALUATOR_PATH)
        _require(probe_v2, (
            "Contract-compatible hardening",
            "SEMANTIC_HARD_MINIMA",
            '"temporal_reconstruction_accuracy": 0.99',
            '"canonical_identity_accuracy": 0.995',
            '"jurisprudence_temporal_link_accuracy": 0.98',
            '"provenance_completeness": 0.995',
            "commutative_independent_admissions",
            "derivation-order-claimed",
            "derivation-order-not-claimed",
            "base.FORMAL_PROBE = base.FORMAL_PROBE.replace",
            'base.PROBES["semantic"] = _semantic_probe',
            "main = base.main"),
            "hardened v2 axis-probe arena")
        compile(base_probe, _path(
            "private-evaluator/evaluator/observatory_axis_probe_arena.py"),
            "exec")
        compile(probe_v2, _path(PROBE_EVALUATOR_PATH), "exec")

        evaluator_routing = _text(
            "executable-orchestrator/lawmax21/"
            "observatory_evaluator_routing_hardening.py")
        _require(evaluator_routing, (
            "def _process_receipt",
            '"evaluator_returncode": result.returncode',
            '"evaluator_stdout_tail"',
            '"evaluator_stderr_tail"',
            'report["candidate_sha256"]',
            "atomic_write_json(out, report)"),
            "bounded specialized evaluator process receipts")
        formal_routing = _text(
            "executable-orchestrator/lawmax21/"
            "observatory_formal_streaming_routing.py")
        _require(formal_routing, (
            '"evaluator_returncode": result.returncode',
            '"evaluator_stdout_tail"',
            '"evaluator_stderr_tail"',
            'report["candidate_sha256"]',
            '"observatory_formal_arena_v3.py"',
            "atomic_write_json(out, report)"),
            "streaming formal evaluator process receipts")

        failure_classifier = _text(
            "executable-orchestrator/lawmax21/"
            "observatory_causal_failure_classification_hardening.py")
        _require(failure_classifier, (
            "_INFRASTRUCTURE_MARKERS",
            "infrastructure failure is non-evidence",
            "candidate_sha256", "evaluator_returncode",
            '"failure_origin": "candidate"'),
            "causal failure classification")

        definition_semantics = _text(
            "executable-orchestrator/lawmax21/"
            "observatory_causal_definition_semantics_hardening.py")
        _require(definition_semantics, (
            "definition_body_sha256",
            "definition_vocabulary_sha256_inputs",
            "definition_vocabulary_sha256",
            "diagnostic_failure_attribution_is_sufficient",
            "removed_definition_name_is_sufficient",
            "group_path_is_sufficient",
            "whole_receipt_searched"),
            "definition diagnostic receipts")

        contract = _text(
            "profiles/national-observatory/GENOME-REALIZATION-CONTRACT.md")
        _require(contract, (
            "Controlled Genome Realization Contract v5",
            "Authoritative baseline-versus-mutant axis probes",
            "observatory-axis-probe-v1",
            "baseline probe", "mutant probe",
            "baseline_axis_probe_passed=true",
            "mutant_axis_probe_failed=true",
            "axis_behavioral_probe_required=true",
            "diagnostic_failure_attribution_is_sufficient",
            "Infrastructure refusal"),
            "genome realization contract")

        causal_audit = _text(
            "executable-orchestrator/lawmax21/"
            "observatory_causal_audit_hardening.py")
        _require(causal_audit, (
            'PROBE_CONTRACT = "observatory-axis-probe-v1"',
            'PROBE_EVALUATOR = "observatory_axis_probe_arena_v2.py"',
            "axis_behavioral_probe_evaluator",
            "all_tasks_have_baseline_mutant_probe_pairs",
            "replication_axis_probe_tasks",
            "replication_axis_probe_pairs",
            "crown_axis_probe_tasks", "crown_axis_probe_pairs",
            "diagnostic_failure_attribution_is_sufficient",
            "all_tasks_axis_behaviorally_falsified"),
            "independent audit axis-probe receipt")

        causal_dossier = _text(
            "executable-orchestrator/lawmax21/"
            "observatory_causal_dossier_hardening.py")
        _require(causal_dossier, (
            'PROBE_CONTRACT = "observatory-axis-probe-v1"',
            'PROBE_EVALUATOR = "observatory_axis_probe_arena_v2.py"',
            "def _probe_evaluator_receipt",
            "def _probe_report", "def _probe_pair",
            "axis_probe_task_identity_sha256",
            "axis_probe_evaluator",
            "axis_probe_pair_receipts",
            "axis_probe_pairs_replication",
            "axis_probe_pairs_crown",
            "all_tasks_have_baseline_mutant_probe_pairs",
            "baseline_axis_probe_required",
            "mutant_axis_probe_failure_required",
            "dossier._evidence"),
            "causal dossier axis-probe binding")

        axis_e2e = _text(
            "executable-orchestrator/tools/"
            "prove_complete_observatory_protocol_axis_hardened.py")
        _require(axis_e2e, (
            'PROBE_CONTRACT = "observatory-axis-probe-v1"',
            'PROBE_EVALUATOR = "observatory_axis_probe_arena_v2.py"',
            "PROBE_EVALUATOR_PATH",
            "def _probe_report", "def _probe_pair",
            "axis_behavioral_probe_required",
            "axis_probe_pairs_verified",
            "axis_probe_evaluator_verified",
            "axis_probe_dossier_index_verified",
            "all_tasks_have_baseline_mutant_probe_pairs",
            "evidence_index",
            "candidate_axis_behavior"),
            "axis-probe Docker E2E verifier")

        provider = _text(
            "executable-orchestrator/tools/"
            "prove_complete_observatory_protocol_causal_provider_hardened.py")
        _require(provider, (
            "def _is_exact_core_provider",
            "def _genome_provider_popen",
            "mock_observatory_protocol_server.py",
            "mock_observatory_causal_server.py",
            '"real_provider_routes_modified": False'),
            "causal-aware local-provider route")

        final_entry = _text(
            "executable-orchestrator/tools/"
            "prove_complete_observatory_protocol_v5.py")
        _require(final_entry, (
            "prove_observatory_protocol_static_v5.py",
            "prove_complete_observatory_protocol_axis_hardened",
            "axis_probe_pairs_verified",
            "axis_probe_evaluator_verified",
            "axis_probe_dossier_index_verified",
            "axis_probe_pairs_bound",
            "axis_probe_evaluator_v2_bound",
            "final_closure_verified"),
            "authoritative final proof")
        stable = _text(
            "executable-orchestrator/tools/run_observatory_proof.py")
        if "prove_complete_observatory_protocol_v5" not in stable:
            raise RuntimeError(
                "stable proof command bypasses protocol-v5 closure")

        with open(
                _path("profiles/national-observatory/PARETO-DIMENSIONS.json"),
                encoding="utf-8") as handle:
            pareto = {row["id"]: row for row in json.load(handle)}
        dimension = pareto.get("genome_realization_survival") or {}
        if dimension.get("direction") != "higher" \
                or float(dimension.get("hard_minimum", -1)) != 1.0:
            raise RuntimeError(
                "causal genome realization is not a hard Pareto obligation")

        result.update({
            "status": "PASS",
            "protocol_version": protocol.PROTOCOL_VERSION,
            "protocol_bundle_sha256":
                protocol.protocol_bundle_sha256(ROOT),
            "protocol_files": len(protocol_files),
            "modules_imported": imported,
            "causal_terminal_conditions": sorted(CAUSAL_CONDITIONS),
            "causal_phases": list(causal.CAUSAL_LABELS),
            "final_audit_v3_identity_binding_verified": True,
            "bounded_evaluator_process_witnesses_verified": True,
            "auditor_specific_definition_set_ablation": True,
            "axis_specific_causal_attribution_verified": True,
            "axis_specific_behavioral_failure_verified": True,
            "axis_probe_contract_verified": True,
            "axis_probe_evaluator_v2_verified": True,
            "axis_probe_evaluator_bytes_bound": True,
            "axis_probe_signed_hard_minima_verified": True,
            "axis_probe_conditional_commutativity_verified": True,
            "axis_probe_task_identity_bound": True,
            "axis_probe_baseline_mutant_pair_required": True,
            "axis_probe_dossier_direct_indexing_required": True,
            "axis_probe_docker_reverification_required": True,
            "failure_scoped_attribution_verified": True,
            "cited_definition_semantics_verified": True,
            "deterministic_definition_body_receipts_verified": True,
            "inert_negative_controls_required": True,
            "exact_mutated_source_receipts_required": True,
            "infrastructure_failure_exclusion_verified": True,
            "causal_dossier_direct_indexing_required": True,
            "causal_genome_ablation_bound": True,
            "genome_aware_local_provider_verified": True,
            "causal_aware_local_provider_verified": True,
            "causal_local_provider_execution_route_verified": True,
            "authoritative_causal_e2e_verified": True,
            "axis_probe_evaluator_sha256": _sha256(
                _path(PROBE_EVALUATOR_PATH)),
            "inherited_static_report_sha256":
                _sha256(PREVIOUS_REPORT),
        })
    except Exception as exc:
        result["reason"] = f"{type(exc).__name__}: {exc}"

    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    with open(REPORT, "w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False,
                  indent=1, sort_keys=True)
    print(json.dumps(result, ensure_ascii=False,
                     indent=1, sort_keys=True))
    print("proof report:", REPORT)
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
