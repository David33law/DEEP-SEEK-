#!/usr/bin/env python3
"""Fault-evidence extension of the calibrated Observatory Docker E2E proof.

This wrapper reopens the owner-ceremony durable systems calibration and the final durable/distributed
crown reports while the disposable proof clone/runtime still exist. A PASS requires actual runtime
container death during an in-flight operation, absence before recovery, complete durable manifest
evidence, exact signed proof workloads and the corrected distributed baseline metric.

The wrapper bootstraps ``executable-orchestrator`` before importing ``lawmax21`` so it is directly
executable from any working directory with no inherited PYTHONPATH.
"""
from __future__ import annotations

import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ORCH = os.path.dirname(HERE)
ROOT = os.path.dirname(ORCH)
LAWMAX_PACKAGE = os.path.join(ORCH, "lawmax21", "__init__.py")
if not os.path.isfile(LAWMAX_PACKAGE):
    raise RuntimeError("fault proof cannot locate lawmax21 package: " + LAWMAX_PACKAGE)
if ORCH not in sys.path:
    sys.path.insert(0, ORCH)

import prove_complete_observatory_protocol_calibration_hardened as previous
from lawmax21 import observatory_protocol

CORE = previous.CORE
_ORIGINAL_VERIFY = CORE.verify_protocol

SYSTEMS_REFERENCE = "benchmark/observatory_systems_reference_candidate.py"
SYSTEMS_EVALUATOR = "private-evaluator/evaluator/observatory_systems_arena_v2.py"
SYSTEMS_REPORT = "proof/systems-reference-calibration.json"
DISTRIBUTED_REPORT = "proof/distributed-reference-calibration.json"
CALIBRATION_RECEIPT = "proof/observatory-specialized-calibration-receipt.json"

FAULT_FILES = {
    "profiles/national-observatory/SYSTEMS-CONTRACT.md",
    "profiles/national-observatory/DISTRIBUTED-SYSTEMS-CONTRACT.md",
    "executable-orchestrator/lawmax21/observatory_protocol.py",
    "executable-orchestrator/lawmax21/observatory_workload_policy.py",
    "executable-orchestrator/lawmax21/observatory_setup_v3.py",
    "executable-orchestrator/lawmax21/observatory_preflight_v3.py",
    "executable-orchestrator/lawmax21/observatory_evaluator_routing_hardening.py",
    "private-evaluator/evaluator/observatory_systems_arena.py",
    SYSTEMS_EVALUATOR,
    "private-evaluator/evaluator/observatory_distributed_arena.py",
    "private-evaluator/evaluator/observatory_distributed_arena_v2.py",
    SYSTEMS_REFERENCE,
    "benchmark/observatory_distributed_reference_candidate.py",
    "executable-orchestrator/tools/prove_observatory_protocol_static_v7.py",
    "executable-orchestrator/tools/prove_complete_observatory_protocol_fault_hardened.py",
    "executable-orchestrator/tools/prove_complete_observatory_protocol_v6.py",
    "executable-orchestrator/tools/run_observatory_proof.py",
}
CORE.REQUIRED_PROTOCOL_FILES.update(FAULT_FILES)


