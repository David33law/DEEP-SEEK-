"""Require every genome ablation to fail for an axis-relevant reason.

A central function can be load-bearing while saying little about the specific controlled class for
which an auditor cited it. This hardening wraps each causal task and requires the mutated evaluator
receipt to expose either the exact removed definition or a failed hard dimension/test family relevant
to the claimed axis and artifact group. An unrelated crash cannot prove an axis. Replication and
crown attribution counts are reproduced from persisted campaign files in the terminal summary.
"""
from __future__ import annotations

import json
from types import MethodType

from . import observatory_genome_causal_ablation_hardening as causal
from .canonical import read_json


SEMANTIC_DIMENSIONS = {
    "canonical_authority_seat": {
        "canonical_identity_accuracy", "replay_determinism",
        "publication_projection_consistency"},
    "evidence_primitive": {
        "source_coverage", "change_detection_recall",
        "provenance_completeness"},
    "identity_model": {
        "canonical_identity_accuracy",
        "jurisprudence_temporal_link_accuracy"},
    "state_derivation_model": {
        "temporal_reconstruction_accuracy", "normative_effect_accuracy",
        "replay_determinism"},
    "temporal_model": {
        "temporal_reconstruction_accuracy",
        "jurisprudence_temporal_link_accuracy"},
    "normative_effect_model": {"normative_effect_accuracy"},
    "provenance_proof_model": {"provenance_completeness"},
    "publication_topology": {"publication_projection_consistency"},
    "governance_evolution_model": {
        "change_detection_recall", "normative_effect_accuracy",
        "replay_determinism"},
}

AXIS_TOKENS = {
    "canonical_authority_seat": (
        "canonical", "authority", "state_root", "root", "publication"),
    "evidence_primitive": (
        "source", "evidence", "admit", "ingest", "duplicate", "conflict"),
    "identity_model": (
        "identity", "canonical_id", "provision", "version", "ecli", "query"),
    "state_derivation_model": (
        "state", "transition", "replay", "rebuild", "root"),
    "temporal_model": (
        "time", "temporal", "bitemporal", "effective", "knowledge",
        "correction"),
    "normative_effect_model": (
        "effect", "amend", "repeal", "revive", "correct", "suspend",
        "impact"),
    "consistency_commit_model": (
        "commit", "quorum", "partition", "duplicate", "conflict",
        "single_writer", "sequence"),
    "replication_distribution_model": (
        "replication", "convergence", "heal", "restart", "recover",
        "rebuild", "corruption", "byzantine", "roots"),
    "trusted_core_topology": (
        "open_system", "durable", "integrity", "crash", "recover",
        "manifest", "transition", "kernel"),
    "provenance_proof_model": (
        "provenance", "evidence", "derivation", "source", "hash"),
    "publication_topology": (
        "publication", "projection", "publish", "linked", "eli", "xml",
        "root"),
    "governance_evolution_model": (
        "governance", "rule", "upgrade", "handler", "transition",
        "version"),
    "scaling_partition_model": (
        "scale", "partition", "shard", "routing", "rebuild", "tail",
        "throughput", "balance"),
}

GROUP_TOKENS = {
    "systems": (
        "restart", "concurrent", "crash", "corruption", "rebuild",
        "integrity", "publication"),
    "distributed": (
        "partition", "quorum", "convergence", "restart", "recovery",
        "rebuild", "corruption", "byzantine", "duplicate"),
    "scale": (
        "partition", "balance", "rebuild", "restart", "tail", "recovery",
        "no_silent", "publication"),
    "formal": (
        "counterexample", "transition", "query", "root", "manifest",
        "bitemporal", "repeal", "revival", "rule-upgrade"),
    "interoperability": (
        "identity", "projection", "eli", "ecli", "akoma", "legalruleml",
        "provenance", "impact", "root", "xml"),
}


def _false_paths(value, prefix=""):
    paths = []
    if isinstance(value, bool):
        if value is False:
            paths.append(prefix or "<root>")
        return paths
    if isinstance(value, dict):
        for key, item in value.items():
            child = f"{prefix}.{key}" if prefix else str(key)
            paths.extend(_false_paths(item, child))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            child = f"{prefix}[{index}]"
            paths.extend(_false_paths(item, child))
    return paths


def _receipt(context, result):
    relative = result.get("evaluator_receipt_path")
    path = causal._runtime_path(context, relative)
    return read_json(path)


