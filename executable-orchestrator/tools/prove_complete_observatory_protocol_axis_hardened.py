#!/usr/bin/env python3
"""Baseline-versus-mutant axis-probe extension of the causal protocol-v5 Docker E2E proof.

The inherited proof verifies exact mutated source bytes, process receipts, inert controls, portable
owner signatures and every architecture arena. This final layer reopens each
``observatory-axis-probe-v1`` baseline and mutant report, rehashes both reports and source files,
requires the exact v2 evaluator bytes from the disposable clone, and proves that the original passes
while the exact mutant fails the same hidden probe. Every probe report is also required in the direct
deterministic supremacy-dossier evidence index.
"""
from __future__ import annotations

import json
import os

import prove_complete_observatory_protocol_causal_provider_hardened as previous

CORE = previous.base.CORE
PROBE_CONTRACT = "observatory-axis-probe-v1"
PROBE_EVALUATOR = "observatory_axis_probe_arena_v2.py"
PROBE_EVALUATOR_PATH = (
    "private-evaluator/evaluator/" + PROBE_EVALUATOR)
AXIS_FILES = {
    "executable-orchestrator/lawmax21/"
    "observatory_causal_axis_attribution_hardening.py",
    "executable-orchestrator/lawmax21/"
    "observatory_causal_attribution_scope_hardening.py",
    "executable-orchestrator/lawmax21/"
    "observatory_causal_definition_semantics_hardening.py",
    "executable-orchestrator/lawmax21/"
    "observatory_causal_behavioral_probe_hardening.py",
    "private-evaluator/evaluator/observatory_axis_probe_arena.py",
    PROBE_EVALUATOR_PATH,
    "executable-orchestrator/tools/"
    "prove_complete_observatory_protocol_axis_hardened.py",
}
for relative in AXIS_FILES:
    previous.base.CAUSAL_FILES.add(relative)
    CORE.REQUIRED_PROTOCOL_FILES.add(relative)
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
            "axis-probe E2E evidence escapes runtime: " + str(relative))
    return path


def _repo_path(repo, relative):
    path = os.path.abspath(os.path.join(
        repo, *str(relative).replace("\\", "/").split("/")))
    root = os.path.abspath(repo)
    if path != root and not path.startswith(root + os.sep):
        raise RuntimeError(
            "axis-probe E2E protocol file escapes repository: " + str(relative))
    return path


def _hex64(value):
    return isinstance(value, str) and len(value) == 64 \
        and all(char in "0123456789abcdef" for char in value.lower())


def _definition_receipt_valid(details):
    vocabulary = details.get("definition_vocabulary_sha256")
    body_hashes = details.get("definition_body_sha256") or {}
    inputs = details.get("definition_vocabulary_sha256_inputs") or []
    return bool(
        inputs
        and _hex64(vocabulary)
        and isinstance(body_hashes, dict)
        and set(body_hashes) == set(inputs)
        and all(_hex64(value) for value in body_hashes.values())
        and details.get("whole_receipt_searched") is False
        and details.get(
            "removed_definition_name_is_sufficient") is False
        and details.get("group_path_is_sufficient") is False
        and details.get(
            "diagnostic_failure_attribution_is_sufficient") is False)


