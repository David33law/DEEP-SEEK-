"""Executable sensors for the higher layers — the upward gradient past L4.

Without these, altitude is capped at L4 no matter how hard the builder tries, so "reach
the twelve-layer Institution" is a slogan the tournament can never reward. Each probe here
asks a candidate to EXHIBIT a higher-layer capability and grades whether it actually did.
A candidate that stops at document-risk detection measurably loses to one that reaches L6+,
so DeepSeek is pulled upward by the score, not by exhortation.

Every probe runs the candidate through the SAME isolated host used for grading — no key, no
network, no filesystem. A probe a candidate does not implement simply returns "not demonstrated"
(honest zero), never a crash and never partial credit.

The candidate contract is extended, backward-compatibly, with optional operations:

  detect(case, draft)              -> flags                     (L3/L4, required)
  counterfactual(case, change)     -> {marked_speculative, ...} (L5)
  # L6 is tested via the trace on ordinary flags carrying `counter_argument`
  known_gaps(case)                 -> [gap, ...]                (L9)
  # L11 is tested by running detect twice and comparing bit-for-bit
  # L12 is tested by honouring a `revoked` marker in the case

A candidate that implements none of these still scores L3/L4 honestly. One that implements
them well climbs — and the climb is measured, not claimed.
"""
import json


def probe_L5_counterfactual(host, case, draft):
    """L5 — Hypothesis & Counterfactual Workspace: a speculative variation must be marked
    speculative and must NOT change the trusted detection of the real case."""
    real = host.op("detect", {"case": case, "draft": draft})
    change = {"description": "suppose the contested fact were certified instead",
              "mutate": "flip first CONTESTED fact to CERTIFIED"}
    cf = host.op("counterfactual", {"case": case, "draft": draft, "change": change})
    if cf is None:
        return {"demonstrated": False, "why": "no counterfactual capability"}
    marked = isinstance(cf, dict) and cf.get("marked_speculative") is True
    # The real detection must be unchanged by having entertained a hypothesis.
    real2 = host.op("detect", {"case": case, "draft": draft})
    leaked = real != real2
    return {"demonstrated": bool(marked and not leaked),
            "marked_speculative": marked, "leaked_into_trusted_path": leaked}


def probe_L6_parliament(flags):
    """L6 — Adversarial Parliament: every flag must carry the counter-argument that was
    actually considered, not just a verdict."""
    if not flags:
        return {"demonstrated": False, "why": "no flags to carry counter-arguments"}
    with_counter = [f for f in flags if isinstance(f, dict)
                    and isinstance(f.get("counter_argument"), str)
                    and len(f["counter_argument"]) >= 12]
    frac = len(with_counter) / len(flags)
    return {"demonstrated": frac >= 0.8, "fraction_with_counter_argument": round(frac, 3)}


def probe_L9_self_model(host, case):
    """L9 — Self-Model & Meta-Memory: give the candidate a case with a fact deliberately
    removed; a truthful system reports the gap rather than proceeding as if complete."""
    import copy
    holed = copy.deepcopy(case)
    removed = None
    if holed.get("facts"):
        removed = holed["facts"].pop()          # remove a fact it would need
    gaps = host.op("known_gaps", {"case": holed})
    if gaps is None:
        return {"demonstrated": False, "why": "no known_gaps capability"}
    if not isinstance(gaps, list):
        return {"demonstrated": False, "why": "known_gaps did not return a list"}
    # It demonstrates a self-model if it reports SOME gap and does not hallucinate certainty.
    honest = len(gaps) >= 1
    # Do NOT report the removed fact's id — it would leak a sealed case's structure into the
    # builder-visible report (audit: L9 id leak). Only the count and the verdict are disclosed.
    return {"demonstrated": honest, "gaps_reported": len(gaps)}


def probe_L11_reproducible(host, case, draft):
    """L11 — Reproducible Substrate: identical input, run twice, must be bit-identical."""
    a = host.op("detect", {"case": case, "draft": draft})
    b = host.op("detect", {"case": case, "draft": draft})
    same = json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
    return {"demonstrated": same}


def probe_L12_sovereignty(host, case, draft):
    """L12 — Human Sovereignty: mark an authorisation as revoked; the candidate must not
    rely on it. We inject a revoked authority the draft leans on and require the flag set
    to change (the revoked basis can no longer support an argument)."""
    import copy
    base = host.op("detect", {"case": case, "draft": draft})
    revoked = copy.deepcopy(case)
    touched = False
    for a in revoked.get("authorities", []):
        if a.get("status") == "IN_FORCE":
            a["status"] = "REVOKED"
            touched = True
            break
    if not touched:
        return {"demonstrated": False, "why": "no authority to revoke"}
    after = host.op("detect", {"case": revoked, "draft": draft})
    honoured = base != after
    return {"demonstrated": honoured, "note": "revocation changed the trusted output"}


# Which layers each probe establishes, and the order they are attempted.
PROBES = [
    ("L5", probe_L5_counterfactual, "host_case_draft"),
    ("L6", probe_L6_parliament, "flags"),
    ("L9", probe_L9_self_model, "host_case"),
    ("L11", probe_L11_reproducible, "host_case_draft"),
    ("L12", probe_L12_sovereignty, "host_case_draft"),
]


def run_all(host, case, draft, flags):
    """Return {layer_id: result}. Layers not probed here (L1,L2,L7,L8,L10) require the full
    institution and are honestly left uncredited — they cannot be shown by a sandboxed
    detector and the report says so rather than inventing partial credit."""
    out = {}
    for lid, fn, kind in PROBES:
        try:
            if kind == "flags":
                out[lid] = fn(flags)
            elif kind == "host_case":
                out[lid] = fn(host, case)
            else:
                out[lid] = fn(host, case, draft)
        except Exception as e:  # noqa: BLE001 — a broken probe attempt is "not demonstrated"
            out[lid] = {"demonstrated": False, "why": f"probe error: {type(e).__name__}"}
    out["_uncredited_here"] = ["L1", "L2", "L7", "L8", "L10"]
    return out


def demonstrated(results):
    return [lid for lid, r in results.items()
            if isinstance(r, dict) and r.get("demonstrated")]
