"""Completion hooks for independently adjudicated controlled-taxonomy claims.

The hardening layer owns the two-adjudicator consensus and fail-closed registry. This final hook makes
that consensus operational at the two earliest architecture boundaries:

* novelty seeds are adjudicated and normalized before the first construction attempt, avoiding a
  needless unresolved round when the claim is unanimously non-distinct;
* initial v0 proposals whose genome was normalized are re-formalized and re-attacked before the
  owner gate, so no formalization can describe a pre-resolution genome.

A genuine extension or adjudicator disagreement remains blocking. Prior CP2 content is never read.
"""
import json
import os

from . import observatory_meta_hardening_overlay as hardening
from . import observatory_novelty_overlay as novelty
from . import observatory_supremacy_overlay as supremacy
from .canonical import atomic_write_json, read_json, sha256_obj
from .handlers import A


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
        forest_path = A(ctx, "architecture", "search_forest.json")
        forest_summary = (read_json(forest_path).get("summary")
                          if os.path.exists(forest_path) else {})
        normalized_ids = []
        changed = False
        for proposal in artifact.get("proposals", []):
            resolution_ids = proposal.get("taxonomy_resolution_ids") or []
            if not resolution_ids:
                normalized_ids.append(
                    novelty.controlled_genome_id(proposal.get("genome") or {}))
                continue
            formal_lid, formal = supremacy._formalize(ctx, proposal)
            destroy_lid, destroy = supremacy._destroy_prebuild(
                ctx, proposal, formal, {
                    **forest_summary,
                    "taxonomy_resolution_ids": resolution_ids,
                    "phase": "post-taxonomy-v0-refomalization",
                })
            proposal["formalization"] = formal
            proposal["formalization_logical_id"] = formal_lid
            proposal["formalization_sha256"] = sha256_obj(formal)
            proposal["prebuild_destroyer"] = destroy
            proposal["prebuild_destroyer_logical_id"] = destroy_lid
            proposal["prebuild_destroyer_sha256"] = sha256_obj(destroy)
            proposal["post_taxonomy_refomalized"] = True
            normalized_ids.append(
                novelty.controlled_genome_id(proposal.get("genome") or {}))
            changed = True
        artifact["controlled_genome_ids"] = normalized_ids
        artifact["taxonomy_normalization_formalization_complete"] = True
        if changed:
            artifact["taxonomy_resolution_registry"] = (
                "architecture/taxonomy-resolutions.json")
        atomic_write_json(path, artifact)
        ctx.esc.register_controlled_genomes(
            normalized_ids, "initial-post-taxonomy-normalization")
        return path

    out["TARGET_ARCHITECTURE_SEARCH"] = target_search
    return out
