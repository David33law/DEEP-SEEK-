"""Supremacy-search overlay for the National Legal Observatory.

This is the layer that turns "ask for a great architecture" into an architecture-search
experiment. It runs a forest of independent and anti-attractor design lineages, measures
structural diversity through an explicit architecture genome, expands only structurally diverse
seeds into complete blueprints, formalizes their invariants, attacks them before implementation,
and binds the complete artifacts into the owner gate.

Prior CP2 remains invisible throughout this module. It is still released only by the later
CEILING_ANALYSIS handler after an executable independent frontier exists.
"""
import json
import os
import re

from . import observatory_roles as oroles
from .canonical import atomic_write_json, read_json, sha256_file, sha256_obj
from .handlers import A
from . import observatory_blueprint_overlay as bpmod


MIN_STRUCTURAL_DISTANCE = 2
MAX_FINALISTS = 18
MIN_FINALISTS = 12
SEEDS_PER_LINEAGE = 6

GENERAL_LINEAGES = [
    ("G01", "first-principles-legal-information",
     "Derive architectures from the legal-information problem itself. Question every inherited database, ledger, graph and service assumption."),
    ("G02", "formal-verification-minimal-tcb",
     "Search for architectures that minimize the trusted computing base and maximize independently checkable proof obligations."),
    ("G03", "distributed-canonical-state",
     "Search from distributed-systems first principles: partitions, replication, deterministic convergence, commit semantics and canonical truth."),
    ("G04", "compiler-dataflow",
     "Treat the legal order as a compilation/derivation problem. Explore declarative IRs, verified compilers, incremental dataflow and proof-producing transformations."),
    ("G05", "cryptographic-proof-object",
     "Search from evidence commitments, proof objects, transparency and independently verifiable publication rather than application-database conventions."),
    ("G06", "national-observation-operations",
     "Search from the operational obligation that legally material changes cannot disappear silently across a national, long-lived source universe."),
]

ANTI_ATTRACTOR_LINEAGES = [
    ("A01", "no-ledger-authority-seat",
     "The canonical authority seat may NOT be an append-only ledger/log/event stream. Logs may exist only as subordinate evidence or audit artifacts."),
    ("A02", "no-global-event-sourcing",
     "Do NOT use global event sourcing or one globally ordered event history as the state-derivation foundation."),
    ("A03", "no-cas-as-design-center",
     "Content-addressed storage may be used as a storage primitive but may NOT be the architectural authority seat or the central design abstraction."),
    ("A04", "no-single-logical-writer",
     "Do NOT rely on one logical writer, leader lease or single canonical append process. Preserve one canonical truth through another consistency construction."),
    ("A05", "replicated-commit-first",
     "Start from replicated/BFT or quorum-verified canonical commit under faults; do not reduce the architecture to a single-node system plus replicas."),
    ("A06", "proof-dag-first",
     "Make immutable proof/dependency objects or a proof DAG the principal state representation; do not use a mutable canonical database or ordered ledger as the principal representation."),
    ("A07", "declarative-calculus-first",
     "Make a declarative legal calculus/typed IR and verified compiler/interpreter the architectural center. Storage is subordinate to semantics."),
    ("A08", "minimal-verifier-kernel",
     "Push almost everything outside the trusted boundary. Search for a tiny verifier/admission kernel that can reject invalid legal-state claims produced by untrusted workers."),
    ("A09", "federated-evidence-authorities",
     "Assume multiple independently operated evidence authorities and no central acquisition authority. Produce one canonical public legal truth through deterministic evidence-aware convergence."),
]


def _norm(value):
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def genome_signature(genome):
    return tuple(_norm((genome or {}).get(k)) for k in oroles.GENOME_FIELDS)


def genome_distance(a, b):
    sa, sb = genome_signature(a), genome_signature(b)
    return sum(1 for x, y in zip(sa, sb) if x != y)


def structurally_distinct(a, b):
    return genome_distance(a, b) >= MIN_STRUCTURAL_DISTANCE


