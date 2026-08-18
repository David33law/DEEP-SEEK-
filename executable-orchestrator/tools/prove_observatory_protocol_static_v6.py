#!/usr/bin/env python3
"""Final static closure for protocol-v5 exhaustive axis-probe calibration.

Runs the complete causal/static v5 proof, then proves that the owner-signed mission requires
calibration, stable setup uses setup-v5, the production launcher binds preflight-v6, both seats share
the exact nine-file source census, the v2 evaluator loads signed minima and structured formal failure
checks, and the authoritative E2E/final proofs pass through calibration hardening. No provider call,
candidate execution, Docker run or owner mutation occurs here.
"""
from __future__ import annotations

import importlib
import json
import os
import sys

import prove_observatory_protocol_static_v5 as previous

ROOT = previous.ROOT
REPORT = previous.REPORT
PROTOCOL_VERSION = "OBSERVATORY-OMEGA-RESEARCH-PROTOCOL-5"
REQUIRED_FILES = {
    "executable-orchestrator/lawmax21/observatory_setup_v5.py",
    "executable-orchestrator/lawmax21/observatory_preflight_v6.py",
    "private-evaluator/evaluator/observatory_axis_probe_calibration.py",
    "executable-orchestrator/tools/"
    "prove_complete_observatory_protocol_calibration_hardened.py",
    "executable-orchestrator/tools/prove_observatory_protocol_static_v6.py",
}


def _path(relative):
    return os.path.join(ROOT, *relative.split("/"))


def _text(relative):
    with open(_path(relative), encoding="utf-8") as handle:
        return handle.read()


def _require(text, tokens, label):
    missing = [token for token in tokens if token not in text]
    if missing:
        raise RuntimeError(label + " lacks: " + ", ".join(missing))


