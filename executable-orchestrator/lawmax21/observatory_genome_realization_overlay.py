"""Executable controlled-genome realization audit for Observatory architectures.

Two independent auditors must bind every controlled class to real AST definitions, frozen INV-* IDs
and persisted executable evidence. The trusted validator reproduces every citation mechanically. The
audit runs at qualification, independent replication and crown and becomes an explicit terminal
condition.
"""
import ast
import glob
import hashlib
import json
import os
from types import MethodType

from . import observatory_crown_overlay as crownmod
from . import observatory_escalation as escalation
from . import observatory_formal_overlay as formal
from . import observatory_interoperability_overlay as interop
from . import observatory_roles as oroles
from .canonical import atomic_write_json, read_json, sha256_file, sha256_obj
from .handlers import A

AUDITORS = ("A", "B")
SOURCE_EXCERPT_LIMIT = 80_000
SUPREMACY_KEYS = (
    "genome_realization_proven",
    "genome_realization_replication_passed",
    "genome_realization_crown_passed",
)
SEARCH_KEYS = SUPREMACY_KEYS[:-1]
ARTIFACTS = (
    "semantic", "systems", "distributed", "scale",
    "formal_A", "formal_B", "interoperability_A", "interoperability_B")

REQUIRED_GROUPS = {
    "canonical_authority_seat": ("semantic", "formal"),
    "evidence_primitive": ("semantic", "formal"),
    "identity_model": ("semantic", "formal", "interoperability"),
    "state_derivation_model": ("semantic", "formal"),
    "temporal_model": ("semantic", "formal", "interoperability"),
    "normative_effect_model": ("semantic", "formal", "interoperability"),
    "consistency_commit_model": ("distributed", "formal"),
    "replication_distribution_model": ("distributed", "formal"),
    "trusted_core_topology": ("formal", "systems"),
    "provenance_proof_model": ("semantic", "interoperability"),
    "publication_topology": ("semantic", "interoperability"),
    "governance_evolution_model": ("semantic", "formal"),
    "scaling_partition_model": ("scale",),
}

SYMBOL_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["artifact", "symbol", "reason"],
    "properties": {
        "artifact": {"enum": list(ARTIFACTS)},
        "symbol": {"type": "string", "pattern": "^[A-Za-z_][A-Za-z0-9_]*$",
                   "maxLength": 200},
        "reason": {"type": "string", "minLength": 12, "maxLength": 12000}}}
AXIS_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["axis", "class", "realized", "source_symbols",
                 "invariant_ids", "evidence_refs", "removal_failure",
                 "falsifier", "blockers"],
    "properties": {
        "axis": {"enum": list(oroles.GENOME_FIELDS)},
        "class": {"type": "string", "minLength": 2, "maxLength": 160},
        "realized": {"type": "boolean"},
        "source_symbols": {"type": "array", "minItems": 1, "maxItems": 64,
                           "items": SYMBOL_SCHEMA},
        "invariant_ids": {"type": "array", "minItems": 1, "maxItems": 64,
                          "items": {"type": "string", "minLength": 2,
                                    "maxLength": 200}},
        "evidence_refs": {"type": "array", "minItems": 1, "maxItems": 64,
                          "items": {"type": "string", "minLength": 3,
                                    "maxLength": 2000}},
        "removal_failure": {"type": "string", "minLength": 20, "maxLength": 16000},
        "falsifier": {"type": "string", "minLength": 20, "maxLength": 16000},
        "blockers": {"type": "array", "maxItems": 32,
                     "items": {"type": "string", "minLength": 5,
                               "maxLength": 12000}}}}
AUDIT_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object", "additionalProperties": False,
    "required": ["auditor_id", "candidate_id", "axis_reviews", "overall_pass",
                 "architecture_level_blockers", "summary"],
    "properties": {
        "auditor_id": {"type": "string", "minLength": 1, "maxLength": 120},
        "candidate_id": {"type": "string", "minLength": 2, "maxLength": 160},
        "axis_reviews": {"type": "array", "minItems": len(oroles.GENOME_FIELDS),
                         "maxItems": len(oroles.GENOME_FIELDS),
                         "items": AXIS_SCHEMA},
        "overall_pass": {"type": "boolean"},
        "architecture_level_blockers": {"type": "array", "maxItems": 64,
            "items": {"type": "string", "minLength": 5, "maxLength": 16000}},
        "summary": {"type": "string", "minLength": 30, "maxLength": 30000}}}


