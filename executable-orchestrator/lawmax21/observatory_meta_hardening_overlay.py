"""Fail-closed hardening for Observatory novelty/meta-search.

The core meta overlay keeps the ordinary search flow readable. This layer closes the remaining
protocol-boundary weaknesses before any handler executes:

* meta-search, mechanical coverage and independent closure become explicit supremacy keys in the
  signed terminal schema, not merely commentary behind ``genome_saturated``;
* every stated blind spot, taxonomy observation and non-search protocol improvement is fail-closed;
* dynamic directives identify exactly which improvements they discharge and are class-validated;
* fresh directives and coverage-repair activity force the current wave non-dry even when they find
  only already-known genomes;
* closure auditors must reproduce every mechanical fact exactly;
* interrupted same-round directives cannot be mistaken for completed work;
* failed dynamic constructions are retried and all meta-search seeds remain permanent coverage
  evidence;
* ``other``/``novel_axes`` claims are resolved by two independent CP2-direct-blind taxonomy
  adjudicators. Consensus mapping/non-distinction normalizes the genome; disagreement or a genuinely
  new class remains an owner-signed taxonomy blocker.

No new state machine is created and prior CP2 source material is never read.
"""
import copy
import json
import os
from types import MethodType

from . import observatory_escalation as escalation
from . import observatory_meta_search_overlay as meta
from . import observatory_novelty_overlay as novelty
from . import observatory_roles as oroles
from .canonical import atomic_write_json, read_json, sha256_obj
from .handlers import A


_RETRY_SEEDS = []
META_SUPREMACY_KEYS = (
    "meta_search_closed",
    "mechanical_coverage_closed",
    "independent_closure_closed",
)

TAXONOMY_ADJUDICATION_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object", "additionalProperties": False,
    "required": ["claim_id", "decision", "mapped_axis", "mapped_class",
                 "argument", "falsifier"],
    "properties": {
        "claim_id": {"type": "string", "minLength": 16, "maxLength": 128},
        "decision": {"enum": ["MAP_EXISTING", "NON_DISTINCT", "REQUIRES_EXTENSION"]},
        "mapped_axis": {"type": ["string", "null"]},
        "mapped_class": {"type": ["string", "null"]},
        "argument": {"type": "string", "minLength": 30, "maxLength": 20000},
        "falsifier": {"type": "string", "minLength": 20, "maxLength": 16000},
    },
}


def _meta_paths(ctx):
    root = A(ctx, "architecture", "x")[:-1]
    if not os.path.isdir(root):
        return []
    rows = []
    for name in os.listdir(root):
        if name.startswith("meta-search-wave-r") and name.endswith(".json"):
            try:
                round_no = int(name[len("meta-search-wave-r"):-len(".json")])
            except ValueError:
                continue
            rows.append((round_no, os.path.join(root, name)))
    return [path for _round, path in sorted(rows)]


def _seed_genomes_from_meta(path):
    if not os.path.isfile(path):
        return []
    obj = read_json(path)
    out = []
    for miner in obj.get("dynamic_miners", []):
        for seed in miner.get("seeds", []):
            if meta._valid_genome(seed.get("genome")):
                out.append(seed["genome"])
    for seed in obj.get("dynamic_fresh_seeds", []):
        if meta._valid_genome(seed.get("genome")):
            out.append(seed["genome"])
    for row in obj.get("dynamic_unresolved", []):
        seed = row.get("seed") if isinstance(row, dict) else None
        if isinstance(seed, dict) and meta._valid_genome(seed.get("genome")):
            out.append(seed["genome"])
    return out


def _prior_retry_seeds(ctx, round_no):
    rows = {}
    for path in _meta_paths(ctx):
        obj = read_json(path)
        if int(obj.get("round", 0)) >= round_no:
            continue
        for item in obj.get("dynamic_unresolved", []):
            seed = item.get("seed") if isinstance(item, dict) else None
            if not isinstance(seed, dict) or not meta._valid_genome(seed.get("genome")):
                continue
            gid = seed.get("genome_id") or novelty.controlled_genome_id(seed["genome"])
            copy_seed = dict(seed)
            copy_seed["genome_id"] = gid
            copy_seed["retry_source"] = os.path.basename(path)
            copy_seed["retry_attempts"] = int(copy_seed.get("retry_attempts", 0)) + 1
            rows[gid] = copy_seed
    return [rows[k] for k in sorted(rows)]


