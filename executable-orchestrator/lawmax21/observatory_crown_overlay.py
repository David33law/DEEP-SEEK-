"""Final supremacy/crown overlay for the National Observatory.

This layer records structural search saturation, makes recombination an executable challenger,
ensures all round-created candidates keep complete blueprints/formalizations, and turns the tail
into a second proof campaign: durable systems, lower bounds, independent destroyers and a public
falsifiable supremacy case.
"""
import hashlib
import json
import os
import subprocess
import sys

from . import observatory_roles as oroles
from .canonical import atomic_write_json, read_json, sha256_file, sha256_obj
from .handlers import A
from . import observatory_blueprint_overlay as bpmod
from . import observatory_supremacy_overlay as supmod


def _candidate_design(ctx, cid):
    c = ctx.candidates.get(cid) or {}
    if isinstance(c.get("blueprint"), dict) and isinstance(c.get("formalization"), dict):
        return c["blueprint"], c["formalization"]
    props_path = A(ctx, "architecture", "proposals.json")
    if os.path.exists(props_path):
        for p in read_json(props_path).get("proposals", []):
            if (c.get("seed_id") and p.get("seed_id") == c.get("seed_id")) or \
                    (c.get("blueprint_sha256") and bpmod.blueprint_sha256(p) == c.get("blueprint_sha256")):
                return bpmod.blueprint(p), p.get("formalization") or {}
    raise RuntimeError(f"{cid}: complete blueprint/formalization unavailable")


def _build_round_candidate(ctx, idea, cid, kind, ticket):
    idea = dict(idea)
    idea.setdefault("seed_id", cid)
    idea.setdefault("lineage_code", f"ROUND-{ctx.round}")
    bp = bpmod.blueprint(idea)
    bp_sha = bpmod.blueprint_sha256(idea)
    _form_lid, form = supmod._formalize(ctx, idea)
    _destroy_lid, destroy = supmod._destroy_prebuild(
        ctx, idea, form,
        {"round": ctx.round, "frontier": ctx.frontier.report(), "kind": kind})
    _, obj, _, _ = ctx.ask(
        "implementation-builder", f"OBS-{ticket}-BUILD::{cid}::{bp_sha[:12]}",
        "Implement this complete round-generated architecture from its blueprint and formalization. "
        "Preserve every INV-* obligation that can be represented in the semantic-kernel contract. "
        "Do not hard-code fixtures and do not collapse the architecture into the first mechanism.",
        [("COMPLETE ARCHITECTURE BLUEPRINT", json.dumps(bp, ensure_ascii=False)),
         ("ARCHITECTURE FORMALIZATION", json.dumps(form, ensure_ascii=False)),
         ("PREBUILD DESTROYER", json.dumps(destroy, ensure_ascii=False)),
         ("SEMANTIC EVALUATOR CONTRACT",
          open(os.path.join(ctx.profile_pkg, "EVALUATOR-CONTRACT.md"), encoding="utf-8").read()[:30000])],
        oroles.BUILD_SCHEMA, line="successor")
    obj["candidate_id"] = cid
    obj["family"] = idea["family"]
    obj["mechanism"] = f"complete-blueprint:{bp_sha}"
    ctx.install_candidate(obj, kind)
    ctx.candidates[cid].update({
        "seed_id": cid,
        "lineage_code": f"ROUND-{ctx.round}",
        "genome": idea["genome"],
        "genome_sha256": sha256_obj(idea["genome"]),
        "blueprint": bp,
        "blueprint_sha256": bp_sha,
        "formalization": form,
        "formalization_sha256": sha256_obj(form),
        "prebuild_destroyer": destroy,
    })
    ctx._save_arena()
    return cid


def _frontier_design_context(ctx):
    rows = []
    for cid in sorted(ctx.candidates):
        c = ctx.candidates[cid]
        h = ctx.scores.get(cid, {}).get("hidden_qualification") or {}
        rows.append({
            "candidate_id": cid,
            "family": c.get("family"),
            "kind": c.get("kind"),
            "genome": c.get("genome"),
            "blueprint_sha256": c.get("blueprint_sha256"),
            "dimension_scores": h.get("dimension_scores", {}),
            "layers": ctx.demonstrated_layers(cid, h) if h else [],
        })
    return rows


