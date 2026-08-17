#!/usr/bin/env python3
"""Authoritative protocol-v5 proof with causal controlled-genome realization.

Runs portable-owner static closure, causal static closure and then the causal-hardened production-
container E2E proof through the complete genome-aware localhost provider. The E2E still uses the real
runner/state-machine/API shape, performs crash/resume and every owner gate, and makes zero real
provider calls.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

import prove_complete_observatory_protocol_causal_provider_hardened as e2e

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
STATIC = os.path.join(HERE, "prove_observatory_protocol_static_v5.py")
INHERITED_STATIC_REPORT = os.path.join(
    ROOT, "proof", "observatory-protocol-static-v5.json")
CAUSAL_STATIC_REPORT = os.path.join(
    ROOT, "proof", "observatory-protocol-static-v5-causal.json")
E2E_REPORT = os.path.join(
    ROOT, "proof", "complete-observatory-protocol-e2e.json")
PROTOCOL_VERSION = "OBSERVATORY-OMEGA-RESEARCH-PROTOCOL-5"
INHERITED_STATIC_GATES = (
    "strict_one_file_build_schema",
    "semantic_source_receipts_bound",
    "source_bound_evidence_required",
    "auditor_inference_diversity_required",
    "cross_auditor_citation_independence_required",
    "unbounded_production_rounds_bound",
    "stagnation_escalation_bound",
    "deterministic_supremacy_dossier_bound",
    "dossier_foundation_evidence_bound",
    "portable_owner_signature_static_extension",
    "final_launcher_v3_verified",
    "owner_public_key_snapshot_verified",
    "signed_owner_decisions_snapshot_verified",
    "owner_gate_crypto_reverification_verified",
    "final_overlay_order_verified",
    "canonical_local_provider_verified",
    "authoritative_e2e_protocol_v5_verified",
)
CAUSAL_STATIC_GATES = (
    "causal_genome_ablation_bound",
    "auditor_specific_definition_set_ablation",
    "inert_negative_controls_required",
    "exact_mutated_source_receipts_required",
    "causal_dossier_direct_indexing_required",
    "authoritative_causal_e2e_verified",
)


def _read(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def main(argv=None):
    static_run = subprocess.run(
        [sys.executable, STATIC], capture_output=True, text=True,
        timeout=3600,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    if static_run.returncode != 0:
        print(static_run.stdout)
        print(static_run.stderr, file=sys.stderr)
        return static_run.returncode

    inherited = _read(INHERITED_STATIC_REPORT)
    causal = _read(CAUSAL_STATIC_REPORT)
    inherited_missing = []
    for key in INHERITED_STATIC_GATES:
        expected = (
            "PASS" if key == "portable_owner_signature_static_extension"
            else True)
        if inherited.get(key) != expected:
            inherited_missing.append(key)
    causal_missing = [
        key for key in CAUSAL_STATIC_GATES
        if causal.get(key) is not True]
    if inherited.get("status") != "PASS" \
            or inherited.get("protocol_version") != PROTOCOL_VERSION \
            or inherited_missing \
            or causal.get("status") != "PASS" \
            or causal.get("protocol_version") != PROTOCOL_VERSION \
            or causal_missing:
        print(json.dumps({
            "status": "FAIL",
            "reason": "static protocol closure incomplete",
            "inherited_missing": inherited_missing,
            "causal_missing": causal_missing,
            "inherited": inherited,
            "causal": causal,
        }, ensure_ascii=False, indent=1, sort_keys=True))
        return 1

    code = e2e.main(argv)
    if os.path.isfile(E2E_REPORT):
        report = _read(E2E_REPORT)
        report["static_protocol_v5_portable_owner_closure"] = {
            "status": inherited.get("status"),
            "protocol_version": inherited.get("protocol_version"),
            "protocol_bundle_sha256": inherited.get(
                "protocol_bundle_sha256"),
            **{key: inherited.get(key)
               for key in INHERITED_STATIC_GATES},
            "report_sha256": e2e.sha256_file(
                INHERITED_STATIC_REPORT),
        }
        report["static_protocol_v5_causal_closure"] = {
            "status": causal.get("status"),
            "protocol_version": causal.get("protocol_version"),
            "protocol_bundle_sha256": causal.get(
                "protocol_bundle_sha256"),
            **{key: causal.get(key) for key in CAUSAL_STATIC_GATES},
            "causal_terminal_conditions": causal.get(
                "causal_terminal_conditions"),
            "causal_phases": causal.get("causal_phases"),
            "report_sha256": e2e.sha256_file(CAUSAL_STATIC_REPORT),
        }
        report["authoritative_entrypoint"] = (
            "prove_complete_observatory_protocol_v5.py")
        report["causal_genome_ablation_bound"] = True
        report["genome_aware_local_provider_used"] = True
        with open(E2E_REPORT, "w", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False,
                      indent=1, sort_keys=True)
    return code


if __name__ == "__main__":
    sys.exit(main())
