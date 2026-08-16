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


def source_complexity(candidate_source):
    lines = [ln for ln in candidate_source.splitlines() if ln.strip() and not ln.lstrip().startswith("#")]
    # Normalised but monotonic. The frontier treats lower as better; no hard minimum is attached.
    return round(min(1.0, len(lines) / 5000.0), 6)


def dimension_vector(candidate_source, report, kind="baseline", files_written=1, migration_cost=None):
    s = dict(report.get("dimension_scores", {}))
    # The sandbox has no network and the contract has no model callback, so any candidate that
    # actually evaluated has zero inference-time external-model dependence on the trusted path.
    s["external_model_dependence"] = 0.0
    s["publication_latency"] = float(report.get("publication_latency", 9999.0))
    s["trusted_kernel_complexity"] = source_complexity(candidate_source)
    s["migration_cost"] = float(migration_cost if migration_cost is not None else min(4, max(1, files_written)))
    # Fail closed if an expected measurement disappeared: Frontier._check will reject an
    # incomplete vector rather than inventing a score.
    return s
