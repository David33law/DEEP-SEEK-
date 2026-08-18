#!/usr/bin/env python3
"""Exhaustive axis-probe calibration extension of the protocol-v5 Docker E2E proof.

The inherited axis proof verifies every runtime baseline/mutant causal pair and the exact v2 evaluator
bytes. This wrapper requires an owner-signed calibration mandate, independently reopens the owner-
ceremony calibration in the disposable clone, rehashes its 56 reports, 28 controlled mutant sources,
six references and evaluator, compares them with preflight-v6, requires strict UTF-8 transport on
every report, and requires zero provider calls.
"""
from __future__ import annotations

import json
import os

import prove_complete_observatory_protocol_axis_hardened as previous

CORE = previous.CORE
PROBE_CONTRACT = "observatory-axis-probe-v1"
PROBE_EVALUATOR = (
    "private-evaluator/evaluator/observatory_axis_probe_arena_v2.py")
CALIBRATION_REPORT = "proof/axis-probe-reference-calibration.json"
CALIBRATION_RECEIPT = (
    "proof/observatory-specialized-calibration-receipt.json")
AXIS_PROBE_SOURCES = {
    "benchmark/observatory_reference_candidate.py",
    "benchmark/observatory_systems_reference_candidate.py",
    "benchmark/observatory_distributed_reference_candidate.py",
    "benchmark/observatory_scale_reference_candidate.py",
    "benchmark/observatory_formal_reference_candidate.py",
    "benchmark/observatory_interoperability_reference_candidate.py",
    "private-evaluator/evaluator/observatory_axis_probe_arena.py",
    PROBE_EVALUATOR,
    "private-evaluator/evaluator/observatory_axis_probe_calibration.py",
}
CALIBRATION_FILES = {
    "executable-orchestrator/lawmax21/observatory_setup_v5.py",
    "executable-orchestrator/lawmax21/observatory_preflight_v6.py",
    "executable-orchestrator/lawmax21/observatory_utf8_process.py",
    "executable-orchestrator/tools/"
    "prove_complete_observatory_protocol_calibration_hardened.py",
    *AXIS_PROBE_SOURCES,
}
for relative in CALIBRATION_FILES:
    previous.AXIS_FILES.add(relative)
    previous.previous.base.CAUSAL_FILES.add(relative)
    CORE.REQUIRED_PROTOCOL_FILES.add(relative)
_ORIGINAL_VERIFY = CORE.verify_protocol