def _raw_taxonomy_claims(genome):
    claims = []
    if not isinstance(genome, dict):
        return ["malformed-genome"]
    for axis in oroles.GENOME_FIELDS:
        value = genome.get(axis) or {}
        if isinstance(value, dict) and value.get("class") == "other":
            claims.append(f"other:{axis}")
    for item in genome.get("novel_axes") or []:
        claims.append("novel-axis:" + sha256_obj(item)
                      if isinstance(item, dict) else "malformed-novel-axis")
    return sorted(set(claims))


def _claim_id(genome, claim):
    return sha256_obj({
        "genome_id": novelty.controlled_genome_id(genome),
        "claim": claim,
    })


def _taxonomy_store(ctx):
    return ctx.esc._sup().setdefault("taxonomy_resolutions", {})


def _persist_taxonomy(ctx):
    path = A(ctx, "architecture", "taxonomy-resolutions.json")
    atomic_write_json(path, {
        "profile": ctx.profile_id,
        "prior_cp2_direct_content_read": False,
        "resolutions": _taxonomy_store(ctx),
    })
    return path


def _adjudication_valid(claim, report):
    decision = report.get("decision")
    axis = report.get("mapped_axis")
    cls = report.get("mapped_class")
    if decision == "REQUIRES_EXTENSION":
        return axis is None and cls is None, "extension decision must not invent a mapping"
    if axis not in oroles.GENOME_FIELDS:
        return False, f"invalid mapped axis {axis!r}"
    if cls not in oroles.GENOME_CLASSES[axis] or cls == "other":
        return False, f"invalid mapped class {axis}={cls!r}"
    if claim.startswith("other:") and axis != claim.split(":", 1)[1]:
        return False, "an `other` claim must map on the same controlled axis"
    return True, ""


def _resolve_taxonomy_claims(ctx, genomes, phase):
    store = _taxonomy_store(ctx)
    new_records = []
    contract = open(os.path.join(ctx.profile_pkg, "NOVELTY-SEARCH-CONTRACT.md"),
                    encoding="utf-8").read()[:50000]
    taxonomy = {axis: list(oroles.GENOME_CLASSES[axis]) for axis in oroles.GENOME_FIELDS}

    for genome in genomes:
        if not meta._valid_genome(genome):
            continue
        gid = novelty.controlled_genome_id(genome)
        for claim in _raw_taxonomy_claims(genome):
            cid = _claim_id(genome, claim)
            if cid in store:
                continue
            context = [
                ("taxonomy claim", json.dumps({
                    "claim_id": cid, "claim": claim, "genome_id": gid,
                    "genome": genome, "phase": phase,
                }, ensure_ascii=False)),
                ("controlled taxonomy", json.dumps(taxonomy, ensure_ascii=False)),
                ("novelty/meta-search contract", contract),
            ]
            reports = []
            for tag in ("A", "B"):
                lid, report, _, _ = ctx.ask(
                    f"taxonomy-adjudicator-{tag}",
                    f"OBS-TAXONOMY-{tag}::{cid[:20]}",
                    "Independently adjudicate this controlled-taxonomy claim. Map it to an existing "
                    "axis/class only when the alleged novelty has no distinct load-bearing consequence. "
                    "Use NON_DISTINCT when it is merely a renamed existing choice. Use "
                    "REQUIRES_EXTENSION when no existing class can represent a falsifiable structural "
                    "difference; that decision blocks the signed run pending owner revision. You are "
                    "directly blind to prior CP2 source content.",
                    context, TAXONOMY_ADJUDICATION_SCHEMA, line="successor", temperature=0.0)
                reports.append({"tag": tag, "logical_id": lid, "report": report})

            valid = []
            errors = []
            for row in reports:
                report = row["report"]
                if report.get("claim_id") != cid:
                    errors.append(f"{row['tag']}: claim id mismatch")
                    continue
                ok, why = _adjudication_valid(claim, report)
                if not ok:
                    errors.append(f"{row['tag']}: {why}")
                    continue
                valid.append(report)

            consensus = len(valid) == 2 \
                and valid[0].get("decision") == valid[1].get("decision") \
                and valid[0].get("mapped_axis") == valid[1].get("mapped_axis") \
                and valid[0].get("mapped_class") == valid[1].get("mapped_class")
            if consensus and valid[0]["decision"] in ("MAP_EXISTING", "NON_DISTINCT"):
                status = "RESOLVED_EXISTING_CLASS"
            elif consensus and valid[0]["decision"] == "REQUIRES_EXTENSION":
                status = "BLOCKING_OWNER_SIGNED_EXTENSION"
            else:
                status = "BLOCKING_ADJUDICATOR_DISAGREEMENT"

            record = {
                "claim_id": cid,
                "claim": claim,
                "genome_id": gid,
                "phase": phase,
                "status": status,
                "decision": valid[0].get("decision") if consensus else None,
                "mapped_axis": valid[0].get("mapped_axis") if consensus else None,
                "mapped_class": valid[0].get("mapped_class") if consensus else None,
                "reports": reports,
                "validation_errors": errors,
                "prior_cp2_direct_content_read": False,
            }
            store[cid] = record
            new_records.append(record)
    if new_records:
        ctx.esc._flush()
        _persist_taxonomy(ctx)
    return new_records


