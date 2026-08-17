"""Add foundational repository, mission, log and accounting evidence to the supremacy dossier.

The crown/search dossier is incomplete if it can be detached from the exact CP1 target, pre-frontier
CP2 quarantine, hidden-bank commitment, signed event log, budget ledger or owner-gate subjects. This
wrapper extends the deterministic dossier builder before its handler is installed, verifies those
facts mechanically and hashes immutable snapshots of the exact persisted bytes into the same evidence
index.
"""
from __future__ import annotations

import os
import tempfile

from . import observatory_supremacy_dossier_overlay as dossier
from .canonical import atomic_write_json, read_json
from .handlers import A


def _add(ctx, path, label, rows, parsed, require_pass=False):
    row, obj = dossier._evidence(
        ctx, path, require_pass=require_pass, label=label)
    if row["path"] in {current["path"] for current in rows}:
        raise RuntimeError(
            "supremacy dossier foundational evidence duplicates path: "
            + row["path"])
    rows.append(row)
    parsed[label] = obj
    return row, obj


def _snapshot_bytes(source, destination):
    """Create an atomic immutable receipt for bytes that will legitimately change later."""
    source = os.path.abspath(source)
    destination = os.path.abspath(destination)
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    with open(source, "rb") as handle:
        payload = handle.read()
    fd, temporary = tempfile.mkstemp(
        prefix=".signed-log-snapshot-", dir=os.path.dirname(destination))
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
        try:
            directory_fd = os.open(os.path.dirname(destination), os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except OSError:
            pass
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return destination


def install(_ctx, handlers):
    if getattr(dossier, "_foundation_hardening_installed", False):
        return dict(handlers)
    original = dossier._build_dossier

    def build(context, original_conditions):
        path, artifact = original(context, original_conditions)
        rows = list(artifact.get("evidence_index") or [])
        parsed = {}

        _add(context, A(context, "reports", "preflight.json"),
             "protocol_preflight", rows, parsed)
        _add(context, A(context, "reports", "evidence_vault.json"),
             "evidence_vault", rows, parsed)
        _add(context, A(context, "audit", "charter_freeze.json"),
             "charter_freeze", rows, parsed)
        _add(context, A(context, "audit", "hidden_commitment.json"),
             "hidden_bank_commitment", rows, parsed)
        _add(context, A(context, "reality", "REPOSITORY-REALITY-MODEL.json"),
             "cp1_repository_reality", rows, parsed)
        _add(context, A(context, "reality", "HISTORICAL-EXPERIMENT-MAP.json"),
             "historical_experiment_quarantine", rows, parsed)
        _add(context, A(context, "reports", "coverage_report.json"),
             "cp1_reuse_coverage", rows, parsed)
        _add(context, A(context, "candidates", "arena.json"),
             "candidate_arena", rows, parsed)
        v0_row, _ = _add(context, A(context, "gates", "v0_subject.json"),
                         "owner_v0_subject", rows, parsed)
        _add(context, A(context, "architecture", "target_v1_evidence_revised.json"),
             "evidence_revised_target_v1", rows, parsed)
        v1_row, _ = _add(context, A(context, "gates", "v1_subject.json"),
                         "owner_v1_subject", rows, parsed)
        migration_row, _ = _add(
            context, A(context, "architecture", "migration_plan.json"),
            "owner_migration_subject", rows, parsed)
        _add(context, A(context, "budget", "ledger.json"),
             "provider_budget_ledger", rows, parsed)

        # The signed log receives the INDEPENDENT_AUDIT and terminal transitions after this handler
        # returns. Hashing its live path would therefore create a self-invalidating dossier. Snapshot
        # the already verified pre-audit prefix and hash that immutable receipt instead.
        live_log = A(context, "state", "events.jsonl")
        log_snapshot = _snapshot_bytes(
            live_log, A(context, "audit", "signed-event-log-before-audit.jsonl"))
        log_row, _ = _add(
            context, log_snapshot, "signed_event_log_before_audit", rows, parsed)

        preflight = parsed["protocol_preflight"] or {}
        if preflight.get("ok") is not True:
            raise RuntimeError("supremacy dossier: protocol preflight did not report ok=true")
        reality = parsed["cp1_repository_reality"] or {}
        history = parsed["historical_experiment_quarantine"] or {}
        coverage = parsed["cp1_reuse_coverage"] or {}
        if reality.get("repository_archaeology_api_calls") != 0:
            raise RuntimeError("supremacy dossier: CP1 reuse made repository-archaeology calls")
        if history.get("prior_cp2_content_read") is not False:
            raise RuntimeError("supremacy dossier: prior CP2 leaked before the frontier")
        if coverage.get("certified") is not True \
                or coverage.get("mode") != "REUSED_SEALED_CP1" \
                or coverage.get("uningested_count") != 0:
            raise RuntimeError("supremacy dossier: sealed CP1 reuse is not certified")

        log_ok, event_count, log_reason = context.log.verify()
        if not log_ok:
            raise RuntimeError(
                "supremacy dossier: signed event log failed verification: "
                + str(log_reason))
        with open(live_log, "rb") as live, open(log_snapshot, "rb") as snapshot:
            if live.read() != snapshot.read():
                raise RuntimeError(
                    "supremacy dossier: event-log snapshot differs before audit transition")
        if not context.ledger.within_ceiling():
            raise RuntimeError("supremacy dossier: provider ledger exceeds signed ceiling")
        ledger = parsed["provider_budget_ledger"] or {}
        if ledger.get("currency") != "USD" \
                or not isinstance(ledger.get("entries"), list):
            raise RuntimeError("supremacy dossier: provider ledger is malformed")

        expected_gate_subjects = {
            "GATE-ARCH-V0": v0_row["sha256"],
            "GATE-ARCH-V1": v1_row["sha256"],
            "GATE-MIGRATION": migration_row["sha256"],
        }
        # Approval files are already in the original evidence index. Reopen their signed envelopes
        # and prove the payload subject hashes match the exact indexed subject bytes above.
        approvals = {}
        for gate, expected_subject in expected_gate_subjects.items():
            approval_path = A(context, "gates", f"{gate}.approval.json")
            approval = read_json(approval_path)
            payload = approval.get("payload") or {}
            observed = payload.get("subject_sha256")
            if payload.get("gate") != gate \
                    or payload.get("run_id") != context.run_id \
                    or payload.get("decision") != "APPROVE" \
                    or observed != expected_subject:
                raise RuntimeError(
                    f"supremacy dossier: {gate} signed approval is not bound to its indexed subject")
            approvals[gate] = {
                "approval_path": os.path.relpath(
                    approval_path, context.runtime).replace("\\", "/"),
                "subject_sha256": expected_subject,
                "decision": payload.get("decision"),
                "signer_key_id": payload.get("signer_key_id"),
            }

        artifact["evidence_index"] = rows
        artifact["foundation"] = {
            "protocol_preflight_ok": True,
            "cp1_reused_without_repository_archaeology_calls": True,
            "prior_cp2_quarantined_until_independent_frontier": True,
            "hidden_bank_committed": True,
            "signed_event_log_verified": True,
            "signed_event_log_snapshot_path": log_row["path"],
            "signed_event_log_snapshot_sha256": log_row["sha256"],
            "signed_event_log_events_before_audit": event_count,
            "signed_event_log_reason": log_reason,
            "provider_budget_within_owner_ceiling": True,
            "provider_ledger_entries": len(ledger["entries"]),
            "owner_gate_subject_bindings": approvals,
        }
        atomic_write_json(path, artifact)
        return path, artifact

    dossier._build_dossier = build
    dossier._foundation_hardening_installed = True
    return dict(handlers)