def _systems_build_and_measure(ctx, winner, bp, form):
    contract = open(os.path.join(ctx.profile_pkg, "SYSTEMS-CONTRACT.md"), encoding="utf-8").read()
    _, obj, _, _ = ctx.ask(
        "durable-systems-builder", f"OBS-SYSTEMS-BUILD::{winner}",
        "Implement systems_candidate.py for the surviving architecture. This is NOT the in-memory "
        "legal-semantic candidate. Implement the architecture's durable persistence/recovery kernel "
        "faithfully under the exact systems contract. Use only the Python standard library; network "
        "and model calls do not exist. Do not fake durability in memory. Return a files array that "
        "contains systems_candidate.py.",
        [("winning complete blueprint", json.dumps(bp, ensure_ascii=False)),
         ("winning formalization", json.dumps(form, ensure_ascii=False)),
         ("durable systems contract", contract)],
        oroles.BUILD_SCHEMA, line="successor")
    files = [f for f in obj.get("files", []) if f.get("path") == "systems_candidate.py"]
    if len(files) != 1:
        raise RuntimeError("durable-systems-builder must return exactly one systems_candidate.py")
    source = files[0]["content"]
    compile(source, f"<systems-{winner}>", "exec")
    cand = A(ctx, "systems-candidate", f"{winner}.py")
    with open(cand, "w", encoding="utf-8") as f:
        f.write(source)
    out = A(ctx, "reports", f"systems-arena-{winner}.json")
    seed = int(hashlib.sha256(f"systems|{ctx.run_id}|{winner}".encode()).hexdigest()[:8], 16)
    r = subprocess.run([
        sys.executable, os.path.join(ctx.evaluator_dir, "observatory_systems_arena.py"),
        "--candidate", cand, "--out", out, "--seed", str(seed), "--large-events", "50000"],
        capture_output=True, text=True)
    if not os.path.exists(out):
        raise RuntimeError("durable systems evaluator produced no report: " + (r.stdout + r.stderr)[-800:])
    rep = read_json(out)
    passed = r.returncode == 0 and rep.get("status") == "PASS" and rep.get("passed") is True
    ctx.esc.record_systems_arena(winner, passed, os.path.relpath(out, ctx.runtime).replace("\\", "/"))
    return rep


def _lower_bounds(ctx, winner, bp, form, systems, holdout):
    perspectives = [
        ("information", "Analyze information-theoretic and observability lower bounds: unknown sources, missing evidence, identity ambiguity and what cannot be inferred without additional observations."),
        ("distributed", "Analyze distributed-systems/computational lower bounds: consistency, partitions, ordering, replication, recovery and verification costs."),
        ("legal-governance", "Analyze legal-evidence and governance lower bounds: authority ambiguity, retroactivity, human resolutions, institutional trust and what additional legal evidence is inherently required."),
    ]
    reports = []
    common = [
        ("winning blueprint", json.dumps(bp, ensure_ascii=False)),
        ("formalization", json.dumps(form, ensure_ascii=False)),
        ("durable systems evidence", json.dumps(systems, ensure_ascii=False)[:50000]),
        ("final holdout", json.dumps(holdout, ensure_ascii=False)[:30000]),
    ]
    for tag, task in perspectives:
        lid, rep, _, _ = ctx.ask(
            f"lower-bound-{tag}", f"OBS-LOWER-BOUND::{winner}::{tag}",
            task + " Distinguish a fundamental limit from unfinished engineering. Any feasible "
            "evidence-supported improvement belongs in attainable_improvements and therefore blocks "
            "a supremacy claim until searched.",
            common, oroles.LOWER_BOUND_SCHEMA, line="successor")
        reports.append({"perspective": tag, "logical_id": lid, "report": rep})
    closed = all(not x["report"]["attainable_improvements"] and not x["report"]["unresolved"]
                 for x in reports)
    return reports, closed