def _apply_taxonomy_resolutions(ctx, genome):
    normalized = copy.deepcopy(genome)
    store = _taxonomy_store(ctx)
    resolution_ids = []
    unresolved = []
    novel_resolved = []
    assignments = {}

    for claim in _raw_taxonomy_claims(genome):
        cid = _claim_id(genome, claim)
        record = store.get(cid)
        if not record or record.get("status") != "RESOLVED_EXISTING_CLASS":
            unresolved.append(cid)
            continue
        axis, cls = record.get("mapped_axis"), record.get("mapped_class")
        if axis in assignments and assignments[axis] != cls:
            unresolved.append(cid)
            continue
        assignments[axis] = cls
        resolution_ids.append(cid)
        if claim.startswith("novel-axis:"):
            novel_resolved.append(claim.split(":", 1)[1])

    if unresolved:
        return normalized, resolution_ids, sorted(set(unresolved))

    for axis, cls in assignments.items():
        old = normalized.get(axis) or {}
        detail = old.get("detail") if isinstance(old, dict) else ""
        normalized[axis] = {
            "class": cls,
            "detail": (str(detail) + " [independent taxonomy consensus mapped this choice to "
                       + f"{axis}={cls}]")[:5000],
        }
    if normalized.get("novel_axes"):
        retained = []
        for item in normalized.get("novel_axes") or []:
            key = sha256_obj(item) if isinstance(item, dict) else None
            if key not in novel_resolved:
                retained.append(item)
        if retained:
            normalized["novel_axes"] = retained
        else:
            normalized.pop("novel_axes", None)
    return normalized, resolution_ids, []


def _directive_valid(directive):
    for item in directive.get("required_classes") or []:
        axis, cls = item.get("axis"), item.get("class")
        if axis not in oroles.GENOME_FIELDS:
            return False, f"unknown controlled axis {axis!r}"
        if cls not in oroles.GENOME_CLASSES[axis]:
            return False, f"unknown controlled class {axis}={cls!r}"
        if cls == "other":
            return False, f"dynamic directive requests unresolved taxonomy class {axis}=other"
    return True, ""


def _harden_meta_schema():
    item = meta.META_SEARCH_SCHEMA["properties"]["dynamic_directives"]["items"]
    if "discharges_improvement_ids" not in item["required"]:
        item["required"].append("discharges_improvement_ids")
    item["properties"]["discharges_improvement_ids"] = {
        "type": "array", "maxItems": 32,
        "items": {"type": "string", "minLength": 2, "maxLength": 120},
    }