def _cluster_count(seeds):
    reps = []
    for seed in seeds:
        g = seed.get("genome") or {}
        if not any(not structurally_distinct(g, r.get("genome") or {}) for r in reps):
            reps.append(seed)
    return len(reps)


def _find_cp1(ctx):
    found = []
    for root, _dirs, files in os.walk(ctx.cp1_evidence):
        if "CP1-REPOSITORY-RECONSTRUCTION.md" in files:
            found.append(os.path.join(root, "CP1-REPOSITORY-RECONSTRUCTION.md"))
    if len(found) != 1:
        raise RuntimeError(f"supremacy search expected exactly one CP1 reconstruction, found {len(found)}")
    return found[0]


def _profile_text(ctx, name, limit):
    p = os.path.join(ctx.profile_pkg, name)
    return open(p, encoding="utf-8").read()[:limit]


def _run_lineage(ctx, code, name, directive, mode, common_context):
    role = f"architecture-search-{mode}"
    task = (
        f"Run architecture-search lineage {code}/{name}. Produce exactly {SEEDS_PER_LINEAGE} "
        "mutually incompatible whole-system architecture seeds for the National Legal Observatory. "
        "Do not optimize for familiarity. For every seed, expose the complete structural genome, "
        "load-bearing mechanisms, assumptions, decisive advantages, failure modes and why it is not "
        "already entitled to a higher claim. Reject at least two additional ideas explicitly. The "
        "candidate list must contain at least four structural families whose genomes differ on two "
        "or more load-bearing axes. You are blind to all prior CP2 architecture conclusions. "
        + directive
    )
    lid, obj, _, _ = ctx.ask(
        role, f"OBS-SEARCH-{code}", task, common_context, oroles.SEARCH_LINEAGE_SCHEMA)

    if _cluster_count(obj["candidates"]) < 4:
        # A second *new* logical request, not a retry, repairs prompt-induced convergence.
        lid, obj, _, _ = ctx.ask(
            role, f"OBS-SEARCH-{code}-DIVERSITY-REPAIR",
            task + " Your first search collapsed into too few structural families. Replace near-"
            "duplicates until at least four pairwise structural clusters exist; do not merely rename them.",
            common_context + [("rejected convergent first search", json.dumps(obj, ensure_ascii=False)[:100000])],
            oroles.SEARCH_LINEAGE_SCHEMA)
    if _cluster_count(obj["candidates"]) < 4:
        raise RuntimeError(f"{code}: search lineage failed to produce four structurally distinct clusters")

    local_to_global = {}
    candidates = []
    for i, seed in enumerate(obj["candidates"], 1):
        x = dict(seed)
        x["local_seed_id"] = seed["seed_id"]
        x["seed_id"] = f"{code}-{i:02d}"
        x["lineage_code"] = code
        x["lineage_name"] = name
        x["lineage_mode"] = mode
        x["constraint"] = directive if mode == "anti-attractor" else None
        x["genome_sha256"] = sha256_obj(seed["genome"])
        local_to_global[seed["seed_id"]] = x["seed_id"]
        candidates.append(x)
    finalists = [local_to_global[x] for x in obj["finalist_ids"] if x in local_to_global]
    if not finalists:
        finalists = [candidates[0]["seed_id"]]
    return {
        "logical_id": lid,
        "lineage": obj["lineage"],
        "code": code,
        "name": name,
        "mode": mode,
        "constraint": directive if mode == "anti-attractor" else None,
        "candidates": candidates,
        "rejected": obj["rejected"],
        "finalist_ids": finalists,
        "exhaustion_note": obj["exhaustion_note"],
        "structural_clusters": _cluster_count(candidates),
    }


