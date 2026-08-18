"""Bind replication/crown causal genome evidence into the deterministic supremacy dossier.

The final dossier independently rehashes every mutant source, evaluator receipt, inert control and
trusted baseline-versus-mutant axis-probe pair. Diagnostic token matching, definition names and broad
artifact failures remain review context only. Causal credit requires the original exact source to pass
and the exact mutant to fail the same hidden ``observatory-axis-probe-v1`` probe ID, seed, axis, group
and controlled-manifest digest. Both probe reports are indexed directly in the public evidence set.
"""
from __future__ import annotations

import os

from . import observatory_supremacy_dossier_overlay as dossier
from .canonical import atomic_write_json, read_json, sha256_file
from .handlers import A


LABELS = ("replication", "crown")
PROBE_CONTRACT = "observatory-axis-probe-v1"


def _inside_runtime(ctx, relative):
    path = os.path.abspath(os.path.join(
        ctx.runtime, *str(relative).replace("\\", "/").split("/")))
    runtime = os.path.abspath(ctx.runtime)
    if path != runtime and not path.startswith(runtime + os.sep):
        raise RuntimeError(
            "causal dossier evidence escapes runtime: " + str(relative))
    return path


def _hex64(value):
    return isinstance(value, str) and len(value) == 64 \
        and all(char in "0123456789abcdef" for char in value.lower())


def _verify_execution(ctx, label, row, kind):
    source_path = _inside_runtime(ctx, row.get("source_path"))
    evidence_path = _inside_runtime(
        ctx, row.get("evaluator_receipt_path"))
    if not os.path.isfile(source_path) \
            or sha256_file(source_path) != row.get("source_sha256"):
        raise RuntimeError(
            f"supremacy dossier: causal genome {label} {kind} source hash drift")
    if not os.path.isfile(evidence_path) \
            or sha256_file(evidence_path) != row.get(
                "evaluator_receipt_sha256"):
        raise RuntimeError(
            f"supremacy dossier: causal genome {label} {kind} evaluator hash drift")
    evaluator = read_json(evidence_path)
    if evaluator.get("candidate_sha256") != row.get("source_sha256"):
        raise RuntimeError(
            f"supremacy dossier: causal genome {label} {kind} evaluator "
            "is not bound to the exact mutated source bytes")
    if row.get("artifact") != "semantic":
        diagnostics = row.get("diagnostics") or {}
        if not isinstance(evaluator.get("evaluator_returncode"), int) \
                or diagnostics.get("infrastructure_failure_excluded") is not True \
                or diagnostics.get("candidate_source_receipt_verified") is not True:
            raise RuntimeError(
                f"supremacy dossier: causal genome {label} {kind} lacks "
                "specialized process/source classification")
        expected_origin = (
            "none-control-passed" if kind == "negative-control"
            else "candidate")
        if diagnostics.get("failure_origin") != expected_origin:
            raise RuntimeError(
                f"supremacy dossier: causal genome {label} {kind} has "
                "the wrong failure origin")


def _definition_receipt_valid(attribution):
    inputs = attribution.get("definition_vocabulary_sha256_inputs") or []
    bodies = attribution.get("definition_body_sha256") or {}
    return bool(
        inputs
        and isinstance(bodies, dict)
        and set(bodies) == set(inputs)
        and all(_hex64(value) for value in bodies.values())
        and _hex64(attribution.get("definition_vocabulary_sha256"))
        and attribution.get("whole_receipt_searched") is False
        and attribution.get(
            "removed_definition_name_is_sufficient") is False
        and attribution.get("group_path_is_sufficient") is False
        and attribution.get(
            "diagnostic_failure_attribution_is_sufficient") is False)


