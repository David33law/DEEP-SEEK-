#!/usr/bin/env python3
"""Final zero-provider-call static closure proof for Observatory protocol v5.

The inherited proof compiles and imports the broad protocol census. This final layer verifies the
remaining load-bearing topology as one owner-bindable mechanism: strict one-file builders, exact
source-bound evaluator receipts, two independently prompted and citation-map-independent genome
auditors, executable controlled-genome realization, an unbounded real-provider search policy with
stagnation escalation, a deterministic hash-indexed supremacy dossier, the canonical localhost
provider, and the authoritative static->Docker-E2E entrypoint. No provider call or candidate execution
occurs here.
"""
from __future__ import annotations

import importlib
import json
import os
import sys

import prove_observatory_protocol_static_v2 as previous

ROOT = previous.ROOT
REPORT = os.path.join(ROOT, "proof", "observatory-protocol-static-v5.json")
PROTOCOL_VERSION = "OBSERVATORY-OMEGA-RESEARCH-PROTOCOL-5"
DOSSIER_KEY = "supremacy_dossier_verified"

REQUIRED_MODULES = (
    "lawmax21.observatory_build_schema_hardening",
    "lawmax21.observatory_genome_auditor_diversity_hardening",
    "lawmax21.observatory_semantic_evidence_binding_hardening",
    "lawmax21.observatory_genome_realization_overlay",
    "lawmax21.observatory_genome_evidence_binding_hardening",
    "lawmax21.observatory_genome_cross_auditor_hardening",
    "lawmax21.observatory_supremacy_dossier_overlay",
    "lawmax21.observatory_phase_gate_hardening",
    "lawmax21.observatory_preflight_v5",
)
REQUIRED_FILES = {
    "profiles/national-observatory/GENOME-REALIZATION-CONTRACT.md",
    "profiles/national-observatory/SUPREMACY-CONTRACT.md",
    "executable-orchestrator/orchestrator.py",
    "executable-orchestrator/lawmax21/observatory_launcher.py",
    "executable-orchestrator/lawmax21/observatory_build_schema_hardening.py",
    "executable-orchestrator/lawmax21/observatory_genome_auditor_diversity_hardening.py",
    "executable-orchestrator/lawmax21/observatory_semantic_evidence_binding_hardening.py",
    "executable-orchestrator/lawmax21/observatory_genome_realization_overlay.py",
    "executable-orchestrator/lawmax21/observatory_genome_evidence_binding_hardening.py",
    "executable-orchestrator/lawmax21/observatory_genome_cross_auditor_hardening.py",
    "executable-orchestrator/lawmax21/observatory_supremacy_dossier_overlay.py",
    "executable-orchestrator/tools/mock_observatory_protocol_server.py",
    "executable-orchestrator/tools/prove_observatory_protocol_static_v3.py",
    "executable-orchestrator/tools/prove_complete_observatory_protocol.py",
    "executable-orchestrator/tools/prove_complete_observatory_protocol_hardened.py",
    "executable-orchestrator/tools/prove_complete_observatory_protocol_v3.py",
}
GENOME_CONDITIONS = {
    "genome_realization_proven",
    "genome_realization_replication_passed",
    "genome_realization_crown_passed",
}
MISSION_FLAGS = {
    "executable_genome_realization_required",
    "deterministic_supremacy_dossier_required",
    "strict_executable_source_schema_required",
    "bounded_candidate_output_required",
    "terminal_negative_proof_required",
    "proof_mode_forbidden_in_production",
    "unbounded_production_rounds_required",
    "stagnation_escalates_search_required",
}
STATIC_GATES = {
    "strict_one_file_build_schema": True,
    "semantic_source_receipts_bound": True,
    "source_bound_evidence_required": True,
    "auditor_inference_diversity_required": True,
    "cross_auditor_citation_independence_required": True,
    "unbounded_production_rounds_bound": True,
    "stagnation_escalation_bound": True,
    "deterministic_supremacy_dossier_bound": True,
    "final_overlay_order_verified": True,
    "canonical_local_provider_verified": True,
    "authoritative_e2e_protocol_v5_verified": True,
}


def _path(relative: str) -> str:
    return os.path.join(ROOT, *relative.split("/"))


def _text(relative: str) -> str:
    with open(_path(relative), encoding="utf-8") as handle:
        return handle.read()


def _require_tokens(text: str, tokens: tuple[str, ...], label: str) -> None:
    missing = [token for token in tokens if token not in text]
    if missing:
        raise RuntimeError(label + " lacks: " + ", ".join(missing))


def _ordered(text: str, tokens: tuple[str, ...], label: str) -> None:
    positions = []
    for token in tokens:
        try:
            positions.append(text.index(token))
        except ValueError as exc:
            raise RuntimeError(f"{label}: missing {token}") from exc
    if positions != sorted(positions):
        raise RuntimeError(label + ": install order drifted")