def _select_diverse(lineages):
    all_seeds = [s for line in lineages for s in line["candidates"]]
    by_id = {s["seed_id"]: s for s in all_seeds}
    selected = []

    # First, preserve one nominated seed from every independent/anti-attractor lineage when it
    # adds a genuinely new genome. This makes search coverage first-class rather than decorative.
    for line in lineages:
        ordered = list(line["finalist_ids"]) + [s["seed_id"] for s in line["candidates"]]
        for sid in ordered:
            s = by_id.get(sid)
            if s and all(structurally_distinct(s["genome"], x["genome"]) for x in selected):
                selected.append(s)
                break
        if len(selected) >= MAX_FINALISTS:
            break

    remaining = [s for s in all_seeds if s not in selected]
    while remaining and len(selected) < MAX_FINALISTS:
        if not selected:
            pick = remaining[0]
        else:
            scored = []
            for s in remaining:
                minimum = min(genome_distance(s["genome"], x["genome"]) for x in selected)
                scored.append((minimum, s["seed_id"], s))
            scored.sort(key=lambda x: (-x[0], x[1]))
            pick = scored[0][2]
            if scored[0][0] < MIN_STRUCTURAL_DISTANCE:
                break
        selected.append(pick)
        remaining.remove(pick)

    if len(selected) < MIN_FINALISTS:
        raise RuntimeError(
            f"search forest produced only {len(selected)} structurally distinct finalists; "
            f"minimum is {MIN_FINALISTS}")
    return selected[:MAX_FINALISTS]


def _expand_seed(ctx, seed, common_context):
    task = (
        "Expand this selected architecture seed into a COMPLETE whole-system Observatory blueprint. "
        "Copy the supplied genome choices exactly; expansion may deepen mechanisms and proof topology "
        "but may not silently move the architecture into another structural family. Cover the entire "
        "Mission-v2 and Supremacy contracts. Give falsifiable predictions and an evidence-bounded "
        "why_not_higher; do not self-award supremacy."
    )
    lid, proposal, _, _ = ctx.ask(
        "architecture-expander", f"OBS-EXPAND::{seed['seed_id']}", task,
        [("selected architecture seed", json.dumps(seed, ensure_ascii=False))] + common_context,
        oroles.PROPOSAL_SCHEMA)
    if genome_signature(proposal["genome"]) != genome_signature(seed["genome"]):
        raise RuntimeError(f"{seed['seed_id']}: architecture expander changed the structural genome")
    return {"role": "architecture-expander", "logical_id": lid,
            "seed_id": seed["seed_id"], "lineage_code": seed["lineage_code"], **proposal}


def _formalize(ctx, proposal):
    bp = bpmod.blueprint(proposal)
    bp_sha = bpmod.blueprint_sha256(proposal)
    lid, form, _, _ = ctx.ask(
        "architecture-formalizer", f"OBS-FORMALIZE::{proposal['seed_id']}::{bp_sha[:12]}",
        "Translate the complete architecture blueprint into explicit invariants and proof obligations. "
        "Do not improve or simplify the architecture here; make its authority/state/failure semantics "
        "precise enough that a builder can be checked for fidelity. Every important requirement needs "
        "a stable INV-* identifier and a concrete failure condition/observable.",
        [("complete blueprint", json.dumps(bp, ensure_ascii=False)),
         ("supremacy contract", _profile_text(ctx, "SUPREMACY-CONTRACT.md", 30000)),
         ("evaluator contract", _profile_text(ctx, "EVALUATOR-CONTRACT.md", 30000))],
        oroles.FORMALIZATION_SCHEMA)
    return lid, form


def _destroy_prebuild(ctx, proposal, formalization, forest_summary):
    lid, rep, _, _ = ctx.ask(
        "architecture-destroyer-prebuild", f"OBS-DESTROY-PRE::{proposal['seed_id']}",
        "Try to kill this architecture before implementation. Attack its assumptions, trusted "
        "boundary, identity/time/effect semantics, failure model, recovery, scale and publication "
        "claims. Name invariant IDs when the formalization itself is inconsistent. A persuasive "
        "architecture is not a reason to spare it; this role is rewarded for finding fatal structure.",
        [("complete blueprint", json.dumps(bpmod.blueprint(proposal), ensure_ascii=False)),
         ("formalization", json.dumps(formalization, ensure_ascii=False)),
         ("search-forest structural summary", json.dumps(forest_summary, ensure_ascii=False)[:40000])],
        oroles.DESTROYER_SCHEMA)
    return lid, rep


