#!/usr/bin/env python3
"""Zero-cost end-to-end proof for the National Legal Observatory profile.

Runs in a disposable Git clone against a localhost DeepSeek-shape provider. It proves the shared
signed state machine, owner gates, crash/resume, CP1 reuse, prior-CP2 quarantine, max V4-Pro request
policy, and the same currency-explicit provider billing seat used by production.
"""
import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ORCH = os.path.dirname(HERE)
ROOT = os.path.dirname(ORCH)
PORT = 8732
RUN_ID = "OBS-PROOF-0001"
MODEL = "deepseek-v4-pro"
EXPECTED_PRICE = {
    "currency": "USD",
    "input_cache_hit_per_mtok": 0.003625,
    "input_cache_miss_per_mtok": 0.435,
    "output_per_mtok": 0.87,
    "require_cache_split": True,
    "model": MODEL,
}


def git_argv(*args):
    cmd = ["git"]
    if os.name == "nt":
        cmd += ["-c", "core.longpaths=true"]
    return cmd + list(args)


def sh(argv, env=None, cwd=None):
    e = dict(os.environ)
    e.update(env or {})
    return subprocess.run(argv, capture_output=True, text=True, env=e, cwd=cwd)


def py(script, *args, env=None, cwd=None):
    return sh([sys.executable, script, *args], env=env, cwd=cwd)


def wait_port(port, timeout=10.0):
    end = time.time() + timeout
    while time.time() < end:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.25):
                return True
        except OSError:
            time.sleep(0.1)
    return False


def read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path, obj):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1, sort_keys=True)


def short_temp_workspace():
    if os.name != "nt":
        return tempfile.mkdtemp(prefix="observatory-proof-")
    parent = os.environ.get("OBSERVATORY_PROOF_TMP_ROOT")
    if not parent:
        drive = os.environ.get("SystemDrive") or os.path.splitdrive(os.getcwd())[0] or "C:"
        parent = os.path.join(drive + os.sep, "obs-pf")
    parent = os.path.abspath(parent)
    os.makedirs(parent, exist_ok=True)
    return tempfile.mkdtemp(prefix="p-", dir=parent)


def clone_disposable(dest):
    # The disposable clone, not the caller's mutable working tree, is what is proven. Still refuse
    # drift in proof/control sources so the launcher itself cannot be silently different from HEAD.
    r = sh(git_argv("-C", ROOT, "status", "--porcelain", "--untracked-files=all", "--",
                    "profiles/national-observatory", "run_observatory.py", "setup_observatory.py",
                    "executable-orchestrator/lawmax21", "private-evaluator/evaluator",
                    "benchmark/observatory_reference_candidate.py",
                    "executable-orchestrator/tools/run_observatory_proof.py",
                    "executable-orchestrator/tools/mock_observatory_server.py"))
    if r.returncode != 0 or (r.stdout or "").strip():
        raise RuntimeError("source checkout has uncommitted proof/Observatory code; refusing disposable proof\n"
                           + (r.stdout or "")[:3000])
    head = sh(git_argv("-C", ROOT, "rev-parse", "HEAD"))
    if head.returncode != 0:
        raise RuntimeError(head.stderr or "git rev-parse failed")
    head = (head.stdout or "").strip()
    r = sh(git_argv("clone", "--no-hardlinks", "--quiet", ROOT, dest))
    if r.returncode != 0:
        raise RuntimeError("disposable clone failed: " + (r.stderr or ""))
    r = sh(git_argv("-C", dest, "checkout", "--quiet", "--detach", head))
    if r.returncode != 0:
        raise RuntimeError("disposable checkout failed: " + (r.stderr or ""))
    return head


def to_resume(args, drop_crash=False):
    out, skip = [], False
    for x in args:
        if skip:
            skip = False
            continue
        if x == "--launch":
            out.append("--resume")
        elif drop_crash and x == "--crash-after":
            skip = True
        else:
            out.append(x)
    return out


