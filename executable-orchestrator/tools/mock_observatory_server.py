#!/usr/bin/env python3
"""Local DeepSeek-shape provider for zero-cost Observatory supremacy rehearsal.

This provider proves control-flow/contracts only, never architecture quality. It deliberately emits
categorical structural genomes matching the production taxonomy, satisfies anti-attractor lineages
mechanically, exercises formalization/build/fidelity/recombination/lower-bound/destroyer/crown roles,
and supplies a durable reference implementation for the local systems arena.
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

OPTIONS = {
    "canonical_authority_seat": ["evidence_set", "ordered_ledger", "replicated_state_machine", "proof_dag", "declarative_ir", "canonical_database", "federated_authority_set", "derived_state_root", "hybrid"],
    "evidence_primitive": ["raw_source_bytes", "signed_source_record", "content_addressed_object", "typed_observation", "proof_object", "authority_assertion", "hybrid"],
    "identity_model": ["structural_address", "source_declared_identity", "content_identity", "composite_identity", "persistent_registry", "theorem_identity", "federated_identity", "hybrid"],
    "state_derivation_model": ["replay_reducer", "incremental_dataflow", "rule_engine", "event_calculus", "verified_compiler", "proof_checker", "replicated_transition_function", "query_derived", "hybrid"],
    "temporal_model": ["bitemporal_intervals", "multitemporal_intervals", "event_calculus_time", "temporal_logic", "transaction_cut_replay", "version_dag_time", "hybrid"],
    "normative_effect_model": ["versioned_rule_pack", "event_calculus", "typed_directive_interpreter", "theorem_proof", "compiler_transform", "constraint_solver", "governed_human_resolution", "hybrid"],
    "consistency_commit_model": ["single_writer_sequence", "transactional_database", "consensus_log", "quorum_certificate", "deterministic_merge", "content_root_commit", "proof_commit", "hybrid"],
    "replication_distribution_model": ["single_primary_read_replicas", "sharded_single_writer", "raft_paxos", "bft_consensus", "crdt_convergence", "federated_witnesses", "independent_replay_replicas", "hybrid"],
    "trusted_core_topology": ["monolithic_kernel", "minimal_verifier", "compiler_kernel", "state_machine_kernel", "multi_component_tcb", "replicated_tcb", "capability_microkernel", "hybrid"],
    "provenance_proof_model": ["hash_chain", "merkle_dag", "signed_receipts", "transparency_log", "proof_carrying_derivation", "theorem_certificate", "provenance_graph", "hybrid"],
    "publication_topology": ["compiled_read_only_projections", "content_addressed_artifacts", "query_views", "signed_release_batches", "federated_mirrors", "proof_serving_api", "hybrid"],
    "governance_evolution_model": ["signed_rule_packs", "shadow_replay_activation", "threshold_governance", "immutable_versioned_core", "capability_policy", "formal_upgrade_proofs", "human_adjudication_ledger", "hybrid"],
    "scaling_partition_model": ["source_sharding", "namespace_sharding", "time_partition", "distributed_log_partitions", "dataflow_partition", "proof_dag_partition", "federated_domains", "single_node_scale_up", "hybrid"],
}

LINEAGE_INDEX = {f"G{i:02d}": i - 1 for i in range(1, 7)}
LINEAGE_INDEX.update({f"A{i:02d}": 6 + i - 1 for i in range(1, 10)})


def reference_source():
    return open(REFERENCE, encoding="utf-8").read()


def systems_reference_source():
    return open(SYSTEMS_REFERENCE, encoding="utf-8").read()


def partial_source():
    return reference_source().replace(
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


def _axis(axis, cls, tag):
    return {"class": cls, "detail": f"{tag} uses structural class {cls} for {axis} as a load-bearing design choice."}


def genome(code="G01", variant=1, tag=None):
    idx = LINEAGE_INDEX.get(code, 30)
    tag = tag or f"{code}-{variant}"
    out = {}
    for aidx, axis in enumerate(GENOME_FIELDS):
        vals = OPTIONS[axis]
        cls = vals[(idx * 3 + variant * (aidx + 1)) % len(vals)]
        out[axis] = _axis(axis, cls, tag)
    if code == "A01":
        out["canonical_authority_seat"] = _axis("canonical_authority_seat", "evidence_set", tag)
    elif code == "A02":
        out["state_derivation_model"] = _axis("state_derivation_model", "verified_compiler", tag)
    elif code == "A03":
        out["evidence_primitive"] = _axis("evidence_primitive", "raw_source_bytes", tag)
        out["canonical_authority_seat"] = _axis("canonical_authority_seat", "canonical_database", tag)
    elif code == "A04":
        out["consistency_commit_model"] = _axis("consistency_commit_model", "quorum_certificate", tag)
        out["replication_distribution_model"] = _axis("replication_distribution_model", "federated_witnesses", tag)
    elif code == "A05":
        out["consistency_commit_model"] = _axis("consistency_commit_model", "quorum_certificate", tag)
        out["replication_distribution_model"] = _axis("replication_distribution_model", "bft_consensus", tag)
    elif code == "A06":
        out["canonical_authority_seat"] = _axis("canonical_authority_seat", "proof_dag", tag)
    elif code == "A07":
        out["canonical_authority_seat"] = _axis("canonical_authority_seat", "declarative_ir", tag)
        out["state_derivation_model"] = _axis("state_derivation_model", "verified_compiler", tag)
        out["normative_effect_model"] = _axis("normative_effect_model", "compiler_transform", tag)
    elif code == "A08":
        out["trusted_core_topology"] = _axis("trusted_core_topology", "minimal_verifier", tag)
    elif code == "A09":
        out["canonical_authority_seat"] = _axis("canonical_authority_seat", "federated_authority_set", tag)
        out["replication_distribution_model"] = _axis("replication_distribution_model", "federated_witnesses", tag)
        out["scaling_partition_model"] = _axis("scaling_partition_model", "federated_domains", tag)
    return out


def proposal(family, mechanism, g=None, altitude="L12"):
    g = g or genome("G01", 1, family)
    return {
        "family": family, "genome": g,
        "trusted_boundary": f"Trusted boundary for {family} keeps deterministic evidence, identity, temporal/effect and proof verification authoritative while probabilistic proposals and projections remain outside.",
        "mechanisms": [mechanism, f"{family} deterministic identity/time/effect kernel", f"{family} proof-bound national publication and explicit unknown/conflict path"],
        "falsifiable_predictions": [
            "bitemporal replay reconstructs legal-time and knowledge-time cuts independently",
            "duplicate and conflicting source injections never create silent second truths",
            "clean replay after crash produces the same canonical state root"],
        "why_not_higher": "No higher claim is allowed before hidden semantic replay, durable fault injection, radical/recombination search, lower-bound closure and independent destroyers complete.",
        "altitude_claimed": altitude, "citations": []}


def context_text(prompt, label):
    marker = f"--- CONTEXT: {label} ---"; i = prompt.find(marker)
    if i < 0: return None
    i += len(marker); j = prompt.find("\n--- CONTEXT:", i)
    if j < 0: j = prompt.find("\nReply with exactly one JSON object", i)
    if j < 0: j = len(prompt)
    return prompt[i:j].strip()


def context_json(prompt, label):
    text = context_text(prompt, label)
    if not text: return None
    try: return json.loads(text)
    except json.JSONDecodeError: return None


def lineage_answer(prompt):
    m = re.search(r"lineage\s+([GA]\d{2})/([A-Za-z0-9_-]+)", prompt)
    code = m.group(1) if m else "G01"; name = m.group(2) if m else "mock-lineage"
    candidates = []
    for i in range(1, 7):
        candidates.append({
            "seed_id": f"S{i}", "family": f"{code}-architecture-{i}",
            "thesis": f"Whole-system architecture thesis {code}/{i} exercises a mechanically distinct controlled structural genome.",
            "genome": genome(code, i, f"forest-{code}-{i}"),
            "mechanisms": [f"{code}/{i} authority mechanism", f"{code}/{i} temporal/effect mechanism", f"{code}/{i} proof/publication mechanism"],
            "decisive_advantages": [f"{code}/{i} exposes a distinct trusted-state construction", f"{code}/{i} makes its dominant failure mode mechanically observable"],
            "assumptions": [f"{code}/{i} assumption about authority admission", f"{code}/{i} assumption about deterministic reconstruction"],
            "failure_modes": [f"{code}/{i} fails if canonical identity cannot be independently checked", f"{code}/{i} fails if durable reconstruction diverges under fault injection"],
            "why_not_higher": "This is a search seed, not a measured implementation; supremacy is intentionally unclaimed."})
    return {"lineage": f"{code}/{name}", "candidates": candidates,
            "rejected": [
                {"idea": f"{code}-rejected-monolith", "reason": "Conflates acquisition, legal effect and publication into one untestable authority seat."},
                {"idea": f"{code}-rejected-first-answer", "reason": "Offers no structural falsification path and therefore cannot support a supremacy claim."}],
            "finalist_ids": ["S1", "S2"],
            "exhaustion_note": "Six incompatible categorical seeds were generated and compared; nominated seeds remain subject to cross-lineage structural selection and executable falsification."}


def expanded_proposal(prompt):
    seed = context_json(prompt, "selected architecture seed") or {}; fam = seed.get("family", "expanded-mock-family")
    p = proposal(fam, f"expanded mechanism for {fam}", seed.get("genome") or genome("G01", 1, fam))
    p["trusted_boundary"] = f"Complete trusted boundary for {fam}; authoritative transitions are deterministic, proof-linked, temporally explicit and isolated from probabilistic proposal workers."
    p["mechanisms"] = list(seed.get("mechanisms") or p["mechanisms"]) + [f"{fam} explicit recovery and governance invariant", f"{fam} single-canonical-root projection verifier"]
    return p


def formalization_answer():
    inv = [{"id": f"INV-MOCK-{i:02d}",
            "statement": f"Invariant {i} preserves a load-bearing architecture property under execution and replay.",
            "failure_condition": f"Invariant {i} fails when the declared property diverges under the corresponding adversarial observation.",
            "observable": f"Evaluator or proof artifact exposes invariant {i} through deterministic output and evidence references."} for i in range(1, 11)]
    return {"formalization_id": "FORMALIZATION-MOCK-V1", "invariant_set": inv,
            "authority_model": "One explicit authoritative legal-state construction with deterministic admission and independently checkable evidence/proof boundaries.",
            "state_transition_model": "Typed deterministic transitions preserve effective time, knowledge time, historical evidence, conflict and unknown states.",
            "proof_obligations": [f"Proof obligation {i} must hold under hidden replay and rebuild." for i in range(1, 7)],
            "failure_semantics": [f"Failure semantic {i} must become explicit rather than silently mutating canonical truth." for i in range(1, 7)],
            "recovery_obligations": [f"Recovery obligation {i} preserves or fail-closes canonical state." for i in range(1, 5)],
            "publication_invariants": [f"Publication invariant {i} binds every channel to one canonical root." for i in range(1, 5)],
            "governance_invariants": [f"Governance invariant {i} makes trusted-policy evolution versioned and replayable." for i in range(1, 5)],
            "forbidden_shortcuts": [f"Forbidden shortcut {i}: do not replace an architecture invariant with a fixture-specific answer." for i in range(1, 6)],
            "unproven_claims": ["Real multi-datacenter national deployment remains outside the local proof envelope."]}


def destroyer_answer():
    return {"survives_prebuild": True, "fatal_flaws": [],
            "challenged_assumptions": ["canonical authority remains coherent under adverse evidence", "bitemporal reconstruction remains explicit under late corrections", "publication channels cannot become independent truth seats"],
            "attack_plan": ["inject missing and late legally material sources", "inject conflicting authoritative bytes and identity collisions", "force crash and corruption boundaries", "challenge temporal/effect rule evolution and rollback", "attempt projection divergence and trusted-boundary bypass"],
            "violated_invariant_ids": [], "missing_evidence": []}


def blueprint_fidelity_answer():
    return {"faithful": True, "preserved_invariant_ids": [f"INV-MOCK-{i:02d}" for i in range(1, 11)],
            "violated_invariant_ids": [], "evidence": ["candidate exposes required semantic operations without fixture literals"], "blocking_reasons": []}


def build_answer(prompt):
    if "COMPLETE ARCHITECTURE BLUEPRINT" not in prompt or "ARCHITECTURE FORMALIZATION" not in prompt:
        return {"candidate_id": "BAD-HANDOFF", "family": "invalid", "mechanism": "invalid", "files": []}
    bp = context_json(prompt, "COMPLETE ARCHITECTURE BLUEPRINT") or {}; family = bp.get("family", "mock-family")
    src = partial_source() if family.startswith("G02-") else weak_source() if family.startswith("G03-") else reference_source()
    return {"candidate_id": "MOCK-CAND", "family": family, "mechanism": "mock complete-blueprint implementation",
            "rationale": "Zero-cost proof candidate makes semantic discrimination observable.", "files": [{"path": "candidate.py", "content": src}]}


def challenger_genome(kind):
    if kind == "successor": return genome("G04", 5, "fixed-successor")
    if kind == "recombination":
        g = genome("G05", 6, "fixed-recombination"); g["canonical_authority_seat"] = _axis("canonical_authority_seat", "hybrid", "fixed-recombination"); g["trusted_core_topology"] = _axis("trusted_core_topology", "hybrid", "fixed-recombination"); return g
    if kind == "radical":
        g = genome("A05", 4, "fixed-radical"); g["canonical_authority_seat"] = _axis("canonical_authority_seat", "replicated_state_machine", "fixed-radical"); g["state_derivation_model"] = _axis("state_derivation_model", "replicated_transition_function", "fixed-radical"); g["provenance_proof_model"] = _axis("provenance_proof_model", "theorem_certificate", "fixed-radical"); return g
    return genome("A08", 5, "fixed-simplification")


def fixed_challenger(family, kind): return proposal(family, f"{family} load-bearing challenger mechanism", challenger_genome(kind))


def lower_bound_answer(tag):
    cls = {"information": "information", "distributed": "distributed_systems", "legal-governance": "legal_evidence"}.get(tag, "other")
    return {"fundamental_limits": [
        {"id": f"LB-{tag}-1", "claim": "An actually unknown source cannot be proven observed before evidence of its existence is available.", "class": cls, "argument": "Completeness over an unenumerated universe cannot manufacture information absent from every observation channel.", "crossing_requirement": "Additional source-universe evidence or an external witness that enumerates the missing class is required."},
        {"id": f"LB-{tag}-2", "claim": "Equal-authority contradictory evidence cannot always be deterministically resolved from the contradictory bytes alone.", "class": cls, "argument": "Choosing one unsupported branch would create information not licensed by evidence and violate honest-unknown semantics.", "crossing_requirement": "A new authoritative source, declared priority rule or governed resolution evidence is required."},
        {"id": f"LB-{tag}-3", "claim": "A distributed canonical publication cannot avoid making partition and commit assumptions explicit.", "class": cls, "argument": "Fault tolerance and availability depend on declared failure assumptions; hiding them does not remove the tradeoff.", "crossing_requirement": "A stronger synchrony/failure assumption or additional consensus evidence is required."}],
        "attainable_improvements": [], "unresolved": []}


def supremacy_case_answer(prompt):
    m = re.search(r"OBS-SUPREMACY-CASE::([A-Za-z0-9_-]+)", prompt); cid = m.group(1) if m else "OBS-01"
    return {"candidate_id": cid, "claim_level": "EVIDENCE_SUPPORTED_SUPREMACY",
            "architecture_thesis": "The finalist is preferred because it survived independent structural search, semantic execution, durable fault injection, recombination, lower-bound analysis and final destroyers while retaining one verifiable legal truth.",
            "measured_alternatives": ["independent search-forest finalist families", "radical/recombination/simplification challengers"],
            "destroyed_families": ["families dominated or rejected by measured hidden/fault evidence"],
            "load_bearing_mechanisms": ["canonical evidence-bound identity", "bitemporal deterministic legal effect", "proof-bound one-root publication"],
            "arena_evidence": ["hidden semantic replay", "durable crash/corruption/rebuild arena", "final holdout and destroyer reports"],
            "lower_bounds": ["unknown-source observability", "equal-authority evidence ambiguity", "distributed commit assumptions"],
            "why_frontier_team_would_choose": "A first-principles frontier engineering team would choose this measured finalist because each retained trusted mechanism carries falsifiable evidence, weaker structural alternatives were exercised rather than merely discussed, and fundamental limits remain explicit instead of hidden behind product claims.",
            "falsifiers": ["a new structural genome dominates the finalist", "a durable fault produces silent canonical corruption", "a simpler trusted kernel matches every measured property"],
            "limitations": ["The local proof is not evidence of actual third-party endorsement or governmental deployment."], "third_party_endorsement_claimed": False}


def migration_answer():
    return {"big_bang": False, "rollback_per_wave": True, "waves": [
        {"id": "W0", "scope": "shadow immutable evidence and canonical identity beside the current system", "acceptance": "byte-preserving import and identity replay agree on the sealed baseline", "rollback": "remove shadow projection; current production path remains untouched"},
        {"id": "W1", "scope": "introduce bitemporal legal state and explicit normative transitions in shadow mode", "acceptance": "historical replay matches frozen ground truth and provenance is complete", "rollback": "disable shadow reducer and preserve imported evidence"},
        {"id": "W2", "scope": "link jurisprudence and doctrine to exact temporal legal objects", "acceptance": "version-link and epistemic-separation gates pass on hidden replay", "rollback": "remove relation projections without changing canonical evidence"},
        {"id": "W3", "scope": "publish verified human and machine projections from the new canonical seat", "acceptance": "dual-run outputs agree and deterministic rebuild reproduces canonical state root", "rollback": "route publication back to prior system while retaining new evidence for diagnosis"}]}


def answer(prompt):
    rm = re.search(r"^ROLE:\s*(.+)$", prompt, re.M); role = rm.group(1).strip() if rm else "unknown"
    if role in ("architecture-search-independent", "architecture-search-anti-attractor"): return lineage_answer(prompt)
    if role == "architecture-expander": return expanded_proposal(prompt)
    if role == "architecture-formalizer": return formalization_answer()
    if role == "architecture-destroyer-prebuild": return destroyer_answer()
    if role == "implementation-builder": return build_answer(prompt)
    if role.startswith("blueprint-fidelity-critic-"): return blueprint_fidelity_answer()
    if role == "future-scale-critic": return fixed_challenger("fixed-successor-family", "successor")
    if role == "architecture-recombination-architect": return fixed_challenger("fixed-recombination-family", "recombination")
    if role == "radical-architecture-destroyer-builder": return fixed_challenger("fixed-radical-family", "radical")
    if role == "simplification-critic": return fixed_challenger("fixed-simplification-family", "simplification")
    if role == "adversarial-architecture-critic":
        return {"cannot_do": ["prove search ceiling until repeated structural-genome waves stop producing novel load-bearing families"], "bottleneck": "controlled structural-genome saturation and measured challenger closure remain the binding search obligations", "next_altitude": "L12", "evidence": ["frontier must survive successor, recombination, radical and simplification rounds"], "candidate_families_untried": ["fixed-successor-family", "fixed-radical-family", "fixed-simplification-family"]}
    if role == "completion-auditor": return {"checks": {"simplification": "measured", "radical": "measured", "recombination": "measured", "ablation": "measured", "first-proposal-bias": "structural forest enforced", "hidden-label-blindness": "enforced", "altitude": "derived", "families": "controlled-genome ledger checked"}, "unresolved": []}
    if role in ("durable-systems-builder", "durable-systems-reviser"):
        return {"candidate_id": "SYSTEMS-MOCK", "family": "durable-finalist", "mechanism": "sqlite durable reference for control-plane proof", "rationale": "Calibrates real durable systems arena/revision path.", "files": [{"path": "systems_candidate.py", "content": systems_reference_source()}]}
    if role.startswith("lower-bound-"): return lower_bound_answer(role[len("lower-bound-"):])
    if role.startswith("final-architecture-destroyer-"): return destroyer_answer()
    if role == "supremacy-case-auditor": return supremacy_case_answer(prompt)
    if role == "verification-critic": return {"useful": ["bitemporal canonical state", "typed normative effects", "proof-carrying provenance"], "decorative": [], "refuted": ["single-clock legal state", "doctrine as binding authority"], "notes": "classification follows measured semantic, durable, destroyer and lower-bound evidence"}
    if role == "migration-critic": return migration_answer()
    return {"checks": {f"check-{i}": "measured" for i in range(8)}, "unresolved": []}


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    def log_message(self, *args): pass
    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0)); body = json.loads(self.rfile.read(n).decode("utf-8"))
        with STATE["lock"]: STATE["calls"] += 1; call_no = STATE["calls"]; STATE["seen"].append(body)
        if not (self.headers.get("Authorization") or "").startswith("Bearer "): return self._send(401, {"error": {"message": "missing bearer token"}})
        thinking = body.get("thinking") or {}
        if thinking.get("type") != "enabled": return self._send(400, {"error": {"message": "proof requires thinking.type=enabled"}})
        if body.get("reasoning_effort") != "max": return self._send(400, {"error": {"message": "proof requires reasoning_effort=max"}})
        if int(body.get("max_tokens") or 0) < 384000: return self._send(400, {"error": {"message": "proof requires max_tokens>=384000"}})
        if body.get("model") != "deepseek-v4-pro": return self._send(400, {"error": {"message": "proof requires model=deepseek-v4-pro"}})
        prompt = "\n".join(m["content"] for m in body.get("messages", []) if m.get("role") == "user"); content = json.dumps(answer(prompt), ensure_ascii=False); pt, ct = max(1, len(prompt)//4), max(1, len(content)//4)
        self._send(200, {"id": f"obs-mock-{call_no}", "object": "chat.completion", "model": body.get("model"), "choices": [{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": content}}], "usage": {"prompt_tokens": pt, "completion_tokens": ct, "total_tokens": pt+ct, "prompt_cache_hit_tokens": 0, "prompt_cache_miss_tokens": pt, "completion_tokens_details": {"reasoning_tokens": 0}}})
    def _send(self, code, obj):
        raw = json.dumps(obj, ensure_ascii=False).encode("utf-8"); self.send_response(code); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(raw))); self.end_headers(); self.wfile.write(raw)


def serve(port=8732):
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler); threading.Thread(target=srv.serve_forever, daemon=True).start(); return srv


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--port", type=int, default=8732); a = ap.parse_args(); srv = serve(a.port); print(f"Observatory supremacy mock DeepSeek API on http://127.0.0.1:{a.port}/chat/completions")
    try:
        while True: threading.Event().wait(3600)
    except KeyboardInterrupt: srv.shutdown()


if __name__ == "__main__": main()