def _final_destroyers(ctx, winner, bp, form, systems, lower, holdout):
    directives = [
        ("legal", "Destroy the finalist through legal-semantic edge cases, evidence ambiguity, temporal effects, jurisprudence linkage, doctrine isolation and silent-loss paths."),
        ("systems", "Destroy the finalist through persistence, crash, corruption, concurrency, partition/replication assumptions, upgrade/recovery and scale claims."),
        ("minimality", "Try to prove the finalist retains unnecessary trusted mechanisms or that a simpler architecture can match it with lower trusted complexity."),
    ]
    common = [
        ("winning blueprint", json.dumps(bp, ensure_ascii=False)),
        ("formalization", json.dumps(form, ensure_ascii=False)),
        ("systems arena", json.dumps(systems, ensure_ascii=False)[:50000]),
        ("lower-bound reports", json.dumps(lower, ensure_ascii=False)[:60000]),
        ("holdout", json.dumps(holdout, ensure_ascii=False)[:30000]),
        ("measured frontier", json.dumps(ctx.frontier.report(), ensure_ascii=False)[:50000]),
    ]
    reports = []
    for tag, task in directives:
        lid, rep, _, _ = ctx.ask(
            f"final-architecture-destroyer-{tag}", f"OBS-FINAL-DESTROY::{winner}::{tag}",
            task + " Do not reward eloquence. A surviving blocking flaw means survives_prebuild=false "
            "even though this is the final, post-measurement attack.",
            common, oroles.DESTROYER_SCHEMA, line="successor")
        reports.append({"destroyer": tag, "logical_id": lid, "report": rep})
    survived = all(x["report"]["survives_prebuild"]
                   and not x["report"]["fatal_flaws"]
                   and not x["report"]["violated_invariant_ids"] for x in reports)
    return reports, survived


