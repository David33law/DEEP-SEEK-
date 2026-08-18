#!/usr/bin/env python3
"""Authoritative protocol-v6 proof wrapper for the protocol-v5 Observatory mission.

The mission/protocol version remains Observatory Research Protocol 5. Static-v8 strictly extends the
calibrated static-v7 fault topology with standalone cwd/PYTHONPATH-independent import closure,
mechanically proves every retired/public proof command is a monotonic shim to this v6 authority, and
proves locale-independent strict UTF-8 trusted process transport with host-codec failures excluded
from causal evidence. Dynamic closure independently requires UTF-8 on exhaustive calibration,
runtime causal axis pairs and actual-container fault campaigns.

The wrapper bootstraps the repository-local ``lawmax21`` package before importing any proof extension,
so direct execution is independent of the caller's current working directory and PYTHONPATH.
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ORCH = os.path.dirname(HERE)
ROOT = os.path.dirname(ORCH)
LAWMAX_PACKAGE = os.path.join(ORCH, "lawmax21", "__init__.py")
if not os.path.isfile(LAWMAX_PACKAGE):
    raise RuntimeError("protocol-v6 cannot locate lawmax21 package: " + LAWMAX_PACKAGE)
if ORCH not in sys.path:
    sys.path.insert(0, ORCH)

import prove_complete_observatory_protocol_fault_hardened as fault_e2e
import prove_complete_observatory_protocol_v5 as base

STATIC_V8 = os.path.join(HERE, "prove_observatory_protocol_static_v8.py")
STATIC_V8_REPORT = os.path.join(ROOT, "proof", "observatory-protocol-static-v8.json")
E2E_REPORT = base.E2E_REPORT
PROTOCOL_VERSION = "OBSERVATORY-OMEGA-RESEARCH-PROTOCOL-5"

base.STATIC = STATIC_V8
base.e2e = fault_e2e

REQUIRED_STATIC_V8_GATES = (
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
    "distributed_crash_workload_static_bound",
    "distributed_contract_signed_crash_static_bound",
    "fault_evaluator_production_routing_static_bound",
    "fault_mid_operation_crash_static_bound",
    "fault_exact_workloads_static_bound",
    "authoritative_fault_final_entry_static_bound",
    "authoritative_entrypoint_standalone_import_static_bound",
    "compatibility_proof_shims_monotonic_static_bound",
    "trusted_utf8_process_static_bound",
    "production_evaluator_utf8_static_bound",
    "axis_probe_utf8_transport_static_bound",
    "axis_calibration_utf8_static_bound",
    "fault_crash_utf8_static_bound",
    "e2e_utf8_transport_static_bound",
    "host_unicode_failure_noncausal_static_bound",
    "utf8_unicode_roundtrip_static_bound",
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
    print(json.dumps(report, ensure_ascii=True, indent=1, sort_keys=True))
    return 1


def main(argv=None):
    code = base.main(argv)
    if code != 0:
        return code
    if not os.path.isfile(E2E_REPORT) or not os.path.isfile(STATIC_V8_REPORT):
        print("protocol-v6 proof lacks final/static-v8 report", file=sys.stderr)
        return 1

    report = _read(E2E_REPORT)
    try:
        if report.get("status") != "PASS" \
                or report.get("protocol_version") != PROTOCOL_VERSION \
                or report.get("final_closure_verified") is not True:
            raise RuntimeError("inherited final protocol-v5 closure is not PASS")

        static = _read(STATIC_V8_REPORT)
        missing = [
            key for key in REQUIRED_STATIC_V8_GATES
            if static.get(key) is not True]
        if static.get("status") != "PASS" \
                or static.get("protocol_version") != PROTOCOL_VERSION \
                or missing:
            raise RuntimeError(
                "static-v8 closure incomplete: " + ", ".join(missing))
        if static.get("authoritative_proof_target") != \
                "prove_complete_observatory_protocol_v6" \
                or int(static.get("compatibility_proof_shim_count", 0)) != 8 \
                or int(static.get("authoritative_entrypoint_import_count", 0)) != 10:
            raise RuntimeError(
                "static-v8 proof-authority/shim census is incomplete")
        roundtrip = static.get("utf8_unicode_roundtrip") or {}
        classifier = static.get("unicode_failure_classifier") or {}
        if roundtrip.get("status") != "PASS" \
                or roundtrip.get("encoding") != "utf-8" \
                or classifier.get("status") != "PASS" \
                or classifier.get("candidate_causal_credit") is not False:
            raise RuntimeError("static-v8 Unicode transport/classification proof is incomplete")

        verification = report.get("protocol_verification") or {}
        systems_calibration = verification.get(
            "systems_reference_calibration_verified") or {}
        distributed_calibration = verification.get(
            "distributed_reference_calibration_verified") or {}
        systems = verification.get(
            "systems_actual_container_crown_verified") or {}
        distributed = verification.get(
            "distributed_actual_container_crown_verified") or {}
        axis_calibration = verification.get(
            "axis_probe_calibration_verified") or {}
        axis_campaigns = verification.get("axis_probe_pairs_verified") or {}
        if verification.get("fault_injection_actual_container_verified") is not True \
                or verification.get("fault_injection_mid_operation_verified") is not True \
                or verification.get("fault_workloads_owner_bound_verified") is not True \
                or verification.get("trusted_process_transport_utf8_verified") is not True \
                or verification.get("axis_probe_utf8_transport_verified") is not True \
                or axis_calibration.get("status") != "PASS" \
                or axis_calibration.get("transport_encoding") != "utf-8" \
                or systems_calibration.get("status") != "PASS" \
                or distributed_calibration.get("status") != "PASS" \
                or systems.get("status") != "PASS" \
                or distributed.get("status") != "PASS":
            raise RuntimeError(
                "dynamic mid-operation/UTF-8 owner-bound verification is incomplete")
        for phase in ("replication", "crown"):
            campaign = axis_campaigns.get(phase) or {}
            if campaign.get("axis_probe_transport_encoding") != "utf-8" \
                    or int(campaign.get("tasks", 0)) < 1 \
                    or int(campaign.get("axis_probe_pairs", 0)) != int(
                        campaign.get("tasks", -1)):
                raise RuntimeError(
                    f"dynamic causal {phase} UTF-8 probe-pair closure is incomplete")

        for label, row in (
                ("systems calibration", systems_calibration),
                ("distributed calibration", distributed_calibration),
                ("systems crown", systems),
                ("distributed crown", distributed)):
            crash = row.get("crash") or {}
            if row.get("transport_encoding") != "utf-8" \
                    or crash.get("actual_container_kill_required") is not True \
                    or crash.get("mid_operation_kill_required") is not True \
                    or crash.get("container_started") is not True \
                    or crash.get("workload_delivered") is not True \
                    or crash.get("operation_reply_observed_before_kill") is not False \
                    or crash.get("mid_operation_kill_verified") is not True \
                    or crash.get("runtime_kill_succeeded") is not True \
                    or crash.get("container_absent_before_recovery") is not True \
                    or crash.get("cli_process_kill_counts_as_evidence") is not False \
                    or int(crash.get("runtime_kill_returncode", -1)) != 0:
                raise RuntimeError(
                    label + " lacks final UTF-8 mid-operation runtime-kill evidence")

        report["authoritative_entrypoint"] = (
            "prove_complete_observatory_protocol_v6.py")
        report["static_v8_authoritative_closure"] = {
            "status": static["status"],
            "protocol_bundle_sha256": static.get("protocol_bundle_sha256"),
            **{key: static.get(key) for key in REQUIRED_STATIC_V8_GATES},
            "authoritative_proof_target": static.get("authoritative_proof_target"),
            "entrypoint_import_count": static.get("authoritative_entrypoint_import_count"),
            "compatibility_proof_shim_count": static.get("compatibility_proof_shim_count"),
            "entrypoint_import_probes": static.get(
                "authoritative_entrypoint_import_probes"),
            "utf8_transport_topology": static.get("utf8_transport_topology"),
            "utf8_unicode_roundtrip": roundtrip,
            "unicode_failure_classifier": classifier,
            "report_sha256": fault_e2e.sha256_file(STATIC_V8_REPORT),
        }
        report["systems_reference_calibration_bound"] = True
        report["distributed_reference_calibration_bound"] = True
        report["systems_actual_container_crown_bound"] = True
        report["distributed_actual_container_crown_bound"] = True
        report["fault_injection_actual_container_bound"] = True
        report["fault_injection_mid_operation_bound"] = True
        report["fault_workloads_owner_bound"] = True
        report["trusted_process_transport_utf8_bound"] = True
        report["axis_probe_calibration_utf8_bound"] = True
        report["axis_probe_runtime_pairs_utf8_bound"] = True
        report["host_unicode_failure_cannot_earn_causal_credit"] = True
        report["utf8_unicode_roundtrip_bound"] = True
        report["authoritative_entrypoint_standalone_import_bound"] = True
        report["compatibility_proof_shims_monotonic_bound"] = True
        report["authoritative_proof_target"] = static.get("authoritative_proof_target")
        report["compatibility_proof_shims"] = static.get("compatibility_proof_shims")
        report["systems_reference_calibration"] = systems_calibration
        report["distributed_reference_calibration"] = distributed_calibration
        report["systems_actual_container_crown"] = systems
        report["distributed_actual_container_crown"] = distributed
        report["cli_process_death_cannot_earn_fault_credit"] = True
        report["post_operation_container_death_cannot_earn_crash_credit"] = True
        report["implicit_fault_workload_cannot_earn_credit"] = True
        report["legacy_proof_commands_cannot_bypass_v6"] = True
        report["final_closure_v6_verified"] = True
        report["final_closure_verified"] = True
        base._atomic_write(E2E_REPORT, report)
        return 0
    except Exception as exc:
        return _fail(report, f"{type(exc).__name__}: {exc}")


if __name__ == "__main__":
    sys.exit(main())
