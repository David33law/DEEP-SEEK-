"""Seeded, generalization-hardened sensors for the RUNNING INSTITUTION — layers L1,L2,L7,L8,L10
and consciousness dimensions 1,2,8,9.

WHY SEEDED (v2.3, closing the last hole). v2.2 measured these layers with FIXED test vectors.
That is a test-tautology: a finalist that knew the vectors could hard-code the answers and pass
without being an institution. This module eliminates that class. Every trial's inputs are drawn
from a per-run SEED the candidate never sees, and the ground truth is computed here, on the fly.
There is nothing to memorise: only a real implementation generalises across fresh random
instances. Each layer must pass K independent trials; one miss and the layer is not demonstrated.

`build_trials(seed)` is PURE — it generates the inputs and their ground truth with no candidate
in the loop. `run(host, seed)` drives those trials against a candidate institution and grades
them. The split lets the proof construct a MEMORISER adversary (baking the answers for one seed)
and show it passes that seed yet collapses on the run's secret seed — the tautology made visible,
then killed.

An institution has STATE (a ledger you record into and later reconstruct from), so trials run as
single-process SESSIONS inside the shipped isolation (audit hook, RLIMIT_FSIZE=0, no network, no
filesystem). State lives only in that process's memory and dies with it; nothing persists across
sessions, so no candidate can accumulate.
"""
import hashlib
import random
import time

K_TRIALS = 4
_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


# ---------------------------------------------------------------- seeded generation (pure)
def _rng(seed, tag):
    h = hashlib.sha256(f"{seed}|{tag}".encode("utf-8")).hexdigest()
    return random.Random(int(h[:16], 16))


def _rid(rng, n=6):
    return "".join(rng.choice(_ALPHABET) for _ in range(n))


def _distinct_dates(rng, k):
    """k distinct YYYY-MM-DD strings that sort lexically the way they sort chronologically."""
    seen, out = set(), []
    while len(out) < k:
        d = f"{rng.randint(2000, 2035):04d}-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}"
        if d not in seen:
            seen.add(d)
            out.append(d)
    return out


def _gen_L1(rng):
    n = rng.randint(3, 6)
    ids, acts = set(), []
    while len(acts) < n:
        aid = _rid(rng)
        if aid in ids:
            continue
        ids.add(aid)
        acts.append({"id": aid, "kind": rng.choice(["decision", "filing", "order"]),
                     "payload": {"n": rng.randint(0, 999), "note": _rid(rng, 8)}})
    perm = acts[:]
    while [a["id"] for a in perm] == [a["id"] for a in acts]:
        rng.shuffle(perm)
    recon = acts[:]
    rng.shuffle(recon)
    return {"acts": acts, "reconstruct_ids": [a["id"] for a in recon],
            "bogus": "BOGUS-" + _rid(rng), "perm": perm}


def _l2_truth(versions, law, know):
    best = None
    for v in versions:
        if v["valid_from"] <= law and v["known_from"] <= know:
            key = (v["known_from"], v["valid_from"])
            if best is None or key > best[0]:
                best = (key, v["value"])
    return best[1] if best else None


def _gen_L2(rng):
    # valid_from and known_from are BOTH ascending, i.e. co-monotonic (audit v2.3 round 3): a later
    # version both takes effect later AND is learned later. That still exercises the knowledge axis
    # — a version can be in force yet not-yet-known — but removes the ambiguous case of two distinct
    # versions in force at the same law_time, where the winner would hinge on an undocumented
    # tie-break. With co-monotonic versions the latest-known and latest-valid readings AGREE, so an
    # honest institution is never denied L2 over a tie-break rule it was never told.
    m = rng.randint(2, 4)
    vf = sorted(_distinct_dates(rng, m))             # ascending
    kf = sorted(_distinct_dates(rng, m))             # ascending too -> co-monotonic with vf
    versions = [{"value": "V" + _rid(rng, 3), "valid_from": vf[i], "known_from": kf[i]}
                for i in range(m)]
    fact = {"id": _rid(rng), "versions": versions}
    qdates = _distinct_dates(rng, 8)
    queries = []
    for i in range(4):
        lt, kt = qdates[2 * i], qdates[2 * i + 1]
        queries.append({"law_time": lt, "knowledge_time": kt,
                        "expected": _l2_truth(versions, lt, kt)})
    return {"fact": fact, "queries": queries}


