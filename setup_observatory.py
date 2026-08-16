#!/usr/bin/env python3
"""Local owner/setup ceremony for the National Legal Observatory tournament.

Zero paid calls. Builds and calibrates the profile-specific visible/hidden evaluation assets,
signs the same shared owner-decision contract, and leaves the existing LAWMAX runner intact.
"""
import argparse
import json
import os
import secrets
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
ORCH = os.path.join(ROOT, "executable-orchestrator")
TOOLS = os.path.join(ORCH, "tools")
EVAL = os.path.join(ROOT, "private-evaluator", "evaluator")
SECRETS = os.path.join(ROOT, "private-evaluator", "owner-held-secrets")
PROFILE = os.path.join(ROOT, "profiles", "national-observatory")


def run(argv):
    r = subprocess.run([sys.executable] + argv, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"FAILED: {' '.join(argv)}\n{r.stdout}\n{r.stderr}")
    return r


def decisions(budget_eur, tokens, calls, days):
    return {
        "D01_BUDGET": {"decided": True, "value": {
            "eur": float(budget_eur), "tokens": int(tokens), "calls": int(calls),
            "wall_clock_days": int(days), "successor_reserve_fraction": 0.35}},
        "D02_HIDDEN_SET_AUTHORITY": {"decided": True,
            "value": "profile-specific encrypted hidden replay bank; grader hashes frozen at bank creation"},
        "D03_RUNTIME_DIRECTION": {"decided": True,
            "value": "architecture family and production substrate remain outputs of measurement, not preset inputs"},
        "D04_PACKAGE_AUTHOR_REPO_ACCESS": {"decided": True,
            "value": "exact isolated target checkout + sealed CP1 reuse; no remote access from target"},
        "D05_PII_FIXTURE_POLICY": {"decided": True,
            "value": "synthetic legal-history fixtures only in evaluator; no client/case PII required"},
        "D06_GATE_CADENCE": {"decided": True,
            "value": "owner reviews architecture/migration/crown gates before continuation"},
        "D07_ACCEPTANCE_THRESHOLDS": {"decided": True, "value": {
            "hidden_pass_rate": 0.98, "min_slice_f1": 0.98, "clean_runs": 2,
            "ablation_min_drop": 0.20, "progress_min_delta": 0.002,
            "max_stagnant_windows": 4, "best_of_n": 4, "revision_rounds": 2}},
        "D08_OFFMACHINE_BACKUP": {"decided": True,
            "value": "encrypted off-machine copy of signed log, checkpoints and final evidence"},
        "D09_ROW0_TARGET": {"decided": True,
            "value": "Observatory profile target is all twelve executable layers; no lower row is a final crown"},
        "D10_CS01_FIXTURE_LICENCE": {"decided": True,
            "value": "not used by Observatory profile; synthetic replay fixtures only"},
        "D11_CHALLENGER_RESERVE": {"decided": True, "value": {
            "fraction": 0.35,
            "critic_contexts": "successor, radical and simplification challengers have independent role contexts"}},
    }


