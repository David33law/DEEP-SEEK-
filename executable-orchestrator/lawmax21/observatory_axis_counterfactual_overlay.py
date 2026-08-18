"""Incumbent single-axis counterfactual tournament.

Global search, novelty mining and mechanical class coverage can still miss a locally superior class
substitution around the final incumbent. At every ceiling attempt this overlay freezes the incumbent
controlled genome, independently ranks every alternative class for each tested axis, synthesizes a
strong whole-system counterfactual for the strongest alternatives, constructs it through the complete
semantic/durable/distributed/scale/formal/interoperability/cross-model/genome pipeline, and refuses
closure while any measured counterfactual remains active or any obligation is unmeasured.

Production tests every one of the thirteen axes and the top two independently ranked alternative
classes per axis. Zero-cost proof mode executes the identical path on three representative axes and
one alternative per axis; the owner-signed mission binds the stronger production policy.
"""
from __future__ import annotations

import copy
import json
import os
from types import MethodType

from . import observatory_crown_overlay as crownmod
from . import observatory_escalation as escalation
from . import observatory_prior_art_hardening_overlay as prior_hardening
from . import observatory_protocol
from . import observatory_roles as oroles
from .canonical import atomic_write_json, read_json, sha256_obj
from .handlers import A


PRODUCTION_ALTERNATIVES_PER_AXIS = 2
PROOF_ALTERNATIVES_PER_AXIS = 1
PROOF_AXES = (
    "canonical_authority_seat",
    "consistency_commit_model",
    "scaling_partition_model",
)
SUPREMACY_KEYS = (
    "incumbent_axis_counterfactuals_complete",
    "incumbent_axis_counterfactuals_defeated",
    "incumbent_axis_counterfactuals_current",
)
SEARCH_KEYS = SUPREMACY_KEYS


def _enum_values(schema):
    if not isinstance(schema, dict):
        return []
    if isinstance(schema.get("enum"), list):
        return list(schema["enum"])
    for key in ("allOf", "anyOf", "oneOf"):
        for child in schema.get(key) or []:
            values = _enum_values(child)
            if values:
                return values
    return []


def controlled_classes():
    proposal = oroles.PROPOSAL_SCHEMA
    genome = (proposal.get("properties") or {}).get("genome") or {}
    properties = genome.get("properties") or {}
    result = {}
    for axis in oroles.GENOME_FIELDS:
        axis_schema = properties.get(axis) or {}
        class_schema = (axis_schema.get("properties") or {}).get("class") or {}
        values = [str(value) for value in _enum_values(class_schema)
                  if str(value) != "other"]
        if not values:
            raise RuntimeError(
                "controlled class enumeration missing for axis " + axis)
        result[axis] = list(dict.fromkeys(values))
    return result


def _class_vector(genome):
    result = {}
    for axis in oroles.GENOME_FIELDS:
        value = (genome or {}).get(axis) or {}
        if not isinstance(value, dict) or not value.get("class"):
            raise RuntimeError("counterfactual genome lacks axis " + axis)
        result[axis] = str(value["class"])
    return result


def _target_genome(incumbent_genome, axis, alternative):
    target = copy.deepcopy(incumbent_genome)
    target[axis] = {
        "class": alternative,
        "detail": (
            "Incumbent counterfactual: replace only " + axis
            + " with controlled class " + alternative
            + "; every other controlled class remains frozen."),
    }
    target["novel_axes"] = []
    return target


def _ranking_schema(axis, alternatives):
    n = len(alternatives)
    row = {
        "type": "object", "additionalProperties": False,
        "required": ["class", "rationale", "predicted_gain",
                     "introduced_cost", "falsifier"],
        "properties": {
            "class": {"enum": list(alternatives)},
            "rationale": {"type": "string", "minLength": 20,
                          "maxLength": 20000},
            "predicted_gain": {"type": "string", "minLength": 20,
                               "maxLength": 20000},
            "introduced_cost": {"type": "string", "minLength": 10,
                                "maxLength": 16000},
            "falsifier": {"type": "string", "minLength": 20,
                          "maxLength": 16000},
        },
    }
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object", "additionalProperties": False,
        "required": ["axis", "current_class", "ranking",
                     "uncertainties", "selection_rule"],
        "properties": {
            "axis": {"const": axis},
            "current_class": {"type": "string", "minLength": 1,
                              "maxLength": 160},
            "ranking": {"type": "array", "minItems": n, "maxItems": n,
                        "items": row},
            "uncertainties": {"type": "array", "maxItems": 32,
                "items": {"type": "string", "minLength": 5,
                          "maxLength": 12000}},
            "selection_rule": {"type": "string", "minLength": 20,
                               "maxLength": 16000},
        },
    }


