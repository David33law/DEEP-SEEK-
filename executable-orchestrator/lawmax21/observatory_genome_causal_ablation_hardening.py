"""Causal source-ablation proof for controlled Observatory genome realization.

Citation existence is necessary but not sufficient: a model can cite a real function, invariant and
passing report even when the definition is behaviorally irrelevant. After the source-bound and
cross-auditor validators, this module tests every finalist during independent replication and the
final incumbent during crown.

For each auditor, controlled axis, required evidence group and cited source artifact it renames the
complete auditor-specific definition set in the exact candidate bytes and reruns the corresponding
hidden or fault evaluator with a fresh deterministic seed. The claimed mechanism is causal only when
the exact mutation destroys at least one hard property. A semantically inert dead-definition control
is run for every artifact first; if that control fails, the ablation environment is invalid and no
causal credit is awarded. Infrastructure refusal, missing output and source-hash drift never count as
successful ablation.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import os
from collections import defaultdict
from types import MethodType

from . import observatory_crown_overlay as crown
from . import observatory_distributed_overlay as distributed
from . import observatory_escalation as escalation
from . import observatory_formal_overlay as formal
from . import observatory_genome_realization_overlay as genome
from . import observatory_interoperability_overlay as interop
from . import observatory_scale_overlay as scale
from .canonical import atomic_write_json, read_json, sha256_file, sha256_obj
from .handlers import A


CAUSAL_LABELS = ("replication", "crown")
REQUIRED_AXIS_COUNT = 13
CAUSAL_SUPREMACY_KEYS = (
    "genome_causal_ablation_replication_passed",
    "genome_causal_ablation_crown_passed",
)
CAUSAL_SEARCH_KEYS = ("genome_causal_ablation_replication_passed",)


def _runtime_path(ctx, relative):
    path = os.path.abspath(os.path.join(
        ctx.runtime, *str(relative).replace("\\", "/").split("/")))
    runtime = os.path.abspath(ctx.runtime)
    if path != runtime and not path.startswith(runtime + os.sep):
        raise RuntimeError(
            "causal-ablation evidence escapes runtime: " + str(relative))
    return path


def _artifact_path(ctx, cid, artifact):
    if artifact == "semantic":
        return A(ctx, "candidate-src", f"{cid}.py")
    if artifact == "systems":
        return crown._systems_path(ctx, cid)
    if artifact == "distributed":
        return distributed._distributed_path(ctx, cid)
    if artifact == "scale":
        return scale._path(ctx, cid)
    if artifact == "formal_A":
        return formal._path(ctx, cid, formal.FORMAL_PERSPECTIVES[0][0])
    if artifact == "formal_B":
        return formal._path(ctx, cid, formal.FORMAL_PERSPECTIVES[1][0])
    if artifact == "interoperability_A":
        return interop._path(ctx, cid, interop.PERSPECTIVES[0][0])
    if artifact == "interoperability_B":
        return interop._path(ctx, cid, interop.PERSPECTIVES[1][0])
    raise RuntimeError(
        "unsupported causal-ablation artifact: " + str(artifact))


def _perspective(artifact):
    if artifact == "formal_A":
        return formal.FORMAL_PERSPECTIVES[0][0]
    if artifact == "formal_B":
        return formal.FORMAL_PERSPECTIVES[1][0]
    if artifact == "interoperability_A":
        return interop.PERSPECTIVES[0][0]
    if artifact == "interoperability_B":
        return interop.PERSPECTIVES[1][0]
    return None


class _DefinitionRenamer(ast.NodeTransformer):
    def __init__(self, names, suffix):
        self.names = set(str(name) for name in names)
        self.suffix = suffix
        self.found = set()

    def _rename(self, node):
        if node.name in self.names:
            original = node.name
            node.name = f"__observatory_ablated_{self.suffix}_{original}"
            self.found.add(original)
        return self.generic_visit(node)

    def visit_FunctionDef(self, node):  # noqa: N802
        return self._rename(node)

    def visit_AsyncFunctionDef(self, node):  # noqa: N802
        return self._rename(node)

    def visit_ClassDef(self, node):  # noqa: N802
        return self._rename(node)


def _mutated_source(source, symbols, identity):
    symbols = sorted(set(str(symbol) for symbol in symbols if symbol))
    if not symbols:
        raise RuntimeError("causal ablation received no source definitions")
    tree = ast.parse(source)
    suffix = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:12]
    renamer = _DefinitionRenamer(symbols, suffix)
    tree = renamer.visit(tree)
    ast.fix_missing_locations(tree)
    missing = sorted(set(symbols) - renamer.found)
    if missing:
        raise RuntimeError(
            "causal ablation could not locate AST definitions: "
            + ", ".join(missing))
    mutated = ast.unparse(tree) + "\n"
    compile(mutated, "<genome-causal-ablation>", "exec")
    return mutated


def _control_source(source, identity):
    marker = "__observatory_inert_control_" + hashlib.sha256(
        identity.encode("utf-8")).hexdigest()[:16]
    augmented = (
        source.rstrip() + "\n\n"
        + f"def {marker}():\n"
        + f"    return {identity!r}\n")
    return _mutated_source(
        augmented, [marker], identity + "|negative-control")


def _tasks(report):
    tasks = {}
    obligations = set()
    auditors = report.get("auditors") or []
    if len(auditors) != 2:
        raise RuntimeError(
            "causal ablation requires exactly two validated genome auditors")
    auditor_ids = []
    for auditor in auditors:
        auditor_id = str(
            auditor.get("auditor_id") or auditor.get("auditor") or "")
        if not auditor_id or auditor_id in auditor_ids:
            raise RuntimeError(
                "causal ablation requires two distinct auditor identities")
        auditor_ids.append(auditor_id)
        raw = auditor.get("report") or {}
        by_axis = {
            row.get("axis"): row
            for row in raw.get("axis_reviews") or []}
        if set(by_axis) != set(genome.oroles.GENOME_FIELDS):
            raise RuntimeError(
                "causal ablation received an incomplete auditor axis map")
        for axis in genome.oroles.GENOME_FIELDS:
            row = by_axis[axis]
            required_groups = tuple(genome.REQUIRED_GROUPS[axis])
            seen_groups = set()
            for citation in row.get("source_symbols") or []:
                artifact = str(citation.get("artifact") or "")
                symbol = str(citation.get("symbol") or "")
                group = genome._artifact_group(artifact)
                if group not in required_groups or not symbol:
                    continue
                key = (auditor_id, axis, group, artifact)
                task = tasks.setdefault(key, {
                    "auditor_id": auditor_id,
                    "axis": axis,
                    "group": group,
                    "artifact": artifact,
                    "symbols": set(),
                })
                task["symbols"].add(symbol)
                seen_groups.add(group)
            missing = sorted(set(required_groups) - seen_groups)
            if missing:
                raise RuntimeError(
                    f"causal ablation {auditor_id}/{axis} lacks cited groups: "
                    + ", ".join(missing))
            for group in required_groups:
                obligations.add((auditor_id, axis, group))

    ordered = []
    for key in sorted(tasks):
        row = tasks[key]
        ordered.append({
            "auditor_id": row["auditor_id"],
            "axis": row["axis"],
            "group": row["group"],
            "artifact": row["artifact"],
            "symbols": sorted(row["symbols"]),
        })
    expected = {
        (auditor_id, axis, group)
        for auditor_id in auditor_ids
        for axis in genome.oroles.GENOME_FIELDS
        for group in genome.REQUIRED_GROUPS[axis]
    }
    if obligations != expected:
        missing = sorted(expected - obligations)
        raise RuntimeError(
            "causal ablation obligation map is incomplete: " + repr(missing))
    return ordered, expected, tuple(auditor_ids)


def _semantic_passes(ctx, report):
    if report.get("status") != "OK":
        raise RuntimeError(
            "semantic ablation evaluator was invalidated/refused: "
            + str(report.get("reason", report.get("status"))))
    scores = report.get("dimension_scores") or {}
    dimensions = read_json(ctx.profile.pareto_path(ctx.root))
    checked = []
    violated = []
    for dimension in dimensions:
        key = dimension.get("id")
        minimum = dimension.get("hard_minimum")
        if minimum is None or key not in scores:
            continue
        value = float(scores[key])
        bound = float(minimum)
        direction = dimension.get("direction")
        checked.append({
            "dimension": key,
            "direction": direction,
            "value": value,
            "hard_minimum": bound,
        })
        if direction == "higher" and value + 1e-12 < bound:
            violated.append(key)
        elif direction == "lower" and value - 1e-12 > bound:
            violated.append(key)
    if not checked:
        raise RuntimeError(
            "semantic ablation report exposed no hard comparable dimensions")
    return not violated, {
        "checked_hard_dimensions": checked,
        "violated_hard_dimensions": violated,
    }


def _specialized_passes(report):
    if not report.get("evidence_path"):
        raise RuntimeError(
            "specialized ablation evaluator produced no persisted evidence path")
    status = report.get("status")
    if status not in ("PASS", "OK", "FAIL"):
        raise RuntimeError(
            "specialized ablation evaluator was invalidated/refused: "
            + str(report.get("reason", status)))
    passed = (
        status in ("PASS", "OK")
        and report.get("passed", True) is not False)
    return passed, {
        "status": status,
        "passed_field": report.get("passed"),
        "evaluator_returncode": report.get("evaluator_returncode"),
        "reason": report.get("reason"),
    }


def _evaluate_source(ctx, cid, label, artifact, source, identity, kind):
    temp_id = "OBS-ABL-" + hashlib.sha256(
        f"{kind}|{identity}".encode("utf-8")).hexdigest()[:24]
    run_label = (
        "genome-" + kind + "-" + label + "-"
        + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:12])
    if temp_id in ctx.candidates:
        raise RuntimeError(
            "causal-ablation temporary candidate collision: " + temp_id)
    temp_path = _artifact_path(ctx, temp_id, artifact)
    with open(temp_path, "w", encoding="utf-8") as handle:
        handle.write(source)
    source_sha = sha256_file(temp_path)
    candidate = copy.deepcopy(ctx.candidates[cid])
    if artifact == "semantic":
        candidate["source"] = source
    ctx.candidates[temp_id] = candidate
    ctx.scores[temp_id] = {}
    try:
        if artifact == "semantic":
            evaluation = ctx.measure_hidden(temp_id, "qualification")
            observed_pass, diagnostics = _semantic_passes(ctx, evaluation)
        elif artifact == "systems":
            evaluation = crown._run_systems(
                ctx, temp_id, run_label, crown.SYSTEMS_QUAL_EVENTS)
            observed_pass, diagnostics = _specialized_passes(evaluation)
        elif artifact == "distributed":
            evaluation = distributed._run(
                ctx, temp_id, run_label,
                distributed.DISTRIBUTED_QUAL_EVENTS)
            observed_pass, diagnostics = _specialized_passes(evaluation)
        elif artifact == "scale":
            evaluation = scale._run(
                ctx, temp_id, run_label, scale.SCALE_QUAL_EVENTS,
                candidate_path=temp_path)
            observed_pass, diagnostics = _specialized_passes(evaluation)
        elif artifact in ("formal_A", "formal_B"):
            evaluation = formal._run(
                ctx, temp_id, _perspective(artifact), run_label,
                formal.FORMAL_QUAL_DEPTH, candidate_path=temp_path)
            observed_pass, diagnostics = _specialized_passes(evaluation)
        elif artifact in ("interoperability_A", "interoperability_B"):
            evaluation = interop._run(
                ctx, temp_id, _perspective(artifact), run_label,
                interop.QUAL_CASES, candidate_path=temp_path)
            observed_pass, diagnostics = _specialized_passes(evaluation)
        else:
            raise RuntimeError(
                "unsupported causal-ablation artifact: " + artifact)
    finally:
        ctx.candidates.pop(temp_id, None)
        ctx.scores.pop(temp_id, None)

    evidence_relative = evaluation.get("evidence_path")
    if not evidence_relative:
        raise RuntimeError(
            "causal ablation has no persisted evaluator receipt")
    evidence_path = _runtime_path(ctx, evidence_relative)
    if not os.path.isfile(evidence_path):
        raise RuntimeError(
            "causal-ablation evaluator receipt disappeared")
    if evaluation.get("candidate_sha256") != source_sha:
        raise RuntimeError(
            f"causal ablation {artifact}: evaluator receipt is not bound "
            "to the exact mutated source bytes")
    return {
        "temporary_candidate_id": temp_id,
        "source_path": os.path.relpath(
            temp_path, ctx.runtime).replace("\\", "/"),
        "source_sha256": source_sha,
        "evaluator_receipt_path": evidence_relative,
        "evaluator_receipt_sha256": sha256_file(evidence_path),
        "observed_candidate_pass": bool(observed_pass),
        "diagnostics": diagnostics,
    }


def _run_control(ctx, cid, label, artifact):
    identity = sha256_obj({
        "candidate_id": cid,
        "label": label,
        "artifact": artifact,
        "kind": "inert-negative-control",
    })
    original_path = _artifact_path(ctx, cid, artifact)
    if not os.path.isfile(original_path):
        raise RuntimeError(
            "causal-ablation control source disappeared: " + original_path)
    source = open(original_path, encoding="utf-8").read()
    controlled = _control_source(source, identity)
    evaluated = _evaluate_source(
        ctx, cid, label, artifact, controlled, identity, "control")
    if not evaluated["observed_candidate_pass"]:
        raise RuntimeError(
            f"causal-ablation negative control failed for {cid}/{label}/{artifact}; "
            "source rewriting or evaluator routing is not a valid causal environment")
    return {
        "control_id": identity,
        "artifact": artifact,
        "inert_definition_renamed": True,
        "control_passed": True,
        **evaluated,
    }


def _run_task(ctx, cid, label, task):
    identity = sha256_obj({
        "candidate_id": cid,
        "label": label,
        "auditor_id": task["auditor_id"],
        "axis": task["axis"],
        "group": task["group"],
        "artifact": task["artifact"],
        "symbols": task["symbols"],
    })
    artifact = task["artifact"]
    original_path = _artifact_path(ctx, cid, artifact)
    if not os.path.isfile(original_path):
        raise RuntimeError(
            "causal-ablation source disappeared: " + original_path)
    source = open(original_path, encoding="utf-8").read()
    mutated = _mutated_source(source, task["symbols"], identity)
    evaluated = _evaluate_source(
        ctx, cid, label, artifact, mutated, identity, "ablation")
    return {
        "task_id": identity,
        "auditor_id": task["auditor_id"],
        "axis": task["axis"],
        "group": task["group"],
        "artifact": artifact,
        "renamed_definitions": task["symbols"],
        "causal_failure_observed": not evaluated["observed_candidate_pass"],
        **evaluated,
    }


def _campaign(ctx, cid, label, genome_report):
    tasks, obligations, auditor_ids = _tasks(genome_report)
    artifacts = sorted({task["artifact"] for task in tasks})
    controls = [
        _run_control(ctx, cid, label, artifact)
        for artifact in artifacts]
    results = [
        _run_task(ctx, cid, label, task)
        for task in tasks]

    by_obligation = defaultdict(list)
    for result in results:
        by_obligation[(
            result["auditor_id"],
            result["axis"],
            result["group"])].append(result)
    verified_obligations = sorted(
        [list(key) for key in obligations
         if by_obligation.get(key)
         and all(row["causal_failure_observed"]
                 for row in by_obligation[key])])
    verified_axes = sorted(
        axis for axis in genome.oroles.GENOME_FIELDS
        if all(
            [auditor_id, axis, group] in verified_obligations
            for auditor_id in auditor_ids
            for group in genome.REQUIRED_GROUPS[axis]))
    passed = (
        len(verified_axes) == REQUIRED_AXIS_COUNT
        and len(verified_obligations) == len(obligations)
        and all(row["causal_failure_observed"] for row in results)
        and all(row["control_passed"] for row in controls))

    path = A(
        ctx, "architecture",
        f"genome-causal-ablation-{label}-{cid}.json")
    relative = os.path.relpath(
        path, ctx.runtime).replace("\\", "/")
    artifact = {
        "status": "PASS" if passed else "FAIL",
        "passed": passed,
        "candidate_id": cid,
        "label": label,
        "auditor_ids": list(auditor_ids),
        "required_axis_count": REQUIRED_AXIS_COUNT,
        "verified_axis_count": len(verified_axes),
        "verified_axes": verified_axes,
        "required_auditor_axis_group_obligations": len(obligations),
        "verified_auditor_axis_group_obligations":
            len(verified_obligations),
        "tasks_executed": len(results),
        "negative_controls_executed": len(controls),
        "negative_controls_passed": all(
            row["control_passed"] for row in controls),
        "all_mutations_source_bound": all(
            bool(row.get("source_sha256"))
            and bool(row.get("evaluator_receipt_sha256"))
            for row in results + controls),
        "all_ablation_mutations_destroyed_claimed_behavior": all(
            row["causal_failure_observed"] for row in results),
        "controls": controls,
        "tasks": results,
        "evidence_path": relative,
        "proof_boundary": (
            "Auditor-specific definition-set renaming under the signed qualification evaluators "
            "proves causal dependence only for the exact cited source bytes, hidden corpora, fault "
            "workloads and controlled auditor/axis/group obligations. Passing inert controls prove "
            "that AST round-tripping and source mutation alone do not cause failure. This is not an "
            "unbounded theorem about all future deployments or semantically equivalent rewrites."),
    }
    atomic_write_json(path, artifact)
    artifact["evidence_sha256"] = sha256_file(path)
    return artifact


def install(ctx, handlers):
    if getattr(genome, "_causal_ablation_hardening_installed", False):
        return dict(handlers)
    original_audit = genome._audit
    original_passes = genome._passes
    original_conditions = ctx.esc._supremacy_conditions
    original_summary = ctx.esc.supremacy_summary

    def audit(context, candidate_id, label):
        report = original_audit(context, candidate_id, label)
        if label in CAUSAL_LABELS:
            causal = _campaign(context, candidate_id, label, report)
            report["causal_ablation_required"] = True
            report["causal_ablation_passed"] = causal["passed"]
            report["causal_ablation_evidence"] = {
                "path": causal["evidence_path"],
                "sha256": causal["evidence_sha256"],
                "tasks_executed": causal["tasks_executed"],
                "negative_controls_executed":
                    causal["negative_controls_executed"],
                "negative_controls_passed":
                    causal["negative_controls_passed"],
                "verified_axis_count": causal["verified_axis_count"],
                "verified_auditor_axis_group_obligations":
                    causal["verified_auditor_axis_group_obligations"],
            }
            if not causal["passed"]:
                report["status"] = "FAIL"
                report["passed"] = False
                report["all_axes_realized"] = False
                report["verified_axis_count"] = causal[
                    "verified_axis_count"]
            path = A(
                context, "architecture",
                f"genome-realization-{label}-{candidate_id}.json")
            atomic_write_json(path, report)
        else:
            report["causal_ablation_required"] = False
        return report

    def passes(report):
        if not original_passes(report):
            return False
        if report.get("label") in CAUSAL_LABELS:
            evidence = report.get("causal_ablation_evidence") or {}
            return (
                report.get("causal_ablation_passed") is True
                and int(evidence.get("verified_axis_count", 0))
                == REQUIRED_AXIS_COUNT
                and int(evidence.get("tasks_executed", 0)) > 0
                and int(evidence.get(
                    "negative_controls_executed", 0)) > 0
                and evidence.get("negative_controls_passed") is True)
        return True

    def conditions(self):
        result = original_conditions()
        incumbent = self.s.get("incumbent")
        scores = (ctx.scores.get(incumbent) or {}) if incumbent else {}
        replication = scores.get(
            "genome_realization_replication") or {}
        crown_report = scores.get("genome_realization_crown") or {}
        result.update({
            "genome_causal_ablation_replication_passed": bool(
                replication.get("causal_ablation_passed") is True),
            "genome_causal_ablation_crown_passed": bool(
                crown_report.get("causal_ablation_passed") is True),
        })
        return result

    def summary(self):
        result = original_summary()
        result.update(conditions(self))
        incumbent = self.s.get("incumbent")
        scores = (ctx.scores.get(incumbent) or {}) if incumbent else {}
        replication = scores.get(
            "genome_realization_replication") or {}
        crown_report = scores.get("genome_realization_crown") or {}
        result.update({
            "genome_causal_ablation_required_labels":
                list(CAUSAL_LABELS),
            "genome_causal_ablation_replication_tasks": int((
                replication.get("causal_ablation_evidence") or {}).get(
                    "tasks_executed", 0)),
            "genome_causal_ablation_crown_tasks": int((
                crown_report.get("causal_ablation_evidence") or {}).get(
                    "tasks_executed", 0)),
            "genome_causal_ablation_replication_controls": int((
                replication.get("causal_ablation_evidence") or {}).get(
                    "negative_controls_executed", 0)),
            "genome_causal_ablation_crown_controls": int((
                crown_report.get("causal_ablation_evidence") or {}).get(
                    "negative_controls_executed", 0)),
        })
        return result

    genome._audit = audit
    genome._passes = passes
    ctx.esc._supremacy_conditions = MethodType(conditions, ctx.esc)
    ctx.esc.supremacy_summary = MethodType(summary, ctx.esc)
    for key in CAUSAL_SUPREMACY_KEYS:
        if key not in escalation.SUPREMACY_KEYS:
            escalation.SUPREMACY_KEYS.append(key)
    for key in CAUSAL_SEARCH_KEYS:
        if key not in escalation.SEARCH_SUPREMACY_KEYS:
            escalation.SEARCH_SUPREMACY_KEYS.append(key)
    schema = escalation.OBSERVATORY_PROOF_SCHEMA
    conditions_schema = schema["properties"]["conditions"]
    supremacy_schema = schema["properties"]["supremacy"]
    for key in CAUSAL_SUPREMACY_KEYS:
        if key not in conditions_schema["required"]:
            conditions_schema["required"].append(key)
        conditions_schema["properties"][key] = {"type": "boolean"}
        if key not in supremacy_schema["required"]:
            supremacy_schema["required"].append(key)
        supremacy_schema["properties"][key] = {"type": "boolean"}
    genome._causal_ablation_hardening_installed = True
    return dict(handlers)
