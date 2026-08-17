#!/usr/bin/env python3
"""Local DeepSeek-shape provider for zero-cost Observatory supremacy rehearsal.

The mock is intentionally contract-rich. It is not evidence that an architecture is good; it proves
that the REAL runner actually traverses every required role/schema/gate without paid calls. If the
production path stops sending complete genomes, formalizations, durable contracts or crown evidence,
this provider returns shapes that make the proof fail instead of silently exercising an old path.
"""
import argparse
import json
import os
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
REFERENCE = os.path.join(ROOT, "benchmark", "observatory_reference_candidate.py")
SYSTEMS_REFERENCE = os.path.join(ROOT, "benchmark", "observatory_systems_reference_candidate.py")
STATE = {"calls": 0, "lock": threading.Lock(), "seen": []}

GENOME_FIELDS = [
    "canonical_authority_seat", "evidence_primitive", "identity_model",
    "state_derivation_model", "temporal_model", "normative_effect_model",
    "consistency_commit_model", "replication_distribution_model", "trusted_core_topology",
    "provenance_proof_model", "publication_topology", "governance_evolution_model",
    "scaling_partition_model",
]


def reference_source():
    return open(REFERENCE, encoding="utf-8").read()


def systems_reference_source():
    return open(SYSTEMS_REFERENCE, encoding="utf-8").read()


def partial_source():
    src = reference_source()
    return src.replace(
        'if kind in ("LEGISLATION", "AMENDMENT", "CORRECTION"):',
        'if kind in ("LEGISLATION", "AMENDMENT"):')


def weak_source():
    return reference_source() + r'''
def apply_change(event):
    return {"accepted": False, "target_id": event.get("target_id", ""),
            "change_type": event.get("kind", ""), "unresolved": ["unsupported-change"]}
def state_at(query):
    return {"canonical_id": query.get("canonical_id", ""), "status": "UNKNOWN", "text": None,
            "legal_time": query.get("legal_time", ""), "knowledge_time": query.get("knowledge_time", ""),
            "evidence_chain": [], "unresolved": ["weak-proof-candidate"]}
def link_jurisprudence(decision):
    return {"decision_id": decision.get("decision_id", ""), "links": [], "unresolved": ["weak-proof-candidate"]}
def provenance(query):
    return {"canonical_id": query.get("canonical_id", ""), "evidence_chain": [], "complete": False}
def publish(query):
    s = state_at(query)
    return {"canonical_id": s["canonical_id"], "status": s["status"], "text": None,
            "evidence_chain": [], "projection": {}}
'''


def genome(tag):
    # Every axis carries the tag so mock search diversity is mechanically indisputable.
    return {k: f"{k}:{tag}" for k in GENOME_FIELDS}


def proposal(family, mechanism, tag=None, altitude="L12"):
    tag = tag or family
    return {
        "family": family,
        "genome": genome(tag),
        "trusted_boundary": (
            f"Trusted boundary for {family}: deterministic evidence, identity, temporal/effect and "
            "proof verification are authoritative; probabilistic proposals and projections are outside."),
        "mechanisms": [
            mechanism,
            f"{family} deterministic identity/time/effect kernel",
            f"{family} proof-bound national publication and explicit unknown/conflict path",
        ],
        "falsifiable_predictions": [
            "bitemporal replay reconstructs legal-time and knowledge-time cuts independently",
            "duplicate and conflicting source injections never create silent second truths",
            "clean replay after crash produces the same canonical state root",
        ],
        "why_not_higher": (
            "No higher claim is allowed before hidden semantic replay, durable fault injection, "
            "radical/recombination search, lower-bound closure and independent destroyers complete."),
        "altitude_claimed": altitude,
        "citations": [],
    }


def context_text(prompt, label):
    marker = f"--- CONTEXT: {label} ---"
    i = prompt.find(marker)
    if i < 0:
        return None
    i += len(marker)
    j = prompt.find("\n--- CONTEXT:", i)
    if j < 0:
        j = prompt.find("\nReply with exactly one JSON object", i)
    if j < 0:
        j = len(prompt)
    return prompt[i:j].strip()