def _read(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _repo_path(repo, relative):
    path = os.path.abspath(os.path.join(
        repo, *str(relative).replace("\\", "/").split("/")))
    root = os.path.abspath(repo)
    if path != root and not path.startswith(root + os.sep):
        raise RuntimeError(
            "axis calibration E2E path escapes disposable clone: "
            + str(relative))
    return path


def _hex64(value):
    return isinstance(value, str) and len(value) == 64 \
        and all(char in "0123456789abcdef" for char in value.lower())


def _hash_bound(repo, relative, expected, label):
    if not relative or not _hex64(expected):
        raise RuntimeError(label + " lacks path/SHA-256")
    path = _repo_path(repo, relative)
    if not os.path.isfile(path) or CORE.sha256_file(path) != expected:
        raise RuntimeError(label + " hash drift: " + str(relative))
    return path


def _valid_pair_report(report, baseline, pair):
    checks = report.get("checks") or []
    expected_candidate = (
        pair.get("reference_sha256") if baseline
        else pair.get("mutant_source_sha256"))
    common = bool(
        report.get("contract") == PROBE_CONTRACT
        and report.get("valid_execution") is True
        and report.get("group") == pair.get("group")
        and report.get("axis") == pair.get("axis")
        and report.get("probe_id") == pair.get("probe_id")
        and report.get("seed") == pair.get("seed")
        and report.get("expected_sha256") == pair.get("expected_sha256")
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


def _verify_calibration(repo, preflight):
    mission = preflight.get("signed_mission") or {}
    if mission.get("axis_probe_calibration_required") is not True:
        raise RuntimeError(
            "owner-signed mission does not require axis-probe calibration")
    protocol = preflight.get("research_protocol") or {}
    preflight_receipt = protocol.get("axis_probe_calibration") or {}
    if preflight_receipt.get("axis_probe_contract") != PROBE_CONTRACT \
            or preflight_receipt.get("evaluator_path") != PROBE_EVALUATOR \
            or preflight_receipt.get("transport_encoding") != "utf-8" \
            or int(preflight_receipt.get("axis_routes", 0)) != 28 \
            or int(preflight_receipt.get("valid_probe_pairs", 0)) != 28 \
            or int(preflight_receipt.get("evidence_files", 0)) != 84 \
            or preflight_receipt.get("provider_calls") != 0:
        raise RuntimeError(
            "preflight-v6 did not close UTF-8 exhaustive axis-probe calibration")

    receipt_path = _repo_path(repo, CALIBRATION_RECEIPT)
    report_path = _repo_path(repo, CALIBRATION_REPORT)
    receipt = _read(receipt_path)
    report = _read(report_path)
    campaign = (receipt.get("campaigns") or {}).get("axis_probe") or {}
    sources = (receipt.get("sources") or {}).get("axis_probe") or {}
    if set(sources) != AXIS_PROBE_SOURCES:
        raise RuntimeError(
            "specialized receipt axis-probe source census drift")
    for relative, expected in sources.items():
        _hash_bound(repo, relative, expected,
                    "specialized axis-probe source")
    if campaign.get("status") != "PASS" \
            or campaign.get("passed") is not True \
            or campaign.get("report_path") != CALIBRATION_REPORT \
            or campaign.get("report_sha256") != CORE.sha256_file(report_path) \
            or campaign.get("axis_probe_contract") != PROBE_CONTRACT \
            or campaign.get("axis_routes") != 28 \
            or campaign.get("valid_probe_pairs") != 28 \
            or campaign.get("baseline_reports") != 28 \
            or campaign.get("mutant_reports") != 28 \
            or campaign.get("provider_calls") != 0:
        raise RuntimeError(
            "specialized axis-probe campaign receipt is incomplete")

    evaluator = report.get("evaluator") or {}
    evaluator_path = _hash_bound(
        repo, evaluator.get("path"), evaluator.get("sha256"),
        "axis-probe calibration evaluator")
    if evaluator.get("path") != PROBE_EVALUATOR \
            or evaluator.get("bytes") != os.path.getsize(evaluator_path) \
            or campaign.get("evaluator_sha256") != evaluator.get("sha256") \
            or preflight_receipt.get("evaluator_sha256") != evaluator.get("sha256"):
        raise RuntimeError(
            "axis-probe calibration evaluator bytes disagree")
    if report.get("status") != "PASS" \
            or report.get("passed") is not True \
            or report.get("axis_probe_contract") != PROBE_CONTRACT \
            or report.get("transport_encoding") != "utf-8" \
            or report.get("failed_route") not in (None, {}, []) \
            or report.get("provider_calls") != 0 \
            or report.get("axis_routes") != 28 \
            or report.get("valid_probe_pairs") != 28 \
            or report.get("baseline_reports") != 28 \
            or report.get("mutant_reports") != 28:
        raise RuntimeError("axis-probe aggregate UTF-8 calibration is not PASS")

    identities = set(); routes = set(); evidence = set(); references = set()
    pairs = report.get("pairs") or []
    if len(pairs) != 28:
        raise RuntimeError("axis-probe calibration pair count drift")
    for pair in pairs:
        identity = pair.get("task_identity_sha256")
        route = (pair.get("group"), pair.get("axis"))
        if not _hex64(identity) or identity in identities or route in routes:
            raise RuntimeError(
                "axis-probe calibration duplicate task identity/route")
        identities.add(identity); routes.add(route)
        references.add(pair.get("reference_path"))
        reference = _hash_bound(
            repo, pair.get("reference_path"),
            pair.get("reference_sha256"),
            f"axis calibration reference {route}")
        mutant_source = _hash_bound(
            repo, pair.get("mutant_source_path"),
            pair.get("mutant_source_sha256"),
            f"axis calibration mutant source {route}")
        baseline_path = _hash_bound(
            repo, pair.get("baseline_report_path"),
            pair.get("baseline_report_sha256"),
            f"axis calibration baseline {route}")
        mutant_path = _hash_bound(
            repo, pair.get("mutant_report_path"),
            pair.get("mutant_report_sha256"),
            f"axis calibration mutant {route}")
        for relative in (
                pair.get("mutant_source_path"),
                pair.get("baseline_report_path"),
                pair.get("mutant_report_path")):
            if relative in evidence:
                raise RuntimeError(
                    "axis calibration evidence reused across routes: "
                    + str(relative))
            evidence.add(relative)
        if pair.get("reference_sha256") == pair.get("mutant_source_sha256") \
                or not os.path.isfile(reference) \
                or pair.get("mutation_symbol") not in open(
                    mutant_source, encoding="utf-8").read():
            raise RuntimeError(
                f"axis calibration source mutation is invalid: {route}")
        baseline = _read(baseline_path); mutant = _read(mutant_path)
        if not _valid_pair_report(baseline, True, pair) \
                or not _valid_pair_report(mutant, False, pair) \
                or baseline.get("probe_id") != mutant.get("probe_id") \
                or baseline.get("seed") != mutant.get("seed") \
                or baseline.get("expected_sha256") != mutant.get(
                    "expected_sha256"):
            raise RuntimeError(
                f"axis calibration baseline/mutant pair failed: {route}")
        failed = sorted(
            str(row.get("id")) for row in mutant.get("checks") or []
            if row.get("passed") is False)
        if failed != sorted(pair.get("mutant_failed_checks") or []):
            raise RuntimeError(
                f"axis calibration failed-check receipt drift: {route}")

    expected_references = {
        relative for relative in AXIS_PROBE_SOURCES
        if relative.startswith("benchmark/")}
    if references != expected_references \
            or len(identities) != 28 \
            or len(routes) != 28 \
            or len(evidence) != 84:
        raise RuntimeError(
            "axis calibration final route/evidence census drift")
    if preflight_receipt.get("sha256") != CORE.sha256_file(report_path):
        raise RuntimeError(
            "preflight axis calibration report hash drift")
    return {
        "status": "PASS",
        "owner_signed_required": True,
        "axis_probe_contract": PROBE_CONTRACT,
        "evaluator_path": PROBE_EVALUATOR,
        "evaluator_sha256": evaluator["sha256"],
        "transport_encoding": "utf-8",
        "axis_routes": len(routes),
        "valid_probe_pairs": len(identities),
        "baseline_reports": len(routes),
        "mutant_reports": len(routes),
        "evidence_files": len(evidence),
        "report_path": CALIBRATION_REPORT,
        "report_sha256": CORE.sha256_file(report_path),
        "receipt_path": CALIBRATION_RECEIPT,
        "receipt_sha256": CORE.sha256_file(receipt_path),
        "provider_calls": 0,
    }


def _verify(repo, runtime, source_head, preflight, launch):
    verified = _ORIGINAL_VERIFY(
        repo, runtime, source_head, preflight, launch)
    verified["axis_probe_calibration_verified"] = _verify_calibration(
        repo, preflight)
    return verified


CORE.verify_protocol = _verify
main = previous.main
sha256_file = previous.sha256_file

__all__ = ["main", "sha256_file"]


if __name__ == "__main__":
    import sys
    sys.exit(main())
