"""Protocol-wide fail-closed preflight for the National Legal Observatory."""
from __future__ import annotations

import json
import os

from . import observatory_preflight as legacy
from . import observatory_protocol
from .canonical import read_json

PreflightFailed = legacy.PreflightFailed

REQUIRED_DIMENSIONS = {
    "source_coverage", "change_detection_recall", "temporal_reconstruction_accuracy",
    "canonical_identity_accuracy", "normative_effect_accuracy",
    "jurisprudence_temporal_link_accuracy", "doctrine_epistemic_separation",
    "provenance_completeness", "publication_projection_consistency",
    "replay_determinism", "recovery_success", "honest_unknown_rate",
    "distributed_fault_survival", "distributed_events_per_second",
    "national_scale_survival", "scale_events_per_second",
    "scale_batch_latency_p95", "scale_bytes_per_event",
    "machine_checked_model_survival", "formal_trace_coverage",
    "legal_interoperability_survival", "interoperability_case_coverage",
    "publication_latency", "trusted_kernel_complexity",
    "external_model_dependence", "migration_cost",
}

SPECIALIZED = {
    "distributed": (
        "benchmark/observatory_distributed_reference_candidate.py",
        "private-evaluator/evaluator/observatory_distributed_arena.py"),
    "scale": (
        "benchmark/observatory_scale_reference_candidate.py",
        "private-evaluator/evaluator/observatory_scale_arena.py"),
    "formal": (
        "benchmark/observatory_formal_reference_candidate.py",
        "private-evaluator/evaluator/observatory_formal_arena.py"),
    "interoperability": (
        "benchmark/observatory_interoperability_reference_candidate.py",
        "private-evaluator/evaluator/observatory_interoperability_arena.py"),
}


def _compile_and_parse_protocol(root):
    compiled, parsed = 0, 0
    for relative in observatory_protocol.protocol_files(root):
        path = os.path.join(root, *relative.split("/"))
        if relative.endswith(".py"):
            compile(open(path, encoding="utf-8").read(), relative, "exec")
            compiled += 1
        elif relative.endswith(".json"):
            read_json(path); parsed += 1
    return {"files": len(observatory_protocol.protocol_files(root)),
            "python_compiled": compiled, "json_parsed": parsed,
            "bundle_sha256": observatory_protocol.protocol_bundle_sha256(root)}


def _pareto(root):
    path = os.path.join(root, "profiles", "national-observatory",
                        "PARETO-DIMENSIONS.json")
    rows = read_json(path)
    if not isinstance(rows, list) or not rows:
        raise RuntimeError("PARETO-DIMENSIONS.json must be a non-empty array")
    ids = [row.get("id") for row in rows]
    if any(not key for key in ids) or len(ids) != len(set(ids)):
        raise RuntimeError("Pareto dimensions contain missing or duplicate IDs")
    missing = sorted(REQUIRED_DIMENSIONS - set(ids))
    if missing:
        raise RuntimeError("required Pareto dimensions missing: " + ", ".join(missing))
    for row in rows:
        if row.get("direction") not in ("higher", "lower"):
            raise RuntimeError(f"{row.get('id')}: invalid Pareto direction")
        if not isinstance(row.get("noise_floor"), (int, float)):
            raise RuntimeError(f"{row.get('id')}: missing numeric noise floor")
    return {"dimensions": len(rows), "required_dimensions": sorted(REQUIRED_DIMENSIONS)}


def _prior_art(root):
    path = os.path.join(root, "profiles", "national-observatory",
                        "PUBLIC-PRIOR-ART-MANIFEST.json")
    obj = read_json(path)
    sources = obj.get("sources") or []
    ids = [row.get("source_id") for row in sources]
    if len(sources) < 12 or any(not source_id for source_id in ids) \
            or len(ids) != len(set(ids)):
        raise RuntimeError("public prior-art manifest is incomplete or has duplicate IDs")
    required = {"authority", "kind", "status", "version", "url",
                "load_bearing_claims", "challenge_axes"}
    for row in sources:
        missing = sorted(required - set(row))
        if missing:
            raise RuntimeError(f"{row.get('source_id')}: prior-art fields missing: {missing}")
        if not row.get("load_bearing_claims") or not row.get("challenge_axes"):
            raise RuntimeError(f"{row.get('source_id')}: empty prior-art challenge")
    return {"source_count": len(sources), "source_ids": ids,
            "manifest_sha256": observatory_protocol.file_sha256(path)}


