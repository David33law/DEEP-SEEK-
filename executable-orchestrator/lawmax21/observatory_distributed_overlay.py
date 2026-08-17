"""Distributed implementation and fault qualification for every Observatory architecture.

Installed after semantic implementation search. Each semantic implementation receives a distributed
implementation faithful to its controlled replication/commit genome, up to two aggregate-diagnostic
revisions, and the independent distributed arena. The selected architecture must preserve at least
two source-distinct distributed implementations across its implementation-search group.

Independent replication and the final crown use fresh evaluator seeds and permit no revision. The
crown report is attached to the existing systems evidence before lower-bound, destroyer and public
supremacy analysis, so distributed claims are not a tail-only afterthought.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
from types import MethodType

from . import observatory_crown_overlay as crownmod
from . import observatory_escalation as escalation
from . import observatory_implementation_search_overlay as implmod
from . import observatory_roles as oroles
from .canonical import atomic_write_json, read_json
from .handlers import A


DISTRIBUTED_REVISIONS = 2
DISTRIBUTED_QUAL_EVENTS = 5000
DISTRIBUTED_REPLICATION_EVENTS = 10000
DISTRIBUTED_CROWN_EVENTS = 50000
MIN_DISTINCT_DISTRIBUTED_IMPLEMENTATIONS = 2

DISTRIBUTED_SUPREMACY_KEYS = (
    "distributed_implementation_diversity_proven",
    "distributed_failure_model_proven",
    "distributed_replication_passed",
    "distributed_crown_passed",
)
DISTRIBUTED_SEARCH_KEYS = DISTRIBUTED_SUPREMACY_KEYS[:-1]


def _distributed_path(ctx, cid):
    return A(ctx, "distributed-candidate", f"{cid}.py")


def _model(ctx, cid, axis):
    genome = (ctx.candidates.get(cid) or {}).get("genome") or {}
    value = genome.get(axis) or {}
    if not isinstance(value, dict) or not value.get("class"):
        raise RuntimeError(f"{cid}: missing controlled distributed genome axis {axis}")
    return str(value["class"])


def _perspective(ctx, cid):
    return str((ctx.candidates.get(cid) or {}).get(
        "implementation_perspective", "baseline"))


def _extract_source(obj):
    files = [x for x in obj.get("files", [])
             if x.get("path") == "distributed_candidate.py"]
    if len(files) != 1:
        raise RuntimeError(
            "distributed role must return exactly one distributed_candidate.py")
    source = files[0]["content"]
    compile(source, "<distributed-candidate>", "exec")
    return source


def _write_source(ctx, cid, source):
    path = _distributed_path(ctx, cid)
    with open(path, "w", encoding="utf-8") as f:
        f.write(source)
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    ctx.candidates[cid]["distributed_candidate_path"] = path
    ctx.candidates[cid]["distributed_source_sha256"] = digest
    ctx._save_arena()
    return path, digest


def _temperature(perspective):
    if "failure" in perspective:
        return 0.35
    if "minimal" in perspective:
        return 0.55
    if "repair" in perspective:
        return 0.70
    if "invariant" in perspective:
        return 0.15
    return 0.25


def _build_source(ctx, cid, line="main"):
    candidate = ctx.candidates[cid]
    blueprint = candidate.get("blueprint") or {}
    formalization = candidate.get("formalization") or {}
    if not blueprint or not formalization:
        raise RuntimeError(f"{cid}: distributed builder requires complete blueprint/formalization")
    replication = _model(ctx, cid, "replication_distribution_model")
    commit = _model(ctx, cid, "consistency_commit_model")
    contract = open(os.path.join(ctx.profile_pkg, "DISTRIBUTED-SYSTEMS-CONTRACT.md"),
                    encoding="utf-8").read()
    perspective = _perspective(ctx, cid)
    _, obj, _, _ = ctx.ask(
        f"distributed-systems-builder-{perspective}",
        f"OBS-DISTRIBUTED-BUILD::{cid}",
        "Implement distributed_candidate.py for THIS exact architecture and implementation "
        "perspective. The manifest must report the supplied controlled replication and commit "
        "classes exactly, and behavior must make those choices load-bearing. Do not return a generic "
        "single-node database with renamed constants. Use only Python standard library; network and "
        "model calls do not exist. Preserve one canonical legal truth and fail closed outside the "
        "declared fault assumptions.",
        [("COMPLETE ARCHITECTURE BLUEPRINT", json.dumps(blueprint, ensure_ascii=False)),
         ("ARCHITECTURE FORMALIZATION", json.dumps(formalization, ensure_ascii=False)),
         ("EXPECTED CONTROLLED DISTRIBUTED GENOME", json.dumps({
             "replication_distribution_model": replication,
             "consistency_commit_model": commit,
             "implementation_perspective": perspective,
         }, ensure_ascii=False)),
         ("DISTRIBUTED SYSTEMS CONTRACT", contract)],
        oroles.BUILD_SCHEMA, line=line, temperature=_temperature(perspective))
    source = _extract_source(obj)
    _write_source(ctx, cid, source)
    return source


def _run(ctx, cid, label, events):
    path = _distributed_path(ctx, cid)
    if not os.path.isfile(path):
        return {"status": "FAIL", "passed": False,
                "reason": "distributed candidate missing"}
    out = A(ctx, "reports", f"distributed-{label}-{cid}.json")
    seed = int(hashlib.sha256(
        f"distributed|{label}|{ctx.run_id}|{cid}".encode()).hexdigest()[:8], 16)
    result = subprocess.run([
        sys.executable,
        os.path.join(ctx.evaluator_dir, "observatory_distributed_arena.py"),
        "--candidate", path,
        "--out", out,
        "--expected-replication-model", _model(
            ctx, cid, "replication_distribution_model"),
        "--expected-commit-model", _model(
            ctx, cid, "consistency_commit_model"),
        "--seed", str(seed),
        "--large-events", str(events),
    ], capture_output=True, text=True)
    if not os.path.exists(out):
        return {"status": "FAIL", "passed": False,
                "reason": "distributed evaluator produced no report: "
                          + (result.stdout + result.stderr)[-1200:]}
    report = read_json(out)
    report["evaluator_returncode"] = result.returncode
    report["evidence_path"] = os.path.relpath(
        out, ctx.runtime).replace("\\", "/")
    return report


def _group_for(ctx, cid):
    groups = implmod._group_store(ctx)
    for base_id, record in groups.items():
        if cid == base_id or cid in (record.get("variant_ids") or []):
            return base_id, record
    return cid, groups.setdefault(cid, {
        "architecture_candidate_id": cid,
        "variant_ids": [cid],
        "selected_candidate_id": None,
        "selected_passed": False,
        "revision_history": [],
    })


def _record_hash(ctx, cid):
    base_id, record = _group_for(ctx, cid)
    hashes = record.setdefault("distributed_source_hashes", {})
    digest = (ctx.candidates.get(cid) or {}).get("distributed_source_sha256")
    if digest:
        hashes[cid] = digest
    record["distinct_distributed_source_hashes"] = len(set(hashes.values()))
    implmod._persist(ctx)
    ctx.esc._flush()
    return base_id, record


def _qualify(ctx, cid, allow_revision=True):
    if not os.path.isfile(_distributed_path(ctx, cid)):
        try:
            _build_source(ctx, cid,
                          line="main" if ctx.candidates[cid].get("kind") == "baseline"
                          else "successor")
        except Exception as exc:
            report = {"status": "FAIL", "passed": False,
                      "reason": f"distributed build failed: {exc}"}
            ctx.record_score(cid, "distributed_qualification", report)
            return report
    report = _run(ctx, cid, "qualification", DISTRIBUTED_QUAL_EVENTS)
    revisions = []
    if allow_revision:
        blueprint = ctx.candidates[cid].get("blueprint") or {}
        formalization = ctx.candidates[cid].get("formalization") or {}
        contract = open(os.path.join(ctx.profile_pkg, "DISTRIBUTED-SYSTEMS-CONTRACT.md"),
                        encoding="utf-8").read()
        for revision in range(1, DISTRIBUTED_REVISIONS + 1):
            if report.get("status") == "PASS" and report.get("passed") is True:
                break
            current = (open(_distributed_path(ctx, cid), encoding="utf-8").read()
                       if os.path.exists(_distributed_path(ctx, cid)) else "")
            try:
                _, obj, _, _ = ctx.ask(
                    "distributed-systems-reviser",
                    f"OBS-DISTRIBUTED-REVISE::{cid}::r{revision}",
                    "Revise distributed_candidate.py to fix the exact aggregate distributed fault "
                    "failures. Preserve the controlled replication/commit classes, blueprint and "
                    "formalization. Do not replace them with a generic reference solution and do not "
                    "infer hidden event fixtures. Return the complete file.",
                    [("COMPLETE ARCHITECTURE BLUEPRINT",
                      json.dumps(blueprint, ensure_ascii=False)),
                     ("ARCHITECTURE FORMALIZATION",
                      json.dumps(formalization, ensure_ascii=False)),
                     ("EXPECTED CONTROLLED DISTRIBUTED GENOME", json.dumps({
                         "replication_distribution_model": _model(
                             ctx, cid, "replication_distribution_model"),
                         "consistency_commit_model": _model(
                             ctx, cid, "consistency_commit_model"),
                     }, ensure_ascii=False)),
                     ("DISTRIBUTED SYSTEMS CONTRACT", contract),
                     ("CURRENT distributed_candidate.py", current[:700000]),
                     ("MEASURED DISTRIBUTED FAILURE",
                      json.dumps(report, ensure_ascii=False)[:80000])],
                    oroles.BUILD_SCHEMA, line="successor", temperature=0.25)
                source = _extract_source(obj)
                _write_source(ctx, cid, source)
                report = _run(
                    ctx, cid, f"qualification-rev{revision}",
                    DISTRIBUTED_QUAL_EVENTS)
                revisions.append({
                    "revision": revision,
                    "passed": report.get("passed") is True,
                    "source_sha256": hashlib.sha256(
                        source.encode("utf-8")).hexdigest(),
                })
            except Exception as exc:
                revisions.append({"revision": revision, "passed": False,
                                  "error": str(exc)[:1600]})
    report["revision_history"] = revisions
    ctx.record_score(cid, "distributed_qualification", report)
    ctx.candidates[cid]["distributed_qualified"] = bool(
        report.get("status") == "PASS" and report.get("passed") is True)
    ctx._save_arena()
    _record_hash(ctx, cid)
    return report


def _copy_candidate(ctx, source_id, target_id):
    src = _distributed_path(ctx, source_id)
    dst = _distributed_path(ctx, target_id)
    if os.path.exists(src):
        shutil.copyfile(src, dst)
        ctx.candidates[target_id]["distributed_candidate_path"] = dst
        ctx.candidates[target_id]["distributed_source_sha256"] = hashlib.sha256(
            open(dst, "rb").read()).hexdigest()
        ctx._save_arena()


def _install_ledger(ctx):
    if getattr(ctx.esc, "_distributed_overlay_installed", False):
        return
    original_conditions = ctx.esc._supremacy_conditions
    original_summary = ctx.esc.supremacy_summary

    def conditions(self):
        result = original_conditions()
        incumbent = self.s.get("incumbent")
        qualification = ((ctx.scores.get(incumbent) or {}).get(
            "distributed_qualification") or {}) if incumbent else {}
        replication = ((ctx.scores.get(incumbent) or {}).get(
            "distributed_replication") or {}) if incumbent else {}
        crown = ((ctx.scores.get(incumbent) or {}).get(
            "distributed_crown") or {}) if incumbent else {}
        groups = implmod._group_store(ctx)
        current = [groups.get(cid) for cid in ctx.candidates]
        result.update({
            "distributed_implementation_diversity_proven": bool(
                current and all(record and record.get(
                    "distinct_distributed_source_hashes", 0)
                    >= MIN_DISTINCT_DISTRIBUTED_IMPLEMENTATIONS
                    for record in current)),
            "distributed_failure_model_proven": bool(
                qualification.get("status") == "PASS"
                and qualification.get("passed") is True),
            "distributed_replication_passed": bool(
                replication.get("status") == "PASS"
                and replication.get("passed") is True),
            "distributed_crown_passed": bool(
                crown.get("status") == "PASS" and crown.get("passed") is True),
        })
        return result

    def summary(self):
        result = original_summary()
        result.update(conditions(self))
        result.update({
            "distributed_minimum_distinct_sources": (
                MIN_DISTINCT_DISTRIBUTED_IMPLEMENTATIONS),
            "distributed_revision_limit": DISTRIBUTED_REVISIONS,
            "distributed_qualification_events": DISTRIBUTED_QUAL_EVENTS,
            "distributed_replication_events": DISTRIBUTED_REPLICATION_EVENTS,
            "distributed_crown_events": DISTRIBUTED_CROWN_EVENTS,
            "distributed_contract": "DISTRIBUTED-SYSTEMS-CONTRACT.md",
        })
        return result

    ctx.esc._supremacy_conditions = MethodType(conditions, ctx.esc)
    ctx.esc.supremacy_summary = MethodType(summary, ctx.esc)
    ctx.esc._distributed_overlay_installed = True

    for key in DISTRIBUTED_SUPREMACY_KEYS:
        if key not in escalation.SUPREMACY_KEYS:
            escalation.SUPREMACY_KEYS.append(key)
    for key in DISTRIBUTED_SEARCH_KEYS:
        if key not in escalation.SEARCH_SUPREMACY_KEYS:
            escalation.SEARCH_SUPREMACY_KEYS.append(key)
    schema = escalation.OBSERVATORY_PROOF_SCHEMA
    cond = schema["properties"]["conditions"]
    proof = schema["properties"]["supremacy"]
    for key in DISTRIBUTED_SUPREMACY_KEYS:
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
        distributed = (self.scores.get(cid) or {}).get(
            "distributed_qualification") or {}
        vector["distributed_fault_survival"] = (
            1.0 if distributed.get("status") == "PASS"
            and distributed.get("passed") is True else 0.0)
        vector["distributed_events_per_second"] = float(
            distributed.get("events_per_second_baseline", 0.0))
        return vector

    ctx.dimension_vector = MethodType(dimension_vector, ctx)

    original_run_systems = crownmod._run_systems

    def run_systems(context, cid, label, events):
        report = original_run_systems(context, cid, label, events)
        if label == "replication":
            distributed = _run(
                context, cid, "replication", DISTRIBUTED_REPLICATION_EVENTS)
            context.record_score(cid, "distributed_replication", distributed)
            report["distributed_arena"] = distributed
        elif label == "crown":
            distributed = _run(
                context, cid, "crown", DISTRIBUTED_CROWN_EVENTS)
            context.record_score(cid, "distributed_crown", distributed)
            report["distributed_arena"] = distributed
        return report

    crownmod._run_systems = run_systems

    original_qualify_systems = crownmod._qualify_systems

    def qualify_systems(context, cid, allow_revision=True):
        systems = original_qualify_systems(context, cid, allow_revision)
        distributed = _qualify(context, cid, allow_revision=allow_revision)
        systems["distributed_qualification"] = distributed
        return systems

    crownmod._qualify_systems = qualify_systems

    original_hard_failures = implmod._hard_failures

    def hard_failures(context, cid):
        failures = list(original_hard_failures(context, cid))
        distributed = (context.scores.get(cid) or {}).get(
            "distributed_qualification") or {}
        if distributed.get("status") != "PASS" or distributed.get("passed") is not True:
            failures.append({
                "dimension": "distributed_failure_model",
                "value": distributed.get("status"),
                "required": "PASS", "direction": "exact",
            })
        return failures

    implmod._hard_failures = hard_failures

    original_copy_systems = implmod._copy_systems_candidate

    def copy_systems(context, source_id, target_id):
        original_copy_systems(context, source_id, target_id)
        _copy_candidate(context, source_id, target_id)
        base_id, record = _group_for(context, target_id)
        digest = (context.candidates.get(target_id) or {}).get(
            "distributed_source_sha256")
        if digest:
            record.setdefault("distributed_source_hashes", {})[target_id] = digest
            record["distinct_distributed_source_hashes"] = len(set(
                record["distributed_source_hashes"].values()))
            implmod._persist(context)
            context.esc._flush()

    implmod._copy_systems_candidate = copy_systems

    original_replication = out["PRIVATE_REPLICATION"]

    def private_replication(machine):
        path = original_replication(machine)
        artifact = read_json(path)
        distributed_rows = []
        for cid in artifact.get("finalists") or []:
            report = (ctx.scores.get(cid) or {}).get("distributed_replication")
            if not report:
                report = _run(
                    ctx, cid, "replication", DISTRIBUTED_REPLICATION_EVENTS)
                ctx.record_score(cid, "distributed_replication", report)
            passed = report.get("status") == "PASS" and report.get("passed") is True
            distributed_rows.append({
                "candidate_id": cid, "passed": passed,
                "evidence_path": report.get("evidence_path"),
            })
            if not passed and cid in ctx.frontier.members:
                ctx.frontier.members[cid]["status"] = "REJECTED_DISTRIBUTED_REPLICATION"
                ctx.frontier.members[cid]["reason"] = (
                    "independent distributed fault replication failed")
                ctx.esc.record_axiom_violation(
                    cid, "distributed_canonical_integrity",
                    "failed independent distributed replication")
        if not ctx.frontier.non_dominated():
            raise RuntimeError(
                "all finalists failed independent distributed replication")
        ctx._save_arena()
        artifact["distributed_replication"] = distributed_rows
        atomic_write_json(path, artifact)
        return path

    out["PRIVATE_REPLICATION"] = private_replication

    original_synthesis = out["ARCHITECTURE_EVIDENCE_SYNTHESIS"]

    def synthesis(machine):
        # crownmod._run_systems is already patched. The original synthesis will therefore attach the
        # distributed crown report before lower-bound, destroyer and public-case calls.
        path = original_synthesis(machine)
        artifact = read_json(path)
        winner = artifact.get("candidate_id")
        distributed = ((ctx.scores.get(winner) or {}).get(
            "distributed_crown") or {}) if winner else {}
        artifact["distributed_crown"] = distributed
        artifact["distributed_crown_passed"] = bool(
            distributed.get("status") == "PASS"
            and distributed.get("passed") is True)
        atomic_write_json(path, artifact)
        return path

    out["ARCHITECTURE_EVIDENCE_SYNTHESIS"] = synthesis
    return out
