#!/usr/bin/env python3
"""Static-v7 closure for calibrated mid-operation actual-container fault evidence.

Runs static-v6 first, then proves that both load-bearing process-death arenas are calibrated before
launch, use the same bounded v2 entrypoints in preflight and production, consume exact owner-bound
workloads, and require actual container death while the tested operation is still in flight. The
stable proof entrypoint must route through the final fault-hardened v6 seat. No provider call,
candidate execution, Docker run or owner mutation occurs here.
"""
from __future__ import annotations

import json
import os
import sys

import prove_observatory_protocol_static_v6 as previous

ROOT = previous.ROOT
CAUSAL_REPORT = previous.REPORT
REPORT = os.path.join(ROOT, "proof", "observatory-protocol-static-v7.json")
PROTOCOL_VERSION = "OBSERVATORY-OMEGA-RESEARCH-PROTOCOL-5"

SYSTEMS_REFERENCE = "benchmark/observatory_systems_reference_candidate.py"
SYSTEMS_EVALUATOR = "private-evaluator/evaluator/observatory_systems_arena_v2.py"
SYSTEMS_CONTRACT = "profiles/national-observatory/SYSTEMS-CONTRACT.md"
DISTRIBUTED_REFERENCE = "benchmark/observatory_distributed_reference_candidate.py"
DISTRIBUTED_EVALUATOR = "private-evaluator/evaluator/observatory_distributed_arena_v2.py"
DISTRIBUTED_CONTRACT = "profiles/national-observatory/DISTRIBUTED-SYSTEMS-CONTRACT.md"
FAULT_E2E = "executable-orchestrator/tools/prove_complete_observatory_protocol_fault_hardened.py"
FINAL_V6 = "executable-orchestrator/tools/prove_complete_observatory_protocol_v6.py"
STABLE = "executable-orchestrator/tools/run_observatory_proof.py"

NEW_GATES = (
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
    "fault_evaluator_production_routing_static_bound",
    "fault_mid_operation_crash_static_bound",
    "fault_exact_workloads_static_bound",
    "authoritative_fault_final_entry_static_bound",
)


def _path(relative):
    return os.path.join(ROOT, *relative.split("/"))


def _text(relative):
    with open(_path(relative), encoding="utf-8") as handle:
        return handle.read()


def _require(text, tokens, label):
    missing = [token for token in tokens if token not in text]
    if missing:
        raise RuntimeError(label + " lacks: " + ", ".join(missing))


def _write(path, value):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    temporary = path + ".tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=1, sort_keys=True)
        handle.flush(); os.fsync(handle.fileno())
    os.replace(temporary, path)


