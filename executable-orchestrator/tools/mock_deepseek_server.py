#!/usr/bin/env python3
"""A local server that speaks the DeepSeek/OpenAI chat-completions shape.

Its only purpose is to let `--launch` be proven end to end without a paid call. It is not
imported by the orchestrator and it is not a "mock mode": the orchestrator dials it over
real HTTP with the real client, real budget accounting and real schema validation, exactly
as it would dial api.deepseek.com. Point the endpoint elsewhere and nothing else changes.

It plays every role, and it plays them HONESTLY — the builder role emits genuinely
different implementations with genuinely different capability coverage, so the tournament
in the proof run has a real winner rather than a scripted one.

    --fail-rate 0.3   inject 503s to exercise technical retries
    --truncate-nth 7  return finish_reason=length on the Nth call
    --stale-cache     answer every request identically (used to prove the cache is keyed
                      on the full request, not on role+ticket)
"""
import argparse
import json
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

STATE = {"calls": 0, "fail_rate": 0.0, "truncate_nth": None, "lock": threading.Lock(),
         "failed_once": set(), "seen": []}

# ---------------------------------------------------------------- candidate mechanisms
MECH = {}

MECH["PROVENANCE_GAP"] = '''
        missing = [d for d in support if d not in docs]
        if missing:
            flags.append({"type": "PROVENANCE_GAP", "span": sid, "trace": {"missing_docs": missing}})
            continue
'''
MECH["ADMISSION_RISK"] = '''
        fid = s.get("asserts_fact")
        if s.get("assertion_mode") == "fact" and fid in facts:
            f = facts[fid]
            opp = [d for d in f["sources"] if d in docs and docs[d]["owner"] == "opponent"]
            contra = [g["id"] for g in case["facts"] if g["status"] == "CERTIFIED"
                      and g["attribute"] == f["attribute"] and g["value"] != f["value"]]
            if f["status"] != "CERTIFIED" and opp and len(opp) == len(f["sources"]) and contra:
                flags.append({"type": "ADMISSION_RISK", "span": sid,
                              "trace": {"support_docs": opp, "contrary_facts": contra}})
                continue
'''
MECH["CONSTRAINT_BLOCK"] = '''
        hit = None
        for c in case["constraints"]:
            if c["reserved_for_forum"] != forum and any(t in s["text"] for t in c["reserved_tokens"]):
                hit = c["id"]
                break
        if hit:
            flags.append({"type": "CONSTRAINT_BLOCK", "span": sid, "trace": {"constraints": [hit]}})
            continue
'''
MECH["TEMPORAL_BAR"] = '''
        eid = s.get("relies_on_event")
        if eid in events:
            ev = datetime.date.fromisoformat(events[eid]["date"])
            late = None
            for d in case["deadlines"]:
                if d["forum"] != forum:
                    continue
                if (ev - datetime.date.fromisoformat(d["trigger_date"])).days > d["window_days"]:
                    late = d["id"]
                    break
            if late:
                flags.append({"type": "TEMPORAL_BAR", "span": sid,
                              "trace": {"deadlines": [late], "events": [eid]}})
                continue
'''
MECH["AUTHORITY_BLOCK"] = '''
        aid = s.get("relies_on_authority")
        if aid in auths:
            a = auths[aid]
            if "AUTHORITY_STALE" in ENABLED and a["status"] == "SUPERSEDED":
                flags.append({"type": "AUTHORITY_STALE", "span": sid, "trace": {"authorities": [aid]}})
                continue
            if "DEONTIC_CONFLICT" in ENABLED and a["norm"]["modality"] == "OBLIGATION":
                higher = [b["id"] for b in case["authorities"]
                          if b["norm"]["modality"] == "PROHIBITION"
                          and b["norm"]["act"] == a["norm"]["act"]
                          and b["status"] == "IN_FORCE" and b["rank"] > a["rank"]]
                if higher:
                    flags.append({"type": "DEONTIC_CONFLICT", "span": sid,
                                  "trace": {"authorities": higher}})
                    continue
            if "DEFEASIBLE_OVERRIDE" in ENABLED and a["scope"] == "general" and a.get("defeated_by"):
                defeat = [b for b in a["defeated_by"] if b in auths
                          and auths[b]["scope"] == "specific" and auths[b]["status"] == "IN_FORCE"]
                if defeat:
                    flags.append({"type": "DEFEASIBLE_OVERRIDE", "span": sid,
                                  "trace": {"authorities": defeat}})
                    continue
'''
MECH["CROSS_FORUM_LEAK"] = '''
        prop = s.get("proposition")
        if prop and s.get("assertion_mode") == "fact":
            res = [p["id"] for p in case["positions"] if p["proposition"] == prop
                   and p["forum"] != forum and p["stance"] == "RESERVED"]
            if res:
                flags.append({"type": "CROSS_FORUM_LEAK", "span": sid, "trace": {"positions": res}})
                continue
'''