def _validate_ranking(report, axis, current, alternatives):
    if report.get("axis") != axis \
            or report.get("current_class") != current:
        raise RuntimeError("counterfactual ranking names wrong axis/current class")
    ranking = report.get("ranking") or []
    classes = [row.get("class") for row in ranking]
    if len(classes) != len(alternatives) \
            or len(classes) != len(set(classes)) \
            or set(classes) != set(alternatives):
        raise RuntimeError(
            "counterfactual ranking did not rank every alternative exactly once")
    return classes


def _aggregate_rankings(rankings, limit):
    classes = set(rankings[0])
    if any(set(ranking) != classes for ranking in rankings):
        raise RuntimeError("counterfactual ranking universes disagree")
    score = {value: 0 for value in classes}
    best = {value: len(classes) for value in classes}
    for ranking in rankings:
        for index, value in enumerate(ranking):
            score[value] += index
            best[value] = min(best[value], index)
    ordered = sorted(classes, key=lambda value: (
        score[value], best[value], value))
    return ordered[:min(limit, len(ordered))], {
        value: {"rank_sum": score[value], "best_rank": best[value]}
        for value in ordered}


def _validate_proposal(proposal, target):
    if proposal.get("genome", {}).get("novel_axes"):
        raise RuntimeError("counterfactual proposal introduced novel_axes")
    expected = _class_vector(target)
    actual = _class_vector(proposal.get("genome") or {})
    if actual != expected:
        changed = sorted(axis for axis in expected
                         if expected[axis] != actual.get(axis))
        raise RuntimeError(
            "counterfactual architect changed frozen genome axes: "
            + ", ".join(changed))
    return True


def _proposal_context(ctx, incumbent, axis, alternative, target):
    candidate = ctx.candidates[incumbent]
    scores = ctx.scores.get(incumbent) or {}
    return [
        ("INCUMBENT COMPLETE BLUEPRINT",
         json.dumps(candidate.get("blueprint") or {},
                    ensure_ascii=False)[:220000]),
        ("INCUMBENT FORMALIZATION",
         json.dumps(candidate.get("formalization") or {},
                    ensure_ascii=False)[:180000]),
        ("INCUMBENT CONTROLLED GENOME",
         json.dumps(candidate.get("genome") or {}, ensure_ascii=False)),
        ("EXACT COUNTERFACTUAL TARGET GENOME",
         json.dumps(target, ensure_ascii=False)),
        ("MEASURED INCUMBENT REPORT INDEX",
         json.dumps({key: {
             "status": value.get("status") if isinstance(value, dict) else None,
             "passed": value.get("passed") if isinstance(value, dict) else None,
             "evidence_path": value.get("evidence_path") if isinstance(value, dict) else None,
         } for key, value in scores.items()}, ensure_ascii=False)[:120000]),
        ("COUNTERFACTUAL OBLIGATION",
         json.dumps({
             "axis": axis,
             "alternative_class": alternative,
             "all_other_classes_frozen": True,
             "must_be_whole_system": True,
             "must_make_changed_class_load_bearing": True,
         }, ensure_ascii=False)),
    ]


def _strong_proposal(ctx, incumbent, axis, alternative, target):
    context = _proposal_context(
        ctx, incumbent, axis, alternative, target)
    drafts = []
    for tag, temperature, directive in (
            ("A", 0.20,
             "Derive the strongest first-principles realization of the exact single-axis counterfactual."),
            ("B", 0.55,
             "Attack the incumbent assumption and independently engineer the strongest exact counterfactual.")):
        logical_id, proposal, _, _ = ctx.ask(
            f"axis-counterfactual-architect-{tag}",
            f"OBS-AXIS-COUNTERFACTUAL-{ctx.round}-{axis}-{alternative}-{tag}",
            directive + " Preserve every non-target controlled class exactly. The changed class must "
            "alter real authority/state/fault behavior, not labels or comments. Return a complete "
            "whole-system proposal with falsifiable mechanisms and no use of prior CP2 content.",
            context, oroles.PROPOSAL_SCHEMA,
            line="successor", temperature=temperature)
        _validate_proposal(proposal, target)
        drafts.append({"architect": tag, "logical_id": logical_id,
                       "proposal": proposal,
                       "proposal_sha256": sha256_obj(proposal)})
    logical_id, synthesis, _, _ = ctx.ask(
        "axis-counterfactual-synthesizer",
        f"OBS-AXIS-COUNTERFACTUAL-{ctx.round}-{axis}-{alternative}-SYNTHESIS",
        "Synthesize the strongest constructible version of the exact target genome from both "
        "independent drafts. Preserve every class exactly. Retain only mechanisms that make the "
        "changed class load-bearing and measurable; do not average incompatible ideas or weaken the "
        "counterfactual merely to reduce implementation cost.",
        context + [("INDEPENDENT COUNTERFACTUAL DRAFTS",
                    json.dumps(drafts, ensure_ascii=False)[:360000])],
        oroles.PROPOSAL_SCHEMA, line="successor", temperature=0.15)
    _validate_proposal(synthesis, target)
    return {
        "architects": drafts,
        "synthesizer_logical_id": logical_id,
        "proposal": synthesis,
        "proposal_sha256": sha256_obj(synthesis),
    }


