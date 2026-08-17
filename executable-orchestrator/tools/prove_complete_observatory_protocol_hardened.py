#!/usr/bin/env python3
"""Hardened protocol-v5 proof wrapper for the National Legal Observatory.

The readable base driver still owns clone, owner ceremony, crash/resume and gate traversal. This
wrapper upgrades its proof obligations to protocol v5, forces the exact production container backend,
routes the localhost provider through the final genome-aware mock, and independently verifies every
new controlled-genome condition and artifact without contacting the real provider.
"""
from __future__ import annotations

import glob
import json
import os
import subprocess

import prove_complete_observatory_protocol as base

GENOME_CONDITIONS = {
    "genome_realization_proven",
    "genome_realization_replication_passed",
    "genome_realization_crown_passed",
}
V5_FLAGS = {
    "cross_model_consistency_required",
    "executable_genome_realization_required",
    "strict_executable_source_schema_required",
    "bounded_candidate_output_required",
    "terminal_negative_proof_required",
    "authoritative_prior_art_challenge_required",
    "proof_mode_forbidden_in_production",
}
V5_FILES = {
    "profiles/national-observatory/GENOME-REALIZATION-CONTRACT.md",
    "executable-orchestrator/lawmax21/observatory_build_schema_hardening.py",
    "executable-orchestrator/lawmax21/observatory_genome_realization_overlay.py",
    "executable-orchestrator/lawmax21/observatory_formal_streaming_routing.py",
    "executable-orchestrator/lawmax21/observatory_setup_v4.py",
    "executable-orchestrator/lawmax21/observatory_preflight_v5.py",
    "private-evaluator/evaluator/observatory_formal_arena_v3.py",
    "executable-orchestrator/tools/mock_observatory_genome_server.py",
    "executable-orchestrator/tools/prove_observatory_protocol_static_v2.py",
}
PROTOCOL = "OBSERVATORY-OMEGA-RESEARCH-PROTOCOL-5"
REPORT = os.path.join(base.ROOT, "proof", "complete-observatory-protocol-e2e.json")

base.RUN_ID = "OBS-PROTOCOL-PROOF-V5-0001"
base.EXPECTED_NEW_CONDITIONS.update(GENOME_CONDITIONS)
base.REQUIRED_PROTOCOL_FILES.discard(
    "private-evaluator/evaluator/observatory_formal_arena_v2.py")
base.REQUIRED_PROTOCOL_FILES.update(V5_FILES)

_ORIGINAL_PY = base.py
_ORIGINAL_POPEN = base.subprocess.Popen


def _container_py(path, *args, cwd=None, env=None, timeout=28800):
    values = list(args)
    if os.path.basename(path) == "run_observatory.py" and "--backend" in values:
        index = values.index("--backend")
        if index + 1 >= len(values):
            raise RuntimeError("proof runner has malformed --backend argument")
        values[index + 1] = "container"
    return _ORIGINAL_PY(path, *values, cwd=cwd, env=env, timeout=timeout)


def _genome_mock_popen(command, *args, **kwargs):
    values = list(command)
    for index, value in enumerate(values):
        if os.path.basename(str(value)) == "mock_observatory_protocol_server.py":
            values[index] = os.path.join(
                os.path.dirname(str(value)), "mock_observatory_genome_server.py")
            break
    return _ORIGINAL_POPEN(values, *args, **kwargs)


def _checked_artifact(runtime, label, candidate_id):
    path = os.path.join(
        runtime, "architecture",
        f"genome-realization-{label}-{candidate_id}.json")
    report = base.assert_pass(path, f"genome realization {label}")
    if report.get("candidate_id") != candidate_id:
        raise RuntimeError(
            f"genome realization {label} names the wrong candidate")
    if report.get("independent_auditors") is not True:
        raise RuntimeError(
            f"genome realization {label} lacks independent auditors")
    if report.get("consensus") is not True \
            or report.get("all_axes_realized") is not True \
            or int(report.get("verified_axis_count", 0)) != 13:
        raise RuntimeError(
            f"genome realization {label} did not prove all thirteen axes")
    auditors = report.get("auditors") or []
    if len(auditors) != 2 \
            or len({row.get("auditor_id") for row in auditors}) != 2 \
            or len({row.get("logical_id") for row in auditors}) != 2 \
            or len({row.get("report_sha256") for row in auditors}) != 2:
        raise RuntimeError(
            f"genome realization {label} does not contain two independent receipts")
    source_census = report.get("source_census") or {}
    required_sources = {
        "semantic", "systems", "distributed", "scale",
        "formal_A", "formal_B", "interoperability_A", "interoperability_B"}
    if set(source_census) != required_sources:
        raise RuntimeError(
            f"genome realization {label} source census is incomplete")
    for artifact, row in source_census.items():
        if not row.get("sha256") or not row.get("definitions"):
            raise RuntimeError(
                f"genome realization {label}/{artifact} lacks definitions/hash")
    evidence = {
        row.get("path"): row for row in report.get("evidence_catalog") or []
        if isinstance(row, dict) and row.get("path")}
    if not evidence:
        raise RuntimeError(
            f"genome realization {label} has no persisted evidence catalog")
    for relative, row in evidence.items():
        absolute = os.path.join(runtime, *relative.split("/"))
        if not os.path.isfile(absolute):
            raise RuntimeError(
                f"genome realization {label} cites missing evidence {relative}")
        if row.get("sha256") != base.sha256_file(absolute):
            raise RuntimeError(
                f"genome realization {label} evidence hash drift: {relative}")
    for auditor in auditors:
        axes = auditor.get("validated_axes") or []
        if len(axes) != 13:
            raise RuntimeError(
                f"genome realization {label} auditor has {len(axes)} axes")
        for axis in axes:
            if not axis.get("verified_symbols") \
                    or not axis.get("verified_invariant_ids") \
                    or not axis.get("verified_evidence"):
                raise RuntimeError(
                    f"genome realization {label}/{axis.get('axis')} "
                    "lacks a reproducible citation class")
    return report


