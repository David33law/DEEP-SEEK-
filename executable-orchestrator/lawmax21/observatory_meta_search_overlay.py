"""Mechanical coverage, meta-search and closure audit for Observatory novelty waves.

The active novelty layer proves that six fixed CP2-direct-blind miners ran. This layer closes the
remaining gap between "miners ran" and "the attainable search space was actively challenged":

* every non-``other`` controlled genome class must appear in validated search evidence;
* six critical axis pairs must achieve breadth in both directions;
* two independent critics inspect the search protocol itself;
* every new dynamic directive is executed as another CP2-direct-blind miner;
* protocol/evaluator/taxonomy changes that cannot be exercised inside the signed run remain explicit
  blockers rather than being converted into a dry wave;
* two independent closure auditors inspect the complete mechanical record;
* the novelty ledger is rewritten fail-closed, so three dry waves mean all of the above completed.

This module installs after ``observatory_novelty_overlay`` and before the independent audit. It does
not create another state machine and never reads prior CP2 source material.
"""
import json
import os
from types import MethodType

from . import observatory_roles as oroles
from .canonical import atomic_write_json, read_json, sha256_file, sha256_obj
from .handlers import A
from . import observatory_crown_overlay as crownmod
from . import observatory_novelty_overlay as novelty
from . import observatory_supremacy_overlay as supmod


META_CRITICS = ("A", "B")
CLOSURE_AUDITORS = ("A", "B")
PAIR_BREADTH_REQUIRED = 3
TARGETS_PER_MINER = 6

CRITICAL_PAIRS = (
    ("canonical_authority_seat", "state_derivation_model"),
    ("canonical_authority_seat", "consistency_commit_model"),
    ("consistency_commit_model", "replication_distribution_model"),
    ("trusted_core_topology", "provenance_proof_model"),
    ("temporal_model", "normative_effect_model"),
    ("publication_topology", "governance_evolution_model"),
)

META_SEARCH_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object", "additionalProperties": False,
    "required": ["critic_id", "protocol_strengths", "blind_spots",
                 "attainable_improvements", "dynamic_directives",
                 "taxonomy_observations", "supports_current_protocol"],
    "properties": {
        "critic_id": {"type": "string", "minLength": 1, "maxLength": 80},
        "protocol_strengths": {
            "type": "array", "minItems": 3, "maxItems": 40,
            "items": {"type": "string", "minLength": 10, "maxLength": 12000}},
        "blind_spots": {
            "type": "array", "maxItems": 40,
            "items": {"type": "string", "minLength": 10, "maxLength": 12000}},
        "attainable_improvements": {
            "type": "array", "maxItems": 32,
            "items": {
                "type": "object", "additionalProperties": False,
                "required": ["improvement_id", "kind", "description", "evidence",
                             "required_action", "blocking"],
                "properties": {
                    "improvement_id": {"type": "string", "minLength": 2, "maxLength": 120},
                    "kind": {"enum": ["dynamic_search", "protocol_code_change",
                                       "evaluator_extension", "taxonomy_extension"]},
                    "description": {"type": "string", "minLength": 15, "maxLength": 16000},
                    "evidence": {"type": "string", "minLength": 10, "maxLength": 16000},
                    "required_action": {"type": "string", "minLength": 10, "maxLength": 16000},
                    "blocking": {"type": "boolean"},
                },
            },
        },
        "dynamic_directives": {
            "type": "array", "maxItems": 24,
            "items": {
                "type": "object", "additionalProperties": False,
                "required": ["directive_id", "objective", "rationale",
                             "required_classes", "falsifiable_gain"],
                "properties": {
                    "directive_id": {"type": "string", "minLength": 2, "maxLength": 120},
                    "objective": {"type": "string", "minLength": 15, "maxLength": 16000},
                    "rationale": {"type": "string", "minLength": 15, "maxLength": 16000},
                    "required_classes": {
                        "type": "array", "maxItems": 13,
                        "items": {
                            "type": "object", "additionalProperties": False,
                            "required": ["axis", "class"],
                            "properties": {
                                "axis": {"enum": oroles.GENOME_FIELDS},
                                "class": {"type": "string", "minLength": 2, "maxLength": 120},
                            },
                        },
                    },
                    "falsifiable_gain": {"type": "string", "minLength": 15, "maxLength": 16000},
                },
            },
        },
        "taxonomy_observations": {
            "type": "array", "maxItems": 32,
            "items": {"type": "string", "minLength": 10, "maxLength": 12000}},
        "supports_current_protocol": {"type": "boolean"},
    },
}

