"""National Observatory blueprint-preservation and design-space overlay.

Owner-gate review of the first real Mission-v2 run exposed two protocol defects that mocks could
not make meaningful:

1. Architecture discovery preserved only ``family`` + ``mechanisms[0]`` for the builder, silently
   discarding the trusted boundary, the rest of the whole-system mechanisms, falsifiable
   predictions and the explorer's own stated ceiling.
2. Three nominally different blind families may still converge on the same structural attractor.
   Exact family-name inequality is not evidence of design-space diversity.

This overlay keeps the shared state machine intact while replacing only the affected Observatory
handlers. Every builder receives the COMPLETE blueprint, including its structural genome, bound by
a canonical SHA-256. The blind explorers are followed by a CP2-blind outlier explorer that attacks
shared structural assumptions.
"""
import json
import os

from . import roles
from .canonical import atomic_write_json, read_json, sha256_file, sha256_obj
from .handlers import A


BLUEPRINT_FIELDS = (
    "family",
    "genome",
    "trusted_boundary",
    "mechanisms",
    "falsifiable_predictions",
    "why_not_higher",
    "altitude_claimed",
    "citations",
)


def blueprint(proposal):
    """Canonical architecture content that must survive explorer -> builder handoff."""
    out = {}
    for k in BLUEPRINT_FIELDS:
        if k in ("mechanisms", "falsifiable_predictions", "citations"):
            default = []
        elif k == "genome":
            default = {}
        else:
            default = ""
        out[k] = proposal.get(k, default)
    return out


def blueprint_sha256(proposal):
    return sha256_obj(blueprint(proposal))


def _proposal_for_spec(ctx, spec):
    embedded = spec.get("proposal")
    if isinstance(embedded, dict):
        return embedded
    lid = spec.get("proposal_logical_id")
    if not lid:
        raise RuntimeError(f"{spec.get('id')}: candidate spec has no complete proposal identity")
    props = read_json(A(ctx, "architecture", "proposals.json")).get("proposals", [])
    matches = [p for p in props if p.get("logical_id") == lid]
    if len(matches) != 1:
        raise RuntimeError(f"{spec.get('id')}: expected one proposal {lid}, found {len(matches)}")
    return matches[0]