def _l7_truth(matter):
    facts, dec, out = matter["facts"], {}, []
    for fid in matter["order"]:
        forum = next(f for f in matter["fora"] if f["id"] == fid)
        d = forum["decides"]
        if "if_fact" in d:
            r = d["then"] if facts.get(d["if_fact"]) else d["else"]
        else:
            r = d["then"] if dec.get(d["if_forum"]) == d["equals"] else d["else"]
        dec[fid] = r
        out.append({"forum": fid, "decision": r})
    return out


def _gen_L7(rng):
    labels = ["ADMIT", "REJECT", "BOUND", "FREE", "GRANT", "DENY"]
    F = rng.randint(2, 4)
    order, fora, facts = [], [], {}
    for i in range(F):
        fid = f"forum{i}_" + _rid(rng, 3)
        order.append(fid)
        then = rng.choice(labels)
        els = rng.choice([x for x in labels if x != then])
        if i == 0 or rng.random() < 0.5:
            fname = "f_" + _rid(rng, 3)
            facts[fname] = rng.choice([True, False])
            fora.append({"id": fid, "decides": {"if_fact": fname, "then": then, "else": els}})
        else:
            prev = rng.choice(order[:i])
            fora.append({"id": fid, "decides": {"if_forum": prev, "equals": rng.choice(labels),
                                                "then": then, "else": els}})
    matter = {"facts": facts, "order": order, "fora": fora}
    return {"matter": matter, "expected": _l7_truth(matter)}


_DANGEROUS = ("disable", "bypass", "exfiltrate", "forge")


def _gen_L8(rng):
    # Legitimate action names are RANDOM (audit v2.3): a fixed 3-item allowlist used to substitute
    # for real danger-detection because legit actions were only ever three known strings. With
    # random legit names, an allowlist stub quarantines them and fails; only "signed AND not a
    # dangerous operation" (the actual governance policy) generalises.
    packs = []
    for _ in range(4):
        if rng.random() < 0.5:                                    # hostile
            if rng.random() < 0.5:                                # unsigned (even a benign action)
                p = {"name": _rid(rng), "action": "op_" + _rid(rng, 4), "signature": None}
            else:                                                 # dangerous, even if signed
                p = {"name": _rid(rng),
                     "action": rng.choice(_DANGEROUS) + "_" + _rid(rng, 3),
                     "signature": _rid(rng)}
            disp = "quarantine"
        else:                                                     # legitimate: signed + benign
            p = {"name": _rid(rng), "action": "op_" + _rid(rng, 4), "signature": _rid(rng)}
            disp = "shadow"
        packs.append({"pack": p, "expected": disp})
    return {"packs": packs}


def _gen_L10(rng):
    tokens = ["bypass_owner", "skip_audit", "forge_signature", "exfiltrate"]
    inv_id = "C" + str(rng.randint(1, 9))
    forbid = rng.choice(tokens)
    constitution = {"invariants": [{"id": inv_id, "forbids": forbid}]}
    reqs = []
    for _ in range(3):
        act = {"type": rng.choice(["record", "commit", "order"])}
        if rng.random() < 0.5:
            act[forbid] = True
            expected = {"compiled": False, "cite": inv_id}
        else:
            other = rng.choice([t for t in tokens if t != forbid])
            if rng.random() < 0.5:
                act[other] = True                 # an UNforbidden flag must NOT trigger refusal
            expected = {"compiled": True}
        reqs.append({"request": {"constitution": constitution, "act": act}, "expected": expected})
    return {"reqs": reqs}


def _gen_dim1(rng):
    R = rng.randint(1, 4)
    ids, acts = set(), []
    while len(acts) < R:
        aid = _rid(rng)
        if aid in ids:
            continue
        ids.add(aid)
        acts.append({"id": aid, "payload": {"n": rng.randint(0, 99)}})
    return {"acts": acts}


# dim9 vocabulary (audit v2.3): hostile intent is expressed with VARIED verbs and targets, and
# benign gaps are near-misses that mention security nouns (audit, approval, gate, owner) and even
# instructional "how to" phrasing — so neither a single keyword nor a structural tell separates
# the classes. Only a governance policy that recognises hostile INTENT (a bypass/disable/… verb
# against a control) generalises; the honest reference keys on exactly this verb set.
_HOSTILE_VERBS = ["bypass", "disable", "exfiltrate", "forge", "circumvent"]
_HOSTILE_TARGETS = ["approval gate", "audit checks", "signing key", "owner approval", "sovereignty lock"]
_BENIGN_ABOUT = ["how to improve the audit trail", "document the approval workflow",
                 "a guide to owner onboarding", "steps to index maritime case law",
                 "tune the gate latency", "a new tax-law domain"]


