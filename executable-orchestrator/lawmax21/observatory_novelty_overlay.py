"""Active design-space saturation for the National Legal Observatory.

A passive round with no improvement is not a search-space result. This overlay runs six independent,
CP2-direct-blind novelty miners after every completed escalation round, normalizes their ideas to the
controlled architecture genome, carries deferred/unbuildable genomes as explicit backlog, expands and
constructs selected new genomes through the ordinary blueprint/formalization/systems path, and only
then records a dry wave.

The overlay deliberately installs after the crown layer and before the final independent audit. It
keeps the shared state machine unchanged and strengthens the profile-local escalation ledger in place.
"""
import json
import os
import re
from types import MethodType

from . import observatory_roles as oroles
from .canonical import atomic_write_json, read_json, sha256_file, sha256_obj
from .handlers import A
from . import observatory_crown_overlay as crownmod
from . import observatory_supremacy_overlay as supmod


NOVELTY_DRY_WAVES_REQUIRED = 3
NOVELTY_BUILD_LIMIT = 8
NOVELTY_SEEDS_PER_METHOD = 6

NOVELTY_METHODS = [
    ("G91", "assumption-inversion",
     "Invert the measured frontier's shared load-bearing assumptions and search for mission-preserving constructions that remain coherent after the inversion."),
    ("G92", "morphological-gap-search",
     "Search underrepresented combinations of controlled genome classes. Prefer gaps in the morphology over refinements of the current attractor."),
    ("G93", "cross-domain-structural-transfer",
     "Transfer structural ideas from theorem proving, verified compilation, distributed consensus, scientific evidence systems and other relevant domains without copying product conventions."),
    ("G94", "surgical-genome-mutation",
     "Mutate one or a small number of load-bearing controlled axes around measured frontier members. State the exact falsifiable advantage and the cost introduced by the mutation."),
    ("G95", "trusted-boundary-recut",
     "Move responsibilities across the trusted/untrusted boundary. Search for a smaller, replicated or otherwise reconstituted authoritative kernel rather than preserving the current cut."),
    ("G96", "ontology-and-taxonomy-challenge",
     "Search for mission-preserving structures poorly represented by the current controlled taxonomy. Use `other` or `novel_axes` only with an explicit load-bearing distinction from every existing class."),
]
METHOD_CODES = [x[0] for x in NOVELTY_METHODS]


def controlled_genome_payload(genome):
    return {axis: supmod.genome_signature(genome)[i]
            for i, axis in enumerate(oroles.GENOME_FIELDS)}


def controlled_genome_id(genome):
    """Identity is the ordered controlled class vector; explanatory prose cannot create novelty."""
    return sha256_obj({"controlled_classes": controlled_genome_payload(genome)})


