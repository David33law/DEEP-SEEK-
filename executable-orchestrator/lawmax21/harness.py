"""Visible development suite + the ablation that turns "the mechanism works" into a number.

Ablation here does not need to understand the candidate's code. It removes from the INPUT
the structure a mechanism must join over — the authorities, the deadlines, the linked
positions — and requires the score on the affected slices to collapse. A candidate that
keeps scoring after its evidence is taken away is not reasoning; it is recognising, and
FIDELITY_CERTIFIED refuses it.

Candidates are executed through the same isolation used for the hidden set, so a builder
cannot write code that behaves differently when it thinks nobody is grading.
"""
import json
import os
import sys

EVALUATOR_DIR = None  # set by configure()


def configure(evaluator_dir):
    global EVALUATOR_DIR
    EVALUATOR_DIR = evaluator_dir
    if evaluator_dir not in sys.path:
        sys.path.insert(0, evaluator_dir)


ABLATIONS = {
    "authorities": ("authorities", ["DEONTIC_CONFLICT", "DEFEASIBLE_OVERRIDE", "AUTHORITY_STALE"]),
    "deadlines": ("deadlines", ["TEMPORAL_BAR"]),
    "positions": ("positions", ["CROSS_FORUM_LEAK"]),
    "constraints": ("constraints", ["CONSTRAINT_BLOCK"]),
}


def load_suite(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _macro_f1(scores):
    vals = [v["f1"] for v in scores.values()]
    return round(sum(vals) / len(vals), 4) if vals else 0.0


def run_suite(candidate_source, suite, backend="subprocess", timeout=60):
    """Returns (classes, slice_scores, macro_f1). Never sees hidden material."""
    import casegen
    import grade as G
    from candidate_host import CandidateFailure, CandidateHost

    host = CandidateHost(candidate_source, backend=backend, timeout=timeout)
    acc = G.empty_tally()
    classes = {c: 0 for c in G.DIAGNOSTIC_CLASSES}
    for item in suite["cases"]:
        try:
            flags = host.detect(item["case"], item["draft"])
        except CandidateFailure:
            classes["CANDIDATE_ERROR"] += 1
            continue
        cls, tally = G.grade_case(item["case"], item["draft"], item["expected_flags"], flags)
        classes[cls] += 1
        G.merge_tally(acc, tally)
    scores = G.slice_scores(acc, casegen.SLICES)
    return classes, scores, _macro_f1(scores)


def ablate_suite(suite, key):
    """Strip one structure from every case and recompute the ground truth accordingly."""
    import casegen

    field, affected = ABLATIONS[key]
    out = {"cases": []}
    for item in suite["cases"]:
        case = json.loads(json.dumps(item["case"]))
        case[field] = []
        draft = item["draft"]
        out["cases"].append({"case": case, "draft": draft,
                             "expected_flags": casegen.ground_truth(case, draft)})
    return out, affected


def _emitted_counts(candidate_source, cases, backend, timeout):
    """Count the flags the candidate ACTUALLY emits, by type — its raw output, not a graded
    score. This is what makes the fidelity gate real: we watch what the candidate DOES when
    the evidence is removed, not how it scores against a nulled ground truth."""
    from candidate_host import CandidateFailure, CandidateHost

    host = CandidateHost(candidate_source, backend=backend, timeout=timeout)
    counts = {}
    for item in cases:
        try:
            flags = host.detect(item["case"], item["draft"])
        except CandidateFailure:
            continue
        for f in flags:
            if isinstance(f, dict):
                counts[f.get("type")] = counts.get(f.get("type"), 0) + 1
    return counts


def fidelity(candidate_source, suite, min_drop, backend="subprocess", timeout=60):
    """Reasoner vs memoriser, measured on the candidate's OWN OUTPUT.

    The earlier version compared recall against ground_truth recomputed on the ablated case —
    but stripping the evidence makes that ground truth empty, so recall_after was structurally
    0 and the 'drop' was just base recall. A memoriser that re-emits a flag by span-id even
    after its evidence is gone passed identically to a reasoner (audit: ablation-fidelity-inert).

    Now we count what the candidate EMITS. When the structure a mechanism needs is stripped,
    a genuine reasoner can no longer make the join and stops emitting that flag (its emission
    collapses). A memoriser keyed on surface features keeps emitting it — now as a SPURIOUS
    flag on a barren record — so its emission does NOT collapse, and the gate refuses it."""
    _, base_scores, base_macro = run_suite(candidate_source, suite, backend, timeout)
    orig_counts = _emitted_counts(candidate_source, suite["cases"], backend, timeout)
    drops = {}
    for key in ABLATIONS:
        field, affected = ABLATIONS[key]
        ablated_cases = []
        for item in suite["cases"]:
            case = json.loads(json.dumps(item["case"]))
            case[field] = []
            ablated_cases.append({"case": case, "draft": item["draft"]})
        ab_counts = _emitted_counts(candidate_source, ablated_cases, backend, timeout)
        before = sum(orig_counts.get(s, 0) for s in affected)
        after = sum(ab_counts.get(s, 0) for s in affected)
        drop = (before - after) / before if before > 0 else 0.0
        drops[key] = {"affected_slices": affected, "emitted_before": before,
                      "emitted_after": after, "drop": round(drop, 4)}
    # Judge only mechanisms the candidate actually exercises (emitted something before). A
    # mechanism it never attempts is not fidelity-testable and is measured by capability score.
    claimed = {k: d for k, d in drops.items() if d["emitted_before"] > 0}
    worst = min((d["drop"] for d in claimed.values()), default=0.0)
    return {
        "macro_f1": base_macro,
        "ablations": drops,
        "claimed_mechanisms": sorted(claimed),
        "unclaimed_mechanisms": sorted(set(drops) - set(claimed)),
        "ablation_drop": round(worst, 4),
        "mechanism_exercised": bool(claimed) and worst >= min_drop,
    }


def scan_for_hardcoded_answers(source, suite):
    """A candidate that ships the answers instead of deriving them is not a candidate."""
    ids = set()
    for item in suite["cases"]:
        ids.add(item["case"]["case_id"])
        for f in item["expected_flags"]:
            ids.add(f"{f['type']}:{f['span']}")
    hits = sorted(i for i in ids if i in source)
    literal_case_ids = [h for h in hits if ":" not in h]
    return {"hardcoded_answer_scan": "CLEAN" if not literal_case_ids else "DIRTY",
            "suspicious_literals": literal_case_ids[:20]}


def build_visible_suite(out_path, seed, n_per_domain=3):
    """Generated once, shipped as fixtures. The generator itself stays on the private side,
    so a builder cannot enumerate the hidden domains from it."""
    import casegen

    cases = []
    for domain, case, draft, answers in casegen.generate(seed, casegen.VISIBLE_DOMAINS,
                                                         n_per_domain, "V"):
        cases.append({"domain": domain, "case": case, "draft": draft,
                      "expected_flags": answers["expected_flags"]})
    suite = {"suite": "visible-development-suite", "seed": seed,
             "domains": casegen.VISIBLE_DOMAINS, "slices": casegen.SLICES, "cases": cases}
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(suite, f, ensure_ascii=False, indent=1)
    return suite
