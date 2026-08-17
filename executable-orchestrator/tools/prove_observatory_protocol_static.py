#!/usr/bin/env python3
"""Static proof for the complete owner-signed Observatory research protocol.

No provider call, owner mutation or candidate execution. Compiles/imports the full protocol census,
parses every JSON contract, validates the Pareto/mission/workload/overlay topology and proves the old
partial proof entrypoints are only compatibility shims to the v5 E2E seat.
"""
import ast
import importlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ORCH = os.path.dirname(HERE)
ROOT = os.path.dirname(ORCH)
if ORCH not in sys.path:
    sys.path.insert(0, ORCH)
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

from lawmax21 import observatory_protocol
from lawmax21.canonical import atomic_write_json, read_json

EXPECTED_DIMENSIONS = {
    "distributed_fault_survival", "national_scale_survival",
    "machine_checked_model_survival", "legal_interoperability_survival",
    "cross_model_consistency_survival", "genome_realization_survival",
    "external_model_dependence"}
EXPECTED_MODULES = [
    "lawmax21.observatory_audit", "lawmax21.observatory_audit_v2",
    "lawmax21.observatory_launcher", "lawmax21.observatory_launcher_v2",
    "lawmax21.observatory_setup", "lawmax21.observatory_setup_v2",
    "lawmax21.observatory_setup_v3", "lawmax21.observatory_setup_v4",
    "lawmax21.observatory_preflight_v5",
    "lawmax21.observatory_implementation_search_overlay",
    "lawmax21.observatory_distributed_overlay",
    "lawmax21.observatory_scale_overlay",
    "lawmax21.observatory_formal_overlay",
    "lawmax21.observatory_interoperability_overlay",
    "lawmax21.observatory_cross_model_overlay",
    "lawmax21.observatory_genome_realization_overlay",
    "lawmax21.observatory_prior_art_overlay",
    "lawmax21.observatory_prior_art_hardening_overlay",
    "lawmax21.observatory_novelty_overlay",
    "lawmax21.observatory_meta_search_overlay",
    "lawmax21.observatory_meta_hardening_overlay",
    "lawmax21.observatory_search_integrity_overlay",
    "lawmax21.observatory_build_schema_hardening",
    "lawmax21.observatory_evaluator_routing_hardening",
    "lawmax21.observatory_formal_streaming_routing",
    "lawmax21.observatory_phase_gate_hardening",
    "lawmax21.observatory_cross_model_workload_hardening"]
EXPECTED_FILES = {
    "profiles/national-observatory/DISTRIBUTED-SYSTEMS-CONTRACT.md",
    "profiles/national-observatory/SCALE-SYSTEMS-CONTRACT.md",
    "profiles/national-observatory/FORMAL-MODEL-CONTRACT.md",
    "profiles/national-observatory/INTEROPERABILITY-CONTRACT.md",
    "profiles/national-observatory/CROSS-MODEL-CONSISTENCY-CONTRACT.md",
    "profiles/national-observatory/GENOME-REALIZATION-CONTRACT.md",
    "profiles/national-observatory/PRIOR-ART-CHALLENGE-CONTRACT.md",
    "profiles/national-observatory/PUBLIC-PRIOR-ART-MANIFEST.json",
    "private-evaluator/evaluator/bounded_subprocess.py",
    "private-evaluator/evaluator/observatory_cross_model_arena_v2.py",
    "private-evaluator/evaluator/observatory_formal_arena_v3.py",
    "executable-orchestrator/lawmax21/observatory_build_schema_hardening.py",
    "executable-orchestrator/lawmax21/observatory_genome_realization_overlay.py",
    "executable-orchestrator/tools/mock_observatory_genome_server.py",
    "executable-orchestrator/tools/prove_terminal_condition_closure.py",
    "executable-orchestrator/tools/prove_complete_observatory_protocol.py"}


def _source(relative):
    return open(
        os.path.join(ROOT, *relative.split("/")), encoding="utf-8").read()


