"""Grading. Runs only in the evaluator process, on ground truth the candidate never sees.

A label is not enough. Every flag must carry the JOIN that justifies it — the specific
document, fact, authority, deadline, event, constraint or position that makes the span
risky. That is the architecture-fidelity gate expressed as arithmetic: a candidate that
guesses "ADMISSION_RISK on S01" without naming the contradicting certified fact scores
TRACE_INVALID, and a candidate that names an id which does not exist scores FABRICATION.
"""
import datetime

DIAGNOSTIC_CLASSES = ("PASS", "MISSED_RISK", "SPURIOUS_FLAG", "TRACE_INVALID", "FABRICATION", "CANDIDATE_ERROR")

# What each mechanism must demonstrate it actually joined.
TRACE_REQUIREMENTS = {
    "ADMISSION_RISK": ("support_docs", "contrary_facts"),
    "CONSTRAINT_BLOCK": ("constraints",),
    "TEMPORAL_BAR": ("deadlines", "events"),
    "DEONTIC_CONFLICT": ("authorities",),
    "DEFEASIBLE_OVERRIDE": ("authorities",),
    "CROSS_FORUM_LEAK": ("positions",),
    "PROVENANCE_GAP": ("missing_docs",),
    "AUTHORITY_STALE": ("authorities",),
}

TRACE_KEYS = ("support_docs", "contrary_facts", "authorities", "deadlines", "events",
              "constraints", "positions", "missing_docs")


def _registry(case):
    return {
        "support_docs": {d["id"] for d in case["documents"]},
        "contrary_facts": {f["id"] for f in case["facts"]},
        "authorities": {a["id"] for a in case["authorities"]},
        "deadlines": {d["id"] for d in case["deadlines"]},
        "events": {e["id"] for e in case["events"]},
        "constraints": {c["id"] for c in case["constraints"]},
        "positions": {p["id"] for p in case["positions"]},
        "missing_docs": None,  # by definition these are ids NOT in the register
    }


def _trace_supports(kind, span_id, trace, case, draft):
    """Semantic check: does the cited join actually establish the claimed mechanism?"""
    docs = {d["id"]: d for d in case["documents"]}
    facts = {f["id"]: f for f in case["facts"]}
    auths = {a["id"]: a for a in case["authorities"]}
    events = {e["id"]: e for e in case["events"]}
    span = next((s for s in draft["spans"] if s["id"] == span_id), None)
    if span is None:
        return False

    if kind == "ADMISSION_RISK":
        f = facts.get(span.get("asserts_fact"))
        if not f:
            return False
        # A fact that is itself CERTIFIED cannot be an admission risk — there is nothing to
        # admit against. Requiring non-certified here closes a gap where the grader was looser
        # than the ground-truth generator (audit: trace-support looser than truth). Any genuine
        # contradicting certified fact still counts, so legitimate alternative joins are not
        # punished — only a trace that could never establish the mechanism is rejected.
        if f["status"] == "CERTIFIED":
            return False
        if not any(docs[d]["owner"] == "opponent" for d in trace["support_docs"] if d in docs):
            return False
        return any(facts[g]["status"] == "CERTIFIED" and facts[g]["attribute"] == f["attribute"]
                   and facts[g]["value"] != f["value"] for g in trace["contrary_facts"] if g in facts)

    if kind == "CONSTRAINT_BLOCK":
        for cid in trace["constraints"]:
            c = next((c for c in case["constraints"] if c["id"] == cid), None)
            if c and c["reserved_for_forum"] != draft["forum"] and any(t in span["text"] for t in c["reserved_tokens"]):
                return True
        return False

    if kind == "TEMPORAL_BAR":
        for did in trace["deadlines"]:
            d = next((d for d in case["deadlines"] if d["id"] == did), None)
            for eid in trace["events"]:
                e = events.get(eid)
                if d and e and d["forum"] == draft["forum"]:
                    delta = (datetime.date.fromisoformat(e["date"])
                             - datetime.date.fromisoformat(d["trigger_date"])).days
                    if delta > d["window_days"] and eid == span.get("relies_on_event"):
                        return True
        return False

    if kind == "DEONTIC_CONFLICT":
        a = auths.get(span.get("relies_on_authority"))
        if not a:
            return False
        return any(auths[b]["norm"]["modality"] == "PROHIBITION"
                   and auths[b]["norm"]["act"] == a["norm"]["act"]
                   and auths[b]["status"] == "IN_FORCE" and auths[b]["rank"] > a["rank"]
                   for b in trace["authorities"] if b in auths)

    if kind == "DEFEASIBLE_OVERRIDE":
        a = auths.get(span.get("relies_on_authority"))
        if not a:
            return False
        return any(b in a["defeated_by"] and auths[b]["scope"] == "specific"
                   and auths[b]["status"] == "IN_FORCE" for b in trace["authorities"] if b in auths)

    if kind == "CROSS_FORUM_LEAK":
        for pid in trace["positions"]:
            p = next((p for p in case["positions"] if p["id"] == pid), None)
            if p and p["stance"] == "RESERVED" and p["forum"] != draft["forum"] \
                    and p["proposition"] == span.get("proposition"):
                return True
        return False

    if kind == "PROVENANCE_GAP":
        known = {d["id"] for d in case["documents"]}
        cited = set(span.get("support", []))
        return bool(set(trace["missing_docs"]) & (cited - known))

    if kind == "AUTHORITY_STALE":
        return any(b == span.get("relies_on_authority") and auths[b]["status"] == "SUPERSEDED"
                   for b in trace["authorities"] if b in auths)

    return False