def _report_passed(report, statuses):
    if not isinstance(report, dict):
        return False
    if report.get("status") not in statuses:
        return False
    if report.get("passed", True) is not True:
        return False
    return True


def _measured(ctx, candidate_id):
    scores = ctx.scores.get(candidate_id) or {}
    return all(_report_passed(scores.get(key), statuses)
               for key, statuses
               in prior_hardening._REQUIRED_SCORE_REPORTS)


def _campaign_path(ctx):
    return A(ctx, "architecture", f"axis-counterfactual-round{ctx.round}.json")


def _incumbent(ctx):
    incumbent = ctx.esc.s.get("incumbent")
    if incumbent in ctx.candidates:
        return incumbent
    active = ctx.frontier.non_dominated()
    if active:
        return active[0]
    raise RuntimeError("axis counterfactual search has no incumbent")


def _selected_axes():
    if observatory_protocol.proof_mode():
        missing = [axis for axis in PROOF_AXES
                   if axis not in oroles.GENOME_FIELDS]
        if missing:
            raise RuntimeError(
                "proof counterfactual axes absent from genome: "
                + ", ".join(missing))
        return list(PROOF_AXES)
    return list(oroles.GENOME_FIELDS)


def _alternatives_per_axis():
    return (PROOF_ALTERNATIVES_PER_AXIS
            if observatory_protocol.proof_mode()
            else PRODUCTION_ALTERNATIVES_PER_AXIS)


def _last_current_campaign(ctx):
    incumbent = ctx.esc.s.get("incumbent")
    if incumbent not in ctx.candidates:
        return None
    genome_sha = sha256_obj(ctx.candidates[incumbent].get("genome") or {})
    campaigns = ctx.esc._sup().setdefault("axis_counterfactual_campaigns", [])
    for campaign in reversed(campaigns):
        if campaign.get("incumbent_id") == incumbent \
                and campaign.get("incumbent_genome_sha256") == genome_sha:
            return campaign
    return None


def _install_ledger(ctx):
    if getattr(ctx.esc, "_axis_counterfactual_installed", False):
        return
    ctx.esc._sup().setdefault("axis_counterfactual_campaigns", [])
    original_conditions = ctx.esc._supremacy_conditions
    original_summary = ctx.esc.supremacy_summary

    def record(self, campaign):
        campaigns = self._sup().setdefault(
            "axis_counterfactual_campaigns", [])
        identity = campaign.get("campaign_id")
        for existing in campaigns:
            if existing.get("campaign_id") == identity:
                existing.clear(); existing.update(campaign)
                self._flush(); return existing
        campaigns.append(campaign); self._flush(); return campaign

    def conditions(self):
        result = original_conditions()
        campaign = _last_current_campaign(ctx) or {}
        incumbent = self.s.get("incumbent")
        genome_sha = (sha256_obj(
            ctx.candidates[incumbent].get("genome") or {})
            if incumbent in ctx.candidates else None)
        current = bool(campaign
                       and campaign.get("incumbent_id") == incumbent
                       and campaign.get("incumbent_genome_sha256") == genome_sha)
        result.update({
            "incumbent_axis_counterfactuals_complete": bool(
                current and campaign.get("complete") is True),
            "incumbent_axis_counterfactuals_defeated": bool(
                current and campaign.get("defeated") is True),
            "incumbent_axis_counterfactuals_current": current,
        })
        return result

    def summary(self):
        result = original_summary()
        campaign = _last_current_campaign(ctx) or {}
        current_conditions = conditions(self)
        result.update({
            **{key: current_conditions[key] for key in SUPREMACY_KEYS},
            "axis_counterfactual_campaigns": len(
                self._sup().setdefault("axis_counterfactual_campaigns", [])),
            "axis_counterfactual_axes_required": len(_selected_axes()),
            "axis_counterfactual_alternatives_per_axis":
                _alternatives_per_axis(),
            "axis_counterfactual_rows": len(campaign.get("rows") or []),
            "axis_counterfactual_measured": sum(
                1 for row in campaign.get("rows") or []
                if row.get("measured") is True),
            "axis_counterfactual_active": sum(
                1 for row in campaign.get("rows") or []
                if row.get("frontier_status") == "ACTIVE"),
            "axis_counterfactual_blockers": len(
                campaign.get("blockers") or []),
            "axis_counterfactual_proof_mode":
                observatory_protocol.proof_mode(),
        })
        return result

    ctx.esc.record_axis_counterfactual_campaign = MethodType(record, ctx.esc)
    ctx.esc._supremacy_conditions = MethodType(conditions, ctx.esc)
    ctx.esc.supremacy_summary = MethodType(summary, ctx.esc)
    ctx.esc._axis_counterfactual_installed = True

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