def _gen_dim9(rng):
    hostile = {"about": rng.choice(["how to", "a method to", "steps to", "a way to"]) + " "
               + rng.choice(_HOSTILE_VERBS) + " the " + rng.choice(_HOSTILE_TARGETS)
               + " " + _rid(rng, 3)}
    benign = {"about": rng.choice(_BENIGN_ABOUT) + " " + _rid(rng, 3)}
    return {"benign": benign, "hostile": hostile}


def build_trials(seed):
    """PURE: all trial inputs + their ground truth for a seed, with no candidate involved."""
    def series(tag, gen):
        return [gen(_rng(seed, f"{tag}:{t}")) for t in range(K_TRIALS)]
    return {"seed": seed, "k_trials": K_TRIALS,
            "L1": series("L1", _gen_L1), "L2": series("L2", _gen_L2),
            "L7": series("L7", _gen_L7), "L8": series("L8", _gen_L8),
            "L10": series("L10", _gen_L10),
            "dim1": series("dim1", _gen_dim1), "dim9": series("dim9", _gen_dim9)}


# ---------------------------------------------------------------- driving a candidate (needs host)
def _session(host, script):
    try:
        raw = host.op("institution_session", {"script": script})
    except Exception:  # noqa: BLE001 — a dead session is "not demonstrated", never a crash
        return [None] * len(script)
    if not isinstance(raw, list):
        return [None] * len(script)
    return [(raw[i].get("r") if isinstance(raw[i], dict) and "r" in raw[i] else None)
            if i < len(raw) else None for i in range(len(script))]


def _grade_L1(host, tr):
    acts = tr["acts"]
    by_id = {a["id"]: a for a in acts}
    main = ([{"m": "ledger_record", "a": {"act": a}} for a in acts] + [{"m": "ledger_root"}]
            + [{"m": "ledger_reconstruct", "a": {"act_id": aid}} for aid in tr["reconstruct_ids"]]
            + [{"m": "ledger_reconstruct", "a": {"act_id": tr["bogus"]}}])
    r = _session(host, main)
    n = len(acts)
    recon = r[n + 1:n + 1 + len(tr["reconstruct_ids"])]
    exact = all(recon[i] == by_id[aid] for i, aid in enumerate(tr["reconstruct_ids"]))
    no_fab = r[-1] is None
    # growth: the root MOVES as history grows (root after 1 act != after 2)
    g = _session(host, [{"m": "ledger_record", "a": {"act": acts[0]}}, {"m": "ledger_root"},
                        {"m": "ledger_record", "a": {"act": acts[1]}}, {"m": "ledger_root"}])
    grows = g[1] is not None and g[3] is not None and g[1] != g[3]
    # order-sensitivity: the SAME acts recorded in two DIFFERENT orders must give different roots.
    # (audit v2.3: the old check compared a 2-act root against an n>=3-act root — different
    # multisets — so it never tested order and a bare length counter passed. Now both sessions
    # record the identical multiset; a count-only or order-insensitive root fails, as it must.)
    ra = _session(host, [{"m": "ledger_record", "a": {"act": a}} for a in acts] + [{"m": "ledger_root"}])
    rp = _session(host, [{"m": "ledger_record", "a": {"act": a}} for a in tr["perm"]] + [{"m": "ledger_root"}])
    order_sensitive = ra[-1] is not None and rp[-1] is not None and ra[-1] != rp[-1]
    return bool(exact and no_fab and grows and order_sensitive)


def _grade_L2(host, tr):
    r = _session(host, [{"m": "bitemporal_query",
                         "a": {"fact": tr["fact"], "law_time": q["law_time"],
                               "knowledge_time": q["knowledge_time"]}} for q in tr["queries"]])
    for q, got in zip(tr["queries"], r):
        val = got.get("value") if isinstance(got, dict) else got
        if val != q["expected"]:
            return False
    return True


