"""Restrict axis attribution to failure-specific evidence only.

A complete evaluator report contains manifests, expected genome labels and successful metadata that
can mention every architecture axis. Searching the whole receipt would therefore make attribution
trivial. This hardening permits tokens and removed-definition names only in explicit failure fields,
failed test/directive paths, counterexamples and trusted parent diagnostics.
"""
from __future__ import annotations

from . import observatory_causal_axis_attribution_hardening as axis


_FAILURE_FIELDS = (
    "reason", "error", "traceback", "stderr", "stderr_tail", "stdout_tail",
    "failures", "counterexamples", "diagnostics", "errors",
    "revision_history", "scale_failure", "formal_model_failure",
    "cross_model_failure", "genome_realization_failure",
)


def _failure_payload(receipt, result):
    failed_tests = axis._false_paths(receipt.get("tests") or {})
    failed_directed = axis._false_paths(receipt.get("directed") or {})
    values = {
        key: receipt.get(key)
        for key in _FAILURE_FIELDS
        if receipt.get(key) not in (None, "", [], {})}
    values["failed_test_paths"] = failed_tests
    values["failed_directed_paths"] = failed_directed
    values["parent_diagnostics"] = result.get("diagnostics") or {}
    return values, failed_tests, failed_directed


def install(_ctx, handlers):
    if getattr(axis, "_failure_scope_hardening_installed", False):
        return dict(handlers)

    def attribution(context, task, result):
        receipt = axis._receipt(context, result)
        claimed_axis = task["axis"]
        group = task["group"]
        symbols = [
            str(value).lower() for value in task.get("symbols") or []]
        payload, failed_tests, failed_directed = _failure_payload(
            receipt, result)
        failure_text = axis._text(payload)
        named_definition = any(
            symbol in failure_text for symbol in symbols)

        if group == "semantic":
            violated = set((result.get("diagnostics") or {}).get(
                "violated_hard_dimensions") or [])
            expected = axis.SEMANTIC_DIMENSIONS.get(claimed_axis, set())
            matched = sorted(violated & expected)
            return bool(matched or named_definition), {
                "mode": "semantic-hard-dimension",
                "expected_dimensions": sorted(expected),
                "violated_dimensions": sorted(violated),
                "matched_dimensions": matched,
                "removed_definition_named": named_definition,
                "failure_payload_fields": sorted(payload),
                "whole_receipt_searched": False,
            }

        tokens = tuple(dict.fromkeys(
            axis.AXIS_TOKENS.get(claimed_axis, ())
            + axis.GROUP_TOKENS.get(group, ())))
        matched_tokens = sorted(
            token for token in tokens if token in failure_text)
        targeted = bool(named_definition or matched_tokens)
        return targeted, {
            "mode": "specialized-failure-signature",
            "removed_definition_named": named_definition,
            "failed_test_paths": failed_tests,
            "failed_directed_paths": failed_directed,
            "matched_axis_or_group_tokens": matched_tokens,
            "counterexample_count": len(
                receipt.get("counterexamples") or []),
            "failure_count": len(receipt.get("failures") or []),
            "failure_payload_fields": sorted(payload),
            "whole_receipt_searched": False,
        }

    axis._attribution = attribution
    axis._failure_scope_hardening_installed = True
    return dict(handlers)
