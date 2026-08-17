"""Cross-model legal-state consistency gates for every Observatory architecture."""
import hashlib
import os
import subprocess
import sys
from types import MethodType

from . import observatory_crown_overlay as crownmod
from . import observatory_escalation as escalation
from . import observatory_formal_overlay as formal
from . import observatory_interoperability_overlay as interop
from .canonical import atomic_write_json, read_json
from .handlers import A

QUALIFICATION_SEED_LABEL = "qualification"
REPLICATION_SEED_LABEL = "replication"
CROWN_SEED_LABEL = "crown"
SUPREMACY_KEYS = (
    "cross_model_consistency_passed",
    "cross_model_replication_passed",
    "cross_model_crown_passed",
)
SEARCH_KEYS = SUPREMACY_KEYS[:-1]


def _run(ctx, cid, label):
    semantic = A(ctx, "candidate-src", f"{cid}.py")
    formal_paths = [formal._path(ctx, cid, perspective)
                    for perspective, _temperature, _directive in formal.FORMAL_PERSPECTIVES]
    interop_paths = [interop._path(ctx, cid, perspective)
                     for perspective, _temperature, _directive in interop.PERSPECTIVES]
    paths = [semantic, *formal_paths, *interop_paths]
    missing = [path for path in paths if not os.path.isfile(path)]
    if missing:
        return {"status": "FAIL", "passed": False,
                "reason": "cross-model source missing: " + ", ".join(missing)}
    out = A(ctx, "reports", f"cross-model-{label}-{cid}.json")
    seed = int(hashlib.sha256(
        f"cross-model|{label}|{ctx.run_id}|{cid}".encode()).hexdigest()[:8], 16)
    command = [sys.executable,
               os.path.join(ctx.evaluator_dir, "observatory_cross_model_arena.py"),
               "--semantic", semantic, "--seed", str(seed), "--out", out]
    for path in formal_paths:
        command.extend(["--formal", path])
    for path in interop_paths:
        command.extend(["--interoperability", path])
    result = subprocess.run(command, capture_output=True, text=True)
    if not os.path.isfile(out):
        return {"status": "FAIL", "passed": False,
                "reason": "cross-model evaluator produced no report: "
                          + (result.stdout + result.stderr)[-1600:]}
    report = read_json(out); report["evaluator_returncode"] = result.returncode
    report["evidence_path"] = os.path.relpath(out, ctx.runtime).replace("\\", "/")
    return report


def _install_ledger(ctx):
    if getattr(ctx.esc, "_cross_model_overlay_installed", False):
        return
    original_conditions = ctx.esc._supremacy_conditions
    original_summary = ctx.esc.supremacy_summary

    def conditions(self):
        result = original_conditions(); incumbent = self.s.get("incumbent")
        scores = (ctx.scores.get(incumbent) or {}) if incumbent else {}
        qualification = scores.get("cross_model_qualification") or {}
        replication = scores.get("cross_model_replication") or {}
        crown = scores.get("cross_model_crown") or {}
        result.update({
            "cross_model_consistency_passed": qualification.get("passed") is True,
            "cross_model_replication_passed": replication.get("passed") is True,
            "cross_model_crown_passed": crown.get("passed") is True})
        return result

    def summary(self):
        result = original_summary(); result.update(conditions(self))
        result["cross_model_contract"] = "CROSS-MODEL-CONSISTENCY-CONTRACT.md"
        return result

    ctx.esc._supremacy_conditions = MethodType(conditions, ctx.esc)
    ctx.esc.supremacy_summary = MethodType(summary, ctx.esc)
    ctx.esc._cross_model_overlay_installed = True
    for key in SUPREMACY_KEYS:
        if key not in escalation.SUPREMACY_KEYS:
            escalation.SUPREMACY_KEYS.append(key)
    for key in SEARCH_KEYS:
        if key not in escalation.SEARCH_SUPREMACY_KEYS:
            escalation.SEARCH_SUPREMACY_KEYS.append(key)
    schema = escalation.OBSERVATORY_PROOF_SCHEMA
    conditions_schema = schema["properties"]["conditions"]
    supremacy_schema = schema["properties"]["supremacy"]
    for key in SUPREMACY_KEYS:
        if key not in conditions_schema["required"]:
            conditions_schema["required"].append(key)
        conditions_schema["properties"][key] = {"type": "boolean"}
        if key not in supremacy_schema["required"]:
            supremacy_schema["required"].append(key)
        supremacy_schema["properties"][key] = {"type": "boolean"}


def _filter_frontier(ctx, reason):
    rejected = []
    for cid, member in list(ctx.frontier.members.items()):
        if member.get("status") != "ACTIVE":
            continue
        report = (ctx.scores.get(cid) or {}).get("cross_model_qualification") or {}
        if report.get("passed") is not True:
            member["status"] = "REJECTED_CROSS_MODEL_INCONSISTENCY"
            member["reason"] = reason; rejected.append(cid)
    if not ctx.frontier.non_dominated():
        raise RuntimeError("no candidate survived cross-model legal-state consistency")
    ctx._save_arena(); return rejected