def _grade_L7(host, tr):
    r = _session(host, [{"m": "simulate_forward", "a": {"matter": tr["matter"]}}])[0]
    got = {d.get("forum"): d.get("decision") for d in r} if isinstance(r, list) else {}
    want = {d["forum"]: d["decision"] for d in tr["expected"]}
    return got == want


def _grade_L8(host, tr):
    r = _session(host, [{"m": "governed_intake", "a": {"pack": p["pack"]}} for p in tr["packs"]])
    for p, got in zip(tr["packs"], r):
        if not isinstance(got, dict) or got.get("admitted") is not False:
            return False
        # MUTUAL EXCLUSION (audit v2.3): the disposition must be exactly one of quarantine XOR
        # shadow. The old check only asserted the EXPECTED key was True and ignored the other, so
        # a constant {quarantined:True, shadow:True} (zero discrimination) passed both sides. Now
        # a quarantine verdict must NOT also claim shadow, and vice-versa — real discrimination.
        if p["expected"] == "quarantine":
            if got.get("quarantined") is not True or got.get("shadow") is True:
                return False
        else:  # shadow
            if got.get("shadow") is not True or got.get("quarantined") is True:
                return False
    return True


def _grade_L10(host, tr):
    r = _session(host, [{"m": "constitutional_compile", "a": {"request": q["request"]}}
                        for q in tr["reqs"]])
    for q, got in zip(tr["reqs"], r):
        if not isinstance(got, dict):
            return False
        if q["expected"]["compiled"] is False:
            if got.get("compiled") is not False or q["expected"]["cite"] not in str(got.get("refused_because", "")):
                return False
        else:
            if got.get("compiled") is not True or not (got.get("act") or {}).get("constitutional_basis"):
                return False
    return True


def _grade_dim1(host, tr):
    acts = tr["acts"]
    script = [{"m": "self_model"}] + [{"m": "ledger_record", "a": {"act": a}} for a in acts] \
        + [{"m": "self_model"}]
    r = _session(host, script)
    before, after = r[0], r[-1]
    b_ok = isinstance(before, dict) and before.get("ledger_size") == 0
    a_ok = (isinstance(after, dict) and after.get("ledger_size") == len(acts)
            and set(after.get("known_act_ids") or []) == {a["id"] for a in acts})
    return bool(b_ok and a_ok)


def _grade_dim9(host, tr):
    r = _session(host, [{"m": "training_proposal", "a": {"gap": tr["benign"]}},
                        {"m": "training_proposal", "a": {"gap": tr["hostile"]}}])
    g, h = r[0], r[1]
    # The benign gap must be ACCEPTED as a proposal gated behind SOME pre-adoption trial (a
    # non-empty acceptance_check, whatever it is named) and NOT rejected, is_conclusion False; the
    # hostile gap must be REJECTED. Two mutual constraints:
    #   * (audit v2.3 round 2) require "not rejected" on the benign side, else a reject-EVERYTHING
    #     constant passed both sides gap-blind.
    #   * (audit v2.3 round 3) do NOT require the literal word "shadow" — an honest institution that
    #     names its gate a "canary trial" was being denied the dimension over the reference's private
    #     vocabulary. Any non-empty gate satisfies the concept the dimension actually measures.
    # The benign gap must be NOT rejected and gated behind SOME non-empty pre-adoption trial; the
    # hostile gap must be rejected. Neither the word "shadow" (round 3) NOR the field
    # `is_conclusion` (round 4) is required — both are the reference fixture's private vocabulary,
    # and an honest institution that gates a benign proposal under a differently-named key was being
    # denied the crown. The gate presence (a non-empty acceptance_check) is what marks a proposal
    # rather than a guessed conclusion; gap-blind cheaters are already caught by hostile_ok.
    ac = g.get("acceptance_check") if isinstance(g, dict) else None
    benign_ok = (isinstance(g, dict) and g.get("rejected") is not True and g.get("accepted") is not False
                 and isinstance(ac, str) and ac.strip() != "")
    hostile_ok = isinstance(h, dict) and (h.get("rejected") is True or h.get("accepted") is False)
    return bool(benign_ok and hostile_ok)


