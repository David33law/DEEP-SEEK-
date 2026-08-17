"""Ground-truth grader for National Observatory stateful replay scenarios.

The candidate never imports this module. It receives only the label-free session script.
"""
from collections import defaultdict

DIAGNOSTIC_CLASSES = (
    "PASS", "CANDIDATE_ERROR", "SHAPE_INVALID", "SEMANTIC_MISMATCH",
    "PROVENANCE_INCOMPLETE", "PUBLICATION_INCONSISTENT", "REPLAY_NONDETERMINISTIC",
)


def _subset(expected, got):
    if not isinstance(got, dict):
        return False
    for k, v in expected.items():
        if k not in got or got[k] != v:
            return False
    return True


def _contains(spec, got):
    if not isinstance(got, dict):
        return False
    for key, required in spec.items():
        actual = got.get(key)
        if not isinstance(actual, list):
            return False
        if not set(required).issubset(set(actual)):
            return False
    return True


def _link_ok(spec, got):
    if not isinstance(got, dict):
        return False
    links = got.get("links")
    if not isinstance(links, list):
        return False
    return any(isinstance(x, dict) and all(x.get(k) == v for k, v in spec.items()) for x in links)


def _nonempty(keys, got):
    if not isinstance(got, dict):
        return False
    return all(isinstance(got.get(k), list) and len(got[k]) > 0 for k in keys)


def _projection_ok(spec, got):
    """Verify that declared publication channels are projections of this exact canonical cut."""
    if not isinstance(got, dict):
        return False
    projection = got.get("projection")
    if not isinstance(projection, dict):
        return False
    required_channels = set(spec.get("channels", []))
    actual_channels = projection.get("channels")
    if not isinstance(actual_channels, list) or not required_channels.issubset(set(actual_channels)):
        return False
    for key in ("canonical_id", "status", "legal_time", "knowledge_time"):
        expected = spec.get(key)
        if expected is not None and projection.get(key) != expected:
            return False
    # Canonical id/status in the projection must also agree with the authoritative top-level
    # publication result, so a channel manifest can never describe a second legal truth.
    if projection.get("canonical_id") != got.get("canonical_id"):
        return False
    if projection.get("status") != got.get("status"):
        return False
    return True


def grade_session(scenario, responses):
    """Return measured dimension scores and per-step diagnostics."""
    steps = scenario["steps"]
    hits, totals = defaultdict(int), defaultdict(int)
    diagnostics = []

    if not isinstance(responses, list) or len(responses) != len(steps):
        return {
            "status": "CANDIDATE_ERROR",
            "dimension_scores": {d: 0.0 for d in _scenario_dimensions(steps)},
            "diagnostics": [{"class": "CANDIDATE_ERROR", "detail": "response count mismatch"}],
        }

    replay_results = {}
    for i, (step, response) in enumerate(zip(steps, responses)):
        dims = list(step.get("dims", []))
        for d in dims:
            totals[d] += 1

        cls, detail = "PASS", ""
        if not isinstance(response, dict) or response.get("m") != step["m"]:
            cls, detail = "SHAPE_INVALID", "missing/mismatched operation envelope"
            got = None
        elif response.get("error"):
            cls, detail = "CANDIDATE_ERROR", str(response.get("error"))[:300]
            got = None
        else:
            got = response.get("r")

        if cls == "PASS" and "expect" in step and not _subset(step["expect"], got):
            cls, detail = "SEMANTIC_MISMATCH", f"expected subset {step['expect']!r}, got {got!r}"[:800]
        if cls == "PASS" and step.get("contains") and not _contains(step["contains"], got):
            cls, detail = "PROVENANCE_INCOMPLETE", f"required list members {step['contains']!r}"[:500]
        if cls == "PASS" and step.get("link") and not _link_ok(step["link"], got):
            cls, detail = "SEMANTIC_MISMATCH", f"required jurisprudence link {step['link']!r}"[:500]
        if cls == "PASS" and step.get("nonempty") and not _nonempty(step["nonempty"], got):
            cls, detail = "SEMANTIC_MISMATCH", f"expected nonempty {step['nonempty']!r}"
        if cls == "PASS" and step.get("projection_required") and not _projection_ok(step["projection_required"], got):
            cls, detail = "PUBLICATION_INCONSISTENT", "publication channels do not preserve one canonical id/status/time cut"

        if step.get("pair") and cls == "PASS":
            if not isinstance(got, dict) or not isinstance(got.get("state_root"), str) or not got.get("state_root"):
                cls, detail = "SHAPE_INVALID", "replay result needs nonempty state_root"
            elif not isinstance(got.get("objects"), int):
                cls, detail = "SHAPE_INVALID", "replay result needs integer objects"
            else:
                replay_results[step["pair"]] = got

        if cls == "PASS":
            for d in dims:
                hits[d] += 1
        diagnostics.append({"step": i, "operation": step["m"], "class": cls, "detail": detail})

    a, b = replay_results.get("replay-A"), replay_results.get("replay-B")
    replay_equal = bool(a and b and a.get("state_root") == b.get("state_root")
                        and a.get("objects") == b.get("objects"))
    if not replay_equal:
        for d in ("replay_determinism", "recovery_success"):
            hits[d] = 0
        diagnostics.append({"step": "replay-pair", "operation": "replay",
                            "class": "REPLAY_NONDETERMINISTIC",
                            "detail": "identical event replay did not produce identical canonical result"})

    scores = {d: round(hits[d] / totals[d], 6) if totals[d] else 0.0
              for d in sorted(totals)}
    status = "PASS" if all(x["class"] == "PASS" for x in diagnostics) else "FAILED_CHECKS"
    return {"status": status, "dimension_scores": scores, "diagnostics": diagnostics,
            "replay_equal": replay_equal}


def merge_reports(reports):
    """Macro-average per scenario; include sandbox-enforced static trusted-path facts."""
    by_dim = defaultdict(list)
    classes = defaultdict(int)
    for rep in reports:
        for d, v in rep.get("dimension_scores", {}).items():
            by_dim[d].append(float(v))
        for item in rep.get("diagnostics", []):
            classes[item.get("class", "CANDIDATE_ERROR")] += 1
    scores = {d: round(sum(vs) / len(vs), 6) for d, vs in sorted(by_dim.items()) if vs}
    # A candidate cannot access the network or a model callback inside CandidateHost; this is a
    # structural property of the measured execution path, not a self-reported score.
    scores["external_model_dependence"] = 0.0
    return {"dimension_scores": scores, "diagnostic_classes": dict(classes),
            "scenarios": len(reports)}


def _scenario_dimensions(steps):
    return sorted({d for s in steps for d in s.get("dims", [])})