def _artifact_paths(ctx, cid):
    formal_paths = [formal._path(ctx, cid, perspective)
                    for perspective, _temperature, _directive
                    in formal.FORMAL_PERSPECTIVES]
    interop_paths = [interop._path(ctx, cid, perspective)
                     for perspective, _temperature, _directive in interop.PERSPECTIVES]
    return {
        "semantic": A(ctx, "candidate-src", f"{cid}.py"),
        "systems": A(ctx, "systems-candidate", f"{cid}.py"),
        "distributed": A(ctx, "distributed-candidate", f"{cid}.py"),
        "scale": A(ctx, "scale-candidate", f"{cid}.py"),
        "formal_A": formal_paths[0], "formal_B": formal_paths[1],
        "interoperability_A": interop_paths[0],
        "interoperability_B": interop_paths[1]}


def _ast_inventory(source):
    tree = ast.parse(source)
    definitions = set()
    symbols = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            definitions.add(node.name)
            symbols.add(node.name)
        elif isinstance(node, ast.Name):
            symbols.add(node.id)
        elif isinstance(node, ast.Attribute):
            symbols.add(node.attr)
        elif isinstance(node, ast.arg):
            symbols.add(node.arg)
    return sorted(definitions), sorted(symbols)


def _source_census(ctx, cid):
    census = {}
    for artifact, path in _artifact_paths(ctx, cid).items():
        if not os.path.isfile(path):
            raise RuntimeError(
                f"{cid}: genome-realization artifact missing: {artifact}={path}")
        source = open(path, encoding="utf-8").read()
        definitions, symbols = _ast_inventory(source)
        if not definitions:
            raise RuntimeError(
                f"{cid}: genome-realization artifact has no AST definitions: {artifact}")
        census[artifact] = {
            "path": os.path.relpath(path, ctx.runtime).replace("\\", "/"),
            "sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
            "bytes": len(source.encode("utf-8")),
            "definitions": definitions,
            "symbols": symbols,
            "source_excerpt": source[:SOURCE_EXCERPT_LIMIT]}
    return census


def _invariant_ids(ctx, cid):
    formalization = (ctx.candidates.get(cid) or {}).get("formalization") or {}
    values = formalization.get("invariant_set") or []
    ids = set()
    for row in values:
        if isinstance(row, dict):
            value = row.get("id") or row.get("invariant_id")
        else:
            value = row
        if value:
            ids.add(str(value))
    if not ids:
        raise RuntimeError(f"{cid}: formalization has no invariant IDs")
    return ids


def _evidence_group(path):
    name = os.path.basename(path).lower()
    if name.startswith("systems-"):
        return "systems"
    if name.startswith("distributed-"):
        return "distributed"
    if name.startswith("scale-"):
        return "scale"
    if name.startswith("formal-"):
        return "formal"
    if name.startswith("interoperability-"):
        return "interoperability"
    if name.startswith("cross-model-"):
        return "cross_model"
    if ("observatory-hidden-" in name or "visible" in name
            or "fidelity" in name or "implementation-search" in name):
        return "semantic"
    return "other"


def _evidence_catalog(ctx, cid):
    paths = set()
    reports_root = A(ctx, "reports", "x")[:-1]
    candidate_reports = []
    if os.path.isdir(reports_root):
        for path in glob.glob(os.path.join(reports_root, "*.json")):
            if cid in os.path.basename(path):
                paths.add(path)
                candidate_reports.append(path)
    for path in (
            A(ctx, "candidates", "implementation-search.json"),
            A(ctx, "frontier", f"members-round{ctx.round}.json")):
        if os.path.isfile(path):
            paths.add(path)
    if not candidate_reports:
        raise RuntimeError(f"{cid}: no candidate-specific executable reports exist")
    catalog = {}
    for path in sorted(paths):
        relative = os.path.relpath(path, ctx.runtime).replace("\\", "/")
        row = {"path": relative, "sha256": sha256_file(path),
               "bytes": os.path.getsize(path),
               "group": _evidence_group(path)}
        try:
            parsed = read_json(path)
        except Exception:
            parsed = None
        if isinstance(parsed, dict):
            row["status"] = parsed.get("status")
            row["passed"] = parsed.get("passed")
        catalog[relative] = row
    required_groups = {
        group for groups in REQUIRED_GROUPS.values() for group in groups}
    available_groups = {row["group"] for row in catalog.values()}
    missing = sorted(required_groups - available_groups)
    if missing:
        raise RuntimeError(
            f"{cid}: persisted evidence lacks required groups: {', '.join(missing)}")
    return catalog


def _class(genome, axis):
    value = (genome or {}).get(axis) or {}
    return str(value.get("class") or "") if isinstance(value, dict) else ""


