"""Preserve cited-definition semantics as diagnostic evidence, never causal authority.

A removed definition name, axis vocabulary in its AST body, or a failed test from the same broad
artifact group is useful review context but is not causal proof for a particular controlled axis.
This hardening binds every cited body to deterministic AST hashes and records its semantic vocabulary.
The authoritative decision is supplied later by the trusted baseline-versus-mutant axis probe.
"""
from __future__ import annotations

import ast
import hashlib
import json
import re
from types import MethodType

from . import observatory_causal_attribution_scope_hardening as scope
from . import observatory_causal_axis_attribution_hardening as axis
from . import observatory_genome_causal_ablation_hardening as causal
from .canonical import read_json


_NORMALIZE = re.compile(r"[^a-z0-9_]+")


def _lexemes(value):
    normalized = _NORMALIZE.sub(" ", str(value).lower())
    result = set()
    for token in normalized.split():
        result.add(token)
        result.update(part for part in token.split("_") if part)
    return result


def _node_vocabulary(node):
    values = []
    for item in ast.walk(node):
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            values.append(item.name)
        elif isinstance(item, ast.Name):
            values.append(item.id)
        elif isinstance(item, ast.Attribute):
            values.append(item.attr)
        elif isinstance(item, ast.arg):
            values.append(item.arg)
        elif isinstance(item, ast.Constant) and isinstance(item.value, str):
            values.append(item.value)
    lexemes = set()
    for value in values:
        lexemes.update(_lexemes(value))
    return sorted(lexemes)