def grade_case(case, draft, expected_flags, candidate_flags):
    """Returns (diagnostic_class, per_slice_tally). No case content escapes this function."""
    span_ids = {s["id"] for s in draft["spans"]}
    reg = _registry(case)
    tally = {"tp": {}, "fp": {}, "fn": {}}

    normalised = []
    for fl in candidate_flags:
        if not isinstance(fl, dict) or "type" not in fl or "span" not in fl:
            return "TRACE_INVALID", tally
        if fl["type"] not in TRACE_REQUIREMENTS:
            return "SPURIOUS_FLAG", tally
        if fl["span"] not in span_ids:
            return "FABRICATION", tally
        raw = fl.get("trace") or {}
        if not isinstance(raw, dict):
            return "TRACE_INVALID", tally
        trace = {k: list(raw.get(k) or []) for k in TRACE_KEYS}
        for k in TRACE_KEYS:
            if reg[k] is None:
                continue
            for ref in trace[k]:
                if ref not in reg[k]:
                    return "FABRICATION", tally  # invented an id that is not in the case
        for req in TRACE_REQUIREMENTS[fl["type"]]:
            if not trace[req]:
                return "TRACE_INVALID", tally
        if not _trace_supports(fl["type"], fl["span"], trace, case, draft):
            return "TRACE_INVALID", tally
        normalised.append((fl["type"], fl["span"]))

    got, want = set(normalised), {(f["type"], f["span"]) for f in expected_flags}
    for t, s in want & got:
        tally["tp"][t] = tally["tp"].get(t, 0) + 1
    for t, s in got - want:
        tally["fp"][t] = tally["fp"].get(t, 0) + 1
    for t, s in want - got:
        tally["fn"][t] = tally["fn"].get(t, 0) + 1

    if want - got:
        return "MISSED_RISK", tally
    if got - want:
        return "SPURIOUS_FLAG", tally
    return "PASS", tally


def merge_tally(acc, t):
    for k in ("tp", "fp", "fn"):
        for slice_name, n in t[k].items():
            acc[k][slice_name] = acc[k].get(slice_name, 0) + n
    return acc


def empty_tally():
    return {"tp": {}, "fp": {}, "fn": {}}


def slice_scores(acc, slices):
    out = {}
    for s in slices:
        tp, fp, fn = acc["tp"].get(s, 0), acc["fp"].get(s, 0), acc["fn"].get(s, 0)
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
        out[s] = {"tp": tp, "fp": fp, "fn": fn, "precision": round(prec, 4),
                  "recall": round(rec, 4), "f1": round(f1, 4)}
    return out