def _probe_report(ctx, label, task, attribution, variant):
    prefix = variant + "_axis_probe_"
    relative = attribution.get(prefix + "path")
    expected_report_sha = attribution.get(prefix + "sha256")
    expected_source_sha = attribution.get(prefix + "source_sha256")
    if not relative or not _hex64(expected_report_sha) \
            or not _hex64(expected_source_sha):
        raise RuntimeError(
            f"supremacy dossier: causal genome {label} {variant} axis probe "
            "lacks path/source/report hashes")
    path = _inside_runtime(ctx, relative)
    if not os.path.isfile(path) \
            or sha256_file(path) != expected_report_sha:
        raise RuntimeError(
            f"supremacy dossier: causal genome {label} {variant} axis-probe "
            "report hash drift")
    report = read_json(path)
    if not isinstance(report, dict):
        raise RuntimeError(
            f"supremacy dossier: causal genome {label} {variant} axis-probe "
            "report is not an object")
    source_path = _inside_runtime(ctx, report.get("source_path"))
    if not os.path.isfile(source_path) \
            or sha256_file(source_path) != expected_source_sha \
            or report.get("source_sha256") != expected_source_sha \
            or report.get("candidate_sha256") != expected_source_sha:
        raise RuntimeError(
            f"supremacy dossier: causal genome {label} {variant} axis probe "
            "is not bound to the exact source bytes")
    if report.get("evidence_path") != relative \
            or report.get("contract") != PROBE_CONTRACT \
            or report.get("variant") != variant \
            or report.get("axis") != task.get("axis") \
            or report.get("group") != task.get("group") \
            or report.get("probe_id") != attribution.get("axis_probe_id") \
            or report.get("seed") != attribution.get("axis_probe_seed") \
            or report.get("task_identity_sha256") != task.get(
                "axis_probe_task_identity_sha256"):
        raise RuntimeError(
            f"supremacy dossier: causal genome {label} {variant} axis-probe "
            "identity drift")
    checks = report.get("checks") or []
    if not isinstance(checks, list) or not checks \
            or not all(isinstance(row, dict)
                       and isinstance(row.get("passed"), bool)
                       for row in checks):
        raise RuntimeError(
            f"supremacy dossier: causal genome {label} {variant} axis-probe "
            "checks are malformed")
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
            f"supremacy dossier: causal genome {label} {variant} axis-probe "
            "behavioral verdict is invalid")
    return {
        "variant": variant,
        "path": path,
        "relative_path": relative,
        "report_sha256": expected_report_sha,
        "source_path": source_path,
        "source_sha256": expected_source_sha,
        "probe_id": report["probe_id"],
        "seed": report["seed"],
        "expected_sha256": report.get("expected_sha256"),
        "task_identity_sha256": report.get("task_identity_sha256"),
        "checks": checks,
        "failed_checks": sorted(
            str(row.get("id")) for row in checks
            if row.get("passed") is False),
    }


def _probe_pair(ctx, label, task):
    attribution = task.get("attribution") or {}
    if attribution.get("mode") != "baseline-versus-mutant-axis-probe" \
            or attribution.get("axis_probe_contract") != PROBE_CONTRACT \
            or attribution.get("same_axis_probe") is not True \
            or attribution.get("baseline_axis_probe_passed") is not True \
            or attribution.get("mutant_axis_probe_failed") is not True \
            or attribution.get("behavioral_axis_evidence") is not True \
            or not _definition_receipt_valid(attribution):
        raise RuntimeError(
            f"supremacy dossier: causal genome {label} task has no valid "
            "baseline-versus-mutant axis attribution")
    identity = attribution.get("axis_probe_task_identity_sha256")
    if not _hex64(identity):
        raise RuntimeError(
            f"supremacy dossier: causal genome {label} task identity is invalid")
    enriched = dict(task)
    enriched["axis_probe_task_identity_sha256"] = identity
    baseline = _probe_report(
        ctx, label, enriched, attribution, "baseline")
    mutant = _probe_report(
        ctx, label, enriched, attribution, "mutant")
    if baseline["probe_id"] != mutant["probe_id"] \
            or baseline["seed"] != mutant["seed"] \
            or baseline["expected_sha256"] != mutant["expected_sha256"] \
            or baseline["task_identity_sha256"] != mutant[
                "task_identity_sha256"] \
            or baseline["source_sha256"] == mutant["source_sha256"] \
            or mutant["source_sha256"] != task.get("source_sha256") \
            or attribution.get("baseline_axis_checks") != baseline["checks"] \
            or attribution.get("mutant_axis_checks") != mutant["checks"]:
        raise RuntimeError(
            f"supremacy dossier: causal genome {label} baseline/mutant "
            "axis-probe pair does not share one exact probe")
    return {
        "task_identity_sha256": identity,
        "auditor_id": task.get("auditor_id"),
        "axis": task.get("axis"),
        "group": task.get("group"),
        "artifact": task.get("artifact"),
        "probe_contract": PROBE_CONTRACT,
        "probe_id": baseline["probe_id"],
        "seed": baseline["seed"],
        "expected_sha256": baseline["expected_sha256"],
        "baseline": baseline,
        "mutant": mutant,
    }


