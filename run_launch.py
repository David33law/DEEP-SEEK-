#!/usr/bin/env python3
"""Run a LAWMAX launch end-to-end with ONE command — no manual setup, no manual gates.

    set DEEPSEEK_API_KEY, then:  python run_launch.py

What it does:
  1. If the machine is not set up yet (no owner key), it runs setup_owner.py for you
     (generates your owner key LOCALLY — it is git-ignored, never uploaded).
  2. It starts the launch and, every time the run pauses for an owner gate, it approves the
     gate automatically with that key and continues — until the run finishes (COMMITTED, i.e.
     a proven ceiling, or BEST_DISCOVERED_SO_FAR).

Rehearse without spending money by pointing at the bundled mock DeepSeek:
    python run_launch.py --endpoint http://127.0.0.1:8731/chat/completions
(start it first in another terminal:  python executable-orchestrator/tools/mock_deepseek_server.py)
"""
import argparse
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
ORCH = os.path.join(ROOT, "executable-orchestrator", "orchestrator.py")
TOOLS = os.path.join(ROOT, "executable-orchestrator", "tools")
OWNER_KEY = os.path.join(ROOT, "private-evaluator", "owner-held-secrets", "OWNER.key")
sys.path.insert(0, os.path.join(ROOT, "executable-orchestrator"))
from lawmax21.canonical import read_json  # noqa: E402

AWAITING_OWNER_RC = 10   # orchestrator exit code meaning "paused for an owner gate"


def _run(argv, env=None):
    return subprocess.run(argv, env=env)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", default="RUN-0001")
    ap.add_argument("--endpoint",
                    default=os.environ.get("DEEPSEEK_ENDPOINT", "https://api.deepseek.com/chat/completions"))
    ap.add_argument("--model", default=os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"))
    ap.add_argument("--max-rounds", default=os.environ.get("LAWMAX_MAX_ROUNDS", "6"))
    ap.add_argument("--runtime", default=os.path.join(ROOT, "runtime"))
    a = ap.parse_args()

    is_mock = "127.0.0.1" in a.endpoint or "localhost" in a.endpoint
    if not os.environ.get("DEEPSEEK_API_KEY"):
        if is_mock:
            os.environ["DEEPSEEK_API_KEY"] = "mock-token"   # the mock ignores it; real runs need a real key
        else:
            sys.exit("Set DEEPSEEK_API_KEY first  (PowerShell:  $env:DEEPSEEK_API_KEY=\"sk-...\").")

    # 1 — set up on first use
    if not os.path.exists(OWNER_KEY):
        print("· first run: setting up (generating your local owner key)…")
        s = _run([sys.executable, os.path.join(ROOT, "setup_owner.py"), "--run-id", a.run_id])
        if s.returncode != 0:
            sys.exit("setup failed")

    # 2 — preflight (informative; refuses if something is genuinely missing)
    pf = subprocess.run([sys.executable, ORCH, "--preflight"], capture_output=True, text=True)
    if pf.returncode != 0 and '"ok": true' not in pf.stdout:
        print(pf.stdout[-800:])
        sys.exit("preflight refused — see above")

    repo = os.path.join(ROOT, "evidence-vault", "lawmax-current")
    env = dict(os.environ)
    env["LAWMAX_RUNTIME"] = a.runtime
    launch = [sys.executable, ORCH, "--launch", "--run-id", a.run_id, "--endpoint", a.endpoint,
              "--model", a.model, "--max-rounds", str(a.max_rounds), "--canonical-repo", repo]
    resume = [x if x != "--launch" else "--resume" for x in launch]

    args, signed = launch, 0
    for _ in range(500):
        r = _run(args, env=env)
        if r.returncode == 0:
            print(f"\n✔ launch finished ({signed} owner gate(s) auto-approved).")
            print(f"  Result is in: {a.runtime}")
            return 0
        if r.returncode == AWAITING_OWNER_RC:
            info = read_json(os.path.join(a.runtime, "gates", "AWAITING-OWNER.json"))
            s = _run([sys.executable, os.path.join(TOOLS, "owner_sign.py"), "--key", OWNER_KEY,
                      "--gate", info["awaiting"], "--run-id", a.run_id,
                      "--subject", info["subject"], "--decision", "APPROVE",
                      "--out", info["approval_expected_at"]])
            if s.returncode != 0:
                sys.exit("gate signing failed")
            signed += 1
            print(f"  · auto-approved owner gate: {info['awaiting']}")
            args = resume
            continue
        sys.exit(f"orchestrator exited with code {r.returncode} — see its output above.")
    sys.exit("too many gate cycles — aborting.")


if __name__ == "__main__":
    sys.exit(main())
