"""Implementation-level search for every Observatory architecture.

A strong blueprint can lose because one deterministic code-generation trajectory is weak. This
overlay gives every architecture four independently prompted semantic implementations, requires
source-level diversity, evaluates the variants on hidden semantics and the durable arena, and permits
two architecture-preserving semantic revisions driven only by aggregate diagnostics. Only the best
fully qualified implementation is canonicalized under the architecture candidate ID before frontier
admission.

Round-created successors, radicals, recombinations, simplifiers, novelty and prior-art challengers use
the same path by wrapping ``crownmod._build_round_candidate``. Hidden cases are never shown to a
builder; revisions receive only aggregate dimension/diagnostic reports.
"""
import hashlib
import json
import math
import os
import shutil
from types import MethodType

from . import observatory_crown_overlay as crownmod
from . import observatory_escalation as escalation
from . import observatory_roles as oroles
from .canonical import atomic_write_json, read_json, sha256_obj
from .handlers import A


DIVERSITY_PERSPECTIVES = (
    ("invariant-first", 0.15,
     "Implement directly from the INV-* obligations. Prefer explicit state transitions and small checkable helpers over implicit cleverness."),
    ("failure-first", 0.35,
     "Design every operation from its adversarial failure semantics: conflicting evidence, late time, unknowns, replay and projection divergence."),
    ("minimal-kernel", 0.55,
     "Minimize trusted semantic code while preserving the declared genome and every measurable invariant. Delete accidental complexity, not architecture."),
)
MIN_DISTINCT_IMPLEMENTATIONS = 3
SEMANTIC_REVISIONS = 2
IMPLEMENTATION_SUPREMACY_KEYS = (
    "implementation_diversity_proven",
    "semantic_implementation_search_closed",
)


def _source_hash(source):
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def _group_store(ctx):
    return ctx.esc._sup().setdefault("implementation_search", {})


def _persist(ctx):
    path = A(ctx, "candidates", "implementation-search.json")
    atomic_write_json(path, {
        "profile": ctx.profile_id,
        "minimum_distinct_sources": MIN_DISTINCT_IMPLEMENTATIONS,
        "semantic_revisions": SEMANTIC_REVISIONS,
        "groups": _group_store(ctx),
    })
    return path


def _install_ledger(ctx):
    if getattr(ctx.esc, "_implementation_search_installed", False):
        return
    original_conditions = ctx.esc._supremacy_conditions
    original_summary = ctx.esc.supremacy_summary

    def conditions(self):
        result = original_conditions()
        groups = self._sup().setdefault("implementation_search", {})
        surviving = [cid for cid in ctx.candidates]
        records = [groups.get(cid) for cid in surviving]
        result["implementation_diversity_proven"] = bool(
            records and all(r and r.get("distinct_source_hashes", 0)
                            >= MIN_DISTINCT_IMPLEMENTATIONS for r in records))
        result["semantic_implementation_search_closed"] = bool(
            records and all(r and r.get("selected_passed") is True for r in records))
        return result

    def summary(self):
        result = original_summary()
        groups = self._sup().setdefault("implementation_search", {})
        current = [groups.get(cid) for cid in ctx.candidates]
        result.update({
            "implementation_diversity_proven": bool(
                current and all(r and r.get("distinct_source_hashes", 0)
                                >= MIN_DISTINCT_IMPLEMENTATIONS for r in current)),
            "semantic_implementation_search_closed": bool(
                current and all(r and r.get("selected_passed") is True for r in current)),
            "implementation_search_groups": len(groups),
            "implementation_search_current_candidates": len(ctx.candidates),
            "implementation_minimum_distinct_sources": MIN_DISTINCT_IMPLEMENTATIONS,
            "semantic_revision_limit": SEMANTIC_REVISIONS,
        })
        return result

    ctx.esc._supremacy_conditions = MethodType(conditions, ctx.esc)
    ctx.esc.supremacy_summary = MethodType(summary, ctx.esc)
    ctx.esc._implementation_search_installed = True

    for key in IMPLEMENTATION_SUPREMACY_KEYS:
        if key not in escalation.SUPREMACY_KEYS:
            escalation.SUPREMACY_KEYS.append(key)
        if key not in escalation.SEARCH_SUPREMACY_KEYS:
            escalation.SEARCH_SUPREMACY_KEYS.append(key)
    schema = escalation.OBSERVATORY_PROOF_SCHEMA
    cond = schema["properties"]["conditions"]
    proof = schema["properties"]["supremacy"]
    for key in IMPLEMENTATION_SUPREMACY_KEYS:
        if key not in cond["required"]:
            cond["required"].append(key)
        cond["properties"][key] = {"type": "boolean"}
        if key not in proof["required"]:
            proof["required"].append(key)
        proof["properties"][key] = {"type": "boolean"}