def main():
    result = {
        "proof": "observatory-protocol-static-v7-fault-closure",
        "protocol_version": PROTOCOL_VERSION,
        "provider_calls": 0,
        "candidate_executions": 0,
        "status": "FAIL",
    }
    try:
        if previous.main() != 0:
            raise RuntimeError("inherited static-v6 closure failed")
        with open(CAUSAL_REPORT, encoding="utf-8") as handle:
            causal = json.load(handle)
        if causal.get("status") != "PASS" \
                or causal.get("protocol_version") != PROTOCOL_VERSION:
            raise RuntimeError("static-v6 causal receipt is not PASS")

        from lawmax21 import observatory_protocol as protocol
        from lawmax21 import observatory_setup_v3 as setup3
        from lawmax21 import observatory_preflight_v6 as preflight6
        from lawmax21 import observatory_workload_policy as workload_policy

        systems = setup3.CAMPAIGNS.get("systems") or {}
        if systems.get("reference") != SYSTEMS_REFERENCE \
                or systems.get("evaluator") != SYSTEMS_EVALUATOR \
                or systems.get("report") != "proof/systems-reference-calibration.json":
            raise RuntimeError("owner ceremony does not calibrate the exact systems v2 route")
        systems_args = list(systems["args"]())
        if systems_args != [
                "--large-events", str(protocol.workload("systems", "qualification")),
                "--crash-events", str(protocol.workload("systems", "crash_events"))]:
            raise RuntimeError("systems calibration does not consume owner workload policy")

        distributed_campaign = setup3.CAMPAIGNS.get("distributed") or {}
        distributed_args = list(distributed_campaign.get("args", lambda: [])())
        if distributed_campaign.get("reference") != DISTRIBUTED_REFERENCE \
                or distributed_campaign.get("evaluator") != DISTRIBUTED_EVALUATOR \
                or "--crash-events" not in distributed_args \
                or distributed_args[distributed_args.index("--crash-events") + 1] != str(
                    protocol.workload("distributed", "crash_events")):
            raise RuntimeError("owner ceremony does not calibrate exact distributed crash workload")

        specialized = preflight6.core.SPECIALIZED
        if tuple(specialized.get("systems") or ()) != (
                SYSTEMS_REFERENCE, SYSTEMS_EVALUATOR):
            raise RuntimeError("preflight does not require the exact systems calibration pair")
        if tuple(specialized.get("distributed") or ()) != (
                DISTRIBUTED_REFERENCE, DISTRIBUTED_EVALUATOR):
            raise RuntimeError("preflight does not require the exact distributed calibration pair")

        for section in ("systems", "distributed"):
            for policy, label in (
                    (protocol.PRODUCTION_WORKLOADS, "production"),
                    (protocol.PROOF_WORKLOADS, "proof")):
                row = policy.get(section) or {}
                if set(row) != {"qualification", "replication", "crown", "crash_events"} \
                        or min(int(row[key]) for key in row) <= 0:
                    raise RuntimeError(
                        f"{label} {section} workload policy is incomplete")

        workload = _text("executable-orchestrator/lawmax21/observatory_workload_policy.py")
        _require(workload, (
            'crown.SYSTEMS_QUAL_EVENTS = protocol.workload("systems", "qualification")',
            'crown.SYSTEMS_REPLICATION_EVENTS = protocol.workload("systems", "replication")',
            'crown.SYSTEMS_CROWN_EVENTS = protocol.workload("systems", "crown")',
            '"crash_events": protocol.workload("systems", "crash_events")',
            '"crash_events": protocol.workload("distributed", "crash_events")'),
            "owner-signed workload router")

        routing = _text(
            "executable-orchestrator/lawmax21/observatory_evaluator_routing_hardening.py")
        _require(routing, (
            '"observatory_systems_arena_v2.py"',
            'crash_events = protocol.workload("systems", "crash_events")',
            '"--crash-events", str(crash_events)',
            '"observatory_distributed_arena_v2.py"',
            'crash_events = protocol.workload("distributed", "crash_events")',
            'report["owner_signed_crash_events"] = int(crash_events)',
            'crown._run_systems = _systems',
            'distributed._run = _distributed'),
            "production fault evaluator routing")

        systems_base = _text("private-evaluator/evaluator/observatory_systems_arena.py")
        _require(systems_base, (
            'ap.add_argument("--crash-events"',
            '"requested_crash_events": int(a.crash_events)',
            'crash_events = _events(max(1000, a.crash_events)',
            'crash_observed = _crash(runtime, source, crash_state, crash_events)'),
            "durable base workload seat")
        systems_v2 = _text(SYSTEMS_EVALUATOR)
        _require(systems_v2, (
            '"actual_container_kill_required": True',
            '"mid_operation_kill_required": True',
            '"operation_reply_observed_before_kill": None',
            '"mid_operation_kill_verified": False',
            'process.stdin.write(_crash_body(source, events))',
            'reply_observed = os.fstat(output.fileno()).st_size > 0',
            '[runtime, "kill", name]',
            '"runtime_kill_succeeded"',
            '"container_absent_before_recovery"',
            '"cli_process_kill_counts_as_evidence": False',
            '"durable_manifest_evidence"',
            'base._manifest = _safe_manifest',
            'base._crash = _safe_crash'),
            "durable systems v2")
        contract = _text(SYSTEMS_CONTRACT)
        _require(contract, (
            "DURABLE SYSTEMS CONTRACT v2",
            "operation_reply_observed_before_kill=false",
            "mid_operation_kill_verified=true",
            "container_absent_before_recovery=true",
            "Calibration and signed workloads"),
            "durable systems contract")

        distributed_v2 = _text(DISTRIBUTED_EVALUATOR)
        _require(distributed_v2, (
            '"actual_container_kill_required": True',
            '"mid_operation_kill_required": True',
            '"operation_reply_observed_before_kill": None',
            '"mid_operation_kill_verified": False',
            '"events_delivered": 0',
            '"distributed v2 requires explicit --crash-events from owner workload policy"',
            'if prefix == "CRASHLOAD"',
            'report["requested_crash_events"] = int(_CRASH_EVENTS)',
            'process.stdin.write(_crash_body(source, events))',
            'reply_observed = os.fstat(output.fileno()).st_size > 0',
            '[runtime, "kill", name]',
            '"container_absent_before_recovery"',
            '"cli_process_kill_counts_as_evidence": False',
            '"cluster_authority_files"',
            '"baseline_elapsed_seconds"',
            '"campaign_elapsed_seconds"'),
            "distributed v2")
        distributed_contract = _text(DISTRIBUTED_CONTRACT)
        _require(distributed_contract, (
            "Distributed Systems Contract v2",
            "operation_reply_observed_before_kill=false",
            "mid_operation_kill_verified=true",
            "confirmed absent",
            "partially serialized canonical authority is never acceptable"),
            "distributed contract")

        fault = _text(FAULT_E2E)
        _require(fault, (
            '"mid_operation_kill_required"',
            '"operation_reply_observed_before_kill"',
            '"mid_operation_kill_verified"',
            '"distributed_reference_calibration_verified"',
            '"fault_workloads_owner_bound_verified"',
            'verified["fault_injection_mid_operation_verified"] = True'),
            "dynamic fault E2E")
        final = _text(FINAL_V6)
        _require(final, (
            "prove_complete_observatory_protocol_fault_hardened",
            "prove_observatory_protocol_static_v7.py",
            'verification.get("fault_injection_mid_operation_verified") is not True',
            'report["fault_injection_mid_operation_bound"] = True',
            'report["final_closure_v6_verified"] = True'),
            "final protocol-v6 proof")
        stable = _text(STABLE)
        _require(stable, (
            "from prove_complete_observatory_protocol_v6 import main",
            "execution always enters prove_complete_observatory_protocol_v6"),
            "stable proof entrypoint")

        snapshot = workload_policy.snapshot()
        for section in ("systems", "distributed"):
            expected = {
                "qualification": protocol.workload(section, "qualification"),
                "replication": protocol.workload(section, "replication"),
                "crown": protocol.workload(section, "crown"),
                "crash_events": protocol.workload(section, "crash_events"),
            }
            if snapshot.get(section) != expected:
                raise RuntimeError(
                    f"runtime workload snapshot omits signed {section} workload")

        protocol_files = set(protocol.protocol_files(ROOT))
        required = {
            SYSTEMS_REFERENCE, SYSTEMS_EVALUATOR, SYSTEMS_CONTRACT,
            DISTRIBUTED_REFERENCE, DISTRIBUTED_EVALUATOR, DISTRIBUTED_CONTRACT,
            "executable-orchestrator/lawmax21/observatory_setup_v3.py",
            "executable-orchestrator/lawmax21/observatory_preflight_v3.py",
            "executable-orchestrator/lawmax21/observatory_workload_policy.py",
            "executable-orchestrator/lawmax21/observatory_evaluator_routing_hardening.py",
            "executable-orchestrator/tools/prove_observatory_protocol_static_v7.py",
            FAULT_E2E, FINAL_V6, STABLE,
        }
        missing = sorted(required - protocol_files)
        if missing:
            raise RuntimeError("fault closure files omitted from protocol census: " + ", ".join(missing))

        result.update({
            "status": "PASS",
            "protocol_bundle_sha256": protocol.protocol_bundle_sha256(ROOT),
            **{key: True for key in NEW_GATES},
            "systems_reference_calibration": {
                "reference": SYSTEMS_REFERENCE,
                "evaluator": SYSTEMS_EVALUATOR,
                "qualification_events": protocol.workload("systems", "qualification"),
                "crash_events": protocol.workload("systems", "crash_events"),
            },
            "distributed_reference_calibration": {
                "reference": DISTRIBUTED_REFERENCE,
                "evaluator": DISTRIBUTED_EVALUATOR,
                "qualification_events": protocol.workload("distributed", "qualification"),
                "crash_events": protocol.workload("distributed", "crash_events"),
            },
            "systems_workloads": dict(snapshot["systems"]),
            "distributed_workloads": dict(snapshot["distributed"]),
            "authoritative_entrypoint": "prove_complete_observatory_protocol_v6.py",
        })
    except Exception as exc:
        result["reason"] = f"{type(exc).__name__}: {exc}"

    _write(REPORT, result)
    print(json.dumps(result, ensure_ascii=False, indent=1, sort_keys=True))
    print("proof report:", REPORT)
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
