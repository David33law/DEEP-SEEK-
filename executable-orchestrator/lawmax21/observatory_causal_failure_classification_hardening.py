"""Classify causal-ablation evaluator outcomes conservatively.

A failing mutant is evidence only when the signed evaluator actually ran against the exact mutated
source and returned a candidate-specific failure. Missing container engines, isolation refusal,
parent timeout, output truncation, missing reports and other infrastructure failures invalidate the
ablation instead of proving that a genome mechanism is load-bearing.
"""
from __future__ import annotations

from . import observatory_genome_causal_ablation_hardening as causal


_INFRASTRUCTURE_MARKERS = (
    "requires docker",
    "requires docker/podman",
    "container runtime unavailable",
    "no container runtime",
    "docker engine is not ready",
    "cannot connect to the docker",
    "permission denied while trying to connect",
    "isolation unavailable",
    "bounded evaluator produced no report",
    "produced no report",
    "output limit exceeded",
    "stdout limit",
    "stderr limit",
    "timed out after",
    "process timeout",
    "image pull",
    "manifest unknown",
)


def install(_ctx, handlers):
    if getattr(causal, "_failure_classification_hardening_installed", False):
        return dict(handlers)
    original = causal._specialized_passes

    def specialized_passes(report):
        if not isinstance(report, dict):
            raise RuntimeError(
                "causal specialized evaluator returned no report object")
        for key in ("candidate_sha256", "candidate_path", "evidence_path"):
            if not report.get(key):
                raise RuntimeError(
                    "causal specialized evaluator lacks exact-source receipt: " + key)
        returncode = report.get("evaluator_returncode")
        if not isinstance(returncode, int):
            raise RuntimeError(
                "causal specialized evaluator lacks a process return code")
        status = report.get("status")
        reason_text = " ".join(str(report.get(key) or "") for key in (
            "reason", "error", "stderr", "stderr_tail", "stdout_tail"))
        lowered = reason_text.lower()
        marker = next((value for value in _INFRASTRUCTURE_MARKERS
                       if value in lowered), None)
        if marker:
            raise RuntimeError(
                "causal evaluator infrastructure failure is non-evidence: " + marker)
        passed, diagnostics = original(report)
        if passed:
            if returncode != 0:
                raise RuntimeError(
                    "causal negative control reports PASS with nonzero evaluator return code")
        else:
            if status != "FAIL" or report.get("passed", False) is not False:
                raise RuntimeError(
                    "causal mutant failure is not an explicit candidate FAIL receipt")
            if returncode == 0:
                raise RuntimeError(
                    "causal mutant reports FAIL with zero evaluator return code")
            candidate_specific = any(
                report.get(key) not in (None, {}, [], "")
                for key in (
                    "tests", "counterexamples", "diagnostics", "reason",
                    "traceback", "errors", "revision_history"))
            if not candidate_specific:
                raise RuntimeError(
                    "causal mutant failure has no candidate-specific diagnostic evidence")
        diagnostics["infrastructure_failure_excluded"] = True
        diagnostics["candidate_source_receipt_verified"] = True
        diagnostics["evaluator_returncode_verified"] = returncode
        return passed, diagnostics

    causal._specialized_passes = specialized_passes
    causal._failure_classification_hardening_installed = True
    return dict(handlers)