def _copy_design_metadata(base):
    keys = (
        "seed_id", "lineage_code", "genome", "genome_sha256", "blueprint",
        "blueprint_sha256", "formalization", "formalization_sha256",
        "prebuild_destroyer", "blueprint_fidelity_reports",
        "blueprint_fidelity_warning", "controlled_genome_id", "novelty_method",
        "meta_directive", "taxonomy_resolution_ids",
    )
    return {key: base[key] for key in keys if key in base}


def _generate_variants(ctx, base_id, kind):
    base = ctx.candidates[base_id]
    blueprint = base.get("blueprint") or {}
    formalization = base.get("formalization") or {}
    if not blueprint or not formalization:
        raise RuntimeError(f"{base_id}: implementation diversity requires blueprint + formalization")
    contract = open(os.path.join(ctx.profile_pkg, "EVALUATOR-CONTRACT.md"),
                    encoding="utf-8").read()[:40000]
    metadata = _copy_design_metadata(base)
    variant_ids = [base_id]
    generated = []
    for index, (perspective, temperature, directive) in enumerate(DIVERSITY_PERSPECTIVES, 1):
        vid = f"{base_id}-d{index}"
        if vid in ctx.candidates:
            variant_ids.append(vid)
            continue
        _, obj, _, _ = ctx.ask(
            f"implementation-diversity-{perspective}",
            f"OBS-IMPLEMENTATION-DIVERSITY::{vid}",
            "Produce an INDEPENDENT implementation of the exact supplied architecture. "
            + directive + " Preserve every representable INV-* obligation and the controlled genome. "
            "Do not copy, summarize or revise the architecture; do not hard-code fixtures.",
            [("COMPLETE ARCHITECTURE BLUEPRINT",
              json.dumps(blueprint, ensure_ascii=False)),
             ("ARCHITECTURE FORMALIZATION",
              json.dumps(formalization, ensure_ascii=False)),
             ("SEMANTIC EVALUATOR CONTRACT", contract)],
            oroles.BUILD_SCHEMA,
            line="main" if kind == "baseline" else "successor",
            temperature=temperature)
        obj["candidate_id"] = vid
        obj["family"] = base["family"]
        obj["mechanism"] = base["mechanism"]
        ctx.install_candidate(obj, kind)
        ctx.candidates[vid].update(metadata)
        ctx.candidates[vid]["implementation_perspective"] = perspective
        ctx._save_arena()
        variant_ids.append(vid)
        generated.append({
            "candidate_id": vid,
            "perspective": perspective,
            "temperature": temperature,
            "source_sha256": _source_hash(ctx.candidates[vid]["source"]),
        })

    hashes = {_source_hash(ctx.candidates[cid]["source"]) for cid in variant_ids}
    if len(hashes) < MIN_DISTINCT_IMPLEMENTATIONS:
        vid = f"{base_id}-diversity-repair"
        _, obj, _, _ = ctx.ask(
            "implementation-diversity-repair",
            f"OBS-IMPLEMENTATION-DIVERSITY-REPAIR::{base_id}",
            "The previous architecture-preserving implementations converged to too few distinct "
            "source programs. Implement the same blueprint/formalization through a substantially "
            "different decomposition, data representation and control flow while preserving every "
            "INV-* obligation. Source-level diversity is required; architecture change and fixture "
            "hard-coding are forbidden.",
            [("COMPLETE ARCHITECTURE BLUEPRINT", json.dumps(blueprint, ensure_ascii=False)),
             ("ARCHITECTURE FORMALIZATION", json.dumps(formalization, ensure_ascii=False)),
             ("existing source hashes", json.dumps(sorted(hashes))),
             ("SEMANTIC EVALUATOR CONTRACT", contract)],
            oroles.BUILD_SCHEMA,
            line="main" if kind == "baseline" else "successor",
            temperature=0.75)
        obj["candidate_id"] = vid
        obj["family"] = base["family"]
        obj["mechanism"] = base["mechanism"]
        ctx.install_candidate(obj, kind)
        ctx.candidates[vid].update(metadata)
        ctx.candidates[vid]["implementation_perspective"] = "diversity-repair"
        ctx._save_arena()
        variant_ids.append(vid)
        hashes.add(_source_hash(ctx.candidates[vid]["source"]))
    if len(hashes) < MIN_DISTINCT_IMPLEMENTATIONS:
        raise RuntimeError(
            f"{base_id}: implementation search produced only {len(hashes)} distinct source hashes")

    record = _group_store(ctx).setdefault(base_id, {})
    record.update({
        "architecture_candidate_id": base_id,
        "variant_ids": variant_ids,
        "generated": generated,
        "distinct_source_hashes": len(hashes),
        "source_hashes": sorted(hashes),
        "selected_candidate_id": None,
        "selected_passed": False,
        "revision_history": [],
    })
    ctx.esc._flush()
    _persist(ctx)
    return variant_ids


