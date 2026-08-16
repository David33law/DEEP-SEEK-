"""Visible Observatory replay harness using the existing CandidateHost isolation seat."""
import json
import os
import time

import observatory_casegen as casegen
import observatory_grade as grade
from observatory_host import ObservatoryCandidateHost


def build_visible_suite(out_path, seeds=(1312, 2718, 3141, 5772)):
    suite = {
        "suite": "national-observatory-visible-replay-v1",
        "seeds": list(seeds),
        "scenarios": [casegen.make_scenario(int(s), f"VISIBLE-{i:02d}") for i, s in enumerate(seeds)],
    }
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(suite, f, ensure_ascii=False, indent=1, sort_keys=True)
    return suite


def load_suite(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def label_free_script(scenario):
    return [{"m": step["m"], "a": step.get("a", {})} for step in scenario["steps"]]


def _run_script(candidate_source, script, backend, timeout=60):
    return ObservatoryCandidateHost(candidate_source, backend=backend, timeout=timeout).run_session(script)


def run_suite(candidate_source, suite, backend="subprocess", timeout=60):
    reports, latencies = [], []
    iso = None
    for scenario in suite["scenarios"]:
        host = ObservatoryCandidateHost(candidate_source, backend=backend, timeout=timeout)
        t0 = time.monotonic()
        try:
            responses = host.run_session(label_free_script(scenario))
        except Exception as exc:  # candidate failure is measured, never promoted to harness failure
            responses = []
            rep = {
                "status": "CANDIDATE_ERROR",
                "dimension_scores": {d: 0.0 for d in casegen.DIMENSIONS},
                "diagnostics": [{"class": "CANDIDATE_ERROR", "detail": str(exc)[:500]}],
            }
        else:
            rep = grade.grade_session(scenario, responses)
        latencies.append(time.monotonic() - t0)
        reports.append(rep)
        if iso is None:
            iso = host.isolation_report()
    merged = grade.merge_reports(reports)
    ordered = sorted(latencies)
    if ordered:
        idx = min(len(ordered) - 1, max(0, int(round(0.95 * (len(ordered) - 1)))))
        p95 = ordered[idx]
    else:
        p95 = 9999.0
    merged["publication_latency"] = round(p95, 6)
    merged["isolation"] = iso or {}
    merged["scenario_statuses"] = [r.get("status") for r in reports]
    return merged


def _result(envelope):
    if not isinstance(envelope, dict) or envelope.get("error"):
        return None
    return envelope.get("r")


def _binding_tuple(result):
    if not isinstance(result, dict):
        return None
    return (result.get("canonical_id"), result.get("status"), result.get("text"),
            tuple(result.get("evidence_chain") or []))


def _expected_subset(step, result):
    return isinstance(result, dict) and all(result.get(k) == v for k, v in step.get("expect", {}).items())


def _visible_literals(suite):
    literals = set()
    for sc in suite.get("scenarios", []):
        for sid in sc.get("metadata", {}).get("source_ids", []):
            if isinstance(sid, str) and len(sid) >= 8:
                literals.add(sid)
        for step in sc.get("steps", []):
            for v in step.get("expect", {}).values():
                if isinstance(v, str) and len(v) >= 12 and v not in {
                    "ACTIVE", "SUSPENDED", "REPEALED", "DOCTRINE", "AMENDMENT",
                    "CORRECTION", "SUSPENSION", "REVIVAL", "REPEAL"}:
                    literals.add(v)
    return sorted(literals)


def fidelity(candidate_source, suite, backend="subprocess", timeout=60):
    """Causal visible-suite check, not a self-description score.

    Amendment and correction must be load-bearing: removing the event must change the state to
    the earlier expected state. Doctrine must be non-load-bearing for binding law: inserting it
    must NOT change canonical status/text/provenance. The candidate also fails if its source
    contains generated visible ids/text literals.
    """
    literal_matches = [x for x in _visible_literals(suite) if x in candidate_source]
    probes = []
    for scenario in suite.get("scenarios", [])[:3]:
        steps = scenario["steps"]
        # Stable indices are part of observatory_casegen v1 and therefore grader-frozen.
        try:
            base, duplicate, amendment = steps[0], steps[1], steps[2]
            before_amend, after_amend = steps[3], steps[4]
            correction, after_corr = steps[5], steps[7]
            doctrine = steps[9]
        except (IndexError, TypeError):
            continue

        # Amendment ablation: after-amend query should fall back to pre-amend state when the
        # amendment event is removed.
        try:
            full = _run_script(candidate_source,
                               [{"m": x["m"], "a": x.get("a", {})}
                                for x in (base, duplicate, amendment, after_amend)], backend, timeout)
            abl = _run_script(candidate_source,
                              [{"m": x["m"], "a": x.get("a", {})}
                               for x in (base, duplicate, after_amend)], backend, timeout)
            full_r, abl_r = _result(full[-1]), _result(abl[-1])
            ok = _expected_subset(after_amend, full_r) and _expected_subset(before_amend, abl_r)
        except Exception:
            ok = False
        probes.append(("amendment-load-bearing", ok))

        # Correction ablation: query with knowledge after correction must show corrected text
        # only if the correction event was actually ingested.
        try:
            full = _run_script(candidate_source,
                               [{"m": x["m"], "a": x.get("a", {})}
                                for x in (base, duplicate, amendment, correction, after_corr)], backend, timeout)
            abl = _run_script(candidate_source,
                              [{"m": x["m"], "a": x.get("a", {})}
                               for x in (base, duplicate, amendment, after_corr)], backend, timeout)
            full_r, abl_r = _result(full[-1]), _result(abl[-1])
            ok = _expected_subset(after_corr, full_r) and _expected_subset(after_amend, abl_r)
        except Exception:
            ok = False
        probes.append(("correction-load-bearing", ok))

        # Doctrine is a negative control: adding scholarly material may enrich links but must not
        # alter the binding state of the provision.
        try:
            plain = _run_script(candidate_source,
                                [{"m": x["m"], "a": x.get("a", {})}
                                 for x in (base, duplicate, amendment, correction, after_corr)], backend, timeout)
            with_doc = _run_script(candidate_source,
                                   [{"m": x["m"], "a": x.get("a", {})}
                                    for x in (base, duplicate, amendment, correction, doctrine, after_corr)], backend, timeout)
            ok = _binding_tuple(_result(plain[-1])) == _binding_tuple(_result(with_doc[-1]))
        except Exception:
            ok = False
        probes.append(("doctrine-binding-invariance", ok))

    passed = [name for name, ok in probes if ok]
    total = max(1, len(probes))
    ratio = sum(1 for _, ok in probes if ok) / total
    # All three causal families must be demonstrated at least once and at least 80% of all
    # repeated probes must pass. This prevents one lucky chain from certifying fidelity.
    families = {name for name, ok in probes if ok}
    required = {"amendment-load-bearing", "correction-load-bearing", "doctrine-binding-invariance"}
    exercised = required.issubset(families) and ratio >= 0.8 and not literal_matches
    return {"mechanism_exercised": exercised,
            "ablation_drop": round(ratio, 6),
            "load_bearing_slices": sorted(families),
            "visible_literal_matches": literal_matches[:20],
            "probes": [{"id": n, "pass": ok} for n, ok in probes]}


def source_complexity(candidate_source):
    lines = [ln for ln in candidate_source.splitlines() if ln.strip() and not ln.lstrip().startswith("#")]
    return round(min(1.0, len(lines) / 5000.0), 6)


def dimension_vector(candidate_source, report, kind="baseline", files_written=1, migration_cost=None):
    s = dict(report.get("dimension_scores", {}))
    s["external_model_dependence"] = 0.0
    s["publication_latency"] = float(report.get("publication_latency", 9999.0))
    s["trusted_kernel_complexity"] = source_complexity(candidate_source)
    s["migration_cost"] = float(migration_cost if migration_cost is not None else min(4, max(1, files_written)))
    return s
