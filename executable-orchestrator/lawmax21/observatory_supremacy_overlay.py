"""Supremacy-search overlay for the National Legal Observatory.

Transforms model ideation into a structural search experiment: controlled architecture-genome
classes, independent and anti-attractor lineages, complete-blueprint expansion, invariant
formalization, prebuild destruction and best-of-three measured implementations. Probabilistic
fidelity critics are advisory evidence; only executable measurement may eliminate a build.

Prior CP2 remains invisible throughout this module and is released only after an executable
independent frontier exists.
"""
import json
import os

from . import observatory_roles as oroles
from .canonical import atomic_write_json, read_json, sha256_file, sha256_obj
from .handlers import A
from . import observatory_blueprint_overlay as bpmod


MIN_STRUCTURAL_DISTANCE = 2
MAX_FINALISTS = 18
MIN_FINALISTS = 12
SEEDS_PER_LINEAGE = 6
IMPLEMENTATION_ATTEMPTS = 3

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
     "Content-addressed storage may be used as storage but may NOT be the architectural authority seat or central design abstraction."),
    ("A04", "no-single-logical-writer",
     "Do NOT rely on one logical writer, leader lease or single canonical append process. Preserve one canonical truth through another consistency construction."),
    ("A05", "replicated-commit-first",
     "Start from replicated/BFT or quorum-verified canonical commit under faults; do not reduce the architecture to a single-node system plus replicas."),
    ("A06", "proof-dag-first",
     "Make immutable proof/dependency objects or a proof DAG the principal state representation; do not use a mutable canonical database or ordered ledger as the principal representation."),
    ("A07", "declarative-calculus-first",
     "Make a declarative legal calculus/typed IR and verified compiler/interpreter the architectural center. Storage is subordinate to semantics."),
    ("A08", "minimal-verifier-kernel",
     "Push almost everything outside the trusted boundary. Search for a tiny verifier/admission kernel that rejects invalid legal-state claims produced by untrusted workers."),
    ("A09", "federated-evidence-authorities",
     "Assume multiple independently operated evidence authorities and no central acquisition authority. Produce one canonical public legal truth through deterministic evidence-aware convergence."),
]


def _class(genome, axis):
    x = (genome or {}).get(axis) or {}
    return str(x.get("class") or "") if isinstance(x, dict) else ""


def genome_signature(genome):
    """Only controlled structural classes count toward design-space distance."""
    return tuple(_class(genome, k) for k in oroles.GENOME_FIELDS)


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


def _anti_ok(code, genome):
    seat = _class(genome, "canonical_authority_seat")
    evidence = _class(genome, "evidence_primitive")
    state = _class(genome, "state_derivation_model")
    commit = _class(genome, "consistency_commit_model")
    repl = _class(genome, "replication_distribution_model")
    tcb = _class(genome, "trusted_core_topology")
    effect = _class(genome, "normative_effect_model")
    scale = _class(genome, "scaling_partition_model")
    if code == "A01":
        return seat != "ordered_ledger"
    if code == "A02":
        return state != "replay_reducer"
    if code == "A03":
        return evidence != "content_addressed_object" and seat != "derived_state_root"
    if code == "A04":
        return commit != "single_writer_sequence" and repl != "single_primary_read_replicas"
    if code == "A05":
        return commit in {"consensus_log", "quorum_certificate", "hybrid"} \
            and repl in {"raft_paxos", "bft_consensus", "hybrid"}
    if code == "A06":
        return seat == "proof_dag"
    if code == "A07":
        return seat == "declarative_ir" or state == "verified_compiler" or effect == "compiler_transform"
    if code == "A08":
        return tcb in {"minimal_verifier", "capability_microkernel"}
    if code == "A09":
        return seat == "federated_authority_set" or repl == "federated_witnesses" or scale == "federated_domains"
    return True


def _valid_lineage_candidates(code, mode, obj):
    xs = list(obj.get("candidates", []))
    if mode == "anti-attractor":
        xs = [x for x in xs if _anti_ok(code, x.get("genome") or {})]
    return xs


def _find_cp1(ctx):
    found = []
    for root, _dirs, files in os.walk(ctx.cp1_evidence):
        if "CP1-REPOSITORY-RECONSTRUCTION.md" in files:
            found.append(os.path.join(root, "CP1-REPOSITORY-RECONSTRUCTION.md"))
    if len(found) != 1:
        raise RuntimeError(f"supremacy search expected exactly one CP1 reconstruction, found {len(found)}")
    return found[0]


