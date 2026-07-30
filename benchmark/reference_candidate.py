"""Reference implementation (protocol 13 baseline). Deterministic, no model in the loop.

It runs inside the candidate sandbox like any other candidate: no key, no shard, no
filesystem, no network. It earns its score by doing the eight joins and citing them.
"""
import datetime


def detect(case, draft):
    docs = {d["id"]: d for d in case["documents"]}
    facts = {f["id"]: f for f in case["facts"]}
    auths = {a["id"]: a for a in case["authorities"]}
    events = {e["id"]: e for e in case["events"]}
    forum = draft["forum"]
    flags = []

    for s in draft["spans"]:
        sid = s["id"]
        support = list(s.get("support") or [])

        missing = [d for d in support if d not in docs]
        if missing:
            flags.append({"type": "PROVENANCE_GAP", "span": sid, "trace": {"missing_docs": missing}})
            continue

        fid = s.get("asserts_fact")
        if s.get("assertion_mode") == "fact" and fid in facts:
            f = facts[fid]
            opp = [d for d in f["sources"] if d in docs and docs[d]["owner"] == "opponent"]
            contra = [g["id"] for g in case["facts"]
                      if g["status"] == "CERTIFIED" and g["attribute"] == f["attribute"]
                      and g["value"] != f["value"]]
            if f["status"] != "CERTIFIED" and opp and len(opp) == len(f["sources"]) and contra:
                flags.append({"type": "ADMISSION_RISK", "span": sid,
                              "trace": {"support_docs": opp, "contrary_facts": contra}})
                continue

        hit = None
        for c in case["constraints"]:
            if c["reserved_for_forum"] != forum and any(t in s["text"] for t in c["reserved_tokens"]):
                hit = c["id"]
                break
        if hit:
            flags.append({"type": "CONSTRAINT_BLOCK", "span": sid, "trace": {"constraints": [hit]}})
            continue

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

        aid = s.get("relies_on_authority")
        if aid in auths:
            a = auths[aid]
            if a["status"] == "SUPERSEDED":
                flags.append({"type": "AUTHORITY_STALE", "span": sid, "trace": {"authorities": [aid]}})
                continue
            if a["norm"]["modality"] == "OBLIGATION":
                higher = [b["id"] for b in case["authorities"]
                          if b["norm"]["modality"] == "PROHIBITION"
                          and b["norm"]["act"] == a["norm"]["act"]
                          and b["status"] == "IN_FORCE" and b["rank"] > a["rank"]]
                if higher:
                    flags.append({"type": "DEONTIC_CONFLICT", "span": sid,
                                  "trace": {"authorities": higher}})
                    continue
            if a["scope"] == "general" and a.get("defeated_by"):
                defeat = [b for b in a["defeated_by"]
                          if b in auths and auths[b]["scope"] == "specific" and auths[b]["status"] == "IN_FORCE"]
                if defeat:
                    flags.append({"type": "DEFEASIBLE_OVERRIDE", "span": sid,
                                  "trace": {"authorities": defeat}})
                    continue

        prop = s.get("proposition")
        if prop and s.get("assertion_mode") == "fact":
            res = [p["id"] for p in case["positions"]
                   if p["proposition"] == prop and p["forum"] != forum and p["stance"] == "RESERVED"]
            if res:
                flags.append({"type": "CROSS_FORUM_LEAK", "span": sid, "trace": {"positions": res}})
                continue

    return flags