def main():
    result = {"proof": "observatory-protocol-static-v5",
              "provider_calls": 0, "status": "FAIL"}
    try:
        files = observatory_protocol.protocol_files(ROOT)
        compiled, parsed = [], []
        for relative in files:
            path = os.path.join(ROOT, *relative.split("/"))
            if relative.endswith(".py"):
                source = open(path, encoding="utf-8").read()
                compile(source, relative, "exec")
                ast.parse(source, filename=relative)
                compiled.append(relative)
            elif relative.endswith(".json"):
                read_json(path)
                parsed.append(relative)
        imported = []
        for module in EXPECTED_MODULES:
            importlib.import_module(module)
            imported.append(module)
        missing_files = sorted(EXPECTED_FILES - set(files))
        if missing_files:
            raise RuntimeError(
                "protocol census omitted: " + ", ".join(missing_files))
        if observatory_protocol.PROTOCOL_VERSION != \
                "OBSERVATORY-OMEGA-RESEARCH-PROTOCOL-5":
            raise RuntimeError("wrong protocol version")
        for flag in (
                "cross_model_consistency_required",
                "executable_genome_realization_required",
                "strict_executable_source_schema_required",
                "bounded_candidate_output_required",
                "terminal_negative_proof_required",
                "proof_mode_forbidden_in_production"):
            if observatory_protocol.MISSION_FLAGS.get(flag) is not True:
                raise RuntimeError("mission flag absent: " + flag)
        if observatory_protocol.SEARCH_POLICY.get(
                "genome_realization_auditors_required") != 2:
            raise RuntimeError(
                "owner-signed policy does not require two genome auditors")
        for section in observatory_protocol.PRODUCTION_WORKLOADS:
            production = observatory_protocol.PRODUCTION_WORKLOADS[section]
            proof = observatory_protocol.PROOF_WORKLOADS[section]
            if set(production) != set(proof):
                raise RuntimeError(
                    section + ": proof/production workload keys differ")
            if not any(
                    int(production[key]) > int(proof[key])
                    for key in production):
                raise RuntimeError(
                    section + ": production workload is not stronger than proof")
        dimensions = read_json(os.path.join(
            ROOT, "profiles", "national-observatory",
            "PARETO-DIMENSIONS.json"))
        ids = [row.get("id") for row in dimensions]
        if len(ids) != len(set(ids)) \
                or not EXPECTED_DIMENSIONS.issubset(set(ids)):
            raise RuntimeError("Pareto dimension identity/coverage failure")
        genome_dimension = next(
            row for row in dimensions
            if row.get("id") == "genome_realization_survival")
        if genome_dimension.get("hard_minimum") != 1.0:
            raise RuntimeError(
                "genome realization is not a hard Pareto gate")
        manifest = read_json(os.path.join(
            ROOT, "profiles", "national-observatory",
            "PUBLIC-PRIOR-ART-MANIFEST.json"))
        source_ids = [
            row.get("source_id") for row in manifest.get("sources") or []]
        if len(source_ids) < 12 or len(source_ids) != len(set(source_ids)):
            raise RuntimeError(
                "prior-art manifest is too small or has duplicate IDs")
        audit = _source(
            "executable-orchestrator/lawmax21/observatory_audit.py")
        ordered = [
            "observatory_build_schema_hardening.install",
            "observatory_shared_corpus_hardening.install",
            "observatory_evaluator_routing_hardening.install",
            "observatory_formal_streaming_routing.install",
            "observatory_scale_hardening.install",
            "observatory_cross_model_workload_hardening.install",
            "observatory_prior_art_hardening_overlay.install",
            "base.install",
            "observatory_cross_model_overlay.install",
            "observatory_genome_realization_overlay.install",
            "observatory_phase_gate_hardening.install"]
        positions = [audit.index(token) for token in ordered]
        if positions != sorted(positions):
            raise RuntimeError(
                "final audit overlay order is not the declared order")
        for relative in (
                "executable-orchestrator/tools/run_observatory_proof.py",
                "executable-orchestrator/tools/"
                "prove_active_novelty_saturation.py"):
            text = _source(relative)
            if "prove_complete_observatory_protocol" not in text \
                    or len(text.splitlines()) > 15:
                raise RuntimeError(
                    relative + " remains a duplicate proof implementation")
        bundle = observatory_protocol.protocol_bundle_sha256(ROOT)
        if len(bundle) != 64:
            raise RuntimeError("protocol bundle hash malformed")
        contracts = observatory_protocol.contract_hashes(ROOT)
        if "genome_realization_contract_sha256" not in contracts:
            raise RuntimeError(
                "owner mission omits genome realization contract hash")
        result.update({
            "status": "PASS",
            "protocol_version": observatory_protocol.PROTOCOL_VERSION,
            "protocol_files": len(files),
            "python_files_compiled": len(compiled),
            "json_files_parsed": len(parsed),
            "modules_imported": imported,
            "pareto_dimensions": len(dimensions),
            "prior_art_sources": len(source_ids),
            "protocol_bundle_sha256": bundle,
            "partial_proof_seats_retired": True,
            "final_overlay_order_verified": True,
            "executable_genome_realization_bound": True})
    except Exception as exc:
        result["reason"] = str(exc)
    output = os.path.join(
        ROOT, "proof", "observatory-protocol-static.json")
    atomic_write_json(output, result)
    print(json.dumps(result, ensure_ascii=False, indent=1, sort_keys=True))
    print("proof report:", output)
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