def drive_launch(dest, target, cp1, prior, runtime, owner_key, endpoint):
    runner = os.path.join(dest, "run_observatory.py")
    signer = os.path.join(dest, "executable-orchestrator", "tools", "owner_sign.py")
    env = {"DEEPSEEK_API_KEY": "proof-token-not-a-real-key",
           "PYTHONDONTWRITEBYTECODE": "1"}
    args = ["--launch", "--run-id", RUN_ID, "--endpoint", endpoint, "--model", MODEL,
            "--backend", "subprocess", "--canonical-repo", target,
            "--cp1-evidence", cp1, "--prior-cp2", prior,
            "--runtime", runtime, "--max-rounds", "4", "--crash-after", "6"]
    transcript, gates = [], []
    crash_pending, crashed_and_resumed = True, False
    for attempt in range(30):
        r = py(runner, *args, env=env, cwd=dest)
        transcript.append({"attempt": attempt, "rc": r.returncode,
                           "stdout_tail": (r.stdout or "")[-1800:],
                           "stderr_tail": (r.stderr or "")[-1800:]})
        if r.returncode == 10:
            info = read_json(os.path.join(runtime, "gates", "AWAITING-OWNER.json"))
            s = py(signer, "--key", owner_key, "--gate", info["awaiting"], "--run-id", RUN_ID,
                   "--subject", info["subject"], "--decision", "APPROVE",
                   "--out", info["approval_expected_at"], cwd=dest)
            if s.returncode != 0:
                raise RuntimeError("proof owner gate signing failed: " + (s.stdout or "") + (s.stderr or ""))
            gates.append(info["awaiting"])
            args = to_resume(args, drop_crash=True)
            crash_pending = False
            continue
        if r.returncode == 0:
            return {"completed": True, "gates": gates, "transcript": transcript,
                    "crashed_and_resumed": crashed_and_resumed}
        if crash_pending:
            crash_pending = False
            crashed_and_resumed = True
            args = to_resume(args, drop_crash=True)
            continue
        return {"completed": False, "gates": gates, "transcript": transcript,
                "crashed_and_resumed": crashed_and_resumed}
    return {"completed": False, "gates": gates, "transcript": transcript,
            "crashed_and_resumed": crashed_and_resumed}


def assert_price_schedule(schedule):
    for key, expected in EXPECTED_PRICE.items():
        if schedule.get(key) != expected:
            raise RuntimeError(f"signed/provider price schedule mismatch for {key}: "
                               f"{schedule.get(key)!r} != {expected!r}")


