#!/usr/bin/env python3
"""Axis-behavioral attribution extension of the causal protocol-v5 Docker E2E proof.

The inherited proof verifies exact mutated source bytes, process/evaluator receipts, inert controls,
portable owner signatures, every arena and the deterministic dossier. This final axis layer requires
every causal task to expose a behavioral failure specific to the controlled axis. A removed definition
name, axis vocabulary in its AST body or a failed path from the same broad artifact group is retained
as diagnostic context but can never independently earn causal credit.
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
    "executable-orchestrator/lawmax21/"
    "observatory_causal_definition_semantics_hardening.py",
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


def _definition_receipt_valid(details):
    vocabulary = details.get("definition_vocabulary_sha256")
    body_hashes = details.get("definition_body_sha256") or {}
    inputs = details.get("definition_vocabulary_sha256_inputs") or []
    return bool(
        inputs
        and isinstance(vocabulary, str)
        and len(vocabulary) == 64
        and isinstance(body_hashes, dict)
        and set(body_hashes) == set(inputs)
        and all(isinstance(value, str) and len(value) == 64
                for value in body_hashes.values()))


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
            f"axis-behavioral causal {label}: campaign has no tasks")
    attributed = []
    for task in tasks:
        details = task.get("attribution") or {}
        if task.get("axis_specific_failure_attributed") is not True \
                or task.get("causal_failure_observed") is not True \
                or task.get("observed_candidate_pass") is not False \
                or details.get("behavioral_axis_evidence") is not True \
                or details.get("whole_receipt_searched") is not False \
                or details.get(
                    "removed_definition_name_is_sufficient") is not False \
                or not _definition_receipt_valid(details):
            raise RuntimeError(
                f"axis-behavioral causal {label}: unrelated, unattributed "
                f"or non-behavioral failure for {task.get('auditor_id')}/"
                f"{task.get('axis')}/{task.get('group')}")

        mode = details.get("mode")
        if mode == "semantic-hard-dimension":
            if not details.get("matched_dimensions"):
                raise RuntimeError(
                    f"axis-behavioral causal {label}: semantic task has no "
                    "axis-mapped violated hard dimension")
        elif mode == "specialized-failure-signature":
            if not details.get("matched_axis_failure_tokens") \
                    or details.get("group_path_is_sufficient") is not False:
                raise RuntimeError(
                    f"axis-behavioral causal {label}: specialized task has "
                    "no axis-specific behavioral failure signature")
        else:
            raise RuntimeError(
                f"axis-behavioral causal {label}: unknown attribution mode "
                + str(mode))
        attributed.append({
            "auditor_id": task.get("auditor_id"),
            "axis": task.get("axis"),
            "group": task.get("group"),
            "artifact": task.get("artifact"),
            "mode": mode,
            "behavioral_axis_evidence": True,
            "definition_vocabulary_sha256": details[
                "definition_vocabulary_sha256"],
            "definition_body_sha256": details["definition_body_sha256"],
            "failure_payload_fields": details.get(
                "failure_payload_fields") or [],
        })
    if len(attributed) != int(causal.get("tasks_executed", -1)):
        raise RuntimeError(
            f"axis-behavioral causal {label}: attributed task count drift")
    return {
        "campaign_path": receipt.get("path"),
        "campaign_sha256": receipt.get("sha256"),
        "tasks": len(tasks),
        "axis_specific_tasks": len(attributed),
        "axis_behavioral_failures": len(attributed),
        "attribution_modes": sorted({row["mode"] for row in attributed}),
        "whole_receipt_searched": False,
        "removed_definition_name_is_sufficient": False,
        "group_failure_path_is_sufficient": False,
        "cited_definition_semantics_checked": True,
        "definition_body_hashes_checked": True,
    }


def _verify(repo, runtime, source_head, preflight, launch):
    verified = _ORIGINAL_VERIFY(
        repo, runtime, source_head, preflight, launch)
    mission = preflight.get("signed_mission") or {}
    for flag in (
            "axis_specific_causal_attribution_required",
            "axis_specific_behavioral_failure_required"):
        if mission.get(flag) is not True:
            raise RuntimeError(
                "signed mission does not require " + flag)
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
                "all_tasks_axis_specifically_attributed") is not True \
            or causal_audit.get(
                "axis_specific_behavioral_failure_required") is not True \
            or causal_audit.get(
                "all_tasks_axis_behaviorally_falsified") is not True \
            or causal_audit.get(
                "removed_definition_name_is_sufficient") is not False \
            or causal_audit.get(
                "group_failure_path_is_sufficient") is not False:
        raise RuntimeError(
            "independent audit did not reproduce axis-behavioral causal attribution")

    dossier_path = os.path.join(
        runtime, "architecture", "OMEGA-SUPREMACY-DOSSIER.json")
    dossier = _read(dossier_path)
    causal_dossier = dossier.get("causal_genome_realization") or {}
    for label, campaign in campaigns.items():
        dossier_receipt = causal_dossier.get(label) or {}
        if dossier_receipt.get(
                "axis_specific_failure_attribution") is not True \
                or dossier_receipt.get(
                    "axis_specific_behavioral_failure_required") is not True \
                or int(dossier_receipt.get("axis_specific_tasks", 0)) != \
                campaign["axis_specific_tasks"] \
                or int(dossier_receipt.get("axis_behavioral_failures", 0)) != \
                campaign["axis_behavioral_failures"] \
                or dossier_receipt.get(
                    "removed_definition_name_is_sufficient") is not False \
                or dossier_receipt.get(
                    "group_failure_path_is_sufficient") is not False \
                or dossier_receipt.get("whole_receipt_searched") is not False:
            raise RuntimeError(
                f"supremacy dossier does not bind axis-behavioral {label} "
                "causal evidence")

    verified["axis_specific_causal_attribution_verified"] = campaigns
    verified["axis_specific_behavioral_failure_verified"] = True
    return verified


CORE.verify_protocol = _verify
main = previous.main
sha256_file = previous.sha256_file

__all__ = ["main", "sha256_file"]


if __name__ == "__main__":
    import sys
    sys.exit(main())
