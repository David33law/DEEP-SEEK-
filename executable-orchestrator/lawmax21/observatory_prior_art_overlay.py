"""Authoritative public prior-art challenge for the National Legal Observatory.

Independent model search remains blind to this corpus until an executable frontier exists. At every
CEILING_ANALYSIS the overlay opens the owner-signed public manifest, runs three independent critics,
constructs every distinct architecture challenger, carries protocol/evaluator gaps as blockers, and
requires the challengers to enter ordinary frontier measurement before the search can close.

The manifest is a falsification corpus, never a preselected architecture and never evidence of
third-party endorsement. Earlier CP2 remains a separate quarantined source.
"""
import json
import os
from types import MethodType

from . import observatory_crown_overlay as crownmod
from . import observatory_escalation as escalation
from . import observatory_novelty_overlay as novelty
from . import observatory_roles as oroles
from . import observatory_supremacy_overlay as supremacy
from .canonical import atomic_write_json, read_json, sha256_file, sha256_obj
from .handlers import A


CRITICS = (
    ("legal-interoperability",
     "Challenge legal identity, versioning, ELI/ECLI, Akoma Ntoso, LegalRuleML, temporal legal effect and multi-channel official publication."),
    ("provenance-governance",
     "Challenge provenance interchange, graph validation, transparency, split-view resistance, trust succession, delegation, revocation and public verification."),
    ("formal-distributed-systems",
     "Challenge state-machine refinement, crash correctness, concurrency, replication, partitions, recovery, trusted proof boundaries and implementation-level verification."),
)

PRIOR_ART_SUPREMACY_KEYS = (
    "prior_art_all_sources_assessed",
    "prior_art_challengers_measured",
    "prior_art_no_blockers",
)

SOURCE_REVIEW_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["source_id", "disposition", "reasoning", "evidence_refs",
                 "gap_kind", "required_action", "challenger_ids"],
    "properties": {
        "source_id": {"type": "string", "minLength": 3, "maxLength": 160},
        "disposition": {"enum": ["SATISFIED", "PARTIAL", "MISSING", "INAPPLICABLE"]},
        "reasoning": {"type": "string", "minLength": 20, "maxLength": 20000},
        "evidence_refs": {
            "type": "array", "maxItems": 32,
            "items": {"type": "string", "minLength": 3, "maxLength": 4000}},
        "gap_kind": {"enum": ["none", "architecture", "protocol", "evaluator"]},
        "required_action": {"type": "string", "minLength": 5, "maxLength": 16000},
        "challenger_ids": {
            "type": "array", "maxItems": 16,
            "items": {"type": "string", "minLength": 2, "maxLength": 120}},
    },
}

CHALLENGER_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["challenger_id", "source_ids", "attacked_assumption",
                 "falsifiable_gain", "introduced_cost", "proposal"],
    "properties": {
        "challenger_id": {"type": "string", "pattern": "^[A-Za-z0-9_.:-]{2,120}$"},
        "source_ids": {
            "type": "array", "minItems": 1, "maxItems": 24,
            "items": {"type": "string", "minLength": 3, "maxLength": 160}},
        "attacked_assumption": {"type": "string", "minLength": 20, "maxLength": 20000},
        "falsifiable_gain": {"type": "string", "minLength": 20, "maxLength": 20000},
        "introduced_cost": {"type": "string", "minLength": 10, "maxLength": 16000},
        "proposal": oroles.PROPOSAL_SCHEMA,
    },
}