def _dimension_vector(ctx, cid):
    scores = ctx.scores.get(cid) or {}
    hidden = scores.get("hidden_qualification") or {}
    fidelity = scores.get("fidelity")
    return ctx.dimension_vector(cid, hidden, fidelity) if hidden else {}


def _hard_failures(ctx, cid):
    vector = _dimension_vector(ctx, cid)
    failures = []
    for dim in read_json(ctx.profile.pareto_path(ctx.root)):
        minimum = dim.get("hard_minimum")
        if minimum is None:
            continue
        default = math.inf if dim["direction"] == "lower" else -math.inf
        value = float(vector.get(dim["id"], default))
        if dim["direction"] == "higher" and value + 1e-12 < float(minimum):
            failures.append({"dimension": dim["id"], "value": value,
                             "required": minimum, "direction": "higher"})
        if dim["direction"] == "lower" and value - 1e-12 > float(minimum):
            failures.append({"dimension": dim["id"], "value": value,
                             "required": minimum, "direction": "lower"})
    systems = (ctx.scores.get(cid) or {}).get("systems_qualification") or {}
    if systems.get("status") != "PASS" or systems.get("passed") is not True:
        failures.append({"dimension": "durable_systems_qualification",
                         "value": systems.get("status"), "required": "PASS",
                         "direction": "exact"})
    return failures


def _rank(ctx, cid):
    vector = _dimension_vector(ctx, cid)
    failures = _hard_failures(ctx, cid)
    utility = 0.0
    for dim in read_json(ctx.profile.pareto_path(ctx.root)):
        value = float(vector.get(dim["id"], 0.0))
        if dim["direction"] == "higher":
            utility += value
        else:
            utility -= math.log1p(max(0.0, value))
    return (not failures, -len(failures), round(utility, 12),
            -float(vector.get("trusted_kernel_complexity", math.inf)), cid)