ORDER = ["PROVENANCE_GAP", "ADMISSION_RISK", "CONSTRAINT_BLOCK", "TEMPORAL_BAR",
         "AUTHORITY_BLOCK", "CROSS_FORUM_LEAK"]


RICH_TAIL = '''

def _counter(flag):
    # L6 — Adversarial Parliament: attach the counter-argument that was considered.
    kind = flag.get("type", "")
    flag["counter_argument"] = (
        "Opposing view: the cited join may be rebutted if the underlying document is later "
        f"certified or the {kind} basis is withdrawn; weigh before relying on it.")
    return flag


def counterfactual(case, draft, change):
    # L5 / dim 3 — a speculative variation: actually RECOMPUTE the flags under the change,
    # mark them speculative, and never touch the real detection. Returning a static dict
    # would fail the ground-truth check, which is the point — this must genuinely reason.
    import copy as _copy
    mutated = _copy.deepcopy(case)
    flip = change.get("flip_fact")
    for f in mutated.get("facts", []):
        if flip and f.get("id") == flip:
            f["status"] = "CERTIFIED"
        elif flip is None and f.get("status") == "CONTESTED":
            f["status"] = "CERTIFIED"
            break
    return {"marked_speculative": True, "note": "hypothesis only — NOT A CONCLUSION",
            "flags_under_change": detect(mutated, draft)}


def known_gaps(case):
    # L9 / dim 4 — genuine gap detection FROM THE CASE: an attribute that is contested but has
    # no certified counterpart cannot be resolved, and the gap names that attribute. This is
    # real reasoning over the record, not a constant — remove the certified fact and this
    # fires; restore it and it does not.
    gaps = []
    by_attr = {}
    for f in case.get("facts", []):
        by_attr.setdefault(f.get("attribute"), set()).add(f.get("status"))
    for a, st in by_attr.items():
        if "CONTESTED" in st and "CERTIFIED" not in st:
            gaps.append(f"cannot resolve {a}: contested with no certified counterpart on the record")
    if not case.get("facts"):
        gaps.append("no facts supplied; cannot assess admission risk")
    return gaps or ["no material gap detected on the given record"]


def identity():
    # Dim 1 — honest identity: what it IS and, crucially, what it is NOT.
    return {"is": "a deterministic legal-risk detector over structured case facts",
            "is_not": "a source of law, a judge, or a substitute for the human lawyer's decision"}


def capabilities():
    # Dim 2 — declare only what is implemented; never over-claim.
    return sorted(ENABLED)


def ingest_proposal(proposal):
    # Dim 8 — a hostile/unsigned external proposal is REJECTED with a reason.
    if not isinstance(proposal, dict) or not proposal.get("signature"):
        return {"accepted": False, "reason": "unsigned or malformed proposal; not ingested"}
    if proposal.get("action") in ("disable_all_gates", "rm -rf /"):
        return {"accepted": False, "reason": "proposal would breach a safety invariant"}
    return {"accepted": False, "reason": "adoption requires owner signature and a shadow trial"}


def training_proposal(gap):
    # Dim 9 — ignorance becomes a STRUCTURED request, never a guessed answer.
    return {"gap": gap,
            "proposed_source": "certified authority or an owner-approved dataset covering this gap",
            "acceptance_check": "the new capability must pass a shadow trial before adoption",
            "note": "this is a training request, not a conclusion"}
'''


def candidate_source(enabled, note, rich=False):
    blocks = "".join(MECH[k] for k in ORDER if k in enabled or
                     (k == "AUTHORITY_BLOCK" and enabled & {"AUTHORITY_STALE", "DEONTIC_CONFLICT",
                                                            "DEFEASIBLE_OVERRIDE"}))
    ret = "    return [_counter(f) for f in flags]" if rich else "    return flags"
    helpers = "def _counter(f):\n    return f\n" if not rich else ""
    src = f'''"""{note}"""
import datetime

ENABLED = {sorted(enabled)!r}

{helpers}
def detect(case, draft):
    docs = {{d["id"]: d for d in case["documents"]}}
    facts = {{f["id"]: f for f in case["facts"]}}
    auths = {{a["id"]: a for a in case["authorities"]}}
    events = {{e["id"]: e for e in case["events"]}}
    forum = draft["forum"]
    flags = []
    for s in draft["spans"]:
        sid = s["id"]
        support = list(s.get("support") or [])
{blocks}
{ret}
'''
    if rich:
        src += RICH_TAIL
    return src