def _probe_report(runtime, task, details, variant):
    prefix = variant + "_axis_probe_"
    relative = details.get(prefix + "path")
    expected_report_sha = details.get(prefix + "sha256")
    expected_source_sha = details.get(prefix + "source_sha256")
    if not relative or not _hex64(expected_report_sha) \
            or not _hex64(expected_source_sha):
        raise RuntimeError(
            f"axis-probe {variant}: missing report/source binding")
    path = _runtime_path(runtime, relative)
    if not os.path.isfile(path) \
            or CORE.sha256_file(path) != expected_report_sha:
        raise RuntimeError(
            f"axis-probe {variant}: report hash drift: {relative}")
    report = _read(path)
    source_path = _runtime_path(runtime, report.get("source_path"))
    if not os.path.isfile(source_path) \
            or CORE.sha256_file(source_path) != expected_source_sha \
            or report.get("source_sha256") != expected_source_sha \
            or report.get("candidate_sha256") != expected_source_sha:
        raise RuntimeError(
            f"axis-probe {variant}: exact source receipt failed")
    identity = details.get("axis_probe_task_identity_sha256")
    if report.get("contract") != PROBE_CONTRACT \
            or details.get("axis_probe_evaluator") != PROBE_EVALUATOR \
            or report.get("variant") != variant \
            or report.get("evidence_path") != relative \
            or report.get("axis") != task.get("axis") \
            or report.get("group") != task.get("group") \
            or report.get("probe_id") != details.get("axis_probe_id") \
            or report.get("seed") != details.get("axis_probe_seed") \
            or report.get("task_identity_sha256") != identity:
        raise RuntimeError(
            f"axis-probe {variant}: evaluator/probe/task identity drift")
    checks = report.get("checks") or []
    if not checks or not all(
            isinstance(row, dict) and isinstance(row.get("passed"), bool)
            for row in checks):
        raise RuntimeError(
            f"axis-probe {variant}: malformed structured checks")
    if variant == "baseline":
        valid = bool(
            report.get("status") == "PASS"
            and report.get("passed") is True
            and report.get("valid_execution") is True
            and report.get("failure_origin") == "none"
            and report.get("axis_probe_returncode") == 0
            and all(row["passed"] is True for row in checks))
    else:
        valid = bool(
            report.get("status") == "FAIL"
            and report.get("passed") is False
            and report.get("valid_execution") is True
            and report.get("failure_origin") == "candidate_axis_behavior"
            and report.get("axis_probe_returncode") == 1
            and any(row["passed"] is False for row in checks))
    if not valid:
        raise RuntimeError(
            f"axis-probe {variant}: invalid behavioral verdict")
    return {
        "variant": variant,
        "path": relative,
        "sha256": expected_report_sha,
        "source_path": report.get("source_path"),
        "source_sha256": expected_source_sha,
        "probe_id": report.get("probe_id"),
        "seed": report.get("seed"),
        "expected_sha256": report.get("expected_sha256"),
        "task_identity_sha256": report.get("task_identity_sha256"),
        "checks": checks,
        "failed_checks": sorted(
            str(row.get("id")) for row in checks
            if row.get("passed") is False),
    }


def _probe_pair(runtime, task):
    details = task.get("attribution") or {}
    if task.get("axis_specific_failure_attributed") is not True \
            or task.get("causal_failure_observed") is not True \
            or task.get("observed_candidate_pass") is not False \
            or details.get("mode") != "baseline-versus-mutant-axis-probe" \
            or details.get("axis_probe_contract") != PROBE_CONTRACT \
            or details.get("axis_probe_evaluator") != PROBE_EVALUATOR \
            or details.get("same_axis_probe") is not True \
            or details.get("baseline_axis_probe_passed") is not True \
            or details.get("mutant_axis_probe_failed") is not True \
            or details.get("behavioral_axis_evidence") is not True \
            or not _hex64(details.get(
                "axis_probe_task_identity_sha256")) \
            or not _definition_receipt_valid(details):
        raise RuntimeError(
            "axis-probe task lacks an authoritative v2 behavioral pair")
    baseline = _probe_report(runtime, task, details, "baseline")
    mutant = _probe_report(runtime, task, details, "mutant")
    if baseline["probe_id"] != mutant["probe_id"] \
            or baseline["seed"] != mutant["seed"] \
            or baseline["expected_sha256"] != mutant["expected_sha256"] \
            or baseline["task_identity_sha256"] != mutant[
                "task_identity_sha256"] \
            or baseline["source_sha256"] == mutant["source_sha256"] \
            or mutant["source_sha256"] != task.get("source_sha256") \
            or details.get("baseline_axis_checks") != baseline["checks"] \
            or details.get("mutant_axis_checks") != mutant["checks"]:
        raise RuntimeError(
            "axis-probe baseline and mutant are not the same exact probe pair")
    return {
        "task_identity_sha256": baseline["task_identity_sha256"],
        "auditor_id": task.get("auditor_id"),
        "axis": task.get("axis"),
        "group": task.get("group"),
        "artifact": task.get("artifact"),
        "probe_contract": PROBE_CONTRACT,
        "probe_evaluator": PROBE_EVALUATOR,
        "probe_id": baseline["probe_id"],
        "seed": baseline["seed"],
        "expected_sha256": baseline["expected_sha256"],
        "baseline": baseline,
        "mutant": mutant,
    }