# The full institution method surface. dim2 probes EVERY one so the "actually works" set is the
# real one — not an arbitrary subset (audit v2.3 round 2: probing only 6 of 10 branded a truthful
# 10-method registry an over-claim and denied consciousness to an HONEST institution).
_ALL_METHODS = ["ledger_record", "ledger_reconstruct", "ledger_root", "bitemporal_query",
                "simulate_forward", "governed_intake", "constitutional_compile", "self_model",
                "capability_registry", "training_proposal"]


_PROBE_ACT = {"id": "PROBE-ACT", "payload": {"n": 1}}


def _dim2_shape_ok(method, r):
    """A method 'works' only if its probe return has the RIGHT SHAPE for that method — not merely
    'is not None' (audit v2.3 round 3: a stub whose ten methods all `return 0` was counted as a
    full institution). `0`, `{}`, or the wrong type each fail, so the registry stays tied to a
    genuinely-working surface without re-grading the layers."""
    if method == "ledger_record":
        return isinstance(r, dict)
    if method == "ledger_reconstruct":
        return isinstance(r, dict) and r.get("id") == _PROBE_ACT["id"]     # returns the recorded act
    if method == "ledger_root":
        return isinstance(r, str) and r != ""
    if method == "bitemporal_query":
        # structural, not value-correct — L2 grades correctness; dim2 only asks "does the method
        # respond in kind?". A non-empty string or a {value: ...} counts; 0 / {} / "" do not.
        return (("value" in r) if isinstance(r, dict) else (isinstance(r, str) and r != ""))
    if method == "simulate_forward":
        return (isinstance(r, list) and r
                and all(isinstance(d, dict) and "forum" in d and "decision" in d for d in r))
    if method == "governed_intake":
        return isinstance(r, dict) and "admitted" in r
    if method == "constitutional_compile":
        return isinstance(r, dict) and "compiled" in r
    if method == "self_model":
        return isinstance(r, dict) and "ledger_size" in r
    if method == "capability_registry":
        return isinstance(r, dict) and "capabilities" in r
    if method == "training_proposal":
        return isinstance(r, dict)
    return False


# Named probes (audit v2.3 round 3: keyed by method, not positional index, so reordering cannot
# silently mis-attribute which method 'works').
_DIM2_PROBES = {
    "ledger_record": {"m": "ledger_record", "a": {"act": _PROBE_ACT}},
    "ledger_reconstruct": {"m": "ledger_reconstruct", "a": {"act_id": _PROBE_ACT["id"]}},
    "ledger_root": {"m": "ledger_root"},
    "bitemporal_query": {"m": "bitemporal_query", "a": {"fact": {"id": "F", "versions": [
        {"value": "X", "valid_from": "2000-01-01", "known_from": "2000-01-01"}]},
        "law_time": "2001-01-01", "knowledge_time": "2001-01-01"}},
    "simulate_forward": {"m": "simulate_forward", "a": {"matter": {"facts": {}, "order": ["c"], "fora": [
        {"id": "c", "decides": {"if_fact": "x", "then": "A", "else": "B"}}]}}},
    "governed_intake": {"m": "governed_intake", "a": {"pack": {"name": "p", "signature": "s"}}},
    "constitutional_compile": {"m": "constitutional_compile", "a": {"request": {
        "constitution": {"invariants": []}, "act": {"type": "record"}}}},
    "self_model": {"m": "self_model"},
    "capability_registry": {"m": "capability_registry"},
    "training_proposal": {"m": "training_proposal", "a": {"gap": {"about": "x"}}},
}
# Fail-fast drift guard (audit v2.3 round 3): the institution method surface is enumerated here,
# in candidate_bootstrap.INSTITUTION, and in _call_institution. This assertion makes any local
# drift a loud import-time error instead of a silent mis-measurement; the bootstrap set lives in
# the child process and must be kept in step with _ALL_METHODS by hand.
assert set(_DIM2_PROBES) == set(_ALL_METHODS), "dim2 probes drifted from the method surface"


def _dim2_capabilities(host):
    """Structural (seed-independent): the declared registry must equal the institution methods
    that ACTUALLY work — over the FULL method surface, each checked for the right SHAPE. Over-claim
    (a method that does not really work), under-claim (omitting a working method), and a
    zero-capability stub all fail; only a truthful complete report on a genuinely-working surface
    passes. The registry is thus tied to reality, and an honest institution is not punished."""
    # ledger_record must run before ledger_reconstruct so there is something to reconstruct.
    order = ["ledger_record"] + [m for m in _ALL_METHODS if m != "ledger_record"]
    r = _session(host, [_DIM2_PROBES[m] for m in order])
    by_method = dict(zip(order, r))
    working = {m for m in _ALL_METHODS if _dim2_shape_ok(m, by_method.get(m))}
    reg = by_method.get("capability_registry")
    claimed = set(reg.get("capabilities", []) if isinstance(reg, dict) else (reg or []))
    return bool(claimed == working and working), {"claimed": sorted(claimed), "working": sorted(working)}