def _harden_terminal_schema(ctx):
    for key in META_SUPREMACY_KEYS:
        if key not in escalation.SUPREMACY_KEYS:
            escalation.SUPREMACY_KEYS.append(key)
        if key not in escalation.SEARCH_SUPREMACY_KEYS:
            escalation.SEARCH_SUPREMACY_KEYS.append(key)

    schema = escalation.OBSERVATORY_PROOF_SCHEMA
    conditions = schema["properties"]["conditions"]
    supremacy = schema["properties"]["supremacy"]
    for key in META_SUPREMACY_KEYS:
        if key not in conditions["required"]:
            conditions["required"].append(key)
        conditions["properties"][key] = {"type": "boolean"}
        if key not in supremacy["required"]:
            supremacy["required"].append(key)
        supremacy["properties"][key] = {"type": "boolean"}

    original = ctx.esc._supremacy_conditions

    def supremacy_conditions(self):
        result = original()
        waves = self._sup().setdefault("novelty_waves", [])
        last = waves[-1] if waves else {}
        result["meta_search_closed"] = bool(
            waves and all(w.get("meta_critics_complete") is True
                          and int(w.get("protocol_improvements_open", 0)) == 0
                          for w in waves))
        result["mechanical_coverage_closed"] = bool(
            last.get("mechanical_coverage_complete") is True
            and int(last.get("taxonomy_unresolved_count", 0)) == 0)
        result["independent_closure_closed"] = bool(
            waves and all(w.get("closure_auditors_complete") is True for w in waves)
            and last.get("closure_auditors_support_dry") is True)
        return result

    ctx.esc._supremacy_conditions = MethodType(supremacy_conditions, ctx.esc)


