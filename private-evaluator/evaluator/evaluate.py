#!/usr/bin/env python3
"""Private evaluator. Holds the key and the ground truth; never executes candidate code.

Order of operations is itself a guarantee:

  1. verify the graders still match the freeze recorded when the bank was built
  2. run the CANARIES — known-hostile candidates that try to steal the answers
  3. only if every canary was DENIED, evaluate the real candidate
  4. emit diagnostic classes and per-slice scores. No case, no span, no answer.

Step 2 is the part v2.0 lacked. An isolation regression can no longer sit undetected:
if the argv-theft canary ever scores, this tool reports EVALUATION_INVALIDATED and the
run cannot proceed, because the same defect would let the real candidate cheat.
"""
import argparse
import glob
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cryptography.fernet import Fernet

import casegen
import grade as G
from candidate_host import CandidateFailure, CandidateHost, IsolationUnavailable

HERE = os.path.dirname(os.path.abspath(__file__))
CANARY_DIR = os.path.join(HERE, "canaries")


class EvaluationInvalidated(Exception):
    pass


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def check_grader_freeze(bank):
    fp = os.path.join(bank, "GRADER-FREEZE.json")
    if not os.path.exists(fp):
        raise EvaluationInvalidated("bank has no GRADER-FREEZE.json — provenance of the questions is unknown")
    frozen = json.load(open(fp, encoding="utf-8"))["frozen_at_build"]
    now = {f: sha256_file(os.path.join(HERE, f)) for f in frozen}
    drifted = [f for f in frozen if frozen[f] != now[f]]
    if drifted:
        raise EvaluationInvalidated(
            f"grading semantics changed after the bank was sealed ({', '.join(drifted)}) — "
            "the hidden set no longer measures what it committed to measure"
        )
    return frozen


def load_shards(bank, key_path, level):
    manifest = json.load(open(os.path.join(bank, "PRIVATE-manifest.json"), encoding="utf-8"))
    fer = Fernet(open(key_path, "rb").read())
    out = []
    for sid in manifest["levels"][level]:
        path = os.path.join(bank, sid + ".shard")
        if sha256_file(path) != sid:
            raise EvaluationInvalidated(f"shard {sid[:12]}… does not match its committed hash")
        out.append((sid, json.loads(fer.decrypt(open(path, "rb").read()))))
    return manifest, out


def run_candidate(source, shards, backend, timeout, probe_layers=False):
    """Grade one candidate. The plaintext `answers` never leave this function's frame."""
    import layer_probes

    host = CandidateHost(source, backend=backend, timeout=timeout)
    acc = G.empty_tally()
    classes = {c: 0 for c in G.DIAGNOSTIC_CLASSES}
    denials = []
    higher_layers = set()
    first_case = None
    for sid, data in shards:
        payload_case, payload_draft = data["case"], data["draft"]  # label-free by construction
        if first_case is None:
            first_case = (payload_case, payload_draft)
        try:
            flags = host.detect(payload_case, payload_draft)
        except CandidateFailure as e:
            classes["CANDIDATE_ERROR"] += 1
            denials.append(str(e)[:200])
            continue
        cls, tally = G.grade_case(payload_case, payload_draft, data["answers"]["expected_flags"], flags)
        classes[cls] += 1
        G.merge_tally(acc, tally)

    # The upward gradient: run the higher-layer sensors ONCE, on the first case, so a
    # candidate that reaches L5/L6/L9/L11/L12 is measurably credited and a document-risk
    # detector that stops at L4 measurably does not. Bounded to one case to keep it cheap.
    layer_results, consciousness = {}, {}
    if probe_layers and first_case is not None:
        import consciousness_probe

        c0, d0 = first_case
        try:
            flags0 = host.detect(c0, d0)
        except CandidateFailure:
            flags0 = []
        layer_results = layer_probes.run_all(host, c0, d0, flags0)
        higher_layers = set(layer_probes.demonstrated(layer_results))
        # Consciousness as results, not philosophy — the owner's own audit, run in isolation.
        consciousness = consciousness_probe.run(host, shards, classes.get('TRACE_INVALID', 0))
    return (classes, acc, denials, host.isolation_report(),
            sorted(higher_layers), layer_results, consciousness)


