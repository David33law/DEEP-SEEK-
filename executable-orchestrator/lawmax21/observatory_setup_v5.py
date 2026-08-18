"""Final owner-ceremony wrapper with exhaustive axis-probe calibration.

The inherited setup performs semantic, durable, distributed, scale, formal and interoperability
calibration and writes the owner-signed protocol receipt. This layer then executes all 28 trusted
axis-probe routes against passing references and controlled candidate-origin failures, and appends the
exact source/report hashes to the same zero-provider-call calibration receipt.
"""
from __future__ import annotations

import os

from . import observatory_protocol
from . import observatory_setup as core
from . import observatory_setup_v4 as base
from .canonical import atomic_write_json, read_json


AXIS_PROBE_SOURCES = (
    "benchmark/observatory_reference_candidate.py",
    "benchmark/observatory_systems_reference_candidate.py",
    "benchmark/observatory_distributed_reference_candidate.py",
    "benchmark/observatory_scale_reference_candidate.py",
    "benchmark/observatory_formal_reference_candidate.py",
    "benchmark/observatory_interoperability_reference_candidate.py",
    "private-evaluator/evaluator/observatory_axis_probe_arena.py",
    "private-evaluator/evaluator/observatory_axis_probe_arena_v2.py",
    "private-evaluator/evaluator/observatory_axis_probe_calibration.py",
)
AXIS_PROBE_REPORT = "proof/axis-probe-reference-calibration.json"
_ORIGINAL_CALIBRATE = core._calibrate_specialized_references


def _path(relative):
    return os.path.join(core.ROOT, *relative.split("/"))


def _calibrate():
    visible = _ORIGINAL_CALIBRATE()
    report_path = _path(AXIS_PROBE_REPORT)
    evidence_dir = _path("proof/axis-probe-calibration-evidence")
    core._run([
        _path("private-evaluator/evaluator/observatory_axis_probe_calibration.py"),
        "--out", report_path,
        "--evidence-dir", evidence_dir,
        "--timeout", "1800",
    ], timeout=43200)
    report = core._assert_report(report_path, "axis_probe")
    if report.get("axis_probe_contract") != "observatory-axis-probe-v1" \
            or int(report.get("axis_routes", 0)) != 28 \
            or int(report.get("valid_probe_pairs", 0)) != 28 \
            or int(report.get("baseline_reports", 0)) != 28 \
            or int(report.get("mutant_reports", 0)) != 28 \
            or len(report.get("pairs") or []) != 28 \
            or report.get("provider_calls") != 0:
        raise RuntimeError(
            "axis-probe calibration did not close all 28 zero-provider routes")

    receipt_path = os.path.join(
        core.PROOF, "observatory-specialized-calibration-receipt.json")
    receipt = read_json(receipt_path)
    sources = receipt.setdefault("sources", {})
    campaigns = receipt.setdefault("campaigns", {})
    sources["axis_probe"] = {
        relative: observatory_protocol.file_sha256(_path(relative))
        for relative in AXIS_PROBE_SOURCES}
    campaigns["axis_probe"] = {
        "status": report["status"],
        "passed": report["passed"],
        "report_path": AXIS_PROBE_REPORT,
        "report_sha256": observatory_protocol.file_sha256(report_path),
        "axis_probe_contract": report["axis_probe_contract"],
        "axis_routes": report["axis_routes"],
        "valid_probe_pairs": report["valid_probe_pairs"],
        "baseline_reports": report["baseline_reports"],
        "mutant_reports": report["mutant_reports"],
        "provider_calls": report["provider_calls"],
        "evaluator_sha256": (report.get("evaluator") or {}).get("sha256"),
    }
    receipt["protocol_bundle_sha256"] = (
        observatory_protocol.protocol_bundle_sha256(core.ROOT))
    receipt["provider_calls"] = 0
    atomic_write_json(receipt_path, receipt)
    visible["axis_probe"] = {
        "status": report["status"],
        "axis_routes": report["axis_routes"],
        "valid_probe_pairs": report["valid_probe_pairs"],
        "report": AXIS_PROBE_REPORT,
    }
    return visible


core._calibrate_specialized_references = _calibrate
main = base.main

__all__ = ["main", "AXIS_PROBE_SOURCES", "AXIS_PROBE_REPORT"]