def _read(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _repo_path(repo, relative):
    root = os.path.abspath(repo)
    path = os.path.abspath(os.path.join(
        root, *str(relative).replace("\\", "/").split("/")))
    if path != root and not path.startswith(root + os.sep):
        raise RuntimeError("fault proof path escapes disposable clone: " + str(relative))
    return path


def _runtime_path(runtime, relative):
    root = os.path.abspath(runtime)
    path = os.path.abspath(os.path.join(
        root, *str(relative).replace("\\", "/").split("/")))
    if path != root and not path.startswith(root + os.sep):
        raise RuntimeError("fault proof path escapes runtime: " + str(relative))
    return path


def _crash_evidence(report, label):
    evidence = report.get("whole_process_crash_evidence") or {}
    required_true = (
        "actual_container_kill_required",
        "mid_operation_kill_required",
        "container_started",
        "workload_delivered",
        "mid_operation_kill_verified",
        "runtime_kill_succeeded",
        "container_absent_before_recovery",
    )
    missing = [key for key in required_true if evidence.get(key) is not True]
    if missing \
            or evidence.get("operation_reply_observed_before_kill") is not False \
            or evidence.get("cli_process_kill_counts_as_evidence") is not False \
            or int(evidence.get("runtime_kill_returncode", -1)) != 0:
        raise RuntimeError(
            label + " lacks authoritative mid-operation container crash evidence: "
            + ", ".join(missing or ["reply/kill-returncode/CLI-credit"]))
    keys = (
        *required_true,
        "operation_reply_observed_before_kill",
        "runtime_kill_returncode",
        "cli_process_kill_counts_as_evidence",
    )
    out = {key: evidence.get(key) for key in keys}
    if "events_delivered" in evidence:
        out["events_delivered"] = evidence.get("events_delivered")
    return out


def _manifest_evidence(report, label):
    evidence = report.get("durable_manifest_evidence") or {}
    if evidence.get("authority_files_verified") is not True \
            or evidence.get("recovery_files_verified") is not True \
            or not evidence.get("declared_authority_files"):
        raise RuntimeError(label + " lacks complete durable manifest evidence")
    authority = [str(x) for x in evidence.get("declared_authority_files") or []]
    recovery = [str(x) for x in evidence.get("declared_recovery_files") or []]
    if len(authority + recovery) != len(set(authority + recovery)):
        raise RuntimeError(label + " aliases declared authority/recovery files")
    return {
        "authority_files": authority,
        "recovery_files": recovery,
        "authority_files_verified": True,
        "recovery_files_verified": True,
    }


def _verify_systems_calibration(repo, preflight):
    receipt_path = _repo_path(repo, CALIBRATION_RECEIPT)
    report_path = _repo_path(repo, SYSTEMS_REPORT)
    if not os.path.isfile(receipt_path) or not os.path.isfile(report_path):
        raise RuntimeError("systems reference calibration evidence is missing")
    receipt = _read(receipt_path)
    campaign = (receipt.get("campaigns") or {}).get("systems") or {}
    sources = (receipt.get("sources") or {}).get("systems") or {}
    expected_sources = {SYSTEMS_REFERENCE, SYSTEMS_EVALUATOR}
    if set(sources) != expected_sources:
        raise RuntimeError("systems calibration source census is not the exact v2 pair")
    for relative, expected in sources.items():
        path = _repo_path(repo, relative)
        if not os.path.isfile(path) or CORE.sha256_file(path) != expected:
            raise RuntimeError("systems calibration source hash drift: " + relative)
    if campaign.get("status") not in ("PASS", "OK") \
            or campaign.get("passed") is not True \
            or campaign.get("report_path") != SYSTEMS_REPORT \
            or campaign.get("report_sha256") != CORE.sha256_file(report_path):
        raise RuntimeError("systems specialized calibration receipt is not PASS/hash-bound")

    protocol = preflight.get("research_protocol") or {}
    specialized_sources = (protocol.get("specialized_sources") or {}).get("systems") or {}
    specialized_calibration = protocol.get("specialized_calibration") or {}
    if specialized_sources != sources \
            or "systems" not in set(specialized_calibration.get("campaigns") or []):
        raise RuntimeError("preflight did not independently bind systems calibration")

    report = _read(report_path)
    expected = observatory_protocol.PROOF_WORKLOADS["systems"]
    if report.get("status") != "PASS" or report.get("passed") is not True \
            or int(report.get("requested_large_events", -1)) != int(expected["qualification"]) \
            or int(report.get("requested_crash_events", -1)) != int(expected["crash_events"]):
        raise RuntimeError("systems reference calibration used the wrong proof workload")
    tests = report.get("tests") or {}
    if tests.get("crash_was_actually_observed") is not True \
            or tests.get("crash_restart_integrity") is not True:
        raise RuntimeError("systems reference calibration did not survive mid-operation process death")
    return {
        "status": "PASS",
        "report_path": SYSTEMS_REPORT,
        "report_sha256": CORE.sha256_file(report_path),
        "qualification_events": int(expected["qualification"]),
        "crash_events": int(expected["crash_events"]),
        "crash": _crash_evidence(report, "systems reference calibration"),
        "manifest": _manifest_evidence(report, "systems reference calibration"),
        "provider_calls": 0,
    }


def _verify_distributed_calibration(repo, preflight):
    receipt_path = _repo_path(repo, CALIBRATION_RECEIPT)
    report_path = _repo_path(repo, DISTRIBUTED_REPORT)
    if not os.path.isfile(receipt_path) or not os.path.isfile(report_path):
        raise RuntimeError("distributed reference calibration evidence is missing")
    receipt = _read(receipt_path)
    campaign = (receipt.get("campaigns") or {}).get("distributed") or {}
    sources = (receipt.get("sources") or {}).get("distributed") or {}
    expected_sources = {
        "benchmark/observatory_distributed_reference_candidate.py",
        "private-evaluator/evaluator/observatory_distributed_arena_v2.py",
    }
    if set(sources) != expected_sources:
        raise RuntimeError("distributed calibration source census is not the exact v2 pair")
    for relative, expected_sha in sources.items():
        path = _repo_path(repo, relative)
        if not os.path.isfile(path) or CORE.sha256_file(path) != expected_sha:
            raise RuntimeError("distributed calibration source hash drift: " + relative)
    protocol = preflight.get("research_protocol") or {}
    specialized_sources = (protocol.get("specialized_sources") or {}).get("distributed") or {}
    specialized_calibration = protocol.get("specialized_calibration") or {}
    if specialized_sources != sources \
            or "distributed" not in set(specialized_calibration.get("campaigns") or []):
        raise RuntimeError("preflight did not independently bind distributed calibration")
    if campaign.get("status") not in ("PASS", "OK") \
            or campaign.get("passed") is not True \
            or campaign.get("report_path") != DISTRIBUTED_REPORT \
            or campaign.get("report_sha256") != CORE.sha256_file(report_path):
        raise RuntimeError("distributed specialized calibration receipt is not PASS/hash-bound")
    report = _read(report_path)
    expected = observatory_protocol.PROOF_WORKLOADS["distributed"]
    crash = _crash_evidence(report, "distributed reference calibration")
    if report.get("status") != "PASS" or report.get("passed") is not True \
            or int(report.get("requested_crash_events", -1)) != int(expected["crash_events"]) \
            or int(crash.get("events_delivered", -1)) != int(expected["crash_events"]):
        raise RuntimeError("distributed reference calibration used the wrong crash workload")
    return {
        "status": "PASS",
        "report_path": DISTRIBUTED_REPORT,
        "report_sha256": CORE.sha256_file(report_path),
        "crash_events": int(expected["crash_events"]),
        "crash": crash,
        "provider_calls": 0,
    }


def _verify_systems_crown(runtime, incumbent):
    path = _runtime_path(
        runtime, f"reports/systems-crown-{incumbent}.json")
    if not os.path.isfile(path):
        raise RuntimeError("durable systems crown report is missing")
    report = _read(path)
    expected = observatory_protocol.PROOF_WORKLOADS["systems"]
    tests = report.get("tests") or {}
    if report.get("status") != "PASS" or report.get("passed") is not True \
            or tests.get("crash_was_actually_observed") is not True \
            or tests.get("crash_restart_integrity") is not True \
            or int(report.get("requested_large_events", -1)) != int(expected["crown"]) \
            or int(report.get("requested_crash_events", -1)) != int(expected["crash_events"]) \
            or int(report.get("owner_signed_large_events", -1)) != int(expected["crown"]) \
            or int(report.get("owner_signed_crash_events", -1)) != int(expected["crash_events"]):
        raise RuntimeError("durable systems crown workload/crash receipt is incomplete")
    return {
        "status": "PASS",
        "path": os.path.relpath(path, runtime).replace("\\", "/"),
        "sha256": CORE.sha256_file(path),
        "large_events": int(expected["crown"]),
        "crash_events": int(expected["crash_events"]),
        "crash": _crash_evidence(report, "durable systems crown"),
        "manifest": _manifest_evidence(report, "durable systems crown"),
    }


def _verify_distributed_crown(runtime, incumbent):
    path = _runtime_path(
        runtime, f"reports/distributed-crown-{incumbent}.json")
    if not os.path.isfile(path):
        raise RuntimeError("distributed crown report is missing")
    report = _read(path)
    expected = observatory_protocol.PROOF_WORKLOADS["distributed"]
    tests = report.get("tests") or {}
    baseline_events = int(report.get("baseline_events", 0))
    baseline_elapsed = float(report.get("baseline_elapsed_seconds", 0.0))
    observed_eps = float(report.get("events_per_second_baseline", 0.0))
    expected_eps = baseline_events / max(baseline_elapsed, 1e-9)
    crash = _crash_evidence(report, "distributed crown")
    if report.get("status") != "PASS" or report.get("passed") is not True \
            or tests.get("whole_process_crash_recovery") is not True \
            or int(report.get("owner_signed_large_events", -1)) != int(expected["crown"]) \
            or int(report.get("requested_crash_events", -1)) != int(expected["crash_events"]) \
            or int(report.get("owner_signed_crash_events", -1)) != int(expected["crash_events"]) \
            or int(crash.get("events_delivered", -1)) != int(expected["crash_events"]) \
            or baseline_events != 1000 or baseline_elapsed <= 0.0 \
            or not math.isclose(observed_eps, expected_eps, rel_tol=1e-12, abs_tol=1e-12) \
            or float(report.get("campaign_elapsed_seconds", 0.0)) < baseline_elapsed:
        raise RuntimeError("distributed crown crash/baseline receipt is incomplete")
    return {
        "status": "PASS",
        "path": os.path.relpath(path, runtime).replace("\\", "/"),
        "sha256": CORE.sha256_file(path),
        "large_events": int(expected["crown"]),
        "crash_events": int(expected["crash_events"]),
        "baseline_events": baseline_events,
        "baseline_elapsed_seconds": baseline_elapsed,
        "events_per_second_baseline": observed_eps,
        "campaign_elapsed_seconds": report.get("campaign_elapsed_seconds"),
        "crash": crash,
    }


def _verify(repo, runtime, source_head, preflight, launch):
    verified = _ORIGINAL_VERIFY(
        repo, runtime, source_head, preflight, launch)
    summary = CORE.read_json(os.path.join(runtime, "reports", "run_summary.json"))
    incumbent = (summary.get("escalation") or {}).get("incumbent")
    if not incumbent:
        raise RuntimeError("fault verifier cannot resolve committed incumbent")
    verified["systems_reference_calibration_verified"] = (
        _verify_systems_calibration(repo, preflight))
    verified["distributed_reference_calibration_verified"] = (
        _verify_distributed_calibration(repo, preflight))
    verified["systems_actual_container_crown_verified"] = (
        _verify_systems_crown(runtime, incumbent))
    verified["distributed_actual_container_crown_verified"] = (
        _verify_distributed_crown(runtime, incumbent))
    verified["fault_injection_actual_container_verified"] = True
    verified["fault_injection_mid_operation_verified"] = True
    verified["fault_workloads_owner_bound_verified"] = True
    return verified


CORE.verify_protocol = _verify
main = previous.main
sha256_file = previous.sha256_file

__all__ = ["main", "sha256_file"]


if __name__ == "__main__":
    sys.exit(main())
