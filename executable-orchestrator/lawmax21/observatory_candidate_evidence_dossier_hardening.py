"""Create a complete source-bound candidate evidence ledger inside the final supremacy dossier.

A statement that one architecture beat another is not auditable if only the incumbent crown is
indexed. This hardening enumerates every candidate still present in the runtime and every frontier
member, binds its source and all qualification reports, requires the full seven-campaign executable
qualification portfolio for every measured frontier member, and hashes a deterministic lifecycle
ledger into the same final dossier.
"""
from __future__ import annotations

import glob
import os

from . import observatory_supremacy_dossier_overlay as dossier
from .canonical import atomic_write_json, sha256_file
from .handlers import A

REQUIRED_FRONTIER_SCORES = (
    "hidden_qualification",
    "systems_qualification",
    "distributed_qualification",
    "scale_qualification",
    "formal_qualification",
    "interoperability_qualification",
    "cross_model_qualification",
    "genome_realization_qualification",
)


def _append(ctx, artifact, path, label):
    row, _parsed = dossier._evidence(ctx, path, label=label)
    rows = artifact.setdefault("evidence_index", [])
    existing = next(
        (current for current in rows if current.get("path") == row["path"]),
        None)
    if existing is not None:
        if existing.get("sha256") != row.get("sha256") \
                or int(existing.get("bytes", -1)) != int(row.get("bytes", -2)):
            raise RuntimeError(
                "candidate evidence changed during dossier construction: "
                + row["path"])
        return existing
    rows.append(row)
    return row


def _runtime_file(ctx, relative):
    path = os.path.abspath(os.path.join(
        ctx.runtime, *str(relative).replace("\\", "/").split("/")))
    runtime = os.path.abspath(ctx.runtime)
    if path != runtime and not path.startswith(runtime + os.sep):
        return None
    return path if os.path.isfile(path) else None


def _nested_evidence_paths(value):
    paths = set()
    if isinstance(value, dict):
        for key, item in value.items():
            if key in ("evidence_path", "report_path", "path") \
                    and isinstance(item, str) \
                    and (item.endswith(".json") or item.endswith(".jsonl")):
                paths.add(item)
            paths.update(_nested_evidence_paths(item))
    elif isinstance(value, list):
        for item in value:
            paths.update(_nested_evidence_paths(item))
    return paths


def _candidate_report_paths(ctx, candidate_id, scores):
    paths = set()
    for relative in _nested_evidence_paths(scores):
        absolute = _runtime_file(ctx, relative)
        if absolute:
            paths.add(absolute)
    for directory in (
            A(ctx, "reports", "x")[:-1],
            A(ctx, "architecture", "x")[:-1]):
        if os.path.isdir(directory):
            paths.update(path for path in glob.glob(
                os.path.join(directory, f"*{candidate_id}*.json"))
                if os.path.isfile(path))
    return sorted(paths)


def _score_summary(scores):
    result = {}
    for key, value in sorted(scores.items()):
        if not isinstance(value, dict):
            continue
        result[key] = {
            "status": value.get("status"),
            "passed": value.get("passed"),
            "candidate_id": value.get("candidate_id"),
            "evidence_path": value.get("evidence_path"),
        }
        if key == "hidden_qualification":
            result[key]["dimension_scores"] = value.get("dimension_scores")
        if key in ("formal_qualification", "interoperability_qualification"):
            result[key]["independent_agreement"] = (
                value.get("independent_model_agreement")
                if key == "formal_qualification"
                else value.get("implementations_agree"))
    return result