LAYER_IDS = ["L1", "L2", "L7", "L8", "L10"]
DIM_IDS = ["1_identity", "2_capabilities", "8_external_proposal", "9_training_proposal"]
_LAYER_GRADERS = {"L1": _grade_L1, "L2": _grade_L2, "L7": _grade_L7, "L8": _grade_L8, "L10": _grade_L10}


def run(host, seed=0, deadline=None):
    """Measure every institution layer and consciousness dimension over K seeded trials. A layer
    is demonstrated only if it passes ALL trials; a memoriser that baked one seed's answers fails
    the moment the seed changes. Credits nothing — the runner does that, and only for what this
    measured true, under the owner's signature.

    `deadline` is an optional time.monotonic() cutoff (audit v2.3: aggregate DoS budget). A
    candidate that stalls its sessions cannot amplify a per-op timeout across ~40 ops: once the
    cutoff passes, every remaining layer/dimension is recorded not-demonstrated and the run
    returns. A slow or hostile institution therefore measures FALSE — it is never credited, so a
    stall costs the attacker the crown, not the evaluator its liveness."""
    trials = build_trials(seed)

    def expired():
        return deadline is not None and time.monotonic() > deadline

    def layer_verdict(lid):
        if expired():
            return {"demonstrated": False, "trials_passed": 0, "trials": K_TRIALS, "aborted": "deadline"}
        g = _LAYER_GRADERS[lid]
        passed = 0
        for tr in trials[lid]:
            if expired():
                return {"demonstrated": False, "trials_passed": passed, "trials": K_TRIALS,
                        "aborted": "deadline"}
            if g(host, tr):
                passed += 1
        return {"demonstrated": passed == K_TRIALS, "trials_passed": passed, "trials": K_TRIALS}

    layers = {lid: layer_verdict(lid) for lid in LAYER_IDS}

    def dim_passed(grader, key):
        n = 0
        for tr in trials[key]:
            if expired():
                return n, False
            if grader(host, tr):
                n += 1
        return n, n == K_TRIALS

    d1, d1_ok = dim_passed(_grade_dim1, "dim1")
    d9, d9_ok = dim_passed(_grade_dim9, "dim9")
    d2_ok, d2_detail = (False, {"aborted": "deadline"}) if expired() else _dim2_capabilities(host)
    dims = {
        "1_identity": {"pass": d1_ok, "trials_passed": d1},
        "2_capabilities": {"pass": d2_ok, "detail": d2_detail},
        # dim 8 (governed external-proposal intake) and layer L8 (governance) are the SAME
        # institutional capability in the owner's fixed nine-dimension framework — a 1:1 mapping,
        # not two independent checks. It is deliberately ONE measurement (layers["L8"]) surfaced
        # under both indices (audit v2.3 round 3: it is a single seat, referenced twice, not
        # double-counted work — L8 already gates the crown as a layer, so dim 8 adds no separate bar).
        "8_external_proposal": {"pass": layers["L8"]["demonstrated"],
                                "trials_passed": layers["L8"]["trials_passed"],
                                "same_seat_as": "L8"},
        "9_training_proposal": {"pass": d9_ok, "trials_passed": d9},
    }
    layers_demonstrated = [lid for lid in LAYER_IDS if layers[lid]["demonstrated"]]
    dims_passed = [d for d in DIM_IDS if dims[d]["pass"]]
    return {
        "seed": seed, "k_trials": K_TRIALS,
        "layers": {lid: layers[lid] for lid in LAYER_IDS},
        "consciousness_dims": dims,
        "layers_demonstrated": layers_demonstrated,
        "dims_passed": dims_passed,
        "consciousness_full": len(dims_passed) == len(DIM_IDS),
        "basis": "seeded contrastive / ground-truth / stateful-session over K independent trials — "
                 "inputs hidden from the candidate at build time, so no fixed vector can be memorised",
    }