def _verify_campaign(runtime, incumbent, label):
    genome_path = os.path.join(
        runtime, "architecture",
        f"genome-realization-{label}-{incumbent}.json")
    genome_report = _read(genome_path)
    receipt = genome_report.get("causal_ablation_evidence") or {}
    causal_path = _runtime_path(runtime, receipt.get("path"))
    if not os.path.isfile(causal_path) \
            or CORE.sha256_file(causal_path) != receipt.get("sha256"):
        raise RuntimeError(
            f"axis-probe causal {label}: campaign hash drift")
    causal = _read(causal_path)
    tasks = causal.get("tasks") or []
    if not tasks or len(tasks) != int(causal.get("tasks_executed", -1)):
        raise RuntimeError(
            f"axis-probe causal {label}: campaign task count drift")
    pairs = [_probe_pair(runtime, task) for task in tasks]
    paths = [
        pair[variant]["path"]
        for pair in pairs for variant in ("baseline", "mutant")]
    if len(pairs) != len(tasks) or len(set(paths)) != 2 * len(tasks):
        raise RuntimeError(
            f"axis-probe causal {label}: probe-pair count or uniqueness drift")
    return {
        "campaign_path": receipt.get("path"),
        "campaign_sha256": receipt.get("sha256"),
        "tasks": len(tasks),
        "axis_specific_tasks": len(pairs),
        "axis_behavioral_failures": len(pairs),
        "axis_probe_contract": PROBE_CONTRACT,
        "axis_probe_evaluator": PROBE_EVALUATOR,
        "axis_probe_pairs": len(pairs),
        "axis_probe_reports": len(paths),
        "whole_receipt_searched": False,
        "removed_definition_name_is_sufficient": False,
        "group_failure_path_is_sufficient": False,
        "diagnostic_failure_attribution_is_sufficient": False,
        "cited_definition_semantics_checked": True,
        "definition_body_hashes_checked": True,
        "pairs": pairs,
    }


def _dossier_pair_map(receipt):
    rows = receipt.get("axis_probe_pair_receipts") or []
    result = {}
    for row in rows:
        identity = row.get("task_identity_sha256")
        if not _hex64(identity) or identity in result:
            raise RuntimeError(
                "supremacy dossier has missing or duplicate axis-probe task identity")
        result[identity] = row
    return result


