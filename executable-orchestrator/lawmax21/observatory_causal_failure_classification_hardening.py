"""Classify causal-ablation evaluator outcomes conservatively.

A failing mutant is evidence only when the signed evaluator actually ran against the exact mutated
source and returned either a completed behavioral failure record or an explicit candidate-origin
exception. Missing container engines, process/container exits, isolation refusal, parent timeout,
resource exhaustion, output truncation, missing reports and harness transport failures invalidate the
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
    "cannot connect to docker",
    "error during connect",
    "permission denied while trying to connect",
    "isolation unavailable",
    "bounded evaluator produced no report",
    "streaming formal evaluator produced no report",
    "evaluator produced no report",
    "produced no report",
    "formal arena produced no json report",
    "container failed or flooded output",
    "container exited",
    "output limit exceeded",
    "exceeded bounded stdout",
    "exceeded bounded stderr",
    "child exceeded bounded",
    "stdout limit",
    "stderr limit",
    "timeoutexpired",
    "timed out after",
    "timed out",
    "process timeout",
    "image pull",
    "manifest unknown",
    "no such image",
    "failed to create shim",
    "out of memory",
    "memory limit",
    "oom-kill",
    "oomkilled",
    "exit code 137",
    "exited 137",
    "signal 9",
)

_CANDIDATE_FAILURE_MARKERS = (
    "candidate error",
    "candidate returned no",
    "candidate produced no",
    "missing open_system",
    "missing open_cluster",
    "missing open_scale_system",
    "missing functions",
    "missing interoperability_manifest",
    "missing project",
    "manifest mismatch",
    "genome mismatch",
    "nameerror:",
    "keyerror:",
    "attributeerror:",
    "syntaxerror:",
    "runtimeerror: missing",
)

_STRUCTURED_FAILURE_FIELDS = (
    "tests",
    "counterexamples",
    "failures",
    "diagnostics",
    "traceback",
    "errors",
    "revision_history",
    "directed",
)


def _diagnostic_text(report):
    keys = (
        "reason", "error", "stderr", "stderr_tail", "stdout_tail",
        "evaluator_stdout_tail", "evaluator_stderr_tail")
    return " ".join(str(report.get(key) or "") for key in keys)


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
        reason_text = _diagnostic_text(report)
        lowered = reason_text.lower()
        infrastructure_marker = next(
            (value for value in _INFRASTRUCTURE_MARKERS if value in lowered),
            None)
        if infrastructure_marker:
            raise RuntimeError(
                "causal evaluator infrastructure failure is non-evidence: "
                + infrastructure_marker)

        passed, diagnostics = original(report)
        diagnostics.update({
            "infrastructure_failure_excluded": True,
            "candidate_source_receipt_verified": True,
            "evaluator_returncode_verified": returncode,
        })
        if passed:
            if returncode != 0:
                raise RuntimeError(
                    "causal negative control reports PASS with nonzero evaluator return code")
            diagnostics["failure_origin"] = "none-control-passed"
            return passed, diagnostics

        if status != "FAIL" or report.get("passed", False) is not False:
            raise RuntimeError(
                "causal mutant failure is not an explicit candidate FAIL receipt")
        if returncode == 0:
            raise RuntimeError(
                "causal mutant reports FAIL with zero evaluator return code")

        structured_fields = sorted(
            key for key in _STRUCTURED_FAILURE_FIELDS
            if report.get(key) not in (None, {}, [], ""))
        candidate_marker = next(
            (value for value in _CANDIDATE_FAILURE_MARKERS
             if value in lowered), None)
        if not structured_fields and not candidate_marker:
            raise RuntimeError(
                "causal mutant failure has no candidate-specific diagnostic evidence")
        diagnostics.update({
            "failure_origin": "candidate",
            "structured_failure_fields": structured_fields,
            "matched_candidate_failure_marker": candidate_marker,
            "process_witness_present": bool(
                report.get("evaluator_stdout_tail")
                or report.get("evaluator_stderr_tail")),
        })
        return passed, diagnostics

    causal._specialized_passes = specialized_passes
    causal._failure_classification_hardening_installed = True
    return dict(handlers)