def main() -> int:
    result = {
        "proof": "observatory-protocol-static-v5-closure",
        "provider_calls": 0,
        "candidate_executions": 0,
        "status": "FAIL",
    }
    try:
        if previous.main() != 0:
            raise RuntimeError("inherited complete static proof failed")

        from lawmax21 import observatory_protocol as protocol
        from lawmax21 import observatory_build_schema_hardening as build_schema
        from lawmax21 import observatory_genome_realization_overlay as genome
        from lawmax21 import observatory_genome_evidence_binding_hardening as evidence_binding
        from lawmax21 import observatory_genome_auditor_diversity_hardening as auditor_diversity
        from lawmax21 import observatory_genome_cross_auditor_hardening as cross_auditor
        from lawmax21 import observatory_supremacy_dossier_overlay as dossier
        from lawmax21 import observatory_semantic_evidence_binding_hardening as semantic_binding
        from lawmax21 import observatory_phase_gate_hardening as phase
        from lawmax21 import observatory_preflight_v2 as preflight_core

        imported = []
        for module_name in REQUIRED_MODULES:
            importlib.import_module(module_name)
            imported.append(module_name)

        if protocol.PROTOCOL_VERSION != PROTOCOL_VERSION:
            raise RuntimeError("owner-signed protocol is not version 5")
        missing_flags = sorted(
            flag for flag in MISSION_FLAGS
            if protocol.MISSION_FLAGS.get(flag) is not True)
        if missing_flags:
            raise RuntimeError("mission flags missing: " + ", ".join(missing_flags))
        if protocol.SEARCH_POLICY.get("production_max_rounds") != 0:
            raise RuntimeError("finite production round cap remains owner-permitted")
        if protocol.SEARCH_POLICY.get("stagnation_response") != \
                "continue-successor-radical-novelty-meta-search":
            raise RuntimeError("stagnation does not widen search")
        if int(protocol.SEARCH_POLICY.get(
                "genome_realization_auditors_required", 0)) != 2:
            raise RuntimeError("two genome-realization auditors are not required")
        if protocol.CONTRACT_FILES.get(
                "genome_realization_contract_sha256") != \
                "profiles/national-observatory/GENOME-REALIZATION-CONTRACT.md":
            raise RuntimeError("genome contract is not owner-hash-bound")

        protocol_files = set(protocol.protocol_files(ROOT))
        missing_files = sorted(REQUIRED_FILES - protocol_files)
        if missing_files:
            raise RuntimeError("protocol census omitted: " + ", ".join(missing_files))
        for relative in REQUIRED_FILES:
            if not os.path.isfile(_path(relative)):
                raise RuntimeError("required file absent: " + relative)

        files_schema = build_schema.BUILD_SCHEMA["properties"]["files"]
        allowed = set(files_schema["items"]["properties"]["path"]["enum"])
        if build_schema.BUILD_SCHEMA.get("additionalProperties") is not False \
                or files_schema.get("minItems") != 1 \
                or files_schema.get("maxItems") != 1 \
                or allowed != {
                    "candidate.py", "systems_candidate.py",
                    "distributed_candidate.py", "scale_candidate.py",
                    "formal_candidate.py", "interoperability_candidate.py"}:
            raise RuntimeError("executable-source boundary is not closed one-file output")

        if tuple(genome.AUDITORS) != ("A", "B") \
                or len(genome.oroles.GENOME_FIELDS) != 13 \
                or set(genome.SUPREMACY_KEYS) != GENOME_CONDITIONS:
            raise RuntimeError("genome realization topology drifted")
        if set(auditor_diversity.PROFILES) != {
                "genome-realization-auditor-A",
                "genome-realization-auditor-B"} \
                or auditor_diversity.PROFILES[
                    "genome-realization-auditor-A"]["temperature"] != 0.0 \
                or auditor_diversity.PROFILES[
                    "genome-realization-auditor-B"]["temperature"] != 0.35:
            raise RuntimeError("genome auditors are not inference-diverse")
        if cross_auditor.MIN_DIFFERING_AXIS_MAPS != 4:
            raise RuntimeError("cross-auditor map independence threshold drifted")
        if dossier.SUPREMACY_KEY != DOSSIER_KEY \
                or dossier.CLAIM_LEVEL != \
                "EVIDENCE_SUPPORTED_SUPREMACY_WITHIN_SIGNED_PROTOCOL_AND_TESTED_BOUNDS":
            raise RuntimeError("deterministic dossier claim/condition drifted")
        if not callable(semantic_binding.install) or not callable(evidence_binding.install):
            raise RuntimeError("source-binding hardening is not installable")
        if phase._DOWNSTREAM.get("genome_realization_qualification") != {
                "genome_realization_survival"}:
            raise RuntimeError("genome hard minimum is not phase-aware")
        importlib.import_module("lawmax21.observatory_preflight_v5")
        if "genome_realization_survival" not in preflight_core.REQUIRED_DIMENSIONS:
            raise RuntimeError("preflight omits genome realization hard dimension")

        with open(_path(
                "profiles/national-observatory/PARETO-DIMENSIONS.json"),
                encoding="utf-8") as handle:
            dimensions = {row["id"]: row for row in json.load(handle)}
        genome_dimension = dimensions.get("genome_realization_survival") or {}
        if genome_dimension.get("direction") != "higher" \
                or float(genome_dimension.get("hard_minimum", -1)) != 1.0:
            raise RuntimeError("genome realization is not a hard Pareto gate")

        launcher = _text("executable-orchestrator/lawmax21/observatory_launcher.py")
        _require_tokens(launcher, (
            "PRODUCTION_MAX_ROUNDS = 0",
            "args.max_rounds != PRODUCTION_MAX_ROUNDS",
            "use --max-rounds 0",
            '"finite_cap_allowed_for_real_provider": False'),
            "production launcher")
        shared = _text("executable-orchestrator/orchestrator.py")
        _require_tokens(shared, (
            "if max_rounds > 0 and rs >= max_rounds",
            "_record_stagnation_escalation",
            'getattr(ctx, "profile_id", "") == "national-observatory"',
            "continue-successor-radical-novelty-meta-search"),
            "shared escalation loop")

        audit = _text("executable-orchestrator/lawmax21/observatory_audit.py")
        _ordered(audit, (
            "observatory_build_schema_hardening.install",
            "observatory_genome_auditor_diversity_hardening.install",
            "observatory_shared_corpus_hardening.install",
            "observatory_evaluator_routing_hardening.install",
            "observatory_semantic_evidence_binding_hardening.install",
            "observatory_formal_streaming_routing.install",
            "observatory_scale_hardening.install",
            "observatory_cross_model_workload_hardening.install",
            "observatory_genome_evidence_binding_hardening.install",
            "observatory_genome_cross_auditor_hardening.install",
            "observatory_prior_art_hardening_overlay.install",
            "base.install",
            "observatory_cross_model_overlay.install",
            "observatory_genome_realization_overlay.install",
            "observatory_supremacy_dossier_overlay.install",
            "observatory_phase_gate_hardening.install"),
            "final Observatory overlay")

        semantic_source = _text(
            "executable-orchestrator/lawmax21/observatory_semantic_evidence_binding_hardening.py")
        _require_tokens(semantic_source, (
            "candidate_sha256",
            "in-memory and persisted semantic source bytes diverge",
            "atomic_write_json", "observatory-hidden-"),
            "semantic source receipt binding")
        evidence_source = _text(
            "executable-orchestrator/lawmax21/observatory_genome_evidence_binding_hardening.py")
        _require_tokens(evidence_source, (
            "_persisted_receipt", "candidate_sha256",
            "MIN_UNIQUE_DEFINITION_CITATIONS = 8",
            "MAX_AXES_PER_DEFINITION = 4",
            "no passing source-bound evidence"),
            "genome evidence binding")
        cross_source = _text(
            "executable-orchestrator/lawmax21/observatory_genome_cross_auditor_hardening.py")
        _require_tokens(cross_source, (
            "MIN_DIFFERING_AXIS_MAPS = 4",
            "auditor_citation_maps_independent",
            "genome._passes = passes"),
            "cross-auditor hardening")
        dossier_source = _text(
            "executable-orchestrator/lawmax21/observatory_supremacy_dossier_overlay.py")
        _require_tokens(dossier_source, (
            'SUPREMACY_KEY = "supremacy_dossier_verified"',
            "OMEGA-SUPREMACY-DOSSIER.json",
            "EVIDENCE_SUPPORTED_SUPREMACY_WITHIN_SIGNED_PROTOCOL_AND_TESTED_BOUNDS",
            "evidence_index",
            'ctx.esc._sup()["final_dossier"]',
            'out["INDEPENDENT_AUDIT"] = independent_audit'),
            "deterministic supremacy dossier")

        provider = _text(
            "executable-orchestrator/tools/mock_observatory_protocol_server.py")
        _require_tokens(provider, (
            "genome-realization-auditor-", "PERSISTED EVIDENCE CATALOG",
            "auditor_offset", "Counter", "_choose_definition"),
            "canonical localhost provider")
        e2e = _text(
            "executable-orchestrator/tools/prove_complete_observatory_protocol_hardened.py")
        _require_tokens(e2e, (
            "deterministic_supremacy_dossier_required",
            "OMEGA-SUPREMACY-DOSSIER.json",
            "supremacy_dossier_verified",
            "auditor_citation_maps_independent",
            "unbounded_production_rounds_required",
            "stagnation_escalates_search_required"),
            "hardened E2E")
        stable = _text("executable-orchestrator/tools/run_observatory_proof.py")
        if "prove_complete_observatory_protocol_v3" not in stable:
            raise RuntimeError("stable proof command bypasses v5 closure")

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
            "dossier_terminal_condition": DOSSIER_KEY,
            **STATIC_GATES,
        })
    except Exception as exc:
        result["reason"] = f"{type(exc).__name__}: {exc}"

    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    with open(REPORT, "w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=1, sort_keys=True)
    print(json.dumps(result, ensure_ascii=False, indent=1, sort_keys=True))
    print("proof report:", REPORT)
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
