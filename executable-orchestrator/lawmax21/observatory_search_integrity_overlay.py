"""Mechanical integrity checks for active novelty miners.

The initial supremacy forest already rejects lineage convergence. Active G91-G96 miners must meet the
same standard: six eloquent variants of one controlled class vector are not six architecture seeds.
This hook repairs a convergent miner once and then fails closed unless at least four pairwise
controlled-genome clusters remain.
"""
import json

from . import observatory_novelty_overlay as novelty
from . import observatory_roles as oroles
from . import observatory_supremacy_overlay as supremacy
from .canonical import sha256_obj


MIN_ACTIVE_CLUSTERS = 4


def _cluster_count(seeds):
    representatives = []
    for seed in seeds:
        genome = seed.get("genome") or {}
        if all(supremacy.structurally_distinct(
                genome, current.get("genome") or {}) for current in representatives):
            representatives.append(seed)
    return len(representatives)


def _normalize(obj, code, name, logical_id, directive):
    candidates = []
    for index, raw in enumerate(obj.get("candidates", []), 1):
        seed = dict(raw)
        seed["local_seed_id"] = raw.get("seed_id")
        seed["seed_id"] = f"{code}-{index:02d}"
        seed["lineage_code"] = code
        seed["lineage_name"] = name
        seed["lineage_mode"] = "active-novelty"
        seed["novelty_method"] = code
        seed["genome_id"] = novelty.controlled_genome_id(seed.get("genome") or {})
        seed["genome_sha256"] = sha256_obj(seed.get("genome") or {})
        candidates.append(seed)
    return {
        "code": code,
        "name": name,
        "logical_id": logical_id,
        "lineage": obj.get("lineage"),
        "directive": directive,
        "seeds": candidates,
        "rejected": obj.get("rejected", []),
        "finalist_ids": obj.get("finalist_ids", []),
        "exhaustion_note": obj.get("exhaustion_note", ""),
        "structural_clusters": _cluster_count(candidates),
    }


def install(ctx, handlers):
    original = novelty._run_miner

    def run_miner(context, code, name, directive, common, catalog, frontier):
        first = original(context, code, name, directive, common, catalog, frontier)
        if _cluster_count(first.get("seeds", [])) >= MIN_ACTIVE_CLUSTERS:
            first["structural_clusters"] = _cluster_count(first["seeds"])
            first["diversity_repair_used"] = False
            return first

        task = (
            f"Repair active novelty lineage {code}/{name}. Produce exactly "
            f"{novelty.NOVELTY_SEEDS_PER_METHOD} seeds containing at least "
            f"{MIN_ACTIVE_CLUSTERS} pairwise structural clusters, where every pair of cluster "
            "representatives differs on two or more controlled genome axes. Do not merely rename the "
            "first result. Preserve direct blindness to prior CP2 source content, expose assumptions, "
            "failure modes and falsifiable advantages, and reject at least two additional ideas. "
            + directive)
        lid, obj, _, _ = context.ask(
            "architecture-search-independent",
            f"OBS-NOVELTY-{code}-r{context.round}-STRUCTURAL-REPAIR",
            task,
            common + [
                ("rejected convergent active-miner result",
                 json.dumps(first, ensure_ascii=False)[:160000]),
                ("attempted controlled-genome catalog",
                 json.dumps(novelty._catalog_context(catalog), ensure_ascii=False)[:160000]),
                ("current measured frontier without prior CP2 source text",
                 json.dumps(frontier, ensure_ascii=False)[:100000]),
            ],
            oroles.SEARCH_LINEAGE_SCHEMA, line="successor", temperature=0.35)
        repaired = _normalize(obj, code, name, lid, directive)
        repaired["diversity_repair_used"] = True
        if repaired["structural_clusters"] < MIN_ACTIVE_CLUSTERS:
            raise RuntimeError(
                f"{code}: active novelty miner produced only "
                f"{repaired['structural_clusters']} controlled-genome clusters after repair")
        return repaired

    novelty._run_miner = run_miner
    return dict(handlers)
