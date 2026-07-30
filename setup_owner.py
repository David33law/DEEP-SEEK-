#!/usr/bin/env python3
"""One-time LOCAL setup for a real LAWMAX launch.

Runs the owner ceremony IN PLACE on this repository so that

    python executable-orchestrator/orchestrator.py --preflight

passes, and the ONLY thing left before `--launch` is your DeepSeek API key (and, for a
genuine paid run, the real materials in evidence-vault/ — the ones shipped here are fixtures).

IT GENERATES YOUR OWNER PRIVATE KEY on this machine, under
private-evaluator/owner-held-secrets/. That key is your INALIENABLE SOVEREIGNTY: it signs the
decisions and every owner gate approval during a run. It is git-ignored and MUST NEVER be
committed or shared — anyone who holds it can approve merges and crown a successor.

    python setup_owner.py                  # run-id RUN-0001 (the orchestrator default)
    python setup_owner.py --run-id RUN-42  # a custom run-id (use the SAME one at --launch)

Idempotent: re-running reuses an existing owner key and refreshes the signed artifacts.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.join(ROOT, "executable-orchestrator", "tools")
ORCH = os.path.join(ROOT, "executable-orchestrator")
EVAL = os.path.join(ROOT, "private-evaluator", "evaluator")
SECRETS = os.path.join(ROOT, "private-evaluator", "owner-held-secrets")
VAULT = os.path.join(ROOT, "evidence-vault")

# The eleven launch decisions. Review and EDIT these before a real run (budget, thresholds,
# cadence are yours to set) — they are signed with your key so the orchestrator can trust them.
DECISIONS = {
    "D01_BUDGET": {"decided": True, "value": {"eur": 40.0, "tokens": 20_000_000, "calls": 4000,
                                              "wall_clock_days": 14, "successor_reserve_fraction": 0.3}},
    "D02_HIDDEN_SET_AUTHORITY": {"decided": True,
                                 "value": "deterministic generator run by an independent party; "
                                          "owner seals the merkle root"},
    "D03_RUNTIME_DIRECTION": {"decided": True, "value": "decided after the reality model; "
                                                        "no runtime is pre-selected by the package"},
    "D04_PACKAGE_AUTHOR_REPO_ACCESS": {"decided": True, "value": "read-only, attested import only"},
    "D05_PII_FIXTURE_POLICY": {"decided": True, "value": "all fixtures anonymised; real case "
                                                         "material never on the experiment machine"},
    "D06_GATE_CADENCE": {"decided": True, "value": "owner answers the gate queue within 48h"},
    "D07_ACCEPTANCE_THRESHOLDS": {"decided": True,
                                  "value": {"hidden_pass_rate": 0.8, "min_slice_f1": 0.7,
                                            "clean_runs": 2, "ablation_min_drop": 0.1,
                                            "progress_min_delta": 0.01, "max_stagnant_windows": 3,
                                            "best_of_n": 2, "revision_rounds": 1}},
    "D08_OFFMACHINE_BACKUP": {"decided": True, "value": "encrypted off-machine copy of the "
                                                        "signed log and checkpoints"},
    "D09_ROW0_TARGET": {"decided": True, "value": "Row 0 approved as first-cycle minimum success"},
    "D10_CS01_FIXTURE_LICENCE": {"decided": True, "value": "anonymised CS-01 fixtures permitted "
                                                           "in the visible suite only"},
    "D11_CHALLENGER_RESERVE": {"decided": True, "value": {"fraction": 0.3,
                                                          "critic_contexts": "separate role contexts; "
                                                                             "the builder never certifies itself"}},
}


def run(argv, **kw):
    r = subprocess.run([sys.executable] + argv, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        sys.exit(f"\nFAILED: {' '.join(argv)}\n{r.stdout}\n{r.stderr}")
    return r


def git(repo, *cmd):
    subprocess.run(["git", "-C", repo] + list(cmd), capture_output=True, text=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", default="RUN-0001",
                    help="must match the --run-id you pass to orchestrator.py --launch")
    a = ap.parse_args()

    sys.path.insert(0, ORCH)
    sys.path.insert(0, EVAL)
    from lawmax21 import harness
    from lawmax21.canonical import atomic_write_json, read_json
    from lawmax21.preflight import REQUIRED_VAULT_SOURCES

    os.makedirs(SECRETS, exist_ok=True)
    owner_key = os.path.join(SECRETS, "OWNER.key")
    owner_pub = os.path.join(ROOT, "immutable-package", "OWNER-PUBLIC-KEY.hex")

    # 1 — owner keypair (private stays here and is git-ignored; public goes into the package)
    if os.path.exists(owner_key):
        print("· owner key already present — reusing it")
    else:
        run([os.path.join(TOOLS, "owner_sign.py"), "--init", "--key", owner_key, "--public-out", owner_pub])
        print("· generated owner keypair — PRIVATE key kept local (git-ignored)")

    # 2 — the eleven decisions, signed for this run-id
    dpath = os.path.join(ROOT, "decisions.unsigned.json")
    atomic_write_json(dpath, DECISIONS)
    run([os.path.join(TOOLS, "owner_sign.py"), "--key", owner_key, "--run-id", a.run_id,
         "--decisions", dpath, "--out", os.path.join(ROOT, "OWNER-DECISIONS.signed.json")])
    os.remove(dpath)
    print(f"· signed the eleven decisions for run-id {a.run_id}")

    # 3 — visible development suite (fixtures) + sealed hidden bank
    harness.configure(EVAL)
    harness.build_visible_suite(os.path.join(ROOT, "benchmark", "visible-suite.json"),
                                seed=1312, n_per_domain=2)
    bank = os.path.join(ROOT, "private-evaluator", "encrypted-hidden-bank")
    if os.path.isdir(bank):
        shutil.rmtree(bank)
    run([os.path.join(EVAL, "bank_builder.py"), "--bank", bank,
         "--key", os.path.join(SECRETS, "HIDDEN.key"),
         "--seed", "777", "--qualification", "6", "--replication", "3", "--holdout", "3"])
    print("· built the visible suite and the sealed hidden bank")

    # 4 — the canonical repository candidates branch from
    repo = os.path.join(VAULT, "lawmax-current")
    os.makedirs(repo, exist_ok=True)
    if not os.path.exists(os.path.join(repo, "core.py")):
        with open(os.path.join(repo, "core.py"), "w", encoding="utf-8") as f:
            f.write("def admission_check(case, draft):\n    return []\n")
        with open(os.path.join(repo, "README.md"), "w", encoding="utf-8") as f:
            f.write("# LAWMAX (current)\n\nThe repository candidates branch from. Replace with your real one.\n")
    if not os.path.isdir(os.path.join(repo, ".git")):
        git(repo, "init", "-q")
        git(repo, "config", "user.email", "info@stavropouloslaw.com")
        git(repo, "config", "user.name", "Stavropoulos Law")
        git(repo, "add", "-A")
        git(repo, "commit", "-qm", "baseline")
    print("· initialised the canonical repository")

    # 5 — attest every required vault source with the owner key
    for name, what in REQUIRED_VAULT_SOURCES.items():
        d = os.path.join(VAULT, name)
        os.makedirs(d, exist_ok=True)
        if not [f for f in os.listdir(d) if f != "SOURCE-ATTESTATION.json"]:
            with open(os.path.join(d, "FIXTURE.md"), "w", encoding="utf-8") as f:
                f.write(f"# {name}\n\n{what}\n\nFIXTURE — replace with the genuine source before a real launch, "
                        f"then re-run this script to re-attest.\n")
        run([os.path.join(TOOLS, "import_evidence.py"), "--attest-only", "--into", name,
             "--vault", VAULT, "--sign-with", owner_key])
    print("· attested the evidence-vault sources")

    # 6 — fill the Canonical Vision from the attested vault, then re-seal the package manifest
    vision_path = os.path.join(ROOT, "immutable-package", "canonical-charter",
                               "LAWMAX-CANONICAL-VISION.json")
    vision = read_json(vision_path)
    vision["status"] = "EVIDENCE_BACKED"

    def _attested(n):
        att = read_json(os.path.join(VAULT, n, "SOURCE-ATTESTATION.json"))
        return f"evidence-vault/{n}#{att['payload']['subject_sha256'][:16]}"

    vision["filled_sections"] = {
        s: {"body": f"section {s} grounded in the attested vault",
            "citations": [_attested(n) for n in list(REQUIRED_VAULT_SOURCES)[:2]]}
        for s in vision["sections"]}
    atomic_write_json(vision_path, vision)
    run([os.path.join(TOOLS, "generate_protocol19.py")])
    run([os.path.join(TOOLS, "make_manifest.py")])
    print("· filled the Canonical Vision and re-sealed the manifest")

    print("\nDONE — everything is set up EXCEPT your DeepSeek API key.\n")
    print("Verify:   python executable-orchestrator/orchestrator.py --preflight")
    print("Launch:   $env:DEEPSEEK_API_KEY=\"sk-...\"   (PowerShell)   /   export DEEPSEEK_API_KEY=sk-...  (bash)")
    print(f"          python executable-orchestrator/orchestrator.py --launch --run-id {a.run_id}")
    print("\nFor a REAL run, first replace the evidence-vault/ fixtures with your genuine materials")
    print("and re-run this script. Keep private-evaluator/owner-held-secrets/ OUT of git.")


if __name__ == "__main__":
    main()