def _evaluate_new(ctx, cid):
    ctx.measure_visible(cid)
    fidelity = ctx.obs_harness.fidelity(
        ctx.candidates[cid]["source"], ctx.suite, ctx.backend)
    ctx.record_score(cid, "fidelity", fidelity)
    hidden = ctx.measure_hidden(cid, "qualification")
    ctx.record_score(cid, "hidden_qualification", hidden)
    crownmod._qualify_systems(ctx, cid, allow_revision=True)


def _revise(ctx, base_id, current_id, attempt):
    current = ctx.candidates[current_id]
    blueprint = current.get("blueprint") or {}
    formalization = current.get("formalization") or {}
    semantic = (ctx.scores.get(current_id) or {}).get("hidden_qualification") or {}
    systems = (ctx.scores.get(current_id) or {}).get("systems_qualification") or {}
    rid = f"{base_id}-semantic-r{attempt}"
    _, obj, _, _ = ctx.ask(
        "semantic-implementation-reviser",
        f"OBS-SEMANTIC-REVISE::{rid}",
        "Revise candidate.py to fix the exact aggregate semantic/durable qualification failures. "
        "Preserve the complete controlled architecture and formalization. Do not infer hidden cases, "
        "hard-code labels or replace the architecture with a generic reference solution.",
        [("COMPLETE ARCHITECTURE BLUEPRINT", json.dumps(blueprint, ensure_ascii=False)),
         ("ARCHITECTURE FORMALIZATION", json.dumps(formalization, ensure_ascii=False)),
         ("CURRENT candidate.py", current["source"][:700000]),
         ("AGGREGATE HIDDEN SEMANTIC REPORT", json.dumps({
             "dimension_scores": semantic.get("dimension_scores", {}),
             "diagnostic_classes": semantic.get("diagnostic_classes", {}),
             "publication_latency": semantic.get("publication_latency"),
         }, ensure_ascii=False)),
         ("DURABLE QUALIFICATION REPORT", json.dumps(systems, ensure_ascii=False)[:50000]),
         ("MECHANICAL HARD FAILURES", json.dumps(_hard_failures(ctx, current_id), ensure_ascii=False))],
        oroles.BUILD_SCHEMA, line="successor", temperature=0.25)
    obj["candidate_id"] = rid
    obj["family"] = current["family"]
    obj["mechanism"] = current["mechanism"]
    ctx.install_candidate(obj, current.get("kind", "baseline"))
    ctx.candidates[rid].update(_copy_design_metadata(current))
    ctx.candidates[rid]["implementation_perspective"] = f"semantic-revision-{attempt}"
    ctx._save_arena()
    _evaluate_new(ctx, rid)
    return rid


def _copy_systems_candidate(ctx, source_id, target_id):
    src = A(ctx, "systems-candidate", f"{source_id}.py")
    dst = A(ctx, "systems-candidate", f"{target_id}.py")
    if os.path.exists(src):
        shutil.copyfile(src, dst)


def _canonicalize(ctx, base_id, selected_id, group_ids):
    chosen_candidate = dict(ctx.candidates[selected_id])
    chosen_scores = dict(ctx.scores.get(selected_id) or {})
    ctx.candidates[base_id] = chosen_candidate
    ctx.scores[base_id] = chosen_scores
    with open(A(ctx, "candidate-src", f"{base_id}.py"), "w", encoding="utf-8") as f:
        f.write(chosen_candidate["source"])
    _copy_systems_candidate(ctx, selected_id, base_id)
    ctx.candidates[base_id]["selected_implementation_source_id"] = selected_id
    ctx.candidates[base_id]["implementation_search_complete"] = True
    for cid in set(group_ids):
        if cid == base_id:
            continue
        ctx.candidates.pop(cid, None)
        ctx.scores.pop(cid, None)
    ctx._save_arena()


