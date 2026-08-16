#!/usr/bin/env python3
"""Private hidden evaluator for the National Legal Observatory profile."""
import argparse
import hashlib
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cryptography.fernet import Fernet

import observatory_casegen as casegen
import observatory_grade as grade
from observatory_canaries import CANARIES
from observatory_host import ObservatoryCandidateHost
from candidate_host import CandidateFailure, IsolationUnavailable

HERE = os.path.dirname(os.path.abspath(__file__))


class EvaluationInvalidated(Exception):
    pass


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def check_grader_freeze(bank):
    p = os.path.join(bank, "GRADER-FREEZE.json")
    if not os.path.exists(p):
        raise EvaluationInvalidated("hidden bank has no GRADER-FREEZE.json")
    frozen = json.load(open(p, encoding="utf-8"))
    if frozen.get("profile") != "national-observatory":
        raise EvaluationInvalidated("hidden bank belongs to another profile")
    expected = frozen.get("frozen_at_build", {})
    actual = {name: sha256_file(os.path.join(HERE, name)) for name in expected}
    drifted = sorted(name for name in expected if expected[name] != actual[name])
    if drifted:
        raise EvaluationInvalidated("Observatory grading semantics drifted after bank seal: " + ", ".join(drifted))
    return actual


def load_shards(bank, key_path, level):
    manifest = json.load(open(os.path.join(bank, "PRIVATE-manifest.json"), encoding="utf-8"))
    if manifest.get("profile") != "national-observatory":
        raise EvaluationInvalidated("wrong hidden-bank profile")
    fer = Fernet(open(key_path, "rb").read())
    out = []
    for sid in manifest["levels"][level]:
        p = os.path.join(bank, sid + ".shard")
        if sha256_file(p) != sid:
            raise EvaluationInvalidated(f"shard commitment mismatch: {sid[:12]}…")
        out.append(json.loads(fer.decrypt(open(p, "rb").read())))
    return manifest, out


def label_free_script(scenario):
    return [{"m": step["m"], "a": step.get("a", {})} for step in scenario["steps"]]


def run_canaries(backend, timeout):
    results = []
    empty_script = []
    for name, source in sorted(CANARIES.items()):
        host = ObservatoryCandidateHost(source, backend=backend, timeout=timeout)
        denied = False
        reason = ""
        try:
            # Malicious action happens at candidate module load. If a session returns at all,
            # the isolation layer failed to deny the forbidden action.
            host.run_session(empty_script)
        except (CandidateFailure, IsolationUnavailable, Exception) as exc:  # fail/deny is expected
            denied = True
            reason = str(exc)[:300]
        results.append({"canary": name, "verdict": "DENIED" if denied else "ISOLATION_BREACH",
                        "reason": reason})
    breached = [r for r in results if r["verdict"] == "ISOLATION_BREACH"]
    if breached:
        raise EvaluationInvalidated("Observatory isolation canary executed: " + ", ".join(r["canary"] for r in breached))
    return results


def holdout_ledger_path(bank):
    return os.path.join(bank, "OBSERVATORY-HOLDOUT-USE-LEDGER.json")


def claim_holdout(bank, candidate_sha):
    p = holdout_ledger_path(bank)
    ledger = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {"uses": []}
    if ledger["uses"]:
        raise EvaluationInvalidated("Observatory holdout is already consumed")
    ledger["uses"].append({"candidate_sha256": candidate_sha})
    with open(p, "w", encoding="utf-8") as f:
        json.dump(ledger, f, indent=1, sort_keys=True)


def run_candidate(source, scenarios, backend, timeout):
    reports, latencies = [], []
    iso = None
    for scenario in scenarios:
        host = ObservatoryCandidateHost(source, backend=backend, timeout=timeout)
        t0 = time.monotonic()
        try:
            responses = host.run_session(label_free_script(scenario))
        except (CandidateFailure, IsolationUnavailable) as exc:
            rep = {"status": "CANDIDATE_ERROR",
                   "dimension_scores": {d: 0.0 for d in casegen.DIMENSIONS},
                   "diagnostics": [{"class": "CANDIDATE_ERROR", "detail": str(exc)[:300]}]}
        else:
            rep = grade.grade_session(scenario, responses)
        latencies.append(time.monotonic() - t0)
        reports.append(rep)
        if iso is None:
            iso = host.isolation_report()
    merged = grade.merge_reports(reports)
    ordered = sorted(latencies)
    idx = min(len(ordered) - 1, max(0, int(round(0.95 * (len(ordered) - 1))))) if ordered else 0
    merged["publication_latency"] = round(ordered[idx], 6) if ordered else 9999.0
    merged["isolation"] = iso or {}
    return merged


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--bank", required=True)
    ap.add_argument("--key", required=True)
    ap.add_argument("--candidate", required=True)
    ap.add_argument("--level", choices=("qualification", "replication", "holdout"), required=True)
    ap.add_argument("--backend", choices=("subprocess", "container"), default="subprocess")
    ap.add_argument("--timeout", type=int, default=60)
    ap.add_argument("--out")
    ap.add_argument("--skip-canaries", action="store_true", help=argparse.SUPPRESS)
    a = ap.parse_args(argv)

    report = {"profile": "national-observatory", "level": a.level,
              "protocol": "NATIONAL-OBSERVATORY-HIDDEN-EVALUATION-v1"}
    try:
        report["grader_freeze_verified"] = check_grader_freeze(a.bank)
        manifest, scenarios = load_shards(a.bank, a.key, a.level)
        source = open(a.candidate, encoding="utf-8").read()
        candidate_sha = hashlib.sha256(source.encode("utf-8")).hexdigest()
        report["candidate_sha256"] = candidate_sha
        if a.level == "holdout":
            claim_holdout(a.bank, candidate_sha)
        if a.skip_canaries:
            report["canaries"] = "SKIPPED — not admissible as final evidence"
        else:
            report["canaries"] = run_canaries(a.backend, a.timeout)
        measured = run_candidate(source, scenarios, a.backend, a.timeout)
        report["dimension_scores"] = measured["dimension_scores"]
        report["diagnostic_classes"] = measured["diagnostic_classes"]
        report["publication_latency"] = measured["publication_latency"]
        report["isolation"] = measured["isolation"]
        report["scenarios_evaluated"] = len(scenarios)
        report["merkle_root"] = manifest["merkle_root"]
        report["disclosed_to_builder"] = ["dimension scores", "diagnostic class counts", "p95 session latency"]
        report["never_disclosed"] = ["scenario content", "generated ids", "dates", "texts", "expected outputs", "shard ids"]
        report["status"] = "OK"
    except (EvaluationInvalidated, IsolationUnavailable) as exc:
        report["status"] = "REFUSED"
        report["reason"] = str(exc)

    text = json.dumps(report, ensure_ascii=False, indent=1, sort_keys=True)
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(text)
    print(text)
    return 0 if report["status"] == "OK" else 3


if __name__ == "__main__":
    sys.exit(main())