def install(ctx, handlers):
    _install_ledger(ctx); out = dict(handlers)
    original_vector = ctx.dimension_vector

    def dimension_vector(self, cid, hidden_rep, fidelity_rep=None):
        vector = original_vector(cid, hidden_rep, fidelity_rep)
        report = (self.scores.get(cid) or {}).get("cross_model_qualification") or {}
        vector["cross_model_consistency_survival"] = 1.0 if report.get("passed") is True else 0.0
        return vector

    ctx.dimension_vector = MethodType(dimension_vector, ctx)
    original_private = out["PRIVATE_QUALIFICATION"]

    def private_qualification(machine):
        path = original_private(machine); artifact = read_json(path); rows = []
        for cid in sorted(ctx.candidates):
            report = _run(ctx, cid, QUALIFICATION_SEED_LABEL)
            ctx.record_score(cid, "cross_model_qualification", report)
            rows.append({"candidate_id": cid, "passed": report.get("passed") is True,
                         "evidence_path": report.get("evidence_path")})
        if len([row for row in rows if row["passed"]]) < 2:
            raise RuntimeError("fewer than two architectures survived cross-model consistency")
        artifact["cross_model_consistency"] = rows; atomic_write_json(path, artifact)
        return path

    out["PRIVATE_QUALIFICATION"] = private_qualification
    original_provisional = out["PROVISIONAL_FRONTIER_MEMBER"]

    def provisional(machine):
        path = original_provisional(machine); artifact = read_json(path)
        artifact["cross_model_rejected"] = _filter_frontier(
            ctx, "cross-model qualification failed")
        artifact["members"] = ctx.frontier.report(); atomic_write_json(path, artifact)
        return path

    out["PROVISIONAL_FRONTIER_MEMBER"] = provisional
    original_round = crownmod._build_round_candidate

    def round_build(context, idea, cid, kind, ticket):
        result = original_round(context, idea, cid, kind, ticket)
        report = _run(context, cid, QUALIFICATION_SEED_LABEL)
        context.record_score(cid, "cross_model_qualification", report)
        if report.get("passed") is not True:
            raise RuntimeError(f"{cid}: cross-model legal-state consistency failed")
        return result

    crownmod._build_round_candidate = round_build
    original_frontier = out["FRONTIER_REVIEW"]

    def frontier_review(machine):
        path = original_frontier(machine); artifact = read_json(path)
        artifact["cross_model_rejected"] = _filter_frontier(
            ctx, "round candidate cross-model consistency failed")
        artifact["statuses"] = {key: value["status"]
                                for key, value in ctx.frontier.report().items()}
        atomic_write_json(path, artifact); return path

    out["FRONTIER_REVIEW"] = frontier_review
    original_replication = out["PRIVATE_REPLICATION"]

    def private_replication(machine):
        path = original_replication(machine); artifact = read_json(path); rows = []
        for cid in artifact.get("finalists") or []:
            report = _run(ctx, cid, REPLICATION_SEED_LABEL)
            ctx.record_score(cid, "cross_model_replication", report)
            passed = report.get("passed") is True
            rows.append({"candidate_id": cid, "passed": passed,
                         "evidence_path": report.get("evidence_path")})
            if not passed and cid in ctx.frontier.members:
                ctx.frontier.members[cid]["status"] = "REJECTED_CROSS_MODEL_REPLICATION"
                ctx.frontier.members[cid]["reason"] = "cross-model replication failed"
        if not ctx.frontier.non_dominated():
            raise RuntimeError("all finalists failed cross-model replication")
        ctx._save_arena(); artifact["cross_model_replication"] = rows
        atomic_write_json(path, artifact); return path

    out["PRIVATE_REPLICATION"] = private_replication
    original_systems = crownmod._run_systems

    def run_systems(context, cid, label, events):
        report = original_systems(context, cid, label, events)
        if label == "crown":
            cross = _run(context, cid, CROWN_SEED_LABEL)
            context.record_score(cid, "cross_model_crown", cross)
            report["cross_model_crown"] = cross
            if cross.get("passed") is not True:
                report["status"] = "FAIL"; report["passed"] = False
                report["cross_model_failure"] = True
        return report

    crownmod._run_systems = run_systems
    original_synthesis = out["ARCHITECTURE_EVIDENCE_SYNTHESIS"]

    def synthesis(machine):
        path = original_synthesis(machine); artifact = read_json(path)
        winner = artifact.get("candidate_id")
        report = ((ctx.scores.get(winner) or {}).get("cross_model_crown") or {}) \
            if winner else {}
        artifact["cross_model_crown"] = report
        artifact["cross_model_crown_passed"] = report.get("passed") is True
        atomic_write_json(path, artifact); return path

    out["ARCHITECTURE_EVIDENCE_SYNTHESIS"] = synthesis
    return out