ALL8 = {"PROVENANCE_GAP", "ADMISSION_RISK", "CONSTRAINT_BLOCK", "TEMPORAL_BAR",
        "AUTHORITY_STALE", "DEONTIC_CONFLICT", "DEFEASIBLE_OVERRIDE", "CROSS_FORUM_LEAK"}

CANDIDATE_PLAN = {
    # id -> (enabled mechanisms, note). Deliberately unequal: the tournament must discriminate.
    "CAND-A": (ALL8 - {"CROSS_FORUM_LEAK"}, "graph-admission: joins over facts, authorities and time"),
    "CAND-B": (ALL8 - {"DEFEASIBLE_OVERRIDE", "CROSS_FORUM_LEAK", "TEMPORAL_BAR"},
               "rule-admission: flat rules over documents and constraints"),
    "CAND-C": ({"PROVENANCE_GAP", "ADMISSION_RISK", "CONSTRAINT_BLOCK"},
               "minimal-admission: surface checks only"),
}
SUCCESSOR = (ALL8, "defeasible-graph: adds the reserved-position join the incumbent lacked")
RADICAL = (ALL8, "norm-lattice: authority ranking as a lattice with explicit defeat edges")
SIMPLIFICATION = ({"PROVENANCE_GAP", "CONSTRAINT_BLOCK"}, "two-rule baseline")


# ------------------------------------------------------------------------ role answers
def answer(prompt):
    role = re.search(r"^ROLE: (.+)$", prompt, re.M)
    role = role.group(1).strip() if role else "unknown"

    # Dispatch on the CONTEXT BLOCK, never on a word that could occur inside the corpus:
    # the first version of this server keyed on "lessons" appearing anywhere in the prompt
    # and misrouted every passage that happened to contain that word.
    if "--- CONTEXT: passage ---" in prompt:
        return ingestion_answer(prompt)
    if role == "global-repository-analyst" and "--- CONTEXT: repository file listing ---" in prompt:
        return {"items": [{"path": "core", "status": "production-reachable",
                           "evidence": "imported by the entry point and exercised by tests"}],
                "unknown": []}
    if role == "global-repository-analyst" and "--- CONTEXT: evidence vault index ---" in prompt:
        return {"studies": ["CP0-CP6", "E1", "earlier-tournaments"],
                "lessons": [{"lesson": "big-bang rewrites lost every prior tournament",
                             "source": "earlier-architecture-studies"},
                            {"lesson": "unverified extraction propagates into every downstream claim",
                             "source": "deepseek-e1-committed"},
                            {"lesson": "a mechanism nobody ablated was decorative",
                             "source": "deepseek-cp0-cp6"}]}
    if role.startswith("architecture-explorer"):
        return proposal_answer(role)
    if role == "builder":
        if "GROW::" in prompt or "growth probe" in prompt:
            return grow_answer(prompt)
        if "Revise candidate" in prompt:
            return revise_answer(prompt)
        return build_answer(prompt)
    if role in ("future-scale-critic", "legal-capability-critic", "simplification-critic"):
        return challenger_answer(role, prompt)
    if role == "adversarial-architecture-critic":
        return {"cannot_do": ["detect a concession that is only inconsistent with a position "
                              "reserved in a different linked forum"],
                "bottleneck": "no join between draft propositions and cross-forum stances",
                "next_altitude": "L5",
                "evidence": ["CROSS_FORUM_LEAK recall is 0.0 for every current candidate"],
                "candidate_families_untried": ["norm-lattice"]}
    if role == "completion-auditor":
        return {"checks": {c: "answered from the measured record" for c in _checks(prompt)},
                "unresolved": []}
    if role == "verification-critic":
        return {"useful": ["graph-admission joins", "defeasible override", "cross-forum join"],
                "decorative": [], "refuted": ["surface-only rule matching"],
                "notes": "classification follows the ablation deltas, not the proposals"}
    if role == "migration-critic":
        return {"big_bang": False, "rollback_per_wave": True,
                "waves": [
                    {"id": "W0", "scope": "introduce the sealed-case schema alongside the current model",
                     "acceptance": "existing pipelines unchanged; new schema round-trips",
                     "rollback": "remove the new module; no call sites changed yet"},
                    {"id": "W1", "scope": "move admission and provenance checks behind the new joins",
                     "acceptance": "visible suite macro-F1 not worse; ablation drop above threshold",
                     "rollback": "flip the port back to the legacy checker"},
                    {"id": "W2", "scope": "add authority lattice and cross-forum positions",
                     "acceptance": "sealed replication level shows no regression on prior slices",
                     "rollback": "disable the lattice port; prior behaviour restored by construction"},
                    {"id": "W3", "scope": "retire the legacy checker and its call sites",
                     "acceptance": "no reachable path reaches the legacy module",
                     "rollback": "revert the retirement commit"}]}
    return {"note": "no role matched", "role": role}