def _text(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True).lower()


def _attribution(context, task, result):
    receipt = _receipt(context, result)
    axis = task["axis"]
    group = task["group"]
    symbols = [str(value).lower() for value in task.get("symbols") or []]
    receipt_text = _text(receipt)
    named_definition = any(symbol in receipt_text for symbol in symbols)

    if group == "semantic":
        violated = set((result.get("diagnostics") or {}).get(
            "violated_hard_dimensions") or [])
        expected = SEMANTIC_DIMENSIONS.get(axis, set())
        matched = sorted(violated & expected)
        return bool(matched or named_definition), {
            "mode": "semantic-hard-dimension",
            "expected_dimensions": sorted(expected),
            "violated_dimensions": sorted(violated),
            "matched_dimensions": matched,
            "removed_definition_named": named_definition,
        }

    false_paths = _false_paths(receipt.get("tests") or {})
    counterexamples = receipt.get("counterexamples") or []
    failure_text = " ".join([
        receipt_text,
        _text(false_paths),
        _text(counterexamples),
        _text(result.get("diagnostics") or {}),
    ])
    tokens = tuple(dict.fromkeys(
        AXIS_TOKENS.get(axis, ()) + GROUP_TOKENS.get(group, ())))
    matched_tokens = sorted(
        token for token in tokens if token in failure_text)
    targeted = bool(named_definition or matched_tokens)
    return targeted, {
        "mode": "specialized-failure-signature",
        "removed_definition_named": named_definition,
        "failed_test_paths": false_paths,
        "matched_axis_or_group_tokens": matched_tokens,
        "counterexample_count": len(counterexamples),
    }


def _campaign_state(context, report):
    receipt = (report or {}).get("causal_ablation_evidence") or {}
    relative = receipt.get("path")
    if not relative:
        return {"passed": False, "tasks": 0, "attributed": 0}
    try:
        campaign = read_json(causal._runtime_path(context, relative))
    except Exception:
        return {"passed": False, "tasks": 0, "attributed": 0}
    tasks = campaign.get("tasks") or []
    attributed = sum(
        1 for task in tasks
        if task.get("axis_specific_failure_attributed") is True
        and task.get("causal_failure_observed") is True)
    passed = bool(
        campaign.get("status") == "PASS"
        and campaign.get("passed") is True
        and tasks
        and attributed == len(tasks))
    return {"passed": passed, "tasks": len(tasks), "attributed": attributed}


def install(ctx, handlers):
    if getattr(causal, "_axis_attribution_hardening_installed", False):
        return dict(handlers)
    original_task = causal._run_task
    original_summary = ctx.esc.supremacy_summary

    def run_task(context, candidate_id, label, task):
        result = original_task(context, candidate_id, label, task)
        if result.get("causal_failure_observed") is not True:
            result["axis_specific_failure_attributed"] = False
            result["attribution"] = {
                "mode": "candidate-did-not-fail",
                "reason": "A passing mutant cannot support causal realization."}
            return result
        attributed, details = _attribution(context, task, result)
        result["axis_specific_failure_attributed"] = attributed
        result["attribution"] = details
        if not attributed:
            # The campaign's existing all-fail condition now rejects this task without treating an
            # unrelated failure as evidence for the claimed controlled axis.
            result["causal_failure_observed"] = False
        return result

    def summary(self):
        result = original_summary()
        incumbent = self.s.get("incumbent")
        scores = (ctx.scores.get(incumbent) or {}) if incumbent else {}
        replication = _campaign_state(
            ctx, scores.get("genome_realization_replication") or {})
        crown = _campaign_state(
            ctx, scores.get("genome_realization_crown") or {})
        result.update({
            "genome_axis_specific_attribution_required": True,
            "genome_axis_specific_replication_passed": replication["passed"],
            "genome_axis_specific_crown_passed": crown["passed"],
            "genome_axis_specific_replication_tasks": replication["tasks"],
            "genome_axis_specific_replication_attributed":
                replication["attributed"],
            "genome_axis_specific_crown_tasks": crown["tasks"],
            "genome_axis_specific_crown_attributed": crown["attributed"],
        })
        return result

    causal._run_task = run_task
    ctx.esc.supremacy_summary = MethodType(summary, ctx.esc)
    causal._axis_attribution_hardening_installed = True
    return dict(handlers)
