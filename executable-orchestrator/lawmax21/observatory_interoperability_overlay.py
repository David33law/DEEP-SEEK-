"""Independent legal-interoperability implementation search and conformance gates.

Two source-distinct projection implementations must preserve the controlled architecture genome,
pass hidden ELI/ELI-impact/ECLI/Akoma-Ntoso/LegalRuleML/PROV checks and agree on the normalized legal
identity/effect digest. Round challengers, independent replication and the crown use the same path.
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

PERSPECTIVES = (
    ("standards-first", 0.15,
     "Start from stable work/expression/manifestation, ECLI and normative-impact exchange semantics."),
    ("proof-projection-first", 0.45,
     "Start from one canonical root, evidence derivation and independently checkable read-only projections."),
)
REVISIONS = 1
QUAL_CASES = 24
REPLICATION_CASES = 48
CROWN_CASES = 96
MIN_DISTINCT_SOURCES = 2
AXES = ("identity_model", "temporal_model", "normative_effect_model",
        "provenance_proof_model", "publication_topology")
SUPREMACY_KEYS = (
    "legal_interoperability_passed",
    "interoperability_implementations_agree",
    "interoperability_replication_passed",
    "interoperability_crown_passed",
)
SEARCH_KEYS = SUPREMACY_KEYS[:-1]


def _path(ctx, cid, perspective):
    return A(ctx, "interoperability-candidate", f"{cid}-{perspective}.py")


def _expected(ctx, cid):
    genome = (ctx.candidates.get(cid) or {}).get("genome") or {}
    out = {}
    for axis in AXES:
        value = genome.get(axis) or {}
        if not isinstance(value, dict) or not value.get("class"):
            raise RuntimeError(f"{cid}: missing interoperability genome axis {axis}")
        out[axis] = str(value["class"])
    return out


def _extract(obj):
    files = [x for x in obj.get("files", [])
             if x.get("path") == "interoperability_candidate.py"]
    if len(files) != 1:
        raise RuntimeError(
            "interoperability role must return exactly one interoperability_candidate.py")
    source = files[0]["content"]
    compile(source, "<interoperability-candidate>", "exec")
    return source


def _write(path, source):
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(source)
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def _build(ctx, cid, perspective, temperature, directive, line="main"):
    candidate = ctx.candidates[cid]
    blueprint = candidate.get("blueprint") or {}
    formalization = candidate.get("formalization") or {}
    if not blueprint or not formalization:
        raise RuntimeError(f"{cid}: interoperability builder requires blueprint/formalization")
    contract = open(os.path.join(ctx.profile_pkg, "INTEROPERABILITY-CONTRACT.md"),
                    encoding="utf-8").read()
    _, obj, _, _ = ctx.ask(
        f"interoperability-builder-{perspective}",
        f"OBS-INTEROPERABILITY-BUILD::{cid}::{perspective}",
        "Implement interoperability_candidate.py as a deterministic read-only projection layer for "
        "THIS exact architecture. " + directive + " Preserve the supplied controlled classes, one "
        "canonical root, exact provision-version links, doctrine non-authority and explicit unknowns. "
        "Use only Python standard library; no network/model call exists. Do not turn an exchange "
        "serialization into a second authority seat.",
        [("COMPLETE ARCHITECTURE BLUEPRINT", json.dumps(blueprint, ensure_ascii=False)),
         ("ARCHITECTURE FORMALIZATION", json.dumps(formalization, ensure_ascii=False)),
         ("EXPECTED CONTROLLED INTEROPERABILITY MANIFEST",
          json.dumps(_expected(ctx, cid), ensure_ascii=False)),
         ("LEGAL INTEROPERABILITY CONTRACT", contract)],
        oroles.BUILD_SCHEMA, line=line, temperature=temperature)
    source = _extract(obj)
    path = _path(ctx, cid, perspective)
    return {"perspective": perspective, "path": path, "source": source,
            "source_sha256": _write(path, source)}


def _run(ctx, cid, perspective, label, cases, candidate_path=None):
    path = candidate_path or _path(ctx, cid, perspective)
    if not os.path.isfile(path):
        return {"status": "FAIL", "passed": False,
                "reason": "interoperability candidate missing"}
    out = A(ctx, "reports", f"interoperability-{label}-{cid}-{perspective}.json")
    seed = int(hashlib.sha256(
        f"interop|{label}|{perspective}|{ctx.run_id}|{cid}".encode()).hexdigest()[:8], 16)
    command = [sys.executable,
               os.path.join(ctx.evaluator_dir, "observatory_interoperability_arena.py"),
               "--candidate", path, "--out", out, "--seed", str(seed),
               "--cases", str(cases)]
    for axis, value in _expected(ctx, cid).items():
        command.extend(["--expected-" + axis.replace("_", "-"), value])
    result = subprocess.run(command, capture_output=True, text=True)
    if not os.path.exists(out):
        return {"status": "FAIL", "passed": False,
                "reason": "interoperability evaluator produced no report: "
                          + (result.stdout + result.stderr)[-1600:]}
    report = read_json(out)
    report["evaluator_returncode"] = result.returncode
    report["evidence_path"] = os.path.relpath(out, ctx.runtime).replace("\\", "/")
    report["candidate_path"] = os.path.relpath(path, ctx.runtime).replace("\\", "/")
    return report


def _revise(ctx, cid, row):
    contract = open(os.path.join(ctx.profile_pkg, "INTEROPERABILITY-CONTRACT.md"),
                    encoding="utf-8").read()
    perspective = row["perspective"] + "-revision-1"
    _, obj, _, _ = ctx.ask(
        "interoperability-reviser", f"OBS-INTEROPERABILITY-REVISE::{cid}::{perspective}",
        "Revise interoperability_candidate.py to fix the exact aggregate bounded-conformance "
        "failures. Preserve the controlled architecture, one-root projection rule, blueprint and "
        "formalization. Do not hard-code hidden bundle IDs or expected output bytes.",
        [("COMPLETE ARCHITECTURE BLUEPRINT",
          json.dumps(ctx.candidates[cid].get("blueprint") or {}, ensure_ascii=False)),
         ("ARCHITECTURE FORMALIZATION",
          json.dumps(ctx.candidates[cid].get("formalization") or {}, ensure_ascii=False)),
         ("EXPECTED CONTROLLED INTEROPERABILITY MANIFEST",
          json.dumps(_expected(ctx, cid), ensure_ascii=False)),
         ("LEGAL INTEROPERABILITY CONTRACT", contract),
         ("CURRENT interoperability_candidate.py", row["source"][:700000]),
         ("AGGREGATE CONFORMANCE FAILURES",
          json.dumps({"failures": row["report"].get("failures", [])[:64],
                      "reason": row["report"].get("reason")},
                     ensure_ascii=False)[:100000])],
        oroles.BUILD_SCHEMA, line="successor", temperature=0.20)
    source = _extract(obj); path = _path(ctx, cid, perspective)
    revised = {"perspective": perspective, "path": path, "source": source,
               "source_sha256": _write(path, source)}
    revised["report"] = _run(ctx, cid, perspective, "qualification-revision",
                             QUAL_CASES, path)
    return revised


def _qualify(ctx, cid, allow_revision=True):
    rows, errors = [], []
    line = "main" if ctx.candidates[cid].get("kind") == "baseline" else "successor"
    for perspective, temperature, directive in PERSPECTIVES:
        try:
            row = _build(ctx, cid, perspective, temperature, directive, line=line)
            row["report"] = _run(ctx, cid, perspective, "qualification",
                                 QUAL_CASES, row["path"])
            if allow_revision and (row["report"].get("status") != "PASS"
                                   or row["report"].get("passed") is not True):
                row = _revise(ctx, cid, row)
            rows.append(row)
        except Exception as exc:
            errors.append({"perspective": perspective, "error": str(exc)[:1800]})
    hashes = {row["source_sha256"] for row in rows}
    passed_rows = [row for row in rows if row["report"].get("status") == "PASS"
                   and row["report"].get("passed") is True]
    digests = {row["report"].get("semantic_digest") for row in passed_rows}
    diversity = len(hashes) >= MIN_DISTINCT_SOURCES
    agreement = len(passed_rows) == len(PERSPECTIVES) and len(digests) == 1 \
        and None not in digests
    passed = diversity and agreement
    result = {"status": "PASS" if passed else "FAIL", "passed": passed,
              "source_diversity": diversity, "distinct_source_hashes": len(hashes),
              "implementations_agree": agreement,
              "semantic_digest": next(iter(digests)) if agreement else None,
              "implementations": [{"perspective": row["perspective"],
                                   "source_sha256": row["source_sha256"],
                                   "passed": row["report"].get("passed") is True,
                                   "semantic_digest": row["report"].get("semantic_digest"),
                                   "cases": row["report"].get("cases"),
                                   "evidence_path": row["report"].get("evidence_path"),
                                   "path": row["path"]} for row in rows],
              "errors": errors}
    if passed:
        canonical_paths = []
        for (canonical_name, _temperature, _directive), row in zip(PERSPECTIVES, rows):
            destination = _path(ctx, cid, canonical_name)
            if row["path"] != destination:
                shutil.copyfile(row["path"], destination)
            canonical_paths.append(destination)
        ctx.candidates[cid]["interoperability_candidate_paths"] = canonical_paths
        ctx.candidates[cid]["interoperability_semantic_digest"] = result["semantic_digest"]
        ctx.candidates[cid]["interoperability_qualified"] = True
    else:
        ctx.candidates[cid]["interoperability_qualified"] = False
    ctx.record_score(cid, "interoperability_qualification", result)
    ctx._save_arena()
    return result


def _replicate(ctx, cid, label, cases):
    rows = []
    for perspective, _temperature, _directive in PERSPECTIVES:
        report = _run(ctx, cid, perspective, label, cases)
        rows.append({"perspective": perspective, "report": report})
    digests = {row["report"].get("semantic_digest") for row in rows
               if row["report"].get("status") == "PASS"
               and row["report"].get("passed") is True}
    passed = len(rows) == len(PERSPECTIVES) \
        and all(row["report"].get("status") == "PASS"
                and row["report"].get("passed") is True for row in rows) \
        and len(digests) == 1 and None not in digests
    return {"status": "PASS" if passed else "FAIL", "passed": passed,
            "semantic_digest": next(iter(digests)) if passed else None,
            "implementations": [{"perspective": row["perspective"],
                                 "passed": row["report"].get("passed") is True,
                                 "cases": row["report"].get("cases"),
                                 "evidence_path": row["report"].get("evidence_path")}
                                for row in rows]}


def _install_ledger(ctx):
    if getattr(ctx.esc, "_interoperability_overlay_installed", False):
        return
    original_conditions = ctx.esc._supremacy_conditions
    original_summary = ctx.esc.supremacy_summary

    def conditions(self):
        result = original_conditions()
        incumbent = self.s.get("incumbent")
        scores = (ctx.scores.get(incumbent) or {}) if incumbent else {}
        qualification = scores.get("interoperability_qualification") or {}
        replication = scores.get("interoperability_replication") or {}
        crown = scores.get("interoperability_crown") or {}
        result.update({
            "legal_interoperability_passed": bool(
                qualification.get("status") == "PASS"
                and qualification.get("passed") is True),
            "interoperability_implementations_agree": bool(
                qualification.get("implementations_agree") is True),
            "interoperability_replication_passed": bool(
                replication.get("status") == "PASS"
                and replication.get("passed") is True),
            "interoperability_crown_passed": bool(
                crown.get("status") == "PASS" and crown.get("passed") is True)})
        return result

    def summary(self):
        result = original_summary(); result.update(conditions(self))
        result.update({"interoperability_implementation_count": len(PERSPECTIVES),
                       "interoperability_revision_limit": REVISIONS,
                       "interoperability_qualification_cases": QUAL_CASES,
                       "interoperability_replication_cases": REPLICATION_CASES,
                       "interoperability_crown_cases": CROWN_CASES,
                       "interoperability_contract": "INTEROPERABILITY-CONTRACT.md"})
        return result

    ctx.esc._supremacy_conditions = MethodType(conditions, ctx.esc)
    ctx.esc.supremacy_summary = MethodType(summary, ctx.esc)
    ctx.esc._interoperability_overlay_installed = True
    for key in SUPREMACY_KEYS:
        if key not in escalation.SUPREMACY_KEYS:
            escalation.SUPREMACY_KEYS.append(key)
    for key in SEARCH_KEYS:
        if key not in escalation.SEARCH_SUPREMACY_KEYS:
            escalation.SEARCH_SUPREMACY_KEYS.append(key)
    schema = escalation.OBSERVATORY_PROOF_SCHEMA
    cond = schema["properties"]["conditions"]
    proof = schema["properties"]["supremacy"]
    for key in SUPREMACY_KEYS:
        if key not in cond["required"]:
            cond["required"].append(key)
        cond["properties"][key] = {"type": "boolean"}
        if key not in proof["required"]:
            proof["required"].append(key)
        proof["properties"][key] = {"type": "boolean"}


def install(ctx, handlers):
    _install_ledger(ctx); out = dict(handlers)
    original_vector = ctx.dimension_vector

    def dimension_vector(self, cid, hidden_rep, fidelity_rep=None):
        vector = original_vector(cid, hidden_rep, fidelity_rep)
        qualification = (self.scores.get(cid) or {}).get(
            "interoperability_qualification") or {}
        rows = qualification.get("implementations") or []
        vector["legal_interoperability_survival"] = (
            1.0 if qualification.get("passed") is True else 0.0)
        vector["interoperability_case_coverage"] = float(
            min((int(row.get("cases") or 0) for row in rows), default=0))
        return vector

    ctx.dimension_vector = MethodType(dimension_vector, ctx)
    original_private = out["PRIVATE_QUALIFICATION"]

    def private_qualification(machine):
        path = original_private(machine); artifact = read_json(path); rows = []
        for cid in sorted(ctx.candidates):
            report = _qualify(ctx, cid, allow_revision=True)
            rows.append({"candidate_id": cid, "passed": report.get("passed") is True,
                         "agreement": report.get("implementations_agree"),
                         "semantic_digest": report.get("semantic_digest")})
        if len([row for row in rows if row["passed"]]) < 2:
            raise RuntimeError("fewer than two architectures survived legal interoperability")
        artifact["legal_interoperability"] = rows; atomic_write_json(path, artifact)
        return path

    out["PRIVATE_QUALIFICATION"] = private_qualification
    original_provisional = out["PROVISIONAL_FRONTIER_MEMBER"]

    def provisional(machine):
        path = original_provisional(machine); artifact = read_json(path); rejected = []
        for cid in list(ctx.frontier.members):
            report = (ctx.scores.get(cid) or {}).get("interoperability_qualification") or {}
            if report.get("status") != "PASS" or report.get("passed") is not True:
                ctx.frontier.members[cid]["status"] = "REJECTED_INTEROPERABILITY"
                ctx.frontier.members[cid]["reason"] = "legal interoperability qualification failed"
                rejected.append(cid)
        if not ctx.frontier.non_dominated():
            raise RuntimeError("no candidate passed legal interoperability")
        ctx._save_arena(); artifact["interoperability_rejected"] = rejected
        artifact["members"] = ctx.frontier.report(); atomic_write_json(path, artifact)
        return path

    out["PROVISIONAL_FRONTIER_MEMBER"] = provisional
    original_round_build = crownmod._build_round_candidate

    def round_build(context, idea, cid, kind, ticket):
        result = original_round_build(context, idea, cid, kind, ticket)
        report = _qualify(context, cid, allow_revision=True)
        if report.get("status") != "PASS" or report.get("passed") is not True:
            raise RuntimeError(f"{cid}: round candidate failed legal interoperability")
        return result

    crownmod._build_round_candidate = round_build
    original_frontier = out["FRONTIER_REVIEW"]

    def frontier_review(machine):
        path = original_frontier(machine); artifact = read_json(path); rejected = []
        for cid, member in list(ctx.frontier.members.items()):
            if member.get("status") != "ACTIVE":
                continue
            report = (ctx.scores.get(cid) or {}).get("interoperability_qualification") or {}
            if report.get("status") != "PASS" or report.get("passed") is not True:
                member["status"] = "REJECTED_INTEROPERABILITY"
                member["reason"] = "round candidate failed legal interoperability"
                rejected.append(cid)
        if not ctx.frontier.non_dominated():
            raise RuntimeError("all frontier candidates failed legal interoperability")
        ctx._save_arena(); artifact["interoperability_rejected"] = rejected
        artifact["statuses"] = {key: value["status"]
                                for key, value in ctx.frontier.report().items()}
        atomic_write_json(path, artifact); return path

    out["FRONTIER_REVIEW"] = frontier_review
    original_replication = out["PRIVATE_REPLICATION"]

    def private_replication(machine):
        path = original_replication(machine); artifact = read_json(path); rows = []
        for cid in artifact.get("finalists") or []:
            report = _replicate(ctx, cid, "replication", REPLICATION_CASES)
            ctx.record_score(cid, "interoperability_replication", report)
            passed = report.get("passed") is True
            rows.append({"candidate_id": cid, "passed": passed,
                         "semantic_digest": report.get("semantic_digest")})
            if not passed and cid in ctx.frontier.members:
                ctx.frontier.members[cid]["status"] = "REJECTED_INTEROPERABILITY_REPLICATION"
                ctx.frontier.members[cid]["reason"] = "interoperability replication failed"
        if not ctx.frontier.non_dominated():
            raise RuntimeError("all finalists failed interoperability replication")
        ctx._save_arena(); artifact["interoperability_replication"] = rows
        atomic_write_json(path, artifact); return path

    out["PRIVATE_REPLICATION"] = private_replication
    original_run_systems = crownmod._run_systems

    def run_systems(context, cid, label, events):
        report = original_run_systems(context, cid, label, events)
        if label == "crown":
            interop = _replicate(context, cid, "crown", CROWN_CASES)
            context.record_score(cid, "interoperability_crown", interop)
            report["legal_interoperability_crown"] = interop
            if interop.get("passed") is not True:
                report["status"] = "FAIL"; report["passed"] = False
                report["interoperability_failure"] = True
        return report

    crownmod._run_systems = run_systems
    original_synthesis = out["ARCHITECTURE_EVIDENCE_SYNTHESIS"]

    def synthesis(machine):
        path = original_synthesis(machine); artifact = read_json(path)
        winner = artifact.get("candidate_id")
        report = ((ctx.scores.get(winner) or {}).get("interoperability_crown") or {}) \
            if winner else {}
        artifact["legal_interoperability_crown"] = report
        artifact["interoperability_crown_passed"] = report.get("passed") is True
        atomic_write_json(path, artifact); return path

    out["ARCHITECTURE_EVIDENCE_SYNTHESIS"] = synthesis
    return out