PRIOR_ART_REVIEW_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object", "additionalProperties": False,
    "required": ["critic_id", "source_reviews", "challengers",
                 "protocol_blockers", "unresolved"],
    "properties": {
        "critic_id": {"type": "string", "minLength": 2, "maxLength": 120},
        "source_reviews": {
            "type": "array", "minItems": 1, "maxItems": 128,
            "items": SOURCE_REVIEW_SCHEMA},
        "challengers": {
            "type": "array", "maxItems": 32,
            "items": CHALLENGER_SCHEMA},
        "protocol_blockers": {
            "type": "array", "maxItems": 64,
            "items": {
                "type": "object", "additionalProperties": False,
                "required": ["blocker_id", "source_ids", "kind", "description",
                             "required_revision"],
                "properties": {
                    "blocker_id": {"type": "string", "minLength": 2, "maxLength": 120},
                    "source_ids": {
                        "type": "array", "minItems": 1, "maxItems": 24,
                        "items": {"type": "string", "minLength": 3, "maxLength": 160}},
                    "kind": {"enum": ["protocol", "evaluator"]},
                    "description": {"type": "string", "minLength": 20, "maxLength": 20000},
                    "required_revision": {"type": "string", "minLength": 20, "maxLength": 20000},
                },
            },
        },
        "unresolved": {
            "type": "array", "maxItems": 64,
            "items": {"type": "string", "minLength": 5, "maxLength": 16000}},
    },
}


def _manifest_path(ctx):
    return os.path.join(ctx.profile_pkg, "PUBLIC-PRIOR-ART-MANIFEST.json")


def _contract_path(ctx):
    return os.path.join(ctx.profile_pkg, "PRIOR-ART-CHALLENGE-CONTRACT.md")


def _manifest(ctx):
    path = _manifest_path(ctx)
    obj = read_json(path)
    sources = obj.get("sources") or []
    ids = [x.get("source_id") for x in sources]
    if not sources or any(not x for x in ids) or len(ids) != len(set(ids)):
        raise RuntimeError("public prior-art manifest has missing or duplicate source IDs")
    return obj


def _genome_id(genome):
    return novelty.controlled_genome_id(genome or {})


def _taxonomy_clean(genome):
    if not isinstance(genome, dict):
        return False
    if genome.get("novel_axes"):
        return False
    for axis in oroles.GENOME_FIELDS:
        value = genome.get(axis) or {}
        if not isinstance(value, dict) or value.get("class") == "other":
            return False
    return True


def _validate_review(report, source_ids):
    reviews = report.get("source_reviews") or []
    seen = [x.get("source_id") for x in reviews]
    if set(seen) != set(source_ids) or len(seen) != len(source_ids):
        raise RuntimeError(
            f"prior-art critic {report.get('critic_id')} did not assess every source exactly once")
    challengers = {x.get("challenger_id"): x for x in report.get("challengers") or []}
    if len(challengers) != len(report.get("challengers") or []):
        raise RuntimeError("prior-art critic returned duplicate challenger IDs")
    for challenger in challengers.values():
        if not set(challenger.get("source_ids") or []).issubset(set(source_ids)):
            raise RuntimeError("prior-art challenger cites an unknown source ID")
        proposal = challenger.get("proposal") or {}
        if not _taxonomy_clean(proposal.get("genome") or {}):
            raise RuntimeError(
                "prior-art challenger must use named controlled classes; taxonomy extensions require a signed protocol revision")
    blocker_sources = set()
    for blocker in report.get("protocol_blockers") or []:
        if not set(blocker.get("source_ids") or []).issubset(set(source_ids)):
            raise RuntimeError("prior-art blocker cites an unknown source ID")
        blocker_sources.update(blocker.get("source_ids") or [])
    for review in reviews:
        sid = review["source_id"]
        disposition = review["disposition"]
        gap_kind = review["gap_kind"]
        linked = [x for x in review.get("challenger_ids") or [] if x in challengers]
        if disposition in ("SATISFIED", "INAPPLICABLE"):
            if gap_kind != "none" or linked:
                raise RuntimeError(f"{sid}: closed review cannot declare an open gap or challenger")
            if disposition == "SATISFIED" and not review.get("evidence_refs"):
                raise RuntimeError(f"{sid}: SATISFIED requires persisted evidence references")
        else:
            if gap_kind == "architecture" and not linked:
                raise RuntimeError(f"{sid}: architecture gap has no complete challenger")
            if gap_kind in ("protocol", "evaluator") and sid not in blocker_sources:
                raise RuntimeError(f"{sid}: protocol/evaluator gap has no explicit blocker")
            if gap_kind == "none":
                raise RuntimeError(f"{sid}: PARTIAL/MISSING cannot use gap_kind=none")
    return True