def _profile_text(ctx, name, limit):
    return open(os.path.join(ctx.profile_pkg, name), encoding="utf-8").read()[:limit]


def _run_lineage(ctx, code, name, directive, mode, common_context):
    role = f"architecture-search-{mode}"
    task = (
        f"Run architecture-search lineage {code}/{name}. Produce exactly {SEEDS_PER_LINEAGE} "
        "mutually incompatible whole-system architecture seeds for the National Legal Observatory. "
        "Use the CONTROLLED genome classes exactly as defined by the response schema: the free-form "
        "detail explains a class but does not create a new structural class. Do not optimize for "
        "familiarity. For every seed expose mechanisms, assumptions, decisive advantages, failure "
        "modes and why it is not already entitled to a higher claim. Reject at least two additional "
        "ideas. The valid candidate set must contain at least four structural clusters differing on "
        "two or more controlled genome axes. You are blind to prior CP2 conclusions. " + directive)
    lid, obj, _, _ = ctx.ask(role, f"OBS-SEARCH-{code}", task, common_context,
                             oroles.SEARCH_LINEAGE_SCHEMA)

    valid = _valid_lineage_candidates(code, mode, obj)
    if len(valid) < 4 or _cluster_count(valid) < 4:
        lid, obj, _, _ = ctx.ask(
            role, f"OBS-SEARCH-{code}-DIVERSITY-REPAIR",
            task + " The first result did not satisfy the mechanically checked anti-attractor/"
            "structural-diversity condition. Replace invalid or near-duplicate seeds; do not rename them.",
            common_context + [("rejected first search", json.dumps(obj, ensure_ascii=False)[:120000])],
            oroles.SEARCH_LINEAGE_SCHEMA)
        valid = _valid_lineage_candidates(code, mode, obj)
    if len(valid) < 4 or _cluster_count(valid) < 4:
        raise RuntimeError(f"{code}: lineage failed mechanical anti-attractor/diversity constraints")

    local_to_global, candidates = {}, []
    for i, seed in enumerate(valid, 1):
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
    return {"logical_id": lid, "lineage": obj["lineage"], "code": code, "name": name,
            "mode": mode, "constraint": directive if mode == "anti-attractor" else None,
            "candidates": candidates, "rejected": obj["rejected"], "finalist_ids": finalists,
            "exhaustion_note": obj["exhaustion_note"], "structural_clusters": _cluster_count(candidates)}


def _select_diverse(lineages):
    all_seeds = [s for line in lineages for s in line["candidates"]]
    by_id = {s["seed_id"]: s for s in all_seeds}
    selected = []
    for line in lineages:
        ordered = list(line["finalist_ids"]) + [s["seed_id"] for s in line["candidates"]]
        for sid in ordered:
            s = by_id.get(sid)
            if s and all(structurally_distinct(s["genome"], x["genome"]) for x in selected):
                selected.append(s); break
        if len(selected) >= MAX_FINALISTS:
            break
    remaining = [s for s in all_seeds if s not in selected]
    while remaining and len(selected) < MAX_FINALISTS:
        scored = []
        for s in remaining:
            minimum = min(genome_distance(s["genome"], x["genome"]) for x in selected) if selected else 99
            scored.append((minimum, s["seed_id"], s))
        scored.sort(key=lambda x: (-x[0], x[1]))
        if scored[0][0] < MIN_STRUCTURAL_DISTANCE:
            break
        pick = scored[0][2]; selected.append(pick); remaining.remove(pick)
    if len(selected) < MIN_FINALISTS:
        raise RuntimeError(f"search forest produced only {len(selected)} controlled-genome finalists; minimum {MIN_FINALISTS}")
    return selected[:MAX_FINALISTS]


def _expand_seed(ctx, seed, common_context):
    lid, proposal, _, _ = ctx.ask(
        "architecture-expander", f"OBS-EXPAND::{seed['seed_id']}",
        "Expand this selected seed into a COMPLETE whole-system Observatory blueprint. Copy every "
        "controlled genome class exactly; detail may become more precise but expansion may not move "
        "the architecture to another class. Cover the Mission-v2 and Supremacy contracts, give "
        "falsifiable predictions and evidence-bounded why_not_higher; do not self-award supremacy.",
        [("selected architecture seed", json.dumps(seed, ensure_ascii=False))] + common_context,
        oroles.PROPOSAL_SCHEMA)
    if genome_signature(proposal["genome"]) != genome_signature(seed["genome"]):
        raise RuntimeError(f"{seed['seed_id']}: expander changed a controlled genome class")
    return {"role": "architecture-expander", "logical_id": lid,
            "seed_id": seed["seed_id"], "lineage_code": seed["lineage_code"], **proposal}