def verify_currency_accounting(runtime, summary, audit):
    budget = summary.get("budget") or {}
    limits = budget.get("limits") or {}
    spent = budget.get("spent") or {}
    if budget.get("currency") != "USD" or limits.get("currency") != "USD":
        raise RuntimeError("Observatory budget is not currency-explicit USD")
    if "amount" not in limits or "amount" not in spent:
        raise RuntimeError("Observatory budget did not use generic monetary amount seat")
    if "eur" in limits or "eur" in spent:
        raise RuntimeError("legacy EUR monetary seat leaked into Observatory budget")
    assert_price_schedule(limits.get("price_schedule") or {})
    if not audit.get("budget_within_ceiling") or audit.get("currency") != "USD":
        raise RuntimeError("independent audit did not certify USD budget ceiling")
    assert_price_schedule((audit.get("provider") or {}).get("price_schedule") or {})

    ledger = read_json(os.path.join(runtime, "budget", "ledger.json"))
    entries = ledger.get("entries") or []
    if not entries:
        raise RuntimeError("currency proof found no settled model-call ledger entries")
    for i, entry in enumerate(entries):
        usage = entry.get("usage") or {}
        if entry.get("currency") != "USD" or usage.get("billing_currency") != "USD":
            raise RuntimeError(f"ledger entry {i} has wrong billing currency")
        hit = usage.get("prompt_cache_hit_tokens")
        miss = usage.get("prompt_cache_miss_tokens")
        prompt = usage.get("prompt_tokens")
        if hit is None or miss is None or prompt is None or int(hit) + int(miss) != int(prompt):
            raise RuntimeError(f"ledger entry {i} lacks exact V4 cache hit/miss accounting")
        if "billing_amount" not in usage or float(usage["billing_amount"]) < 0:
            raise RuntimeError(f"ledger entry {i} lacks nonnegative provider billing amount")
    return {"currency": "USD", "settled_calls_checked": len(entries),
            "spent_amount": spent["amount"],
            "cache_split_verified_every_call": True,
            "signed_price_schedule_verified": True}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--canonical-repo", required=True,
                    help="exact isolated STAVROPOULOSLAWCORPUS CP1 checkout")
    ap.add_argument("--cp1-evidence", required=True,
                    help="sealed evidence directory containing CP1 map + verification receipt")
    ap.add_argument("--prior-cp2", required=True,
                    help="sealed prior CP2 directory; may be the same sealed evidence root")
    ap.add_argument("--keep", action="store_true")
    a = ap.parse_args(argv)

    target, cp1, prior = map(os.path.abspath, (a.canonical_repo, a.cp1_evidence, a.prior_cp2))
    temp = short_temp_workspace()
    dest = os.path.join(temp, "r")
    runtime = os.path.join(temp, "rt")
    mock = None
    result = {"proof": "national-observatory-zero-cost-e2e-v2", "paid_api_calls": 0,
              "workspace": temp, "runtime": runtime,
              "path_budget": {"workspace_chars": len(temp), "runtime_chars": len(runtime),
                              "windows_longpaths_git": os.name == "nt"}}
    try:
        source_head = clone_disposable(dest)
        result["source_head"] = source_head

        setup = py(os.path.join(dest, "setup_observatory.py"), "--run-id", RUN_ID,
                   "--budget-usd", "25", "--tokens", "10000000", "--calls", "3000", "--days", "3",
                   "--qualification", "3", "--replication", "2", "--holdout", "2", cwd=dest)
        result["setup"] = {"rc": setup.returncode, "tail": ((setup.stdout or "") + (setup.stderr or ""))[-2500:]}
        if setup.returncode != 0:
            raise RuntimeError("setup_observatory failed\n" + result["setup"]["tail"])

        owner_key = os.path.join(dest, "private-evaluator", "owner-held-secrets", "OWNER.key")
        endpoint = f"http://127.0.0.1:{PORT}/chat/completions"
        # Preflight is local/subprocess here because container readiness is a separate production
        # proof. The signed owner budget/model contract is nevertheless the exact production one.
        pre = py(os.path.join(dest, "run_observatory.py"), "--preflight", "--run-id", RUN_ID,
                 "--endpoint", endpoint, "--model", MODEL, "--backend", "subprocess",
                 "--runtime", runtime, "--canonical-repo", target,
                 "--cp1-evidence", cp1, "--prior-cp2", prior, cwd=dest)
        result["preflight"] = {"rc": pre.returncode, "tail": ((pre.stdout or "") + (pre.stderr or ""))[-3500:]}
        if pre.returncode != 0:
            raise RuntimeError("Observatory preflight failed\n" + result["preflight"]["tail"])

        mock_script = os.path.join(dest, "executable-orchestrator", "tools", "mock_observatory_server.py")
        mock = subprocess.Popen([sys.executable, mock_script, "--port", str(PORT)],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if not wait_port(PORT):
            out, err = mock.communicate(timeout=2)
            raise RuntimeError("Observatory mock server did not start\n" + (out or "") + (err or ""))

        run = drive_launch(dest, target, cp1, prior, runtime, owner_key, endpoint)
        result["launch"] = run
        if not run["completed"]:
            raise RuntimeError("shared state-machine rehearsal did not complete")
        if not run["crashed_and_resumed"]:
            raise RuntimeError("crash/resume drill did not actually crash and resume")

        summary = read_json(os.path.join(runtime, "reports", "run_summary.json"))
        result["run_summary"] = summary
        if summary.get("final_state") != "COMMITTED":
            raise RuntimeError(f"expected COMMITTED, got {summary.get('final_state')}")
        if not summary.get("log_verified"):
            raise RuntimeError("signed event log did not verify")
        spent = summary.get("budget", {}).get("spent", {})
        if int(spent.get("calls", 0)) <= 0:
            raise RuntimeError("mock HTTP path recorded zero model calls")

        # Observatory terminal proof must be semantically clean: no inherited LAWMAX consciousness
        # or integration-credit placeholders may survive in the profile artifact.
        escalation = summary.get("escalation") or {}
        conditions = escalation.get("conditions") or {}
        forbidden_terminal = {"consciousness", "integration_attested",
                              "integration_credited_candidate", "credited_layers"}
        leaked = sorted(forbidden_terminal & set(escalation))
        if leaked or "consciousness_real" in conditions:
            raise RuntimeError(f"legacy LAWMAX terminal semantics leaked into Observatory proof: "
                               f"fields={leaked}, consciousness_real={'consciousness_real' in conditions}")

        reality = read_json(os.path.join(runtime, "reality", "REPOSITORY-REALITY-MODEL.json"))
        history = read_json(os.path.join(runtime, "reality", "HISTORICAL-EXPERIMENT-MAP.json"))
        proposals = read_json(os.path.join(runtime, "architecture", "proposals.json"))
        if reality.get("repository_archaeology_api_calls") != 0:
            raise RuntimeError("CP1 reuse proof failed: repository archaeology model calls were made")
        if history.get("prior_cp2_content_read") is not False:
            raise RuntimeError("prior CP2 quarantine proof failed before new frontier")
        if proposals.get("prior_cp2_visible") is not False:
            raise RuntimeError("prior CP2 was visible during independent Observatory proposal generation")
        result["cp1_reused_without_api"] = True
        result["prior_cp2_quarantined_during_new_discovery"] = True

        audit = read_json(os.path.join(runtime, "audit", "independent_audit.json"))
        if not audit.get("immutable_package_unchanged") or audit.get("hidden_disclosed_to_builder"):
            raise RuntimeError("independent audit failed immutable/hidden invariants")
        result["independent_audit"] = audit
        result["currency_accounting"] = verify_currency_accounting(runtime, summary, audit)
        result["status"] = "PASS"
    except Exception as exc:
        result["status"] = "FAIL"
        result["reason"] = str(exc)
    finally:
        if mock is not None:
            mock.terminate()
            try:
                mock.wait(timeout=3)
            except subprocess.TimeoutExpired:
                mock.kill()
        proof_dir = os.path.join(ROOT, "proof")
        os.makedirs(proof_dir, exist_ok=True)
        out = os.path.join(proof_dir, "national-observatory-zero-cost-e2e.json")
        write_json(out, result)
        print(json.dumps(result, ensure_ascii=False, indent=1, sort_keys=True))
        print("proof report:", out)
        if a.keep or result.get("status") != "PASS":
            print("disposable proof directory retained:", temp)
        else:
            shutil.rmtree(temp, ignore_errors=True)
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
