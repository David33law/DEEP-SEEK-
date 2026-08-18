"""Final protocol preflight with exhaustive axis-probe calibration verification.

The inherited preflight verifies the signed mission, full protocol bundle, Pareto census, prior art and
all specialized campaigns. This layer additionally reopens every one of the 28 axis-probe calibration
pairs, rehashes all 56 reports and 28 controlled mutant sources, verifies the six exact reference
sources and the v2 evaluator bytes, and rejects launch if any baseline/mutant route is missing, reused
or was transported through anything other than strict UTF-8.
"""
from __future__ import annotations

import json
import os

from . import observatory_preflight_v2 as core
from . import observatory_preflight_v5 as base
from . import observatory_protocol
from .canonical import read_json


PROBE_CONTRACT = "observatory-axis-probe-v1"
PROBE_EVALUATOR = (
    "private-evaluator/evaluator/observatory_axis_probe_arena_v2.py")
CALIBRATION_REPORT = "proof/axis-probe-reference-calibration.json"
AXIS_PROBE_SOURCES = (
    "benchmark/observatory_reference_candidate.py",
    "benchmark/observatory_systems_reference_candidate.py",
    "benchmark/observatory_distributed_reference_candidate.py",
    "benchmark/observatory_scale_reference_candidate.py",
    "benchmark/observatory_formal_reference_candidate.py",
    "benchmark/observatory_interoperability_reference_candidate.py",
    "private-evaluator/evaluator/observatory_axis_probe_arena.py",
    PROBE_EVALUATOR,
    "private-evaluator/evaluator/observatory_axis_probe_calibration.py",
)
core.SPECIALIZED["axis_probe"] = AXIS_PROBE_SOURCES

PreflightFailed = base.PreflightFailed
_ORIGINAL_RUN = base.run


def _inside(root, relative):
    path = os.path.abspath(os.path.join(
        root, *str(relative).replace("\\", "/").split("/")))
    root = os.path.abspath(root)
    if path != root and not path.startswith(root + os.sep):
        raise RuntimeError(
            "axis-probe calibration evidence escapes repository: "
            + str(relative))
    return path


def _hex64(value):
    return isinstance(value, str) and len(value) == 64 \
        and all(char in "0123456789abcdef" for char in value.lower())


def _hash_bound(root, relative, expected, label):
    if not relative or not _hex64(expected):
        raise RuntimeError(label + " lacks path/SHA-256")
    path = _inside(root, relative)
    if not os.path.isfile(path):
        raise RuntimeError(label + " is missing: " + str(relative))
    actual = observatory_protocol.file_sha256(path)
    if actual != expected:
        raise RuntimeError(label + " hash drift: " + str(relative))
    return path


def _report_valid(report, baseline, reference_sha, mutant_sha,
                  group, axis, probe_id, seed, expected_sha):
    checks = report.get("checks") or []
    expected_candidate = reference_sha if baseline else mutant_sha
    common = bool(
        report.get("contract") == PROBE_CONTRACT
        and report.get("valid_execution") is True
        and report.get("group") == group
        and report.get("axis") == axis
        and report.get("probe_id") == probe_id
        and report.get("seed") == seed
        and report.get("expected_sha256") == expected_sha
        and report.get("candidate_sha256") == expected_candidate
        and report.get("calibration_transport_encoding") == "utf-8"
        and isinstance(checks, list) and checks
        and all(isinstance(row, dict)
                and isinstance(row.get("passed"), bool)
                for row in checks))
    if baseline:
        return bool(
            common
            and report.get("status") == "PASS"
            and report.get("passed") is True
            and report.get("failure_origin") == "none"
            and report.get("calibration_process_returncode") == 0
            and all(row["passed"] is True for row in checks))
    return bool(
        common
        and report.get("status") == "FAIL"
        and report.get("passed") is False
        and report.get("failure_origin") == "candidate_axis_behavior"
        and report.get("calibration_process_returncode") == 1
        and any(row["passed"] is False for row in checks))