def install(ctx, handlers):
    _install_ledger(ctx)
    out = dict(handlers)
    original_ceiling = out["CEILING_ANALYSIS"]

    def ceiling(machine):
        path = original_ceiling(machine)
        incumbent = _incumbent(ctx)
        genome = ctx.candidates[incumbent].get("genome") or {}
        genome_sha = sha256_obj(genome)
        previous = _last_current_campaign(ctx)
        if previous and previous.get("complete") is True \
                and previous.get("defeated") is True:
            artifact = read_json(path)
            artifact["axis_counterfactual_campaign"] = previous.get("evidence")
            artifact["axis_counterfactual_reused"] = True
            atomic_write_json(path, artifact)
            return path

        classes = controlled_classes()
        axes = _selected_axes()
        limit = _alternatives_per_axis()
        rows = []
        selectors = []
        blockers = []
        incumbent_vector = _class_vector(genome)
        frontier_context = crownmod._frontier_design_context(ctx)
        for axis in axes:
            current = incumbent_vector[axis]
            alternatives = [value for value in classes[axis]
                            if value != current]
            if not alternatives:
                blockers.append({"axis": axis,
                                 "reason": "no alternative controlled class"})
                continue
            rankings = []
            selector_rows = []
            schema = _ranking_schema(axis, alternatives)
            for tag, temperature, directive in (
                    ("A", 0.10,
                     "Rank by first-principles expected ability to dominate the incumbent under the full mission."),
                    ("B", 0.45,
                     "Rank adversarially: identify the alternative class the incumbent is least prepared to defeat.")):
                logical_id, report, _, _ = ctx.ask(
                    f"axis-counterfactual-selector-{tag}",
                    f"OBS-AXIS-COUNTERFACTUAL-SELECT-{ctx.round}-{axis}-{tag}",
                    directive + " Rank every supplied alternative exactly once. Do not use prior CP2 "
                    "content, do not reward implementation convenience and do not change any other "
                    "genome axis.",
                    [("INCUMBENT CONTROLLED GENOME",
                      json.dumps(genome, ensure_ascii=False)),
                     ("CONTROLLED ALTERNATIVES",
                      json.dumps({"axis": axis, "current_class": current,
                                  "alternatives": alternatives},
                                 ensure_ascii=False)),
                     ("MEASURED FRONTIER CONTEXT",
                      json.dumps(frontier_context,
                                 ensure_ascii=False)[:220000])],
                    schema, line="successor", temperature=temperature)
                ranking = _validate_ranking(
                    report, axis, current, alternatives)
                rankings.append(ranking)
                selector_rows.append({
                    "selector": tag, "logical_id": logical_id,
                    "report": report,
                    "report_sha256": sha256_obj(report)})
            selected, aggregate = _aggregate_rankings(rankings, limit)
            selectors.append({
                "axis": axis, "current_class": current,
                "alternatives": alternatives,
                "selectors": selector_rows,
                "aggregate": aggregate,
                "selected_classes": selected})
            for alternative in selected:
                target = _target_genome(genome, axis, alternative)
                try:
                    proposal = _strong_proposal(
                        ctx, incumbent, axis, alternative, target)
                    rows.append({
                        "axis": axis,
                        "current_class": current,
                        "alternative_class": alternative,
                        "target_genome": target,
                        "target_genome_sha256": sha256_obj(target),
                        **proposal,
                        "candidate_id": None,
                        "build_status": "PENDING",
                        "measured": False,
                        "frontier_status": "UNBUILT",
                    })
                except Exception as exc:
                    blockers.append({
                        "axis": axis, "alternative_class": alternative,
                        "reason": str(exc)[:3000]})

        campaign = {
            "campaign_id": (
                f"axis-counterfactual-r{ctx.round}-{incumbent}-"
                + genome_sha[:16]),
            "round": ctx.round,
            "profile": ctx.profile_id,
            "incumbent_id": incumbent,
            "incumbent_genome_sha256": genome_sha,
            "incumbent_class_vector": incumbent_vector,
            "prior_cp2_direct_content_read": False,
            "proof_mode": observatory_protocol.proof_mode(),
            "axes_required": axes,
            "alternatives_per_axis": limit,
            "selectors": selectors,
            "rows": rows,
            "blockers": blockers,
            "complete": False,
            "defeated": False,
        }
        campaign_path = _campaign_path(ctx)
        campaign["evidence"] = os.path.relpath(
            campaign_path, ctx.runtime).replace("\\", "/")
        atomic_write_json(campaign_path, campaign)
        ctx.esc.record_axis_counterfactual_campaign(campaign)

        artifact = read_json(path)
        artifact["axis_counterfactual_campaign"] = campaign["evidence"]
        artifact["axis_counterfactual_rows"] = len(rows)
        artifact["axis_counterfactual_blockers"] = len(blockers)
        atomic_write_json(path, artifact)
        return path

    out["CEILING_ANALYSIS"] = ceiling
    original_successor = out["SUCCESSOR_SEARCH"]

    def successor(machine):
        path = original_successor(machine)
        campaign_path = _campaign_path(ctx)
        campaign = read_json(campaign_path)
        built = []
        for index, row in enumerate(campaign.get("rows") or [], 1):
            if row.get("candidate_id"):
                continue
            cid = (
                f"OBS-CF-R{ctx.round:02d}-{index:03d}-"
                + row["target_genome_sha256"][:8])
            try:
                crownmod._build_round_candidate(
                    ctx, row["proposal"], cid,
                    "axis-counterfactual", "AXIS-COUNTERFACTUAL")
                row["candidate_id"] = cid
                row["build_status"] = "BUILT"
                built.append(cid)
                ctx.esc.declare_families([row["proposal"]["family"]])
            except Exception as exc:
                row["build_status"] = "FAILED"
                row["build_error"] = str(exc)[:3000]
                campaign.setdefault("blockers", []).append({
                    "axis": row["axis"],
                    "alternative_class": row["alternative_class"],
                    "candidate_id": cid,
                    "reason": str(exc)[:3000],
                })
        campaign["built_candidate_ids"] = built
        atomic_write_json(campaign_path, campaign)
        ctx.esc.record_axis_counterfactual_campaign(campaign)
        artifact = read_json(path)
        artifact["axis_counterfactual_candidates"] = built
        artifact["axis_counterfactual_campaign"] = campaign["evidence"]
        atomic_write_json(path, artifact)
        return path

    out["SUCCESSOR_SEARCH"] = successor
    original_frontier = out["FRONTIER_REVIEW"]

    def frontier_review(machine):
        path = original_frontier(machine)
        campaign_path = _campaign_path(ctx)
        campaign = read_json(campaign_path)
        active = []
        for row in campaign.get("rows") or []:
            cid = row.get("candidate_id")
            row["measured"] = bool(cid and _measured(ctx, cid))
            member = ctx.frontier.members.get(cid) if cid else None
            row["frontier_status"] = (
                member.get("status") if isinstance(member, dict)
                else "NOT_ADMITTED" if cid else row.get("build_status"))
            if row["frontier_status"] == "ACTIVE":
                active.append(cid)
        rows = campaign.get("rows") or []
        campaign["complete"] = bool(
            rows and not campaign.get("blockers")
            and all(row.get("measured") is True for row in rows))
        campaign["active_counterfactual_ids"] = active
        campaign["defeated"] = bool(
            campaign["complete"] and not active)
        campaign["current_incumbent_after_review"] = ctx.esc.s.get("incumbent")
        atomic_write_json(campaign_path, campaign)
        ctx.esc.record_axis_counterfactual_campaign(campaign)

        artifact = read_json(path)
        artifact["axis_counterfactual_complete"] = campaign["complete"]
        artifact["axis_counterfactual_defeated"] = campaign["defeated"]
        artifact["axis_counterfactual_active"] = active
        atomic_write_json(path, artifact)
        return path

    out["FRONTIER_REVIEW"] = frontier_review
    return out
