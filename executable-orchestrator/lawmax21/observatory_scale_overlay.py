"""National-scale implementation search and qualification for Observatory architectures.

Runs after semantic/distributed implementation selection. Each architecture receives three
source-distinct scale implementations (balanced, throughput-first, recovery-first), all faithful to
its controlled scaling class. Executable qualification selects a passing Pareto-preferred variant;
if none pass, at most two architecture-preserving revisions use aggregate reports only.

Round challengers use the same path. Independent scale replication and a one-million-event crown
permit no revision and become explicit supremacy conditions.
"""
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
from types import MethodType

from . import observatory_crown_overlay as crownmod
from . import observatory_escalation as escalation
from . import observatory_roles as oroles
from .canonical import atomic_write_json, read_json
from .handlers import A


SCALE_PERSPECTIVES = (
    ("balanced", 0.15,
     "Balance deterministic rebuild, durable bytes, partition balance and incremental publication latency."),
    ("throughput-first", 0.40,
     "Maximize streaming and partition-local work without weakening root determinism, recovery or one-truth publication."),
    ("recovery-first", 0.60,
     "Minimize recovery ambiguity and checkpoint trust while retaining measurable partitioning and acceptable ingestion cost."),
)
SCALE_REVISIONS = 2
SCALE_QUAL_EVENTS = 100000
SCALE_REPLICATION_EVENTS = 250000
SCALE_CROWN_EVENTS = 1000000
SCALE_PARTITIONS = 16
SCALE_BATCH = 5000
MIN_DISTINCT_SCALE_IMPLEMENTATIONS = 2

SCALE_SUPREMACY_KEYS = (
    "scale_implementation_diversity_proven",
    "national_scale_qualification_passed",
    "national_scale_replication_passed",
    "national_scale_crown_passed",
)
SCALE_SEARCH_KEYS = SCALE_SUPREMACY_KEYS[:-1]


def _path(ctx, cid, suffix=""):
    tail = f"-{suffix}" if suffix else ""
    return A(ctx, "scale-candidate", f"{cid}{tail}.py")


def _model(ctx, cid):
    genome = (ctx.candidates.get(cid) or {}).get("genome") or {}
    value = genome.get("scaling_partition_model") or {}
    if not isinstance(value, dict) or not value.get("class"):
        raise RuntimeError(f"{cid}: missing controlled scaling_partition_model")
    return str(value["class"])


def _extract(obj):
    files = [x for x in obj.get("files", []) if x.get("path") == "scale_candidate.py"]
    if len(files) != 1:
        raise RuntimeError("scale role must return exactly one scale_candidate.py")
    source = files[0]["content"]
    compile(source, "<scale-candidate>", "exec")
    return source


def _write(path, source):
    with open(path, "w", encoding="utf-8") as f:
        f.write(source)
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def _build(ctx, cid, perspective, temperature, directive, line="main"):
    candidate = ctx.candidates[cid]
    blueprint = candidate.get("blueprint") or {}
    formalization = candidate.get("formalization") or {}
    if not blueprint or not formalization:
        raise RuntimeError(f"{cid}: scale builder requires blueprint/formalization")
    contract = open(os.path.join(ctx.profile_pkg, "SCALE-SYSTEMS-CONTRACT.md"),
                    encoding="utf-8").read()
    _, obj, _, _ = ctx.ask(
        f"scale-systems-builder-{perspective}",
        f"OBS-SCALE-BUILD::{cid}::{perspective}",
        "Implement scale_candidate.py for THIS exact architecture and its controlled scaling class. "
        + directive + " Do not relabel a monolithic implementation as a partitioned design. Preserve "
        "one canonical root, deterministic routing/rebuild, explicit checkpoint recovery and all "
        "required publication channels. Use only Python standard library; no network/model exists.",
        [("COMPLETE ARCHITECTURE BLUEPRINT", json.dumps(blueprint, ensure_ascii=False)),
         ("ARCHITECTURE FORMALIZATION", json.dumps(formalization, ensure_ascii=False)),
         ("EXPECTED CONTROLLED SCALING GENOME", json.dumps({
             "scaling_partition_model": _model(ctx, cid),
             "perspective": perspective,
         }, ensure_ascii=False)),
         ("NATIONAL SCALE SYSTEMS CONTRACT", contract)],
        oroles.BUILD_SCHEMA, line=line, temperature=temperature)
    source = _extract(obj)
    path = _path(ctx, cid, perspective)
    digest = _write(path, source)
    return {"perspective": perspective, "path": path,
            "source_sha256": digest, "source": source}