def _verify(ctx, incumbent, label):
    genome_path = A(
        ctx, "architecture",
        f"genome-realization-{label}-{incumbent}.json")
    genome_report = read_json(genome_path)
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
            f"supremacy dossier: causal genome {label} receipt is incomplete")
    relative = receipt.get("path")
    causal_path = _inside_runtime(ctx, relative)
    if not os.path.isfile(causal_path) \
            or sha256_file(causal_path) != receipt.get("sha256"):
        raise RuntimeError(
            f"supremacy dossier: causal genome {label} receipt hash drift")
    causal = read_json(causal_path)
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
            f"supremacy dossier: causal genome {label} campaign did not pass")
    auditors = causal.get("auditor_ids") or []
    if len(auditors) != 2 or len(set(auditors)) != 2:
        raise RuntimeError(
            f"supremacy dossier: causal genome {label} auditor set is invalid")
    if int(causal.get(
            "verified_auditor_axis_group_obligations", 0)) != int(
                causal.get("required_auditor_axis_group_obligations", -1)):
        raise RuntimeError(
            f"supremacy dossier: causal genome {label} obligations remain open")

    controls = causal.get("controls") or []
    tasks = causal.get("tasks") or []
    if len(controls) != int(causal.get("negative_controls_executed", 0)) \
            or len(tasks) != int(causal.get("tasks_executed", 0)):
        raise RuntimeError(
            f"supremacy dossier: causal genome {label} count mismatch")
    for row in controls:
        if row.get("control_passed") is not True \
                or row.get("observed_candidate_pass") is not True \
                or row.get("inert_definition_renamed") is not True:
            raise RuntimeError(
                f"supremacy dossier: causal genome {label} inert control failed")
        _verify_execution(ctx, label, row, "negative-control")

    pairs = []
    probe_paths = []
    for task in tasks:
        if task.get("auditor_id") not in auditors \
                or not task.get("axis") \
                or not task.get("group") \
                or not task.get("renamed_definitions") \
                or task.get("causal_failure_observed") is not True \
                or task.get("observed_candidate_pass") is not False \
                or task.get("axis_specific_failure_attributed") is not True:
            raise RuntimeError(
                f"supremacy dossier: causal genome {label} task is incomplete")
        _verify_execution(ctx, label, task, "ablation")
        pair = _probe_pair(ctx, label, task)
        pairs.append(pair)
        probe_paths.extend((
            pair["baseline"]["relative_path"],
            pair["mutant"]["relative_path"]))
    if len(pairs) != len(tasks) \
            or len(set(probe_paths)) != 2 * len(tasks):
        raise RuntimeError(
            f"supremacy dossier: causal genome {label} axis-probe pair count drift")
    return {
        "genome_path": genome_path,
        "causal_path": causal_path,
        "causal": causal,
        "pairs": pairs,
        "task_count": len(tasks),
    }