def main():
    if previous.main() != 0:
        return 1
    receipt = json.load(open(REPORT, encoding="utf-8"))
    try:
        if receipt.get("status") != "PASS" \
                or receipt.get("protocol_version") != PROTOCOL_VERSION:
            raise RuntimeError("inherited static-v5 receipt is not PASS")
        from lawmax21 import observatory_protocol
        setup = importlib.import_module(
            "lawmax21.observatory_setup_v5")
        preflight = importlib.import_module(
            "lawmax21.observatory_preflight_v6")
        if observatory_protocol.MISSION_FLAGS.get(
                "axis_probe_calibration_required") is not True:
            raise RuntimeError(
                "owner-signed mission does not require axis-probe calibration")
        if tuple(setup.AXIS_PROBE_SOURCES) != tuple(
                preflight.AXIS_PROBE_SOURCES):
            raise RuntimeError(
                "setup-v5 and preflight-v6 use different axis calibration sources")
        if len(set(setup.AXIS_PROBE_SOURCES)) != 9 \
                or setup.AXIS_PROBE_REPORT != \
                preflight.CALIBRATION_REPORT \
                or preflight.PROBE_EVALUATOR != \
                "private-evaluator/evaluator/observatory_axis_probe_arena_v2.py":
            raise RuntimeError(
                "axis calibration source/report/evaluator policy drift")
        protocol_files = set(observatory_protocol.protocol_files(ROOT))
        omitted = sorted(REQUIRED_FILES - protocol_files)
        if omitted:
            raise RuntimeError(
                "protocol census omitted calibration closure files: "
                + ", ".join(omitted))
        specialized = tuple(preflight.core.SPECIALIZED.get("axis_probe") or ())
        if specialized != tuple(setup.AXIS_PROBE_SOURCES):
            raise RuntimeError(
                "preflight specialized-source census differs from setup-v5")

        stable_setup = _text("setup_observatory.py")
        _require(stable_setup, (
            "from lawmax21.observatory_setup_v5 import main",),
            "stable owner ceremony")
        setup_source = _text(
            "executable-orchestrator/lawmax21/observatory_setup_v5.py")
        _require(setup_source, (
            "AXIS_PROBE_SOURCES", "AXIS_PROBE_REPORT",
            "observatory_axis_probe_calibration.py",
            "valid_probe_pairs", "baseline_reports", "mutant_reports",
            '"provider_calls": report["provider_calls"]',
            "core._calibrate_specialized_references = _calibrate"),
            "owner ceremony axis calibration")
        launcher = _text(
            "executable-orchestrator/lawmax21/observatory_launcher_v3.py")
        _require(launcher, (
            "observatory_preflight_v6 as final_preflight",
            "_launcher.observatory_preflight = final_preflight",
            "_final_observatory_preflight_v6_bound"),
            "production launcher preflight-v6 binding")
        preflight_source = _text(
            "executable-orchestrator/lawmax21/observatory_preflight_v6.py")
        _require(preflight_source, (
            "core.SPECIALIZED[\"axis_probe\"] = AXIS_PROBE_SOURCES",
            "def _axis_probe_calibration",
            "axis_routes", "valid_probe_pairs", "evidence_files",
            "calibration_process_returncode",
            "axis_probe_calibration"),
            "preflight-v6 calibration verification")

        calibration = _text(
            "private-evaluator/evaluator/observatory_axis_probe_calibration.py")
        _require(calibration, (
            "GROUP_AXES", "REFERENCES", "EXPECTED", "MUTATIONS",
            "set(MUTATIONS)", "expected_pairs",
            "axis-probe baseline calibration failed",
            "axis-probe mutant calibration failed",
            '"provider_calls": 0',
            '"valid_probe_pairs": expected_pairs',
            '"baseline_reports": expected_pairs',
            '"mutant_reports": expected_pairs'),
            "28-route axis calibration suite")
        compile(calibration, _path(
            "private-evaluator/evaluator/observatory_axis_probe_calibration.py"),
            "exec")

        probe_v2 = _text(
            "private-evaluator/evaluator/observatory_axis_probe_arena_v2.py")
        _require(probe_v2, (
            "PARETO-DIMENSIONS.json", "def _load_hard_minima",
            "SEMANTIC_HARD_MINIMA = _load_hard_minima()",
            "_ORIGINAL_FORMAL_PROBE",
            "def _formal_probe",
            "formal-axis-candidate-operation",
            "structured_candidate_failure",
            'base.PROBES["formal"] = _formal_probe'),
            "structured v2 axis-probe route")
        compile(probe_v2, _path(
            "private-evaluator/evaluator/observatory_axis_probe_arena_v2.py"),
            "exec")

        e2e = _text(
            "executable-orchestrator/tools/"
            "prove_complete_observatory_protocol_calibration_hardened.py")
        _require(e2e, (
            "prove_complete_observatory_protocol_axis_hardened",
            "axis_probe_calibration_required",
            "AXIS_PROBE_SOURCES", "CALIBRATION_REPORT",
            "CALIBRATION_RECEIPT", "def _verify_calibration",
            "axis_probe_calibration_verified",
            "valid_probe_pairs", "evidence_files", "provider_calls"),
            "calibration-hardened Docker E2E")
        final = _text(
            "executable-orchestrator/tools/"
            "prove_complete_observatory_protocol_v5.py")
        _require(final, (
            "prove_complete_observatory_protocol_calibration_hardened",
            "prove_observatory_protocol_static_v6.py",
            "axis_probe_calibration_verified",
            "axis_probe_calibration_bound",
            "axis_probe_calibration_final_summary"),
            "authoritative final proof calibration binding")

        receipt.update({
            "status": "PASS",
            "protocol_version": observatory_protocol.PROTOCOL_VERSION,
            "protocol_bundle_sha256":
                observatory_protocol.protocol_bundle_sha256(ROOT),
            "axis_probe_calibration_static_bound": True,
            "axis_probe_calibration_preflight_bound": True,
            "axis_probe_calibration_e2e_bound": True,
            "axis_probe_calibration_owner_signed": True,
            "axis_probe_setup_v5_bound": True,
            "axis_probe_preflight_v6_bound": True,
            "axis_probe_structured_formal_failure_bound": True,
            "axis_probe_calibration_routes": 28,
            "axis_probe_calibration_expected_reports": 56,
            "axis_probe_calibration_expected_evidence_files": 84,
            "axis_probe_calibration_provider_calls": 0,
            "axis_probe_calibration_sources": list(
                setup.AXIS_PROBE_SOURCES),
            "axis_probe_calibration_report": setup.AXIS_PROBE_REPORT,
            "axis_probe_calibration_modules_imported": [
                setup.__name__, preflight.__name__],
        })
    except Exception as exc:
        receipt["status"] = "FAIL"
        receipt["reason"] = f"{type(exc).__name__}: {exc}"
    with open(REPORT, "w", encoding="utf-8") as handle:
        json.dump(receipt, handle, ensure_ascii=False,
                  indent=1, sort_keys=True)
    print(json.dumps(receipt, ensure_ascii=False,
                     indent=1, sort_keys=True))
    return 0 if receipt.get("status") == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