def install(_ctx, handlers):
    if getattr(dossier, "_candidate_evidence_hardening_installed", False):
        return dict(handlers)
    original = dossier._build_dossier

    def build(context, original_conditions):
        dossier_path, artifact = original(context, original_conditions)
        frontier = context.frontier.report()
        candidate_ids = sorted(set(context.candidates) | set(frontier))
        if not candidate_ids:
            raise RuntimeError("candidate evidence ledger found no candidates")
        ledger_rows = []
        measured_frontier_count = 0
        for candidate_id in candidate_ids:
            candidate = context.candidates.get(candidate_id) or {}
            scores = context.scores.get(candidate_id) or {}
            member = frontier.get(candidate_id)
            source_path = A(context, "candidate-src", f"{candidate_id}.py")
            source_evidence = None
            if os.path.isfile(source_path):
                source_evidence = _append(
                    context, artifact, source_path,
                    f"candidate_source:{candidate_id}")
                expected_source = candidate.get("source")
                if isinstance(expected_source, str):
                    actual = sha256_file(source_path)
                    import hashlib
                    expected = hashlib.sha256(
                        expected_source.encode("utf-8")).hexdigest()
                    if actual != expected:
                        raise RuntimeError(
                            f"{candidate_id}: persisted semantic source differs from arena source")
            reports = []
            for report_path in _candidate_report_paths(
                    context, candidate_id, scores):
                reports.append(_append(
                    context, artifact, report_path,
                    f"candidate_report:{candidate_id}:{os.path.basename(report_path)}"))

            missing_scores = []
            if member is not None:
                measured_frontier_count += 1
                missing_scores = [
                    key for key in REQUIRED_FRONTIER_SCORES
                    if not isinstance(scores.get(key), dict)]
                if missing_scores:
                    raise RuntimeError(
                        f"{candidate_id}: measured frontier member lacks qualification scores: "
                        + ", ".join(missing_scores))
                if source_evidence is None:
                    raise RuntimeError(
                        f"{candidate_id}: measured frontier member lacks persisted semantic source")
                if len(reports) < 8:
                    raise RuntimeError(
                        f"{candidate_id}: measured frontier member has only {len(reports)} "
                        "persisted report artefacts")

            ledger_rows.append({
                "candidate_id": candidate_id,
                "family": candidate.get("family"),
                "kind": candidate.get("kind"),
                "mechanism": candidate.get("mechanism"),
                "seed_id": candidate.get("seed_id"),
                "lineage_code": candidate.get("lineage_code"),
                "genome_sha256": candidate.get("genome_sha256"),
                "blueprint_sha256": candidate.get("blueprint_sha256"),
                "formalization_sha256": candidate.get("formalization_sha256"),
                "frontier_member": member is not None,
                "frontier_status": member.get("status") if member else None,
                "frontier_reason": member.get("reason") if member else None,
                "dimension_vector": member.get("dimension_vector") if member else None,
                "source_evidence": source_evidence,
                "score_summary": _score_summary(scores),
                "report_evidence": reports,
                "missing_required_frontier_scores": missing_scores,
            })

        if measured_frontier_count < 2:
            raise RuntimeError(
                "candidate evidence ledger requires at least two measured frontier members")
        ledger = {
            "status": "PASS",
            "candidate_count": len(ledger_rows),
            "measured_frontier_count": measured_frontier_count,
            "required_frontier_score_keys": list(REQUIRED_FRONTIER_SCORES),
            "candidates": ledger_rows,
        }
        ledger_path = A(
            context, "architecture", "CANDIDATE-EVIDENCE-LEDGER.json")
        atomic_write_json(ledger_path, ledger)
        ledger_evidence = _append(
            context, artifact, ledger_path, "complete_candidate_evidence_ledger")
        artifact["complete_candidate_field"] = {
            "verified": True,
            "candidate_count": len(ledger_rows),
            "measured_frontier_count": measured_frontier_count,
            "ledger_path": ledger_evidence["path"],
            "ledger_sha256": ledger_evidence["sha256"],
            "all_frontier_members_have_complete_qualification_portfolio": True,
        }
        atomic_write_json(dossier_path, artifact)
        return dossier_path, artifact

    dossier._build_dossier = build
    dossier._candidate_evidence_hardening_installed = True
    return dict(handlers)
