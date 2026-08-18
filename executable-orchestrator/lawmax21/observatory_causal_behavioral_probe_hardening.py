"""Make trusted baseline-versus-mutant axis probes authoritative for causal attribution.

The earlier attribution layers retain valuable failure-only diagnostics and deterministic AST-body
receipts. They are not allowed to decide causal credit. This hardening runs the private axis-probe
arena twice for every auditor/axis/group/artifact task: once over the exact original source and once
over the exact load-bearing mutant, with the same hidden seed and probe ID. Credit requires a valid
passing baseline and a valid candidate-origin failing mutant. Infrastructure-invalid probes, a weak
baseline or a passing mutant leave the obligation open.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from types import MethodType

from . import observatory_causal_axis_attribution_hardening as axis
from . import observatory_distributed_overlay as distributed
from . import observatory_formal_overlay as formal
from . import observatory_genome_causal_ablation_hardening as causal
from . import observatory_interoperability_overlay as interop
from . import observatory_scale_overlay as scale
from .canonical import atomic_write_json, read_json, sha256_file
from .handlers import A


PROBE_CONTRACT = "observatory-axis-probe-v1"
PROBE_TIMEOUT_SECONDS = 1800
_TAIL_LIMIT = 4000


def _expected(ctx, cid, task):
    group = task["group"]
    if group == "distributed":
        return {
            "replication_distribution_model": distributed._model(
                ctx, cid, "replication_distribution_model"),
            "consistency_commit_model": distributed._model(
                ctx, cid, "consistency_commit_model"),
        }
    if group == "scale":
        return {"scaling_partition_model": scale._model(ctx, cid)}
    if group == "formal":
        return formal._expected(ctx, cid)
    if group == "interoperability":
        return interop._expected(ctx, cid)
    return {}


def _identity(ctx, cid, label, task):
    payload = {
        "run_id": ctx.run_id,
        "candidate_id": cid,
        "label": label,
        "auditor_id": task.get("auditor_id"),
        "axis": task.get("axis"),
        "group": task.get("group"),
        "artifact": task.get("artifact"),
        "symbols": sorted(task.get("symbols") or []),
    }
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True,
        separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _probe(ctx, cid, label, task, source_path, variant, seed, identity):
    source_path = os.path.abspath(source_path)
    runtime = os.path.abspath(ctx.runtime)
    if source_path != runtime and not source_path.startswith(runtime + os.sep):
        # Original candidate artifacts are also under the runtime. Refuse any future routing drift
        # rather than letting a probe read an arbitrary checkout path.
        raise RuntimeError(
            "axis-probe source escapes runtime: " + source_path)
    expected = _expected(ctx, cid, task)
    output = A(
        ctx, "reports",
        f"axis-probe-{label}-{identity[:20]}-{variant}.json")
    evaluator = os.path.join(
        ctx.evaluator_dir, "observatory_axis_probe_arena.py")
    if not os.path.isfile(evaluator):
        raise RuntimeError("trusted axis-probe evaluator is missing: " + evaluator)
    command = [
        sys.executable, evaluator,
        "--candidate", source_path,
        "--group", task["group"],
        "--axis", task["axis"],
        "--out", output,
        "--seed", str(seed),
        "--expected-json", json.dumps(
            expected, ensure_ascii=False, sort_keys=True,
            separators=(",", ":")),
    ]
    process = subprocess.run(
        command, capture_output=True, text=True,
        timeout=PROBE_TIMEOUT_SECONDS)
    process_receipt = {
        "axis_probe_returncode": process.returncode,
        "axis_probe_stdout_tail": (process.stdout or "")[-_TAIL_LIMIT:],
        "axis_probe_stderr_tail": (process.stderr or "")[-_TAIL_LIMIT:],
    }
    if not os.path.isfile(output):
        raise RuntimeError(
            "axis-probe evaluator produced no persisted report: "
            + json.dumps(process_receipt, ensure_ascii=False))
    report = read_json(output)
    actual_source = sha256_file(source_path)
    if report.get("candidate_sha256") != actual_source:
        raise RuntimeError(
            "axis-probe report is not bound to exact candidate source bytes")
    report.update(process_receipt)
    report["variant"] = variant
    report["task_identity_sha256"] = identity
    report["source_path"] = os.path.relpath(
        source_path, ctx.runtime).replace("\\", "/")
    report["source_sha256"] = actual_source
    report["evidence_path"] = os.path.relpath(
        output, ctx.runtime).replace("\\", "/")
    atomic_write_json(output, report)
    report["evidence_sha256"] = sha256_file(output)
    return report


def _valid_baseline(report):
    return bool(
        report.get("contract") == PROBE_CONTRACT
        and report.get("status") == "PASS"
        and report.get("passed") is True
        and report.get("valid_execution") is True
        and report.get("failure_origin") == "none"
        and report.get("axis_probe_returncode") == 0
        and report.get("checks")
        and all(row.get("passed") is True
                for row in report.get("checks") or []))


def _valid_mutant_failure(report):
    return bool(
        report.get("contract") == PROBE_CONTRACT
        and report.get("status") == "FAIL"
        and report.get("passed") is False
        and report.get("valid_execution") is True
        and report.get("failure_origin") == "candidate_axis_behavior"
        and report.get("axis_probe_returncode") == 1
        and report.get("checks")
        and any(row.get("passed") is False
                for row in report.get("checks") or []))


def _campaign_state(context, report):
    receipt = (report or {}).get("causal_ablation_evidence") or {}
    relative = receipt.get("path")
    if not relative:
        return {"checked": False, "tasks": 0, "probe_pairs": 0}
    try:
        campaign = read_json(causal._runtime_path(context, relative))
    except Exception:
        return {"checked": False, "tasks": 0, "probe_pairs": 0}
    tasks = campaign.get("tasks") or []
    pairs = sum(
        1 for task in tasks
        if (task.get("attribution") or {}).get(
            "axis_probe_contract") == PROBE_CONTRACT
        and (task.get("attribution") or {}).get(
            "baseline_axis_probe_passed") is True
        and (task.get("attribution") or {}).get(
            "mutant_axis_probe_failed") is True)
    return {
        "checked": bool(tasks and pairs == len(tasks)),
        "tasks": len(tasks),
        "probe_pairs": pairs,
    }


def install(ctx, handlers):
    if getattr(axis, "_behavioral_probe_hardening_installed", False):
        return dict(handlers)
    previous_attribution = axis._attribution
    previous_task = causal._run_task
    previous_summary = ctx.esc.supremacy_summary

    def attribution(context, task, result):
        cid = task.get("candidate_id")
        label = task.get("causal_label")
        if not cid or not label:
            raise RuntimeError(
                "axis-probe attribution lacks candidate/phase identity")
        diagnostic_attributed, diagnostic = previous_attribution(
            context, task, result)
        identity = _identity(context, cid, label, task)
        seed = int(hashlib.sha256(
            f"axis-probe|{context.run_id}|{identity}".encode()).hexdigest()[:8], 16)
        original_path = causal._artifact_path(
            context, cid, task["artifact"])
        mutant_path = causal._runtime_path(
            context, result.get("source_path"))
        baseline = _probe(
            context, cid, label, task, original_path,
            "baseline", seed, identity)
        mutant = _probe(
            context, cid, label, task, mutant_path,
            "mutant", seed, identity)
        same_probe = bool(
            baseline.get("probe_id") == mutant.get("probe_id")
            and baseline.get("axis") == task["axis"]
            and mutant.get("axis") == task["axis"]
            and baseline.get("group") == task["group"]
            and mutant.get("group") == task["group"]
            and baseline.get("seed") == mutant.get("seed") == seed
            and baseline.get("expected_sha256") == mutant.get("expected_sha256"))
        baseline_passed = _valid_baseline(baseline)
        mutant_failed = _valid_mutant_failure(mutant)
        attributed = bool(same_probe and baseline_passed and mutant_failed)
        details = dict(diagnostic)
        details.update({
            "mode": "baseline-versus-mutant-axis-probe",
            "axis_probe_contract": PROBE_CONTRACT,
            "axis_probe_id": baseline.get("probe_id"),
            "axis_probe_seed": seed,
            "same_axis_probe": same_probe,
            "baseline_axis_probe_passed": baseline_passed,
            "mutant_axis_probe_failed": mutant_failed,
            "behavioral_axis_evidence": attributed,
            "baseline_axis_probe_path": baseline.get("evidence_path"),
            "baseline_axis_probe_sha256": baseline.get("evidence_sha256"),
            "baseline_axis_probe_source_sha256": baseline.get("source_sha256"),
            "mutant_axis_probe_path": mutant.get("evidence_path"),
            "mutant_axis_probe_sha256": mutant.get("evidence_sha256"),
            "mutant_axis_probe_source_sha256": mutant.get("source_sha256"),
            "baseline_axis_checks": baseline.get("checks") or [],
            "mutant_axis_checks": mutant.get("checks") or [],
            "diagnostic_failure_attribution": bool(diagnostic_attributed),
            "diagnostic_failure_attribution_is_sufficient": False,
            "removed_definition_name_is_sufficient": False,
            "group_path_is_sufficient": False,
            "whole_receipt_searched": False,
        })
        return attributed, details

    def run_task(context, candidate_id, label, task):
        enriched = dict(task)
        enriched["candidate_id"] = candidate_id
        enriched["causal_label"] = label
        return previous_task(context, candidate_id, label, enriched)

    def summary(self):
        result = previous_summary()
        incumbent = self.s.get("incumbent")
        scores = (ctx.scores.get(incumbent) or {}) if incumbent else {}
        replication = _campaign_state(
            ctx, scores.get("genome_realization_replication") or {})
        crown = _campaign_state(
            ctx, scores.get("genome_realization_crown") or {})
        result.update({
            "genome_axis_behavioral_probe_required": True,
            "genome_axis_behavioral_probe_contract": PROBE_CONTRACT,
            "genome_axis_behavioral_probe_replication_checked":
                replication["checked"],
            "genome_axis_behavioral_probe_crown_checked": crown["checked"],
            "genome_axis_behavioral_probe_replication_tasks":
                replication["tasks"],
            "genome_axis_behavioral_probe_replication_pairs":
                replication["probe_pairs"],
            "genome_axis_behavioral_probe_crown_tasks": crown["tasks"],
            "genome_axis_behavioral_probe_crown_pairs": crown["probe_pairs"],
        })
        return result

    axis._attribution = attribution
    causal._run_task = run_task
    ctx.esc.supremacy_summary = MethodType(summary, ctx.esc)
    axis._behavioral_probe_hardening_installed = True
    return dict(handlers)