def run_canaries(shards, backend, timeout):
    """Every canary must fail to score. A canary that passes invalidates the run."""
    results = []
    for path in sorted(glob.glob(os.path.join(CANARY_DIR, "ATTACK-*.py"))):
        src = open(path, encoding="utf-8").read()
        classes, acc, denials, _, _, _, _ = run_candidate(src, shards, backend, timeout)
        scored = classes["PASS"] > 0
        results.append({
            "canary": os.path.basename(path),
            "passes_scored": classes["PASS"],
            "candidate_errors": classes["CANDIDATE_ERROR"],
            "denied": bool(denials),
            "first_denial": denials[0] if denials else None,
            "verdict": "DEFEATED_THE_ISOLATION" if scored else "DENIED",
        })
    breached = [r for r in results if r["verdict"] == "DEFEATED_THE_ISOLATION"]
    if breached:
        raise EvaluationInvalidated(
            "EVALUATION_INVALIDATED — hidden-set isolation is broken: "
            + ", ".join(r["canary"] for r in breached)
        )
    return results


def holdout_ledger_path(bank):
    return os.path.join(bank, "HOLDOUT-USE-LEDGER.json")


def claim_holdout(bank, candidate_sha):
    """The holdout is single-use, enforced on the owner side by an append-only ledger."""
    p = holdout_ledger_path(bank)
    ledger = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {"uses": []}
    if ledger["uses"]:
        raise EvaluationInvalidated(
            f"holdout already consumed by candidate {ledger['uses'][0]['candidate_sha256'][:16]}… — "
            "a second use would destroy its meaning"
        )
    ledger["uses"].append({"candidate_sha256": candidate_sha})
    with open(p, "w", encoding="utf-8") as f:
        json.dump(ledger, f, indent=1)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Evaluate a candidate against the hidden bank.")
    ap.add_argument("--bank", required=True)
    ap.add_argument("--key", required=True)
    ap.add_argument("--candidate", required=True)
    ap.add_argument("--level", choices=("qualification", "replication", "holdout"), required=True)
    ap.add_argument("--backend", choices=("subprocess", "container"), default="subprocess")
    ap.add_argument("--timeout", type=int, default=60)
    ap.add_argument("--out", help="write the builder-visible report here")
    ap.add_argument("--skip-canaries", action="store_true",
                    help=argparse.SUPPRESS)  # test-only; recorded in the report when used
    a = ap.parse_args(argv)

    report = {"level": a.level, "protocol": "09-HIDDEN-EVALUATION-PROTOCOL v2.1"}
    try:
        report["grader_freeze_verified"] = check_grader_freeze(a.bank)
        manifest, shards = load_shards(a.bank, a.key, a.level)
        source = open(a.candidate, encoding="utf-8").read()
        cand_sha = hashlib.sha256(source.encode("utf-8")).hexdigest()
        report["candidate_sha256"] = cand_sha

        if a.level == "holdout":
            claim_holdout(a.bank, cand_sha)

        if a.skip_canaries:
            report["canaries"] = "SKIPPED — report is not admissible as evidence"
        else:
            report["canaries"] = run_canaries(shards, a.backend, a.timeout)

        classes, acc, denials, iso, higher_layers, layer_results, consciousness = run_candidate(
            source, shards, a.backend, a.timeout, probe_layers=True)
        report["isolation"] = iso
        report["higher_layers_demonstrated"] = higher_layers
        report["layer_probe_results"] = layer_results
        report["consciousness"] = consciousness
        report["diagnostic_classes"] = classes
        report["slice_scores"] = G.slice_scores(acc, casegen.SLICES)
        report["cases_evaluated"] = len(shards)
        report["merkle_root"] = manifest["merkle_root"]
        report["disclosed_to_builder"] = ["diagnostic class counts", "per-slice precision/recall/F1",
                                          "which higher layers were demonstrated"]
        report["never_disclosed"] = ["case content", "span text", "expected flags", "domain names",
                                     "shard ids", "which cases failed"]
        report["status"] = "OK"
    except (EvaluationInvalidated, IsolationUnavailable) as e:
        report["status"] = "REFUSED"
        report["reason"] = str(e)

    text = json.dumps(report, ensure_ascii=False, indent=1, sort_keys=True)
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(text)
    print(text)
    return 0 if report["status"] == "OK" else 3


if __name__ == "__main__":
    sys.exit(main())
