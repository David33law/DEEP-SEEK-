#!/usr/bin/env python3
"""Final protocol-v5 proof: portable-owner static closure followed by hardened Docker E2E."""
from __future__ import annotations

import json
import os
import subprocess
import sys

import prove_complete_observatory_protocol_signature_hardened as e2e

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
STATIC = os.path.join(HERE, "prove_observatory_protocol_static_v4.py")
STATIC_REPORT = os.path.join(
    ROOT, "proof", "observatory-protocol-static-v5.json")
E2E_REPORT = os.path.join(
    ROOT, "proof", "complete-observatory-protocol-e2e.json")
PROTOCOL_VERSION = "OBSERVATORY-OMEGA-RESEARCH-PROTOCOL-5"
STATIC_GATES = (
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


def main(argv=None):
    static_run = subprocess.run(
        [sys.executable, STATIC], capture_output=True, text=True,
        timeout=3600,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    if static_run.returncode != 0:
        print(static_run.stdout)
        print(static_run.stderr, file=sys.stderr)
        return static_run.returncode
    with open(STATIC_REPORT, encoding="utf-8") as handle:
        static = json.load(handle)
    missing = []
    for key in STATIC_GATES:
        expected = "PASS" if key == "portable_owner_signature_static_extension" else True
        if static.get(key) != expected:
            missing.append(key)
    if static.get("status") != "PASS" \
            or static.get("protocol_version") != PROTOCOL_VERSION \
            or missing:
        static["entrypoint_missing_static_gates"] = missing
        print(json.dumps(static, ensure_ascii=False, indent=1, sort_keys=True))
        return 1

    code = e2e.main(argv)
    if os.path.isfile(E2E_REPORT):
        with open(E2E_REPORT, encoding="utf-8") as handle:
            report = json.load(handle)
        report["static_protocol_v5_portable_owner_closure"] = {
            "status": static.get("status"),
            "protocol_version": static.get("protocol_version"),
            "protocol_bundle_sha256": static.get("protocol_bundle_sha256"),
            "protocol_files": static.get("protocol_files"),
            **{key: static.get(key) for key in STATIC_GATES},
            "report_sha256": e2e.sha256_file(STATIC_REPORT),
        }
        with open(E2E_REPORT, "w", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=1, sort_keys=True)
    return code


if __name__ == "__main__":
    sys.exit(main())
