#!/usr/bin/env python3
"""Final zero-provider static closure for protocol-v5 axis-probe calibration.

Runs the complete inherited causal/static proof and then binds the current owner ceremony,
preflight-v6, exhaustive 28-route calibration, and the exact imported v2 axis evaluator into the
causal static receipt consumed by the authoritative E2E driver.  This proof performs no provider
calls, candidate executions, Docker runs, or owner mutations.
"""
from __future__ import annotations

import hashlib
import importlib
import json
import os
import sys

import prove_observatory_protocol_static_v5 as previous

ROOT = previous.ROOT
REPORT = previous.REPORT
PROTOCOL_VERSION = "OBSERVATORY-OMEGA-RESEARCH-PROTOCOL-5"
PROBE_EVALUATOR = (
    "private-evaluator/evaluator/observatory_axis_probe_arena_v2.py")
REQUIRED_FILES = {
    "executable-orchestrator/lawmax21/observatory_setup_v5.py",
    "executable-orchestrator/lawmax21/observatory_preflight_v6.py",
    "private-evaluator/evaluator/observatory_axis_probe_arena.py",
    PROBE_EVALUATOR,
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


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _signed_semantic_minima(probe):
    pareto_path = _path("profiles/national-observatory/PARETO-DIMENSIONS.json")
    with open(pareto_path, encoding="utf-8") as handle:
        rows = json.load(handle)
    if not isinstance(rows, list):
        raise RuntimeError("owner-signed Pareto dimensions are not a JSON array")
    by_id = {
        row.get("id"): row for row in rows
        if isinstance(row, dict) and row.get("id")}
    expected = {}
    for dimension in probe._REQUIRED_SEMANTIC_DIMENSIONS:
        row = by_id.get(dimension) or {}
        value = row.get("hard_minimum")
        if row.get("direction") != "higher" \
                or not isinstance(value, (int, float)):
            raise RuntimeError(
                "owner-signed semantic hard minimum is invalid: " + dimension)
        expected[dimension] = float(value)
    if probe.SEMANTIC_HARD_MINIMA != expected:
        raise RuntimeError(
            "imported v2 evaluator hard minima differ from owner-signed Pareto minima")
    if os.path.realpath(probe.PARETO_PATH) != os.path.realpath(pareto_path):
        raise RuntimeError("v2 evaluator reads a different Pareto source")
    return expected


def _import_and_verify_v2_evaluator():
    evaluator_path = _path(PROBE_EVALUATOR)
    evaluator_dir = os.path.dirname(evaluator_path)
    if evaluator_dir not in sys.path:
        sys.path.insert(0, evaluator_dir)
    probe = importlib.import_module("observatory_axis_probe_arena_v2")
    if os.path.realpath(getattr(probe, "__file__", "")) != \
            os.path.realpath(evaluator_path):
        raise RuntimeError("v2 axis evaluator import resolved to the wrong file")
    minima = _signed_semantic_minima(probe)
    formal = probe.base.FORMAL_PROBE
    for token in (
            'manifest.get("commutative_independent_admissions") is True',
            '"derivation-order-claimed"',
            '"derivation-order-not-claimed"'):
        if token not in formal:
            raise RuntimeError(
                "v2 evaluator conditional-commutativity route lacks: " + token)
    if probe._OLD_DERIVATION in formal or probe._NEW_DERIVATION not in formal:
        raise RuntimeError(
            "v2 evaluator did not replace the unconditional derivation-order seat")
    if probe.base.PROBES.get("semantic") is not probe._semantic_probe \
            or probe.base.PROBES.get("formal") is not probe._formal_probe:
        raise RuntimeError("v2 evaluator probe routing is not load-bearing")
    size = os.path.getsize(evaluator_path)
    digest = _sha256(evaluator_path)
    if size <= 0 or len(digest) != 64:
        raise RuntimeError("v2 evaluator byte identity is malformed")
    return {
        "path": PROBE_EVALUATOR,
        "sha256": digest,
        "bytes": size,
        "semantic_dimensions": sorted(minima),
        "semantic_hard_minima": minima,
    }


def main():
    if previous.main() != 0:
        return 1
    receipt = json.load(open(REPORT, encoding="utf-8"))
    try:
        if receipt.get("status") != "PASS" \
                or receipt.get("protocol_version") != PROTOCOL_VERSION:
            raise RuntimeError("inherited static-v5 receipt is not PASS")

        from lawmax21 import observatory_protocol
        setup = importlib.import_module("lawmax21.observatory_setup_v5")
        preflight = importlib.import_module("lawmax21.observatory_preflight_v6")

        if observatory_protocol.MISSION_FLAGS.get(
                "axis_probe_calibration_required") is not True:
            raise RuntimeError(
                "owner-signed mission does not require axis-probe calibration")
        if tuple(setup.AXIS_PROBE_SOURCES) != tuple(preflight.AXIS_PROBE_SOURCES):
            raise RuntimeError(
                "setup-v5 and preflight-v6 use different axis calibration sources")
        if len(set(setup.AXIS_PROBE_SOURCES)) != 9 \
                or setup.AXIS_PROBE_REPORT != preflight.CALIBRATION_REPORT \
                or preflight.PROBE_EVALUATOR != PROBE_EVALUATOR:
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

        probe_source = _text(PROBE_EVALUATOR)
        _require(probe_source, (
            "PARETO-DIMENSIONS.json", "def _load_hard_minima",
            "SEMANTIC_HARD_MINIMA = _load_hard_minima()",
            "_ORIGINAL_FORMAL_PROBE", "def _formal_probe",
            "formal-axis-candidate-operation",
            "structured_candidate_failure",
            'base.PROBES["formal"] = _formal_probe',
            "commutative_independent_admissions",
            "derivation-order-claimed",
            "derivation-order-not-claimed"),
            "structured v2 axis-probe route")
        compile(probe_source, _path(PROBE_EVALUATOR), "exec")
        evaluator = _import_and_verify_v2_evaluator()

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
            "executable-orchestrator/tools/prove_complete_observatory_protocol_v5.py")
        _require(final, (
            "prove_complete_observatory_protocol_calibration_hardened",
            "prove_observatory_protocol_static_v6.py",
            "axis_probe_evaluator_v2_verified",
            "axis_probe_evaluator_imported",
            "axis_probe_evaluator_bytes_bound",
            "axis_probe_signed_hard_minima_verified",
            "axis_probe_conditional_commutativity_verified",
            "axis_probe_calibration_verified",
            "axis_probe_calibration_bound",
            "axis_probe_calibration_final_summary"),
            "authoritative final proof calibration binding")

        receipt.update({
            "status": "PASS",
            "protocol_version": observatory_protocol.PROTOCOL_VERSION,
            "protocol_bundle_sha256":
                observatory_protocol.protocol_bundle_sha256(ROOT),
            "axis_probe_evaluator_v2_verified": True,
            "axis_probe_evaluator_imported": True,
            "axis_probe_evaluator_bytes_bound": True,
            "axis_probe_signed_hard_minima_verified": True,
            "axis_probe_conditional_commutativity_verified": True,
            "axis_probe_evaluator_path": evaluator["path"],
            "axis_probe_evaluator_sha256": evaluator["sha256"],
            "axis_probe_evaluator_bytes": evaluator["bytes"],
            "axis_probe_semantic_dimensions": evaluator["semantic_dimensions"],
            "axis_probe_semantic_hard_minima": evaluator["semantic_hard_minima"],
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
            "axis_probe_calibration_sources": list(setup.AXIS_PROBE_SOURCES),
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