def hard_minimum_failures(scores, spec):
    bad = []
    for d in spec:
        hm = d.get("hard_minimum")
        if hm is None:
            continue
        v = float(scores.get(d["id"], 9999.0 if d["direction"] == "lower" else 0.0))
        if d["direction"] == "higher" and v < hm:
            bad.append((d["id"], v, hm))
        if d["direction"] == "lower" and v > hm:
            bad.append((d["id"], v, hm))
    return bad


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", default="OBS-RUN-0001")
    ap.add_argument("--budget-eur", type=float, default=500.0)
    ap.add_argument("--tokens", type=int, default=250_000_000)
    ap.add_argument("--calls", type=int, default=20_000)
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--qualification", type=int, default=12)
    ap.add_argument("--replication", type=int, default=8)
    ap.add_argument("--holdout", type=int, default=6)
    a = ap.parse_args(argv)

    sys.path.insert(0, ORCH)
    sys.path.insert(0, EVAL)
    from lawmax21.canonical import atomic_write_json, read_json
    import observatory_harness

    os.makedirs(SECRETS, exist_ok=True)
    owner_key = os.path.join(SECRETS, "OWNER.key")
    owner_pub = os.path.join(ROOT, "immutable-package", "OWNER-PUBLIC-KEY.hex")
    if not os.path.exists(owner_key):
        run([os.path.join(TOOLS, "owner_sign.py"), "--init", "--key", owner_key,
             "--public-out", owner_pub])
        print("· generated owner keypair; private key remains under owner-held-secrets/")
    else:
        print("· owner key already present — reusing")

    # OWNER-PUBLIC-KEY.hex is inside the historical package and is intentionally local-owner
    # specific. Re-seal the manifest after key creation/update; no Observatory profile file lives
    # in immutable-package, so the LAWMAX package remains internally self-consistent.
    run([os.path.join(TOOLS, "make_manifest.py")])

    unsigned = os.path.join(ROOT, "observatory-decisions.unsigned.json")
    atomic_write_json(unsigned, decisions(a.budget_eur, a.tokens, a.calls, a.days))
    run([os.path.join(TOOLS, "owner_sign.py"), "--key", owner_key, "--run-id", a.run_id,
         "--decisions", unsigned, "--out", os.path.join(ROOT, "OWNER-DECISIONS.signed.json")])
    os.remove(unsigned)
    print(f"· signed Observatory decisions for {a.run_id}")

    visible = os.path.join(ROOT, "benchmark", "observatory-visible-suite.json")
    observatory_harness.build_visible_suite(visible)
    print("· built Observatory visible replay suite")

    bank = os.path.join(ROOT, "private-evaluator", "observatory-hidden-bank")
    if os.path.isdir(bank):
        shutil.rmtree(bank)
    hidden_key = os.path.join(SECRETS, "OBSERVATORY-HIDDEN.key")
    if os.path.exists(hidden_key):
        os.remove(hidden_key)  # new bank => new key; old bank is gone, so key reuse adds no value
    bank_seed = secrets.randbelow(2**31 - 2) + 1
    r = run([os.path.join(EVAL, "observatory_bank_builder.py"), "--bank", bank,
             "--key", hidden_key, "--seed", str(bank_seed),
             "--qualification", str(a.qualification), "--replication", str(a.replication),
             "--holdout", str(a.holdout)])
    public = read_json(os.path.join(bank, "PUBLIC-commitment.json"))
    print(f"· sealed hidden bank: {public['merkle_root'][:16]}… "
          f"Q={public['counts']['qualification']} R={public['counts']['replication']} H={public['counts']['holdout']}")

    # Calibration 1: visible reference must satisfy every hard dimension available there.
    reference = os.path.join(ROOT, "benchmark", "observatory_reference_candidate.py")
    src = open(reference, encoding="utf-8").read()
    suite = read_json(visible)
    visible_report = observatory_harness.run_suite(src, suite, "subprocess")
    spec = read_json(os.path.join(PROFILE, "PARETO-DIMENSIONS.json"))
    bad_visible = hard_minimum_failures(visible_report["dimension_scores"], spec)
    if bad_visible:
        raise RuntimeError(f"visible evaluator calibration failed hard minima: {bad_visible}")
    fidelity = observatory_harness.fidelity(src, suite, "subprocess")
    if not fidelity.get("mechanism_exercised"):
        raise RuntimeError(f"visible causal-fidelity calibration failed: {fidelity}")
    print("· visible evaluator calibration PASS")

    # Calibration 2: same reference through encrypted qualification bank + isolation canaries.
    out = os.path.join(ROOT, "proof", "observatory-hidden-calibration.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    run([os.path.join(EVAL, "observatory_evaluate.py"), "--bank", bank, "--key", hidden_key,
         "--candidate", reference, "--level", "qualification", "--backend", "subprocess",
         "--out", out])
    hidden = read_json(out)
    bad_hidden = hard_minimum_failures(hidden.get("dimension_scores", {}), spec)
    if hidden.get("status") != "OK" or bad_hidden:
        raise RuntimeError(f"hidden evaluator calibration failed: status={hidden.get('status')} bad={bad_hidden}")
    if not isinstance(hidden.get("canaries"), list) or not all(x.get("verdict") == "DENIED" for x in hidden["canaries"]):
        raise RuntimeError("hidden evaluator calibration did not deny every isolation canary")
    print("· hidden evaluator + canaries calibration PASS")

    print("\nOBSERVATORY SETUP: PASS")
    print(f"run-id: {a.run_id}")
    print(f"budget: EUR {a.budget_eur}, tokens {a.tokens}, calls {a.calls}, days {a.days}")
    print("No DeepSeek/API call was made.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # one terminal FAIL, no misleading trailing PASS
        print("\nOBSERVATORY SETUP: FAIL")
        print(str(exc))
        sys.exit(1)
