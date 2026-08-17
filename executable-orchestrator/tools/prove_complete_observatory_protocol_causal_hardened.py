#!/usr/bin/env python3
"""Causal genome-ablation extension of the portable-owner protocol-v5 Docker E2E proof.

The inherited proof still owns exact-clone setup, owner ceremony, production-container isolation,
crash/resume, owner gates, every architecture arena, novelty closure, terminal-negative proof,
portable owner-signature verification and the deterministic supremacy dossier. This extension adds
independent verification of every replication/crown causal mutant, inert negative control and exact
source/evaluator receipt. It never contacts the real provider.
"""
from __future__ import annotations

import json
import os

import prove_complete_observatory_protocol_signature_hardened as previous

CORE = previous.base.base
CAUSAL_CONDITIONS = {
    "genome_causal_ablation_replication_passed",
    "genome_causal_ablation_crown_passed",
}
CAUSAL_FILES = {
    "executable-orchestrator/lawmax21/observatory_genome_causal_ablation_hardening.py",
    "executable-orchestrator/lawmax21/observatory_causal_audit_hardening.py",
    "executable-orchestrator/lawmax21/observatory_causal_dossier_hardening.py",
    "executable-orchestrator/tools/prove_observatory_protocol_static_v5.py",
    "executable-orchestrator/tools/prove_complete_observatory_protocol_causal_hardened.py",
    "executable-orchestrator/tools/prove_complete_observatory_protocol_v5.py",
}
CORE.EXPECTED_NEW_CONDITIONS.update(CAUSAL_CONDITIONS)
CORE.REQUIRED_PROTOCOL_FILES.update(CAUSAL_FILES)
_ORIGINAL_VERIFY = CORE.verify_protocol


