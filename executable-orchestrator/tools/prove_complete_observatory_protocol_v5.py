#!/usr/bin/env python3
"""Authoritative protocol-v5 proof with baseline-versus-mutant axis causality.

Runs portable-owner static closure, axis-probe static closure and the axis-hardened production-
container E2E proof through the exact causal-aware localhost provider. Final closure is written only
after the E2E receipt proves COMMITTED state, zero paid calls, one provider-route substitution, exact-
source causal campaigns and a complete ``observatory-axis-probe-v1`` baseline/mutant pair for every
replication and crown causal task, with both reports indexed in the deterministic supremacy dossier.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

import prove_complete_observatory_protocol_axis_hardened as e2e

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
STATIC = os.path.join(HERE, "prove_observatory_protocol_static_v5.py")
INHERITED_STATIC_REPORT = os.path.join(
    ROOT, "proof", "observatory-protocol-static-v5.json")
CAUSAL_STATIC_REPORT = os.path.join(
    ROOT, "proof", "observatory-protocol-static-v5-causal.json")
E2E_REPORT = os.path.join(
    ROOT, "proof", "complete-observatory-protocol-e2e.json")
PROTOCOL_VERSION = "OBSERVATORY-OMEGA-RESEARCH-PROTOCOL-5"
PROBE_CONTRACT = "observatory-axis-probe-v1"
INHERITED_STATIC_GATES = (
    "strict_one_file_build_schema",
    "semantic_source_receipts_bound",
    "source_bound_evidence_required",
    "auditor_inference_diversity_required",
    "cross_auditor_citation_independence_required",
    "unbounded_production_rounds_bound",
    "stagnation_escalation_bound",
    "deterministic_supremacy_dossier_bound",
    "dossier_foundation_evidence_bound",
    "portable_owner_signature_static_extension",
    "final_launcher_v3_verified",
    "final_audit_v3_wired",
    "candidate_identity_prompt_bound",
    "owner_public_key_snapshot_verified",
    "signed_owner_decisions_snapshot_verified",
    "owner_gate_crypto_reverification_verified",
    "final_overlay_order_verified",
    "canonical_local_provider_verified",
    "authoritative_e2e_protocol_v5_verified",
)
CAUSAL_STATIC_GATES = (
    "final_audit_v3_identity_binding_verified",
    "bounded_evaluator_process_witnesses_verified",
    "causal_genome_ablation_bound",
    "auditor_specific_definition_set_ablation",
    "axis_specific_causal_attribution_verified",
    "axis_specific_behavioral_failure_verified",
    "axis_probe_contract_verified",
    "axis_probe_task_identity_bound",
    "axis_probe_baseline_mutant_pair_required",
    "axis_probe_dossier_direct_indexing_required",
    "axis_probe_docker_reverification_required",
    "failure_scoped_attribution_verified",
    "cited_definition_semantics_verified",
    "deterministic_definition_body_receipts_verified",
    "inert_negative_controls_required",
    "exact_mutated_source_receipts_required",
    "infrastructure_failure_exclusion_verified",
    "causal_dossier_direct_indexing_required",
    "genome_aware_local_provider_verified",
    "causal_aware_local_provider_verified",
    "causal_local_provider_execution_route_verified",
    "authoritative_causal_e2e_verified",
)


def _read(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _atomic_write(path, value):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    temporary = path + f".tmp-{os.getpid()}"
    try:
        with open(temporary, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False,
                      indent=1, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        try:
            directory = os.open(os.path.dirname(os.path.abspath(path)), os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        except OSError:
            pass
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _static_closure():
    inherited = _read(INHERITED_STATIC_REPORT)
    causal = _read(CAUSAL_STATIC_REPORT)
    inherited_missing = []
    for key in INHERITED_STATIC_GATES:
        expected = (
            "PASS" if key == "portable_owner_signature_static_extension"
            else True)
        if inherited.get(key) != expected:
            inherited_missing.append(key)
    causal_missing = [
        key for key in CAUSAL_STATIC_GATES
        if causal.get(key) is not True]
    if inherited.get("status") != "PASS" \
            or inherited.get("protocol_version") != PROTOCOL_VERSION \
            or inherited_missing \
            or causal.get("status") != "PASS" \
            or causal.get("protocol_version") != PROTOCOL_VERSION \
            or causal_missing:
        raise RuntimeError(json.dumps({
            "reason": "static protocol closure incomplete",
            "inherited_missing": inherited_missing,
            "causal_missing": causal_missing,
        }, ensure_ascii=False, sort_keys=True))
    inherited_bundle = inherited.get("protocol_bundle_sha256")
    causal_bundle = causal.get("protocol_bundle_sha256")
    if not isinstance(inherited_bundle, str) \
            or len(inherited_bundle) != 64 \
            or inherited_bundle != causal_bundle:
        raise RuntimeError(
            "portable-owner and causal static receipts bind different protocol bundles")
    return inherited, causal


def _pair_summary_valid(phase, summary):
    tasks = int(summary.get("tasks", 0))
    pairs = int(summary.get("axis_probe_pairs", 0))
    reports = int(summary.get("axis_probe_reports", 0))
    rows = summary.get("pairs") or []
    if tasks < 1 or tasks != pairs or reports != 2 * tasks \
            or len(rows) != tasks \
            or summary.get("axis_probe_contract") != PROBE_CONTRACT:
        raise RuntimeError(
            f"E2E {phase} axis-probe pair count or contract drift")
    identities = set()
    evidence_paths = set()
    for row in rows:
        identity = row.get("task_identity_sha256")
        baseline = row.get("baseline") or {}
        mutant = row.get("mutant") or {}
        if not isinstance(identity, str) or len(identity) != 64 \
                or identity in identities \
                or baseline.get("task_identity_sha256") != identity \
                or mutant.get("task_identity_sha256") != identity \
                or baseline.get("probe_id") != mutant.get("probe_id") \
                or baseline.get("seed") != mutant.get("seed") \
                or baseline.get("expected_sha256") != mutant.get(
                    "expected_sha256") \
                or baseline.get("source_sha256") == mutant.get(
                    "source_sha256") \
                or not baseline.get("path") or not mutant.get("path") \
                or len(str(baseline.get("sha256") or "")) != 64 \
                or len(str(mutant.get("sha256") or "")) != 64 \
                or not mutant.get("failed_checks"):
            raise RuntimeError(
                f"E2E {phase} contains a malformed axis-probe pair")
        identities.add(identity)
        evidence_paths.update((baseline["path"], mutant["path"]))
    if len(evidence_paths) != 2 * tasks:
        raise RuntimeError(
            f"E2E {phase} reuses an axis-probe report across tasks")
    return {
        "tasks": tasks,
        "pairs": pairs,
        "reports": reports,
        "task_identities": len(identities),
        "evidence_paths": len(evidence_paths),
    }


def _dynamic_closure(report):
    if report.get("status") != "PASS" \
            or report.get("protocol_version") != PROTOCOL_VERSION \
            or report.get("paid_api_calls") != 0:
        raise RuntimeError("base E2E receipt is not a zero-paid-call PASS")
    summary = report.get("run_summary") or {}
    if summary.get("final_state") != "COMMITTED" \
            or summary.get("log_verified") is not True:
        raise RuntimeError(
            "base E2E did not finish COMMITTED with a verified signed log")
    accounting = report.get("accounting") or {}
    if accounting.get("real_paid_api_calls") != 0 \
            or accounting.get("local_provider_accounting_verified") is not True:
        raise RuntimeError("E2E accounting does not prove zero real paid calls")

    verification = report.get("protocol_verification") or {}
    route = verification.get("causal_local_provider_route_verified") or {}
    if route.get("substitutions_observed") != 1 \
            or route.get("real_provider_routes_modified") is not False \
            or route.get("selected_path") != \
            "executable-orchestrator/tools/mock_observatory_causal_server.py" \
            or len(str(route.get("selected_sha256") or "")) != 64:
        raise RuntimeError(
            "E2E did not prove exactly one causal localhost-provider route")
    if verification.get("infrastructure_failure_exclusion_reverified") is not True:
        raise RuntimeError(
            "E2E did not independently exclude infrastructure-only causal credit")
    if verification.get("axis_specific_behavioral_failure_verified") is not True \
            or verification.get("axis_probe_dossier_index_verified") is not True:
        raise RuntimeError(
            "E2E did not prove axis behavior and direct dossier indexing")

    causal = verification.get("causal_genome_ablation_verified") or {}
    probes = verification.get("axis_probe_pairs_verified") or {}
    pair_summaries = {}
    for phase in ("replication", "crown"):
        campaign = causal.get(phase) or {}
        probe = probes.get(phase) or {}
        if int(campaign.get("tasks", 0)) < 1 \
                or int(campaign.get("negative_controls", 0)) < 1 \
                or int(campaign.get("specialized_process_witnesses", 0)) < 1 \
                or int(campaign.get("verified_axis_count", 0)) != 13 \
                or int(campaign.get(
                    "verified_auditor_axis_group_obligations", 0)) < 1:
            raise RuntimeError(
                f"E2E causal {phase} campaign is incomplete")
        pair_summaries[phase] = _pair_summary_valid(phase, probe)
        if pair_summaries[phase]["tasks"] != int(campaign.get("tasks", -1)):
            raise RuntimeError(
                f"E2E {phase} axis-probe pairs do not cover every causal task")
    verification["axis_probe_pair_final_summaries"] = pair_summaries
    return verification


def main(argv=None):
    static_run = subprocess.run(
        [sys.executable, STATIC], capture_output=True, text=True,
        timeout=3600,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    if static_run.returncode != 0:
        print(static_run.stdout)
        print(static_run.stderr, file=sys.stderr)
        return static_run.returncode
    try:
        inherited, causal = _static_closure()
    except Exception as exc:
        print(json.dumps({
            "status": "FAIL",
            "reason": f"{type(exc).__name__}: {exc}",
        }, ensure_ascii=False, indent=1, sort_keys=True))
        return 1

    code = e2e.main(argv)
    if code != 0:
        return code
    if not os.path.isfile(E2E_REPORT):
        print("authoritative E2E returned success without a proof report", file=sys.stderr)
        return 1
    report = _read(E2E_REPORT)
    try:
        verification = _dynamic_closure(report)
        report["static_protocol_v5_portable_owner_closure"] = {
            "status": inherited.get("status"),
            "protocol_version": inherited.get("protocol_version"),
            "protocol_bundle_sha256": inherited.get(
                "protocol_bundle_sha256"),
            **{key: inherited.get(key)
               for key in INHERITED_STATIC_GATES},
            "report_sha256": e2e.sha256_file(
                INHERITED_STATIC_REPORT),
        }
        report["static_protocol_v5_causal_closure"] = {
            "status": causal.get("status"),
            "protocol_version": causal.get("protocol_version"),
            "protocol_bundle_sha256": causal.get(
                "protocol_bundle_sha256"),
            **{key: causal.get(key) for key in CAUSAL_STATIC_GATES},
            "causal_terminal_conditions": causal.get(
                "causal_terminal_conditions"),
            "causal_phases": causal.get("causal_phases"),
            "report_sha256": e2e.sha256_file(CAUSAL_STATIC_REPORT),
        }
        report["authoritative_entrypoint"] = (
            "prove_complete_observatory_protocol_v5.py")
        report["causal_genome_ablation_bound"] = True
        report["axis_specific_causal_attribution_bound"] = True
        report["axis_specific_behavioral_failure_bound"] = True
        report["axis_probe_pairs_bound"] = True
        report["axis_probe_dossier_index_bound"] = True
        report["axis_probe_pair_summaries"] = verification[
            "axis_probe_pair_final_summaries"]
        report["failure_scoped_causal_attribution_bound"] = True
        report["cited_definition_semantics_bound"] = True
        report["deterministic_definition_body_receipts_bound"] = True
        report["causal_aware_local_provider_used"] = True
        report["causal_local_provider_route"] = verification[
            "causal_local_provider_route_verified"]
        report["infrastructure_failure_cannot_earn_causal_credit"] = True
        report["removed_definition_name_cannot_earn_causal_credit"] = True
        report["group_failure_path_cannot_earn_causal_credit"] = True
        report["diagnostic_token_matching_cannot_earn_causal_credit"] = True
        report["final_closure_verified"] = True
        _atomic_write(E2E_REPORT, report)
        return 0
    except Exception as exc:
        report["status"] = "FAIL"
        report["final_closure_verified"] = False
        report["final_closure_reason"] = f"{type(exc).__name__}: {exc}"
        _atomic_write(E2E_REPORT, report)
        print(json.dumps(report, ensure_ascii=False,
                         indent=1, sort_keys=True))
        return 1


if __name__ == "__main__":
    sys.exit(main())