def _axis_probe_calibration(root):
    report_path = _inside(root, CALIBRATION_REPORT)
    if not os.path.isfile(report_path):
        raise RuntimeError(
            "axis-probe calibration report is missing; rerun setup_observatory.py")
    report = read_json(report_path)
    evaluator = report.get("evaluator") or {}
    evaluator_path = _hash_bound(
        root, evaluator.get("path"), evaluator.get("sha256"),
        "axis-probe evaluator")
    if evaluator.get("path") != PROBE_EVALUATOR \
            or evaluator.get("bytes") != os.path.getsize(evaluator_path) \
            or report.get("status") != "PASS" \
            or report.get("passed") is not True \
            or report.get("axis_probe_contract") != PROBE_CONTRACT \
            or report.get("transport_encoding") != "utf-8" \
            or report.get("failed_route") not in (None, {}, []) \
            or report.get("provider_calls") != 0 \
            or int(report.get("axis_routes", 0)) != 28 \
            or int(report.get("valid_probe_pairs", 0)) != 28 \
            or int(report.get("baseline_reports", 0)) != 28 \
            or int(report.get("mutant_reports", 0)) != 28:
        raise RuntimeError("axis-probe calibration aggregate receipt is incomplete")

    pairs = report.get("pairs") or []
    if len(pairs) != 28:
        raise RuntimeError("axis-probe calibration does not contain 28 pairs")
    identities = set()
    routes = set()
    evidence_paths = set()
    references = set()
    for pair in pairs:
        identity = pair.get("task_identity_sha256")
        route = (pair.get("group"), pair.get("axis"))
        if not _hex64(identity) or identity in identities or route in routes:
            raise RuntimeError(
                "axis-probe calibration has duplicate/invalid task identity or route")
        identities.add(identity); routes.add(route)
        reference_relative = pair.get("reference_path")
        reference_path = _hash_bound(
            root, reference_relative, pair.get("reference_sha256"),
            f"axis-probe reference {route}")
        references.add(reference_relative)
        mutant_source = _hash_bound(
            root, pair.get("mutant_source_path"),
            pair.get("mutant_source_sha256"),
            f"axis-probe mutant source {route}")
        baseline_path = _hash_bound(
            root, pair.get("baseline_report_path"),
            pair.get("baseline_report_sha256"),
            f"axis-probe baseline report {route}")
        mutant_path = _hash_bound(
            root, pair.get("mutant_report_path"),
            pair.get("mutant_report_sha256"),
            f"axis-probe mutant report {route}")
        for relative in (
                pair.get("mutant_source_path"),
                pair.get("baseline_report_path"),
                pair.get("mutant_report_path")):
            if relative in evidence_paths:
                raise RuntimeError(
                    "axis-probe calibration reuses evidence across routes: "
                    + str(relative))
            evidence_paths.add(relative)
        baseline = read_json(baseline_path)
        mutant = read_json(mutant_path)
        probe_id = pair.get("probe_id")
        seed = pair.get("seed")
        expected_sha = pair.get("expected_sha256")
        reference_sha = pair.get("reference_sha256")
        mutant_sha = pair.get("mutant_source_sha256")
        if reference_sha == mutant_sha \
                or pair.get("mutation_symbol") not in open(
                    mutant_source, encoding="utf-8").read() \
                or not _report_valid(
                    baseline, True, reference_sha, mutant_sha,
                    route[0], route[1], probe_id, seed, expected_sha) \
                or not _report_valid(
                    mutant, False, reference_sha, mutant_sha,
                    route[0], route[1], probe_id, seed, expected_sha):
            raise RuntimeError(
                f"axis-probe calibration pair is invalid: {route}")
        failed = sorted(
            str(row.get("id")) for row in mutant.get("checks") or []
            if row.get("passed") is False)
        if failed != sorted(pair.get("mutant_failed_checks") or []):
            raise RuntimeError(
                f"axis-probe calibration failed-check receipt drift: {route}")

    expected_references = {
        relative for relative in AXIS_PROBE_SOURCES
        if relative.startswith("benchmark/")}
    if references != expected_references \
            or len(evidence_paths) != 84:
        raise RuntimeError(
            "axis-probe calibration reference/evidence census is incomplete")
    return {
        "path": CALIBRATION_REPORT,
        "sha256": observatory_protocol.file_sha256(report_path),
        "axis_probe_contract": PROBE_CONTRACT,
        "evaluator_path": PROBE_EVALUATOR,
        "evaluator_sha256": evaluator["sha256"],
        "transport_encoding": "utf-8",
        "axis_routes": len(routes),
        "valid_probe_pairs": len(pairs),
        "evidence_files": len(evidence_paths),
        "reference_sources": sorted(references),
        "provider_calls": 0,
    }


def run(root, orchestrator_root, runtime, require_vault=True,
        owner_public=None, backend=None):
    report = _ORIGINAL_RUN(
        root, orchestrator_root, runtime,
        require_vault=require_vault,
        owner_public=owner_public, backend=backend)
    try:
        calibration = _axis_probe_calibration(root)
    except Exception as exc:
        raise PreflightFailed(
            "Observatory protocol preflight refused to launch:\n  - "
            "axis_probe_calibration: " + str(exc)) from exc
    report.setdefault("research_protocol", {})[
        "axis_probe_calibration"] = calibration
    report["ok"] = not report.get("problems")
    return report


__all__ = [
    "PreflightFailed", "run", "AXIS_PROBE_SOURCES",
    "CALIBRATION_REPORT", "PROBE_EVALUATOR",
]