def install(_ctx, handlers):
    if getattr(dossier, "_causal_dossier_hardening_installed", False):
        return dict(handlers)
    original = dossier._build_dossier

    def build(context, original_conditions):
        path, artifact = original(context, original_conditions)
        incumbent = artifact.get("candidate_id")
        if not incumbent:
            raise RuntimeError("causal dossier hardening has no incumbent")
        rows = list(artifact.get("evidence_index") or [])
        existing = {row.get("path") for row in rows}
        receipts = {}
        for label in LABELS:
            verified = _verify(context, incumbent, label)
            causal = verified["causal"]
            for evidence_path, evidence_label in (
                    (verified["genome_path"],
                     f"genome_realization_{label}"),
                    (verified["causal_path"],
                     f"genome_causal_ablation_{label}")):
                relative = os.path.relpath(
                    evidence_path, context.runtime).replace("\\", "/")
                if relative in existing:
                    continue
                row, _parsed = dossier._evidence(
                    context, evidence_path, require_pass=True,
                    label=evidence_label)
                rows.append(row)
                existing.add(relative)

            pair_receipts = []
            for index, pair in enumerate(verified["pairs"], 1):
                for variant in ("baseline", "mutant"):
                    probe = pair[variant]
                    relative = probe["relative_path"]
                    if relative not in existing:
                        row, _parsed = dossier._evidence(
                            context, probe["path"],
                            require_pass=(variant == "baseline"),
                            label=(
                                f"axis_probe_{label}_{index:04d}_"
                                f"{pair['axis']}_{pair['group']}_{variant}"))
                        rows.append(row)
                        existing.add(relative)
                pair_receipts.append({
                    "task_identity_sha256": pair[
                        "task_identity_sha256"],
                    "auditor_id": pair["auditor_id"],
                    "axis": pair["axis"],
                    "group": pair["group"],
                    "artifact": pair["artifact"],
                    "probe_contract": pair["probe_contract"],
                    "probe_id": pair["probe_id"],
                    "seed": pair["seed"],
                    "expected_sha256": pair["expected_sha256"],
                    "baseline_path": pair["baseline"]["relative_path"],
                    "baseline_sha256": pair["baseline"]["report_sha256"],
                    "baseline_source_sha256": pair[
                        "baseline"]["source_sha256"],
                    "mutant_path": pair["mutant"]["relative_path"],
                    "mutant_sha256": pair["mutant"]["report_sha256"],
                    "mutant_source_sha256": pair[
                        "mutant"]["source_sha256"],
                    "mutant_failed_checks": pair[
                        "mutant"]["failed_checks"],
                })

            receipts[label] = {
                "status": causal["status"],
                "tasks_executed": causal["tasks_executed"],
                "axis_specific_tasks": verified["task_count"],
                "axis_behavioral_failures": verified["task_count"],
                "axis_probe_contract": PROBE_CONTRACT,
                "axis_probe_pairs": len(pair_receipts),
                "axis_probe_reports": 2 * len(pair_receipts),
                "all_tasks_have_baseline_mutant_probe_pairs": bool(
                    pair_receipts
                    and len(pair_receipts) == verified["task_count"]),
                "axis_probe_pair_receipts": pair_receipts,
                "axis_specific_failure_attribution": True,
                "axis_specific_behavioral_failure_required": True,
                "baseline_axis_probe_required": True,
                "mutant_axis_probe_failure_required": True,
                "diagnostic_failure_attribution_is_sufficient": False,
                "cited_definition_semantics_checked": True,
                "removed_definition_name_is_sufficient": False,
                "group_failure_path_is_sufficient": False,
                "whole_receipt_searched": False,
                "negative_controls_executed":
                    causal["negative_controls_executed"],
                "verified_axis_count": causal["verified_axis_count"],
                "verified_auditor_axis_group_obligations": causal[
                    "verified_auditor_axis_group_obligations"],
                "evidence_path": os.path.relpath(
                    verified["causal_path"], context.runtime).replace(
                        "\\", "/"),
                "evidence_sha256": sha256_file(verified["causal_path"]),
            }
        artifact["evidence_index"] = rows
        artifact["causal_genome_realization"] = receipts
        artifact.setdefault("search_closure", {})[
            "causal_genome_replication"] = "PASS"
        artifact.setdefault("search_closure", {})[
            "axis_specific_causal_replication"] = "PASS"
        artifact.setdefault("search_closure", {})[
            "axis_behavioral_causal_replication"] = "PASS"
        artifact.setdefault("search_closure", {})[
            "axis_probe_pairs_replication"] = "PASS"
        artifact.setdefault("crown_summary", {})[
            "causal_genome_crown"] = "PASS"
        artifact.setdefault("crown_summary", {})[
            "axis_specific_causal_crown"] = "PASS"
        artifact.setdefault("crown_summary", {})[
            "axis_behavioral_causal_crown"] = "PASS"
        artifact.setdefault("crown_summary", {})[
            "axis_probe_pairs_crown"] = "PASS"
        atomic_write_json(path, artifact)
        return path, artifact

    dossier._build_dossier = build
    dossier._causal_dossier_hardening_installed = True
    return dict(handlers)
