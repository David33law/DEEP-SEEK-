"""Completion hooks for independently adjudicated controlled-taxonomy claims.

The hardening layer owns the two-adjudicator consensus and fail-closed registry. This final hook makes
that consensus operational at the earliest architecture boundaries:

* novelty seeds are adjudicated and normalized before the first construction attempt;
* normalized initial v0 proposals are re-formalized and re-attacked;
* if independent taxonomy mapping collapses two nominal finalists into one controlled family, fresh
  CP2-direct-blind replacement seeds are generated, expanded, formalized and attacked automatically
  before the owner gate.

A genuine extension or adjudicator disagreement remains blocking. Prior CP2 content is never read.
"""
import json
import os

from . import observatory_meta_hardening_overlay as hardening
from . import observatory_novelty_overlay as novelty
from . import observatory_roles as oroles
from . import observatory_supremacy_overlay as supremacy
from .canonical import atomic_write_json, read_json, sha256_obj
from .handlers import A


REPAIR_ATTEMPTS = 2
REPAIR_SEEDS = 6


def _formalize_and_attack(ctx, proposal, forest_summary, phase):
    formal_lid, formal = supremacy._formalize(ctx, proposal)
    destroy_lid, destroy = supremacy._destroy_prebuild(
        ctx, proposal, formal, {**forest_summary, "phase": phase})
    proposal["formalization"] = formal
    proposal["formalization_logical_id"] = formal_lid
    proposal["formalization_sha256"] = sha256_obj(formal)
    proposal["prebuild_destroyer"] = destroy
    proposal["prebuild_destroyer_logical_id"] = destroy_lid
    proposal["prebuild_destroyer_sha256"] = sha256_obj(destroy)
    return proposal


def _common_context(ctx):
    return [
        ("National Observatory objective charter",
         supremacy._profile_text(ctx, "OBJECTIVE-CHARTER.md", 40000)),
        ("Supremacy research contract",
         supremacy._profile_text(ctx, "SUPREMACY-CONTRACT.md", 40000)),
        ("Novelty/meta-search contract",
         supremacy._profile_text(ctx, "NOVELTY-SEARCH-CONTRACT.md", 50000)),
        ("sealed CP1 repository reconstruction",
         open(supremacy._find_cp1(ctx), encoding="utf-8").read()[:70000]),
    ]


def _distinct_from_all(genome, proposals):
    return all(supremacy.structurally_distinct(
        genome, proposal.get("genome") or {}) for proposal in proposals)


def _repair_collapsed(ctx, accepted, needed, forest_summary):
    common = _common_context(ctx)
    replacements = []
    for ordinal in range(1, needed + 1):
        produced = None
        rejected_results = []
        for attempt in range(1, REPAIR_ATTEMPTS + 1):
            task = (
                f"Produce exactly {REPAIR_SEEDS} mutually incompatible whole-system National Legal "
                "Observatory seeds to replace a finalist collapsed by independent controlled-taxonomy "
                "normalization. Every seed must use only named non-`other` controlled classes, contain "
                "no novel_axes claim, remain directly blind to prior CP2 source content and differ from "
                "every accepted genome supplied below on at least two controlled axes. Expose assumptions, "
                "failure modes, advantages and why_not_higher; reject at least two additional ideas."
            )
            lid, obj, _, _ = ctx.ask(
                "architecture-search-independent",
                f"OBS-TAXONOMY-COLLAPSE-REPAIR-{ordinal}-A{attempt}",
                task,
                common + [("already accepted controlled genomes", json.dumps([
                    {"family": p.get("family"), "genome": p.get("genome")}
                    for p in accepted + replacements
                ], ensure_ascii=False)[:160000])],
                oroles.SEARCH_LINEAGE_SCHEMA, line="successor", temperature=0.30)
            rejected_results.append({"logical_id": lid, "result": obj})
            for index, raw in enumerate(obj.get("candidates", []), 1):
                genome = raw.get("genome") or {}
                if hardening._raw_taxonomy_claims(genome):
                    continue
                if not _distinct_from_all(genome, accepted + replacements):
                    continue
                seed = dict(raw)
                seed["local_seed_id"] = raw.get("seed_id")
                seed["seed_id"] = f"TAX-REPAIR-{ordinal:02d}-{index:02d}"
                seed["lineage_code"] = "TAX-REPAIR"
                seed["lineage_name"] = "post-normalization-structural-repair"
                seed["lineage_mode"] = "taxonomy-collapse-repair"
                seed["genome_sha256"] = sha256_obj(genome)
                produced = (seed, lid)
                break
            if produced:
                break
        if not produced:
            blocker = A(ctx, "architecture", "taxonomy-collapse-repair-blocker.json")
            atomic_write_json(blocker, {
                "status": "BLOCKING_NO_STRUCTURALLY_DISTINCT_REPLACEMENT",
                "ordinal": ordinal,
                "accepted": [p.get("family") for p in accepted + replacements],
                "attempts": rejected_results,
                "prior_cp2_direct_content_read": False,
            })
            raise RuntimeError(
                "taxonomy normalization collapsed the v0 finalist set and independent repair did not "
                "produce a structurally distinct non-taxonomy-challenging replacement")

        seed, search_lid = produced
        proposal = supremacy._expand_seed(ctx, seed, common)
        if hardening._raw_taxonomy_claims(proposal.get("genome") or {}):
            raise RuntimeError("taxonomy collapse repair expansion introduced a new taxonomy claim")
        proposal["taxonomy_collapse_repair"] = True
        proposal["taxonomy_repair_search_logical_id"] = search_lid
        proposal = _formalize_and_attack(
            ctx, proposal, forest_summary,
            f"post-taxonomy-collapse-repair-{ordinal}")
        replacements.append(proposal)
        ctx.esc.declare_families([proposal["family"]])
    return replacements