def _formalize(ctx, proposal):
    bp = bpmod.blueprint(proposal); bp_sha = bpmod.blueprint_sha256(proposal)
    lid, form, _, _ = ctx.ask(
        "architecture-formalizer", f"OBS-FORMALIZE::{proposal['seed_id']}::{bp_sha[:12]}",
        "Translate the complete blueprint into explicit invariants and proof obligations. Do not "
        "improve/simplify it here. Every load-bearing requirement needs a stable INV-* identifier, "
        "failure condition and observable so implementations can be checked for truncation.",
        [("complete blueprint", json.dumps(bp, ensure_ascii=False)),
         ("supremacy contract", _profile_text(ctx, "SUPREMACY-CONTRACT.md", 40000)),
         ("evaluator contract", _profile_text(ctx, "EVALUATOR-CONTRACT.md", 30000)),
         ("systems contract", _profile_text(ctx, "SYSTEMS-CONTRACT.md", 30000))],
        oroles.FORMALIZATION_SCHEMA)
    return lid, form


def _destroy_prebuild(ctx, proposal, formalization, forest_summary):
    lid, rep, _, _ = ctx.ask(
        "architecture-destroyer-prebuild", f"OBS-DESTROY-PRE::{proposal['seed_id']}",
        "Try to kill this architecture before implementation. Attack assumptions, trusted boundary, "
        "identity/time/effect semantics, failure model, recovery, scale and publication claims. Name "
        "INV-* IDs where the formalization is inconsistent. This is adversarial evidence, not an "
        "authority to eliminate the design without executable measurement.",
        [("complete blueprint", json.dumps(bpmod.blueprint(proposal), ensure_ascii=False)),
         ("formalization", json.dumps(formalization, ensure_ascii=False)),
         ("search-forest summary", json.dumps(forest_summary, ensure_ascii=False)[:50000])],
        oroles.DESTROYER_SCHEMA)
    return lid, rep


def _visible_score(ctx, candidate_id):
    rec = ctx.measure_visible(candidate_id)
    dims = rec.get("slice_scores") or {}
    total = sum(float(v) for v in dims.values())
    complexity = ctx.obs_harness.source_complexity(ctx.candidates[candidate_id]["source"])
    return (round(total, 9), -float(complexity)), rec