def _install_ledger(ctx):
    esc = ctx.esc
    if getattr(esc, "_prior_art_installed", False):
        return
    sup = esc._sup()
    sup.setdefault("prior_art_waves", [])
    original_conditions = esc._supremacy_conditions
    original_summary = esc.supremacy_summary

    def record_prior_art_wave(self, wave):
        waves = self._sup().setdefault("prior_art_waves", [])
        label = wave.get("label")
        for existing in waves:
            if existing.get("label") == label:
                existing.clear(); existing.update(wave); self._flush(); return existing
        waves.append(wave); self._flush(); return wave

    def conditions(self):
        result = original_conditions()
        waves = self._sup().setdefault("prior_art_waves", [])
        last = waves[-1] if waves else {}
        result.update({
            "prior_art_all_sources_assessed": bool(last.get("all_sources_assessed")),
            "prior_art_challengers_measured": bool(last.get("challengers_measured")),
            "prior_art_no_blockers": bool(last.get("no_blockers")),
        })
        return result

    def summary(self):
        result = original_summary()
        waves = self._sup().setdefault("prior_art_waves", [])
        last = waves[-1] if waves else {}
        result.update({
            "prior_art_all_sources_assessed": bool(last.get("all_sources_assessed")),
            "prior_art_challengers_measured": bool(last.get("challengers_measured")),
            "prior_art_no_blockers": bool(last.get("no_blockers")),
            "prior_art_waves": len(waves),
            "prior_art_sources": int(last.get("source_count", 0)),
            "prior_art_challengers": len(last.get("challengers") or []),
            "prior_art_blockers": len(last.get("blockers") or []),
            "prior_art_manifest_sha256": last.get("manifest_sha256"),
        })
        return result

    esc.record_prior_art_wave = MethodType(record_prior_art_wave, esc)
    esc._supremacy_conditions = MethodType(conditions, esc)
    esc.supremacy_summary = MethodType(summary, esc)
    esc._prior_art_installed = True

    for key in PRIOR_ART_SUPREMACY_KEYS:
        if key not in escalation.SUPREMACY_KEYS:
            escalation.SUPREMACY_KEYS.append(key)
        if key not in escalation.SEARCH_SUPREMACY_KEYS:
            escalation.SEARCH_SUPREMACY_KEYS.append(key)
    schema = escalation.OBSERVATORY_PROOF_SCHEMA
    cond = schema["properties"]["conditions"]
    proof = schema["properties"]["supremacy"]
    for key in PRIOR_ART_SUPREMACY_KEYS:
        if key not in cond["required"]:
            cond["required"].append(key)
        cond["properties"][key] = {"type": "boolean"}
        if key not in proof["required"]:
            proof["required"].append(key)
        proof["properties"][key] = {"type": "boolean"}


def _existing_candidate_for_genome(ctx, gid):
    for cid, candidate in ctx.candidates.items():
        genome = candidate.get("genome") or {}
        if genome and _genome_id(genome) == gid:
            return cid
    return None


def _measured(ctx, cid):
    if not cid:
        return False
    scores = ctx.scores.get(cid) or {}
    semantic = scores.get("hidden_qualification")
    systems = scores.get("systems_qualification")
    return bool(semantic and systems)


def _campaign_path(ctx):
    return A(ctx, "architecture", f"prior-art-round{ctx.round}.json")


