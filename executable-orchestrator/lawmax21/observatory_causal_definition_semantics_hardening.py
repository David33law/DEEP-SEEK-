"""Bind causal attribution to the semantics of the cited AST definitions.

A removed function name in an exception is not axis evidence when one broad function was cited for
many unrelated classes. This hardening parses the exact mutated source, recovers the bodies of the
renamed definitions and requires their AST identifiers/string literals to contain axis-relevant
semantic vocabulary unless the hidden evaluator independently exposes a relevant hard dimension or
failed axis-specific test signature.
"""
from __future__ import annotations

import ast
import re

from . import observatory_causal_attribution_scope_hardening as scope
from . import observatory_causal_axis_attribution_hardening as axis
from . import observatory_genome_causal_ablation_hardening as causal


_NORMALIZE = re.compile(r"[^a-z0-9_]+")


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
    normalized = " ".join(
        _NORMALIZE.sub(" ", str(value).lower()) for value in values)
    return normalized


def _definition_axis_support(context, task, result):
    source_path = causal._runtime_path(
        context, result.get("source_path"))
    source = open(source_path, encoding="utf-8").read()
    tree = ast.parse(source)
    symbols = [str(value) for value in task.get("symbols") or []]
    vocabularies = {}
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
    missing = sorted(set(symbols) - set(vocabularies))
    if missing:
        raise RuntimeError(
            "axis attribution could not recover mutated definition bodies: "
            + ", ".join(missing))
    tokens = tuple(axis.AXIS_TOKENS.get(task["axis"], ()))
    matched = sorted({
        token for text in vocabularies.values()
        for token in tokens if token in text})
    return {
        "definition_vocabulary_sha256_inputs": sorted(vocabularies),
        "matched_source_axis_tokens": matched,
        "source_semantic_support": bool(matched),
    }


def install(_ctx, handlers):
    if getattr(axis, "_definition_semantics_hardening_installed", False):
        return dict(handlers)

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
            attributed = bool(
                matched_dimensions
                or (removed_named
                    and source_support["source_semantic_support"]))
            return attributed, {
                "mode": "semantic-hard-dimension",
                "expected_dimensions": sorted(expected),
                "violated_dimensions": sorted(violated),
                "matched_dimensions": matched_dimensions,
                "removed_definition_named": removed_named,
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
        path_evidence = bool(failed_tests or failed_directed
                             or receipt.get("failures")
                             or receipt.get("counterexamples"))
        attributed = bool(
            matched_axis_failure
            or (path_evidence and matched_group_paths)
            or (removed_named
                and source_support["source_semantic_support"]))
        return attributed, {
            "mode": "specialized-failure-signature",
            "removed_definition_named": removed_named,
            **source_support,
            "failed_test_paths": failed_tests,
            "failed_directed_paths": failed_directed,
            "matched_axis_failure_tokens": matched_axis_failure,
            "matched_group_path_tokens": matched_group_paths,
            "matched_axis_or_group_tokens": sorted(set(
                matched_axis_failure + matched_group_paths)),
            "counterexample_count": len(
                receipt.get("counterexamples") or []),
            "failure_count": len(receipt.get("failures") or []),
            "failure_payload_fields": sorted(payload),
            "whole_receipt_searched": False,
        }

    axis._attribution = attribution
    axis._definition_semantics_hardening_installed = True
    return dict(handlers)