CLOSURE_AUDIT_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object", "additionalProperties": False,
    "required": ["auditor_id", "supports_dry_wave", "verified_facts",
                 "blockers", "reason"],
    "properties": {
        "auditor_id": {"type": "string", "minLength": 1, "maxLength": 80},
        "supports_dry_wave": {"type": "boolean"},
        "verified_facts": {
            "type": "object", "additionalProperties": False,
            "required": ["fixed_miners_complete", "meta_critics_complete",
                         "mechanical_coverage_complete", "backlog_empty",
                         "unresolved_empty", "taxonomy_clear",
                         "prior_cp2_direct_blind", "no_new_genome"],
            "properties": {
                "fixed_miners_complete": {"type": "boolean"},
                "meta_critics_complete": {"type": "boolean"},
                "mechanical_coverage_complete": {"type": "boolean"},
                "backlog_empty": {"type": "boolean"},
                "unresolved_empty": {"type": "boolean"},
                "taxonomy_clear": {"type": "boolean"},
                "prior_cp2_direct_blind": {"type": "boolean"},
                "no_new_genome": {"type": "boolean"},
            },
        },
        "blockers": {
            "type": "array", "maxItems": 64,
            "items": {"type": "string", "minLength": 5, "maxLength": 16000}},
        "reason": {"type": "string", "minLength": 20, "maxLength": 20000},
    },
}


def _class(genome, axis):
    value = (genome or {}).get(axis) or {}
    return str(value.get("class") or "") if isinstance(value, dict) else ""


def _valid_genome(genome):
    return isinstance(genome, dict) and all(_class(genome, axis) for axis in oroles.GENOME_FIELDS)


def _taxonomy_claims(genome):
    claims = []
    if not isinstance(genome, dict):
        return ["malformed-genome"]
    for axis in oroles.GENOME_FIELDS:
        if _class(genome, axis) == "other":
            claims.append(f"other:{axis}")
    for item in genome.get("novel_axes") or []:
        if isinstance(item, dict):
            claims.append("novel-axis:" + sha256_obj(item))
        else:
            claims.append("malformed-novel-axis")
    return sorted(set(claims))


def _genomes_from_artifact(path):
    if not os.path.exists(path):
        return []
    obj = read_json(path)
    out = []
    for line in obj.get("lineages", []):
        for seed in line.get("candidates", []):
            if _valid_genome(seed.get("genome")):
                out.append(seed["genome"])
    for proposal in obj.get("proposals", []):
        if _valid_genome(proposal.get("genome")):
            out.append(proposal["genome"])
    for miner in obj.get("miners", []):
        for seed in miner.get("seeds", []):
            if _valid_genome(seed.get("genome")):
                out.append(seed["genome"])
    meta = obj.get("meta_search") or {}
    for miner in meta.get("dynamic_miners", []):
        for seed in miner.get("seeds", []):
            if _valid_genome(seed.get("genome")):
                out.append(seed["genome"])
    return out


def _all_search_genomes(ctx, extra=None):
    out = []
    out.extend(_genomes_from_artifact(A(ctx, "architecture", "search_forest.json")))
    out.extend(_genomes_from_artifact(A(ctx, "architecture", "proposals.json")))
    root = A(ctx, "architecture", "x")[:-1]
    if os.path.isdir(root):
        for name in sorted(os.listdir(root)):
            if name.startswith("novelty-wave-r") and name.endswith(".json"):
                out.extend(_genomes_from_artifact(os.path.join(root, name)))
    for candidate in ctx.candidates.values():
        if _valid_genome(candidate.get("genome")):
            out.append(candidate["genome"])
    for genome in extra or []:
        if _valid_genome(genome):
            out.append(genome)
    return out


