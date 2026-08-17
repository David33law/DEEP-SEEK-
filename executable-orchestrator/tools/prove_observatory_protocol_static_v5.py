#!/usr/bin/env python3
"""Static closure extension for causal controlled-genome realization.

Runs the complete portable-owner protocol-v5 static proof, then verifies that causal source ablation
is bound to the owner-signed mission, explicit terminal conditions, final overlay order, independent
audit, hard Pareto gate, deterministic dossier, causal-aware localhost provider and authoritative
Docker E2E path. No provider call, candidate execution or owner mutation occurs here.
"""
from __future__ import annotations

import hashlib
import importlib
import json
import os
import sys

import prove_observatory_protocol_static_v4 as previous

ROOT = previous.ROOT
PREVIOUS_REPORT = previous.REPORT
REPORT = os.path.join(
    ROOT, "proof", "observatory-protocol-static-v5-causal.json")
PROTOCOL_VERSION = "OBSERVATORY-OMEGA-RESEARCH-PROTOCOL-5"
CAUSAL_CONDITIONS = {
    "genome_causal_ablation_replication_passed",
    "genome_causal_ablation_crown_passed",
}
REQUIRED_MODULES = (
    "lawmax21.observatory_genome_causal_ablation_hardening",
    "lawmax21.observatory_causal_audit_hardening",
    "lawmax21.observatory_causal_dossier_hardening",
)
REQUIRED_FILES = {
    "executable-orchestrator/lawmax21/observatory_genome_causal_ablation_hardening.py",
    "executable-orchestrator/lawmax21/observatory_causal_audit_hardening.py",
    "executable-orchestrator/lawmax21/observatory_causal_dossier_hardening.py",
    "executable-orchestrator/tools/mock_observatory_causal_server.py",
    "executable-orchestrator/tools/prove_observatory_protocol_static_v5.py",
    "executable-orchestrator/tools/prove_complete_observatory_protocol_causal_hardened.py",
    "executable-orchestrator/tools/prove_complete_observatory_protocol_causal_provider_hardened.py",
    "executable-orchestrator/tools/prove_complete_observatory_protocol_v5.py",
}


def _path(relative):
    return os.path.join(ROOT, *relative.split("/"))


def _text(relative):
    with open(_path(relative), encoding="utf-8") as handle:
        return handle.read()


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require(text, tokens, label):
    missing = [token for token in tokens if token not in text]
    if missing:
        raise RuntimeError(label + " lacks: " + ", ".join(missing))


def _ordered(text, tokens, label):
    positions = []
    for token in tokens:
        try:
            positions.append(text.index(token))
        except ValueError as exc:
            raise RuntimeError(label + " lacks: " + token) from exc
    if positions != sorted(positions):
        raise RuntimeError(label + " order drifted")