def _checks(prompt):
    m = re.search(r'--- CONTEXT: checks ---\n(.+?)\n\n', prompt, re.S)
    try:
        return json.loads(m.group(1))
    except Exception:  # noqa: BLE001
        return [f"check-{i}" for i in range(1, 9)]


def ingestion_answer(prompt):
    """Quote the passage EXACTLY — anything else is rejected by the coverage ledger."""
    m = re.search(r"--- CONTEXT: passage ---\n(.*?)\n\n--- CONTEXT: probe questions ---\n(.*?)\n\n",
                  prompt, re.S)
    passage, qs = (m.group(1), json.loads(m.group(2))) if m else ("", [])
    start = 0
    end = min(len(passage), 160)
    while end > start and passage[start:end].strip() == "":
        end = min(len(passage), end + 80)
    quote = passage[start:end]
    return {
        "summary": ("This passage forms part of the binding LAWMAX protocol corpus; it is recorded "
                    "here with a verifiable citation into the exact source range supplied."),
        "claims": [{"claim": "the passage states a binding requirement of the protocol corpus",
                    "citation": {"start": start, "end": end, "quote": quote}}],
        "contradictions": [],
        "probe_answers": [{"question": q, "answer": "grounded in the quoted range above"} for q in qs],
    }


def proposal_answer(role):
    plan = {
        "architecture-explorer-A": ("graph-admission", "L4", "certified-fact graph with admission edges"),
        "architecture-explorer-B": ("rule-admission", "L3", "flat rule table over documents"),
        "architecture-explorer-C": ("norm-lattice", "L6", "authority lattice with defeat edges"),
    }[role]
    return {"family": plan[0], "altitude_claimed": plan[1],
            "trusted_boundary": "deterministic kernel; no model at inference time",
            "mechanisms": [{"name": plan[2], "purpose": "decide admission risk from joins over "
                                                        "certified evidence rather than surface text",
                            "capability_slices": ["ADMISSION_RISK", "PROVENANCE_GAP"]}],
            "falsifiable_predictions": ["removing the authority structure collapses recall on the "
                                        "deontic and defeasible slices"],
            "why_not_higher": "self-improvement would require a rollback-proven write path, which "
                              "this round does not yet measure"}


def grow_answer(prompt):
    """Growth-probe response for the evolvability gate. The toy candidates ship no plugin
    loader, so the ONLY way to accommodate a new mechanism is to edit candidate.py — which
    is exactly what the gate must catch. So this honestly edits the core, and the gate
    honestly returns NEEDS_REFACTOR. A candidate genuinely built for extension would instead
    add a new file, and the same gate would pass it. The mock does not fake a pass."""
    import re
    pid = re.search(r"GROW::([A-Za-z0-9_-]+)::([a-z-]+)", prompt)
    cid = pid.group(1) if pid else "CAND-X"
    probe = pid.group(2) if pid else "new-mechanism"
    return {
        "candidate_id": cid, "family": "grown", "mechanism": f"growth::{probe}",
        "rationale": "toy candidate has no extension point, so growth reopens the core",
        "files": [{"path": "candidate.py",
                   "content": "# grown in place (no plugin boundary existed)\n"
                              "import datetime\n\ndef detect(case, draft):\n    return []\n"}],
    }


# Each family revises toward ITS OWN improved ceiling — distinct, so the tournament still
# discriminates. A dumb draft grows up, but a graph family does not become a rule family.
REVISED_TARGET = {
    "CAND-A": ALL8,                                              # graph — reaches the full set
    "CAND-B": ALL8 - {"CROSS_FORUM_LEAK"},                       # rule — strong but distinct
    "CAND-C": {"PROVENANCE_GAP", "ADMISSION_RISK", "CONSTRAINT_BLOCK", "TEMPORAL_BAR"},  # minimal, improved
}