def _coverage(genomes):
    clean = [g for g in genomes if _valid_genome(g)]
    axis_seen = {axis: set() for axis in oroles.GENOME_FIELDS}
    for genome in clean:
        for axis in oroles.GENOME_FIELDS:
            cls = _class(genome, axis)
            if cls:
                axis_seen[axis].add(cls)

    axis_missing = {}
    for axis in oroles.GENOME_FIELDS:
        required = {x for x in oroles.GENOME_CLASSES[axis] if x != "other"}
        missing = sorted(required - axis_seen[axis])
        if missing:
            axis_missing[axis] = missing

    pair_gaps = []
    pair_evidence = []
    for left, right in CRITICAL_PAIRS:
        left_classes = [x for x in oroles.GENOME_CLASSES[left] if x != "other"]
        right_classes = [x for x in oroles.GENOME_CLASSES[right] if x != "other"]
        for axis, classes, other_axis, other_classes in (
                (left, left_classes, right, right_classes),
                (right, right_classes, left, left_classes)):
            for cls in classes:
                counterparts = sorted({
                    _class(g, other_axis) for g in clean
                    if _class(g, axis) == cls and _class(g, other_axis) != "other"
                })
                pair_evidence.append({
                    "axis": axis, "class": cls, "counterpart_axis": other_axis,
                    "counterparts": counterparts, "count": len(counterparts),
                })
                if len(counterparts) < PAIR_BREADTH_REQUIRED:
                    available = [x for x in other_classes if x not in counterparts]
                    pair_gaps.append({
                        "axis": axis, "class": cls, "counterpart_axis": other_axis,
                        "counterparts_seen": counterparts,
                        "required": PAIR_BREADTH_REQUIRED,
                        "needed": PAIR_BREADTH_REQUIRED - len(counterparts),
                        "available_counterparts": available,
                    })

    taxonomy = []
    for genome in clean:
        for claim in _taxonomy_claims(genome):
            taxonomy.append({
                "claim": claim,
                "genome_id": novelty.controlled_genome_id(genome),
            })
    dedup_taxonomy = {sha256_obj(x): x for x in taxonomy}
    return {
        "valid_genomes": len(clean),
        "axis_seen": {k: sorted(v) for k, v in axis_seen.items()},
        "axis_missing": axis_missing,
        "critical_pair_breadth_required": PAIR_BREADTH_REQUIRED,
        "pair_evidence": pair_evidence,
        "pair_gaps": pair_gaps,
        "taxonomy_claims": [dedup_taxonomy[k] for k in sorted(dedup_taxonomy)],
        "complete": not axis_missing and not pair_gaps and not dedup_taxonomy,
    }


def _coverage_obligations(report):
    obligations = []
    for axis, classes in sorted((report.get("axis_missing") or {}).items()):
        for cls in classes:
            obligations.append({"kind": "axis_class", "axis": axis, "class": cls})
    for gap in report.get("pair_gaps") or []:
        choices = list(gap.get("available_counterparts") or [])
        for cls in choices[:int(gap.get("needed", 0))]:
            obligations.append({
                "kind": "pair",
                "axis": gap["axis"],
                "class": gap["class"],
                "counterpart_axis": gap["counterpart_axis"],
                "counterpart_class": cls,
            })
    return obligations


def _obligation_satisfied(seed, obligation):
    genome = seed.get("genome") or {}
    required = obligation.get("required_classes")
    if isinstance(required, list):
        return all(_class(genome, x.get("axis")) == x.get("class") for x in required)
    if obligation.get("kind") == "axis_class":
        return _class(genome, obligation["axis"]) == obligation["class"]
    if obligation.get("kind") == "pair":
        return (_class(genome, obligation["axis"]) == obligation["class"]
                and _class(genome, obligation["counterpart_axis"])
                == obligation["counterpart_class"])
    return True


def _normalise_seeds(obj, code, method):
    rows = []
    for index, raw in enumerate(obj.get("candidates", []), 1):
        seed = dict(raw)
        seed["local_seed_id"] = raw.get("seed_id")
        seed["seed_id"] = f"{code}-{index:02d}"
        seed["lineage_code"] = code
        seed["lineage_name"] = method
        seed["lineage_mode"] = "meta-targeted"
        seed["novelty_method"] = code
        seed["genome_id"] = novelty.controlled_genome_id(seed.get("genome") or {})
        rows.append(seed)
    return rows