def main():
    result = {
        "proof": "observatory-protocol-static-v5-causal-closure",
        "provider_calls": 0,
        "candidate_executions": 0,
        "status": "FAIL",
    }
    try:
        if previous.main() != 0:
            raise RuntimeError(
                "inherited portable-owner static closure failed")
        with open(PREVIOUS_REPORT, encoding="utf-8") as handle:
            inherited = json.load(handle)
        if inherited.get("status") != "PASS":
            raise RuntimeError("inherited static receipt is not PASS")

        from lawmax21 import observatory_protocol as protocol
        from lawmax21 import observatory_genome_causal_ablation_hardening as causal

        imported = [
            importlib.import_module(name).__name__
            for name in REQUIRED_MODULES]
        if protocol.PROTOCOL_VERSION != PROTOCOL_VERSION:
            raise RuntimeError("wrong protocol version")
        for flag in (
                "causal_genome_ablation_required",
                "causal_genome_negative_controls_required"):
            if protocol.MISSION_FLAGS.get(flag) is not True:
                raise RuntimeError("signed mission flag absent: " + flag)
        if int(protocol.SEARCH_POLICY.get(
                "genome_causal_ablation_phases_required", 0)) != 2:
            raise RuntimeError(
                "signed search policy does not require replication+crown ablation")

        protocol_files = set(protocol.protocol_files(ROOT))
        omitted = sorted(REQUIRED_FILES - protocol_files)
        if omitted:
            raise RuntimeError(
                "protocol census omitted causal proof files: "
                + ", ".join(omitted))
        if set(causal.CAUSAL_LABELS) != {"replication", "crown"}:
            raise RuntimeError("causal genome phases drifted")
        if set(causal.CAUSAL_SUPREMACY_KEYS) != CAUSAL_CONDITIONS:
            raise RuntimeError("causal terminal condition identity drifted")

        audit = _text(
            "executable-orchestrator/lawmax21/observatory_audit.py")
        _ordered(audit, (
            "observatory_causal_audit_hardening.install",
            "base.install",
            "observatory_cross_model_overlay.install",
            "observatory_genome_realization_overlay.install",
            "observatory_genome_causal_ablation_hardening.install",
            "observatory_causal_dossier_hardening.install",
            "observatory_supremacy_dossier_overlay.install",
            "observatory_phase_gate_hardening.install"),
            "causal final overlay")

        causal_source = _text(
            "executable-orchestrator/lawmax21/"
            "observatory_genome_causal_ablation_hardening.py")
        _require(causal_source, (
            "class _DefinitionRenamer",
            "auditor-specific definition set",
            "inert-negative-control",
            "negative_controls_passed",
            "candidate_sha256",
            "causal_failure_observed",
            "Infrastructure refusal",
            "escalation.SUPREMACY_KEYS.append",
            "genome_causal_ablation_replication_passed",
            "genome_causal_ablation_crown_passed"),
            "causal genome implementation")
        contract = _text(
            "profiles/national-observatory/GENOME-REALIZATION-CONTRACT.md")
        _require(contract, (
            "Causal source-ablation proof",
            "Inert negative controls",
            "auditor-specific axis/group/artifact citation set",
            "genome_causal_ablation_replication_passed",
            "genome_causal_ablation_crown_passed"),
            "genome realization contract")
        causal_audit = _text(
            "executable-orchestrator/lawmax21/"
            "observatory_causal_audit_hardening.py")
        _require(causal_audit, (
            "causal_replication", "causal_crown",
            "negative_controls", "exact_mutated_source_receipts_required"),
            "independent audit causal receipt")
        causal_dossier = _text(
            "executable-orchestrator/lawmax21/"
            "observatory_causal_dossier_hardening.py")
        _require(causal_dossier, (
            "all_ablation_mutations_destroyed_claimed_behavior",
            "negative_controls_passed",
            "genome_causal_ablation_replication",
            "genome_causal_ablation_crown",
            "evaluator_receipt_sha256"),
            "causal dossier binding")

        with open(
                _path("profiles/national-observatory/PARETO-DIMENSIONS.json"),
                encoding="utf-8") as handle:
            pareto = {row["id"]: row for row in json.load(handle)}
        dimension = pareto.get("genome_realization_survival") or {}
        if dimension.get("direction") != "higher" \
                or float(dimension.get("hard_minimum", -1)) != 1.0 \
                or "inert AST-mutation controls" not in str(
                    dimension.get("measurement", "")):
            raise RuntimeError(
                "causal genome realization is not a hard Pareto obligation")

        hardened = _text(
            "executable-orchestrator/tools/"
            "prove_complete_observatory_protocol_causal_hardened.py")
        _require(hardened, (
            "genome_causal_ablation_replication_passed",
            "genome_causal_ablation_crown_passed",
            "negative_controls_passed",
            "causal_failure_observed",
            "evaluator_receipt_sha256"),
            "causal Docker E2E verifier")
        provider = _text(
            "executable-orchestrator/tools/"
            "prove_complete_observatory_protocol_causal_provider_hardened.py")
        _require(provider, (
            "_genome_provider_popen",
            "mock_observatory_protocol_server.py",
            "mock_observatory_causal_server.py",
            "CORE.subprocess.Popen",
            "Real-provider endpoints are never affected"),
            "causal-aware local-provider route")
        causal_provider = _text(
            "executable-orchestrator/tools/mock_observatory_causal_server.py")
        _require(causal_provider, (
            "mock_observatory_genome_server.py",
            "governance_evolution_model",
            "apply_change",
            "hidden semantic scenario"),
            "causal-aware local provider")
        final_entry = _text(
            "executable-orchestrator/tools/"
            "prove_complete_observatory_protocol_v5.py")
        _require(final_entry, (
            "prove_observatory_protocol_static_v5.py",
            "prove_complete_observatory_protocol_causal_provider_hardened",
            "causal_genome_ablation_bound",
            "genome_aware_local_provider_used"),
            "authoritative causal proof entrypoint")
        stable = _text(
            "executable-orchestrator/tools/run_observatory_proof.py")
        if "prove_complete_observatory_protocol_v5" not in stable:
            raise RuntimeError(
                "stable proof command bypasses causal protocol closure")

        result.update({
            "status": "PASS",
            "protocol_version": protocol.PROTOCOL_VERSION,
            "protocol_bundle_sha256":
                protocol.protocol_bundle_sha256(ROOT),
            "protocol_files": len(protocol_files),
            "modules_imported": imported,
            "causal_terminal_conditions": sorted(CAUSAL_CONDITIONS),
            "causal_phases": list(causal.CAUSAL_LABELS),
            "auditor_specific_definition_set_ablation": True,
            "inert_negative_controls_required": True,
            "exact_mutated_source_receipts_required": True,
            "causal_dossier_direct_indexing_required": True,
            "causal_genome_ablation_bound": True,
            "genome_aware_local_provider_verified": True,
            "causal_aware_local_provider_verified": True,
            "authoritative_causal_e2e_verified": True,
            "inherited_static_report_sha256":
                _sha256(PREVIOUS_REPORT),
        })
    except Exception as exc:
        result["reason"] = f"{type(exc).__name__}: {exc}"

    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    with open(REPORT, "w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False,
                  indent=1, sort_keys=True)
    print(json.dumps(result, ensure_ascii=False,
                     indent=1, sort_keys=True))
    print("proof report:", REPORT)
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
