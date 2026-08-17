"""Hardening hooks for the Observatory meta-search overlay.

The core meta overlay intentionally keeps its control flow readable. This layer strengthens four
failure boundaries without introducing another state-machine handler:

* every stated blind spot, taxonomy observation and non-search protocol improvement is fail-closed;
* dynamic directives are schema/taxonomy checked before execution;
* closure auditors must reproduce the mechanical facts exactly, not merely return an approving flag;
* failed dynamic constructions are carried into the next wave and all meta-search seeds remain part
  of the permanent controlled-coverage record.

The hooks patch module functions before any handler executes; handler closures resolve those globals
at call time. Prior CP2 content is never read.
"""
import os

from . import observatory_meta_search_overlay as meta
from . import observatory_novelty_overlay as novelty
from . import observatory_roles as oroles
from .canonical import read_json
from .handlers import A


_RETRY_SEEDS = []


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
            copy = dict(seed)
            copy["genome_id"] = gid
            copy["retry_source"] = os.path.basename(path)
            copy["retry_attempts"] = int(copy.get("retry_attempts", 0)) + 1
            rows[gid] = copy
    return [rows[k] for k in sorted(rows)]


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


def install(ctx, handlers):
    if getattr(meta, "_meta_hardening_installed", False):
        return dict(handlers)

    original_all_search_genomes = meta._all_search_genomes
    original_dynamic_directives = meta._dynamic_directives
    original_closure_auditor = meta._run_closure_auditor
    original_dedupe_fresh = meta._dedupe_fresh
    original_execute_meta_wave = meta._execute_meta_wave

    def all_search_genomes(context, extra=None):
        out = list(original_all_search_genomes(context, extra))
        for path in _meta_paths(context):
            out.extend(_seed_genomes_from_meta(path))
        return out

    def dynamic_directives(critics, context):
        # Start with the base dedup/history semantics, then independently reconstruct every blocker
        # so a model cannot neutralize a feasible improvement by setting blocking=false.
        fresh, base_blockers, history = original_dynamic_directives(critics, context)
        blockers = list(base_blockers)
        accepted = []
        accepted_keys = set()
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

            for improvement in improvements:
                kind = improvement.get("kind")
                if kind == "dynamic_search":
                    if not directives:
                        blockers.append({"kind": "undischarged-dynamic-improvement",
                                         "critic": critic["tag"],
                                         "improvement": improvement})
                else:
                    blockers.append({"kind": kind or "unclassified-improvement",
                                     "critic": critic["tag"],
                                     "improvement": improvement})

            if blind_spots and not improvements and not directives:
                blockers.append({"kind": "blind-spots-without-required-action",
                                 "critic": critic["tag"], "blind_spots": blind_spots})
            if taxonomy:
                blockers.append({"kind": "meta-taxonomy-observation",
                                 "critic": critic["tag"], "observations": taxonomy})
            if report.get("supports_current_protocol") is not True \
                    and not improvements and not blind_spots and not taxonomy:
                blockers.append({"kind": "protocol-rejected-without-falsifiable-reason",
                                 "critic": critic["tag"]})

        # Canonical blocker deduplication keeps resume artifacts deterministic.
        unique = {}
        from .canonical import sha256_obj
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

    def execute_meta_wave(context, round_no):
        global _RETRY_SEEDS
        _RETRY_SEEDS = _prior_retry_seeds(context, round_no)
        try:
            return original_execute_meta_wave(context, round_no)
        finally:
            _RETRY_SEEDS = []

    meta._all_search_genomes = all_search_genomes
    meta._dynamic_directives = dynamic_directives
    meta._run_closure_auditor = closure_auditor
    meta._dedupe_fresh = dedupe_fresh
    meta._execute_meta_wave = execute_meta_wave
    meta._meta_hardening_installed = True
    return dict(handlers)
