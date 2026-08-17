#!/usr/bin/env python3
"""Hardening layer for the authoritative protocol-v5 zero-cost E2E proof.

The underlying driver retains the readable owner-gate, crash/resume and artifact-verification flow.
This layer forces the production container backend, requires every final protocol-v5 route in the
owner-signed census, verifies streaming formal crowns, and independently rechecks source-bound,
diversified executable-genome qualification, replication and crown evidence. It never contacts the
real DeepSeek endpoint.
"""
from __future__ import annotations

import glob
import json
import os

import prove_complete_observatory_protocol as base

GENOME_CONDITIONS = {
    "genome_realization_proven",
    "genome_realization_replication_passed",
    "genome_realization_crown_passed",
}
base.EXPECTED_NEW_CONDITIONS.update(GENOME_CONDITIONS)
base.REQUIRED_PROTOCOL_FILES.update({
    "profiles/national-observatory/GENOME-REALIZATION-CONTRACT.md",
    "private-evaluator/evaluator/observatory_formal_arena_v3.py",
    "executable-orchestrator/lawmax21/observatory_build_schema_hardening.py",
    "executable-orchestrator/lawmax21/observatory_semantic_evidence_binding_hardening.py",
    "executable-orchestrator/lawmax21/observatory_formal_streaming_routing.py",
    "executable-orchestrator/lawmax21/observatory_genome_realization_overlay.py",
    "executable-orchestrator/lawmax21/observatory_genome_auditor_diversity_hardening.py",
    "executable-orchestrator/lawmax21/observatory_genome_evidence_binding_hardening.py",
    "executable-orchestrator/lawmax21/observatory_setup_v4.py",
    "executable-orchestrator/lawmax21/observatory_preflight_v5.py",
    "executable-orchestrator/tools/mock_observatory_protocol_server.py",
    "executable-orchestrator/tools/mock_observatory_genome_server.py",
    "executable-orchestrator/tools/prove_observatory_protocol_static_v3.py",
    "executable-orchestrator/tools/prove_complete_observatory_protocol_v3.py",
})

_original_py = base.py
_original_verify = base.verify_protocol


def _container_py(path, *args, cwd=None, env=None, timeout=28800):
    values = list(args)
    if os.path.basename(path) == "run_observatory.py" and "--backend" in values:
        index = values.index("--backend")
        if index + 1 >= len(values):
            raise RuntimeError("proof runner has malformed --backend argument")
        values[index + 1] = "container"
    return _original_py(path, *values, cwd=cwd, env=env, timeout=timeout)