def _artifact_group(artifact):
    if artifact.startswith("formal_"):
        return "formal"
    if artifact.startswith("interoperability_"):
        return "interoperability"
    if artifact in ("semantic", "systems", "distributed", "scale"):
        return artifact
    return ""


def _validate(ctx, cid, report, census, invariants, evidence):
    if report.get("candidate_id") != cid:
        raise RuntimeError("genome-realization auditor returned wrong candidate ID")
    reviews = report.get("axis_reviews") or []
    by_axis = {row.get("axis"): row for row in reviews}
    if len(by_axis) != len(reviews) or set(by_axis) != set(oroles.GENOME_FIELDS):
        raise RuntimeError(
            "genome-realization auditor did not review every axis exactly once")
    genome = ctx.candidates[cid].get("genome") or {}
    validated = []
    for axis in oroles.GENOME_FIELDS:
        row = by_axis[axis]
        expected = _class(genome, axis)
        if not expected or row.get("class") != expected:
            raise RuntimeError(f"{cid}/{axis}: controlled class mismatch")
        if row.get("realized") is not True or row.get("blockers"):
            raise RuntimeError(f"{cid}/{axis}: auditor did not prove realization")
        cited_groups = set()
        verified_symbols = []
        for citation in row.get("source_symbols") or []:
            artifact = citation["artifact"]
            symbol = citation["symbol"]
            if symbol not in set(census[artifact]["definitions"]):
                raise RuntimeError(
                    f"{cid}/{axis}: citation is not a real AST definition "
                    f"{artifact}:{symbol}")
            group = _artifact_group(artifact)
            cited_groups.add(group)
            verified_symbols.append({
                "artifact": artifact, "symbol": symbol,
                "source_sha256": census[artifact]["sha256"]})
        missing_groups = sorted(set(REQUIRED_GROUPS[axis]) - cited_groups)
        if missing_groups:
            raise RuntimeError(
                f"{cid}/{axis}: missing required source groups: "
                + ", ".join(missing_groups))
        cited_invariants = set(
            str(value) for value in row.get("invariant_ids") or [])
        unknown = sorted(cited_invariants - invariants)
        if unknown or not cited_invariants:
            raise RuntimeError(
                f"{cid}/{axis}: invented or absent INV-* citations: {unknown}")
        verified_evidence = []
        evidence_groups = set()
        for reference in row.get("evidence_refs") or []:
            if reference not in evidence:
                raise RuntimeError(
                    f"{cid}/{axis}: nonexistent evidence path {reference}")
            verified_evidence.append(evidence[reference])
            evidence_groups.add(evidence[reference]["group"])
        missing_evidence_groups = sorted(
            set(REQUIRED_GROUPS[axis]) - evidence_groups)
        if missing_evidence_groups:
            raise RuntimeError(
                f"{cid}/{axis}: missing required evidence groups: "
                + ", ".join(missing_evidence_groups))
        validated.append({
            "axis": axis, "class": expected,
            "verified_symbols": verified_symbols,
            "verified_invariant_ids": sorted(cited_invariants),
            "verified_evidence": verified_evidence,
            "removal_failure": row["removal_failure"],
            "falsifier": row["falsifier"]})
    if report.get("overall_pass") is not True \
            or report.get("architecture_level_blockers"):
        raise RuntimeError(
            f"{cid}: architecture-level realization audit did not pass")
    return validated


def _passes(report):
    return (isinstance(report, dict)
            and report.get("status") == "PASS"
            and report.get("passed") is True
            and report.get("consensus") is True
            and report.get("all_axes_realized") is True)