def _run(ctx, cid, label, events, candidate_path=None):
    path = candidate_path or _path(ctx, cid)
    if not os.path.isfile(path):
        return {"status": "FAIL", "passed": False,
                "reason": "scale candidate missing"}
    out = A(ctx, "reports", f"scale-{label}-{cid}.json")
    seed = int(hashlib.sha256(
        f"scale|{label}|{ctx.run_id}|{cid}".encode()).hexdigest()[:8], 16)
    tail = max(1000, min(50000, max(1, events // 10)))
    result = subprocess.run([
        sys.executable,
        os.path.join(ctx.evaluator_dir, "observatory_scale_arena.py"),
        "--candidate", path, "--out", out,
        "--expected-scaling-model", _model(ctx, cid),
        "--seed", str(seed), "--events", str(events),
        "--tail-events", str(tail), "--partitions", str(SCALE_PARTITIONS),
        "--batch-size", str(SCALE_BATCH), "--timeout", "14400",
    ], capture_output=True, text=True)
    if not os.path.exists(out):
        return {"status": "FAIL", "passed": False,
                "reason": "scale evaluator produced no report: "
                          + (result.stdout + result.stderr)[-1600:]}
    report = read_json(out)
    report["evaluator_returncode"] = result.returncode
    report["evidence_path"] = os.path.relpath(out, ctx.runtime).replace("\\", "/")
    report["candidate_path"] = os.path.relpath(path, ctx.runtime).replace("\\", "/")
    return report


def _rank(report):
    passed = report.get("status") == "PASS" and report.get("passed") is True
    throughput = float(report.get("events_per_second", 0.0))
    latency = float(report.get("batch_latency_p95_seconds", math.inf))
    bytes_per_event = float(report.get("bytes_per_event", math.inf))
    balance = float(report.get("partition_balance_ratio", math.inf))
    return (passed, throughput, -latency, -bytes_per_event, -balance)


def _qualify(ctx, cid, allow_revision=True):
    variants = []
    errors = []
    line = "main" if ctx.candidates[cid].get("kind") == "baseline" else "successor"
    for perspective, temperature, directive in SCALE_PERSPECTIVES:
        try:
            built = _build(ctx, cid, perspective, temperature, directive, line=line)
            report = _run(ctx, cid, f"qualification-{perspective}",
                          SCALE_QUAL_EVENTS, built["path"])
            built["report"] = report
            variants.append(built)
        except Exception as exc:
            errors.append({"perspective": perspective, "error": str(exc)[:1600]})
    distinct = len({x["source_sha256"] for x in variants})
    if distinct < MIN_DISTINCT_SCALE_IMPLEMENTATIONS:
        errors.append({"kind": "scale-implementation-convergence",
                       "distinct_source_hashes": distinct,
                       "required": MIN_DISTINCT_SCALE_IMPLEMENTATIONS})

    selected = max(variants, key=lambda x: _rank(x["report"])) if variants else None
    revisions = []
    if selected and not _rank(selected["report"])[0] and allow_revision:
        current = selected
        contract = open(os.path.join(ctx.profile_pkg, "SCALE-SYSTEMS-CONTRACT.md"),
                        encoding="utf-8").read()
        for revision in range(1, SCALE_REVISIONS + 1):
            try:
                _, obj, _, _ = ctx.ask(
                    "scale-systems-reviser",
                    f"OBS-SCALE-REVISE::{cid}::r{revision}",
                    "Revise scale_candidate.py to fix the exact aggregate scale failures while "
                    "preserving the controlled scaling class, blueprint and formalization. Do not "
                    "hard-code workload IDs or replace the architecture with a generic reference. "
                    "Return the complete file.",
                    [("COMPLETE ARCHITECTURE BLUEPRINT", json.dumps(
                        ctx.candidates[cid].get("blueprint") or {}, ensure_ascii=False)),
                     ("ARCHITECTURE FORMALIZATION", json.dumps(
                        ctx.candidates[cid].get("formalization") or {}, ensure_ascii=False)),
                     ("EXPECTED CONTROLLED SCALING GENOME", json.dumps({
                         "scaling_partition_model": _model(ctx, cid)}, ensure_ascii=False)),
                     ("NATIONAL SCALE SYSTEMS CONTRACT", contract),
                     ("CURRENT scale_candidate.py", current["source"][:700000]),
                     ("MEASURED SCALE FAILURE", json.dumps(
                         current["report"], ensure_ascii=False)[:100000])],
                    oroles.BUILD_SCHEMA, line="successor", temperature=0.25)
                source = _extract(obj)
                suffix = f"revision-{revision}"
                path = _path(ctx, cid, suffix)
                digest = _write(path, source)
                report = _run(ctx, cid, f"qualification-{suffix}",
                              SCALE_QUAL_EVENTS, path)
                row = {"perspective": suffix, "path": path,
                       "source_sha256": digest, "source": source,
                       "report": report}
                variants.append(row); revisions.append(row)
                if _rank(row["report"]) > _rank(selected["report"]):
                    selected = row
                current = row
                if _rank(selected["report"])[0]:
                    break
            except Exception as exc:
                errors.append({"revision": revision, "error": str(exc)[:1600]})

    passed = bool(selected and _rank(selected["report"])[0]
                  and distinct >= MIN_DISTINCT_SCALE_IMPLEMENTATIONS)
    result = {
        "status": "PASS" if passed else "FAIL",
        "passed": passed,
        "selected_perspective": selected.get("perspective") if selected else None,
        "selected_source_sha256": selected.get("source_sha256") if selected else None,
        "selected_report": selected.get("report") if selected else None,
        "distinct_source_hashes": distinct,
        "variants": [{
            "perspective": x["perspective"],
            "source_sha256": x["source_sha256"],
            "report_status": x["report"].get("status"),
            "passed": x["report"].get("passed") is True,
            "evidence_path": x["report"].get("evidence_path"),
        } for x in variants],
        "revision_history": [{
            "perspective": x["perspective"],
            "source_sha256": x["source_sha256"],
            "passed": x["report"].get("passed") is True,
        } for x in revisions],
        "errors": errors,
    }
    if passed:
        shutil.copyfile(selected["path"], _path(ctx, cid))
        ctx.candidates[cid]["scale_candidate_path"] = _path(ctx, cid)
        ctx.candidates[cid]["scale_source_sha256"] = selected["source_sha256"]
        ctx.candidates[cid]["scale_qualified"] = True
    else:
        ctx.candidates[cid]["scale_qualified"] = False
    ctx.record_score(cid, "scale_qualification", result)
    ctx._save_arena()
    return result


def _install_ledger(ctx):
    if getattr(ctx.esc, "_scale_overlay_installed", False):
        return
    original_conditions = ctx.esc._supremacy_conditions
    original_summary = ctx.esc.supremacy_summary

    def conditions(self):
        result = original_conditions()
        incumbent = self.s.get("incumbent")
        scores = ctx.scores.get(incumbent) or {} if incumbent else {}
        qualification = scores.get("scale_qualification") or {}
        replication = scores.get("scale_replication") or {}
        crown = scores.get("scale_crown") or {}
        result.update({
            "scale_implementation_diversity_proven": bool(
                qualification.get("distinct_source_hashes", 0)
                >= MIN_DISTINCT_SCALE_IMPLEMENTATIONS),
            "national_scale_qualification_passed": bool(
                qualification.get("status") == "PASS"
                and qualification.get("passed") is True),
            "national_scale_replication_passed": bool(
                replication.get("status") == "PASS"
                and replication.get("passed") is True),
            "national_scale_crown_passed": bool(
                crown.get("status") == "PASS" and crown.get("passed") is True),
        })
        return result

    def summary(self):
        result = original_summary()
        result.update(conditions(self))
        result.update({
            "scale_minimum_distinct_sources": MIN_DISTINCT_SCALE_IMPLEMENTATIONS,
            "scale_revision_limit": SCALE_REVISIONS,
            "scale_qualification_events": SCALE_QUAL_EVENTS,
            "scale_replication_events": SCALE_REPLICATION_EVENTS,
            "scale_crown_events": SCALE_CROWN_EVENTS,
            "scale_partitions": SCALE_PARTITIONS,
            "scale_contract": "SCALE-SYSTEMS-CONTRACT.md",
        })
        return result

    ctx.esc._supremacy_conditions = MethodType(conditions, ctx.esc)
    ctx.esc.supremacy_summary = MethodType(summary, ctx.esc)
    ctx.esc._scale_overlay_installed = True

    for key in SCALE_SUPREMACY_KEYS:
        if key not in escalation.SUPREMACY_KEYS:
            escalation.SUPREMACY_KEYS.append(key)
    for key in SCALE_SEARCH_KEYS:
        if key not in escalation.SEARCH_SUPREMACY_KEYS:
            escalation.SEARCH_SUPREMACY_KEYS.append(key)
    schema = escalation.OBSERVATORY_PROOF_SCHEMA
    cond = schema["properties"]["conditions"]
    proof = schema["properties"]["supremacy"]
    for key in SCALE_SUPREMACY_KEYS:
        if key not in cond["required"]:
            cond["required"].append(key)
        cond["properties"][key] = {"type": "boolean"}
        if key not in proof["required"]:
            proof["required"].append(key)
        proof["properties"][key] = {"type": "boolean"}


def install(ctx, handlers):
    _install_ledger(ctx)
    out = dict(handlers)

    original_dimension_vector = ctx.dimension_vector

    def dimension_vector(self, cid, hidden_rep, fidelity_rep=None):
        vector = original_dimension_vector(cid, hidden_rep, fidelity_rep)
        scale = (self.scores.get(cid) or {}).get("scale_qualification") or {}
        report = scale.get("selected_report") or {}
        vector["national_scale_survival"] = (
            1.0 if scale.get("status") == "PASS" and scale.get("passed") is True else 0.0)
        vector["scale_events_per_second"] = float(report.get("events_per_second", 0.0))
        vector["scale_batch_latency_p95"] = float(
            report.get("batch_latency_p95_seconds", math.inf))
        vector["scale_bytes_per_event"] = float(report.get("bytes_per_event", math.inf))
        return vector

    ctx.dimension_vector = MethodType(dimension_vector, ctx)

    original_private = out["PRIVATE_QUALIFICATION"]

    def private_qualification(machine):
        path = original_private(machine)
        artifact = read_json(path)
        rows = []
        selected_ids = list((artifact.get("implementation_search_selection") or {}).get(
            "selected_architecture_ids") or sorted(ctx.candidates))
        for cid in selected_ids:
            if cid not in ctx.candidates:
                continue
            report = _qualify(ctx, cid, allow_revision=True)
            rows.append({"candidate_id": cid,
                         "passed": report.get("passed") is True,
                         "distinct_source_hashes": report.get("distinct_source_hashes", 0),
                         "selected_perspective": report.get("selected_perspective")})
        if len([x for x in rows if x["passed"]]) < 2:
            raise RuntimeError(
                "fewer than two architectures survived national-scale qualification")
        artifact["national_scale_qualification"] = rows
        atomic_write_json(path, artifact)
        return path

    out["PRIVATE_QUALIFICATION"] = private_qualification

    original_provisional = out["PROVISIONAL_FRONTIER_MEMBER"]

    def provisional(machine):
        path = original_provisional(machine)
        artifact = read_json(path)
        rejected = []
        for cid in list(ctx.frontier.members):
            scale = (ctx.scores.get(cid) or {}).get("scale_qualification") or {}
            if scale.get("status") != "PASS" or scale.get("passed") is not True:
                ctx.frontier.members[cid]["status"] = "REJECTED_NATIONAL_SCALE"
                ctx.frontier.members[cid]["reason"] = (
                    "candidate failed national-scale qualification")
                rejected.append(cid)
        if not ctx.frontier.non_dominated():
            raise RuntimeError("no candidate passed semantic, durable, distributed and scale gates")
        ctx._save_arena()
        artifact["national_scale_rejected"] = rejected
        artifact["members"] = ctx.frontier.report()
        atomic_write_json(path, artifact)
        return path

    out["PROVISIONAL_FRONTIER_MEMBER"] = provisional

    original_round_build = crownmod._build_round_candidate

    def round_build(context, idea, cid, kind, ticket):
        result = original_round_build(context, idea, cid, kind, ticket)
        report = _qualify(context, cid, allow_revision=True)
        if report.get("status") != "PASS" or report.get("passed") is not True:
            raise RuntimeError(f"{cid}: round candidate failed national-scale qualification")
        return result

    crownmod._build_round_candidate = round_build

    original_frontier = out["FRONTIER_REVIEW"]

    def frontier_review(machine):
        path = original_frontier(machine)
        artifact = read_json(path)
        rejected = []
        for cid in list(ctx.frontier.members):
            if ctx.frontier.members[cid].get("status") != "ACTIVE":
                continue
            scale = (ctx.scores.get(cid) or {}).get("scale_qualification") or {}
            if scale.get("status") != "PASS" or scale.get("passed") is not True:
                ctx.frontier.members[cid]["status"] = "REJECTED_NATIONAL_SCALE"
                ctx.frontier.members[cid]["reason"] = (
                    "round candidate failed national-scale qualification")
                rejected.append(cid)
        if not ctx.frontier.non_dominated():
            raise RuntimeError("all frontier candidates failed national-scale qualification")
        ctx._save_arena()
        artifact["national_scale_rejected"] = rejected
        artifact["statuses"] = {k: v["status"]
                                for k, v in ctx.frontier.report().items()}
        atomic_write_json(path, artifact)
        return path

    out["FRONTIER_REVIEW"] = frontier_review

    original_replication = out["PRIVATE_REPLICATION"]

    def private_replication(machine):
        path = original_replication(machine)
        artifact = read_json(path)
        rows = []
        for cid in artifact.get("finalists") or []:
            report = _run(ctx, cid, "replication", SCALE_REPLICATION_EVENTS)
            ctx.record_score(cid, "scale_replication", report)
            passed = report.get("status") == "PASS" and report.get("passed") is True
            rows.append({"candidate_id": cid, "passed": passed,
                         "evidence_path": report.get("evidence_path")})
            if not passed and cid in ctx.frontier.members:
                ctx.frontier.members[cid]["status"] = "REJECTED_SCALE_REPLICATION"
                ctx.frontier.members[cid]["reason"] = (
                    "independent national-scale replication failed")
        if not ctx.frontier.non_dominated():
            raise RuntimeError("all finalists failed independent national-scale replication")
        ctx._save_arena()
        artifact["national_scale_replication"] = rows
        atomic_write_json(path, artifact)
        return path

    out["PRIVATE_REPLICATION"] = private_replication

    original_run_systems = crownmod._run_systems

    def run_systems(context, cid, label, events):
        report = original_run_systems(context, cid, label, events)
        if label == "crown":
            scale = _run(context, cid, "crown", SCALE_CROWN_EVENTS)
            context.record_score(cid, "scale_crown", scale)
            report["national_scale_arena"] = scale
            if scale.get("status") != "PASS" or scale.get("passed") is not True:
                report["passed"] = False
                report["status"] = "FAIL"
                report["scale_failure"] = True
        return report

    crownmod._run_systems = run_systems

    original_synthesis = out["ARCHITECTURE_EVIDENCE_SYNTHESIS"]

    def synthesis(machine):
        path = original_synthesis(machine)
        artifact = read_json(path)
        winner = artifact.get("candidate_id")
        scale = ((ctx.scores.get(winner) or {}).get("scale_crown") or {}) if winner else {}
        artifact["national_scale_crown"] = scale
        artifact["national_scale_crown_passed"] = bool(
            scale.get("status") == "PASS" and scale.get("passed") is True)
        atomic_write_json(path, artifact)
        return path

    out["ARCHITECTURE_EVIDENCE_SYNTHESIS"] = synthesis
    return out
