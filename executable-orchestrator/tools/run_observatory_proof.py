#!/usr/bin/env python3
"""Zero-cost end-to-end proof for the National Legal Observatory profile.

Runs in a disposable Git clone. Uses the shipped setup/preflight/runner/evaluator and a localhost
DeepSeek-shape provider. Drives owner gates with a temporary owner key, injects a crash, resumes
from the signed log, and requires COMMITTED plus CP1-reuse / prior-CP2-quarantine evidence.
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


def clone_disposable(dest):
    # Prove the exact committed source, not an uncommitted working-tree variant.
    r = sh(["git", "-C", ROOT, "status", "--porcelain", "--untracked-files=all", "--",
            "profiles/national-observatory", "run_observatory.py", "setup_observatory.py",
            "executable-orchestrator/lawmax21", "private-evaluator/evaluator", "benchmark/observatory_reference_candidate.py"])
    if r.returncode != 0 or r.stdout.strip():
        raise RuntimeError("source checkout has uncommitted proof/Observatory code; refusing disposable proof\n" + r.stdout[:3000])
    head = sh(["git", "-C", ROOT, "rev-parse", "HEAD"])
    if head.returncode != 0:
        raise RuntimeError(head.stderr)
    head = head.stdout.strip()
    r = sh(["git", "clone", "--no-hardlinks", "--quiet", ROOT, dest])
    if r.returncode != 0:
        raise RuntimeError("disposable clone failed: " + r.stderr)
    r = sh(["git", "-C", dest, "checkout", "--quiet", "--detach", head])
    if r.returncode != 0:
        raise RuntimeError("disposable checkout failed: " + r.stderr)
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
    args = ["--launch", "--run-id", RUN_ID, "--endpoint", endpoint, "--model", "observatory-proof-model",
            "--backend", "subprocess", "--canonical-repo", target,
            "--cp1-evidence", cp1, "--prior-cp2", prior,
            "--runtime", runtime, "--max-rounds", "4", "--crash-after", "6"]
    transcript, gates = [], []
    crash_pending, crashed_and_resumed = True, False
    for attempt in range(30):
        r = py(runner, *args, env=env, cwd=dest)
        transcript.append({"attempt": attempt, "rc": r.returncode,
                           "stdout_tail": r.stdout[-1800:], "stderr_tail": r.stderr[-1800:]})
        if r.returncode == 10:
            info = read_json(os.path.join(runtime, "gates", "AWAITING-OWNER.json"))
            s = py(signer, "--key", owner_key, "--gate", info["awaiting"], "--run-id", RUN_ID,
                   "--subject", info["subject"], "--decision", "APPROVE",
                   "--out", info["approval_expected_at"], cwd=dest)
            if s.returncode != 0:
                raise RuntimeError("proof owner gate signing failed: " + s.stdout + s.stderr)
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
    temp = tempfile.mkdtemp(prefix="observatory-proof-")
    dest = os.path.join(temp, "repo")
    mock = None
    result = {"proof": "national-observatory-zero-cost-e2e-v1", "paid_api_calls": 0}
    try:
        source_head = clone_disposable(dest)
        result["source_head"] = source_head

        setup = py(os.path.join(dest, "setup_observatory.py"), "--run-id", RUN_ID,
                   "--budget-eur", "25", "--tokens", "10000000", "--calls", "3000", "--days", "3",
                   "--qualification", "3", "--replication", "2", "--holdout", "2", cwd=dest)
        result["setup"] = {"rc": setup.returncode, "tail": (setup.stdout + setup.stderr)[-2500:]}
        if setup.returncode != 0:
            raise RuntimeError("setup_observatory failed\n" + result["setup"]["tail"])

        owner_key = os.path.join(dest, "private-evaluator", "owner-held-secrets", "OWNER.key")
        runtime = os.path.join(dest, "proof", "runtime-observatory")
        pre = py(os.path.join(dest, "run_observatory.py"), "--preflight", "--run-id", RUN_ID,
                 "--runtime", runtime, "--canonical-repo", target,
                 "--cp1-evidence", cp1, "--prior-cp2", prior, cwd=dest)
        result["preflight"] = {"rc": pre.returncode, "tail": (pre.stdout + pre.stderr)[-2500:]}
        if pre.returncode != 0:
            raise RuntimeError("Observatory preflight failed\n" + result["preflight"]["tail"])

        mock_script = os.path.join(dest, "executable-orchestrator", "tools", "mock_observatory_server.py")
        mock = subprocess.Popen([sys.executable, mock_script, "--port", str(PORT)],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if not wait_port(PORT):
            out, err = mock.communicate(timeout=2)
            raise RuntimeError("Observatory mock server did not start\n" + out + err)
        endpoint = f"http://127.0.0.1:{PORT}/chat/completions"

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
        result["status"] = "PASS"
    except Exception as exc:  # one terminal failure, never trailing PASS
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