def _verify(repo, runtime, source_head, preflight, launch):
    verified = _ORIGINAL_VERIFY(
        repo, runtime, source_head, preflight, launch)
    mission = preflight.get("signed_mission") or {}
    for flag in (
            "axis_specific_causal_attribution_required",
            "axis_specific_behavioral_failure_required",
            "axis_behavioral_probe_required"):
        if mission.get(flag) is not True:
            raise RuntimeError(
                "signed mission does not require " + flag)
    files = set(mission.get("research_protocol_files") or [])
    missing = sorted(AXIS_FILES - files)
    if missing:
        raise RuntimeError(
            "signed protocol omitted axis-probe files: "
            + ", ".join(missing))

    evaluator_path = _repo_path(repo, PROBE_EVALUATOR_PATH)
    if not os.path.isfile(evaluator_path):
        raise RuntimeError("hardened axis-probe evaluator is absent from clone")
    evaluator_receipt = {
        "name": PROBE_EVALUATOR,
        "path": PROBE_EVALUATOR_PATH,
        "sha256": CORE.sha256_file(evaluator_path),
        "bytes": os.path.getsize(evaluator_path),
    }

    incumbent = verified["incumbent"]
    campaigns = {
        label: _verify_campaign(runtime, incumbent, label)
        for label in ("replication", "crown")}
    audit = verified["audit"]
    causal_audit = (audit.get("campaigns") or {}).get(
        "causal_genome_ablation") or {}
    for label, campaign in campaigns.items():
        task_key = f"{label}_axis_probe_tasks"
        pair_key = f"{label}_axis_probe_pairs"
        if int(causal_audit.get(task_key, 0)) != campaign["tasks"] \
                or int(causal_audit.get(pair_key, 0)) != campaign[
                    "axis_probe_pairs"]:
            raise RuntimeError(
                f"independent audit axis-probe {label} count drift")
    if causal_audit.get("axis_behavioral_probe_required") is not True \
            or causal_audit.get(
                "axis_behavioral_probe_contract") != PROBE_CONTRACT \
            or causal_audit.get(
                "axis_behavioral_probe_evaluator") != PROBE_EVALUATOR \
            or causal_audit.get(
                "all_tasks_have_baseline_mutant_probe_pairs") is not True \
            or causal_audit.get(
                "all_tasks_axis_behaviorally_falsified") is not True \
            or causal_audit.get(
                "diagnostic_failure_attribution_is_sufficient") is not False \
            or causal_audit.get(
                "removed_definition_name_is_sufficient") is not False \
            or causal_audit.get(
                "group_failure_path_is_sufficient") is not False:
        raise RuntimeError(
            "independent audit did not reproduce v2 axis-probe pairs")

    dossier_path = os.path.join(
        runtime, "architecture", "OMEGA-SUPREMACY-DOSSIER.json")
    dossier = _read(dossier_path)
    dossier_evaluator = dossier.get("axis_probe_evaluator") or {}
    if dossier_evaluator != evaluator_receipt:
        raise RuntimeError(
            "supremacy dossier does not bind exact v2 axis-probe evaluator bytes")
    evidence_index = {
        row.get("path"): row
        for row in dossier.get("evidence_index") or []
        if isinstance(row, dict) and row.get("path")}
    causal_dossier = dossier.get("causal_genome_realization") or {}
    for label, campaign in campaigns.items():
        receipt = causal_dossier.get(label) or {}
        mapped = _dossier_pair_map(receipt)
        if receipt.get("axis_probe_contract") != PROBE_CONTRACT \
                or receipt.get("axis_probe_evaluator") != evaluator_receipt \
                or receipt.get(
                    "all_tasks_have_baseline_mutant_probe_pairs") is not True \
                or int(receipt.get("axis_probe_pairs", 0)) != campaign[
                    "axis_probe_pairs"] \
                or int(receipt.get("axis_probe_reports", 0)) != campaign[
                    "axis_probe_reports"] \
                or len(mapped) != campaign["axis_probe_pairs"]:
            raise RuntimeError(
                f"supremacy dossier does not bind all {label} v2 axis-probe pairs")
        for pair in campaign["pairs"]:
            dossier_pair = mapped.get(pair["task_identity_sha256"]) or {}
            if dossier_pair.get("probe_contract") != PROBE_CONTRACT \
                    or dossier_pair.get("probe_evaluator") != PROBE_EVALUATOR \
                    or dossier_pair.get("probe_id") != pair["probe_id"] \
                    or dossier_pair.get("seed") != pair["seed"] \
                    or dossier_pair.get("expected_sha256") != pair[
                        "expected_sha256"]:
                raise RuntimeError(
                    f"supremacy dossier {label} axis-probe pair identity drift")
            for variant in ("baseline", "mutant"):
                probe = pair[variant]
                if dossier_pair.get(f"{variant}_path") != probe["path"] \
                        or dossier_pair.get(f"{variant}_sha256") != probe[
                            "sha256"] \
                        or dossier_pair.get(
                            f"{variant}_source_sha256") != probe[
                                "source_sha256"]:
                    raise RuntimeError(
                        f"supremacy dossier {label} {variant} probe receipt drift")
                evidence = evidence_index.get(probe["path"]) or {}
                if evidence.get("sha256") != probe["sha256"]:
                    raise RuntimeError(
                        f"supremacy dossier evidence index omits {label} "
                        f"{variant} axis probe: {probe['path']}")
        summary_key = (
            "axis_probe_pairs_replication" if label == "replication"
            else "axis_probe_pairs_crown")
        summary = (
            dossier.get("search_closure") if label == "replication"
            else dossier.get("crown_summary")) or {}
        if summary.get(summary_key) != "PASS":
            raise RuntimeError(
                f"supremacy dossier {label} axis-probe closure summary is absent")

    verified["axis_specific_causal_attribution_verified"] = campaigns
    verified["axis_specific_behavioral_failure_verified"] = True
    verified["axis_probe_pairs_verified"] = campaigns
    verified["axis_probe_evaluator_verified"] = evaluator_receipt
    verified["axis_probe_dossier_index_verified"] = True
    return verified


CORE.verify_protocol = _verify
main = previous.main
sha256_file = previous.sha256_file

__all__ = ["main", "sha256_file"]


if __name__ == "__main__":
    import sys
    sys.exit(main())