def _run_targeted_miner(ctx, code, method, obligations, common, catalog, frontier):
    task = (
        f"Run architecture-search lineage {code}/{method}. Produce exactly six incompatible "
        "whole-system Observatory seeds. The JSON obligations below are mechanically binding: every "
        "obligation must be satisfied by at least one returned seed. Use only controlled genome class "
        "values, remain directly blind to prior CP2 source content, expose assumptions/failure modes, "
        "and reject at least two additional ideas. Do not rename an attempted genome."
    )
    context = common + [
        ("targeted obligations", json.dumps(obligations, ensure_ascii=False)),
        ("attempted controlled-genome catalog",
         json.dumps(novelty._catalog_context(catalog), ensure_ascii=False)[:180000]),
        ("current measured frontier without prior CP2 source text",
         json.dumps(frontier, ensure_ascii=False)[:100000]),
    ]
    ticket = f"OBS-META-MINER-{code}-r{ctx.round}"
    lid, obj, _, _ = ctx.ask(
        "architecture-search-independent", ticket, task, context,
        oroles.SEARCH_LINEAGE_SCHEMA, line="successor", temperature=0.30)
    seeds = _normalise_seeds(obj, code, method)
    unmet = [x for x in obligations if not any(_obligation_satisfied(s, x) for s in seeds)]
    if unmet:
        lid, obj, _, _ = ctx.ask(
            "architecture-search-independent", ticket + "-REPAIR",
            task + " The first result failed the mechanical obligation check. Replace seeds until "
            "every listed obligation is literally present in the controlled class vector.",
            context + [("rejected first result", json.dumps(obj, ensure_ascii=False)[:140000]),
                       ("unmet obligations", json.dumps(unmet, ensure_ascii=False))],
            oroles.SEARCH_LINEAGE_SCHEMA, line="successor", temperature=0.35)
        seeds = _normalise_seeds(obj, code, method)
        unmet = [x for x in obligations if not any(_obligation_satisfied(s, x) for s in seeds)]
    return {
        "code": code, "method": method, "logical_id": lid,
        "obligations": obligations, "seeds": seeds,
        "rejected": obj.get("rejected", []),
        "exhaustion_note": obj.get("exhaustion_note", ""),
        "unmet_obligations": unmet,
    }


def _protocol_context(ctx):
    paths = [
        "run_observatory.py",
        "executable-orchestrator/lawmax21/observatory_supremacy_overlay.py",
        "executable-orchestrator/lawmax21/observatory_crown_overlay.py",
        "executable-orchestrator/lawmax21/observatory_novelty_overlay.py",
        "executable-orchestrator/lawmax21/observatory_meta_search_overlay.py",
        "executable-orchestrator/lawmax21/observatory_escalation.py",
        "private-evaluator/evaluator/observatory_systems_arena.py",
    ]
    manifest = []
    excerpts = []
    for rel in paths:
        path = os.path.join(ctx.root, *rel.split("/"))
        if not os.path.isfile(path):
            manifest.append({"path": rel, "missing": True})
            continue
        manifest.append({"path": rel, "sha256": sha256_file(path)})
        excerpts.append((rel, open(path, encoding="utf-8").read()[:24000]))
    return manifest, excerpts


def _run_meta_critic(ctx, tag, wave, coverage, catalog, frontier):
    manifest, excerpts = _protocol_context(ctx)
    context = [
        ("active novelty and meta-search contract",
         supmod._profile_text(ctx, "NOVELTY-SEARCH-CONTRACT.md", 50000)),
        ("current novelty wave", json.dumps(wave, ensure_ascii=False)[:120000]),
        ("mechanical coverage report", json.dumps(coverage, ensure_ascii=False)[:120000]),
        ("attempted controlled-genome catalog",
         json.dumps(novelty._catalog_context(catalog), ensure_ascii=False)[:180000]),
        ("measured frontier without prior CP2 source text",
         json.dumps(frontier, ensure_ascii=False)[:100000]),
        ("research protocol manifest", json.dumps(manifest, ensure_ascii=False)),
    ] + [("protocol source: " + rel, text) for rel, text in excerpts]
    lid, obj, _, _ = ctx.ask(
        f"novelty-meta-search-critic-{tag}", f"OBS-META-CRITIC-{tag}-r{ctx.round}",
        "Audit the architecture-search process itself. Find only feasible, evidence-backed blind "
        "spots or protocol improvements. A search-only improvement must also appear as an executable "
        "dynamic_directive. Code/evaluator/taxonomy changes cannot be silently applied inside this "
        "owner-signed run and must be marked blocking. Do not use elapsed time, money or agreement as "
        "closure evidence. You are directly blind to prior CP2 source content.",
        context, META_SEARCH_SCHEMA, line="successor", temperature=0.15)
    return {"tag": tag, "logical_id": lid, "report": obj}


def _directive_key(directive):
    return sha256_obj({
        "objective": directive.get("objective"),
        "required_classes": directive.get("required_classes") or [],
        "falsifiable_gain": directive.get("falsifiable_gain"),
    })


