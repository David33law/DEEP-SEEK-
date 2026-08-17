"""Bind replication/crown causal genome-ablation receipts into the deterministic dossier.

The genome-realization report contains the causal receipt hash, but the final public dossier also
indexes the exact causal campaign bytes directly. This wrapper runs after foundational dossier
hardening and before the dossier handler is installed. It independently rehashes every mutated source
and evaluator receipt, checks evaluator-to-source identity, inert controls, auditor obligations,
axis-specific failure attribution and load-bearing failures, then adds replication and crown receipts
to the evidence index.
"""
from __future__ import annotations

import os

from . import observatory_supremacy_dossier_overlay as dossier
from .canonical import atomic_write_json, read_json, sha256_file
from .handlers import A


LABELS = ("replication", "crown")


def _inside_runtime(ctx, relative):
    path = os.path.abspath(os.path.join(
        ctx.runtime, *str(relative).replace("\\", "/").split("/")))
    runtime = os.path.abspath(ctx.runtime)
    if path != runtime and not path.startswith(runtime + os.sep):
        raise RuntimeError(
            "causal dossier evidence escapes runtime: " + str(relative))
    return path


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
    attributed = 0
    for row in tasks:
        attribution = row.get("attribution") or {}
        if row.get("auditor_id") not in auditors \
                or not row.get("axis") \
                or not row.get("group") \
                or not row.get("renamed_definitions") \
                or row.get("causal_failure_observed") is not True \
                or row.get("observed_candidate_pass") is not False \
                or row.get("axis_specific_failure_attributed") is not True \
                or attribution.get("mode") not in (
                    "semantic-hard-dimension",
                    "specialized-failure-signature"):
            raise RuntimeError(
                f"supremacy dossier: causal genome {label} task did not "
                "falsify an axis-specific claim")
        _verify_execution(ctx, label, row, "ablation")
        attributed += 1
    if attributed != len(tasks):
        raise RuntimeError(
            f"supremacy dossier: causal genome {label} attribution count drift")
    return genome_path, causal_path, causal, attributed


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
            genome_path, causal_path, causal, attributed = _verify(
                context, incumbent, label)
            for evidence_path, evidence_label in (
                    (genome_path, f"genome_realization_{label}"),
                    (causal_path, f"genome_causal_ablation_{label}")):
                relative = os.path.relpath(
                    evidence_path, context.runtime).replace("\\", "/")
                if relative in existing:
                    continue
                row, _parsed = dossier._evidence(
                    context, evidence_path, require_pass=True,
                    label=evidence_label)
                rows.append(row)
                existing.add(relative)
            receipts[label] = {
                "status": causal["status"],
                "tasks_executed": causal["tasks_executed"],
                "axis_specific_tasks": attributed,
                "axis_specific_failure_attribution": True,
                "negative_controls_executed":
                    causal["negative_controls_executed"],
                "verified_axis_count": causal["verified_axis_count"],
                "verified_auditor_axis_group_obligations": causal[
                    "verified_auditor_axis_group_obligations"],
                "evidence_path": os.path.relpath(
                    causal_path, context.runtime).replace("\\", "/"),
                "evidence_sha256": sha256_file(causal_path),
            }
        artifact["evidence_index"] = rows
        artifact["causal_genome_realization"] = receipts
        artifact.setdefault("search_closure", {})[
            "causal_genome_replication"] = "PASS"
        artifact.setdefault("search_closure", {})[
            "axis_specific_causal_replication"] = "PASS"
        artifact.setdefault("crown_summary", {})[
            "causal_genome_crown"] = "PASS"
        artifact.setdefault("crown_summary", {})[
            "axis_specific_causal_crown"] = "PASS"
        atomic_write_json(path, artifact)
        return path, artifact

    dossier._build_dossier = build
    dossier._causal_dossier_hardening_installed = True
    return dict(handlers)
