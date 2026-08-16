#!/usr/bin/env python3
"""Local DeepSeek-shape provider for the National Observatory zero-cost rehearsal.

It exercises the REAL HTTP client, structured-output validation, shared 37-state machine,
candidate sandbox, hidden evaluator, frontier and owner gates. It is proof infrastructure only:
no function here is imported by a real Observatory launch.
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
STATE = {"calls": 0, "lock": threading.Lock(), "seen": []}


def reference_source():
    return open(REFERENCE, encoding="utf-8").read()


def partial_source():
    src = reference_source()
    # A real semantic defect: corrections are admitted but do not update binding text/status.
    return src.replace(
        'if kind in ("LEGISLATION", "AMENDMENT", "CORRECTION"):',
        'if kind in ("LEGISLATION", "AMENDMENT"):')


def weak_source():
    return reference_source() + r'''

# proof-only deliberately weak override: complete API surface, little legal semantics.
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


def proposal(family, mechanism, altitude="L12"):
    return {
        "family": family,
        "trusted_boundary": (
            "Primary source bytes and deterministic canonical identity, temporal-state, normative-effect "
            "and provenance transitions are inside the trusted boundary; model proposals remain outside."),
        "mechanisms": [mechanism],
        "falsifiable_predictions": [
            "bitemporal replay reconstructs legal-time and knowledge-time cuts independently",
            "duplicate and conflicting source injections never create silent second truths",
            "clean replay after crash produces the same canonical state root",
        ],
        "why_not_higher": "No higher family is asserted without executable evidence from the sealed replay and challenger rounds.",
        "altitude_claimed": altitude,
        "citations": [],
    }


def parse_candidate(prompt):
    m = re.search(r"candidate\s+([A-Za-z0-9_-]{3,40})", prompt, re.I)
    cid = m.group(1) if m else "OBS-MOCK"
    fm = re.search(r"family\s+'([^']+)'", prompt)
    mm = re.search(r"mechanism\s+'([^']+)'", prompt)
    return cid, (fm.group(1) if fm else "mock-observatory-family"), (mm.group(1) if mm else "mock-observatory-mechanism")


def build_answer(prompt):
    cid, family, mechanism = parse_candidate(prompt)
    if cid == "OBS-02":
        src = partial_source()
    elif cid == "OBS-03":
        src = weak_source()
    else:
        src = reference_source()
    return {"candidate_id": cid, "family": family, "mechanism": mechanism,
            "rationale": "proof-provider candidate chosen to make evaluator discrimination observable",
            "files": [{"path": "candidate.py", "content": src}]}


def answer(prompt):
    rm = re.search(r"^ROLE:\s*(.+)$", prompt, re.M)
    role = rm.group(1).strip() if rm else "unknown"

    if role == "architecture-explorer-A":
        return proposal("bitemporal-evidence-ledger", "content-addressed evidence + bitemporal transition ledger")
    if role == "architecture-explorer-B":
        return proposal("norm-calculus-graph", "typed normative event calculus over canonical legal identities")
    if role == "architecture-explorer-C":
        return proposal("federated-authority-mesh", "source-authority mesh converging into one canonical temporal state")
    if role == "builder":
        return build_answer(prompt)
    if role == "future-scale-critic":
        return proposal("content-addressed-bitemporal-mesh", "partitioned evidence ledger with deterministic temporal projections")
    if role == "legal-capability-critic":
        return proposal("normative-event-calculus", "declarative legal-effect calculus with immutable event evidence")
    if role == "simplification-critic":
        return proposal("minimal-bitemporal-ledger", "single canonical append-only ledger with typed deterministic reducers")
    if role == "adversarial-architecture-critic":
        return {
            "cannot_do": ["prove that no untried whole-system family could dominate the current measured frontier"],
            "bottleneck": "frontier-exhaustion evidence is incomplete until successor, radical and simplification families are measured",
            "next_altitude": "L12",
            "evidence": ["measured frontier exists but challenger families must still be executed under the same hidden replay"],
            "candidate_families_untried": [
                "content-addressed-bitemporal-mesh", "normative-event-calculus", "minimal-bitemporal-ledger"],
        }
    if role == "completion-auditor":
        return {"checks": {
            "simplification": "measured", "radical": "measured", "ablation": "measured",
            "first-proposal-bias": "not evidenced", "hidden-label-blindness": "enforced",
            "unmeasured-capability": "not accepted", "altitude": "derived", "families": "ledger checked",
        }, "unresolved": []}
    if role == "verification-critic":
        return {"useful": ["bitemporal canonical state", "typed normative effects", "proof-carrying provenance"],
                "decorative": [], "refuted": ["single-clock legal state", "doctrine as binding authority"],
                "notes": "classification follows measured hidden replay, causal ablation and frontier evidence"}
    if role == "migration-critic":
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
                     "rollback": "route publication back to prior system while retaining new ledger for diagnosis"},
                ]}
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
        prompt = "\n".join(m["content"] for m in body.get("messages", []) if m.get("role") == "user")
        content = json.dumps(answer(prompt), ensure_ascii=False)
        pt, ct = max(1, len(prompt) // 4), max(1, len(content) // 4)
        self._send(200, {
            "id": f"obs-mock-{call_no}", "object": "chat.completion", "model": body.get("model"),
            "choices": [{"index": 0, "finish_reason": "stop",
                         "message": {"role": "assistant", "content": content}}],
            "usage": {"prompt_tokens": pt, "completion_tokens": ct, "total_tokens": pt + ct,
                      "prompt_tokens_details": {"cached_tokens": 0}},
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
    print(f"Observatory mock DeepSeek API on http://127.0.0.1:{a.port}/chat/completions")
    try:
        while True:
            threading.Event().wait(3600)
    except KeyboardInterrupt:
        srv.shutdown()


if __name__ == "__main__":
    main()