def install(ctx, handlers):
    H = dict(handlers)

    def target_search(_m):
        common = [
            ("National Observatory objective charter", _profile_text(ctx, "OBJECTIVE-CHARTER.md", 40000)),
            ("Supremacy research contract", _profile_text(ctx, "SUPREMACY-CONTRACT.md", 40000)),
            ("sealed CP1 repository reconstruction", open(_find_cp1(ctx), encoding="utf-8").read()[:70000]),
        ]
        lineages = [_run_lineage(ctx, c, n, d, "independent", common) for c, n, d in GENERAL_LINEAGES]
        for code, name, constraint in ANTI_ATTRACTOR_LINEAGES:
            lineages.append(_run_lineage(
                ctx, code, name, "ANTI-ATTRACTOR CONSTRAINT: " + constraint +
                " If impossible, prove why while still searching the closest mission-preserving construction.",
                "anti-attractor", common))
        selected = _select_diverse(lineages)
        forest_summary = {
            "lineages": len(lineages), "general_lineages": len(GENERAL_LINEAGES),
            "anti_attractor_lineages": len(ANTI_ATTRACTOR_LINEAGES),
            "seeds": sum(len(x["candidates"]) for x in lineages),
            "selected_finalists": len(selected), "minimum_structural_distance_fields": MIN_STRUCTURAL_DISTANCE,
            "distance_basis": "controlled_genome_class",
            "selected": [{"seed_id": s["seed_id"], "lineage": s["lineage_code"],
                          "family": s["family"], "genome_sha256": s["genome_sha256"]} for s in selected],
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
            proposal.update({
                "formalization": form, "formalization_logical_id": form_lid,
                "formalization_sha256": sha256_obj(form), "prebuild_destroyer": destroy,
                "prebuild_destroyer_logical_id": destroy_lid,
                "prebuild_destroyer_sha256": sha256_obj(destroy)})
            proposals.append(proposal)
        ctx.esc.declare_families([x["family"] for x in proposals])
        p = A(ctx, "architecture", "proposals.json")
        atomic_write_json(p, {"profile": ctx.profile_id, "prior_cp2_visible": False,
                              "search_mode": "SUPREMACY_SEARCH_FOREST_V1",
                              "search_forest_sha256": sha256_file(forest_path),
                              "structural_finalists": len(proposals), "proposals": proposals})
        return p
    H["TARGET_ARCHITECTURE_SEARCH"] = target_search

    def v0_reviewed(_m):
        proposals_path = A(ctx, "architecture", "proposals.json"); forest_path = A(ctx, "architecture", "search_forest.json")
        artifact = read_json(proposals_path); props = artifact["proposals"]
        for i, a in enumerate(props):
            for b in props[i + 1:]:
                if not structurally_distinct(a["genome"], b["genome"]):
                    raise RuntimeError(f"owner gate refused near-duplicate controlled genomes: {a['seed_id']} / {b['seed_id']}")
        p = A(ctx, "gates", "v0_subject.json")
        atomic_write_json(p, {
            "gate": "GATE-ARCH-V0", "run_id": ctx.run_id,
            "supremacy_contract_sha256": sha256_file(os.path.join(ctx.profile_pkg, "SUPREMACY-CONTRACT.md")),
            "search_forest_sha256": sha256_file(forest_path), "proposals_sha256": sha256_file(proposals_path),
            "search_mode": artifact["search_mode"], "structural_finalists": len(props),
            "blueprints": [{"seed_id": x["seed_id"], "lineage_code": x["lineage_code"],
                            "family": x["family"], "genome_sha256": sha256_obj(x["genome"]),
                            "blueprint_sha256": bpmod.blueprint_sha256(x),
                            "formalization_sha256": x["formalization_sha256"],
                            "prebuild_destroyer_sha256": x["prebuild_destroyer_sha256"],
                            "mechanisms": len(x["mechanisms"])} for x in props],
            "builder_handoff": "COMPLETE_BLUEPRINT_PLUS_FORMALIZATION_REQUIRED",
            "owner_review_requires": ["controlled-genome diversity", "independent + anti-attractor search",
                                      "complete blueprint/formalization handoff", "CP2 still quarantined"],
            "asks": "owner approval of the supremacy-search v0 finalist set, not endorsement of a winner"})
        return p
    H["TARGET_ARCHITECTURE_v0_REVIEWED"] = v0_reviewed

    def architecture_discovery(_m):
        props = read_json(A(ctx, "architecture", "proposals.json"))["proposals"]
        candidates = [{"id": f"OBS-{i:02d}", "family": p["family"],
                       "mechanism": f"complete-blueprint:{bpmod.blueprint_sha256(p)}",
                       "proposal_logical_id": p["logical_id"], "seed_id": p["seed_id"],
                       "lineage_code": p["lineage_code"], "genome_sha256": sha256_obj(p["genome"]),
                       "blueprint_sha256": bpmod.blueprint_sha256(p),
                       "formalization_sha256": p["formalization_sha256"]}
                      for i, p in enumerate(props, 1)]
        p = A(ctx, "candidates", "discovery.json")
        atomic_write_json(p, {"candidates": candidates, "prior_cp2_visible": False,
                              "builder_handoff": "COMPLETE_BLUEPRINT_PLUS_FORMALIZATION_REQUIRED"})
        return p
    H["ARCHITECTURE_DISCOVERY"] = architecture_discovery

    def candidate_building(_m):
        props = read_json(A(ctx, "architecture", "proposals.json"))["proposals"]
        by_lid = {x["logical_id"]: x for x in props}
        specs = read_json(A(ctx, "candidates", "discovery.json"))["candidates"]
        built, build_failures = [], []
        contract = _profile_text(ctx, "EVALUATOR-CONTRACT.md", 30000)
        for spec in specs:
            prop = by_lid[spec["proposal_logical_id"]]; bp = bpmod.blueprint(prop)
            bp_sha = bpmod.blueprint_sha256(prop); form = prop["formalization"]; form_sha = sha256_obj(form)
            if bp_sha != spec["blueprint_sha256"] or form_sha != spec["formalization_sha256"]:
                raise RuntimeError(f"{spec['id']}: blueprint/formalization identity changed before build")

            attempts = []
            for attempt in range(1, IMPLEMENTATION_ATTEMPTS + 1):
                aid = f"{spec['id']}-a{attempt}"
                try:
                    _, obj, _, _ = ctx.ask(
                        "implementation-builder", f"OBS-BUILD::{aid}::{bp_sha[:12]}",
                        f"Implementation attempt {attempt}/{IMPLEMENTATION_ATTEMPTS}. Implement the faithful semantic kernel "
                        "from the COMPLETE blueprint and INV-* formalization. Preserve architecture semantics; "
                        "generalize beyond visible cases; do not hard-code fixtures.",
                        [("COMPLETE ARCHITECTURE BLUEPRINT", json.dumps(bp, ensure_ascii=False)),
                         ("ARCHITECTURE FORMALIZATION", json.dumps(form, ensure_ascii=False)),
                         ("PREBUILD DESTROYER ATTACK PLAN", json.dumps(prop["prebuild_destroyer"], ensure_ascii=False)),
                         ("SEMANTIC EVALUATOR CONTRACT", contract)], oroles.BUILD_SCHEMA)
                    obj["candidate_id"] = aid; obj["family"] = prop["family"]; obj["mechanism"] = f"complete-blueprint:{bp_sha}"
                    ctx.install_candidate(obj, "baseline")
                    score, rec = _visible_score(ctx, aid)
                    attempts.append((score, aid, rec))
                except Exception as exc:
                    build_failures.append({"candidate_id": aid, "reason": str(exc)[:1200]})
            if not attempts:
                build_failures.append({"candidate_id": spec["id"], "reason": "all implementation attempts failed"})
                continue
            attempts.sort(key=lambda x: (x[0][0], x[0][1], x[1]), reverse=True)
            _score, winner, _rec = attempts[0]
            ctx.candidates[spec["id"]] = dict(ctx.candidates[winner])
            source = ctx.candidates[spec["id"]]["source"]
            with open(A(ctx, "candidate-src", f"{spec['id']}.py"), "w", encoding="utf-8") as f:
                f.write(source)
            for _s, aid, _r in attempts:
                ctx.candidates.pop(aid, None)
                ctx.scores.pop(aid, None)

            reports = []
            for critic in ("A", "B"):
                _, frep, _, _ = ctx.ask(
                    f"blueprint-fidelity-critic-{critic}", f"OBS-FIDELITY-{critic}::{spec['id']}::{bp_sha[:12]}",
                    "Audit architectural truncation against the blueprint/formalization and cite INV-* IDs. "
                    "This is advisory evidence only; executable graders decide elimination.",
                    [("complete blueprint", json.dumps(bp, ensure_ascii=False)),
                     ("formalization", json.dumps(form, ensure_ascii=False)), ("candidate.py", source[:700000])],
                    oroles.BLUEPRINT_FIDELITY_SCHEMA)
                reports.append(frep)
            warning = (not reports[0]["faithful"] and not reports[1]["faithful"]) or bool(
                set(reports[0]["violated_invariant_ids"]) & set(reports[1]["violated_invariant_ids"]))
            ctx.candidates[spec["id"]].update({
                "seed_id": prop["seed_id"], "lineage_code": prop["lineage_code"], "genome": prop["genome"],
                "genome_sha256": sha256_obj(prop["genome"]), "blueprint": bp, "blueprint_sha256": bp_sha,
                "formalization": form, "formalization_sha256": form_sha,
                "blueprint_fidelity_reports": reports, "blueprint_fidelity_warning": warning,
                "implementation_attempts": len(attempts)})
            ctx._save_arena()
            built.append({"candidate_id": spec["id"], "worktree": ctx.candidates[spec["id"]]["worktree"],
                          "files_written": ctx.candidates[spec["id"]]["files_written"], "compiles": True,
                          "family": prop["family"], "genome_sha256": sha256_obj(prop["genome"]),
                          "blueprint_sha256": bp_sha, "formalization_sha256": form_sha,
                          "complete_blueprint_handoff": True, "formalization_handoff": True,
                          "implementation_attempts": len(attempts), "blueprint_fidelity_warning": warning})
        if len(built) < 2:
            raise RuntimeError("fewer than two formalized architectures produced executable semantic implementations")
        p = A(ctx, "candidates", "built.json")
        atomic_write_json(p, {"built": built, "build_failures": build_failures,
                              "complete_blueprint_handoff": True, "formalization_handoff": True,
                              "probabilistic_fidelity_is_advisory": True})
        return p
    H["CANDIDATE_BUILDING"] = candidate_building
    return H
