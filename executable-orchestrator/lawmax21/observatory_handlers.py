"""Handler overlay for the National Legal Observatory profile.

The shared state machine remains untouched. This module replaces only states whose semantics are
LAWMAX/case-risk specific. Generic package validation, attestation, owner gates, signed-log audit
and terminal writing remain the original handlers.
"""
import json
import os
import subprocess
import sys

from . import roles
from .canonical import atomic_write_json, read_json, sha256_file, utc
from .handlers import A, tree_hash


def _find_one(root, name, contains=None):
    found = []
    for r, _ds, fs in os.walk(root):
        if name in fs:
            p = os.path.join(r, name)
            if contains is None or contains.lower() in p.lower():
                found.append(p)
    if len(found) != 1:
        raise RuntimeError(f"expected exactly one {name!r} under {root}, found {len(found)}")
    return found[0]


def _cp1_material(ctx):
    receipt = os.path.join(ctx.cp1_evidence, "SEALED-VERIFICATION-RECEIPT.json")
    if not os.path.exists(receipt):
        raise RuntimeError(f"sealed CP1 verification receipt missing: {receipt}")
    cp1 = _find_one(ctx.cp1_evidence, "CP1-REPOSITORY-RECONSTRUCTION.md")
    return receipt, cp1


def _profile_baseline(ctx):
    return read_json(os.path.join(ctx.profile_pkg, "TARGET-BASELINE.json"))


def _git_identity(repo):
    def g(*args):
        r = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"git {' '.join(args)} failed: {r.stderr.strip()[:500]}")
        return r.stdout.strip()
    return g("rev-parse", "HEAD"), g("rev-parse", "HEAD^{tree}"), g("status", "--porcelain"), g("remote")


def _profile_files(ctx):
    out = []
    for r, ds, fs in os.walk(ctx.profile_pkg):
        ds[:] = [d for d in ds if d != "__pycache__"]
        for f in sorted(fs):
            p = os.path.join(r, f)
            out.append((os.path.relpath(p, ctx.profile_pkg).replace("\\", "/"), p))
    return out


def _cp1_excerpt(cp1_path, limit=70000):
    text = open(cp1_path, encoding="utf-8").read()
    return text[:limit]


def _prior_cp2_summary(ctx):
    """Read prior CP2 only after the new frontier exists. Caller placement enforces quarantine."""
    manifest = _find_one(ctx.prior_cp2, "RUN-MANIFEST.json", contains="CP2-CORRECTION")
    run = read_json(manifest)
    adjud = _find_one(ctx.prior_cp2, "CP2-CORRECTIVE-ADJUDICATION.md")
    return {"manifest": run,
            "adjudication_excerpt": open(adjud, encoding="utf-8").read()[:35000],
            "source": os.path.relpath(manifest, ctx.prior_cp2).replace("\\", "/")}