def context_json(prompt, label):
    text = context_text(prompt, label)
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def lineage_answer(prompt):
    m = re.search(r"lineage\s+([GA]\d{2})/([A-Za-z0-9_-]+)", prompt)
    code = m.group(1) if m else "G99"
    name = m.group(2) if m else "mock-lineage"
    candidates = []
    for i in range(1, 7):
        tag = f"forest-{code}-{i}"
        candidates.append({
            "seed_id": f"S{i}",
            "family": f"{code}-architecture-{i}",
            "thesis": f"Whole-system architecture thesis {code}/{i} constructed to exercise a distinct structural genome.",
            "genome": genome(tag),
            "mechanisms": [
                f"{code}/{i} authority mechanism",
                f"{code}/{i} temporal/effect mechanism",
                f"{code}/{i} proof/publication mechanism",
            ],
            "decisive_advantages": [
                f"{code}/{i} exposes a distinct trusted-state construction",
                f"{code}/{i} makes its dominant failure mode mechanically observable",
            ],
            "assumptions": [
                f"{code}/{i} assumption about authority admission",
                f"{code}/{i} assumption about deterministic reconstruction",
            ],
            "failure_modes": [
                f"{code}/{i} fails if canonical identity cannot be independently checked",
                f"{code}/{i} fails if durable reconstruction diverges under fault injection",
            ],
            "why_not_higher": "This is a search seed, not a measured implementation; supremacy is intentionally unclaimed.",
        })
    return {
        "lineage": f"{code}/{name}",
        "candidates": candidates,
        "rejected": [
            {"idea": f"{code}-rejected-monolith", "reason": "Conflates acquisition, legal effect and publication into one untestable authority seat."},
            {"idea": f"{code}-rejected-first-answer", "reason": "Offers no structural falsification path and therefore cannot support a supremacy claim."},
        ],
        "finalist_ids": ["S1", "S2"],
        "exhaustion_note": (
            "Six incompatible seeds were generated and compared; the nominated seeds are only lineage "
            "finalists and remain subject to cross-lineage structural selection and executable falsification."),
    }


def expanded_proposal(prompt):
    seed = context_json(prompt, "selected architecture seed") or {}
    fam = seed.get("family", "expanded-mock-family")
    g = seed.get("genome") or genome(fam)
    p = proposal(fam, f"expanded mechanism for {fam}", tag="temporary")
    p["genome"] = g  # exact genome preservation is what the real overlay checks.
    p["trusted_boundary"] = (
        f"Complete trusted boundary for {fam}; all authoritative transitions are deterministic, "
        "proof-linked, temporally explicit and isolated from probabilistic proposal workers.")
    p["mechanisms"] = list(seed.get("mechanisms") or p["mechanisms"]) + [
        f"{fam} explicit recovery and governance invariant",
        f"{fam} single-canonical-root projection verifier",
    ]
    return p


def formalization_answer():
    invariants = []
    for i in range(1, 11):
        invariants.append({
            "id": f"INV-MOCK-{i:02d}",
            "statement": f"Invariant {i} preserves a load-bearing architecture property under execution and replay.",
            "failure_condition": f"Invariant {i} fails when the declared property diverges under the corresponding adversarial observation.",
            "observable": f"Evaluator or proof artifact exposes invariant {i} through deterministic output and evidence references.",
        })
    return {
        "formalization_id": "FORMALIZATION-MOCK-V1",
        "invariant_set": invariants,
        "authority_model": "One explicit authoritative legal-state construction with deterministic admission and independently checkable evidence/proof boundaries.",
        "state_transition_model": "Typed deterministic transitions preserve effective time, knowledge time, historical evidence, conflict and unknown states.",
        "proof_obligations": [f"Proof obligation {i} must hold under hidden replay and rebuild." for i in range(1, 7)],
        "failure_semantics": [f"Failure semantic {i} must become explicit rather than silently mutating canonical truth." for i in range(1, 7)],
        "recovery_obligations": [f"Recovery obligation {i} preserves or fail-closes canonical state." for i in range(1, 5)],
        "publication_invariants": [f"Publication invariant {i} binds every channel to one canonical root." for i in range(1, 5)],
        "governance_invariants": [f"Governance invariant {i} makes trusted-policy evolution versioned and replayable." for i in range(1, 5)],
        "forbidden_shortcuts": [f"Forbidden shortcut {i}: do not replace an architecture invariant with a fixture-specific answer." for i in range(1, 6)],
        "unproven_claims": ["Real multi-datacenter national deployment remains outside the local proof envelope."],
    }