def install(ctx, handlers):
    _install_ledger(ctx)
    out = dict(handlers)

    original_ceiling = out["CEILING_ANALYSIS"]

    def ceiling(machine):
        path = original_ceiling(machine)
        if not ctx.frontier.members:
            raise RuntimeError("prior-art challenge opened before an executable frontier existed")
        manifest = _manifest(ctx)
        source_ids = [x["source_id"] for x in manifest["sources"]]
        frontier = crownmod._frontier_design_context(ctx)
        contract = open(_contract_path(ctx), encoding="utf-8").read()
        common = [
            ("owner-signed public prior-art manifest",
             json.dumps(manifest, ensure_ascii=False)),
            ("prior-art challenge contract", contract),
            ("measured independent frontier",
             json.dumps(frontier, ensure_ascii=False)[:180000]),
            ("current Pareto report",
             json.dumps(ctx.frontier.report(), ensure_ascii=False)[:120000]),
        ]
        reports = []
        for tag, directive in CRITICS:
            lid, report, _, _ = ctx.ask(
                f"prior-art-critic-{tag}", f"OBS-PRIOR-ART-{tag}-r{ctx.round}",
                directive + " Assess every source ID exactly once. A SATISFIED conclusion needs "
                "persisted evidence references. PARTIAL/MISSING architectural gaps need complete "
                "controlled-genome challengers; protocol/evaluator gaps need explicit blockers. "
                "Do not infer endorsement and do not use earlier CP2 source content.",
                common, PRIOR_ART_REVIEW_SCHEMA, line="successor", temperature=0.10)
            _validate_review(report, source_ids)
            reports.append({"tag": tag, "logical_id": lid, "report": report})

        challengers = {}
        blockers = []
        unresolved = []
        for row in reports:
            report = row["report"]
            unresolved.extend({"critic": row["tag"], "reason": x}
                              for x in report.get("unresolved") or [])
            blockers.extend({"critic": row["tag"], **x}
                            for x in report.get("protocol_blockers") or [])
            for challenger in report.get("challengers") or []:
                proposal = challenger["proposal"]
                gid = _genome_id(proposal["genome"])
                entry = challengers.setdefault(gid, {
                    "genome_id": gid,
                    "proposal": proposal,
                    "source_ids": set(),
                    "attacked_assumptions": [],
                    "falsifiable_gains": [],
                    "introduced_costs": [],
                    "critic_challenger_ids": [],
                })
                entry["source_ids"].update(challenger["source_ids"])
                entry["attacked_assumptions"].append(challenger["attacked_assumption"])
                entry["falsifiable_gains"].append(challenger["falsifiable_gain"])
                entry["introduced_costs"].append(challenger["introduced_cost"])
                entry["critic_challenger_ids"].append({
                    "critic": row["tag"], "id": challenger["challenger_id"]})

        rows = []
        for gid in sorted(challengers):
            entry = challengers[gid]
            existing = _existing_candidate_for_genome(ctx, gid)
            rows.append({
                **{k: v for k, v in entry.items() if k != "source_ids"},
                "source_ids": sorted(entry["source_ids"]),
                "existing_candidate_id": existing,
                "candidate_id": existing,
                "build_status": "EXISTING" if existing else "PENDING",
                "measured": _measured(ctx, existing),
            })

        campaign = {
            "label": f"prior-art-round-{ctx.round}",
            "round": ctx.round,
            "profile": ctx.profile_id,
            "manifest_sha256": sha256_file(_manifest_path(ctx)),
            "contract_sha256": sha256_file(_contract_path(ctx)),
            "prior_cp2_direct_content_read": False,
            "source_count": len(source_ids),
            "source_ids": source_ids,
            "critics": reports,
            "all_sources_assessed": True,
            "challengers": rows,
            "blockers": blockers,
            "unresolved": unresolved,
            "challengers_measured": bool(all(x["measured"] for x in rows)),
            "no_blockers": not blockers and not unresolved,
        }
        campaign_path = _campaign_path(ctx)
        atomic_write_json(campaign_path, campaign)
        ctx.esc.record_prior_art_wave({
            **campaign,
            "evidence": os.path.relpath(campaign_path, ctx.runtime).replace("\\", "/"),
        })

        ceiling_obj = read_json(path)
        families = [x["proposal"]["family"] for x in rows
                    if x["build_status"] == "PENDING"]
        if families:
            existing = list(ceiling_obj.get("candidate_families_untried") or [])
            ceiling_obj["candidate_families_untried"] = list(dict.fromkeys(existing + families))
            ctx.esc.declare_families(families)
        ceiling_obj["authoritative_prior_art"] = {
            "manifest_sha256": campaign["manifest_sha256"],
            "campaign": os.path.relpath(campaign_path, ctx.runtime).replace("\\", "/"),
            "challenger_genomes": [x["genome_id"] for x in rows],
            "blockers": len(blockers) + len(unresolved),
        }
        atomic_write_json(path, ceiling_obj)
        return path

    out["CEILING_ANALYSIS"] = ceiling

    original_successor = out["SUCCESSOR_SEARCH"]

    def successor(machine):
        path = original_successor(machine)
        campaign_path = _campaign_path(ctx)
        campaign = read_json(campaign_path)
        built = []
        for index, row in enumerate(campaign.get("challengers") or [], 1):
            if row.get("candidate_id"):
                continue
            cid = f"OBS-PRIOR-R{ctx.round:02d}-{index:02d}"
            try:
                crownmod._build_round_candidate(
                    ctx, row["proposal"], cid, "prior-art", "PRIOR-ART")
                row["candidate_id"] = cid
                row["build_status"] = "BUILT"
                built.append(cid)
                ctx.esc.declare_families([row["proposal"]["family"]])
            except Exception as exc:
                row["build_status"] = "FAILED"
                row["build_error"] = str(exc)[:2000]
                campaign["blockers"].append({
                    "kind": "architecture_challenger_build_failure",
                    "genome_id": row["genome_id"],
                    "reason": str(exc)[:2000],
                })
        campaign["built_candidate_ids"] = built
        campaign["challengers_measured"] = bool(all(
            row.get("candidate_id") and _measured(ctx, row.get("candidate_id"))
            for row in campaign.get("challengers") or []))
        campaign["no_blockers"] = not campaign.get("blockers") and not campaign.get("unresolved")
        atomic_write_json(campaign_path, campaign)
        ctx.esc.record_prior_art_wave({
            **campaign,
            "evidence": os.path.relpath(campaign_path, ctx.runtime).replace("\\", "/"),
        })

        artifact = read_json(path)
        artifact["prior_art_challengers"] = built
        artifact["prior_art_campaign"] = os.path.relpath(
            campaign_path, ctx.runtime).replace("\\", "/")
        atomic_write_json(path, artifact)
        return path

    out["SUCCESSOR_SEARCH"] = successor

    original_frontier = out["FRONTIER_REVIEW"]

    def frontier_review(machine):
        path = original_frontier(machine)
        campaign_path = _campaign_path(ctx)
        campaign = read_json(campaign_path)
        for row in campaign.get("challengers") or []:
            cid = row.get("candidate_id")
            row["measured"] = _measured(ctx, cid)
            if cid and cid in ctx.frontier.members:
                row["frontier_status"] = ctx.frontier.members[cid].get("status")
            elif cid:
                row["frontier_status"] = "NOT_ADMITTED"
        campaign["challengers_measured"] = bool(all(
            row.get("measured") for row in campaign.get("challengers") or []))
        campaign["no_blockers"] = not campaign.get("blockers") and not campaign.get("unresolved")
        atomic_write_json(campaign_path, campaign)
        ctx.esc.record_prior_art_wave({
            **campaign,
            "evidence": os.path.relpath(campaign_path, ctx.runtime).replace("\\", "/"),
        })
        artifact = read_json(path)
        artifact["prior_art_challenge_closed"] = bool(
            campaign["all_sources_assessed"]
            and campaign["challengers_measured"]
            and campaign["no_blockers"])
        atomic_write_json(path, artifact)
        return path

    out["FRONTIER_REVIEW"] = frontier_review
    return out