def _install_ledger_semantics(ctx):
    esc = ctx.esc
    if getattr(esc, "_active_novelty_installed", False):
        return

    original_supremacy_conditions = esc._supremacy_conditions
    original_supremacy_summary = esc.supremacy_summary

    def register_controlled_genomes(self, genome_ids, source):
        sup = self._sup()
        known = sup.setdefault("controlled_genomes", [])
        ordered = []
        for gid in genome_ids:
            gid = str(gid)
            if gid and gid not in ordered:
                ordered.append(gid)
            if gid and gid not in known:
                known.append(gid)
        refs = sup.setdefault("controlled_genome_sources", [])
        rec = {"source": str(source), "genomes": ordered}
        if rec not in refs:
            refs.append(rec)
        sup.setdefault("novelty_methods_expected", list(METHOD_CODES))
        self._flush()
        return len(known)

    def record_novelty_wave(self, label, methods, discovered_ids, admitted_ids,
                            backlog_ids, unresolved_ids, evidence_ref,
                            prior_cp2_direct_content_read=False):
        sup = self._sup()
        waves = sup.setdefault("novelty_waves", [])
        for existing in waves:
            if existing.get("label") == label:
                return existing

        expected = list(METHOD_CODES)
        completed = []
        for method in methods:
            method = str(method)
            if method not in completed:
                completed.append(method)
        methods_complete = set(completed) == set(expected)

        known = sup.setdefault("controlled_genomes", [])
        before = set(known)
        discovered = []
        for gid in discovered_ids:
            gid = str(gid)
            if gid and gid not in discovered:
                discovered.append(gid)
        new = [gid for gid in discovered if gid not in before]
        for gid in discovered:
            if gid not in known:
                known.append(gid)

        admitted = list(dict.fromkeys(str(x) for x in admitted_ids if x))
        backlog = list(dict.fromkeys(str(x) for x in backlog_ids if x))
        unresolved = list(dict.fromkeys(str(x) for x in unresolved_ids if x))
        dry = bool(methods_complete
                   and not prior_cp2_direct_content_read
                   and not new
                   and not admitted
                   and not backlog
                   and not unresolved)
        wave = {
            "label": str(label),
            "methods_expected": expected,
            "methods_completed": completed,
            "methods_complete": methods_complete,
            "prior_cp2_direct_content_read": bool(prior_cp2_direct_content_read),
            "discovered_genomes": discovered,
            "new_genomes": new,
            "new_count": len(new),
            "admitted_genomes": admitted,
            "backlog_genomes": backlog,
            "unresolved_genomes": unresolved,
            "backlog_count": len(backlog),
            "unresolved_count": len(unresolved),
            "dry": dry,
            "evidence": str(evidence_ref),
        }
        waves.append(wave)
        self._flush()
        return wave

    def genome_dry_waves(self):
        n = 0
        for wave in reversed(self._sup().setdefault("novelty_waves", [])):
            if not wave.get("dry"):
                break
            n += 1
        return n

    def supremacy_conditions(self):
        conditions = original_supremacy_conditions()
        sup = self._sup()
        waves = sup.setdefault("novelty_waves", [])
        controlled = sup.setdefault("controlled_genomes", [])
        complete = bool(waves) and all(w.get("methods_complete") is True for w in waves)
        no_direct_cp2 = bool(waves) and all(
            w.get("prior_cp2_direct_content_read") is False for w in waves)
        last = waves[-1] if waves else {}
        no_open_work = (int(last.get("backlog_count", 0)) == 0
                        and int(last.get("unresolved_count", 0)) == 0)
        conditions["search_forest_executed"] = bool(
            conditions.get("search_forest_executed") and controlled)
        conditions["genome_saturated"] = bool(
            complete and no_direct_cp2 and no_open_work
            and self.genome_dry_waves() >= NOVELTY_DRY_WAVES_REQUIRED)
        return conditions

    def supremacy_summary(self):
        base = original_supremacy_summary()
        sup = self._sup()
        waves = sup.setdefault("novelty_waves", [])
        last = waves[-1] if waves else {}
        base.update({
            "genome_dry_waves": self.genome_dry_waves(),
            "known_genomes": len(sup.setdefault("controlled_genomes", [])),
            "novelty_waves": len(waves),
            "novelty_methods_expected": list(METHOD_CODES),
            "novelty_methods_complete": bool(waves) and all(
                w.get("methods_complete") is True for w in waves),
            "novelty_prior_cp2_direct_blind": bool(waves) and all(
                w.get("prior_cp2_direct_content_read") is False for w in waves),
            "novelty_open_backlog": int(last.get("backlog_count", 0)),
            "novelty_unresolved": int(last.get("unresolved_count", 0)),
            "novelty_contract": "NOVELTY-SEARCH-CONTRACT.md",
        })
        return base

    esc.register_controlled_genomes = MethodType(register_controlled_genomes, esc)
    esc.record_novelty_wave = MethodType(record_novelty_wave, esc)
    esc.genome_dry_waves = MethodType(genome_dry_waves, esc)
    esc._supremacy_conditions = MethodType(supremacy_conditions, esc)
    esc.supremacy_summary = MethodType(supremacy_summary, esc)
    esc._active_novelty_installed = True


def _add_catalog_record(catalog, genome, family, source, seed=None):
    if not isinstance(genome, dict):
        return
    signature = supmod.genome_signature(genome)
    if len(signature) != len(oroles.GENOME_FIELDS) or any(not x for x in signature):
        return
    gid = controlled_genome_id(genome)
    catalog.setdefault(gid, {
        "genome_id": gid,
        "controlled_classes": controlled_genome_payload(genome),
        "genome": genome,
        "family": str(family or "unknown"),
        "source": str(source),
        "seed": seed,
    })


def _wave_paths(ctx):
    root = A(ctx, "architecture", "x")[:-1]
    if not os.path.isdir(root):
        return []
    rows = []
    for name in os.listdir(root):
        m = re.fullmatch(r"novelty-wave-r(\d+)\.json", name)
        if m:
            rows.append((int(m.group(1)), os.path.join(root, name)))
    rows.sort()
    return rows