def _dynamic_directives(critics, ctx):
    sup = ctx.esc._sup()
    history = sup.setdefault("meta_directive_history", [])
    seen = {x.get("directive_key") for x in history if isinstance(x, dict)}
    fresh = []
    blockers = []
    for critic in critics:
        report = critic["report"]
        improvements = report.get("attainable_improvements") or []
        directives = list(report.get("dynamic_directives") or [])
        for improvement in improvements:
            if not improvement.get("blocking"):
                continue
            if improvement.get("kind") == "dynamic_search":
                if not directives:
                    blockers.append({"kind": "missing-dynamic-directive",
                                     "critic": critic["tag"], "improvement": improvement})
            else:
                blockers.append({"kind": improvement.get("kind"),
                                 "critic": critic["tag"], "improvement": improvement})
        if report.get("supports_current_protocol") is not True and not improvements:
            blockers.append({"kind": "unsupported-protocol-without-action",
                             "critic": critic["tag"]})
        for directive in directives:
            key = _directive_key(directive)
            if key not in seen:
                row = dict(directive)
                row["directive_key"] = key
                row["critic"] = critic["tag"]
                fresh.append(row)
                seen.add(key)
    return fresh, blockers, history


def _dedupe_fresh(seeds, known):
    out = {}
    for seed in seeds:
        genome = seed.get("genome") or {}
        if not _valid_genome(genome):
            continue
        gid = seed.get("genome_id") or novelty.controlled_genome_id(genome)
        seed = dict(seed)
        seed["genome_id"] = gid
        if gid in known:
            continue
        out.setdefault(gid, seed)
    return [out[k] for k in sorted(out)]


def _build_dynamic(ctx, seeds, common):
    built = []
    unresolved = []
    for index, seed in enumerate(seeds, 1):
        cid = f"OBS-META-R{ctx.round:02d}-{index:03d}"
        gid = seed["genome_id"]
        claims = _taxonomy_claims(seed.get("genome") or {})
        if claims:
            unresolved.append({"genome_id": gid, "seed": seed,
                               "reason": "unresolved taxonomy claim: " + ", ".join(claims)})
            continue
        try:
            if cid in ctx.candidates:
                existing = novelty.controlled_genome_id(ctx.candidates[cid].get("genome") or {})
                if existing != gid:
                    raise RuntimeError(f"{cid}: existing candidate has a different controlled genome")
            else:
                proposal = supmod._expand_seed(ctx, seed, common)
                expanded = novelty.controlled_genome_id(proposal.get("genome") or {})
                if expanded != gid:
                    raise RuntimeError(f"{seed.get('seed_id')}: expansion changed controlled genome")
                crownmod._build_round_candidate(ctx, proposal, cid, "meta-novelty", "META-NOVELTY")
                ctx.candidates[cid]["controlled_genome_id"] = gid
                ctx.candidates[cid]["meta_directive"] = seed.get("meta_directive")
                ctx.candidates[cid]["novelty_seed_id"] = seed.get("seed_id")
                ctx._save_arena()
                ctx.esc.declare_families([proposal["family"]])
            built.append({"candidate_id": cid, "genome_id": gid,
                          "seed_id": seed.get("seed_id"),
                          "method": seed.get("novelty_method")})
        except Exception as exc:
            unresolved.append({"genome_id": gid, "seed": seed,
                               "reason": str(exc)[:2000]})
    return built, unresolved


def _run_closure_auditor(ctx, tag, facts, evidence):
    lid, obj, _, _ = ctx.ask(
        f"novelty-closure-auditor-{tag}", f"OBS-CLOSURE-AUDITOR-{tag}-r{ctx.round}",
        "Independently decide whether this novelty wave is entitled to count as dry. Verify every "
        "mechanical fact against the supplied evidence. Any missing miner, critic, coverage class, "
        "pair-breadth obligation, backlog, unresolved build/taxonomy issue, new genome, protocol "
        "improvement or CP2-direct leak requires supports_dry_wave=false.",
        [("mechanical closure facts", json.dumps(facts, ensure_ascii=False)),
         ("complete meta-search evidence", json.dumps(evidence, ensure_ascii=False)[:220000]),
         ("active novelty and meta-search contract",
          supmod._profile_text(ctx, "NOVELTY-SEARCH-CONTRACT.md", 50000))],
        CLOSURE_AUDIT_SCHEMA, line="successor", temperature=0.0)
    return {"tag": tag, "logical_id": lid, "report": obj}