def _definition_axis_support(context, task, result):
    source_path = causal._runtime_path(
        context, result.get("source_path"))
    source = open(source_path, encoding="utf-8").read()
    tree = ast.parse(source)
    symbols = [str(value) for value in task.get("symbols") or []]
    vocabularies = {}
    body_hashes = {}
    for node in ast.walk(tree):
        if not isinstance(node, (
                ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        matched = next((
            symbol for symbol in symbols
            if node.name == symbol
            or (node.name.startswith("__observatory_ablated_")
                and node.name.endswith("_" + symbol))), None)
        if matched:
            vocabularies[matched] = _node_vocabulary(node)
            body_hashes[matched] = hashlib.sha256(
                ast.dump(node, annotate_fields=True,
                         include_attributes=False).encode("utf-8")).hexdigest()
    missing = sorted(set(symbols) - set(vocabularies))
    if missing:
        raise RuntimeError(
            "axis attribution could not recover mutated definition bodies: "
            + ", ".join(missing))
    axis_tokens = set()
    for token in axis.AXIS_TOKENS.get(task["axis"], ()):
        axis_tokens.update(_lexemes(token))
    matched = sorted({
        token for values in vocabularies.values()
        for token in axis_tokens if token in set(values)})
    vocabulary_receipt = json.dumps(
        {key: vocabularies[key] for key in sorted(vocabularies)},
        ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {
        "definition_vocabulary_sha256_inputs": sorted(vocabularies),
        "definition_body_sha256": {
            key: body_hashes[key] for key in sorted(body_hashes)},
        "definition_vocabulary_sha256": hashlib.sha256(
            vocabulary_receipt.encode("utf-8")).hexdigest(),
        "matched_source_axis_tokens": matched,
        "source_semantic_support": bool(matched),
    }


def _campaign_state(context, report):
    receipt = (report or {}).get("causal_ablation_evidence") or {}
    relative = receipt.get("path")
    if not relative:
        return {"checked": False, "tasks": 0, "failure_scoped": 0,
                "behavioral": 0}
    try:
        campaign = read_json(causal._runtime_path(context, relative))
    except Exception:
        return {"checked": False, "tasks": 0, "failure_scoped": 0,
                "behavioral": 0}
    tasks = campaign.get("tasks") or []
    failure_scoped = sum(
        1 for task in tasks
        if (task.get("attribution") or {}).get(
            "definition_vocabulary_sha256_inputs")
        and (task.get("attribution") or {}).get(
            "definition_vocabulary_sha256")
        and (task.get("attribution") or {}).get(
            "whole_receipt_searched") is False)
    behavioral = sum(
        1 for task in tasks
        if (task.get("attribution") or {}).get(
            "behavioral_axis_evidence") is True)
    return {
        "checked": bool(
            tasks and failure_scoped == len(tasks)
            and behavioral == len(tasks)),
        "tasks": len(tasks),
        "failure_scoped": failure_scoped,
        "behavioral": behavioral,
    }


def install(ctx, handlers):
    if getattr(axis, "_definition_semantics_hardening_installed", False):
        return dict(handlers)
    original_summary = ctx.esc.supremacy_summary

    def attribution(context, task, result):
        receipt = axis._receipt(context, result)
        payload, failed_tests, failed_directed = scope._failure_payload(
            receipt, result)
        failure_text = axis._text(payload)
        failed_path_text = axis._text({
            "failed_tests": failed_tests,
            "failed_directed": failed_directed,
            "failures": receipt.get("failures") or [],
            "counterexamples": receipt.get("counterexamples") or [],
        })
        symbols = [
            str(value).lower() for value in task.get("symbols") or []]
        removed_named = any(
            symbol in failure_text for symbol in symbols)
        source_support = _definition_axis_support(
            context, task, result)

        claimed_axis = task["axis"]
        group = task["group"]
        if group == "semantic":
            violated = set((result.get("diagnostics") or {}).get(
                "violated_hard_dimensions") or [])
            expected = axis.SEMANTIC_DIMENSIONS.get(claimed_axis, set())
            matched_dimensions = sorted(violated & expected)
            behavioral = bool(matched_dimensions)
            return behavioral, {
                "mode": "semantic-hard-dimension",
                "expected_dimensions": sorted(expected),
                "violated_dimensions": sorted(violated),
                "matched_dimensions": matched_dimensions,
                "behavioral_axis_evidence": behavioral,
                "removed_definition_named": removed_named,
                "removed_definition_name_is_sufficient": False,
                "group_path_is_sufficient": False,
                "diagnostic_failure_attribution_is_sufficient": False,
                **source_support,
                "failure_payload_fields": sorted(payload),
                "whole_receipt_searched": False,
            }

        axis_tokens = tuple(axis.AXIS_TOKENS.get(claimed_axis, ()))
        group_tokens = tuple(axis.GROUP_TOKENS.get(group, ()))
        matched_axis_failure = sorted(
            token for token in axis_tokens if token in failure_text)
        matched_group_paths = sorted(
            token for token in group_tokens if token in failed_path_text)
        behavioral = bool(matched_axis_failure)
        return behavioral, {
            "mode": "specialized-failure-signature",
            "behavioral_axis_evidence": behavioral,
            "removed_definition_named": removed_named,
            "removed_definition_name_is_sufficient": False,
            "diagnostic_failure_attribution_is_sufficient": False,
            **source_support,
            "failed_test_paths": failed_tests,
            "failed_directed_paths": failed_directed,
            "matched_axis_failure_tokens": matched_axis_failure,
            "matched_group_path_tokens": matched_group_paths,
            "group_path_is_sufficient": False,
            "matched_axis_or_group_tokens": sorted(set(
                matched_axis_failure + matched_group_paths)),
            "counterexample_count": len(
                receipt.get("counterexamples") or []),
            "failure_count": len(receipt.get("failures") or []),
            "failure_payload_fields": sorted(payload),
            "whole_receipt_searched": False,
        }

    def summary(self):
        result = original_summary()
        incumbent = self.s.get("incumbent")
        scores = (ctx.scores.get(incumbent) or {}) if incumbent else {}
        replication = _campaign_state(
            ctx, scores.get("genome_realization_replication") or {})
        crown = _campaign_state(
            ctx, scores.get("genome_realization_crown") or {})
        result.update({
            "genome_definition_semantic_attribution_required": True,
            "genome_axis_behavioral_failure_required": True,
            "genome_definition_semantic_replication_checked":
                replication["checked"],
            "genome_definition_semantic_crown_checked": crown["checked"],
            "genome_definition_semantic_replication_tasks":
                replication["tasks"],
            "genome_definition_semantic_replication_failure_scoped":
                replication["failure_scoped"],
            "genome_definition_semantic_replication_behavioral":
                replication["behavioral"],
            "genome_definition_semantic_crown_tasks": crown["tasks"],
            "genome_definition_semantic_crown_failure_scoped":
                crown["failure_scoped"],
            "genome_definition_semantic_crown_behavioral":
                crown["behavioral"],
        })
        return result

    axis._attribution = attribution
    ctx.esc.supremacy_summary = MethodType(summary, ctx.esc)
    axis._definition_semantics_hardening_installed = True
    return dict(handlers)
