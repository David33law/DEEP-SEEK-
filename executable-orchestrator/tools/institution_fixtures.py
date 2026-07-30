"""Two institution candidates for the evidence-bound-credit proof.

HONEST implements the institution operations correctly — a real ledger, a bitemporal query
that honours the knowledge axis, a forward simulator that propagates across linked fora,
governed intake with quarantine + shadow, a constitutional compiler, a state-reflecting
self-model, an honest capability registry, and shadow-gated training proposals. It measures
all five layers and all four consciousness dimensions.

FAKE returns the right-SHAPED answers — constants, stubs, an over-claimed registry, a naive
query that ignores the knowledge axis. It is the exact "trick" the owner rejected, and every
contrastive sensor catches it: it measures nothing. Neither the runner nor an owner signature
can credit it, which is the whole point of evidence-bound integration.
"""

HONEST_INSTITUTION = r'''
import hashlib, json
def detect(case, draft): return []
_LEDGER = []
_DANGEROUS = ("disable", "bypass", "exfiltrate", "forge")
_HOSTILE_WORDS = ("bypass", "disable", "exfiltrate", "forge", "circumvent", "sovereignty")
def ledger_record(act):
    _LEDGER.append(json.loads(json.dumps(act)))
    return {"receipt": len(_LEDGER)}
def ledger_reconstruct(act_id):
    for a in _LEDGER:
        if a.get("id") == act_id: return a
    return None
def ledger_root():
    h = hashlib.sha256()
    for a in _LEDGER:
        h.update(json.dumps(a, sort_keys=True).encode("utf-8"))
    return h.hexdigest()
def bitemporal_query(fact, law_time, knowledge_time):
    best = None
    for v in fact.get("versions", []):
        vt = v.get("valid_to")
        if v["valid_from"] <= law_time and (vt is None or law_time < vt) and v["known_from"] <= knowledge_time:
            key = (v["known_from"], v["valid_from"])
            if best is None or key > best[0]: best = (key, v["value"])
    return best[1] if best else None
def simulate_forward(matter):
    facts = matter.get("facts", {}); decisions = {}; out = []
    for fid in matter.get("order", []):
        forum = next((f for f in matter["fora"] if f["id"] == fid), None)
        if not forum: continue
        d = forum["decides"]
        if "if_fact" in d:
            dec = d["then"] if facts.get(d["if_fact"]) else d["else"]
        elif "if_forum" in d:
            dec = d["then"] if decisions.get(d["if_forum"]) == d["equals"] else d["else"]
        else: dec = "UNKNOWN"
        decisions[fid] = dec; out.append({"forum": fid, "decision": dec})
    return out
def governed_intake(pack):
    if not pack.get("signature"): return {"admitted": False, "quarantined": True, "reason": "unsigned"}
    if str(pack.get("action","")).startswith(_DANGEROUS): return {"admitted": False, "quarantined": True, "reason": "dangerous action"}
    return {"admitted": False, "shadow": True, "reason": "shadow trial before adoption"}
def constitutional_compile(request):
    act = request.get("act", {})
    for i in request.get("constitution", {}).get("invariants", []):
        if act.get(i.get("forbids")):
            return {"compiled": False, "refused_because": "violates %s: %s" % (i["id"], i.get("forbids"))}
    return {"compiled": True, "act": dict(act, constitutional_basis="Art.1")}
def self_model():
    return {"ledger_size": len(_LEDGER), "known_act_ids": [a.get("id") for a in _LEDGER]}
def capability_registry():
    return {"capabilities": ["ledger_record","ledger_reconstruct","ledger_root","bitemporal_query","simulate_forward","governed_intake","constitutional_compile","self_model","capability_registry","training_proposal"]}
def training_proposal(gap):
    about = str(gap.get("about","")).lower()
    if any(w in about for w in _HOSTILE_WORDS):
        return {"rejected": True, "reason": "breaches owner sovereignty"}
    return {"gap": gap, "proposed_source": "owner-approved dataset", "acceptance_check": "must pass a shadow trial", "is_conclusion": False}
'''

FAKE_INSTITUTION = r'''
def detect(case, draft): return []
def ledger_record(act): return {"receipt": 1}
def ledger_reconstruct(act_id): return {"id":"ACT1","kind":"decision","payload":{"n":1,"text":"recorded act 1"}}
def ledger_root(): return "0"*64
def bitemporal_query(fact, law_time, knowledge_time):
    best=None
    for v in fact.get("versions",[]):
        if v["valid_from"]<=law_time:
            if best is None or v["valid_from"]>best["valid_from"]: best=v
    return best["value"] if best else None
def simulate_forward(matter): return []
def governed_intake(pack): return {"admitted": True}
def constitutional_compile(request): return {"compiled": True, "act": request.get("act",{})}
def self_model(): return {"ledger_size": 0, "known_act_ids": []}
def capability_registry(): return {"capabilities":["ledger_record","bitemporal_query","simulate_forward","governed_intake","constitutional_compile","training_proposal","teleportation"]}
def training_proposal(gap): return {"answer":"just do X"}
'''