def _select_group(ctx, base_id, allow_revision=True):
    record = _group_store(ctx).get(base_id) or {}
    variants = [cid for cid in record.get("variant_ids", []) if cid in ctx.candidates]
    if not variants:
        raise RuntimeError(f"{base_id}: implementation-search group has no surviving variants")
    ranked = sorted(variants, key=lambda cid: _rank(ctx, cid), reverse=True)
    selected = ranked[0]
    revisions = []
    if _hard_failures(ctx, selected) and allow_revision:
        current = selected
        for attempt in range(1, SEMANTIC_REVISIONS + 1):
            revised = _revise(ctx, base_id, current, attempt)
            variants.append(revised)
            revisions.append({
                "attempt": attempt,
                "candidate_id": revised,
                "hard_failures": _hard_failures(ctx, revised),
                "source_sha256": _source_hash(ctx.candidates[revised]["source"]),
            })
            if _rank(ctx, revised) > _rank(ctx, selected):
                selected = revised
            current = revised
            if not _hard_failures(ctx, selected):
                break
    passed = not _hard_failures(ctx, selected)
    record.update({
        "variant_ids": variants,
        "selected_candidate_id": selected,
        "selected_passed": passed,
        "selected_hard_failures": _hard_failures(ctx, selected),
        "selected_source_sha256": _source_hash(ctx.candidates[selected]["source"]),
        "revision_history": revisions,
    })
    ctx.esc._flush()
    _persist(ctx)
    if not passed:
        for cid in set(variants):
            ctx.candidates.pop(cid, None)
            ctx.scores.pop(cid, None)
        ctx._save_arena()
        return False
    _canonicalize(ctx, base_id, selected, variants)
    return True


def install(ctx, handlers):
    _install_ledger(ctx)
    out = dict(handlers)

    original_building = out["CANDIDATE_BUILDING"]

    def candidate_building(machine):
        path = original_building(machine)
        artifact = read_json(path)
        groups = []
        for built in artifact.get("built", []):
            cid = built["candidate_id"]
            variants = _generate_variants(ctx, cid, "baseline")
            groups.append({"candidate_id": cid, "variant_ids": variants})
        artifact["implementation_search"] = {
            "minimum_distinct_sources": MIN_DISTINCT_IMPLEMENTATIONS,
            "groups": groups,
        }
        atomic_write_json(path, artifact)
        return path

    out["CANDIDATE_BUILDING"] = candidate_building

    original_private = out["PRIVATE_QUALIFICATION"]

    def private_qualification(machine):
        path = original_private(machine)
        artifact = read_json(path)
        selected = []
        rejected = []
        # Only initial architecture groups exist at this state.
        for base_id in sorted(list(_group_store(ctx))):
            if base_id not in ctx.candidates and not any(
                    cid in ctx.candidates for cid in (_group_store(ctx)[base_id].get("variant_ids") or [])):
                continue
            if _select_group(ctx, base_id, allow_revision=True):
                selected.append(base_id)
            else:
                rejected.append(base_id)
        if len(selected) < 2:
            raise RuntimeError(
                "fewer than two architectures survived diverse implementation search and semantic/durable revision")
        artifact["implementation_search_selection"] = {
            "selected_architecture_ids": selected,
            "rejected_architecture_ids": rejected,
            "evidence": "candidates/implementation-search.json",
        }
        atomic_write_json(path, artifact)
        return path

    out["PRIVATE_QUALIFICATION"] = private_qualification

    original_round_build = crownmod._build_round_candidate

    def round_build(context, idea, cid, kind, ticket):
        result = original_round_build(context, idea, cid, kind, ticket)
        _generate_variants(context, cid, kind)
        group = _group_store(context)[cid]
        for vid in list(group.get("variant_ids") or []):
            if vid == cid:
                # The base was built before this function and may not have been evaluated yet.
                if not (context.scores.get(vid) or {}).get("hidden_qualification"):
                    _evaluate_new(context, vid)
            else:
                _evaluate_new(context, vid)
        if not _select_group(context, cid, allow_revision=True):
            raise RuntimeError(
                f"{cid}: no diverse implementation survived semantic and durable qualification")
        return result

    crownmod._build_round_candidate = round_build
    return out