def build_observatory_handlers(ctx, base):
    H = dict(base)

    # ---------------------------------------------------------------- evidence / reused CP1
    def evidence_vault(_m):
        receipt, cp1 = _cp1_material(ctx)
        baseline = _profile_baseline(ctx)
        sources = {
            "canonical-target": ctx.canonical_repo,
            "sealed-cp1-reconstruction": cp1,
            "sealed-verification-receipt": receipt,
            "observatory-profile-contract": ctx.profile_pkg,
            "visible-replay-suite": ctx.suite_path,
            "hidden-bank-commitment": os.path.join(ctx.bank_dir, "PUBLIC-commitment.json"),
            "profile-evaluator": os.path.join(ctx.evaluator_dir, "observatory_evaluate.py"),
            "quarantined-prior-cp2": ctx.prior_cp2,
        }
        missing = [name for name, path in sources.items() if not os.path.exists(path)]
        if missing:
            raise RuntimeError("Observatory evidence inputs missing: " + ", ".join(missing))
        sizes = {}
        total = 0
        for name, path in sources.items():
            if os.path.isdir(path):
                n = b = 0
                for r, _ds, fs in os.walk(path):
                    for f in fs:
                        try:
                            b += os.path.getsize(os.path.join(r, f)); n += 1
                        except OSError:
                            pass
            else:
                b, n = os.path.getsize(path), 1
            sizes[name] = {"bytes": b, "files": n}; total += b
        p = A(ctx, "reports", "evidence_vault.json")
        atomic_write_json(p, {"required_sources": sorted(sources), "present": sorted(sources),
                              "missing": [], "sizes": sizes, "total_bytes": total,
                              "target_commit": baseline["target_commit"],
                              "prior_cp2_visibility": baseline["prior_cp2"]["visibility"]})
        return p
    H["EVIDENCE_VAULT_CERTIFIED"] = evidence_vault

    def charter(_m):
        files = _profile_files(ctx)
        p = A(ctx, "audit", "charter_freeze.json")
        atomic_write_json(p, {"vision_status": "EVIDENCE_BACKED",
                              "profile": ctx.profile_id,
                              "frozen_files": [rel for rel, _ in files],
                              "charter_sha256": sha256_file(ctx.profile.charter_path(ctx.root)),
                              "profile_tree_sha256": tree_hash(ctx.profile_pkg), "utc": utc(),
                              "note": "Observatory objective frozen before architecture search"})
        return p
    H["CHARTER_FROZEN"] = charter

    def hidden_commit(_m):
        pub = read_json(os.path.join(ctx.bank_dir, "PUBLIC-commitment.json"))
        frozen = read_json(os.path.join(ctx.bank_dir, "GRADER-FREEZE.json"))["frozen_at_build"]
        if pub.get("profile") != "national-observatory":
            raise RuntimeError("hidden bank has wrong profile")
        import observatory_canaries
        p = A(ctx, "audit", "hidden_commitment.json")
        atomic_write_json(p, {"merkle_root": pub["merkle_root"], "counts": pub["counts"],
                              "grader_freeze": frozen,
                              "canaries": sorted(observatory_canaries.CANARIES),
                              "disclosed": pub["discloses"], "profile": ctx.profile_id})
        return p
    H["HIDDEN_BANK_COMMITTED"] = hidden_commit

    def reconstructed(_m):
        receipt_p, cp1_p = _cp1_material(ctx)
        baseline = _profile_baseline(ctx)
        receipt = read_json(receipt_p)
        head, tree, dirty, remotes = _git_identity(ctx.canonical_repo)
        expected_commit, expected_tree = baseline["target_commit"], baseline["target_tree"]
        if head != expected_commit or tree != expected_tree or dirty or remotes:
            raise RuntimeError("canonical target is not the exact isolated CP1 baseline")
        st = receipt.get("source_target", {})
        if st.get("commit") != expected_commit or st.get("tree") != expected_tree:
            raise RuntimeError("sealed CP1 receipt does not bind the target commit/tree")
        p = A(ctx, "reality", "REPOSITORY-REALITY-MODEL.json")
        atomic_write_json(p, {"items": [
            {"path": "TARGET-GIT-IDENTITY", "status": "EXACT_ISOLATED_BASELINE",
             "evidence": f"commit={head};tree={tree};dirty=0;remotes=0"},
            {"path": "SEALED-CP1-REPOSITORY-RECONSTRUCTION", "status": "REUSED_VERIFIED_CP1",
             "evidence": f"sha256={sha256_file(cp1_p)};receipt={sha256_file(receipt_p)}"}],
            "unknown": [{"note": "all CP1 unknowns remain exactly as recorded in the sealed CP1 map",
                         "source": os.path.basename(cp1_p)}],
            "profile": ctx.profile_id, "repository_archaeology_api_calls": 0,
            "cp1_path": cp1_p, "cp1_sha256": sha256_file(cp1_p)})
        return p
    H["REPOSITORY_RECONSTRUCTED"] = reconstructed

    def history(_m):
        receipt_p, cp1_p = _cp1_material(ctx)
        # No prior CP2 bytes or conclusions are opened here. That evidence is quarantined until
        # CEILING_ANALYSIS, after a new measured frontier already exists.
        p = A(ctx, "reality", "HISTORICAL-EXPERIMENT-MAP.json")
        atomic_write_json(p, {"studies": [
            {"id": "sealed-cp1", "visibility": "OPEN", "source": sha256_file(cp1_p)},
            {"id": "target-git-identity", "visibility": "OPEN", "source": ctx.canonical_repo},
            {"id": "prior-architecture-research", "visibility": "SEALED_QUARANTINED",
             "source": "content intentionally undisclosed until a new frontier exists"}],
            "lessons": [
                {"lesson": "reuse the verified repository reconstruction rather than pay to reread unchanged bytes",
                 "source": "sealed-cp1"},
                {"lesson": "architecture search is bound to an exact commit/tree and isolated checkout",
                 "source": "target-git-identity"},
                {"lesson": "prior architecture conclusions cannot seed independent Observatory discovery",
                 "source": "profile blindness rule"}],
            "prior_cp2_content_read": False, "receipt_sha256": sha256_file(receipt_p)})
        return p
    H["HISTORICAL_EVIDENCE_SYNTHESIZED"] = history

    def cp1_certified(_m):
        reality = read_json(A(ctx, "reality", "REPOSITORY-REALITY-MODEL.json"))
        p = A(ctx, "reports", "coverage_report.json")
        atomic_write_json(p, {"certified": True, "chunks_required": 1, "chunks_ingested": 1,
                              "uningested_count": 0, "verified_citations": 2,
                              "mode": "REUSED_SEALED_CP1",
                              "cp1_sha256": reality["cp1_sha256"],
                              "note": "No new full-reading claim: this gate certifies exact reuse of the already completed CP1 map."})
        return p
    H["GLOBAL_LAWMAX_MODEL_CERTIFIED"] = cp1_certified

    # ---------------------------------------------------------------- independent architecture search
    def target_search(_m):
        charter_text = open(ctx.profile.charter_path(ctx.root), encoding="utf-8").read()
        _receipt, cp1_p = _cp1_material(ctx)
        cp1 = _cp1_excerpt(cp1_p)
        proposals = []
        for role in ("architecture-explorer-A", "architecture-explorer-B", "architecture-explorer-C"):
            lid, obj, _, _ = ctx.ask(
                role, "OBSERVATORY-ARCH-PROPOSAL",
                "Propose a COMPLETE whole-system architecture for the National Legal Observatory. "
                "Cover source evidence, canonical identity, bitemporal state, normative effects, "
                "change detection, jurisprudence-version links, doctrine typing, provenance, "
                "unknown/conflict handling, publication, replay/recovery and governance. You are "
                "blind to prior CP2 architecture conclusions. Choose a genuinely distinct family; "
                "why_not_higher must name the evidence that stops you proposing a higher family.",
                [("National Observatory charter", charter_text[:40000]),
                 ("sealed CP1 reconstruction", cp1)], roles.PROPOSAL_SCHEMA)
            proposals.append({"role": role, "logical_id": lid, **obj})
        ctx.esc.declare_families([x["family"] for x in proposals])
        p = A(ctx, "architecture", "proposals.json")
        atomic_write_json(p, {"profile": ctx.profile_id, "prior_cp2_visible": False,
                              "proposals": proposals})
        return p
    H["TARGET_ARCHITECTURE_SEARCH"] = target_search

    def eval_params(_m):
        p = A(ctx, "audit", "eval_params_freeze.json")
        atomic_write_json(p, {"profile": ctx.profile_id,
                              "pareto_dims_sha256": sha256_file(ctx.profile.pareto_path(ctx.root)),
                              "thresholds": ctx.decisions.thresholds,
                              "suite_sha256": sha256_file(ctx.suite_path),
                              "hidden_merkle_root": read_json(A(ctx, "audit", "hidden_commitment.json"))["merkle_root"]})
        return p
    H["EVALUATION_PARAMETERS_FROZEN"] = eval_params

    def substrate_build(_m):
        p = A(ctx, "substrate", "build_log.json")
        atomic_write_json(p, {"substrate": "shared CandidateHost isolation + Observatory executable contract",
                              "candidate_mode": ctx.profile.candidate_mode, "utc": utc()})
        return p
    H["SUBSTRATE_BUILDING"] = substrate_build

    def substrate_cert(_m):
        ref_p = os.path.join(ctx.root, "benchmark", "observatory_reference_candidate.py")
        if not os.path.exists(ref_p):
            raise RuntimeError("Observatory reference candidate missing")
        ref = open(ref_p, encoding="utf-8").read()
        rep = ctx.obs_harness.run_suite(ref, ctx.suite, ctx.backend)
        dims = rep.get("dimension_scores", {})
        hard = read_json(ctx.profile.pareto_path(ctx.root))
        bad = [d["id"] for d in hard if d.get("hard_minimum") is not None
               and ((d["direction"] == "higher" and float(dims.get(d["id"], 0)) < d["hard_minimum"])
                    or (d["direction"] == "lower" and float(dims.get(d["id"], 9999)) > d["hard_minimum"]))]
        p = A(ctx, "reports", "substrate_visible_report.json")
        atomic_write_json(p, {"all_pass": not bad, "cases": len(ctx.suite.get("scenarios", [])),
                              "slice_scores": dims, "failed_hard_dimensions": bad,
                              "profile": ctx.profile_id})
        return p
    H["SUBSTRATE_CERTIFIED"] = substrate_cert

    def architecture_discovery(_m):
        props = read_json(A(ctx, "architecture", "proposals.json"))["proposals"]
        candidates = []
        for i, prop in enumerate(props, 1):
            mechanism = prop.get("mechanisms", [prop.get("family", "whole-system")])[0]
            candidates.append({"id": f"OBS-{i:02d}", "family": prop["family"],
                               "mechanism": mechanism,
                               "proposal_logical_id": prop["logical_id"]})
        p = A(ctx, "candidates", "discovery.json")
        atomic_write_json(p, {"candidates": candidates, "prior_cp2_visible": False})
        return p
    H["ARCHITECTURE_DISCOVERY"] = architecture_discovery

    def _build_candidate(spec, kind="baseline", ticket="BUILD"):
        cid, family, mechanism = spec["id"], spec["family"], spec["mechanism"]
        contract = open(os.path.join(ctx.profile_pkg, "EVALUATOR-CONTRACT.md"), encoding="utf-8").read()
        _, obj, _, _ = ctx.ask(
            "builder", f"{ticket}::{cid}::r{ctx.round}",
            f"Implement whole-system Observatory candidate {cid}, family {family!r}, architecture "
            f"mechanism {mechanism!r}. Return candidate.py implementing ALL required operations "
            "and `register_change_handler(kind, fn)` as a real runtime extension registry. The "
            "prototype runs without filesystem/network/model access; trusted semantics must be "
            "deterministic. Do not implement a detect(case,draft) detector — the evaluator owns "
            "the adapter. Generalise over ids, dates, text and event kinds; hard-coded fixtures are disqualifying.",
            [("Observatory executable contract", contract[:30000]),
             ("public schema hint", json.dumps({"required_operations": ctx.profile.target.REQUIRED_OPERATIONS,
                                                "time_dimensions": ["legal_time", "knowledge_time"]}))],
            roles.BUILD_SCHEMA, line="successor" if kind != "baseline" else "main")
        obj["candidate_id"], obj["family"], obj["mechanism"] = cid, family, mechanism
        ctx.install_candidate(obj, kind)
        return obj

    def candidate_building(_m):
        specs = read_json(A(ctx, "candidates", "discovery.json"))["candidates"]
        built = []
        for spec in specs:
            obj = _build_candidate(spec)
            built.append({"candidate_id": spec["id"], "worktree": ctx.candidates[spec["id"]]["worktree"],
                          "files_written": ctx.candidates[spec["id"]]["files_written"], "compiles": True,
                          "family": obj["family"], "mechanism": obj["mechanism"]})
        p = A(ctx, "candidates", "built.json")
        atomic_write_json(p, {"built": built})
        return p
    H["CANDIDATE_BUILDING"] = candidate_building

    # ---------------------------------------------------------------- measurement / frontier
    def visible(_m):
        results = []
        for cid in sorted(ctx.candidates):
            rec = ctx.measure_visible(cid)
            results.append({"candidate_id": cid, "slice_scores": rec["slice_scores"],
                            "macro_f1": rec["macro_f1"], "diagnostic_classes": rec["classes"]})
        p = A(ctx, "reports", f"visible-round{ctx.round}.json")
        atomic_write_json(p, {"results": results, "profile": ctx.profile_id})
        return p
    H["VISIBLE_CERTIFIED"] = visible

    def fidelity(_m):
        out, contenders, killed = [], [], []
        for cid in sorted(ctx.candidates):
            rep = ctx.obs_harness.fidelity(ctx.candidates[cid]["source"], ctx.suite, ctx.backend)
            ctx.record_score(cid, "fidelity", rep)
            cheating = bool(rep.get("visible_literal_matches"))
            salvageable = not cheating and rep.get("mechanism_exercised", False)
            if cheating:
                killed.append(cid)
            if salvageable:
                contenders.append(cid)
            out.append({"candidate_id": cid,
                        "hardcoded_answer_scan": "FAIL" if cheating else "CLEAN",
                        "salvageable": salvageable,
                        "mechanism_exercised": bool(rep.get("mechanism_exercised")),
                        "load_bearing_slices": rep.get("load_bearing_slices", []),
                        "ablation_drop": rep.get("ablation_drop", 0.0)})
        for cid in killed:
            ctx.candidates.pop(cid, None)
        if not contenders:
            raise RuntimeError("no Observatory candidate demonstrated a causal load-bearing mechanism")
        ctx._save_arena()
        p = A(ctx, "reports", f"fidelity-round{ctx.round}.json")
        atomic_write_json(p, {"results": out, "kept_as_contenders": contenders,
                              "killed_for_cheating": killed})
        return p
    H["FIDELITY_CERTIFIED"] = fidelity

    def private_qualification(_m):
        results, canaries_ok = [], True
        for cid in sorted(ctx.candidates):
            rep = ctx.measure_hidden(cid, "qualification")
            ctx.record_score(cid, "hidden_qualification", rep)
            cs = rep.get("canaries", [])
            canaries_ok = canaries_ok and isinstance(cs, list) and all(x.get("verdict") == "DENIED" for x in cs)
            results.append({"candidate_id": cid, "diagnostic_classes": rep.get("diagnostic_classes", {}),
                            "slice_scores": rep.get("dimension_scores", {})})
        p = A(ctx, "reports", f"private-qualification-round{ctx.round}.json")
        atomic_write_json(p, {"results": results, "canaries_all_denied": canaries_ok,
                              "isolation_backend": ctx.backend, "profile": ctx.profile_id})
        return p
    H["PRIVATE_QUALIFICATION"] = private_qualification

    def provisional(_m):
        for cid in sorted(ctx.candidates):
            rep = ctx.scores[cid]["hidden_qualification"]
            vec = ctx.dimension_vector(cid, rep, ctx.scores[cid].get("fidelity"))
            ctx.frontier.add({"candidate_id": cid, "mechanism": ctx.candidates[cid]["mechanism"],
                              "declared_altitude": ctx.candidates[cid].get("altitude_claimed", "L0"),
                              "dimension_vector": vec,
                              "evidence_refs": [f"observatory-hidden-qualification-round{ctx.round}"]})
            for lid in ctx.demonstrated_layers(cid, rep):
                ctx.esc.record_altitude_evidence(cid, lid, f"{lid} demonstrated in hidden Observatory replay")
            ctx.screen_axioms(cid, rep)
        ctx._save_arena()
        p = A(ctx, "frontier", f"members-round{ctx.round}.json")
        atomic_write_json(p, {"members": ctx.frontier.report(),
                              "layers_demonstrated": {cid: ctx.demonstrated_layers(
                                  cid, ctx.scores[cid]["hidden_qualification"]) for cid in ctx.candidates},
                              "profile": ctx.profile_id})
        return p
    H["PROVISIONAL_FRONTIER_MEMBER"] = provisional

    # ---------------------------------------------------------------- first point where old CP2 may be opened
    def ceiling(_m):
        frontier = ctx.frontier.report()
        prior = _prior_cp2_summary(ctx)
        _, obj, _, _ = ctx.ask(
            "adversarial-architecture-critic", f"OBS-CEILING-r{ctx.round}",
            "The independent Observatory frontier already exists. Only now compare it against the "
            "quarantined earlier CP2 research. Identify what the CURRENT frontier cannot do, its "
            "binding bottleneck, and architecture families still untried. Prior CP2 is evidence "
            "for missed families, never a preselected answer.",
            [("measured Observatory frontier", json.dumps(frontier, ensure_ascii=False)[:50000]),
             ("quarantined prior CP2, now released for adversarial comparison",
              json.dumps(prior, ensure_ascii=False)[:45000])], roles.CEILING_SCHEMA)
        ctx.esc.declare_families(obj.get("candidate_families_untried", []))
        p = A(ctx, "architecture", f"ceiling-round{ctx.round}.json")
        atomic_write_json(p, obj)
        return p
    H["CEILING_ANALYSIS"] = ceiling

    def challenger(kind, role, ticket, directive):
        def run(_m):
            ceiling_obj = read_json(A(ctx, "architecture", f"ceiling-round{ctx.round}.json"))
            untried = ctx.esc.untried_families()
            _, idea, _, _ = ctx.ask(
                role, f"OBS-{ticket}-IDEA-r{ctx.round}", directive,
                [("ceiling analysis", json.dumps(ceiling_obj, ensure_ascii=False)[:30000]),
                 ("untried families", json.dumps(untried, ensure_ascii=False)),
                 ("measured frontier", json.dumps(ctx.frontier.report(), ensure_ascii=False)[:30000])],
                roles.PROPOSAL_SCHEMA, line="successor")
            spec = {"id": f"OBS-{kind.upper()}-R{ctx.round}", "family": idea["family"],
                    "mechanism": idea.get("mechanisms", [idea["family"]])[0]}
            _build_candidate(spec, kind=kind, ticket=ticket)
            p = A(ctx, "candidates", f"{kind}-round{ctx.round}.json")
            atomic_write_json(p, {"candidate_id": spec["id"], "family": spec["family"],
                                  "mechanism": spec["mechanism"], "kind": kind})
            return p
        return run

    H["SUCCESSOR_SEARCH"] = challenger(
        "successor", "future-scale-critic", "SUCCESSOR",
        "Design a whole-system Observatory successor that breaks the measured bottleneck while preserving every stronger measured property. Compose strong parts when compatible; do not merely rename an existing family.")
    H["RADICAL_CHALLENGER_SEARCH"] = challenger(
        "radical", "legal-capability-critic", "RADICAL",
        "Design a radical whole-system Observatory architecture from a genuinely different, preferably untried family. It must challenge assumptions about identity, time, effect, provenance and publication, not merely implementation language.")
    H["SIMPLIFICATION_CHALLENGE"] = challenger(
        "simplification", "simplification-critic", "SIMPLIFY",
        "Design the simplest whole-system Observatory architecture that could match or dominate the measured frontier. Complexity survives only if measurement proves it load-bearing.")

    def frontier_review(_m):
        for cid in sorted(ctx.candidates):
            if cid in ctx.frontier.members:
                continue
            ctx.measure_visible(cid)
            fid = ctx.obs_harness.fidelity(ctx.candidates[cid]["source"], ctx.suite, ctx.backend)
            ctx.record_score(cid, "fidelity", fid)
            rep = ctx.measure_hidden(cid, "qualification")
            ctx.record_score(cid, "hidden_qualification", rep)
            vec = ctx.dimension_vector(cid, rep, fid)
            ctx.frontier.add({"candidate_id": cid, "mechanism": ctx.candidates[cid]["mechanism"],
                              "declared_altitude": "L0", "dimension_vector": vec,
                              "evidence_refs": [f"observatory-round{ctx.round}"]})
            for lid in ctx.demonstrated_layers(cid, rep):
                ctx.esc.record_altitude_evidence(cid, lid, f"{lid} demonstrated, round {ctx.round}")
            ctx.screen_axioms(cid, rep)
        active = ctx.frontier.non_dominated()
        below = [cid for cid in active if ctx.esc.below_floor(
            ctx.frontier.members[cid]["dimension_vector"].get(ctx.profile.primary_dimension, 0.0))]
        advancing = [cid for cid in active if cid not in below]
        to_shards = advancing or active
        p = A(ctx, "frontier", f"review-round{ctx.round}.json")
        report = ctx.frontier.report()
        atomic_write_json(p, {"statuses": {k: v["status"] for k, v in report.items()},
                              "to_private_shards": to_shards, "cut_below_floor": below,
                              "floor": ctx.esc.s.get("floor"),
                              "dominated": [k for k, v in report.items() if v["status"] != "ACTIVE"]})
        return p
    H["FRONTIER_REVIEW"] = frontier_review

    def private_replication(_m):
        review = read_json(A(ctx, "frontier", f"review-round{ctx.round}.json"))
        nd = set(ctx.frontier.non_dominated())
        finalists = [cid for cid in review["to_private_shards"] if cid in nd] or sorted(nd)
        out = []
        for cid in finalists:
            rep = ctx.measure_hidden(cid, "replication")
            ctx.record_score(cid, "hidden_replication", rep)
            for lid in ctx.demonstrated_layers(cid, rep):
                ctx.esc.record_altitude_evidence(cid, lid, f"{lid} replicated on independent hidden shard")
            evo = ctx.measure_evolvability(cid)
            out.append({"candidate_id": cid, "diagnostic_classes": rep.get("diagnostic_classes", {}),
                        "slice_scores": rep.get("dimension_scores", {}),
                        "evolvability": evo["verdict"], "core_untouched": evo["core_untouched"],
                        "layers": ctx.esc.layers_covered(cid)})
        p = A(ctx, "reports", f"private-replication-round{ctx.round}.json")
        atomic_write_json(p, {"finalists": finalists, "results": out,
                              "profile": ctx.profile_id})
        return p
    H["PRIVATE_REPLICATION"] = private_replication

    def anti_satisficing(_m):
        winner, margin = ctx.frontier.head_to_head(ctx.profile.primary_dimension,
                                                   ctx.profile.secondary_dimension)
        score = (ctx.frontier.members[winner]["dimension_vector"].get(ctx.profile.primary_dimension, 0.0)
                 if winner else 0.0)
        kinds = {cid: {"kind": c["kind"], "family": c["family"]} for cid, c in ctx.candidates.items()}
        ctx.esc.record_round(f"round-{ctx.round}", sorted(ctx.candidates), winner, score, kinds)
        ctx.esc.ratchet_floor(score)
        cont, why = ctx.esc.must_continue()
        conditions = ctx.esc.conditions()
        _, obj, _, _ = ctx.ask(
            "completion-auditor", f"OBS-ANTI-SATISFICING-r{ctx.round}",
            "Audit the measured Observatory record. Every check must cite executable evidence; "
            "place any unsupported conclusion in unresolved. Do not call resource exhaustion a ceiling.",
            [("measured frontier", json.dumps(ctx.frontier.report(), ensure_ascii=False)[:45000]),
             ("escalation conditions", json.dumps(conditions, ensure_ascii=False)),
             ("target layers", json.dumps(ctx.profile.target.target_summary(), ensure_ascii=False)[:20000])],
            roles.AUDIT_SCHEMA)
        obj["escalation_required"] = cont; obj["escalation_reason"] = why
        p = A(ctx, "reports", f"anti-satisficing-round{ctx.round}.json")
        atomic_write_json(p, obj)
        return p
    H["ANTI_SATISFICING_AUDIT"] = anti_satisficing

    def hesa(_m):
        winner, margin = ctx.frontier.head_to_head(ctx.profile.primary_dimension,
                                                   ctx.profile.secondary_dimension)
        beaten = [c for c in ctx.frontier.members if c != winner]
        p = A(ctx, "frontier", "hesa_candidate.json")
        atomic_write_json(p, {"candidate_id": winner, "beats": beaten, "margin": margin,
                              "basis": f"non-dominated Observatory frontier; tie-break {ctx.profile.primary_dimension}/{ctx.profile.secondary_dimension}"})
        return p
    H["HESA_CANDIDATE"] = hesa

    def holdout(_m):
        winner = read_json(A(ctx, "frontier", "hesa_candidate.json"))["candidate_id"]
        rep = ctx.measure_hidden(winner, "holdout")
        p = A(ctx, "reports", "final_holdout.json")
        atomic_write_json(p, {"candidate_id": winner, "holdout_used_once": True,
                              "diagnostic_classes": rep.get("diagnostic_classes", {}),
                              "slice_scores": rep.get("dimension_scores", {}),
                              "profile": ctx.profile_id})
        return p
    H["FINAL_HOLDOUT_EVALUATION"] = holdout

    def synthesis(_m):
        _, obj, _, _ = ctx.ask(
            "verification-critic", "OBS-SYNTHESIS",
            "Produce the evidence-revised National Observatory target architecture. Classify each "
            "mechanism as load-bearing, decorative or refuted using the measured frontier, fidelity, "
            "hidden replay, evolvability and holdout record only.",
            [("frontier", json.dumps(ctx.frontier.report(), ensure_ascii=False)[:50000]),
             ("fidelity", json.dumps({k: v.get("fidelity") for k, v in ctx.scores.items()}, ensure_ascii=False)[:30000])],
            roles.SYNTHESIS_SCHEMA)
        p = A(ctx, "architecture", "target_v1_evidence_revised.json")
        atomic_write_json(p, obj)
        return p
    H["ARCHITECTURE_EVIDENCE_SYNTHESIS"] = synthesis

    def migration(_m):
        v1 = read_json(A(ctx, "architecture", "target_v1_evidence_revised.json"))
        reality = read_json(A(ctx, "reality", "REPOSITORY-REALITY-MODEL.json"))
        _, obj, _, _ = ctx.ask(
            "migration-critic", "OBS-MIGRATION",
            "Produce a wave-by-wave migration from the exact sealed STAVROPOULOSLAWCORPUS baseline "
            "to the evidence-revised Observatory architecture. Every wave needs a measurable "
            "acceptance gate and rollback; big-bang replacement is forbidden.",
            [("evidence-revised Observatory target", json.dumps(v1, ensure_ascii=False)[:45000]),
             ("sealed CP1 identity", json.dumps(reality, ensure_ascii=False)[:25000])],
            roles.MIGRATION_SCHEMA)
        p = A(ctx, "architecture", "migration_plan.json")
        atomic_write_json(p, obj)
        return p
    H["MIGRATION_PLAN_FROZEN"] = migration

    return H
