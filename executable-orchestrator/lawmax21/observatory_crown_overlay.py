"""Supremacy/crown overlay for the National Observatory.

Whole-system admission means both arenas. Every semantic implementation gets a durable systems
implementation, failure-driven durable revisions before first admission, hidden semantic replay and
a Docker fault campaign before it can enter the Pareto frontier. Independent durable replication is
then required without revision. The final HESA receives a larger 50K-event crown campaign plus
lower-bound and destroyer closure.
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

SYSTEMS_REVISIONS = 2
SYSTEMS_QUAL_EVENTS = 5000
SYSTEMS_REPLICATION_EVENTS = 10000
SYSTEMS_CROWN_EVENTS = 50000


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


def _systems_path(ctx, cid):
    return A(ctx, "systems-candidate", f"{cid}.py")


def _extract_systems_source(obj):
    files = [f for f in obj.get("files", []) if f.get("path") == "systems_candidate.py"]
    if len(files) != 1:
        raise RuntimeError("durable systems role must return exactly one systems_candidate.py")
    source = files[0]["content"]
    compile(source, "<systems-candidate>", "exec")
    return source


def _write_systems_source(ctx, cid, source):
    p = _systems_path(ctx, cid)
    with open(p, "w", encoding="utf-8") as f:
        f.write(source)
    ctx.candidates[cid]["systems_source_sha256"] = hashlib.sha256(source.encode("utf-8")).hexdigest()
    ctx.candidates[cid]["systems_candidate_path"] = p
    ctx._save_arena()
    return p


def _build_systems_source(ctx, cid, line="main"):
    bp, form = _candidate_design(ctx, cid)
    contract = open(os.path.join(ctx.profile_pkg, "SYSTEMS-CONTRACT.md"), encoding="utf-8").read()
    _, obj, _, _ = ctx.ask(
        "durable-systems-builder", f"OBS-SYSTEMS-BUILD::{cid}",
        "Implement systems_candidate.py as the durable persistence/recovery kernel of THIS exact "
        "architecture. Do not substitute a generic database design when the blueprint chose another "
        "authority/commit topology. The local arena cannot prove every distributed deployment claim, "
        "but every locally constructible durability invariant must be faithfully implemented. Use only "
        "Python standard library; no network/model exists.",
        [("COMPLETE ARCHITECTURE BLUEPRINT", json.dumps(bp, ensure_ascii=False)),
         ("ARCHITECTURE FORMALIZATION", json.dumps(form, ensure_ascii=False)),
         ("DURABLE SYSTEMS CONTRACT", contract)],
        oroles.BUILD_SCHEMA, line=line)
    source = _extract_systems_source(obj)
    _write_systems_source(ctx, cid, source)
    return source


def _run_systems(ctx, cid, label, events):
    p = _systems_path(ctx, cid)
    if not os.path.exists(p):
        return {"status": "FAIL", "passed": False, "reason": "systems candidate missing"}
    out = A(ctx, "reports", f"systems-{label}-{cid}.json")
    seed = int(hashlib.sha256(f"systems|{label}|{ctx.run_id}|{cid}".encode()).hexdigest()[:8], 16)
    r = subprocess.run([
        sys.executable, os.path.join(ctx.evaluator_dir, "observatory_systems_arena.py"),
        "--candidate", p, "--out", out, "--seed", str(seed), "--large-events", str(events)],
        capture_output=True, text=True)
    if not os.path.exists(out):
        return {"status": "FAIL", "passed": False,
                "reason": "systems evaluator produced no report: " + (r.stdout + r.stderr)[-800:]}
    rep = read_json(out)
    rep["evaluator_returncode"] = r.returncode
    rep["evidence_path"] = os.path.relpath(out, ctx.runtime).replace("\\", "/")
    return rep


def _qualify_systems(ctx, cid, allow_revision=True):
    if not os.path.exists(_systems_path(ctx, cid)):
        try:
            _build_systems_source(ctx, cid, line="main" if ctx.candidates[cid].get("kind") == "baseline" else "successor")
        except Exception as exc:
            rep = {"status": "FAIL", "passed": False, "reason": f"systems build failed: {exc}"}
            ctx.record_score(cid, "systems_qualification", rep)
            return rep
    rep = _run_systems(ctx, cid, "qualification", SYSTEMS_QUAL_EVENTS)
    revisions = []
    if allow_revision:
        bp, form = _candidate_design(ctx, cid)
        contract = open(os.path.join(ctx.profile_pkg, "SYSTEMS-CONTRACT.md"), encoding="utf-8").read()
        for rev in range(1, SYSTEMS_REVISIONS + 1):
            if rep.get("status") == "PASS" and rep.get("passed") is True:
                break
            current = open(_systems_path(ctx, cid), encoding="utf-8").read() if os.path.exists(_systems_path(ctx, cid)) else ""
            try:
                _, obj, _, _ = ctx.ask(
                    "durable-systems-reviser", f"OBS-SYSTEMS-REVISE::{cid}::r{rev}",
                    "Revise systems_candidate.py to fix the EXACT measured durable fault failures. "
                    "Preserve the architecture and formalization; do not replace them with a generic "
                    "reference solution. Return the complete systems_candidate.py.",
                    [("COMPLETE ARCHITECTURE BLUEPRINT", json.dumps(bp, ensure_ascii=False)),
                     ("ARCHITECTURE FORMALIZATION", json.dumps(form, ensure_ascii=False)),
                     ("DURABLE SYSTEMS CONTRACT", contract),
                     ("CURRENT systems_candidate.py", current[:500000]),
                     ("MEASURED DURABLE FAILURE", json.dumps(rep, ensure_ascii=False)[:50000])],
                    oroles.BUILD_SCHEMA, line="successor")
                source = _extract_systems_source(obj); _write_systems_source(ctx, cid, source)
                rep = _run_systems(ctx, cid, f"qualification-rev{rev}", SYSTEMS_QUAL_EVENTS)
                revisions.append({"revision": rev, "passed": rep.get("passed") is True})
            except Exception as exc:
                revisions.append({"revision": rev, "passed": False, "error": str(exc)[:1000]})
    rep["revision_history"] = revisions
    ctx.record_score(cid, "systems_qualification", rep)
    ctx.candidates[cid]["systems_qualified"] = rep.get("status") == "PASS" and rep.get("passed") is True
    ctx._save_arena()
    return rep


def _build_round_candidate(ctx, idea, cid, kind, ticket):
    idea = dict(idea); idea.setdefault("seed_id", cid); idea.setdefault("lineage_code", f"ROUND-{ctx.round}")
    bp = bpmod.blueprint(idea); bp_sha = bpmod.blueprint_sha256(idea)
    _form_lid, form = supmod._formalize(ctx, idea)
    _destroy_lid, destroy = supmod._destroy_prebuild(ctx, idea, form,
        {"round": ctx.round, "frontier": ctx.frontier.report(), "kind": kind})
    _, obj, _, _ = ctx.ask(
        "implementation-builder", f"OBS-{ticket}-BUILD::{cid}::{bp_sha[:12]}",
        "Implement this complete round-generated architecture from blueprint + formalization. Preserve "
        "every representable INV-* obligation; no fixture hard-coding or first-mechanism collapse.",
        [("COMPLETE ARCHITECTURE BLUEPRINT", json.dumps(bp, ensure_ascii=False)),
         ("ARCHITECTURE FORMALIZATION", json.dumps(form, ensure_ascii=False)),
         ("PREBUILD DESTROYER", json.dumps(destroy, ensure_ascii=False)),
         ("SEMANTIC EVALUATOR CONTRACT", open(os.path.join(ctx.profile_pkg, "EVALUATOR-CONTRACT.md"), encoding="utf-8").read()[:30000])],
        oroles.BUILD_SCHEMA, line="successor")
    obj["candidate_id"], obj["family"], obj["mechanism"] = cid, idea["family"], f"complete-blueprint:{bp_sha}"
    ctx.install_candidate(obj, kind)
    ctx.candidates[cid].update({"seed_id": cid, "lineage_code": f"ROUND-{ctx.round}",
        "genome": idea["genome"], "genome_sha256": sha256_obj(idea["genome"]),
        "blueprint": bp, "blueprint_sha256": bp_sha, "formalization": form,
        "formalization_sha256": sha256_obj(form), "prebuild_destroyer": destroy})
    ctx._save_arena()
    try: _build_systems_source(ctx, cid, line="successor")
    except Exception as exc:
        ctx.candidates[cid]["systems_build_error"] = str(exc)[:1200]; ctx._save_arena()
    return cid


def _frontier_design_context(ctx):
    rows = []
    for cid in sorted(ctx.candidates):
        c = ctx.candidates[cid]; h = ctx.scores.get(cid, {}).get("hidden_qualification") or {}
        sq = ctx.scores.get(cid, {}).get("systems_qualification") or {}
        rows.append({"candidate_id": cid, "family": c.get("family"), "kind": c.get("kind"),
                     "genome": c.get("genome"), "blueprint_sha256": c.get("blueprint_sha256"),
                     "dimension_scores": h.get("dimension_scores", {}),
                     "systems_qualified": sq.get("passed") is True,
                     "layers": ctx.demonstrated_layers(cid, h) if h else []})
    return rows


def _lower_bounds(ctx, winner, bp, form, systems, holdout):
    perspectives = [
        ("information", "Analyze information-theoretic/observability lower bounds: unknown sources, missing evidence and identity ambiguity."),
        ("distributed", "Analyze distributed-systems/computational lower bounds: consistency, partitions, ordering, replication and recovery."),
        ("legal-governance", "Analyze legal-evidence/governance lower bounds: authority ambiguity, retroactivity, adjudication and institutional trust."),
    ]
    common = [("winning blueprint", json.dumps(bp, ensure_ascii=False)),
              ("formalization", json.dumps(form, ensure_ascii=False)),
              ("durable systems evidence", json.dumps(systems, ensure_ascii=False)[:60000]),
              ("final holdout", json.dumps(holdout, ensure_ascii=False)[:30000])]
    reports = []
    for tag, task in perspectives:
        lid, rep, _, _ = ctx.ask(f"lower-bound-{tag}", f"OBS-LOWER-BOUND::{winner}::{tag}",
            task + " Distinguish fundamental impossibility from unfinished engineering. Every feasible "
            "improvement belongs in attainable_improvements and blocks supremacy until searched.",
            common, oroles.LOWER_BOUND_SCHEMA, line="successor")
        reports.append({"perspective": tag, "logical_id": lid, "report": rep})
    return reports, all(not x["report"]["attainable_improvements"] and not x["report"]["unresolved"] for x in reports)


def _final_destroyers(ctx, winner, bp, form, systems, lower, holdout):
    directives = [
        ("legal", "Destroy through legal semantics, evidence ambiguity, temporal effects, jurisprudence, doctrine and silent-loss paths."),
        ("systems", "Destroy through persistence, crash, corruption, concurrency, partition/replication, upgrade/recovery and scale."),
        ("minimality", "Prove retained trusted mechanisms unnecessary or show a simpler architecture can match the frontier."),
    ]
    common = [("winning blueprint", json.dumps(bp, ensure_ascii=False)),
              ("formalization", json.dumps(form, ensure_ascii=False)),
              ("systems arena", json.dumps(systems, ensure_ascii=False)[:60000]),
              ("lower-bound reports", json.dumps(lower, ensure_ascii=False)[:60000]),
              ("holdout", json.dumps(holdout, ensure_ascii=False)[:30000]),
              ("measured frontier", json.dumps(ctx.frontier.report(), ensure_ascii=False)[:50000])]
    reports = []
    for tag, task in directives:
        lid, rep, _, _ = ctx.ask(f"final-architecture-destroyer-{tag}", f"OBS-FINAL-DESTROY::{winner}::{tag}",
            task + " Do not reward eloquence; a blocking flaw means survives_prebuild=false.",
            common, oroles.DESTROYER_SCHEMA, line="successor")
        reports.append({"destroyer": tag, "logical_id": lid, "report": rep})
    survived = all(x["report"]["survives_prebuild"] and not x["report"]["fatal_flaws"]
                   and not x["report"]["violated_invariant_ids"] for x in reports)
    return reports, survived


def install(ctx, handlers):
    H = dict(handlers)

    # After semantic construction, create a durable implementation for EVERY architecture.
    original_build = H["CANDIDATE_BUILDING"]
    def candidate_building(machine):
        p = original_build(machine); art = read_json(p); systems = []
        for b in art.get("built", []):
            cid = b["candidate_id"]
            try:
                src = _build_systems_source(ctx, cid, line="main")
                b["systems_candidate_sha256"] = hashlib.sha256(src.encode("utf-8")).hexdigest()
                systems.append({"candidate_id": cid, "built": True})
            except Exception as exc:
                ctx.candidates[cid]["systems_build_error"] = str(exc)[:1200]; ctx._save_arena()
                systems.append({"candidate_id": cid, "built": False, "reason": str(exc)[:1200]})
        art["systems_candidates"] = systems; atomic_write_json(p, art); return p
    H["CANDIDATE_BUILDING"] = candidate_building

    # Run both hidden semantic and durable qualification before frontier admission.
    original_private = H["PRIVATE_QUALIFICATION"]
    def private_qualification(machine):
        p = original_private(machine); art = read_json(p); systems = []
        for cid in sorted(ctx.candidates):
            rep = _qualify_systems(ctx, cid, allow_revision=True)
            systems.append({"candidate_id": cid, "passed": rep.get("passed") is True,
                            "status": rep.get("status"), "revision_history": rep.get("revision_history", []),
                            "evidence_path": rep.get("evidence_path")})
        art["systems_qualification"] = systems; atomic_write_json(p, art); return p
    H["PRIVATE_QUALIFICATION"] = private_qualification

    def provisional(_m):
        rejected = []
        for cid in sorted(ctx.candidates):
            rep = ctx.scores[cid]["hidden_qualification"]
            sq = ctx.scores[cid].get("systems_qualification") or {}
            ctx.screen_axioms(cid, rep)
            if sq.get("status") != "PASS" or sq.get("passed") is not True:
                ctx.esc.record_axiom_violation(cid, "durable_system_integrity",
                                                "candidate failed pre-frontier durable systems qualification")
                rejected.append(cid); continue
            vec = ctx.dimension_vector(cid, rep, ctx.scores[cid].get("fidelity"))
            ctx.frontier.add({"candidate_id": cid, "mechanism": ctx.candidates[cid]["mechanism"],
                              "declared_altitude": ctx.candidates[cid].get("altitude_claimed", "L0"),
                              "dimension_vector": vec,
                              "evidence_refs": ["hidden-semantic-qualification", "durable-systems-qualification"]})
            for lid in ctx.demonstrated_layers(cid, rep):
                ctx.esc.record_altitude_evidence(cid, lid, f"{lid} demonstrated in hidden Observatory replay")
        if not ctx.frontier.non_dominated():
            raise RuntimeError("no whole-system candidate passed both semantic and durable qualification")
        ctx._save_arena(); p = A(ctx, "frontier", f"members-round{ctx.round}.json")
        atomic_write_json(p, {"members": ctx.frontier.report(), "systems_rejected": rejected,
                              "layers_demonstrated": {cid: ctx.demonstrated_layers(cid, ctx.scores[cid]["hidden_qualification"])
                                                      for cid in ctx.candidates}, "profile": ctx.profile_id})
        return p
    H["PROVISIONAL_FRONTIER_MEMBER"] = provisional

    # Structural search waves count only controlled genome hashes.
    original_target_search = H["TARGET_ARCHITECTURE_SEARCH"]
    def target_search(machine):
        p = original_target_search(machine); props = read_json(p).get("proposals", [])
        ctx.esc.record_search_wave("initial-supremacy-search-forest", [sha256_obj(x["genome"]) for x in props]); return p
    H["TARGET_ARCHITECTURE_SEARCH"] = target_search

    original_anti = H["ANTI_SATISFICING_AUDIT"]
    def anti_satisficing(machine):
        genomes = [c.get("genome_sha256") for c in ctx.candidates.values() if c.get("genome_sha256")]
        ctx.esc.record_search_wave(f"escalation-round-{ctx.round}", genomes); return original_anti(machine)
    H["ANTI_SATISFICING_AUDIT"] = anti_satisficing

    def successor_search(_m):
        ceiling = read_json(A(ctx, "architecture", f"ceiling-round{ctx.round}.json")); field = _frontier_design_context(ctx)
        made, rejected = [], []
        for kind, role, task in [
            ("successor", "future-scale-critic", "Break the measured bottleneck while preserving stronger measured properties."),
            ("recombination", "architecture-recombination-architect", "Construct a NEW architecture from measured load-bearing strengths of different genomes; resolve incompatibilities and expose TCB cost.")]:
            _, idea, _, _ = ctx.ask(role, f"OBS-{kind.upper()}-IDEA-r{ctx.round}", task,
                [("ceiling analysis", json.dumps(ceiling, ensure_ascii=False)[:30000]),
                 ("measured frontier designs", json.dumps(field, ensure_ascii=False)[:90000]),
                 ("recombination field", json.dumps(ctx.field_for_recombination(), ensure_ascii=False)[:50000])],
                oroles.PROPOSAL_SCHEMA, line="successor")
            cid = f"OBS-{kind.upper()}-R{ctx.round}"
            try:
                _build_round_candidate(ctx, idea, cid, kind, kind.upper()); made.append(cid); ctx.esc.declare_families([idea["family"]])
                if kind == "recombination": ctx.esc.record_recombination(cid, sha256_obj(idea["genome"]), f"candidates/{kind}-round{ctx.round}.json")
            except Exception as exc: rejected.append({"candidate_id": cid, "reason": str(exc)[:1200]})
        p = A(ctx, "candidates", f"successor-round{ctx.round}.json")
        atomic_write_json(p, {"candidates": made, "rejected": rejected, "recombination_attempted": True, "round": ctx.round}); return p
    H["SUCCESSOR_SEARCH"] = successor_search

    def radical_search(_m):
        field = _frontier_design_context(ctx); incumbent = ctx.esc.s.get("incumbent")
        inc_genome = (ctx.candidates.get(incumbent) or {}).get("genome") if incumbent else None
        _, idea, _, _ = ctx.ask("radical-architecture-destroyer-builder", f"OBS-RADICAL-IDEA-r{ctx.round}",
            "Design a radical mission-preserving architecture differing from the incumbent on at least three CONTROLLED genome classes.",
            [("measured frontier designs", json.dumps(field, ensure_ascii=False)[:90000])], oroles.PROPOSAL_SCHEMA, line="successor")
        if inc_genome and supmod.genome_distance(inc_genome, idea["genome"]) < 3:
            _, idea, _, _ = ctx.ask("radical-architecture-destroyer-builder", f"OBS-RADICAL-IDEA-r{ctx.round}-REPAIR",
                "Prior radical was mechanically too close. Change at least three load-bearing controlled genome classes while preserving mission invariants.",
                [("incumbent genome", json.dumps(inc_genome, ensure_ascii=False)), ("rejected radical", json.dumps(idea, ensure_ascii=False)[:50000])],
                oroles.PROPOSAL_SCHEMA, line="successor")
        cid = f"OBS-RADICAL-R{ctx.round}"; made = False; reason = ""
        try: _build_round_candidate(ctx, idea, cid, "radical", "RADICAL"); ctx.esc.declare_families([idea["family"]]); made = True
        except Exception as exc: reason = str(exc)[:1200]
        p = A(ctx, "candidates", f"radical-round{ctx.round}.json"); atomic_write_json(p, {"candidate_id": cid if made else None, "built": made, "reason": reason}); return p
    H["RADICAL_CHALLENGER_SEARCH"] = radical_search

    def simplification_search(_m):
        _, idea, _, _ = ctx.ask("simplification-critic", f"OBS-SIMPLIFY-IDEA-r{ctx.round}",
            "Design the smallest trusted-core architecture that could match/dominates the measured frontier. Retain complexity only with measured invariant evidence.",
            [("measured frontier designs", json.dumps(_frontier_design_context(ctx), ensure_ascii=False)[:90000])], oroles.PROPOSAL_SCHEMA, line="successor")
        cid = f"OBS-SIMPLIFICATION-R{ctx.round}"; made = False; reason = ""
        try: _build_round_candidate(ctx, idea, cid, "simplification", "SIMPLIFY"); ctx.esc.declare_families([idea["family"]]); made = True
        except Exception as exc: reason = str(exc)[:1200]
        p = A(ctx, "candidates", f"simplification-round{ctx.round}.json"); atomic_write_json(p, {"candidate_id": cid if made else None, "built": made, "reason": reason}); return p
    H["SIMPLIFICATION_CHALLENGE"] = simplification_search

    # New round candidates must pass both arenas before joining the frontier.
    def frontier_review(_m):
        for cid in sorted(ctx.candidates):
            if cid in ctx.frontier.members: continue
            ctx.measure_visible(cid)
            fid = ctx.obs_harness.fidelity(ctx.candidates[cid]["source"], ctx.suite, ctx.backend); ctx.record_score(cid, "fidelity", fid)
            rep = ctx.measure_hidden(cid, "qualification"); ctx.record_score(cid, "hidden_qualification", rep)
            sq = _qualify_systems(ctx, cid, allow_revision=True)
            ctx.screen_axioms(cid, rep)
            if sq.get("status") != "PASS" or sq.get("passed") is not True:
                ctx.esc.record_axiom_violation(cid, "durable_system_integrity", "round candidate failed durable qualification"); continue
            vec = ctx.dimension_vector(cid, rep, fid)
            ctx.frontier.add({"candidate_id": cid, "mechanism": ctx.candidates[cid]["mechanism"], "declared_altitude": "L0",
                              "dimension_vector": vec, "evidence_refs": [f"semantic+systems-round{ctx.round}"]})
            for lid in ctx.demonstrated_layers(cid, rep): ctx.esc.record_altitude_evidence(cid, lid, f"{lid} demonstrated round {ctx.round}")
        active = ctx.frontier.non_dominated(); below = [cid for cid in active if ctx.esc.below_floor(ctx.frontier.members[cid]["dimension_vector"].get(ctx.profile.primary_dimension, 0.0))]
        advancing = [cid for cid in active if cid not in below]; to_shards = advancing or active
        if not to_shards: raise RuntimeError("no whole-system candidate survives frontier review")
        p = A(ctx, "frontier", f"review-round{ctx.round}.json"); report = ctx.frontier.report()
        atomic_write_json(p, {"statuses": {k: v["status"] for k, v in report.items()}, "to_private_shards": to_shards,
                              "cut_below_floor": below, "floor": ctx.esc.s.get("floor"),
                              "dominated": [k for k, v in report.items() if v["status"] != "ACTIVE"]}); return p
    H["FRONTIER_REVIEW"] = frontier_review

    original_replication = H["PRIVATE_REPLICATION"]
    def private_replication(machine):
        p = original_replication(machine); art = read_json(p); systems = []
        for cid in list(art.get("finalists") or []):
            rep = _run_systems(ctx, cid, "replication", SYSTEMS_REPLICATION_EVENTS)
            ok = rep.get("status") == "PASS" and rep.get("passed") is True
            systems.append({"candidate_id": cid, "passed": ok, "evidence_path": rep.get("evidence_path")})
            if not ok and cid in ctx.frontier.members:
                ctx.frontier.members[cid]["status"] = "REJECTED_SYSTEMS_REPLICATION"
                ctx.frontier.members[cid]["reason"] = "durable systems replication failed"
                ctx.esc.record_axiom_violation(cid, "durable_system_integrity", "failed independent systems replication")
        if not ctx.frontier.non_dominated(): raise RuntimeError("all finalists failed independent durable systems replication")
        ctx._save_arena(); art["systems_replication"] = systems; atomic_write_json(p, art); return p
    H["PRIVATE_REPLICATION"] = private_replication

    # Crown tail re-runs durable arena at larger history against the already-qualified architecture.
    def synthesis(_m):
        winner = read_json(A(ctx, "frontier", "hesa_candidate.json"))["candidate_id"]; bp, form = _candidate_design(ctx, winner)
        holdout = read_json(A(ctx, "reports", "final_holdout.json")); systems = _run_systems(ctx, winner, "crown", SYSTEMS_CROWN_EVENTS)
        systems_ok = systems.get("status") == "PASS" and systems.get("passed") is True
        ctx.esc.record_systems_arena(winner, systems_ok, systems.get("evidence_path", "systems-crown"))
        lower, lower_closed = _lower_bounds(ctx, winner, bp, form, systems, holdout)
        lp = A(ctx, "architecture", "lower_bounds.json"); atomic_write_json(lp, {"candidate_id": winner, "closed": lower_closed, "reports": lower})
        ctx.esc.record_lower_bound(winner, lower_closed, os.path.relpath(lp, ctx.runtime).replace("\\", "/"))
        destroyers, survived = _final_destroyers(ctx, winner, bp, form, systems, lower, holdout)
        dp = A(ctx, "architecture", "final_destroyers.json"); atomic_write_json(dp, {"candidate_id": winner, "survived": survived, "reports": destroyers})
        ctx.esc.record_destroyer(winner, survived, os.path.relpath(dp, ctx.runtime).replace("\\", "/"))
        search_ready = all(ctx.esc.search_conditions().values()); mechanical = bool(systems_ok and lower_closed and survived and search_ready)
        _, case, _, _ = ctx.ask("supremacy-case-auditor", f"OBS-SUPREMACY-CASE::{winner}",
            "Produce the public falsifiable engineering case. Explain why a first-principles frontier team would rationally choose the finalist over measured alternatives. Never claim actual Elon Musk/xAI/SpaceX endorsement. Use EVIDENCE_SUPPORTED_SUPREMACY only if every supplied mechanical prerequisite closes.",
            [("winning blueprint", json.dumps(bp, ensure_ascii=False)), ("formalization", json.dumps(form, ensure_ascii=False)),
             ("measured frontier", json.dumps(ctx.frontier.report(), ensure_ascii=False)[:60000]),
             ("systems arena", json.dumps(systems, ensure_ascii=False)[:60000]), ("lower bounds", json.dumps(lower, ensure_ascii=False)[:60000]),
             ("final destroyers", json.dumps(destroyers, ensure_ascii=False)[:60000]),
             ("mechanical prerequisites", json.dumps({"search_ready": search_ready, "systems_passed": systems_ok, "lower_bound_closed": lower_closed, "destroyer_survived": survived}))],
            oroles.SUPREMACY_CASE_SCHEMA, line="successor")
        supported = mechanical and case["claim_level"] == "EVIDENCE_SUPPORTED_SUPREMACY"
        cp = A(ctx, "architecture", "SUPREMACY-CASE.json"); atomic_write_json(cp, {**case, "mechanically_supported": supported})
        ctx.esc.record_supremacy_case(winner, supported, os.path.relpath(cp, ctx.runtime).replace("\\", "/"), case["third_party_endorsement_claimed"])
        _, classification, _, _ = ctx.ask("verification-critic", "OBS-SYNTHESIS-SUPREMACY",
            "Classify mechanisms using measured semantic, durable, destroyer and lower-bound evidence only.",
            [("winning blueprint", json.dumps(bp, ensure_ascii=False)), ("semantic frontier", json.dumps(ctx.frontier.report(), ensure_ascii=False)[:50000]),
             ("systems arena", json.dumps(systems, ensure_ascii=False)[:60000]), ("destroyers", json.dumps(destroyers, ensure_ascii=False)[:50000]),
             ("lower bounds", json.dumps(lower, ensure_ascii=False)[:50000])], oroles.SYNTHESIS_SCHEMA, line="successor")
        p = A(ctx, "architecture", "target_v1_evidence_revised.json")
        atomic_write_json(p, {**classification, "candidate_id": winner, "systems_arena": systems,
                              "lower_bound_closed": lower_closed, "final_destroyer_survived": survived,
                              "supremacy_case_sha256": sha256_file(cp), "supremacy_mechanically_supported": supported}); return p
    H["ARCHITECTURE_EVIDENCE_SYNTHESIS"] = synthesis
    return H