def _audit(ctx, cid, label):
    census = _source_census(ctx, cid)
    invariants = _invariant_ids(ctx, cid)
    evidence = _evidence_catalog(ctx, cid)
    genome = ctx.candidates[cid].get("genome") or {}
    contract_path = os.path.join(
        ctx.profile_pkg, "GENOME-REALIZATION-CONTRACT.md")
    contract = open(contract_path, encoding="utf-8").read()
    prompt_census = {
        key: {
            "path": value["path"],
            "sha256": value["sha256"],
            "definitions": value["definitions"],
            "symbols": value["symbols"],
            "source_excerpt": value["source_excerpt"],
        }
        for key, value in census.items()
    }
    reports = []
    for tag in AUDITORS:
        logical_id, report, _, _ = ctx.ask(
            f"genome-realization-auditor-{tag}",
            f"OBS-GENOME-REALIZATION-{label}-{tag}::{cid}",
            "Prove or refute whether every controlled genome axis is genuinely realized in the "
            "actual source artifacts and executable evidence. Cite only AST definitions, INV-* IDs "
            "and runtime evidence paths supplied below. A label, constant, imported name, comment "
            "or family name alone is never enough. Return every axis exactly once, cite every "
            "required source/evidence group and fail closed on uncertainty.",
            [("CONTROLLED GENOME", json.dumps(genome, ensure_ascii=False)),
             ("COMPLETE BLUEPRINT", json.dumps(
                 ctx.candidates[cid].get("blueprint") or {},
                 ensure_ascii=False)),
             ("FORMALIZATION", json.dumps(
                 ctx.candidates[cid].get("formalization") or {},
                 ensure_ascii=False)),
             ("AST SOURCE CENSUS", json.dumps(
                 prompt_census, ensure_ascii=False)),
             ("PERSISTED EVIDENCE CATALOG", json.dumps(
                 list(evidence.values()), ensure_ascii=False)),
             ("GENOME REALIZATION CONTRACT", contract)],
            AUDIT_SCHEMA, line="successor", temperature=0.0)
        validated = _validate(
            ctx, cid, report, census, invariants, evidence)
        reports.append({
            "auditor": tag,
            "auditor_id": report["auditor_id"],
            "logical_id": logical_id,
            "report": report,
            "validated_axes": validated,
            "report_sha256": sha256_obj(report)})
    independent = (
        len(reports) == len(AUDITORS)
        and len({row["auditor_id"] for row in reports}) == len(AUDITORS)
        and len({row["logical_id"] for row in reports}) == len(AUDITORS)
        and len({row["report_sha256"] for row in reports}) == len(AUDITORS))
    consensus = independent and all(
        len(row["validated_axes"]) == len(oroles.GENOME_FIELDS)
        for row in reports)
    path = A(ctx, "architecture", f"genome-realization-{label}-{cid}.json")
    relative = os.path.relpath(path, ctx.runtime).replace("\\", "/")
    artifact = {
        "status": "PASS" if consensus else "FAIL",
        "passed": consensus,
        "candidate_id": cid,
        "label": label,
        "genome_sha256": sha256_obj(genome),
        "source_census": {
            key: {k: v for k, v in value.items()
                  if k != "source_excerpt"}
            for key, value in census.items()},
        "evidence_catalog": list(evidence.values()),
        "auditors": reports,
        "independent_auditors": independent,
        "consensus": consensus,
        "all_axes_realized": consensus,
        "verified_axis_count": (
            len(oroles.GENOME_FIELDS) if consensus else 0),
        "contract_sha256": sha256_file(contract_path),
        "evidence_path": relative,
    }
    atomic_write_json(path, artifact)
    return artifact


def _install_ledger(ctx):
    if getattr(ctx.esc, "_genome_realization_installed", False):
        return
    original_conditions = ctx.esc._supremacy_conditions
    original_summary = ctx.esc.supremacy_summary

    def conditions(self):
        result = original_conditions()
        incumbent = self.s.get("incumbent")
        scores = (ctx.scores.get(incumbent) or {}) if incumbent else {}
        result.update({
            "genome_realization_proven": _passes(scores.get(
                "genome_realization_qualification")),
            "genome_realization_replication_passed": _passes(scores.get(
                "genome_realization_replication")),
            "genome_realization_crown_passed": _passes(scores.get(
                "genome_realization_crown"))})
        return result

    def summary(self):
        result = original_summary()
        result.update(conditions(self))
        result.update({
            "genome_realization_auditors": len(AUDITORS),
            "genome_realization_axes": len(oroles.GENOME_FIELDS),
            "genome_realization_contract": "GENOME-REALIZATION-CONTRACT.md"})
        return result

    ctx.esc._supremacy_conditions = MethodType(conditions, ctx.esc)
    ctx.esc.supremacy_summary = MethodType(summary, ctx.esc)
    ctx.esc._genome_realization_installed = True
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


def _filter(ctx, score_key, reason):
    rejected = []
    for cid, member in list(ctx.frontier.members.items()):
        if member.get("status") != "ACTIVE":
            continue
        report = (ctx.scores.get(cid) or {}).get(score_key) or {}
        if not _passes(report):
            member["status"] = "REJECTED_GENOME_REALIZATION"
            member["reason"] = reason
            rejected.append(cid)
    if not ctx.frontier.non_dominated():
        raise RuntimeError(
            "no candidate survived executable genome-realization audit")
    ctx._save_arena()
    return rejected