def _read(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _verify_genome_report(path, label, incumbent):
    if not os.path.isfile(path):
        raise RuntimeError(f"{label}: genome-realization report missing: {path}")
    report = _read(path)
    if report.get("status") != "PASS" or report.get("passed") is not True \
            or report.get("consensus") is not True \
            or report.get("all_axes_realized") is not True \
            or report.get("candidate_id") != incumbent:
        raise RuntimeError(f"{label}: genome-realization report did not pass")
    auditors = report.get("auditors") or []
    if len(auditors) != 2 \
            or len({row.get("auditor_id") for row in auditors}) != 2 \
            or len({row.get("logical_id") for row in auditors}) != 2 \
            or len({row.get("report_sha256") for row in auditors}) != 2:
        raise RuntimeError(f"{label}: genome auditors are not independent")
    for auditor in auditors:
        axes = auditor.get("validated_axes") or []
        if len(axes) != 13:
            raise RuntimeError(f"{label}: auditor did not validate all thirteen axes")
        for axis in axes:
            diversity = axis.get("auditor_definition_diversity") or {}
            if axis.get("source_bound_evidence") is not True:
                raise RuntimeError(
                    f"{label}/{axis.get('axis')}: evidence is not bound to current source bytes")
            if not axis.get("verified_symbols") \
                    or not axis.get("verified_invariant_ids") \
                    or not axis.get("verified_evidence"):
                raise RuntimeError(
                    f"{label}/{axis.get('axis')}: executable citation proof is incomplete")
            if int(diversity.get("unique_definition_citations", 0)) < 8 \
                    or int(diversity.get("maximum_axes_per_definition", 99)) > 4:
                raise RuntimeError(
                    f"{label}/{axis.get('axis')}: auditor definition map is too generic")
    return report


def _verify(repo, runtime, source_head, preflight, launch):
    verified = _original_verify(repo, runtime, source_head, preflight, launch)
    backend = (preflight.get("container_backend") or {}).get("backend")
    if backend != "container":
        raise RuntimeError("full E2E proof did not exercise production container isolation")

    mission = preflight.get("signed_mission") or {}
    if mission.get("protocol_version") != "OBSERVATORY-OMEGA-RESEARCH-PROTOCOL-5":
        raise RuntimeError("hardened E2E is not bound to owner-signed protocol v5")
    for flag in (
            "executable_genome_realization_required",
            "strict_executable_source_schema_required",
            "bounded_candidate_output_required",
            "terminal_negative_proof_required"):
        if mission.get(flag) is not True:
            raise RuntimeError("signed protocol-v5 mission flag missing: " + flag)

    mission_files = set(mission.get("research_protocol_files") or [])
    missing = sorted(base.REQUIRED_PROTOCOL_FILES - mission_files)
    if missing:
        raise RuntimeError("signed protocol omitted final routes: " + ", ".join(missing))

    incumbent = verified["incumbent"]
    formal_paths = glob.glob(os.path.join(
        runtime, "reports", f"formal-crown-{incumbent}-*.json"))
    if len(formal_paths) != 2:
        raise RuntimeError("streaming formal crown report count is not two")
    for path in formal_paths:
        report = _read(path)
        if report.get("behavioral_digest_mode") != \
                "ordered-length-delimited-stream-v1":
            raise RuntimeError(
                os.path.basename(path)
                + ": crown did not use streaming formal digest mode")

    architecture = os.path.join(runtime, "architecture")
    genome_reports = {
        "qualification": _verify_genome_report(os.path.join(
            architecture, f"genome-realization-qualification-{incumbent}.json"),
            "qualification", incumbent),
        "replication": _verify_genome_report(os.path.join(
            architecture, f"genome-realization-replication-{incumbent}.json"),
            "replication", incumbent),
        "crown": _verify_genome_report(os.path.join(
            architecture, f"genome-realization-crown-{incumbent}.json"),
            "crown", incumbent),
    }

    summary = verified["summary"]
    conditions = (summary.get("escalation") or {}).get("conditions") or {}
    supremacy = (summary.get("escalation") or {}).get("supremacy") or {}
    for condition in GENOME_CONDITIONS:
        if conditions.get(condition) is not True \
                or supremacy.get(condition) is not True:
            raise RuntimeError("terminal proof does not carry condition: " + condition)

    audit = verified["audit"]
    if audit.get("proof_mode") is not True \
            or (audit.get("workload_policy") or {}).get("proof_mode") is not True:
        raise RuntimeError("zero-cost workload was not explicitly audited")
    campaign = (audit.get("campaigns") or {}).get(
        "controlled_genome_realization") or {}
    if campaign.get("qualification") is not True \
            or campaign.get("replication") is not True \
            or campaign.get("crown") is not True \
            or campaign.get("auditors") != 2 \
            or campaign.get("axes") != 13:
        raise RuntimeError(
            "independent audit did not reproduce genome-realization closure")

    verified["exact_candidate_backend"] = "container"
    verified["streaming_formal_crown_verified"] = True
    verified["genome_realization_verified"] = {
        label: {
            "genome_sha256": report.get("genome_sha256"),
            "contract_sha256": report.get("contract_sha256"),
            "auditors": len(report.get("auditors") or []),
            "axes_per_auditor": 13,
            "source_bound": True,
            "definition_diversity": True,
        }
        for label, report in genome_reports.items()
    }
    return verified


base.py = _container_py
base.verify_protocol = _verify
main = base.main
sha256_file = base.sha256_file

__all__ = ["main", "sha256_file"]


if __name__ == "__main__":
    import sys
    sys.exit(main())