def _ledger_wave(ctx, label):
    waves = ctx.esc._sup().setdefault("novelty_waves", [])
    matches = [w for w in waves if w.get("label") == label]
    if len(matches) != 1:
        raise RuntimeError(f"expected one novelty ledger wave {label!r}, found {len(matches)}")
    return matches[0]


def _restore_meta_ledger(ctx, artifact):
    label = artifact["ledger_wave"]["label"]
    wave = _ledger_wave(ctx, label)
    wave.clear()
    wave.update(artifact["ledger_wave"])
    ctx.esc._flush()


def _execute_meta_wave(ctx, round_no):
    meta_path = A(ctx, "architecture", f"meta-search-wave-r{round_no}.json")
    if os.path.exists(meta_path):
        artifact = read_json(meta_path)
        _restore_meta_ledger(ctx, artifact)
        return artifact

    wave_path = A(ctx, "architecture", f"novelty-wave-r{round_no}.json")
    if not os.path.exists(wave_path):
        raise RuntimeError(f"active novelty artifact missing before meta-search: {wave_path}")
    wave_artifact = read_json(wave_path)
    ledger = dict(wave_artifact.get("ledger_wave") or {})
    label = ledger.get("label")
    if not label:
        raise RuntimeError("novelty wave has no ledger label")

    common = novelty._common_context(ctx)
    catalog = novelty._catalog(ctx)
    known_before = set(catalog)
    frontier = crownmod._frontier_design_context(ctx)
    coverage_before = _coverage(_all_search_genomes(ctx))

    critics = [_run_meta_critic(ctx, tag, wave_artifact, coverage_before,
                                catalog, frontier) for tag in META_CRITICS]
    critic_directives, protocol_blockers, history = _dynamic_directives(critics, ctx)

    coverage_targets = _coverage_obligations(coverage_before)
    target_batches = [coverage_targets[i:i + TARGETS_PER_MINER]
                      for i in range(0, len(coverage_targets), TARGETS_PER_MINER)]
    dynamic_miners = []
    dynamic_seeds = []
    unmet = []
    for index, obligations in enumerate(target_batches, 1):
        result = _run_targeted_miner(
            ctx, f"C{index:02d}", "mechanical-coverage-repair",
            obligations, common, catalog, frontier)
        dynamic_miners.append(result)
        dynamic_seeds.extend(result["seeds"])
        unmet.extend(result["unmet_obligations"])

    for index, directive in enumerate(critic_directives, 1):
        obligation = {
            "kind": "meta_directive",
            "directive_id": directive.get("directive_id"),
            "required_classes": directive.get("required_classes") or [],
            "objective": directive.get("objective"),
            "falsifiable_gain": directive.get("falsifiable_gain"),
        }
        result = _run_targeted_miner(
            ctx, f"M{index:02d}", "meta-search-directive",
            [obligation], common, catalog, frontier)
        for seed in result["seeds"]:
            seed["meta_directive"] = directive["directive_key"]
        dynamic_miners.append(result)
        dynamic_seeds.extend(result["seeds"])
        unmet.extend(result["unmet_obligations"])
        history.append({
            "directive_key": directive["directive_key"],
            "directive_id": directive.get("directive_id"),
            "round": round_no,
            "evidence": f"architecture/meta-search-wave-r{round_no}.json",
        })

    fresh = _dedupe_fresh(dynamic_seeds, known_before)
    built, build_unresolved = _build_dynamic(ctx, fresh, common)
    dynamic_ids = [x["genome_id"] for x in fresh]
    if dynamic_ids:
        ctx.esc.register_controlled_genomes(dynamic_ids, f"meta-search-round-{round_no}")

    coverage_after = _coverage(_all_search_genomes(
        ctx, [seed.get("genome") for seed in dynamic_seeds]))
    taxonomy_unresolved = list(coverage_after.get("taxonomy_claims") or [])

    existing_backlog = list(ledger.get("backlog_genomes") or [])
    existing_unresolved = list(ledger.get("unresolved_genomes") or [])
    unresolved_rows = list(build_unresolved)
    unresolved_rows.extend({"reason": "unmet mechanical coverage obligation", "obligation": x}
                           for x in unmet)
    unresolved_rows.extend({"reason": "protocol/meta-search blocker", "blocker": x}
                           for x in protocol_blockers)
    unresolved_rows.extend({"reason": "taxonomy extension unresolved", "claim": x}
                           for x in taxonomy_unresolved)
    unresolved_rows.extend({"reason": "mechanical coverage gap remains", "gap": x}
                           for x in _coverage_obligations(coverage_after))

    dynamic_new = [gid for gid in dynamic_ids if gid not in known_before]
    admitted = list(ledger.get("admitted_genomes") or []) + [x["genome_id"] for x in built]
    discovered = list(ledger.get("discovered_genomes") or []) + dynamic_ids
    new_genomes = list(ledger.get("new_genomes") or []) + dynamic_new
    backlog = existing_backlog
    unresolved_ids = existing_unresolved + [
        "META:" + sha256_obj(x) for x in unresolved_rows
    ]

    fixed_complete = bool(ledger.get("methods_complete"))
    meta_complete = len(critics) == len(META_CRITICS)
    mechanical_facts = {
        "fixed_miners_complete": fixed_complete,
        "meta_critics_complete": meta_complete,
        "mechanical_coverage_complete": bool(coverage_after.get("complete")),
        "backlog_empty": len(backlog) == 0,
        "unresolved_empty": len(unresolved_ids) == 0,
        "taxonomy_clear": not taxonomy_unresolved,
        "prior_cp2_direct_blind": ledger.get("prior_cp2_direct_content_read") is False,
        "no_new_genome": len(new_genomes) == 0 and len(admitted) == 0,
    }
    closure_evidence = {
        "critics": critics,
        "dynamic_miners": dynamic_miners,
        "coverage_before": coverage_before,
        "coverage_after": coverage_after,
        "protocol_blockers": protocol_blockers,
        "unresolved": unresolved_rows,
        "existing_wave": ledger,
    }
    auditors = [_run_closure_auditor(ctx, tag, mechanical_facts, closure_evidence)
                for tag in CLOSURE_AUDITORS]
    closure_complete = len(auditors) == len(CLOSURE_AUDITORS)
    closure_support = closure_complete and all(
        x["report"].get("supports_dry_wave") is True
        and not x["report"].get("blockers") for x in auditors)

    dry = bool(all(mechanical_facts.values()) and closure_support)
    enhanced = dict(ledger)
    enhanced.update({
        "methods_completed": list(ledger.get("methods_completed") or [])
                             + [f"META-{x}" for x in META_CRITICS]
                             + [f"CLOSURE-{x}" for x in CLOSURE_AUDITORS],
        "methods_complete": bool(fixed_complete and meta_complete and closure_complete),
        "meta_critics_complete": meta_complete,
        "closure_auditors_complete": closure_complete,
        "closure_auditors_support_dry": closure_support,
        "mechanical_coverage_complete": bool(coverage_after.get("complete")),
        "protocol_improvements_open": len(protocol_blockers),
        "taxonomy_unresolved_count": len(taxonomy_unresolved),
        "discovered_genomes": sorted(set(discovered)),
        "new_genomes": sorted(set(new_genomes)),
        "new_count": len(set(new_genomes)),
        "admitted_genomes": sorted(set(admitted)),
        "backlog_genomes": sorted(set(backlog)),
        "unresolved_genomes": sorted(set(unresolved_ids)),
        "backlog_count": len(set(backlog)),
        "unresolved_count": len(set(unresolved_ids)),
        "dry": dry,
    })

    ledger_wave = _ledger_wave(ctx, label)
    ledger_wave.clear()
    ledger_wave.update(enhanced)
    ctx.esc._flush()

    meta = {
        "contract_sha256": sha256_file(
            os.path.join(ctx.profile_pkg, "NOVELTY-SEARCH-CONTRACT.md")),
        "round": round_no,
        "prior_cp2_direct_content_read": False,
        "meta_critics": critics,
        "dynamic_directives": critic_directives,
        "dynamic_miners": dynamic_miners,
        "dynamic_fresh_seeds": fresh,
        "dynamic_built": built,
        "dynamic_unresolved": build_unresolved,
        "coverage_before": coverage_before,
        "coverage_after": coverage_after,
        "protocol_blockers": protocol_blockers,
        "taxonomy_unresolved": taxonomy_unresolved,
        "closure_auditors": auditors,
        "mechanical_facts": mechanical_facts,
        "ledger_wave": enhanced,
    }
    atomic_write_json(meta_path, meta)
    wave_artifact["ledger_wave"] = enhanced
    wave_artifact["meta_search"] = {
        "artifact": os.path.relpath(meta_path, ctx.runtime).replace("\\", "/"),
        "critics": len(critics),
        "dynamic_miners": len(dynamic_miners),
        "closure_auditors": len(auditors),
        "coverage_complete": coverage_after.get("complete") is True,
        "protocol_blockers": len(protocol_blockers),
        "taxonomy_unresolved": len(taxonomy_unresolved),
        "dry": dry,
    }
    atomic_write_json(wave_path, wave_artifact)
    return meta