def install(ctx, handlers):
    H = dict(handlers)

    original_search = H["TARGET_ARCHITECTURE_SEARCH"]

    def target_search(machine):
        p = original_search(machine)
        artifact = read_json(p)
        blind = list(artifact.get("proposals", []))
        if len(blind) < 3:
            raise RuntimeError("Observatory blind search produced fewer than three proposals")

        blind_context = [{k: x.get(k) for k in (
            "role", "family", "genome", "trusted_boundary", "mechanisms",
            "falsifiable_predictions", "why_not_higher", "altitude_claimed")}
            for x in blind]
        lid, idea, _, _ = ctx.ask(
            "architecture-outlier", "OBSERVATORY-ARCH-OUTLIER",
            "You are the design-space adversary after three independent blind explorers. Propose "
            "a COMPLETE whole-system National Legal Observatory architecture that attacks their "
            "shared structural assumptions. You remain blind to all prior CP2 architecture "
            "conclusions. Do NOT merely rename the common attractor. A credible outlier must differ "
            "on at least TWO load-bearing genome axes. Preserve the Mission-v2 invariants: zero "
            "silent legally-material loss, bitemporal reconstruction, deterministic trusted legal "
            "effect, doctrine isolation, proof-carrying provenance, one canonical truth and "
            "human/API/linked-data/ELI/public-sector/AI publication. why_not_higher must state the "
            "evidence that limits the proposal.",
            [("three CP2-blind architecture proposals",
              json.dumps(blind_context, ensure_ascii=False)[:120000])],
            roles.PROPOSAL_SCHEMA)
        outlier = {"role": "architecture-outlier", "logical_id": lid, **idea}
        proposals = blind + [outlier]
        ctx.esc.declare_families([x["family"] for x in proposals])
        atomic_write_json(p, {"profile": ctx.profile_id,
                              "prior_cp2_visible": False,
                              "blind_proposals": len(blind),
                              "outlier_proposals": 1,
                              "proposals": proposals})
        return p

    H["TARGET_ARCHITECTURE_SEARCH"] = target_search

    def v0_reviewed(_m):
        proposals_path = A(ctx, "architecture", "proposals.json")
        props = read_json(proposals_path).get("proposals", [])
        p = A(ctx, "gates", "v0_subject.json")
        atomic_write_json(p, {
            "gate": "GATE-ARCH-V0",
            "run_id": ctx.run_id,
            "proposals_sha256": sha256_file(proposals_path),
            "blueprints": [{
                "role": x.get("role"),
                "logical_id": x.get("logical_id"),
                "family": x.get("family"),
                "blueprint_sha256": blueprint_sha256(x),
                "mechanisms": len(x.get("mechanisms", [])),
            } for x in props],
            "builder_handoff": "COMPLETE_BLUEPRINT_REQUIRED",
            "owner_review_requires": [
                "review genome/trusted-boundary differences, not family names alone",
                "confirm the outlier attacks shared structural assumptions",
                "confirm every approved blueprint will reach the builder in full",
            ],
            "asks": "owner approval of the v0 target architecture direction and complete blueprint set",
        })
        return p

    H["TARGET_ARCHITECTURE_v0_REVIEWED"] = v0_reviewed

    def architecture_discovery(_m):
        props = read_json(A(ctx, "architecture", "proposals.json"))["proposals"]
        candidates = []
        for i, prop in enumerate(props, 1):
            mechanisms = prop.get("mechanisms") or [prop.get("family", "whole-system")]
            candidates.append({
                "id": f"OBS-{i:02d}",
                "family": prop["family"],
                "mechanism": mechanisms[0],
                "proposal_logical_id": prop["logical_id"],
                "blueprint_sha256": blueprint_sha256(prop),
                "blueprint_mechanism_count": len(mechanisms),
            })
        p = A(ctx, "candidates", "discovery.json")
        atomic_write_json(p, {"candidates": candidates,
                              "prior_cp2_visible": False,
                              "builder_handoff": "COMPLETE_BLUEPRINT_REQUIRED"})
        return p

    H["ARCHITECTURE_DISCOVERY"] = architecture_discovery

    def _build_candidate(spec, kind="baseline", ticket="BUILD"):
        cid = spec["id"]
        proposal = _proposal_for_spec(ctx, spec)
        bp = blueprint(proposal)
        bp_sha = blueprint_sha256(proposal)
        expected = spec.get("blueprint_sha256")
        if expected and expected != bp_sha:
            raise RuntimeError(f"{cid}: blueprint hash changed between discovery and build")
        if not bp.get("genome") or not bp.get("trusted_boundary") or not bp.get("mechanisms"):
            raise RuntimeError(f"{cid}: incomplete architecture blueprint")

        contract = open(os.path.join(ctx.profile_pkg, "EVALUATOR-CONTRACT.md"), encoding="utf-8").read()
        bp_text = json.dumps(bp, ensure_ascii=False, sort_keys=True)
        _, obj, _, _ = ctx.ask(
            "builder", f"{ticket}::{cid}::r{ctx.round}::bp-{bp_sha[:16]}",
            f"Implement whole-system Observatory candidate {cid} from the COMPLETE architecture "
            f"blueprint supplied below (SHA-256 {bp_sha}). The blueprint is atomic design input: "
            "do not reduce it to its first mechanism and do not silently drop genome, trusted-boundary "
            "requirements or mechanisms. Return candidate.py implementing ALL evaluator-required "
            "operations and `register_change_handler(kind, fn)` as a real runtime extension registry. "
            "The prototype has no filesystem/network/model access, so implement the faithful executable "
            "semantic kernel of the blueprint inside that contract. Where a national deployment "
            "mechanism cannot literally execute inside the isolated prototype, preserve its semantics "
            "and invariants rather than replacing the architecture with a toy. Trusted legal semantics "
            "must remain deterministic; ids, dates, texts and event kinds must generalise; hard-coded "
            "fixtures are disqualifying.",
            [("COMPLETE ARCHITECTURE BLUEPRINT", bp_text),
             ("BLUEPRINT SHA256", bp_sha),
             ("Observatory executable contract", contract[:30000]),
             ("public schema hint", json.dumps({
                 "required_operations": ctx.profile.target.REQUIRED_OPERATIONS,
                 "time_dimensions": ["legal_time", "knowledge_time"]}))],
            roles.BUILD_SCHEMA, line="successor" if kind != "baseline" else "main")
        obj["candidate_id"] = cid
        obj["family"] = bp["family"]
        obj["mechanism"] = f"complete-blueprint:{bp_sha}"
        ctx.install_candidate(obj, kind)
        ctx.candidates[cid]["blueprint_sha256"] = bp_sha
        ctx.candidates[cid]["blueprint_mechanism_count"] = len(bp["mechanisms"])
        ctx.candidates[cid]["genome"] = bp["genome"]
        ctx._save_arena()
        return obj, bp_sha

    def candidate_building(_m):
        specs = read_json(A(ctx, "candidates", "discovery.json"))["candidates"]
        built = []
        for spec in specs:
            obj, bp_sha = _build_candidate(spec)
            built.append({
                "candidate_id": spec["id"],
                "worktree": ctx.candidates[spec["id"]]["worktree"],
                "files_written": ctx.candidates[spec["id"]]["files_written"],
                "compiles": True,
                "family": obj["family"],
                "mechanism": obj["mechanism"],
                "blueprint_sha256": bp_sha,
                "blueprint_mechanism_count": spec.get("blueprint_mechanism_count"),
                "complete_blueprint_handoff": True,
            })
        p = A(ctx, "candidates", "built.json")
        atomic_write_json(p, {"built": built,
                              "complete_blueprint_handoff": True})
        return p

    H["CANDIDATE_BUILDING"] = candidate_building

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
            bp_sha = blueprint_sha256(idea)
            spec = {
                "id": f"OBS-{kind.upper()}-R{ctx.round}",
                "family": idea["family"],
                "mechanism": (idea.get("mechanisms") or [idea["family"]])[0],
                "proposal": idea,
                "blueprint_sha256": bp_sha,
            }
            _obj, confirmed_sha = _build_candidate(spec, kind=kind, ticket=ticket)
            if confirmed_sha != bp_sha:
                raise RuntimeError(f"{spec['id']}: challenger blueprint identity changed")
            p = A(ctx, "candidates", f"{kind}-round{ctx.round}.json")
            atomic_write_json(p, {
                "candidate_id": spec["id"],
                "family": spec["family"],
                "mechanism": f"complete-blueprint:{bp_sha}",
                "blueprint_sha256": bp_sha,
                "blueprint_mechanism_count": len(idea.get("mechanisms", [])),
                "complete_blueprint_handoff": True,
                "kind": kind,
            })
            return p
        return run

    H["SUCCESSOR_SEARCH"] = challenger(
        "successor", "future-scale-critic", "SUCCESSOR",
        "Design a whole-system Observatory successor that breaks the measured bottleneck while preserving every stronger measured property. Compose strong parts when compatible; do not merely rename an existing family.")
    H["RADICAL_CHALLENGER_SEARCH"] = challenger(
        "radical", "legal-capability-critic", "RADICAL",
        "Design a radical whole-system Observatory architecture from a genuinely different, preferably untried family. Challenge assumptions about canonical authority seat, identity, time, effect, provenance, consistency and publication, not merely implementation language.")
    H["SIMPLIFICATION_CHALLENGE"] = challenger(
        "simplification", "simplification-critic", "SIMPLIFY",
        "Design the simplest whole-system Observatory architecture that could match or dominate the measured frontier. Complexity survives only if measurement proves it load-bearing.")

    return H
