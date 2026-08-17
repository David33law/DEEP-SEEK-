"""Add foundational repository, mission, log and accounting evidence to the supremacy dossier.

The crown/search dossier is incomplete if it can be detached from the exact CP1 target, pre-frontier
CP2 quarantine, hidden-bank commitment, signed event log, budget ledger or owner-gate subjects. This
wrapper extends the deterministic dossier builder before its handler is installed, verifies those
facts mechanically and hashes the exact persisted bytes into the same evidence index.
"""
from __future__ import annotations

import os

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
        _add(context, A(context, "gates", "v0_subject.json"),
             "owner_v0_subject", rows, parsed)
        _add(context, A(context, "architecture", "target_v1_evidence_revised.json"),
             "owner_v1_subject", rows, parsed)
        _add(context, A(context, "architecture", "migration_plan.json"),
             "owner_migration_subject", rows, parsed)
        _add(context, A(context, "budget", "ledger.json"),
             "provider_budget_ledger", rows, parsed)
        _add(context, A(context, "state", "events.jsonl"),
             "signed_event_log_before_audit", rows, parsed)

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
        if not context.ledger.within_ceiling():
            raise RuntimeError("supremacy dossier: provider ledger exceeds signed ceiling")
        ledger = parsed["provider_budget_ledger"] or {}
        if ledger.get("currency") != "USD" \
                or not isinstance(ledger.get("entries"), list):
            raise RuntimeError("supremacy dossier: provider ledger is malformed")

        expected_gate_subjects = {
            "GATE-ARCH-V0": rows[-5]["sha256"],
            "GATE-ARCH-V1": rows[-4]["sha256"],
            "GATE-MIGRATION": rows[-3]["sha256"],
        }
        # Approval files are already in the original evidence index. Reopen them and prove that the
        # persisted signed approval subject hashes match the exact subject bytes indexed above.
        approvals = {}
        for gate, expected_subject in expected_gate_subjects.items():
            approval_path = A(context, "gates", f"{gate}.approval.json")
            approval = read_json(approval_path)
            observed = (approval.get("subject_sha256")
                        or approval.get("subject")
                        or approval.get("subject_hash"))
            if observed != expected_subject:
                raise RuntimeError(
                    f"supremacy dossier: {gate} approval is not bound to its indexed subject")
            approvals[gate] = {
                "approval_path": os.path.relpath(
                    approval_path, context.runtime).replace("\\", "/"),
                "subject_sha256": expected_subject,
            }

        artifact["evidence_index"] = rows
        artifact["foundation"] = {
            "protocol_preflight_ok": True,
            "cp1_reused_without_repository_archaeology_calls": True,
            "prior_cp2_quarantined_until_independent_frontier": True,
            "hidden_bank_committed": True,
            "signed_event_log_verified": True,
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
