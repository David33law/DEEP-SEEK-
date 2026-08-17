#!/usr/bin/env python3
"""Portable owner-signature extension of the hardened protocol-v5 Docker E2E proof."""
from __future__ import annotations

import json
import os

import prove_complete_observatory_protocol_hardened as base

_original_verify_dossier = base._verify_dossier


def _read(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _verify_dossier(repo, runtime, audit, incumbent, conditions, supremacy,
                    mission, source_head):
    dossier = _original_verify_dossier(
        repo, runtime, audit, incumbent, conditions, supremacy,
        mission, source_head)
    foundation = dossier.get("foundation") or {}
    portable = dossier.get("portable_owner_verification_material") or {}
    if foundation.get("owner_gate_signatures_cryptographically_verified") is not True:
        raise RuntimeError(
            "dossier did not cryptographically reverify owner-gate signatures")

    evidence = {
        row.get("path"): row for row in dossier.get("evidence_index") or []}
    public_relative = foundation.get("owner_public_key_snapshot_path")
    decisions_relative = foundation.get("signed_owner_decisions_snapshot_path")
    if public_relative != "audit/OWNER-PUBLIC-KEY.hex" \
            or decisions_relative != "audit/OWNER-DECISIONS.signed.json":
        raise RuntimeError("portable owner-verification snapshot paths drifted")
    for relative, expected in (
            (public_relative, foundation.get("owner_public_key_snapshot_sha256")),
            (decisions_relative, foundation.get("signed_owner_decisions_snapshot_sha256"))):
        row = evidence.get(relative) or {}
        path = os.path.join(runtime, *relative.split("/"))
        if not os.path.isfile(path) \
                or row.get("sha256") != expected \
                or base.sha256_file(path) != expected:
            raise RuntimeError(
                "portable owner-verification snapshot hash mismatch: " + relative)

    decisions_source = os.path.join(repo, "OWNER-DECISIONS.signed.json")
    public_source = os.path.join(
        repo, "immutable-package", "OWNER-PUBLIC-KEY.hex")
    if base.sha256_file(decisions_source) != \
            foundation["signed_owner_decisions_snapshot_sha256"]:
        raise RuntimeError("signed decisions snapshot differs from exact proof checkout")
    if base.sha256_file(public_source) != \
            foundation["owner_public_key_snapshot_sha256"]:
        raise RuntimeError("owner public-key snapshot differs from exact proof checkout")

    gates = foundation.get("owner_gate_signature_verification") or {}
    if set(gates) != {"GATE-ARCH-V0", "GATE-ARCH-V1", "GATE-MIGRATION"}:
        raise RuntimeError("portable owner-verification gate set is incomplete")
    for gate, row in gates.items():
        if row.get("cryptographic_signature_verified") is not True \
                or len(str(row.get("approval_sha256") or "")) != 64 \
                or len(str(row.get("subject_sha256") or "")) != 64:
            raise RuntimeError(gate + ": portable cryptographic receipt is incomplete")
        approval_relative = row.get("approval_path")
        approval_path = os.path.join(
            runtime, *str(approval_relative).replace("\\", "/").split("/"))
        if base.sha256_file(approval_path) != row["approval_sha256"]:
            raise RuntimeError(gate + ": approval snapshot hash mismatch")

    if portable.get("public_key") != evidence[public_relative] \
            or portable.get("signed_decisions") != evidence[decisions_relative] \
            or portable.get("gates") != gates:
        raise RuntimeError("portable owner-verification material disagrees with foundation")
    dossier["portable_owner_signature_e2e_verified"] = True
    return dossier


base._verify_dossier = _verify_dossier
main = base.main
sha256_file = base.sha256_file

__all__ = ["main", "sha256_file"]


if __name__ == "__main__":
    import sys
    sys.exit(main())