def destroyer_answer():
    return {
        "survives_prebuild": True,
        "fatal_flaws": [],
        "challenged_assumptions": [
            "canonical authority seat remains coherent under adverse evidence",
            "bitemporal reconstruction remains explicit under late corrections",
            "publication channels cannot become independent truth seats",
        ],
        "attack_plan": [
            "inject missing and late legally material sources",
            "inject conflicting authoritative bytes and identity collisions",
            "force crash and corruption boundaries",
            "challenge temporal/effect rule evolution and rollback",
            "attempt projection divergence and trusted-boundary bypass",
        ],
        "violated_invariant_ids": [],
        "missing_evidence": [],
    }


def blueprint_fidelity_answer():
    return {
        "faithful": True,
        "preserved_invariant_ids": [f"INV-MOCK-{i:02d}" for i in range(1, 11)],
        "violated_invariant_ids": [],
        "evidence": ["candidate exposes all required semantic operations without fixture literals"],
        "blocking_reasons": [],
    }


def build_answer(prompt):
    if "COMPLETE ARCHITECTURE BLUEPRINT" not in prompt or "ARCHITECTURE FORMALIZATION" not in prompt:
        return {"candidate_id": "BAD-HANDOFF", "family": "invalid", "mechanism": "invalid", "files": []}
    bp = context_json(prompt, "COMPLETE ARCHITECTURE BLUEPRINT") or {}
    family = bp.get("family", "mock-family")
    if family.startswith("G02-"):
        src = partial_source()
    elif family.startswith("G03-"):
        src = weak_source()
    else:
        src = reference_source()
    return {
        "candidate_id": "MOCK-CAND",
        "family": family,
        "mechanism": "mock complete-blueprint implementation",
        "rationale": "Zero-cost proof candidate selected to make semantic discrimination observable.",
        "files": [{"path": "candidate.py", "content": src}],
    }


def fixed_challenger(family, tag):
    return proposal(family, f"{family} load-bearing challenger mechanism", tag=tag)


def lower_bound_answer(tag):
    classes = {
        "information": "information",
        "distributed": "distributed_systems",
        "legal-governance": "legal_evidence",
    }
    cls = classes.get(tag, "other")
    return {
        "fundamental_limits": [
            {"id": f"LB-{tag}-1", "claim": "An actually unknown source cannot be proven observed before evidence of its existence is available.",
             "class": cls, "argument": "Completeness over an unenumerated universe cannot manufacture information absent from every observation channel.",
             "crossing_requirement": "Additional source-universe evidence or an external witness that enumerates the missing class is required."},
            {"id": f"LB-{tag}-2", "claim": "Equal-authority contradictory evidence cannot always be deterministically resolved from the contradictory bytes alone.",
             "class": cls, "argument": "Choosing one unsupported branch would create information not licensed by the evidence and violate honest-unknown semantics.",
             "crossing_requirement": "A new authoritative source, declared priority rule or governed resolution evidence is required."},
            {"id": f"LB-{tag}-3", "claim": "A distributed canonical publication cannot avoid making its partition and commit assumptions explicit.",
             "class": cls, "argument": "Fault tolerance and availability depend on declared failure assumptions; hiding them does not remove the tradeoff.",
             "crossing_requirement": "A stronger synchrony/failure assumption or additional consensus evidence is required."},
        ],
        "attainable_improvements": [],
        "unresolved": [],
    }


