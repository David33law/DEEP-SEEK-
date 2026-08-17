#!/usr/bin/env python3
"""Final zero-provider-call static closure proof for Observatory protocol v5.

This is deliberately independent of the runtime tournament. It first executes the existing complete
static proof, then verifies the protocol-v5 additions as one connected mechanism: owner-signed
mission flags and contract hashes, executable controlled-genome realization, source-bound evidence,
phase-aware hard gates, the final overlay order, the protocol-v5 mock provider and the authoritative
E2E entrypoint. It compiles/imports code but makes no provider call and executes no candidate.
"""
from __future__ import annotations

import importlib
import json
import os
import sys

import prove_observatory_protocol_static_v2 as previous

ROOT = previous.ROOT
REPORT = os.path.join(ROOT, "proof", "observatory-protocol-static-v5.json")

REQUIRED_MODULES = (
    "lawmax21.observatory_build_schema_hardening",
    "lawmax21.observatory_genome_realization_overlay",
    "lawmax21.observatory_genome_evidence_binding_hardening",
    "lawmax21.observatory_phase_gate_hardening",
    "lawmax21.observatory_preflight_v5",
)
REQUIRED_FILES = {
    "profiles/national-observatory/GENOME-REALIZATION-CONTRACT.md",
    "executable-orchestrator/lawmax21/observatory_build_schema_hardening.py",
    "executable-orchestrator/lawmax21/observatory_genome_realization_overlay.py",
    "executable-orchestrator/lawmax21/observatory_genome_evidence_binding_hardening.py",
    "executable-orchestrator/tools/mock_observatory_genome_server.py",
    "executable-orchestrator/tools/prove_observatory_protocol_static_v3.py",
    "executable-orchestrator/tools/prove_complete_observatory_protocol_v3.py",
}
GENOME_CONDITIONS = {
    "genome_realization_proven",
    "genome_realization_replication_passed",
    "genome_realization_crown_passed",
}
MISSION_FLAGS = {
    "executable_genome_realization_required",
    "strict_executable_source_schema_required",
    "bounded_candidate_output_required",
    "terminal_negative_proof_required",
    "proof_mode_forbidden_in_production",
}


def _path(relative: str) -> str:
    return os.path.join(ROOT, *relative.split("/"))


def _text(relative: str) -> str:
    with open(_path(relative), encoding="utf-8") as handle:
        return handle.read()


def _ordered(text: str, tokens: list[str], label: str) -> None:
    positions = []
    for token in tokens:
        try:
            positions.append(text.index(token))
        except ValueError as exc:
            raise RuntimeError(f"{label}: missing integration token {token}") from exc
    if positions != sorted(positions):
        raise RuntimeError(f"{label}: integration order is not fail-closed")