def _install_summary(ctx):
    esc = ctx.esc
    if getattr(esc, "_meta_summary_installed", False):
        return
    original = esc.supremacy_summary

    def summary(self):
        base = original()
        waves = self._sup().setdefault("novelty_waves", [])
        last = waves[-1] if waves else {}
        base.update({
            "meta_search_critics_complete": bool(waves) and all(
                x.get("meta_critics_complete") is True for x in waves),
            "closure_auditors_complete": bool(waves) and all(
                x.get("closure_auditors_complete") is True for x in waves),
            "closure_auditors_support_final_dry": bool(last.get(
                "closure_auditors_support_dry", False)),
            "mechanical_coverage_complete": bool(last.get(
                "mechanical_coverage_complete", False)),
            "protocol_improvements_open": int(last.get(
                "protocol_improvements_open", 0)),
            "taxonomy_unresolved_count": int(last.get(
                "taxonomy_unresolved_count", 0)),
            "meta_search_contract": "NOVELTY-SEARCH-CONTRACT.md",
        })
        return base

    esc.supremacy_summary = MethodType(summary, esc)
    esc._meta_summary_installed = True


def install(ctx, handlers):
    """Install fail-closed meta-search around the complete active novelty handler path."""
    _install_summary(ctx)
    out = dict(handlers)

    original_target = out["TARGET_ARCHITECTURE_SEARCH"]

    def target_search(machine):
        path = original_target(machine)
        artifact = read_json(path)
        claims = []
        for proposal in artifact.get("proposals", []):
            for claim in _taxonomy_claims(proposal.get("genome") or {}):
                claims.append({"seed_id": proposal.get("seed_id"),
                               "family": proposal.get("family"), "claim": claim})
        artifact["initial_taxonomy_claims"] = claims
        atomic_write_json(path, artifact)
        if claims:
            backlog = A(ctx, "architecture", "initial-taxonomy-backlog.json")
            atomic_write_json(backlog, {
                "status": "BLOCKING_OWNER_SIGNED_TAXONOMY_REVISION",
                "claims": claims,
                "note": "other/novel axes cannot enter the frontier without explicit resolution",
            })
        return path

    out["TARGET_ARCHITECTURE_SEARCH"] = target_search

    original_v0 = out["TARGET_ARCHITECTURE_v0_REVIEWED"]

    def v0_reviewed(machine):
        backlog = A(ctx, "architecture", "initial-taxonomy-backlog.json")
        if os.path.exists(backlog) and read_json(backlog).get("claims"):
            raise RuntimeError(
                "GATE-ARCH-V0 refused: unresolved controlled-taxonomy extensions remain")
        return original_v0(machine)

    out["TARGET_ARCHITECTURE_v0_REVIEWED"] = v0_reviewed

    original_anti = out["ANTI_SATISFICING_AUDIT"]

    def anti_satisficing(machine):
        path = original_anti(machine)
        artifact = read_json(path)
        meta = _execute_meta_wave(ctx, ctx.round)
        artifact["meta_search_wave"] = {
            "round": meta["round"],
            "critics": len(meta["meta_critics"]),
            "dynamic_miners": len(meta["dynamic_miners"]),
            "closure_auditors": len(meta["closure_auditors"]),
            "coverage_complete": meta["coverage_after"].get("complete") is True,
            "protocol_blockers": len(meta["protocol_blockers"]),
            "taxonomy_unresolved": len(meta["taxonomy_unresolved"]),
            "dry": meta["ledger_wave"].get("dry") is True,
            "evidence": f"architecture/meta-search-wave-r{ctx.round}.json",
        }
        cont, why = ctx.esc.must_continue()
        artifact["escalation_required"] = cont
        artifact["escalation_reason"] = why
        atomic_write_json(path, artifact)
        return path

    out["ANTI_SATISFICING_AUDIT"] = anti_satisficing
    return out
