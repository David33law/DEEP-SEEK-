"""Independent bounded formal-model qualification for every Observatory architecture.

Two separately prompted pure transition models must preserve the parent controlled genome, survive
hidden exhaustive finite traces and produce the same evaluator-normalized behavioral digest. Each
model may receive one architecture-preserving revision based on aggregate counterexamples. Round
challengers, independent replication and the final crown follow the same path.
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
from . import observatory_roles as oroles
from .canonical import atomic_write_json, read_json
from .handlers import A


FORMAL_PERSPECTIVES = (
    ("specification-first", 0.10,
     "Construct the smallest pure model that directly represents the formalized INV-* obligations and no implementation accidents."),
    ("counterexample-first", 0.45,
     "Construct an independent pure model organized around adversarial traces, conflict observability, temporal counterexamples and fault recovery."),
)
FORMAL_REVISIONS = 1
FORMAL_QUAL_DEPTH = 3
FORMAL_REPLICATION_DEPTH = 4
FORMAL_CROWN_DEPTH = 5

FORMAL_SUPREMACY_KEYS = (
    "machine_checked_models_passed",
    "independent_model_agreement",
    "formal_replication_passed",
    "formal_crown_passed",
)
FORMAL_SEARCH_KEYS = FORMAL_SUPREMACY_KEYS[:-1]
FORMAL_AXES = (
    "canonical_authority_seat", "state_derivation_model", "temporal_model",
    "normative_effect_model", "consistency_commit_model",
    "replication_distribution_model", "trusted_core_topology",
)


def _path(ctx, cid, perspective):
    return A(ctx, "formal-candidate", f"{cid}-{perspective}.py")


def _expected(ctx, cid):
    genome = (ctx.candidates.get(cid) or {}).get("genome") or {}
    out = {}
    for axis in FORMAL_AXES:
        value = genome.get(axis) or {}
        if not isinstance(value, dict) or not value.get("class"):
            raise RuntimeError(f"{cid}: missing formal controlled axis {axis}")
        out[axis] = str(value["class"])
    return out


def _extract(obj):
    files = [x for x in obj.get("files", []) if x.get("path") == "formal_candidate.py"]
    if len(files) != 1:
        raise RuntimeError("formal model role must return exactly one formal_candidate.py")
    source = files[0]["content"]
    compile(source, "<formal-candidate>", "exec")
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
        raise RuntimeError(f"{cid}: formal model builder requires blueprint/formalization")
    contract = open(os.path.join(ctx.profile_pkg, "FORMAL-MODEL-CONTRACT.md"),
                    encoding="utf-8").read()
    _, obj, _, _ = ctx.ask(
        f"formal-model-builder-{perspective}",
        f"OBS-FORMAL-MODEL-BUILD::{cid}::{perspective}",
        "Implement formal_candidate.py as a pure deterministic bounded model of THIS exact "
        "architecture. " + directive + " The model manifest must report every supplied controlled "
        "class exactly. Do not hard-code evaluator seed data, do not call a model/network and do not "
        "replace the architecture with a generic event log. Return only the complete model file.",
        [("COMPLETE ARCHITECTURE BLUEPRINT", json.dumps(blueprint, ensure_ascii=False)),
         ("ARCHITECTURE FORMALIZATION", json.dumps(formalization, ensure_ascii=False)),
         ("EXPECTED CONTROLLED FORMAL MANIFEST", json.dumps(
             _expected(ctx, cid), ensure_ascii=False)),
         ("MACHINE-CHECKED MODEL CONTRACT", contract)],
        oroles.BUILD_SCHEMA, line=line, temperature=temperature)
    source = _extract(obj)
    path = _path(ctx, cid, perspective)
    digest = _write(path, source)
    return {"perspective": perspective, "path": path,
            "source": source, "source_sha256": digest}


def _run(ctx, cid, perspective, label, depth, candidate_path=None):
    path = candidate_path or _path(ctx, cid, perspective)
    if not os.path.isfile(path):
        return {"status": "FAIL", "passed": False,
                "reason": "formal model missing"}
    out = A(ctx, "reports", f"formal-{label}-{cid}-{perspective}.json")
    seed = int(hashlib.sha256(
        f"formal|{label}|{perspective}|{ctx.run_id}|{cid}".encode()).hexdigest()[:8], 16)
    command = [
        sys.executable,
        os.path.join(ctx.evaluator_dir, "observatory_formal_arena.py"),
        "--candidate", path, "--out", out,
        "--seed", str(seed), "--depth", str(depth), "--timeout", "14400",
    ]
    for axis, value in _expected(ctx, cid).items():
        command.extend(["--expected-" + axis.replace("_", "-"), value])
    result = subprocess.run(command, capture_output=True, text=True)
    if not os.path.exists(out):
        return {"status": "FAIL", "passed": False,
                "reason": "formal evaluator produced no report: "
                          + (result.stdout + result.stderr)[-1600:]}
    report = read_json(out)
    report["evaluator_returncode"] = result.returncode
    report["evidence_path"] = os.path.relpath(out, ctx.runtime).replace("\\", "/")
    report["candidate_path"] = os.path.relpath(path, ctx.runtime).replace("\\", "/")
    return report


def _revise(ctx, cid, row, attempt):
    blueprint = ctx.candidates[cid].get("blueprint") or {}
    formalization = ctx.candidates[cid].get("formalization") or {}
    contract = open(os.path.join(ctx.profile_pkg, "FORMAL-MODEL-CONTRACT.md"),
                    encoding="utf-8").read()
    perspective = row["perspective"] + f"-revision-{attempt}"
    _, obj, _, _ = ctx.ask(
        "formal-model-reviser",
        f"OBS-FORMAL-MODEL-REVISE::{cid}::{row['perspective']}::r{attempt}",
        "Revise formal_candidate.py to eliminate the exact aggregate bounded-model "
        "counterexamples while preserving the parent controlled genome and formalization. Do not "
        "hard-code hidden identifiers, traces or expected digest. Return the complete pure model.",
        [("COMPLETE ARCHITECTURE BLUEPRINT", json.dumps(blueprint, ensure_ascii=False)),
         ("ARCHITECTURE FORMALIZATION", json.dumps(formalization, ensure_ascii=False)),
         ("EXPECTED CONTROLLED FORMAL MANIFEST", json.dumps(
             _expected(ctx, cid), ensure_ascii=False)),
         ("MACHINE-CHECKED MODEL CONTRACT", contract),
         ("CURRENT formal_candidate.py", row["source"][:700000]),
         ("AGGREGATE BOUNDED COUNTEREXAMPLES", json.dumps({
             "counterexamples": row["report"].get("counterexamples", [])[:64],
             "directed": row["report"].get("directed", {}),
             "reason": row["report"].get("reason"),
         }, ensure_ascii=False)[:100000])],
        oroles.BUILD_SCHEMA, line="successor", temperature=0.20)
    source = _extract(obj)
    path = _path(ctx, cid, perspective)
    digest = _write(path, source)
    report = _run(ctx, cid, perspective, "qualification-revision",
                  FORMAL_QUAL_DEPTH, path)
    return {"perspective": perspective, "path": path, "source": source,
            "source_sha256": digest, "report": report}


def _qualify(ctx, cid, allow_revision=True):
    rows = []
    errors = []
    line = "main" if ctx.candidates[cid].get("kind") == "baseline" else "successor"
    for perspective, temperature, directive in FORMAL_PERSPECTIVES:
        try:
            row = _build(ctx, cid, perspective, temperature, directive, line=line)
            row["report"] = _run(ctx, cid, perspective, "qualification",
                                 FORMAL_QUAL_DEPTH, row["path"])
            if allow_revision and (row["report"].get("status") != "PASS"
                                   or row["report"].get("passed") is not True):
                row = _revise(ctx, cid, row, 1)
            rows.append(row)
        except Exception as exc:
            errors.append({"perspective": perspective, "error": str(exc)[:1800]})

    hashes = {x["source_sha256"] for x in rows}
    passed_rows = [x for x in rows if x["report"].get("status") == "PASS"
                   and x["report"].get("passed") is True]
    digests = {x["report"].get("behavioral_digest") for x in passed_rows}
    diversity = len(hashes) >= 2
    agreement = len(passed_rows) == 2 and len(digests) == 1 and None not in digests
    passed = diversity and agreement
    result = {
        "status": "PASS" if passed else "FAIL", "passed": passed,
        "source_diversity": diversity,
        "distinct_source_hashes": len(hashes),
        "independent_model_agreement": agreement,
        "behavioral_digest": next(iter(digests)) if agreement else None,
        "models": [{
            "perspective": row["perspective"],
            "source_sha256": row["source_sha256"],
            "passed": row["report"].get("passed") is True,
            "behavioral_digest": row["report"].get("behavioral_digest"),
            "trace_count": row["report"].get("trace_count"),
            "unique_state_count": row["report"].get("unique_state_count"),
            "counterexample_count": len(row["report"].get("counterexamples") or []),
            "evidence_path": row["report"].get("evidence_path"),
            "path": row["path"],
        } for row in rows],
        "errors": errors,
    }
    if passed:
        for row in rows:
            canonical = _path(ctx, cid, row["perspective"].split("-revision-")[0])
            if row["path"] != canonical:
                shutil.copyfile(row["path"], canonical)
        ctx.candidates[cid]["formal_model_paths"] = [
            _path(ctx, cid, perspective) for perspective, _t, _d in FORMAL_PERSPECTIVES]
        ctx.candidates[cid]["formal_behavioral_digest"] = result["behavioral_digest"]
        ctx.candidates[cid]["formal_models_qualified"] = True
    else:
        ctx.candidates[cid]["formal_models_qualified"] = False
    ctx.record_score(cid, "formal_qualification", result)
    ctx._save_arena()
    return result


def _replicate(ctx, cid, label, depth):
    rows = []
    for perspective, _temperature, _directive in FORMAL_PERSPECTIVES:
        report = _run(ctx, cid, perspective, label, depth)
        rows.append({"perspective": perspective, "report": report})
    digests = {x["report"].get("behavioral_digest") for x in rows
               if x["report"].get("status") == "PASS"
               and x["report"].get("passed") is True}
    passed = len(rows) == 2 \
        and all(x["report"].get("status") == "PASS"
                and x["report"].get("passed") is True for x in rows) \
        and len(digests) == 1 and None not in digests
    return {"status": "PASS" if passed else "FAIL", "passed": passed,
            "behavioral_digest": next(iter(digests)) if passed else None,
            "models": [{"perspective": x["perspective"],
                        "passed": x["report"].get("passed") is True,
                        "behavioral_digest": x["report"].get("behavioral_digest"),
                        "trace_count": x["report"].get("trace_count"),
                        "evidence_path": x["report"].get("evidence_path")}
                       for x in rows]}


def _install_ledger(ctx):
    if getattr(ctx.esc, "_formal_overlay_installed", False):
        return
    original_conditions = ctx.esc._supremacy_conditions
    original_summary = ctx.esc.supremacy_summary

    def conditions(self):
        result = original_conditions()
        incumbent = self.s.get("incumbent")
        scores = ctx.scores.get(incumbent) or {} if incumbent else {}
        qualification = scores.get("formal_qualification") or {}
        replication = scores.get("formal_replication") or {}
        crown = scores.get("formal_crown") or {}
        result.update({
            "machine_checked_models_passed": bool(
                qualification.get("status") == "PASS"
                and qualification.get("passed") is True),
            "independent_model_agreement": bool(
                qualification.get("independent_model_agreement") is True),
            "formal_replication_passed": bool(
                replication.get("status") == "PASS"
                and replication.get("passed") is True),
            "formal_crown_passed": bool(
                crown.get("status") == "PASS" and crown.get("passed") is True),
        })
        return result

    def summary(self):
        result = original_summary()
        result.update(conditions(self))
        result.update({
            "formal_model_count": len(FORMAL_PERSPECTIVES),
            "formal_revision_limit": FORMAL_REVISIONS,
            "formal_qualification_depth": FORMAL_QUAL_DEPTH,
            "formal_replication_depth": FORMAL_REPLICATION_DEPTH,
            "formal_crown_depth": FORMAL_CROWN_DEPTH,
            "formal_contract": "FORMAL-MODEL-CONTRACT.md",
        })
        return result

    ctx.esc._supremacy_conditions = MethodType(conditions, ctx.esc)
    ctx.esc.supremacy_summary = MethodType(summary, ctx.esc)
    ctx.esc._formal_overlay_installed = True

    for key in FORMAL_SUPREMACY_KEYS:
        if key not in escalation.SUPREMACY_KEYS:
            escalation.SUPREMACY_KEYS.append(key)
    for key in FORMAL_SEARCH_KEYS:
        if key not in escalation.SEARCH_SUPREMACY_KEYS:
            escalation.SEARCH_SUPREMACY_KEYS.append(key)
    schema = escalation.OBSERVATORY_PROOF_SCHEMA
    cond = schema["properties"]["conditions"]
    proof = schema["properties"]["supremacy"]
    for key in FORMAL_SUPREMACY_KEYS:
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
        formal = (self.scores.get(cid) or {}).get("formal_qualification") or {}
        vector["machine_checked_model_survival"] = (
            1.0 if formal.get("status") == "PASS"
            and formal.get("passed") is True else 0.0)
        trace_counts = [int(x.get("trace_count") or 0)
                        for x in formal.get("models", [])]
        vector["formal_trace_coverage"] = float(min(trace_counts) if trace_counts else 0)
        return vector

    ctx.dimension_vector = MethodType(dimension_vector, ctx)

    original_private = out["PRIVATE_QUALIFICATION"]

    def private_qualification(machine):
        path = original_private(machine)
        artifact = read_json(path)
        rows = []
        for cid in sorted(ctx.candidates):
            report = _qualify(ctx, cid, allow_revision=True)
            rows.append({"candidate_id": cid, "passed": report.get("passed") is True,
                         "agreement": report.get("independent_model_agreement"),
                         "behavioral_digest": report.get("behavioral_digest")})
        if len([x for x in rows if x["passed"]]) < 2:
            raise RuntimeError(
                "fewer than two architectures survived independent machine-checked models")
        artifact["machine_checked_models"] = rows
        atomic_write_json(path, artifact)
        return path

    out["PRIVATE_QUALIFICATION"] = private_qualification

    original_provisional = out["PROVISIONAL_FRONTIER_MEMBER"]

    def provisional(machine):
        path = original_provisional(machine)
        artifact = read_json(path)
        rejected = []
        for cid in list(ctx.frontier.members):
            formal = (ctx.scores.get(cid) or {}).get("formal_qualification") or {}
            if formal.get("status") != "PASS" or formal.get("passed") is not True:
                ctx.frontier.members[cid]["status"] = "REJECTED_FORMAL_MODEL"
                ctx.frontier.members[cid]["reason"] = (
                    "independent machine-checked models failed or disagreed")
                rejected.append(cid)
        if not ctx.frontier.non_dominated():
            raise RuntimeError("no candidate passed machine-checked model qualification")
        ctx._save_arena()
        artifact["formal_model_rejected"] = rejected
        artifact["members"] = ctx.frontier.report()
        atomic_write_json(path, artifact)
        return path

    out["PROVISIONAL_FRONTIER_MEMBER"] = provisional

    original_round_build = crownmod._build_round_candidate

    def round_build(context, idea, cid, kind, ticket):
        result = original_round_build(context, idea, cid, kind, ticket)
        report = _qualify(context, cid, allow_revision=True)
        if report.get("status") != "PASS" or report.get("passed") is not True:
            raise RuntimeError(f"{cid}: round candidate failed machine-checked models")
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
            formal = (ctx.scores.get(cid) or {}).get("formal_qualification") or {}
            if formal.get("status") != "PASS" or formal.get("passed") is not True:
                ctx.frontier.members[cid]["status"] = "REJECTED_FORMAL_MODEL"
                ctx.frontier.members[cid]["reason"] = (
                    "round candidate failed machine-checked model qualification")
                rejected.append(cid)
        if not ctx.frontier.non_dominated():
            raise RuntimeError("all frontier candidates failed machine-checked models")
        ctx._save_arena()
        artifact["formal_model_rejected"] = rejected
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
            report = _replicate(ctx, cid, "replication", FORMAL_REPLICATION_DEPTH)
            ctx.record_score(cid, "formal_replication", report)
            passed = report.get("status") == "PASS" and report.get("passed") is True
            rows.append({"candidate_id": cid, "passed": passed,
                         "behavioral_digest": report.get("behavioral_digest")})
            if not passed and cid in ctx.frontier.members:
                ctx.frontier.members[cid]["status"] = "REJECTED_FORMAL_REPLICATION"
                ctx.frontier.members[cid]["reason"] = (
                    "independent formal-model replication failed")
        if not ctx.frontier.non_dominated():
            raise RuntimeError("all finalists failed formal-model replication")
        ctx._save_arena()
        artifact["formal_model_replication"] = rows
        atomic_write_json(path, artifact)
        return path

    out["PRIVATE_REPLICATION"] = private_replication

    original_run_systems = crownmod._run_systems

    def run_systems(context, cid, label, events):
        report = original_run_systems(context, cid, label, events)
        if label == "crown":
            formal = _replicate(context, cid, "crown", FORMAL_CROWN_DEPTH)
            context.record_score(cid, "formal_crown", formal)
            report["machine_checked_formal_crown"] = formal
            if formal.get("status") != "PASS" or formal.get("passed") is not True:
                report["passed"] = False; report["status"] = "FAIL"
                report["formal_model_failure"] = True
        return report

    crownmod._run_systems = run_systems

    original_synthesis = out["ARCHITECTURE_EVIDENCE_SYNTHESIS"]

    def synthesis(machine):
        path = original_synthesis(machine)
        artifact = read_json(path)
        winner = artifact.get("candidate_id")
        formal = ((ctx.scores.get(winner) or {}).get("formal_crown") or {}) if winner else {}
        artifact["machine_checked_formal_crown"] = formal
        artifact["formal_crown_passed"] = bool(
            formal.get("status") == "PASS" and formal.get("passed") is True)
        atomic_write_json(path, artifact)
        return path

    out["ARCHITECTURE_EVIDENCE_SYNTHESIS"] = synthesis
    return out