def main() -> int:
    result = {
        "proof": "observatory-protocol-static-v5-closure",
        "provider_calls": 0,
        "candidate_executions": 0,
        "status": "FAIL",
    }
    try:
        prior_code = previous.main()
        if prior_code != 0:
            raise RuntimeError("the inherited complete static proof did not pass")

        from lawmax21 import observatory_protocol as protocol
        from lawmax21 import observatory_build_schema_hardening as build_schema
        from lawmax21 import observatory_genome_realization_overlay as genome
        from lawmax21 import observatory_genome_evidence_binding_hardening as evidence_binding
        from lawmax21 import observatory_phase_gate_hardening as phase
        from lawmax21 import observatory_preflight_v2 as preflight_core

        imported = []
        for module_name in REQUIRED_MODULES:
            importlib.import_module(module_name)
            imported.append(module_name)

        if protocol.PROTOCOL_VERSION != "OBSERVATORY-OMEGA-RESEARCH-PROTOCOL-5":
            raise RuntimeError("owner-signed protocol is not version 5")
        missing_flags = sorted(
            flag for flag in MISSION_FLAGS
            if protocol.MISSION_FLAGS.get(flag) is not True)
        if missing_flags:
            raise RuntimeError("protocol-v5 mission flags missing: " + ", ".join(missing_flags))
        if int(protocol.SEARCH_POLICY.get("genome_realization_auditors_required", 0)) != 2:
            raise RuntimeError("protocol-v5 does not require two genome-realization auditors")
        if protocol.CONTRACT_FILES.get("genome_realization_contract_sha256") != \
                "profiles/national-observatory/GENOME-REALIZATION-CONTRACT.md":
            raise RuntimeError("genome-realization contract is not owner-hash-bound")

        protocol_files = set(protocol.protocol_files(ROOT))
        missing_files = sorted(REQUIRED_FILES - protocol_files)
        if missing_files:
            raise RuntimeError("protocol census omitted: " + ", ".join(missing_files))
        for relative in REQUIRED_FILES:
            if not os.path.isfile(_path(relative)):
                raise RuntimeError("required protocol-v5 file is absent: " + relative)

        schema = build_schema.BUILD_SCHEMA
        files_schema = schema["properties"]["files"]
        if schema.get("additionalProperties") is not False \
                or files_schema.get("minItems") != 1 \
                or files_schema.get("maxItems") != 1:
            raise RuntimeError("executable-source schema is not a closed one-file boundary")
        allowed = set(files_schema["items"]["properties"]["path"]["enum"])
        expected_allowed = {
            "candidate.py", "systems_candidate.py", "distributed_candidate.py",
            "scale_candidate.py", "formal_candidate.py", "interoperability_candidate.py"}
        if allowed != expected_allowed:
            raise RuntimeError("executable-source path surface drifted")

        if tuple(genome.AUDITORS) != ("A", "B") \
                or len(genome.oroles.GENOME_FIELDS) != 13:
            raise RuntimeError("genome realization is not a two-auditor thirteen-axis campaign")
        if set(genome.SUPREMACY_KEYS) != GENOME_CONDITIONS:
            raise RuntimeError("genome-realization terminal conditions drifted")
        if not callable(getattr(evidence_binding, "install", None)):
            raise RuntimeError("source-bound genome evidence hardening is not installable")

        downstream = phase._DOWNSTREAM
        if downstream.get("genome_realization_qualification") != {
                "genome_realization_survival"}:
            raise RuntimeError("genome-realization hard minimum is not phase-aware")
        if "genome_realization_survival" not in preflight_core.REQUIRED_DIMENSIONS:
            # Importing preflight-v5 must mutate the shared required census.
            importlib.import_module("lawmax21.observatory_preflight_v5")
        if "genome_realization_survival" not in preflight_core.REQUIRED_DIMENSIONS:
            raise RuntimeError("preflight does not require genome_realization_survival")

        pareto = json.load(open(_path(
            "profiles/national-observatory/PARETO-DIMENSIONS.json"), encoding="utf-8"))
        dimensions = {row.get("id"): row for row in pareto}
        genome_dimension = dimensions.get("genome_realization_survival") or {}
        if genome_dimension.get("direction") != "higher" \
                or float(genome_dimension.get("hard_minimum", -1)) != 1.0:
            raise RuntimeError("genome realization is not a hard Pareto gate")

        audit = _text("executable-orchestrator/lawmax21/observatory_audit.py")
        _ordered(audit, [
            "observatory_build_schema_hardening.install",
            "observatory_shared_corpus_hardening.install",
            "observatory_evaluator_routing_hardening.install",
            "observatory_formal_streaming_routing.install",
            "observatory_scale_hardening.install",
            "observatory_cross_model_workload_hardening.install",
            "observatory_genome_evidence_binding_hardening.install",
            "observatory_prior_art_hardening_overlay.install",
            "base.install",
            "observatory_cross_model_overlay.install",
            "observatory_genome_realization_overlay.install",
            "observatory_phase_gate_hardening.install",
        ], "final Observatory overlay")

        audit_v2 = _text("executable-orchestrator/lawmax21/observatory_audit_v2.py")
        for token in ("cross_model", "genome_realization"):
            if token not in audit_v2:
                raise RuntimeError("independent audit omits campaign: " + token)

        genome_source = _text(
            "executable-orchestrator/lawmax21/observatory_genome_realization_overlay.py")
        for token in (
                '"status": "PASS" if consensus else "FAIL"',
                '"passed": consensus',
                '"definitions"',
                '"candidate_sha256"',
                '"group"'):
            if token not in genome_source:
                raise RuntimeError("genome realization lacks load-bearing token: " + token)

        e2e = _text("executable-orchestrator/tools/prove_complete_observatory_protocol.py")
        if "OBSERVATORY-OMEGA-RESEARCH-PROTOCOL-5" not in e2e:
            raise RuntimeError("authoritative E2E does not require signed protocol v5")
        if "mock_observatory_genome_server.py" not in e2e:
            raise RuntimeError("authoritative E2E does not exercise the genome-realization mock")
        for condition in GENOME_CONDITIONS:
            if condition not in e2e:
                raise RuntimeError("authoritative E2E omits condition: " + condition)
        for token in (
                "genome-realization-qualification-",
                "genome-realization-replication-",
                "genome-realization-crown-"):
            if token not in e2e:
                raise RuntimeError("authoritative E2E omits evidence family: " + token)

        hardened = _text(
            "executable-orchestrator/tools/prove_complete_observatory_protocol_hardened.py")
        for relative in (
                "executable-orchestrator/lawmax21/observatory_genome_realization_overlay.py",
                "executable-orchestrator/lawmax21/observatory_genome_evidence_binding_hardening.py",
                "executable-orchestrator/tools/mock_observatory_genome_server.py"):
            if relative not in hardened:
                raise RuntimeError("hardened E2E census omits: " + relative)

        bundle = protocol.protocol_bundle_sha256(ROOT)
        if len(bundle) != 64:
            raise RuntimeError("protocol-v5 bundle hash is malformed")
        result.update({
            "status": "PASS",
            "protocol_version": protocol.PROTOCOL_VERSION,
            "protocol_bundle_sha256": bundle,
            "protocol_files": len(protocol_files),
            "modules_imported": imported,
            "genome_axes": len(genome.oroles.GENOME_FIELDS),
            "genome_auditors": list(genome.AUDITORS),
            "genome_terminal_conditions": sorted(GENOME_CONDITIONS),
            "strict_one_file_build_schema": True,
            "source_bound_evidence_required": True,
            "final_overlay_order_verified": True,
            "authoritative_e2e_protocol_v5_verified": True,
        })
    except Exception as exc:  # fail closed; the report is the diagnostic receipt
        result["reason"] = f"{type(exc).__name__}: {exc}"

    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    with open(REPORT, "w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=1, sort_keys=True)
    print(json.dumps(result, ensure_ascii=False, indent=1, sort_keys=True))
    print("proof report:", REPORT)
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