def _catalog(ctx):
    catalog = {}
    proposals_path = A(ctx, "architecture", "proposals.json")
    if os.path.exists(proposals_path):
        for proposal in read_json(proposals_path).get("proposals", []):
            _add_catalog_record(catalog, proposal.get("genome"), proposal.get("family"),
                                "initial-proposals", proposal)
    for cid, candidate in ctx.candidates.items():
        _add_catalog_record(catalog, candidate.get("genome"), candidate.get("family"),
                            f"candidate:{cid}")
    for _round, path in _wave_paths(ctx):
        artifact = read_json(path)
        for row in artifact.get("candidate_pool", []):
            seed = row.get("seed") if isinstance(row, dict) else None
            if isinstance(seed, dict):
                _add_catalog_record(catalog, seed.get("genome"), seed.get("family"),
                                    os.path.basename(path), seed)
        for seed in artifact.get("deferred_seeds", []):
            if isinstance(seed, dict):
                _add_catalog_record(catalog, seed.get("genome"), seed.get("family"),
                                    os.path.basename(path) + ":backlog", seed)
    return catalog


def _latest_backlog(ctx):
    paths = _wave_paths(ctx)
    if not paths:
        return []
    artifact = read_json(paths[-1][1])
    out = []
    for seed in artifact.get("deferred_seeds", []):
        if isinstance(seed, dict):
            out.append(seed)
    for row in artifact.get("unresolved_seeds", []):
        seed = row.get("seed") if isinstance(row, dict) else None
        if isinstance(seed, dict):
            seed = dict(seed)
            seed["attempts"] = int(seed.get("attempts", 0)) + 1
            out.append(seed)
    dedup = {}
    for seed in out:
        gid = seed.get("genome_id") or controlled_genome_id(seed.get("genome") or {})
        seed["genome_id"] = gid
        dedup.setdefault(gid, seed)
    return list(dedup.values())


def _catalog_context(catalog):
    return [{
        "genome_id": gid,
        "controlled_classes": rec["controlled_classes"],
        "family": rec["family"],
        "source": rec["source"],
    } for gid, rec in sorted(catalog.items())]


def _distance_to_catalog(genome, catalog):
    if not catalog:
        return len(oroles.GENOME_FIELDS)
    return min(supmod.genome_distance(genome, rec["genome"])
               for rec in catalog.values())


def _run_miner(ctx, code, name, directive, common, catalog, frontier):
    task = (
        f"Run architecture-search lineage {code}/{name}. Produce exactly "
        f"{NOVELTY_SEEDS_PER_METHOD} incompatible whole-system seeds. This is an ACTIVE novelty "
        "campaign, not a request to praise or rename the frontier. Use the controlled genome classes "
        "exactly. Search for class vectors absent from the supplied attempted-genome catalog. For each "
        "seed expose assumptions, failure modes, decisive advantages and why_not_higher; reject at "
        "least two additional ideas. You are directly blind to all prior CP2 content and must not ask "
        "for it. " + directive)
    context = common + [
        ("attempted controlled-genome catalog",
         json.dumps(_catalog_context(catalog), ensure_ascii=False)[:160000]),
        ("current measured frontier without prior CP2 source text",
         json.dumps(frontier, ensure_ascii=False)[:100000]),
    ]
    lid, obj, _, _ = ctx.ask(
        "architecture-search-independent", f"OBS-NOVELTY-{code}-r{ctx.round}",
        task, context, oroles.SEARCH_LINEAGE_SCHEMA, line="successor", temperature=0.25)
    if len(obj.get("candidates", [])) < 4:
        raise RuntimeError(f"{code}: novelty miner returned fewer than four seeds")

    rows = []
    for index, raw in enumerate(obj["candidates"], 1):
        seed = dict(raw)
        seed["local_seed_id"] = raw["seed_id"]
        seed["seed_id"] = f"{code}-{index:02d}"
        seed["lineage_code"] = code
        seed["lineage_name"] = name
        seed["lineage_mode"] = "active-novelty"
        seed["novelty_method"] = code
        seed["genome_id"] = controlled_genome_id(seed["genome"])
        seed["nearest_catalog_distance"] = _distance_to_catalog(seed["genome"], catalog)
        rows.append(seed)
    return {
        "code": code,
        "name": name,
        "logical_id": lid,
        "lineage": obj["lineage"],
        "seeds": rows,
        "rejected": obj["rejected"],
        "finalist_ids": obj["finalist_ids"],
        "exhaustion_note": obj["exhaustion_note"],
    }