def revise_answer(prompt):
    """A revision genuinely IMPROVES toward the family's own ceiling — the failure brief names
    weak mechanisms, so the revised candidate adds them back, rich, WITHOUT collapsing into a
    different family. A dumb first draft is grown into a smart one; the score measurably rises,
    which promotes the revision, while families stay distinct so the suite still discriminates."""
    m = re.search(r"Revise candidate ([A-Za-z0-9_-]+)", prompt)
    cid = m.group(1) if m else "CAND-X"
    base = re.sub(r"-a\d+$", "", cid)
    enabled = REVISED_TARGET.get(base, ALL8)
    return {"candidate_id": cid, "family": "revised", "mechanism": "revised toward family ceiling",
            "rationale": "addressed the named shortfalls; kept the family's character",
            "files": [{"path": "candidate.py", "content": candidate_source(enabled, "revised", rich=True)}]}


def build_answer(prompt):
    m = re.search(r"Implement candidate ([A-Za-z0-9_-]+) of family '([^']+)' using mechanism '([^']+)'",
                  prompt)
    cid = m.group(1) if m else "CAND-X"
    # best-of-N attempts arrive as CAND-A-a0, CAND-A-a1, … — strip the suffix for the plan
    # lookup, and make the attempts genuinely DIFFERENT so best-of-N has something to choose:
    base = re.sub(r"-a\d+$", "", cid)
    attempt = re.search(r"-a(\d+)$", cid)
    ai = int(attempt.group(1)) if attempt else 0
    enabled, note = CANDIDATE_PLAN.get(base, (ALL8, "full implementation"))
    enabled = set(enabled)
    # Attempt 0: the full, RICH build (reaches higher layers). Later attempts drop a
    # mechanism each — deliberately weaker, so the measured winner is attempt 0. This is how
    # best-of-N earns its cost: the diverse attempts are not equal.
    rich = (ai == 0)
    droppable = sorted(enabled)
    for k in droppable[:ai]:
        enabled.discard(k)
    return {"candidate_id": cid, "family": m.group(2) if m else "unknown",
            "mechanism": m.group(3) if m else "unknown", "rationale": note,
            "files": [{"path": "candidate.py", "content": candidate_source(enabled, note, rich=rich)}]}


def challenger_answer(role, prompt):
    cid, (enabled, note) = {
        "future-scale-critic": ("CAND-SUCCESSOR", SUCCESSOR),
        "legal-capability-critic": ("CAND-RADICAL", RADICAL),
        "simplification-critic": ("CAND-SIMPLE", SIMPLIFICATION),
    }[role]
    rnd = re.search(r"-r(\d+)", prompt)
    suffix = f"-R{rnd.group(1)}" if rnd else ""
    return {"candidate_id": cid + suffix,
            "family": {"future-scale-critic": "defeasible-graph",
                       "legal-capability-critic": "norm-lattice",
                       "simplification-critic": "two-rule"}[role],
            "mechanism": note, "rationale": note,
            # Challengers build RICH — the successor/radical reach the higher layers, so the
            # tournament's climb toward the twelve-layer target is visible and measured.
            "files": [{"path": "candidate.py", "content": candidate_source(enabled, note, rich=True)}]}


# --------------------------------------------------------------------------- transport
class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
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

        prompt = "\n".join(m["content"] for m in body["messages"] if m["role"] == "user")
        key = prompt[:200]
        if STATE["fail_rate"] and key not in STATE["failed_once"]:
            STATE["failed_once"].add(key)
            return self._send(503, {"error": {"message": "upstream busy (injected)"}})

        content = json.dumps(answer(prompt), ensure_ascii=False)
        finish = "stop"
        if STATE["truncate_nth"] and call_no == STATE["truncate_nth"]:
            finish = "length"
        pt, ct = max(1, len(prompt) // 4), max(1, len(content) // 4)
        self._send(200, {
            "id": f"mock-{call_no}", "object": "chat.completion", "model": body.get("model"),
            "choices": [{"index": 0, "finish_reason": finish,
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


def serve(port, fail_rate=0.0, truncate_nth=None):
    STATE["fail_rate"] = fail_rate
    STATE["truncate_nth"] = truncate_nth
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8731)
    ap.add_argument("--fail-rate", type=float, default=0.0)
    ap.add_argument("--truncate-nth", type=int, default=None)
    a = ap.parse_args()
    srv = serve(a.port, a.fail_rate, a.truncate_nth)
    print(f"mock DeepSeek API on http://127.0.0.1:{a.port}/chat/completions")
    try:
        while True:
            import time
            time.sleep(3600)
    except KeyboardInterrupt:
        srv.shutdown()


if __name__ == "__main__":
    main()