def install(ctx, handlers):
    if getattr(meta, "_meta_hardening_installed", False):
        return dict(handlers)

    _harden_meta_schema()
    _harden_terminal_schema(ctx)

    original_all_search_genomes = meta._all_search_genomes
    original_dynamic_directives = meta._dynamic_directives
    original_closure_auditor = meta._run_closure_auditor
    original_dedupe_fresh = meta._dedupe_fresh
    original_execute_meta_wave = meta._execute_meta_wave
    original_taxonomy_claims = meta._taxonomy_claims
    original_meta_build_dynamic = meta._build_dynamic
    original_novelty_build_selected = novelty._build_selected

    def taxonomy_claims(genome):
        unresolved = []
        store = _taxonomy_store(ctx)
        for claim in original_taxonomy_claims(genome):
            record = store.get(_claim_id(genome, claim))
            if not record or record.get("status") != "RESOLVED_EXISTING_CLASS":
                unresolved.append(claim)
        return unresolved

    def all_search_genomes(context, extra=None):
        raw = list(original_all_search_genomes(context, extra))
        for path in _meta_paths(context):
            raw.extend(_seed_genomes_from_meta(path))
        out = []
        for genome in raw:
            normalized, _ids, unresolved = _apply_taxonomy_resolutions(context, genome)
            out.append(normalized if not unresolved else genome)
        return out

    def dynamic_directives(critics, context):
        # A crash may flush directive history before the corresponding meta artifact. Prune only the
        # current round when no artifact exists, so resume re-executes rather than assumes completion.
        meta_path = A(context, "architecture", f"meta-search-wave-r{context.round}.json")
        history_store = context.esc._sup().setdefault("meta_directive_history", [])
        if not os.path.exists(meta_path):
            retained = [x for x in history_store
                        if int(x.get("round", -1)) != int(context.round)]
            if len(retained) != len(history_store):
                history_store[:] = retained
                context.esc._flush()

        fresh, base_blockers, history = original_dynamic_directives(critics, context)
        blockers = list(base_blockers)
        accepted = []
        accepted_keys = set()
        existing_ids = {x.get("directive_key") for x in history if isinstance(x, dict)}

        for directive in fresh:
            ok, why = _directive_valid(directive)
            if not ok:
                blockers.append({"kind": "invalid-dynamic-directive",
                                 "critic": directive.get("critic"), "reason": why,
                                 "directive": directive})
                continue
            key = directive["directive_key"]
            if key not in accepted_keys:
                accepted.append(directive)
                accepted_keys.add(key)

        for critic in critics:
            report = critic["report"]
            directives = report.get("dynamic_directives") or []
            improvements = report.get("attainable_improvements") or []
            blind_spots = report.get("blind_spots") or []
            taxonomy = report.get("taxonomy_observations") or []
            dynamic_ids = {x.get("improvement_id") for x in improvements
                           if x.get("kind") == "dynamic_search"}
            directive_map = {}
            for directive in directives:
                ok, why = _directive_valid(directive)
                if not ok:
                    blockers.append({"kind": "invalid-dynamic-directive",
                                     "critic": critic["tag"], "reason": why,
                                     "directive": directive})
                    continue
                referenced = set(directive.get("discharges_improvement_ids") or [])
                invalid_refs = sorted(referenced - dynamic_ids)
                if invalid_refs:
                    blockers.append({"kind": "directive-references-unknown-improvement",
                                     "critic": critic["tag"],
                                     "invalid_ids": invalid_refs,
                                     "directive": directive})
                for iid in referenced & dynamic_ids:
                    directive_map.setdefault(iid, []).append(directive)

            for improvement in improvements:
                kind = improvement.get("kind")
                iid = improvement.get("improvement_id")
                if kind == "dynamic_search":
                    mapped = directive_map.get(iid) or []
                    if not mapped:
                        blockers.append({"kind": "undischarged-dynamic-improvement",
                                         "critic": critic["tag"],
                                         "improvement": improvement})
                    else:
                        keys = {meta._directive_key(x) for x in mapped}
                        if not keys.issubset(existing_ids | accepted_keys):
                            blockers.append({"kind": "dynamic-directive-not-scheduled",
                                             "critic": critic["tag"],
                                             "improvement": improvement})
                else:
                    blockers.append({"kind": kind or "unclassified-improvement",
                                     "critic": critic["tag"],
                                     "improvement": improvement})

            # A blind spot is, by definition, an unresolved weakness of the current search. The
            # critic may instead express an actionable blind spot as a mapped attainable improvement.
            if blind_spots:
                blockers.append({"kind": "unresolved-meta-search-blind-spots",
                                 "critic": critic["tag"], "blind_spots": blind_spots})
            if taxonomy:
                blockers.append({"kind": "meta-taxonomy-observation",
                                 "critic": critic["tag"], "observations": taxonomy})
            if report.get("supports_current_protocol") is not True:
                blockers.append({"kind": "meta-critic-does-not-support-closure",
                                 "critic": critic["tag"]})

        unique = {}
        for blocker in blockers:
            unique.setdefault(sha256_obj(blocker), blocker)
        return accepted, [unique[k] for k in sorted(unique)], history

    def closure_auditor(context, tag, facts, evidence):
        row = original_closure_auditor(context, tag, facts, evidence)
        report = row["report"]
        verified = report.get("verified_facts") or {}
        mismatches = [key for key, expected in facts.items()
                      if verified.get(key) is not bool(expected)]
        if mismatches:
            blockers = list(report.get("blockers") or [])
            blockers.append("auditor mechanical-fact mismatch: " + ", ".join(sorted(mismatches)))
            report["blockers"] = blockers
            report["supports_dry_wave"] = False
            report["reason"] = (
                "Closure refused because the auditor did not reproduce the persisted mechanical "
                "facts exactly. " + report.get("reason", ""))[:20000]
        return row

    def dedupe_fresh(seeds, known):
        combined = list(_RETRY_SEEDS) + list(seeds)
        return original_dedupe_fresh(combined, known)

    def novelty_build_selected(context, selected, common):
        normalized = []
        pending = []
        for seed in selected:
            genome, resolution_ids, unresolved = _apply_taxonomy_resolutions(
                context, seed.get("genome") or {})
            if unresolved:
                retry = dict(seed)
                retry["taxonomy_resolution_pending"] = unresolved
                pending.append({
                    "genome_id": seed.get("genome_id")
                                 or novelty.controlled_genome_id(seed.get("genome") or {}),
                    "seed": retry,
                    "reason": "independent taxonomy resolution pending",
                })
                continue
            row = dict(seed)
            row["genome"] = genome
            row["genome_id"] = novelty.controlled_genome_id(genome)
            row["taxonomy_resolution_ids"] = resolution_ids
            normalized.append(row)
        built, unresolved = original_novelty_build_selected(context, normalized, common)
        return built, pending + unresolved

    def meta_build_dynamic(context, seeds, common):
        _resolve_taxonomy_claims(context,
                                 [x.get("genome") for x in seeds if isinstance(x, dict)],
                                 f"meta-dynamic-round-{context.round}")
        normalized = []
        pending = []
        for seed in seeds:
            genome, resolution_ids, unresolved = _apply_taxonomy_resolutions(
                context, seed.get("genome") or {})
            if unresolved:
                pending.append({
                    "genome_id": seed.get("genome_id")
                                 or novelty.controlled_genome_id(seed.get("genome") or {}),
                    "seed": seed,
                    "reason": "independent taxonomy resolution pending",
                })
                continue
            row = dict(seed)
            row["genome"] = genome
            row["genome_id"] = novelty.controlled_genome_id(genome)
            row["taxonomy_resolution_ids"] = resolution_ids
            normalized.append(row)
        built, unresolved = original_meta_build_dynamic(context, normalized, common)
        return built, pending + unresolved

    def execute_meta_wave(context, round_no):
        global _RETRY_SEEDS
        raw = list(original_all_search_genomes(context))
        for path in _meta_paths(context):
            raw.extend(_seed_genomes_from_meta(path))
        _resolve_taxonomy_claims(context, raw, f"pre-meta-round-{round_no}")
        _RETRY_SEEDS = _prior_retry_seeds(context, round_no)
        try:
            artifact = original_execute_meta_wave(context, round_no)
            activity = bool(
                artifact.get("dynamic_directives")
                or not (artifact.get("coverage_before") or {}).get("complete", False))
            if activity and artifact.get("ledger_wave", {}).get("dry") is True:
                artifact["ledger_wave"]["dry"] = False
                artifact["ledger_wave"]["dry_blocked_by_new_search_activity"] = True
                meta_path = A(context, "architecture", f"meta-search-wave-r{round_no}.json")
                wave_path = A(context, "architecture", f"novelty-wave-r{round_no}.json")
                atomic_write_json(meta_path, artifact)
                wave_artifact = read_json(wave_path)
                wave_artifact["ledger_wave"] = artifact["ledger_wave"]
                if isinstance(wave_artifact.get("meta_search"), dict):
                    wave_artifact["meta_search"]["dry"] = False
                atomic_write_json(wave_path, wave_artifact)
                label = artifact["ledger_wave"]["label"]
                for wave in context.esc._sup().setdefault("novelty_waves", []):
                    if wave.get("label") == label:
                        wave.clear()
                        wave.update(artifact["ledger_wave"])
                        break
                context.esc._flush()
            return artifact
        finally:
            _RETRY_SEEDS = []

    # Patch module globals before the handler closures execute.
    meta._taxonomy_claims = taxonomy_claims
    meta._all_search_genomes = all_search_genomes
    meta._dynamic_directives = dynamic_directives
    meta._run_closure_auditor = closure_auditor
    meta._dedupe_fresh = dedupe_fresh
    meta._build_dynamic = meta_build_dynamic
    meta._execute_meta_wave = execute_meta_wave
    novelty._build_selected = novelty_build_selected

    out = dict(handlers)
    original_target = out["TARGET_ARCHITECTURE_SEARCH"]

    def target_search(machine):
        path = original_target(machine)
        artifact = read_json(path)
        proposals = artifact.get("proposals", [])
        _resolve_taxonomy_claims(ctx, [x.get("genome") for x in proposals], "initial-v0")
        unresolved_rows = []
        for proposal in proposals:
            original = proposal.get("genome") or {}
            normalized, resolution_ids, unresolved = _apply_taxonomy_resolutions(ctx, original)
            if unresolved:
                unresolved_rows.append({
                    "seed_id": proposal.get("seed_id"),
                    "family": proposal.get("family"),
                    "claim_ids": unresolved,
                })
                continue
            if resolution_ids:
                proposal["pre_resolution_genome_sha256"] = sha256_obj(original)
                proposal["genome"] = normalized
                proposal["taxonomy_resolution_ids"] = resolution_ids
        artifact["proposals"] = proposals
        artifact["initial_taxonomy_claims"] = unresolved_rows
        atomic_write_json(path, artifact)
        backlog = A(ctx, "architecture", "initial-taxonomy-backlog.json")
        atomic_write_json(backlog, {
            "status": ("BLOCKING_OWNER_SIGNED_TAXONOMY_REVISION"
                       if unresolved_rows else "RESOLVED"),
            "claims": unresolved_rows,
            "taxonomy_resolutions": "architecture/taxonomy-resolutions.json",
        })
        return path

    out["TARGET_ARCHITECTURE_SEARCH"] = target_search
    meta._meta_hardening_installed = True
    return out