def _specialized_sources(root):
    report = {}
    for label, relatives in SPECIALIZED.items():
        hashes = {}
        for relative in relatives:
            path = os.path.join(root, *relative.split("/"))
            if not os.path.isfile(path):
                raise RuntimeError(f"{label}: required source missing: {relative}")
            compile(open(path, encoding="utf-8").read(), relative, "exec")
            hashes[relative] = observatory_protocol.file_sha256(path)
        report[label] = hashes
    return report


def _calibration_receipt(root, expected_sources, require):
    path = os.path.join(root, "proof", "observatory-specialized-calibration-receipt.json")
    if not os.path.isfile(path):
        if require:
            raise RuntimeError(
                "specialized calibration receipt missing; run setup_observatory.py")
        return None
    receipt = read_json(path)
    expected = {
        "protocol_version": observatory_protocol.PROTOCOL_VERSION,
        "protocol_bundle_sha256": observatory_protocol.protocol_bundle_sha256(root),
        "proof_mode": observatory_protocol.proof_mode(),
        "sources": expected_sources,
    }
    mismatch = [key for key, value in expected.items()
                if receipt.get(key) != value]
    if mismatch:
        raise RuntimeError("specialized calibration receipt drift: " + ", ".join(mismatch))
    campaigns = receipt.get("campaigns") or {}
    for label in SPECIALIZED:
        row = campaigns.get(label) or {}
        if row.get("status") not in ("PASS", "OK") or row.get("passed") is False:
            raise RuntimeError(f"{label}: specialized calibration receipt is not passing")
        artifact = row.get("report_path")
        if not artifact:
            raise RuntimeError(f"{label}: calibration report path missing")
        absolute = os.path.abspath(os.path.join(root, *artifact.split("/")))
        if not absolute.startswith(os.path.abspath(root) + os.sep) \
                or not os.path.isfile(absolute):
            raise RuntimeError(f"{label}: calibration report unavailable")
        if row.get("report_sha256") != observatory_protocol.file_sha256(absolute):
            raise RuntimeError(f"{label}: calibration report hash drift")
    return {"path": os.path.relpath(path, root).replace("\\", "/"),
            "sha256": observatory_protocol.file_sha256(path),
            "campaigns": sorted(campaigns)}


def run(root, orchestrator_root, runtime, require_vault=True,
        owner_public=None, backend=None):
    report = legacy.run(root, orchestrator_root, runtime,
                        require_vault=require_vault,
                        owner_public=owner_public, backend=backend)
    problems = []
    extensions = {}
    for label, function in (
            ("protocol", lambda: _compile_and_parse_protocol(root)),
            ("pareto", lambda: _pareto(root)),
            ("prior_art", lambda: _prior_art(root)),
            ("specialized_sources", lambda: _specialized_sources(root))):
        try:
            extensions[label] = function()
        except Exception as exc:
            problems.append(f"{label}: {exc}")
    if "specialized_sources" in extensions:
        try:
            extensions["specialized_calibration"] = _calibration_receipt(
                root, extensions["specialized_sources"], require_vault)
        except Exception as exc:
            problems.append("specialized_calibration: " + str(exc))
    extensions["proof_mode"] = observatory_protocol.proof_mode()
    extensions["production_workloads"] = observatory_protocol.PRODUCTION_WORKLOADS
    report["research_protocol"] = extensions
    report["problems"] = list(report.get("problems") or []) + problems
    report["ok"] = not report["problems"]
    if problems:
        raise PreflightFailed("\n  - ".join(
            ["Observatory protocol preflight refused to launch:"] + problems))
    return report