def _dedupe_pool(seeds):
    by_gid = {}
    for seed in seeds:
        gid = seed.get("genome_id") or controlled_genome_id(seed.get("genome") or {})
        seed = dict(seed)
        seed["genome_id"] = gid
        current = by_gid.get(gid)
        if current is None:
            by_gid[gid] = seed
            continue
        a = int(seed.get("nearest_catalog_distance", 0))
        b = int(current.get("nearest_catalog_distance", 0))
        if a > b or (a == b and str(seed.get("seed_id")) < str(current.get("seed_id"))):
            by_gid[gid] = seed
    return list(by_gid.values())


def _select(seeds, backlog_ids):
    backlog = [x for x in seeds if x.get("genome_id") in backlog_ids]
    fresh = [x for x in seeds if x.get("genome_id") not in backlog_ids]
    backlog.sort(key=lambda x: (int(x.get("attempts", 0)),
                                -int(x.get("nearest_catalog_distance", 0)),
                                str(x.get("seed_id"))))

    selected = backlog[:NOVELTY_BUILD_LIMIT]
    slots = NOVELTY_BUILD_LIMIT - len(selected)
    if slots > 0:
        # First preserve method coverage, then maximize minimum structural distance.
        used = set()
        for code in METHOD_CODES:
            choices = [x for x in fresh if x.get("novelty_method") == code
                       and x.get("genome_id") not in used]
            choices.sort(key=lambda x: (-int(x.get("nearest_catalog_distance", 0)),
                                        str(x.get("seed_id"))))
            if choices and len(selected) < NOVELTY_BUILD_LIMIT:
                selected.append(choices[0])
                used.add(choices[0]["genome_id"])
        remaining = [x for x in fresh if x.get("genome_id") not in used]
        remaining.sort(key=lambda x: (-int(x.get("nearest_catalog_distance", 0)),
                                      str(x.get("seed_id"))))
        for seed in remaining:
            if len(selected) >= NOVELTY_BUILD_LIMIT:
                break
            selected.append(seed)
            used.add(seed["genome_id"])

    selected_ids = {x["genome_id"] for x in selected}
    deferred = [x for x in seeds if x["genome_id"] not in selected_ids]
    return selected, deferred


def _common_context(ctx):
    return [
        ("National Observatory objective charter",
         supmod._profile_text(ctx, "OBJECTIVE-CHARTER.md", 40000)),
        ("Supremacy research contract",
         supmod._profile_text(ctx, "SUPREMACY-CONTRACT.md", 40000)),
        ("Active novelty-search contract",
         supmod._profile_text(ctx, "NOVELTY-SEARCH-CONTRACT.md", 40000)),
        ("sealed CP1 repository reconstruction",
         open(supmod._find_cp1(ctx), encoding="utf-8").read()[:70000]),
    ]


def _build_selected(ctx, selected, common):
    built = []
    unresolved = []
    for index, seed in enumerate(selected, 1):
        cid = f"OBS-NOV-R{ctx.round:02d}-{index:02d}"
        gid = seed["genome_id"]
        try:
            if cid in ctx.candidates:
                existing = controlled_genome_id(ctx.candidates[cid].get("genome") or {})
                if existing != gid:
                    raise RuntimeError(f"{cid}: existing candidate has different controlled genome")
            else:
                proposal = supmod._expand_seed(ctx, seed, common)
                expanded_gid = controlled_genome_id(proposal["genome"])
                if expanded_gid != gid:
                    raise RuntimeError(
                        f"{seed['seed_id']}: expansion changed controlled genome {gid} -> {expanded_gid}")
                crownmod._build_round_candidate(ctx, proposal, cid, "novelty", "NOVELTY")
                ctx.candidates[cid]["controlled_genome_id"] = gid
                ctx.candidates[cid]["novelty_method"] = seed.get("novelty_method")
                ctx.candidates[cid]["novelty_seed_id"] = seed.get("seed_id")
                ctx._save_arena()
                ctx.esc.declare_families([proposal["family"]])
            built.append({"candidate_id": cid, "genome_id": gid,
                          "seed_id": seed.get("seed_id"),
                          "method": seed.get("novelty_method")})
        except Exception as exc:
            retry = dict(seed)
            retry["attempts"] = int(retry.get("attempts", 0)) + 1
            unresolved.append({"genome_id": gid, "seed": retry,
                               "reason": str(exc)[:2000]})
    return built, unresolved