def install(ctx, handlers):
    _install_ledger(ctx)
    out = dict(handlers)
    original_vector = ctx.dimension_vector

    def dimension_vector(self, cid, hidden_rep, fidelity_rep=None):
        vector = original_vector(cid, hidden_rep, fidelity_rep)
        report = (self.scores.get(cid) or {}).get(
            "genome_realization_qualification") or {}
        vector["genome_realization_survival"] = (
            1.0 if _passes(report) else 0.0)
        return vector

    ctx.dimension_vector = MethodType(dimension_vector, ctx)
    original_private = out["PRIVATE_QUALIFICATION"]

    def private_qualification(machine):
        path = original_private(machine)
        artifact = read_json(path)
        rows = []
        for cid in sorted(ctx.candidates):
            report = _audit(ctx, cid, "qualification")
            ctx.record_score(cid, "genome_realization_qualification", report)
            rows.append({
                "candidate_id": cid,
                "passed": _passes(report),
                "evidence_path": report["evidence_path"]})
        if len([row for row in rows if row["passed"]]) < 2:
            raise RuntimeError(
                "fewer than two architectures survived genome realization")
        artifact["genome_realization"] = rows
        atomic_write_json(path, artifact)
        return path

    out["PRIVATE_QUALIFICATION"] = private_qualification
    original_provisional = out["PROVISIONAL_FRONTIER_MEMBER"]

    def provisional(machine):
        path = original_provisional(machine)
        artifact = read_json(path)
        artifact["genome_realization_rejected"] = _filter(
            ctx, "genome_realization_qualification",
            "genome realization failed")
        artifact["members"] = ctx.frontier.report()
        atomic_write_json(path, artifact)
        return path

    out["PROVISIONAL_FRONTIER_MEMBER"] = provisional
    original_round = crownmod._build_round_candidate

    def round_build(context, idea, cid, kind, ticket):
        result = original_round(context, idea, cid, kind, ticket)
        report = _audit(context, cid, "qualification")
        context.record_score(
            cid, "genome_realization_qualification", report)
        if not _passes(report):
            raise RuntimeError(
                f"{cid}: executable genome realization failed")
        return result

    crownmod._build_round_candidate = round_build
    original_frontier = out["FRONTIER_REVIEW"]

    def frontier_review(machine):
        path = original_frontier(machine)
        artifact = read_json(path)
        artifact["genome_realization_rejected"] = _filter(
            ctx, "genome_realization_qualification",
            "round candidate genome realization failed")
        artifact["statuses"] = {
            key: value["status"]
            for key, value in ctx.frontier.report().items()}
        atomic_write_json(path, artifact)
        return path

    out["FRONTIER_REVIEW"] = frontier_review
    original_replication = out["PRIVATE_REPLICATION"]

    def private_replication(machine):
        path = original_replication(machine)
        artifact = read_json(path)
        rows = []
        for cid in artifact.get("finalists") or []:
            report = _audit(ctx, cid, "replication")
            ctx.record_score(cid, "genome_realization_replication", report)
            passed = _passes(report)
            rows.append({
                "candidate_id": cid, "passed": passed,
                "evidence_path": report.get("evidence_path")})
            if not passed and cid in ctx.frontier.members:
                ctx.frontier.members[cid][
                    "status"] = "REJECTED_GENOME_REALIZATION_REPLICATION"
                ctx.frontier.members[cid][
                    "reason"] = "genome realization replication failed"
        if not ctx.frontier.non_dominated():
            raise RuntimeError(
                "all finalists failed genome realization replication")
        ctx._save_arena()
        artifact["genome_realization_replication"] = rows
        atomic_write_json(path, artifact)
        return path

    out["PRIVATE_REPLICATION"] = private_replication
    original_systems = crownmod._run_systems

    def run_systems(context, cid, label, events):
        report = original_systems(context, cid, label, events)
        if label == "crown":
            realization = _audit(context, cid, "crown")
            context.record_score(
                cid, "genome_realization_crown", realization)
            report["genome_realization_crown"] = realization
            if not _passes(realization):
                report["status"] = "FAIL"
                report["passed"] = False
                report["genome_realization_failure"] = True
        return report

    crownmod._run_systems = run_systems
    original_synthesis = out["ARCHITECTURE_EVIDENCE_SYNTHESIS"]

    def synthesis(machine):
        path = original_synthesis(machine)
        artifact = read_json(path)
        winner = artifact.get("candidate_id")
        report = ((ctx.scores.get(winner) or {}).get(
            "genome_realization_crown") or {}) if winner else {}
        artifact["genome_realization_crown"] = report
        artifact["genome_realization_crown_passed"] = _passes(report)
        atomic_write_json(path, artifact)
        return path

    out["ARCHITECTURE_EVIDENCE_SYNTHESIS"] = synthesis
    return out