def install(ctx, handlers):
    H = dict(handlers)

    def target_search(_m):
        charter = _profile_text(ctx, "OBJECTIVE-CHARTER.md", 40000)
        supremacy = _profile_text(ctx, "SUPREMACY-CONTRACT.md", 40000)
        cp1 = open(_find_cp1(ctx), encoding="utf-8").read()[:70000]
        common = [
            ("National Observatory objective charter", charter),
            ("Supremacy research contract", supremacy),
            ("sealed CP1 repository reconstruction", cp1),
        ]

        lineages = []
        for code, name, directive in GENERAL_LINEAGES:
            lineages.append(_run_lineage(ctx, code, name, directive, "independent", common))
        for code, name, constraint in ANTI_ATTRACTOR_LINEAGES:
            lineages.append(_run_lineage(
                ctx, code, name,
                "ANTI-ATTRACTOR CONSTRAINT: " + constraint +
                " If the constraint makes the mission impossible, prove why and still search for "
                "the closest structurally different construction rather than ignoring it.",
                "anti-attractor", common))

        selected = _select_diverse(lineages)
        forest_summary = {
            "lineages": len(lineages),
            "general_lineages": len(GENERAL_LINEAGES),
            "anti_attractor_lineages": len(ANTI_ATTRACTOR_LINEAGES),
            "seeds": sum(len(x["candidates"]) for x in lineages),
            "selected_finalists": len(selected),
            "minimum_structural_distance_fields": MIN_STRUCTURAL_DISTANCE,
            "selected": [{"seed_id": s["seed_id"], "lineage": s["lineage_code"],
                          "family": s["family"], "genome_sha256": s["genome_sha256"]}
                         for s in selected],
            "prior_cp2_visible": False,
        }
        forest_path = A(ctx, "architecture", "search_forest.json")
        atomic_write_json(forest_path, {"summary": forest_summary, "lineages": lineages,
                                       "selected_seed_ids": [s["seed_id"] for s in selected]})

        proposals = []
        for seed in selected:
            proposal = _expand_seed(ctx, seed, common)
            form_lid, form = _formalize(ctx, proposal)
            destroy_lid, destroy = _destroy_prebuild(ctx, proposal, form, forest_summary)
            proposal["formalization"] = form
            proposal["formalization_logical_id"] = form_lid
            proposal["formalization_sha256"] = sha256_obj(form)
            proposal["prebuild_destroyer"] = destroy
            proposal["prebuild_destroyer_logical_id"] = destroy_lid
            proposal["prebuild_destroyer_sha256"] = sha256_obj(destroy)
            proposals.append(proposal)

        # Family names remain in the historical escalation ledger for compatibility, but the
        # supremacy layer separately binds structural genomes and never treats names as diversity.
        ctx.esc.declare_families([x["family"] for x in proposals])
        p = A(ctx, "architecture", "proposals.json")
        atomic_write_json(p, {
            "profile": ctx.profile_id,
            "prior_cp2_visible": False,
            "search_mode": "SUPREMACY_SEARCH_FOREST_V1",
            "search_forest_sha256": sha256_file(forest_path),
            "structural_finalists": len(proposals),
            "proposals": proposals,
        })
        return p

    H["TARGET_ARCHITECTURE_SEARCH"] = target_search

    def v0_reviewed(_m):
        proposals_path = A(ctx, "architecture", "proposals.json")
        forest_path = A(ctx, "architecture", "search_forest.json")
        artifact = read_json(proposals_path)
        props = artifact["proposals"]
        # Gate cannot be satisfied if any two finalists are merely renamed near-duplicates.
        for i, a in enumerate(props):
            for b in props[i + 1:]:
                if not structurally_distinct(a["genome"], b["genome"]):
                    raise RuntimeError(
                        f"owner gate refused: {a['seed_id']} and {b['seed_id']} differ on fewer "
                        f"than {MIN_STRUCTURAL_DISTANCE} genome axes")
        p = A(ctx, "gates", "v0_subject.json")
        atomic_write_json(p, {
            "gate": "GATE-ARCH-V0",
            "run_id": ctx.run_id,
            "supremacy_contract_sha256": sha256_file(os.path.join(ctx.profile_pkg, "SUPREMACY-CONTRACT.md")),
            "search_forest_sha256": sha256_file(forest_path),
            "proposals_sha256": sha256_file(proposals_path),
            "search_mode": artifact["search_mode"],
            "structural_finalists": len(props),
            "blueprints": [{
                "seed_id": x["seed_id"],
                "lineage_code": x["lineage_code"],
                "family": x["family"],
                "genome_sha256": sha256_obj(x["genome"]),
                "blueprint_sha256": bpmod.blueprint_sha256(x),
                "formalization_sha256": x["formalization_sha256"],
                "prebuild_destroyer_sha256": x["prebuild_destroyer_sha256"],
                "mechanisms": len(x["mechanisms"]),
                "prebuild_survives": x["prebuild_destroyer"]["survives_prebuild"],
            } for x in props],
            "builder_handoff": "COMPLETE_BLUEPRINT_PLUS_FORMALIZATION_REQUIRED",
            "owner_review_requires": [
                "search forest includes independent and anti-attractor lineages",
                "finalists are structurally distinct by architecture genome",
                "every builder receives complete blueprint plus formalization",
                "prebuild destroyer findings remain attached and are not hidden from builders",
                "no prior CP2 architecture conclusion was visible during search",
            ],
            "asks": "owner approval of the supremacy-search v0 finalist set, not endorsement of any winner",
        })
        return p

    H["TARGET_ARCHITECTURE_v0_REVIEWED"] = v0_reviewed

    def architecture_discovery(_m):
        props = read_json(A(ctx, "architecture", "proposals.json"))["proposals"]
        candidates = []
        for i, prop in enumerate(props, 1):
            candidates.append({
                "id": f"OBS-{i:02d}",
                "family": prop["family"],
                "mechanism": f"complete-blueprint:{bpmod.blueprint_sha256(prop)}",
                "proposal_logical_id": prop["logical_id"],
                "seed_id": prop["seed_id"],
                "lineage_code": prop["lineage_code"],
                "genome_sha256": sha256_obj(prop["genome"]),
                "blueprint_sha256": bpmod.blueprint_sha256(prop),
                "formalization_sha256": prop["formalization_sha256"],
            })
        p = A(ctx, "candidates", "discovery.json")
        atomic_write_json(p, {"candidates": candidates,
                              "prior_cp2_visible": False,
                              "builder_handoff": "COMPLETE_BLUEPRINT_PLUS_FORMALIZATION_REQUIRED"})
        return p

    H["ARCHITECTURE_DISCOVERY"] = architecture_discovery

    def candidate_building(_m):
        props = read_json(A(ctx, "architecture", "proposals.json"))["proposals"]
        by_lid = {x["logical_id"]: x for x in props}
        specs = read_json(A(ctx, "candidates", "discovery.json"))["candidates"]
        built, rejected = [], []
        contract = _profile_text(ctx, "EVALUATOR-CONTRACT.md", 30000)

        for spec in specs:
            prop = by_lid[spec["proposal_logical_id"]]
            bp = bpmod.blueprint(prop)
            bp_sha = bpmod.blueprint_sha256(prop)
            form = prop["formalization"]
            form_sha = sha256_obj(form)
            if bp_sha != spec["blueprint_sha256"] or form_sha != spec["formalization_sha256"]:
                raise RuntimeError(f"{spec['id']}: blueprint/formalization identity changed before build")

            _, obj, _, _ = ctx.ask(
                "implementation-builder", f"OBS-BUILD::{spec['id']}::{bp_sha[:12]}",
                "Implement the faithful semantic kernel of this complete architecture. The formalized "
                "INV-* obligations are binding. Do not optimize merely for the visible evaluator and "
                "do not drop a mechanism because the in-memory contract cannot exercise its deployment "
                "form; preserve its invariant semantics. Return candidate.py implementing every required "
                "operation and register_change_handler(kind, fn).",
                [("COMPLETE ARCHITECTURE BLUEPRINT", json.dumps(bp, ensure_ascii=False)),
                 ("ARCHITECTURE FORMALIZATION", json.dumps(form, ensure_ascii=False)),
                 ("PREBUILD DESTROYER ATTACK PLAN", json.dumps(prop["prebuild_destroyer"], ensure_ascii=False)),
                 ("SEMANTIC EVALUATOR CONTRACT", contract)],
                oroles.BUILD_SCHEMA)
            obj["candidate_id"] = spec["id"]
            obj["family"] = prop["family"]
            obj["mechanism"] = f"complete-blueprint:{bp_sha}"
            ctx.install_candidate(obj, "baseline")
            src = ctx.candidates[spec["id"]]["source"]

            reports = []
            for critic in ("A", "B"):
                _, frep, _, _ = ctx.ask(
                    f"blueprint-fidelity-critic-{critic}",
                    f"OBS-FIDELITY-{critic}::{spec['id']}::{bp_sha[:12]}",
                    "Audit whether candidate.py faithfully implements the formalized architecture "
                    "inside the semantic-kernel contract. Cite invariant IDs. Do not award behavioral "
                    "correctness that belongs to the executable grader; this audit is only blueprint "
                    "fidelity and architectural truncation detection.",
                    [("complete blueprint", json.dumps(bp, ensure_ascii=False)),
                     ("formalization", json.dumps(form, ensure_ascii=False)),
                     ("candidate.py", src[:700000])],
                    oroles.BLUEPRINT_FIDELITY_SCHEMA)
                reports.append(frep)

            common_violations = sorted(
                set(reports[0]["violated_invariant_ids"]) & set(reports[1]["violated_invariant_ids"]))
            consensus_unfaithful = (not reports[0]["faithful"] and not reports[1]["faithful"])
            if common_violations or consensus_unfaithful:
                rejected.append({
                    "candidate_id": spec["id"],
                    "reason": "independent blueprint-fidelity critics agree implementation is truncated",
                    "common_violated_invariants": common_violations,
                    "reports": reports,
                })
                ctx.candidates.pop(spec["id"], None)
                ctx._save_arena()
                continue

            ctx.candidates[spec["id"]].update({
                "seed_id": prop["seed_id"],
                "lineage_code": prop["lineage_code"],
                "genome": prop["genome"],
                "genome_sha256": sha256_obj(prop["genome"]),
                "blueprint_sha256": bp_sha,
                "formalization": form,
                "formalization_sha256": form_sha,
                "blueprint_fidelity_reports": reports,
                "blueprint_fidelity_consensus": True,
            })
            ctx._save_arena()
            built.append({
                "candidate_id": spec["id"],
                "worktree": ctx.candidates[spec["id"]]["worktree"],
                "files_written": ctx.candidates[spec["id"]]["files_written"],
                "compiles": True,
                "family": prop["family"],
                "genome_sha256": sha256_obj(prop["genome"]),
                "blueprint_sha256": bp_sha,
                "formalization_sha256": form_sha,
                "complete_blueprint_handoff": True,
                "formalization_handoff": True,
                "blueprint_fidelity_consensus": True,
            })

        if len(built) < 2:
            raise RuntimeError("fewer than two structurally formalized candidates survived blueprint-fidelity audit")
        p = A(ctx, "candidates", "built.json")
        atomic_write_json(p, {"built": built, "rejected_before_execution": rejected,
                              "complete_blueprint_handoff": True,
                              "formalization_handoff": True})
        return p

    H["CANDIDATE_BUILDING"] = candidate_building
    return H