def _execute_wave(ctx, round_no):
    wave_path = A(ctx, "architecture", f"novelty-wave-r{round_no}.json")
    if os.path.exists(wave_path):
        artifact = read_json(wave_path)
        summary = artifact["ledger_wave"]
        ctx.esc.record_novelty_wave(
            summary["label"], summary["methods_completed"],
            summary["discovered_genomes"], summary["admitted_genomes"],
            summary["backlog_genomes"], summary["unresolved_genomes"],
            os.path.relpath(wave_path, ctx.runtime).replace("\\", "/"),
            summary.get("prior_cp2_direct_content_read", False))
        return artifact

    catalog = _catalog(ctx)
    known_before = set(catalog)
    backlog = _latest_backlog(ctx)
    backlog_ids = {x["genome_id"] for x in backlog}
    common = _common_context(ctx)
    frontier = crownmod._frontier_design_context(ctx)

    miners = []
    mined = []
    for code, name, directive in NOVELTY_METHODS:
        result = _run_miner(ctx, code, name, directive, common, catalog, frontier)
        miners.append(result)
        mined.extend(result["seeds"])

    fresh = [seed for seed in mined if seed["genome_id"] not in known_before]
    pool = _dedupe_pool(backlog + fresh)
    selected, deferred = _select(pool, backlog_ids)
    built, unresolved = _build_selected(ctx, selected, common)

    unresolved_ids = {x["genome_id"] for x in unresolved}
    deferred = [x for x in deferred if x["genome_id"] not in unresolved_ids]
    deferred.extend(x["seed"] for x in unresolved)
    deferred = _dedupe_pool(deferred)

    discovered_ids = [x["genome_id"] for x in fresh]
    admitted_ids = [x["genome_id"] for x in built]
    backlog_out = [x["genome_id"] for x in deferred]
    unresolved_out = [x["genome_id"] for x in unresolved]
    evidence_ref = os.path.relpath(wave_path, ctx.runtime).replace("\\", "/")
    ledger_wave = ctx.esc.record_novelty_wave(
        f"active-novelty-round-{round_no}", METHOD_CODES,
        discovered_ids, admitted_ids, backlog_out, unresolved_out,
        evidence_ref, prior_cp2_direct_content_read=False)

    artifact = {
        "contract_sha256": sha256_file(
            os.path.join(ctx.profile_pkg, "NOVELTY-SEARCH-CONTRACT.md")),
        "round": round_no,
        "prior_cp2_direct_content_read": False,
        "methods_expected": METHOD_CODES,
        "methods_completed": METHOD_CODES,
        "catalog_before": _catalog_context(catalog),
        "miners": miners,
        "candidate_pool": [{"genome_id": x["genome_id"],
                            "distance": x.get("nearest_catalog_distance", 0),
                            "method": x.get("novelty_method"), "seed": x}
                           for x in pool],
        "selected_seeds": selected,
        "built": built,
        "unresolved_seeds": unresolved,
        "deferred_seeds": deferred,
        "ledger_wave": ledger_wave,
    }
    atomic_write_json(wave_path, artifact)
    return artifact


def install(ctx, handlers):
    _install_ledger_semantics(ctx)
    out = dict(handlers)

    original_target = out["TARGET_ARCHITECTURE_SEARCH"]

    def target_search(machine):
        p = original_target(machine)
        artifact = read_json(p)
        proposals = artifact.get("proposals", [])
        ids = [controlled_genome_id(x.get("genome") or {}) for x in proposals]
        artifact["controlled_genome_ids"] = ids
        artifact["controlled_genome_identity"] = "ordered controlled class vector"
        atomic_write_json(p, artifact)
        ctx.esc.register_controlled_genomes(ids, "initial-supremacy-search-forest")
        return p

    out["TARGET_ARCHITECTURE_SEARCH"] = target_search

    original_anti = out["ANTI_SATISFICING_AUDIT"]

    def anti_satisficing(machine):
        p = original_anti(machine)
        artifact = read_json(p)
        novelty = _execute_wave(ctx, ctx.round)
        cont, why = ctx.esc.must_continue()
        artifact["active_novelty_wave"] = {
            "round": novelty["round"],
            "methods_completed": novelty["methods_completed"],
            "prior_cp2_direct_content_read": False,
            "new_genomes": novelty["ledger_wave"]["new_genomes"],
            "built": novelty["built"],
            "backlog_count": novelty["ledger_wave"]["backlog_count"],
            "unresolved_count": novelty["ledger_wave"]["unresolved_count"],
            "dry": novelty["ledger_wave"]["dry"],
            "evidence": f"architecture/novelty-wave-r{ctx.round}.json",
        }
        artifact["escalation_required"] = cont
        artifact["escalation_reason"] = why
        atomic_write_json(p, artifact)
        return p

    out["ANTI_SATISFICING_AUDIT"] = anti_satisficing
    return out