def install(ctx, handlers):
    H = dict(handlers)

    original_target_search = H["TARGET_ARCHITECTURE_SEARCH"]
    def target_search(machine):
        p = original_target_search(machine)
        props = read_json(p).get("proposals", [])
        ctx.esc.record_search_wave(
            "initial-supremacy-search-forest",
            [sha256_obj(x.get("genome") or {}) for x in props])
        return p
    H["TARGET_ARCHITECTURE_SEARCH"] = target_search

    # Every completed escalation round is a structural-search wave. Repeated family names do not
    # matter; only previously unseen genome hashes reset saturation.
    original_anti = H["ANTI_SATISFICING_AUDIT"]
    def anti_satisficing(machine):
        genomes = [c.get("genome_sha256") or sha256_obj(c.get("genome") or {})
                   for c in ctx.candidates.values() if c.get("genome")]
        ctx.esc.record_search_wave(f"escalation-round-{ctx.round}", genomes)
        return original_anti(machine)
    H["ANTI_SATISFICING_AUDIT"] = anti_satisficing

    # Successor state now contains both an ordinary bottleneck-breaking successor and an explicit
    # recombination of measured load-bearing parts. Frontier review will measure both.
    def successor_search(_m):
        ceiling_obj = read_json(A(ctx, "architecture", f"ceiling-round{ctx.round}.json"))
        frontier_ctx = _frontier_design_context(ctx)
        made, rejected = [], []

        for kind, role, task in [
            ("successor", "future-scale-critic",
             "Design a whole-system successor that breaks the measured bottleneck while preserving every stronger measured property."),
            ("recombination", "architecture-recombination-architect",
             "Construct a NEW whole-system architecture by recombining only measured load-bearing strengths from different surviving genomes. Resolve incompatibilities explicitly; do not create a bag of features and do not hide increased trusted-kernel complexity."),
        ]:
            _, idea, _, _ = ctx.ask(
                role, f"OBS-{kind.upper()}-IDEA-r{ctx.round}", task,
                [("ceiling analysis", json.dumps(ceiling_obj, ensure_ascii=False)[:30000]),
                 ("measured frontier designs", json.dumps(frontier_ctx, ensure_ascii=False)[:90000]),
                 ("recombination field", json.dumps(ctx.field_for_recombination(), ensure_ascii=False)[:50000])],
                oroles.PROPOSAL_SCHEMA, line="successor")
            cid = f"OBS-{kind.upper()}-R{ctx.round}"
            try:
                _build_round_candidate(ctx, idea, cid, kind, kind.upper())
                made.append(cid)
                ctx.esc.declare_families([idea["family"]])
                if kind == "recombination":
                    ctx.esc.record_recombination(
                        cid, sha256_obj(idea["genome"]), f"candidates/{kind}-round{ctx.round}.json")
            except Exception as exc:
                rejected.append({"candidate_id": cid, "reason": str(exc)[:1200]})
        p = A(ctx, "candidates", f"successor-round{ctx.round}.json")
        atomic_write_json(p, {"candidates": made, "rejected": rejected,
                              "recombination_attempted": True, "round": ctx.round})
        return p
    H["SUCCESSOR_SEARCH"] = successor_search

    def radical_search(_m):
        frontier_ctx = _frontier_design_context(ctx)
        incumbent = ctx.esc.s.get("incumbent")
        inc_genome = (ctx.candidates.get(incumbent) or {}).get("genome") if incumbent else None
        _, idea, _, _ = ctx.ask(
            "radical-architecture-destroyer-builder", f"OBS-RADICAL-IDEA-r{ctx.round}",
            "Design a radical whole-system architecture intended to falsify the current frontier's "
            "shared assumptions. It must differ from the incumbent on at least three load-bearing "
            "genome axes unless you can demonstrate no such mission-preserving architecture exists.",
            [("measured frontier designs", json.dumps(frontier_ctx, ensure_ascii=False)[:90000])],
            oroles.PROPOSAL_SCHEMA, line="successor")
        if inc_genome and supmod.genome_distance(inc_genome, idea["genome"]) < 3:
            _, idea, _, _ = ctx.ask(
                "radical-architecture-destroyer-builder", f"OBS-RADICAL-IDEA-r{ctx.round}-REPAIR",
                "The prior radical was structurally too close to the incumbent. Produce a mission-"
                "preserving architecture that differs on at least three load-bearing genome axes.",
                [("incumbent genome", json.dumps(inc_genome, ensure_ascii=False)),
                 ("rejected radical", json.dumps(idea, ensure_ascii=False)[:50000])],
                oroles.PROPOSAL_SCHEMA, line="successor")
        cid = f"OBS-RADICAL-R{ctx.round}"
        made = False
        reason = ""
        try:
            _build_round_candidate(ctx, idea, cid, "radical", "RADICAL")
            ctx.esc.declare_families([idea["family"]])
            made = True
        except Exception as exc:
            reason = str(exc)[:1200]
        p = A(ctx, "candidates", f"radical-round{ctx.round}.json")
        atomic_write_json(p, {"candidate_id": cid if made else None, "built": made,
                              "reason": reason, "round": ctx.round})
        return p
    H["RADICAL_CHALLENGER_SEARCH"] = radical_search

    def simplification_search(_m):
        frontier_ctx = _frontier_design_context(ctx)
        _, idea, _, _ = ctx.ask(
            "simplification-critic", f"OBS-SIMPLIFY-IDEA-r{ctx.round}",
            "Design the smallest trusted-core whole-system architecture that could match or dominate "
            "the measured frontier. Delete mechanisms aggressively; retain complexity only when a "
            "specific measured invariant requires it.",
            [("measured frontier designs", json.dumps(frontier_ctx, ensure_ascii=False)[:90000])],
            oroles.PROPOSAL_SCHEMA, line="successor")
        cid = f"OBS-SIMPLIFICATION-R{ctx.round}"
        made = False
        reason = ""
        try:
            _build_round_candidate(ctx, idea, cid, "simplification", "SIMPLIFY")
            ctx.esc.declare_families([idea["family"]])
            made = True
        except Exception as exc:
            reason = str(exc)[:1200]
        p = A(ctx, "candidates", f"simplification-round{ctx.round}.json")
        atomic_write_json(p, {"candidate_id": cid if made else None, "built": made,
                              "reason": reason, "round": ctx.round})
        return p
    H["SIMPLIFICATION_CHALLENGE"] = simplification_search

    # Tail: a semantic winner is not yet a national architecture. Build and attack its durable
    # implementation, establish lower bounds, then demand a public falsifiable engineering case.
    def synthesis(_m):
        winner = read_json(A(ctx, "frontier", "hesa_candidate.json"))["candidate_id"]
        bp, form = _candidate_design(ctx, winner)
        holdout = read_json(A(ctx, "reports", "final_holdout.json"))
        systems = _systems_build_and_measure(ctx, winner, bp, form)

        lower, lower_closed = _lower_bounds(ctx, winner, bp, form, systems, holdout)
        lower_path = A(ctx, "architecture", "lower_bounds.json")
        atomic_write_json(lower_path, {"candidate_id": winner, "closed": lower_closed,
                                      "reports": lower})
        ctx.esc.record_lower_bound(
            winner, lower_closed, os.path.relpath(lower_path, ctx.runtime).replace("\\", "/"))

        destroyers, survived = _final_destroyers(ctx, winner, bp, form, systems, lower, holdout)
        destroy_path = A(ctx, "architecture", "final_destroyers.json")
        atomic_write_json(destroy_path, {"candidate_id": winner, "survived": survived,
                                        "reports": destroyers})
        ctx.esc.record_destroyer(
            winner, survived, os.path.relpath(destroy_path, ctx.runtime).replace("\\", "/"))

        search_ready = all(ctx.esc.search_conditions().values())
        mechanical = bool(systems.get("passed") and lower_closed and survived and search_ready)
        _, case, _, _ = ctx.ask(
            "supremacy-case-auditor", f"OBS-SUPREMACY-CASE::{winner}",
            "Produce the public falsifiable engineering case for the finalist. Explain why a "
            "first-principles frontier engineering team would rationally choose it over the measured "
            "alternatives. Do NOT claim Elon Musk/xAI/SpaceX or any third party actually endorses it. "
            "Use EVIDENCE_SUPPORTED_SUPREMACY only if the supplied mechanical evidence closes every "
            "attainable improvement; otherwise use BEST_DISCOVERED_SO_FAR or NOT_SUPPORTED.",
            [("winning blueprint", json.dumps(bp, ensure_ascii=False)),
             ("formalization", json.dumps(form, ensure_ascii=False)),
             ("measured frontier", json.dumps(ctx.frontier.report(), ensure_ascii=False)[:60000]),
             ("systems arena", json.dumps(systems, ensure_ascii=False)[:50000]),
             ("lower bounds", json.dumps(lower, ensure_ascii=False)[:60000]),
             ("final destroyers", json.dumps(destroyers, ensure_ascii=False)[:60000]),
             ("mechanical supremacy prerequisites", json.dumps({
                 "search_ready": search_ready, "systems_passed": systems.get("passed"),
                 "lower_bound_closed": lower_closed, "destroyer_survived": survived}, ensure_ascii=False))],
            oroles.SUPREMACY_CASE_SCHEMA, line="successor")
        supported = mechanical and case["claim_level"] == "EVIDENCE_SUPPORTED_SUPREMACY"
        case_path = A(ctx, "architecture", "SUPREMACY-CASE.json")
        atomic_write_json(case_path, {**case, "mechanically_supported": supported})
        ctx.esc.record_supremacy_case(
            winner, supported, os.path.relpath(case_path, ctx.runtime).replace("\\", "/"),
            third_party_endorsement_claimed=case["third_party_endorsement_claimed"])

        _, classification, _, _ = ctx.ask(
            "verification-critic", "OBS-SYNTHESIS-SUPREMACY",
            "Classify finalist mechanisms using only measured semantic, durable, destroyer and "
            "lower-bound evidence. Useful means load-bearing; decorative means removable without "
            "measured loss; refuted means contradicted by evidence.",
            [("winning blueprint", json.dumps(bp, ensure_ascii=False)),
             ("semantic frontier", json.dumps(ctx.frontier.report(), ensure_ascii=False)[:50000]),
             ("systems arena", json.dumps(systems, ensure_ascii=False)[:50000]),
             ("destroyers", json.dumps(destroyers, ensure_ascii=False)[:50000]),
             ("lower bounds", json.dumps(lower, ensure_ascii=False)[:50000])],
            oroles.SYNTHESIS_SCHEMA, line="successor")
        p = A(ctx, "architecture", "target_v1_evidence_revised.json")
        atomic_write_json(p, {
            **classification,
            "candidate_id": winner,
            "systems_arena": systems,
            "lower_bound_closed": lower_closed,
            "final_destroyer_survived": survived,
            "supremacy_case_sha256": sha256_file(case_path),
            "supremacy_mechanically_supported": supported,
        })
        return p
    H["ARCHITECTURE_EVIDENCE_SYNTHESIS"] = synthesis

    return H