def _read(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _runtime_path(runtime, relative):
    path = os.path.abspath(os.path.join(
        runtime, *str(relative).replace("\\", "/").split("/")))
    root = os.path.abspath(runtime)
    if path != root and not path.startswith(root + os.sep):
        raise RuntimeError(
            "causal E2E evidence escapes runtime: " + str(relative))
    return path


def _hash_bound(runtime, relative, expected, label):
    path = _runtime_path(runtime, relative)
    if not os.path.isfile(path):
        raise RuntimeError(label + " is missing: " + str(relative))
    actual = CORE.sha256_file(path)
    if actual != expected:
        raise RuntimeError(label + " hash drift: " + str(relative))
    return path


def _verify_causal_campaign(runtime, incumbent, label):
    genome_relative = (
        f"architecture/genome-realization-{label}-{incumbent}.json")
    genome_path = _runtime_path(runtime, genome_relative)
    genome_report = _read(genome_path)
    receipt = genome_report.get("causal_ablation_evidence") or {}
    if genome_report.get("status") != "PASS" \
            or genome_report.get("passed") is not True \
            or genome_report.get("causal_ablation_required") is not True \
            or genome_report.get("causal_ablation_passed") is not True \
            or receipt.get("negative_controls_passed") is not True \
            or int(receipt.get("verified_axis_count", 0)) != 13 \
            or int(receipt.get("tasks_executed", 0)) < 1 \
            or int(receipt.get("negative_controls_executed", 0)) < 1:
        raise RuntimeError(
            f"causal genome {label}: genome receipt is incomplete")
    causal_path = _hash_bound(
        runtime, receipt.get("path"), receipt.get("sha256"),
        f"causal genome {label} campaign")
    causal = _read(causal_path)
    if causal.get("status") != "PASS" \
            or causal.get("passed") is not True \
            or causal.get("candidate_id") != incumbent \
            or causal.get("label") != label \
            or causal.get("negative_controls_passed") is not True \
            or causal.get("all_mutations_source_bound") is not True \
            or causal.get(
                "all_ablation_mutations_destroyed_claimed_behavior") is not True \
            or int(causal.get("verified_axis_count", 0)) != 13:
        raise RuntimeError(
            f"causal genome {label}: campaign did not pass")
    auditors = causal.get("auditor_ids") or []
    if len(auditors) != 2 or len(set(auditors)) != 2:
        raise RuntimeError(
            f"causal genome {label}: auditor identities are not independent")
    controls = causal.get("controls") or []
    tasks = causal.get("tasks") or []
    if len(controls) != int(causal.get("negative_controls_executed", 0)) \
            or len(tasks) != int(causal.get("tasks_executed", 0)):
        raise RuntimeError(
            f"causal genome {label}: persisted count mismatch")
    if int(causal.get(
            "verified_auditor_axis_group_obligations", 0)) != int(
                causal.get("required_auditor_axis_group_obligations", -1)):
        raise RuntimeError(
            f"causal genome {label}: auditor/axis/group obligations remain open")

    def verify_execution(row, kind):
        source_path = _hash_bound(
            runtime, row.get("source_path"), row.get("source_sha256"),
            f"causal genome {label} {kind} source")
        report_path = _hash_bound(
            runtime, row.get("evaluator_receipt_path"),
            row.get("evaluator_receipt_sha256"),
            f"causal genome {label} {kind} evaluator")
        persisted = _read(report_path)
        if persisted.get("candidate_sha256") != row.get("source_sha256"):
            raise RuntimeError(
                f"causal genome {label} {kind}: evaluator is not bound "
                "to exact mutant source bytes")
        if os.path.getsize(source_path) < 20:
            raise RuntimeError(
                f"causal genome {label} {kind}: mutant source is implausibly small")

    for control in controls:
        if control.get("control_passed") is not True \
                or control.get("observed_candidate_pass") is not True \
                or control.get("inert_definition_renamed") is not True:
            raise RuntimeError(
                f"causal genome {label}: inert negative control failed")
        verify_execution(control, "negative-control")
    for task in tasks:
        if task.get("auditor_id") not in auditors \
                or not task.get("axis") \
                or not task.get("group") \
                or not task.get("renamed_definitions") \
                or task.get("causal_failure_observed") is not True \
                or task.get("observed_candidate_pass") is not False:
            raise RuntimeError(
                f"causal genome {label}: load-bearing task did not falsify")
        verify_execution(task, "ablation")
    return {
        "genome_report_path": genome_relative,
        "genome_report_sha256": CORE.sha256_file(genome_path),
        "causal_report_path": receipt["path"],
        "causal_report_sha256": receipt["sha256"],
        "auditors": auditors,
        "tasks": len(tasks),
        "negative_controls": len(controls),
        "verified_axis_count": causal["verified_axis_count"],
        "verified_auditor_axis_group_obligations": causal[
            "verified_auditor_axis_group_obligations"],
    }


def _verify(repo, runtime, source_head, preflight, launch):
    verified = _ORIGINAL_VERIFY(
        repo, runtime, source_head, preflight, launch)
    mission = preflight.get("signed_mission") or {}
    for flag in (
            "causal_genome_ablation_required",
            "causal_genome_negative_controls_required"):
        if mission.get(flag) is not True:
            raise RuntimeError("signed mission flag missing: " + flag)
    if int(mission.get(
            "genome_causal_ablation_phases_required", 0)) != 2:
        raise RuntimeError(
            "signed mission does not require replication+crown causal phases")
    protocol_files = set(mission.get("research_protocol_files") or [])
    missing = sorted(CAUSAL_FILES - protocol_files)
    if missing:
        raise RuntimeError(
            "signed protocol omitted causal files: " + ", ".join(missing))

    summary = verified["summary"]
    escalation = summary.get("escalation") or {}
    conditions = escalation.get("conditions") or {}
    supremacy = escalation.get("supremacy") or {}
    for key in CAUSAL_CONDITIONS:
        if conditions.get(key) is not True \
                or supremacy.get(key) is not True:
            raise RuntimeError("terminal causal condition failed: " + key)
    incumbent = verified["incumbent"]
    campaigns = {
        label: _verify_causal_campaign(runtime, incumbent, label)
        for label in ("replication", "crown")}

    audit = verified["audit"]
    controlled = (audit.get("campaigns") or {}).get(
        "controlled_genome_realization") or {}
    causal_audit = (audit.get("campaigns") or {}).get(
        "causal_genome_ablation") or {}
    if controlled.get("causal_replication") is not True \
            or controlled.get("causal_crown") is not True \
            or causal_audit.get("replication_passed") is not True \
            or causal_audit.get("crown_passed") is not True \
            or causal_audit.get(
                "infrastructure_failure_counts_as_causal_failure") is not False \
            or causal_audit.get(
                "exact_mutated_source_receipts_required") is not True:
        raise RuntimeError(
            "independent audit did not reproduce causal genome closure")

    dossier_path = os.path.join(
        runtime, "architecture", "OMEGA-SUPREMACY-DOSSIER.json")
    dossier = _read(dossier_path)
    causal_dossier = dossier.get("causal_genome_realization") or {}
    evidence = {
        row.get("path"): row
        for row in dossier.get("evidence_index") or []
        if isinstance(row, dict) and row.get("path")}
    for label, campaign in campaigns.items():
        receipt = causal_dossier.get(label) or {}
        if receipt.get("status") != "PASS" \
                or receipt.get("evidence_path") != campaign[
                    "causal_report_path"] \
                or receipt.get("evidence_sha256") != campaign[
                    "causal_report_sha256"]:
            raise RuntimeError(
                f"supremacy dossier does not bind causal {label} campaign")
        for relative in (
                campaign["genome_report_path"],
                campaign["causal_report_path"]):
            row = evidence.get(relative) or {}
            path = _runtime_path(runtime, relative)
            if not row or row.get("sha256") != CORE.sha256_file(path):
                raise RuntimeError(
                    f"supremacy dossier evidence index omits causal {label}: "
                    + relative)
    if (dossier.get("search_closure") or {}).get(
            "causal_genome_replication") != "PASS" \
            or (dossier.get("crown_summary") or {}).get(
                "causal_genome_crown") != "PASS":
        raise RuntimeError(
            "supremacy dossier causal closure summary is incomplete")

    verified["causal_genome_ablation_verified"] = campaigns
    return verified


CORE.verify_protocol = _verify
main = previous.main
sha256_file = previous.sha256_file

__all__ = ["main", "sha256_file"]


if __name__ == "__main__":
    import sys
    sys.exit(main())