def supremacy_case_answer():
    return {
        "candidate_id": "OBS-01",
        "claim_level": "EVIDENCE_SUPPORTED_SUPREMACY",
        "architecture_thesis": "The finalist is preferred because it survived independent structural search, semantic execution, durable fault injection, recombination, lower-bound analysis and final destroyers while retaining one verifiable legal truth.",
        "measured_alternatives": ["independent search-forest finalist families", "radical/recombination/simplification challengers"],
        "destroyed_families": ["families dominated or rejected by measured hidden/fault evidence"],
        "load_bearing_mechanisms": ["canonical evidence-bound identity", "bitemporal deterministic legal effect", "proof-bound one-root publication"],
        "arena_evidence": ["hidden semantic replay", "durable crash/corruption/rebuild arena", "final holdout and destroyer reports"],
        "lower_bounds": ["unknown-source observability", "equal-authority evidence ambiguity", "distributed commit assumptions"],
        "why_frontier_team_would_choose": "A first-principles frontier engineering team would choose this measured finalist because each retained trusted mechanism carries falsifiable evidence, weaker structural alternatives were exercised rather than merely discussed, and unresolved fundamental limits remain explicit instead of being hidden behind product claims.",
        "falsifiers": ["a new structural genome dominates the finalist", "a durable fault produces silent canonical corruption", "a simpler trusted kernel matches every measured property"],
        "limitations": ["The local proof is not evidence of actual third-party endorsement or governmental deployment."],
        "third_party_endorsement_claimed": False,
    }


def migration_answer():
    return {"big_bang": False, "rollback_per_wave": True,
            "waves": [
                {"id": "W0", "scope": "shadow immutable evidence and canonical identity beside the current system",
                 "acceptance": "byte-preserving import and identity replay agree on the sealed baseline",
                 "rollback": "remove shadow projection; current production path remains untouched"},
                {"id": "W1", "scope": "introduce bitemporal legal state and explicit normative transitions in shadow mode",
                 "acceptance": "historical replay matches frozen ground truth and provenance is complete",
                 "rollback": "disable shadow reducer and preserve imported evidence"},
                {"id": "W2", "scope": "link jurisprudence and doctrine to exact temporal legal objects",
                 "acceptance": "version-link and epistemic-separation gates pass on hidden replay",
                 "rollback": "remove relation projections without changing canonical evidence"},
                {"id": "W3", "scope": "publish verified human and machine projections from the new canonical seat",
                 "acceptance": "dual-run outputs agree and deterministic rebuild reproduces canonical state root",
                 "rollback": "route publication back to prior system while retaining new evidence for diagnosis"},
            ]}