def _verify(repo, runtime, source_head, preflight, launch):
    summary = base.read_json(os.path.join(runtime, "reports", "run_summary.json"))
    if summary.get("final_state") != "COMMITTED" \
            or summary.get("log_verified") is not True:
        raise RuntimeError(
            "run did not finish COMMITTED with a verified signed log")
    escalation = summary.get("escalation") or {}
    conditions = escalation.get("conditions") or {}
    if not conditions or any(value is not True for value in conditions.values()):
        raise RuntimeError(
            "terminal conditions are incomplete: "
            + ", ".join(key for key, value in conditions.items() if not value))
    missing = sorted(base.EXPECTED_NEW_CONDITIONS - set(conditions))
    if missing:
        raise RuntimeError(
            "protocol-v5 terminal conditions absent: " + ", ".join(missing))
    supremacy = escalation.get("supremacy") or {}
    failed = sorted(
        key for key in base.EXPECTED_NEW_CONDITIONS
        if supremacy.get(key) is not True)
    if failed:
        raise RuntimeError(
            "protocol-v5 supremacy summary is incomplete: " + ", ".join(failed))

    mission = preflight.get("signed_mission") or {}
    if mission.get("protocol_version") != PROTOCOL:
        raise RuntimeError("signed mission is not protocol v5")
    if mission.get("runner_head") != source_head:
        raise RuntimeError("signed mission is not bound to proof source HEAD")
    absent_flags = sorted(flag for flag in V5_FLAGS if mission.get(flag) is not True)
    if absent_flags:
        raise RuntimeError(
            "signed mission flags missing: " + ", ".join(absent_flags))
    if int(mission.get("genome_realization_auditors_required", 0)) != 2:
        raise RuntimeError(
            "signed mission does not require two genome-realization auditors")
    protocol_files = set(mission.get("research_protocol_files") or [])
    missing_files = sorted(base.REQUIRED_PROTOCOL_FILES - protocol_files)
    if missing_files:
        raise RuntimeError(
            "signed protocol census omitted: " + ", ".join(missing_files))
    if preflight.get("proof_mode") is not True:
        raise RuntimeError(
            "zero-cost proof did not run under explicit proof mode")
    backend = (preflight.get("container_backend") or {}).get("backend")
    if backend != "container":
        raise RuntimeError(
            "full protocol proof did not exercise production container isolation")

    receipt = base.read_json(os.path.join(
        repo, "proof", "observatory-specialized-calibration-receipt.json"))
    if receipt.get("proof_mode") is not True or receipt.get("provider_calls") != 0:
        raise RuntimeError(
            "specialized calibration receipt has wrong mode/provider count")
    if receipt.get("protocol_bundle_sha256") != mission.get(
            "research_protocol_bundle_sha256"):
        raise RuntimeError(
            "specialized calibration receipt is not bound to signed protocol")
    for label in ("distributed", "scale", "formal", "interoperability"):
        row = (receipt.get("campaigns") or {}).get(label) or {}
        if row.get("status") not in ("PASS", "OK") \
                or row.get("passed") is not True:
            raise RuntimeError(label + " reference calibration did not pass")
        report_path = os.path.join(repo, *row["report_path"].split("/"))
        if row.get("report_sha256") != base.sha256_file(report_path):
            raise RuntimeError(label + " reference calibration hash drift")

    audit = base.read_json(os.path.join(runtime, "audit", "independent_audit.json"))
    if audit.get("protocol_version") != PROTOCOL \
            or audit.get("proof_mode") is not True:
        raise RuntimeError("independent audit has wrong protocol/mode")
    if not audit.get("immutable_package_unchanged") \
            or audit.get("hidden_disclosed_to_builder") is not False:
        raise RuntimeError(
            "independent audit failed immutable/hidden guarantees")
    if (audit.get("supremacy_conditions") or {}) != conditions:
        raise RuntimeError(
            "independent audit did not reproduce terminal conditions exactly")
    genome_campaign = (audit.get("campaigns") or {}).get(
        "controlled_genome_realization") or {}
    for key in ("qualification", "replication", "crown"):
        if genome_campaign.get(key) is not True:
            raise RuntimeError(
                f"independent audit genome campaign {key} is not passing")
    if int(genome_campaign.get("auditors", 0)) != 2 \
            or int(genome_campaign.get("axes", 0)) != 13:
        raise RuntimeError(
            "independent audit reports wrong genome auditor/axis census")

    forest = base.read_json(os.path.join(
        runtime, "architecture", "search_forest.json"))
    forest_summary = forest.get("summary") or {}
    if forest_summary.get("lineages") != 15 \
            or forest_summary.get("general_lineages") != 6 \
            or forest_summary.get("anti_attractor_lineages") != 9 \
            or int(forest_summary.get("seeds", 0)) < 90 \
            or int(forest_summary.get("selected_finalists", 0)) < 12 \
            or forest_summary.get("prior_cp2_visible") is not False:
        raise RuntimeError(
            "search forest is not the required independent 15-lineage forest")
    proposals = base.read_json(os.path.join(
        runtime, "architecture", "proposals.json"))
    if proposals.get("prior_cp2_visible") is not False \
            or len(proposals.get("proposals") or []) < 12:
        raise RuntimeError(
            "independent proposal frontier is too small or CP2-contaminated")
    built = base.read_json(os.path.join(runtime, "candidates", "built.json"))
    if built.get("complete_blueprint_handoff") is not True \
            or built.get("formalization_handoff") is not True \
            or len(built.get("built") or []) < 2:
        raise RuntimeError(
            "complete blueprint/formalization implementation handoff failed")

    incumbent = escalation["incumbent"]
    base.assert_pass(os.path.join(
        runtime, "reports", f"systems-crown-{incumbent}.json"),
        "durable crown")
    base.assert_pass(os.path.join(
        runtime, "reports", f"distributed-crown-{incumbent}.json"),
        "distributed crown")
    base.assert_pass(os.path.join(
        runtime, "reports", f"scale-crown-{incumbent}.json"),
        "scale crown")
    cross = base.assert_pass(os.path.join(
        runtime, "reports", f"cross-model-crown-{incumbent}.json"),
        "cross-model crown")
    proof_histories = int((audit.get("workload_policy") or {}).get(
        "cross_model", {}).get("crown_histories", 0))
    production_histories = int((mission.get("production_workloads") or {}).get(
        "cross_model", {}).get("crown_histories", 0))
    if int(cross.get("histories", 0)) != proof_histories \
            or production_histories <= proof_histories:
        raise RuntimeError(
            "cross-model crown did not preserve proof/production boundary")

    formal_paths = glob.glob(os.path.join(
        runtime, "reports", f"formal-crown-{incumbent}-*.json"))
    interop_paths = glob.glob(os.path.join(
        runtime, "reports", f"interoperability-crown-{incumbent}-*.json"))
    if len(formal_paths) != 2 or len(interop_paths) != 2:
        raise RuntimeError(
            "independent formal/interoperability crown evidence count is wrong")
    formal_reports = [
        base.assert_pass(path, "formal crown") for path in formal_paths]
    interop_reports = [
        base.assert_pass(path, "interoperability crown") for path in interop_paths]
    if len({row.get("behavioral_digest") for row in formal_reports}) != 1 \
            or len({row.get("semantic_digest") for row in interop_reports}) != 1:
        raise RuntimeError("independent crown implementations disagree")
    for path, report in zip(formal_paths, formal_reports):
        if report.get(
                "behavioral_digest_mode") != "ordered-length-delimited-stream-v1":
            raise RuntimeError(
                os.path.basename(path) + " did not use streaming formal digest")

    genome = {
        label: _checked_artifact(runtime, label, incumbent)
        for label in ("qualification", "replication", "crown")}

    prior_paths = base.numbered(glob.glob(os.path.join(
        runtime, "architecture", "prior-art-round*.json")), r"round(\d+)")
    if not prior_paths:
        raise RuntimeError("authoritative prior-art campaign is missing")
    prior = base.read_json(prior_paths[-1])
    if prior.get("all_sources_assessed") is not True \
            or prior.get("challengers_measured") is not True \
            or prior.get("no_blockers") is not True \
            or prior.get("blockers") or prior.get("unresolved"):
        raise RuntimeError(
            "authoritative prior-art campaign did not close")
    for critic in prior.get("critics") or []:
        for review in (critic.get("report") or {}).get("source_reviews") or []:
            if review.get("disposition") != "SATISFIED":
                continue
            verified = review.get("verified_evidence") or []
            if not verified:
                raise RuntimeError(
                    "SATISFIED prior-art review has no verified evidence")
            for evidence in verified:
                path = os.path.join(runtime, *evidence["path"].split("/"))
                if not os.path.isfile(path) \
                        or base.sha256_file(path) != evidence["sha256"]:
                    raise RuntimeError(
                        "prior-art verified evidence hash mismatch")

    novelty_paths = base.numbered(glob.glob(os.path.join(
        runtime, "architecture", "novelty-wave-r*.json")), r"r(\d+)")
    if len(novelty_paths) < 3:
        raise RuntimeError("fewer than three active novelty waves exist")
    for path in novelty_paths[-3:]:
        wave = base.read_json(path)
        ledger = wave.get("ledger_wave") or {}
        if ledger.get("dry") is not True \
                or ledger.get("methods_complete") is not True \
                or ledger.get("backlog_count") != 0 \
                or ledger.get("unresolved_count") != 0 \
                or ledger.get("prior_cp2_direct_content_read") is not False:
            raise RuntimeError("final novelty waves are not genuinely dry")
        round_number = base.re.search(r"r(\d+)\.json$", path).group(1)
        meta = base.read_json(os.path.join(
            runtime, "architecture",
            f"meta-search-wave-r{round_number}.json"))
        if len(meta.get("meta_critics") or []) != 2 \
                or len(meta.get("closure_auditors") or []) != 2 \
                or (meta.get("coverage_after") or {}).get("complete") is not True:
            raise RuntimeError(
                "meta-search/closure evidence incomplete")

    lower = base.read_json(os.path.join(
        runtime, "architecture", "lower_bounds.json"))
    destroyers = base.read_json(os.path.join(
        runtime, "architecture", "final_destroyers.json"))
    public_case = base.read_json(os.path.join(
        runtime, "architecture", "SUPREMACY-CASE.json"))
    if lower.get("closed") is not True \
            or destroyers.get("survived") is not True \
            or public_case.get("mechanically_supported") is not True \
            or public_case.get("third_party_endorsement_claimed") is not False:
        raise RuntimeError(
            "lower-bound/destroyer/public supremacy evidence did not close")
    required_gates = {
        "GATE-ARCH-V0", "GATE-ARCH-V1", "GATE-MIGRATION", "GATE-COMMIT"}
    if not required_gates.issubset(set(launch.get("gates") or [])):
        raise RuntimeError("proof did not traverse all owner gates")

    reality = base.read_json(os.path.join(
        runtime, "reality", "REPOSITORY-REALITY-MODEL.json"))
    history = base.read_json(os.path.join(
        runtime, "reality", "HISTORICAL-EXPERIMENT-MAP.json"))
    if reality.get("repository_archaeology_api_calls") != 0 \
            or history.get("prior_cp2_content_read") is not False:
        raise RuntimeError(
            "CP1 reuse / pre-frontier CP2 quarantine failed")
    return {
        "summary": summary,
        "audit": audit,
        "incumbent": incumbent,
        "conditions": sorted(conditions),
        "search_forest": forest_summary,
        "prior_art_sources": prior.get("source_count"),
        "novelty_waves": len(novelty_paths),
        "cross_model_histories": cross.get("histories"),
        "genome_realization": {
            label: {
                "evidence_path": report.get("evidence_path"),
                "auditors": len(report.get("auditors") or []),
                "axes": report.get("verified_axis_count")}
            for label, report in genome.items()},
        "exact_candidate_backend": "container",
        "streaming_formal_crown_verified": True,
        "protocol_version": PROTOCOL,
    }


def main(argv=None):
    base.py = _container_py
    base.subprocess.Popen = _genome_mock_popen
    base.verify_protocol = _verify
    code = base.main(argv)
    if os.path.isfile(REPORT):
        report = json.load(open(REPORT, encoding="utf-8"))
        report["proof"] = "complete-observatory-protocol-zero-cost-e2e-v5"
        report["hardened_wrapper"] = {
            "protocol_version": PROTOCOL,
            "exact_candidate_backend": "container",
            "final_mock_provider": "mock_observatory_genome_server.py",
            "real_paid_api_calls": 0,
        }
        with open(REPORT, "w", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False,
                      indent=1, sort_keys=True)
    return code


sha256_file = base.sha256_file
__all__ = ["main", "sha256_file"]


if __name__ == "__main__":
    import sys
    sys.exit(main())