def install(ctx, handlers):
    out = dict(handlers)

    current_build_selected = novelty._build_selected

    def build_selected(context, selected, common):
        hardening._resolve_taxonomy_claims(
            context,
            [x.get("genome") for x in selected if isinstance(x, dict)],
            f"novelty-prebuild-round-{context.round}")
        return current_build_selected(context, selected, common)

    novelty._build_selected = build_selected

    original_target = out["TARGET_ARCHITECTURE_SEARCH"]

    def target_search(machine):
        path = original_target(machine)
        artifact = read_json(path)
        original_count = len(artifact.get("proposals", []))
        forest_path = A(ctx, "architecture", "search_forest.json")
        forest_summary = (read_json(forest_path).get("summary")
                          if os.path.exists(forest_path) else {})
        normalized = []
        collapsed = []
        changed = False

        for proposal in artifact.get("proposals", []):
            resolution_ids = proposal.get("taxonomy_resolution_ids") or []
            if resolution_ids:
                proposal = _formalize_and_attack(
                    ctx, proposal,
                    {**forest_summary, "taxonomy_resolution_ids": resolution_ids},
                    "post-taxonomy-v0-reformalization")
                proposal["post_taxonomy_reformalized"] = True
                changed = True
            if _distinct_from_all(proposal.get("genome") or {}, normalized):
                normalized.append(proposal)
            else:
                collapsed.append({
                    "family": proposal.get("family"),
                    "genome": proposal.get("genome"),
                    "reason": "controlled taxonomy normalization reduced structural distance below two",
                })

        if len(normalized) < original_count:
            replacements = _repair_collapsed(
                ctx, normalized, original_count - len(normalized), forest_summary)
            normalized.extend(replacements)
            changed = True

        normalized_ids = [
            novelty.controlled_genome_id(p.get("genome") or {}) for p in normalized
        ]
        artifact["proposals"] = normalized
        artifact["controlled_genome_ids"] = normalized_ids
        artifact["taxonomy_normalization_formalization_complete"] = True
        artifact["taxonomy_collapses"] = collapsed
        artifact["taxonomy_collapse_replacements"] = [
            p.get("seed_id") for p in normalized if p.get("taxonomy_collapse_repair")
        ]
        if changed:
            artifact["taxonomy_resolution_registry"] = (
                "architecture/taxonomy-resolutions.json")
        atomic_write_json(path, artifact)
        ctx.esc.register_controlled_genomes(
            normalized_ids, "initial-post-taxonomy-normalization")
        return path

    out["TARGET_ARCHITECTURE_SEARCH"] = target_search
    return out