def answer(prompt):
    rm = re.search(r"^ROLE:\s*(.+)$", prompt, re.M)
    role = rm.group(1).strip() if rm else "unknown"

    if role in ("architecture-search-independent", "architecture-search-anti-attractor"):
        return lineage_answer(prompt)
    if role == "architecture-expander":
        return expanded_proposal(prompt)
    if role == "architecture-formalizer":
        return formalization_answer()
    if role == "architecture-destroyer-prebuild":
        return destroyer_answer()
    if role == "implementation-builder":
        return build_answer(prompt)
    if role.startswith("blueprint-fidelity-critic-"):
        return blueprint_fidelity_answer()

    if role == "future-scale-critic":
        return fixed_challenger("fixed-successor-family", "fixed-successor-genome")
    if role == "architecture-recombination-architect":
        return fixed_challenger("fixed-recombination-family", "fixed-recombination-genome")
    if role == "radical-architecture-destroyer-builder":
        return fixed_challenger("fixed-radical-family", "fixed-radical-genome")
    if role == "simplification-critic":
        return fixed_challenger("fixed-simplification-family", "fixed-simplification-genome")

    if role == "adversarial-architecture-critic":
        return {
            "cannot_do": ["prove the search ceiling until repeated structural-genome waves stop producing novel load-bearing families"],
            "bottleneck": "structural-genome saturation and measured challenger closure remain the binding search obligations",
            "next_altitude": "L12",
            "evidence": ["the measured frontier must survive successor, recombination, radical and simplification rounds"],
            "candidate_families_untried": [
                "fixed-successor-family", "fixed-radical-family", "fixed-simplification-family"],
        }
    if role == "completion-auditor":
        return {"checks": {
            "simplification": "measured", "radical": "measured", "recombination": "measured",
            "ablation": "measured", "first-proposal-bias": "structural forest enforced",
            "hidden-label-blindness": "enforced", "altitude": "derived", "families": "genome ledger checked",
        }, "unresolved": []}

    if role == "durable-systems-builder":
        return {
            "candidate_id": "SYSTEMS-MOCK", "family": "durable-finalist",
            "mechanism": "sqlite durable reference for control-plane proof",
            "rationale": "Calibrates that the real durable systems arena is traversed.",
            "files": [{"path": "systems_candidate.py", "content": systems_reference_source()}],
        }
    if role.startswith("lower-bound-"):
        return lower_bound_answer(role[len("lower-bound-"):])
    if role.startswith("final-architecture-destroyer-"):
        return destroyer_answer()
    if role == "supremacy-case-auditor":
        return supremacy_case_answer()

    if role == "verification-critic":
        return {"useful": ["bitemporal canonical state", "typed normative effects", "proof-carrying provenance"],
                "decorative": [], "refuted": ["single-clock legal state", "doctrine as binding authority"],
                "notes": "classification follows measured semantic, durable, destroyer and lower-bound evidence"}
    if role == "migration-critic":
        return migration_answer()

    return {"checks": {f"check-{i}": "measured" for i in range(8)}, "unresolved": []}


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):
        pass

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(n).decode("utf-8"))
        with STATE["lock"]:
            STATE["calls"] += 1
            call_no = STATE["calls"]
            STATE["seen"].append(body)
        if not (self.headers.get("Authorization") or "").startswith("Bearer "):
            return self._send(401, {"error": {"message": "missing bearer token"}})

        thinking = body.get("thinking") or {}
        if thinking.get("type") != "enabled":
            return self._send(400, {"error": {"message": "proof requires thinking.type=enabled"}})
        if body.get("reasoning_effort") != "max":
            return self._send(400, {"error": {"message": "proof requires reasoning_effort=max"}})
        if int(body.get("max_tokens") or 0) < 384000:
            return self._send(400, {"error": {"message": "proof requires max_tokens>=384000"}})
        if body.get("model") != "deepseek-v4-pro":
            return self._send(400, {"error": {"message": "proof requires model=deepseek-v4-pro"}})

        prompt = "\n".join(m["content"] for m in body.get("messages", []) if m.get("role") == "user")
        content = json.dumps(answer(prompt), ensure_ascii=False)
        pt, ct = max(1, len(prompt) // 4), max(1, len(content) // 4)
        self._send(200, {
            "id": f"obs-mock-{call_no}", "object": "chat.completion", "model": body.get("model"),
            "choices": [{"index": 0, "finish_reason": "stop",
                         "message": {"role": "assistant", "content": content}}],
            "usage": {"prompt_tokens": pt, "completion_tokens": ct, "total_tokens": pt + ct,
                      "prompt_cache_hit_tokens": 0, "prompt_cache_miss_tokens": pt,
                      "completion_tokens_details": {"reasoning_tokens": 0}},
        })

    def _send(self, code, obj):
        raw = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def serve(port=8732):
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8732)
    a = ap.parse_args()
    srv = serve(a.port)
    print(f"Observatory supremacy mock DeepSeek API on http://127.0.0.1:{a.port}/chat/completions")
    try:
        while True:
            threading.Event().wait(3600)
    except KeyboardInterrupt:
        srv.shutdown()


if __name__ == "__main__":
    main()
