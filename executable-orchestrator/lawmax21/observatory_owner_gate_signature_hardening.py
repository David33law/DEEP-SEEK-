"""Cryptographically reproduce owner-gate approval and mission identity inside the final dossier.

The state machine already verifies approvals before each gated transition, but a portable supremacy
dossier should not rely on that historical control-flow fact alone. This wrapper snapshots the owner
public key and signed owner decisions into the runtime, indexes their exact hashes, and independently
calls the same trusted ``verify_approval`` primitive over every pre-terminal owner gate and its exact
indexed subject before the dossier may become a terminal condition.
"""
from __future__ import annotations

import os

from . import observatory_supremacy_dossier_hardening as foundation
from . import observatory_supremacy_dossier_overlay as dossier
from .canonical import atomic_write_json, read_json, sha256_file
from .handlers import A
from .signing import SignatureRejected, verify_approval


def _append_evidence(context, artifact, path, label):
    row, _parsed = dossier._evidence(context, path, label=label)
    rows = artifact.setdefault("evidence_index", [])
    existing = next(
        (current for current in rows if current.get("path") == row["path"]),
        None)
    if existing is not None:
        if existing.get("sha256") != row.get("sha256") \
                or int(existing.get("bytes", -1)) != int(row.get("bytes", -2)):
            raise RuntimeError(
                "owner-signature dossier evidence changed during construction: "
                + row["path"])
        return existing
    rows.append(row)
    return row


def install(_ctx, handlers):
    if getattr(dossier, "_owner_signature_hardening_installed", False):
        return dict(handlers)
    original = dossier._build_dossier

    def build(context, original_conditions):
        path, artifact = original(context, original_conditions)
        public_source = os.path.join(
            context.root, "immutable-package", "OWNER-PUBLIC-KEY.hex")
        decisions_source = os.path.join(
            context.root, "OWNER-DECISIONS.signed.json")
        public_snapshot = foundation._snapshot_bytes(
            public_source, A(context, "audit", "OWNER-PUBLIC-KEY.hex"))
        decisions_snapshot = foundation._snapshot_bytes(
            decisions_source, A(context, "audit", "OWNER-DECISIONS.signed.json"))
        public_row = _append_evidence(
            context, artifact, public_snapshot, "owner_public_key_snapshot")
        decisions_row = _append_evidence(
            context, artifact, decisions_snapshot, "signed_owner_decisions_snapshot")

        protocol = artifact.get("protocol") or {}
        if decisions_row["sha256"] != protocol.get("signed_decisions_sha256"):
            raise RuntimeError(
                "supremacy dossier signed-decisions snapshot does not match protocol identity")
        if sha256_file(public_snapshot) != public_row["sha256"]:
            raise RuntimeError("supremacy dossier owner-public-key snapshot hash drift")

        foundation_row = artifact.get("foundation") or {}
        bindings = foundation_row.get("owner_gate_subject_bindings") or {}
        verified = {}
        for gate in ("GATE-ARCH-V0", "GATE-ARCH-V1", "GATE-MIGRATION"):
            binding = bindings.get(gate) or {}
            subject_sha256 = binding.get("subject_sha256")
            approval_relative = binding.get("approval_path")
            if not subject_sha256 or not approval_relative:
                raise RuntimeError(
                    f"supremacy dossier lacks owner-gate binding for {gate}")
            approval_path = os.path.abspath(os.path.join(
                context.runtime,
                *str(approval_relative).replace("\\", "/").split("/")))
            try:
                verify_approval(
                    read_json(approval_path), context.owner,
                    gate, context.run_id, subject_sha256)
            except SignatureRejected as exc:
                raise RuntimeError(
                    f"supremacy dossier owner approval failed cryptographic verification: "
                    f"{gate}: {exc}") from exc
            verified[gate] = {
                "approval_path": approval_relative,
                "approval_sha256": sha256_file(approval_path),
                "subject_sha256": subject_sha256,
                "cryptographic_signature_verified": True,
            }

        foundation_row.update({
            "owner_public_key_snapshot_path": public_row["path"],
            "owner_public_key_snapshot_sha256": public_row["sha256"],
            "signed_owner_decisions_snapshot_path": decisions_row["path"],
            "signed_owner_decisions_snapshot_sha256": decisions_row["sha256"],
            "owner_gate_signatures_cryptographically_verified": True,
            "owner_gate_signature_verification": verified,
        })
        artifact["foundation"] = foundation_row
        artifact["portable_owner_verification_material"] = {
            "public_key": public_row,
            "signed_decisions": decisions_row,
            "gates": verified,
        }
        atomic_write_json(path, artifact)
        return path, artifact

    dossier._build_dossier = build
    dossier._owner_signature_hardening_installed = True
    return dict(handlers)
