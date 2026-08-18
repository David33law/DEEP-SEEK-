#!/usr/bin/env python3
"""Static-v7 closure for calibrated actual-container fault evidence.

Runs static-v6 first, then proves that both load-bearing process-death arenas are calibrated before
launch, use the same bounded v2 entrypoints in preflight and production, consume owner-bound workloads,
and require actual container death rather than local CLI death.  No provider call, candidate execution,
Docker run or owner mutation occurs here.
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
    "distributed_crash_floor_static_bound",
    "fault_evaluator_production_routing_static_bound",
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

        specialized = preflight6.core.SPECIALIZED
        if tuple(specialized.get("systems") or ()) != (
                SYSTEMS_REFERENCE, SYSTEMS_EVALUATOR):
            raise RuntimeError("preflight does not require the exact systems calibration pair")
        if tuple(specialized.get("distributed") or ()) != (
                DISTRIBUTED_REFERENCE, DISTRIBUTED_EVALUATOR):
            raise RuntimeError("preflight does not require the exact distributed calibration pair")

        production_systems = protocol.PRODUCTION_WORKLOADS.get("systems") or {}
        proof_systems = protocol.PROOF_WORKLOADS.get("systems") or {}
        for row, label in ((production_systems, "production"), (proof_systems, "proof")):
            if set(row) != {"qualification", "replication", "crown", "crash_events"} \
                    or min(int(row[key]) for key in row) <= 0:
                raise RuntimeError(f"{label} systems workload policy is incomplete")
        production_distributed = protocol.PRODUCTION_WORKLOADS.get("distributed") or {}
        proof_distributed = protocol.PROOF_WORKLOADS.get("distributed") or {}
        if int(production_distributed.get("crash_event_floor", 0)) != 20000 \
                or int(proof_distributed.get("crash_event_floor", 0)) != 20000:
            raise RuntimeError("distributed crash-event floor is not owner-bound to evaluator semantics")

        workload = _text("executable-orchestrator/lawmax21/observatory_workload_policy.py")
        _require(workload, (
            'crown.SYSTEMS_QUAL_EVENTS = protocol.workload("systems", "qualification")',
            'crown.SYSTEMS_REPLICATION_EVENTS = protocol.workload("systems", "replication")',
            'crown.SYSTEMS_CROWN_EVENTS = protocol.workload("systems", "crown")',
            '"crash_events": protocol.workload("systems", "crash_events")',
            '"crash_event_floor": protocol.workload(',
            '"distributed", "crash_event_floor"'),
            "owner-signed workload router")

        routing = _text(
            "executable-orchestrator/lawmax21/observatory_evaluator_routing_hardening.py")
        _require(routing, (
            '"observatory_systems_arena_v2.py"',
            '"--crash-events", str(protocol.workload("systems", "crash_events"))',
            '"owner_signed_crash_events"',
            '"observatory_distributed_arena_v2.py"',
            '"owner_signed_crash_event_floor"',
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
            '"cli_process_kill_counts_as_evidence": False',
            '[runtime, "kill", name]',
            '"runtime_kill_succeeded"',
            '"container_absent_before_recovery"',
            '"durable_manifest_evidence"',
            '"authority_files_verified"',
            '"recovery_files_verified"',
            'base._manifest = _safe_manifest',
            'base._crash = _safe_crash'),
            "durable systems v2")
        contract = _text(SYSTEMS_CONTRACT)
        _require(contract, (
            "DURABLE SYSTEMS CONTRACT v2",
            "Authoritative whole-process crash evidence",
            "runtime-kill",
            "container_absent_before_recovery=true",
            "cli_process_kill_counts_as_evidence=false",
            "Calibration and signed workloads"),
            "durable systems contract")

        distributed_base = _text(
            "private-evaluator/evaluator/observatory_distributed_arena.py")
        _require(distributed_base, (
            '_events(max(20000, args.large_events), args.seed + 21, "CRASHLOAD")',),
            "distributed base crash floor")
        distributed_v2 = _text(DISTRIBUTED_EVALUATOR)
        _require(distributed_v2, (
            '"actual_container_kill_required": True',
            '"cli_process_kill_counts_as_evidence": False',
            '[runtime, "kill", name]',
            '"container_absent_before_recovery"',
            '"cluster_authority_files"',
            '"baseline_elapsed_seconds"',
            '"campaign_elapsed_seconds"'),
            "distributed v2")
        distributed_contract = _text(DISTRIBUTED_CONTRACT)
        _require(distributed_contract, (
            "Distributed Systems Contract v2",
            "actual named candidate container",
            "confirmed absent",
            "partially serialized canonical authority is never acceptable"),
            "distributed contract")

        snapshot = workload_policy.snapshot()
        if snapshot.get("systems") != {
                "qualification": protocol.workload("systems", "qualification"),
                "replication": protocol.workload("systems", "replication"),
                "crown": protocol.workload("systems", "crown"),
                "crash_events": protocol.workload("systems", "crash_events")}:
            raise RuntimeError("runtime workload snapshot omits signed systems workload")
        if int((snapshot.get("distributed") or {}).get("crash_event_floor", 0)) != \
                protocol.workload("distributed", "crash_event_floor"):
            raise RuntimeError("runtime workload snapshot omits distributed crash floor")

        protocol_files = set(protocol.protocol_files(ROOT))
        required = {
            SYSTEMS_REFERENCE, SYSTEMS_EVALUATOR, SYSTEMS_CONTRACT,
            DISTRIBUTED_REFERENCE, DISTRIBUTED_EVALUATOR, DISTRIBUTED_CONTRACT,
            "executable-orchestrator/lawmax21/observatory_setup_v3.py",
            "executable-orchestrator/lawmax21/observatory_preflight_v3.py",
            "executable-orchestrator/lawmax21/observatory_workload_policy.py",
            "executable-orchestrator/lawmax21/observatory_evaluator_routing_hardening.py",
            "executable-orchestrator/tools/prove_observatory_protocol_static_v7.py",
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
            "systems_workloads": dict(snapshot["systems"]),
            "distributed_workloads": dict(snapshot["distributed"]),
        })
    except Exception as exc:
        result["reason"] = f"{type(exc).__name__}: {exc}"

    _write(REPORT, result)
    print(json.dumps(result, ensure_ascii=False, indent=1, sort_keys=True))
    print("proof report:", REPORT)
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