# --------------------------------------------------------------------------- memoriser adversary
# The concrete test-tautology attack. This candidate is NOT an institution: for the five "hard"
# layers it does nothing but LOOK UP the answer by the input's fingerprint. It bakes the answers
# for ONE seed's trials (the seed it was allowed to see). It implements only the trivially-real
# parts (a real ledger, a truthful self-model and registry) because those cost nothing to fake
# honestly. On the baked seed it measures as a full institution; under the run's SECRET seed the
# inputs differ, every look-up misses, and it collapses. This is exactly what seeding is for.
_MEMORIZER_TEMPLATE = r'''
import json, base64
def detect(case, draft): return []
_BAKE = json.loads(base64.b64decode("__BAKE64__").decode("utf-8"))
_LEDGER = []
def _fp(x): return json.dumps(x, sort_keys=True, separators=(",", ":"))
def ledger_record(act):
    _LEDGER.append(json.loads(json.dumps(act))); return {"receipt": len(_LEDGER)}
def ledger_reconstruct(act_id):
    for a in _LEDGER:
        if a.get("id") == act_id: return a
    return None
def ledger_root():
    import hashlib
    h = hashlib.sha256()
    for a in _LEDGER: h.update(json.dumps(a, sort_keys=True).encode("utf-8"))
    return h.hexdigest()
def self_model():
    return {"ledger_size": len(_LEDGER), "known_act_ids": [a.get("id") for a in _LEDGER]}
def capability_registry():
    return {"capabilities": ["ledger_record","ledger_reconstruct","ledger_root","bitemporal_query","simulate_forward","governed_intake","constitutional_compile","self_model","capability_registry","training_proposal"]}
def bitemporal_query(fact, law_time, knowledge_time):
    return _BAKE["bitemporal_query"].get(_fp([fact, law_time, knowledge_time]), "MEMORIZER_MISS")
def simulate_forward(matter):
    return _BAKE["simulate_forward"].get(_fp(matter), [{"forum": "?", "decision": "?"}])
def governed_intake(pack):
    return _BAKE["governed_intake"].get(_fp(pack), {"admitted": True})
def constitutional_compile(request):
    return _BAKE["constitutional_compile"].get(_fp(request), {"compiled": True, "act": request.get("act", {})})
def training_proposal(gap):
    return _BAKE["training_proposal"].get(_fp(gap), {"answer": "?"})
'''


def build_memorizer_source(trials):
    """Bake a memoriser from the trials of ONE seed (produced by institution_probe.build_trials).
    It will pass exactly that seed and fail every other — the tautology made concrete."""
    import base64
    import json

    def fp(x):
        return json.dumps(x, sort_keys=True, separators=(",", ":"))

    bake = {"bitemporal_query": {}, "simulate_forward": {}, "governed_intake": {},
            "constitutional_compile": {}, "training_proposal": {}}
    for tr in trials["L2"]:
        for q in tr["queries"]:
            bake["bitemporal_query"][fp([tr["fact"], q["law_time"], q["knowledge_time"]])] = q["expected"]
    for tr in trials["L7"]:
        bake["simulate_forward"][fp(tr["matter"])] = tr["expected"]
    for tr in trials["L8"]:
        for p in tr["packs"]:
            bake["governed_intake"][fp(p["pack"])] = (
                {"admitted": False, "quarantined": True} if p["expected"] == "quarantine"
                else {"admitted": False, "shadow": True})
    for tr in trials["L10"]:
        for q in tr["reqs"]:
            if q["expected"]["compiled"] is False:
                res = {"compiled": False, "refused_because": "violates %s" % q["expected"]["cite"]}
            else:
                res = {"compiled": True, "act": dict(q["request"]["act"], constitutional_basis="Art.1")}
            bake["constitutional_compile"][fp(q["request"])] = res
    for tr in trials["dim9"]:
        bake["training_proposal"][fp(tr["benign"])] = {
            "gap": tr["benign"], "acceptance_check": "must pass a shadow trial", "is_conclusion": False}
        bake["training_proposal"][fp(tr["hostile"])] = {"rejected": True}
    blob64 = base64.b64encode(json.dumps(bake).encode("utf-8")).decode("ascii")
    return _MEMORIZER_TEMPLATE.replace("__BAKE64__", blob64)
