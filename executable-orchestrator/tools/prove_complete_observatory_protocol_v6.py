#!/usr/bin/env python3
"""Authoritative protocol-v6 proof wrapper for the protocol-v5 Observatory mission.

The mission/protocol version remains Observatory Research Protocol 5.  This proof seat advances the
verification chain: static-v7 must close calibrated fault topology, the dynamic E2E must pass through
the actual-container fault verifier, and the final receipt must contain durable reference calibration,
durable crown and distributed crown runtime-kill evidence.  No real provider route is changed.
"""
from __future__ import annotations

import json
import os
import sys

import prove_complete_observatory_protocol_fault_hardened as fault_e2e
import prove_complete_observatory_protocol_v5 as base

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
STATIC_V7 = os.path.join(HERE, "prove_observatory_protocol_static_v7.py")
STATIC_V7_REPORT = os.path.join(ROOT, "proof", "observatory-protocol-static-v7.json")
E2E_REPORT = base.E2E_REPORT
PROTOCOL_VERSION = "OBSERVATORY-OMEGA-RESEARCH-PROTOCOL-5"

# The inherited final proof remains the complete causal/axis/calibration closure.  Replace only its
# static and dynamic extension seats with strictly stronger wrappers.
base.STATIC = STATIC_V7
base.e2e = fault_e2e

REQUIRED_STATIC_V7_GATES = (
    "systems_reference_calibration_static_bound",
    "systems_preflight_calibration_static_bound",
    "systems_signed_workload_static_bound",
    "systems_crash_workload_static_bound",
    "systems_contract_v2_static_bound",
    "systems_actual_container_crash_static_bound",
    "systems_authority_manifest_static_bound",
    "distributed_actual_container_crash_static_bound",
    "distributed_authority_files_static_bound",
    "distributed_baseline_metric_static_bound",
    "distributed_atomic_batch_reference_static_bound",
    "distributed_crash_floor_static_bound",
    "fault_evaluator_production_routing_static_bound",
)


def _read(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _fail(report, reason):
    report["status"] = "FAIL"
    report["final_closure_verified"] = False
    report["final_closure_v6_verified"] = False
    report["final_closure_reason"] = reason
    base._atomic_write(E2E_REPORT, report)
    print(json.dumps(report, ensure_ascii=False, indent=1, sort_keys=True))
    return 1


def main(argv=None):
    code = base.main(argv)
    if code != 0:
        return code
    if not os.path.isfile(E2E_REPORT) or not os.path.isfile(STATIC_V7_REPORT):
        print("protocol-v6 proof lacks final/static-v7 report", file=sys.stderr)
        return 1

    report = _read(E2E_REPORT)
    try:
        if report.get("status") != "PASS" \
                or report.get("protocol_version") != PROTOCOL_VERSION \
                or report.get("final_closure_verified") is not True:
            raise RuntimeError("inherited final protocol-v5 closure is not PASS")

        static = _read(STATIC_V7_REPORT)
        missing = [
            key for key in REQUIRED_STATIC_V7_GATES
            if static.get(key) is not True]
        if static.get("status") != "PASS" \
                or static.get("protocol_version") != PROTOCOL_VERSION \
                or missing:
            raise RuntimeError(
                "static-v7 fault closure incomplete: " + ", ".join(missing))

        verification = report.get("protocol_verification") or {}
        calibration = verification.get(
            "systems_reference_calibration_verified") or {}
        systems = verification.get(
            "systems_actual_container_crown_verified") or {}
        distributed = verification.get(
            "distributed_actual_container_crown_verified") or {}
        if verification.get("fault_injection_actual_container_verified") is not True \
                or calibration.get("status") != "PASS" \
                or systems.get("status") != "PASS" \
                or distributed.get("status") != "PASS":
            raise RuntimeError(
                "dynamic actual-container fault verification is incomplete")

        for label, row in (
                ("systems calibration", calibration),
                ("systems crown", systems),
                ("distributed crown", distributed)):
            crash = row.get("crash") or {}
            if crash.get("runtime_kill_succeeded") is not True \
                    or crash.get("container_absent_before_recovery") is not True \
                    or crash.get("cli_process_kill_counts_as_evidence") is not False \
                    or int(crash.get("runtime_kill_returncode", -1)) != 0:
                raise RuntimeError(label + " lacks final runtime-kill evidence")

        protocol_files = set(
            (report.get("run_summary") or {}).get("research_protocol_files") or [])
        # run_summary implementations need not repeat the full census; static-v7 and signed D09 own
        # that identity.  The final receipt therefore records the authoritative seats explicitly.
        report["authoritative_entrypoint"] = (
            "prove_complete_observatory_protocol_v6.py")
        report["static_v7_fault_closure"] = {
            "status": static["status"],
            "protocol_bundle_sha256": static.get("protocol_bundle_sha256"),
            **{key: static.get(key) for key in REQUIRED_STATIC_V7_GATES},
            "report_sha256": fault_e2e.sha256_file(STATIC_V7_REPORT),
        }
        report["systems_reference_calibration_bound"] = True
        report["systems_actual_container_crown_bound"] = True
        report["distributed_actual_container_crown_bound"] = True
        report["fault_injection_actual_container_bound"] = True
        report["systems_reference_calibration"] = calibration
        report["systems_actual_container_crown"] = systems
        report["distributed_actual_container_crown"] = distributed
        report["cli_process_death_cannot_earn_fault_credit"] = True
        report["final_closure_v6_verified"] = True
        report["final_closure_verified"] = True
        base._atomic_write(E2E_REPORT, report)
        return 0
    except Exception as exc:
        return _fail(report, f"{type(exc).__name__}: {exc}")


if __name__ == "__main__":
    sys.exit(main())
