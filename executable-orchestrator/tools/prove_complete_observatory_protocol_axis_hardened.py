#!/usr/bin/env python3
"""Axis-specific attribution extension of the causal protocol-v5 Docker E2E proof.

The inherited proof already verifies exact mutated source bytes, evaluator receipts, inert controls,
portable owner signatures, every arena and the deterministic dossier. This extension additionally
requires every causal task to fail for a mechanically persisted reason relevant to the controlled
axis and artifact group rather than from an unrelated candidate defect or successful receipt metadata.
"""
from __future__ import annotations

import json
import os

import prove_complete_observatory_protocol_causal_provider_hardened as previous

CORE = previous.base.CORE
AXIS_FILES = {
    "executable-orchestrator/lawmax21/"
    "observatory_causal_axis_attribution_hardening.py",
    "executable-orchestrator/lawmax21/"
    "observatory_causal_attribution_scope_hardening.py",
    "executable-orchestrator/tools/"
    "prove_complete_observatory_protocol_axis_hardened.py",
}
for relative in AXIS_FILES:
    previous.base.CAUSAL_FILES.add(relative)
    CORE.REQUIRED_PROTOCOL_FILES.add(relative)
_ORIGINAL_VERIFY = CORE.verify_protocol


def _read(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _runtime_path(runtime, relative):
    path = os.path.abspath(os.path.join(
        runtime, *str(relative).replace("\\", "/").split("/")))
    root = os.path.abspath(runtime)
    if path != root and not path.startswith(root + os.sep):
        raise RuntimeError(
            "axis-attribution E2E evidence escapes runtime: "
            + str(relative))
    return path


def _verify_campaign(runtime, incumbent, label):
    genome_path = os.path.join(
        runtime, "architecture",
        f"genome-realization-{label}-{incumbent}.json")
    genome_report = _read(genome_path)
    receipt = genome_report.get("causal_ablation_evidence") or {}
    causal_path = _runtime_path(runtime, receipt.get("path"))
    causal = _read(causal_path)
    tasks = causal.get("tasks") or []
    if not tasks:
        raise RuntimeError(
            f"axis-specific causal {label}: campaign has no tasks")
    attributed = []
    for task in tasks:
        details = task.get("attribution") or {}
        if task.get("axis_specific_failure_attributed") is not True \
                or task.get("causal_failure_observed") is not True \
                or task.get("observed_candidate_pass") is not False \
                or not details.get("mode") \
                or details.get("whole_receipt_searched") is not False:
            raise RuntimeError(
                f"axis-specific causal {label}: unrelated, unattributed or "
                f"whole-receipt-derived failure for {task.get('auditor_id')}/"
                f"{task.get('axis')}/{task.get('group')}")
        if details.get("mode") == "semantic-hard-dimension":
            if not details.get("matched_dimensions") \
                    and details.get("removed_definition_named") is not True:
                raise RuntimeError(
                    f"axis-specific causal {label}: semantic task has no "
                    "matched hard dimension or removed-definition evidence")
        elif details.get("mode") == "specialized-failure-signature":
            if not details.get("matched_axis_or_group_tokens") \
                    and details.get("removed_definition_named") is not True:
                raise RuntimeError(
                    f"axis-specific causal {label}: specialized task has no "
                    "axis/group failure signature")
        else:
            raise RuntimeError(
                f"axis-specific causal {label}: unknown attribution mode "
                + str(details.get("mode")))
        attributed.append({
            "auditor_id": task.get("auditor_id"),
            "axis": task.get("axis"),
            "group": task.get("group"),
            "artifact": task.get("artifact"),
            "mode": details.get("mode"),
            "failure_payload_fields": details.get(
                "failure_payload_fields") or [],
        })
    if len(attributed) != int(causal.get("tasks_executed", -1)):
        raise RuntimeError(
            f"axis-specific causal {label}: attributed task count drift")
    return {
        "campaign_path": receipt.get("path"),
        "campaign_sha256": receipt.get("sha256"),
        "tasks": len(tasks),
        "axis_specific_tasks": len(attributed),
        "attribution_modes": sorted({row["mode"] for row in attributed}),
        "whole_receipt_searched": False,
    }


def _verify(repo, runtime, source_head, preflight, launch):
    verified = _ORIGINAL_VERIFY(
        repo, runtime, source_head, preflight, launch)
    mission = preflight.get("signed_mission") or {}
    if mission.get("axis_specific_causal_attribution_required") is not True:
        raise RuntimeError(
            "signed mission does not require axis-specific causal attribution")
    files = set(mission.get("research_protocol_files") or [])
    missing = sorted(AXIS_FILES - files)
    if missing:
        raise RuntimeError(
            "signed protocol omitted axis-attribution files: "
            + ", ".join(missing))

    incumbent = verified["incumbent"]
    campaigns = {
        label: _verify_campaign(runtime, incumbent, label)
        for label in ("replication", "crown")}
    audit = verified["audit"]
    causal_audit = (audit.get("campaigns") or {}).get(
        "causal_genome_ablation") or {}
    if causal_audit.get("axis_specific_attribution_required") is not True \
            or causal_audit.get(
                "all_tasks_axis_specifically_attributed") is not True:
        raise RuntimeError(
            "independent audit did not reproduce axis-specific causal attribution")

    dossier_path = os.path.join(
        runtime, "architecture", "OMEGA-SUPREMACY-DOSSIER.json")
    dossier = _read(dossier_path)
    causal_dossier = dossier.get("causal_genome_realization") or {}
    for label, campaign in campaigns.items():
        receipt = causal_dossier.get(label) or {}
        if receipt.get("axis_specific_failure_attribution") is not True \
                or int(receipt.get("axis_specific_tasks", 0)) != \
                campaign["axis_specific_tasks"]:
            raise RuntimeError(
                f"supremacy dossier does not bind axis-specific {label} "
                "causal evidence")

    verified["axis_specific_causal_attribution_verified"] = campaigns
    return verified


CORE.verify_protocol = _verify
main = previous.main
sha256_file = previous.sha256_file

__all__ = ["main", "sha256_file"]


if __name__ == "__main__":
    import sys
    sys.exit(main())
