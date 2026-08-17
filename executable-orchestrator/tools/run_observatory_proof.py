#!/usr/bin/env python3
"""Zero-cost end-to-end proof for the National Observatory supremacy protocol.

Runs a disposable Git clone against a localhost DeepSeek-shape provider. PASS requires the SAME
shared signed state machine to traverse: signed mission, search forest, structural genomes,
formalizations, blueprint-fidelity gates, semantic hidden replay, recombination/radical/simplifier
search, durable systems fault injection, lower-bound closure, final destroyers, public falsifiable
supremacy case, owner gates and final independent audit. No real provider call exists.
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
SUPREMACY_KEYS = [
    "search_forest_executed", "genome_saturated", "recombination_tested",
    "systems_arena_passed", "lower_bound_closed", "destroyer_survived",
    "public_supremacy_case",
]


def git_argv(*args):
    cmd = ["git"]
    if os.name == "nt":
        cmd += ["-c", "core.longpaths=true"]
    return cmd + list(args)


def sh(argv, env=None, cwd=None, timeout=None):
    e = dict(os.environ)
    e.update(env or {})
    return subprocess.run(argv, capture_output=True, text=True, env=e, cwd=cwd, timeout=timeout)


def py(script, *args, env=None, cwd=None, timeout=None):
    return sh([sys.executable, script, *args], env=env, cwd=cwd, timeout=timeout)


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
    watched = [
        "profiles/national-observatory", "run_observatory.py", "setup_observatory.py",
        "executable-orchestrator/lawmax21", "private-evaluator/evaluator",
        "benchmark/observatory_reference_candidate.py",
        "benchmark/observatory_systems_reference_candidate.py",
        "executable-orchestrator/tools/run_observatory_proof.py",
        "executable-orchestrator/tools/mock_observatory_server.py",
    ]
    r = sh(git_argv("-C", ROOT, "status", "--porcelain", "--untracked-files=all", "--", *watched))
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
    for attempt in range(40):
        r = py(runner, *args, env=env, cwd=dest, timeout=1800)
        transcript.append({"attempt": attempt, "rc": r.returncode,
                           "stdout_tail": (r.stdout or "")[-2500:],
                           "stderr_tail": (r.stderr or "")[-2500:]})
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


def verify_supremacy_artifacts(runtime, summary, run):
    forest = read_json(os.path.join(runtime, "architecture", "search_forest.json"))
    fsum = forest.get("summary") or {}
    if fsum.get("lineages") != 15 or fsum.get("general_lineages") != 6 \
            or fsum.get("anti_attractor_lineages") != 9:
        raise RuntimeError(f"supremacy search forest shape is wrong: {fsum}")
    if int(fsum.get("seeds", 0)) < 90 or int(fsum.get("selected_finalists", 0)) < 12:
        raise RuntimeError("supremacy search forest did not create/select enough structural alternatives")
    if fsum.get("prior_cp2_visible") is not False:
        raise RuntimeError("prior CP2 leaked into independent supremacy search forest")

    proposals = read_json(os.path.join(runtime, "architecture", "proposals.json"))
    if proposals.get("search_mode") != "SUPREMACY_SEARCH_FOREST_V1":
        raise RuntimeError("production path did not use supremacy search forest")
    if proposals.get("prior_cp2_visible") is not False:
        raise RuntimeError("prior CP2 was visible during supremacy proposal expansion")
    props = proposals.get("proposals") or []
    if len(props) < 12:
        raise RuntimeError("fewer than 12 structurally diverse complete finalists reached v0")
    for p in props:
        if not isinstance(p.get("genome"), dict) or not p.get("formalization") or not p.get("prebuild_destroyer"):
            raise RuntimeError(f"proposal {p.get('seed_id')} lost genome/formalization/destroyer evidence")
        if len((p.get("formalization") or {}).get("invariant_set", [])) < 8:
            raise RuntimeError(f"proposal {p.get('seed_id')} has weak/incomplete invariant formalization")

    gate = read_json(os.path.join(runtime, "gates", "v0_subject.json"))
    if gate.get("builder_handoff") != "COMPLETE_BLUEPRINT_PLUS_FORMALIZATION_REQUIRED":
        raise RuntimeError("owner v0 gate does not bind complete blueprint + formalization handoff")
    if int(gate.get("structural_finalists", 0)) < 12:
        raise RuntimeError("owner v0 gate binds too few structural finalists")
    if not gate.get("supremacy_contract_sha256") or not gate.get("search_forest_sha256"):
        raise RuntimeError("owner v0 gate does not bind supremacy/search-forest hashes")

    built = read_json(os.path.join(runtime, "candidates", "built.json"))
    if built.get("complete_blueprint_handoff") is not True or built.get("formalization_handoff") is not True:
        raise RuntimeError("candidate builds were not certified from complete blueprint + formalization")
    if len(built.get("built") or []) < 2:
        raise RuntimeError("fewer than two candidates survived blueprint-fidelity audit")
    for b in built["built"]:
        if not b.get("blueprint_sha256") or not b.get("formalization_sha256") \
                or b.get("blueprint_fidelity_consensus") is not True:
            raise RuntimeError(f"candidate {b.get('candidate_id')} lost architecture-fidelity binding")

    escalation = summary.get("escalation") or {}
    sup = escalation.get("supremacy") or {}
    missing = [k for k in SUPREMACY_KEYS if sup.get(k) is not True]
    if missing:
        raise RuntimeError("terminal proof lacks supremacy conditions: " + ", ".join(missing))
    if int(sup.get("genome_dry_waves", 0)) < 3 or int(sup.get("known_genomes", 0)) < 12:
        raise RuntimeError("structural-genome saturation was not established")
    if sup.get("third_party_endorsement_claimed") is not False:
        raise RuntimeError("terminal proof contains unsupported third-party endorsement")

    systems = read_json(os.path.join(runtime, "reports", f"systems-arena-{escalation['incumbent']}.json"))
    if systems.get("status") != "PASS" or systems.get("passed") is not True:
        raise RuntimeError("durable systems arena did not pass")
    tests = systems.get("tests") or {}
    required_tests = ["initial_durable_state", "restart_identity", "duplicate_idempotence",
                      "concurrent_access_integrity", "crash_restart_integrity",
                      "deterministic_large_rebuild", "large_history_integrity",
                      "publication_root_consistency"]
    if any(tests.get(k) is not True for k in required_tests):
        raise RuntimeError("durable systems arena lacks a required passing fault test")
    corruption = tests.get("corruption_detection_recovery") or {}
    if corruption.get("passed") is not True:
        raise RuntimeError("durable corruption/recovery fault injection did not pass")

    lower = read_json(os.path.join(runtime, "architecture", "lower_bounds.json"))
    if lower.get("closed") is not True or len(lower.get("reports") or []) != 3:
        raise RuntimeError("independent lower-bound campaign did not close")

    destroyers = read_json(os.path.join(runtime, "architecture", "final_destroyers.json"))
    if destroyers.get("survived") is not True or len(destroyers.get("reports") or []) != 3:
        raise RuntimeError("final independent destroyer campaign did not close")

    case = read_json(os.path.join(runtime, "architecture", "SUPREMACY-CASE.json"))
    if case.get("mechanically_supported") is not True \
            or case.get("claim_level") != "EVIDENCE_SUPPORTED_SUPREMACY" \
            or case.get("third_party_endorsement_claimed") is not False:
        raise RuntimeError("public supremacy case is unsupported or contains endorsement fiction")
    if len(case.get("falsifiers") or []) < 3:
        raise RuntimeError("public supremacy case is not sufficiently falsifiable")

    required_gates = {"GATE-ARCH-V0", "GATE-ARCH-V1", "GATE-MIGRATION", "GATE-COMMIT"}
    if not required_gates.issubset(set(run.get("gates") or [])):
        raise RuntimeError(f"proof did not traverse all owner gates: {run.get('gates')}")

    return {"search_forest": fsum,
            "structural_finalists": len(props),
            "built_candidates": len(built["built"]),
            "supremacy": sup,
            "systems_arena": systems,
            "lower_bounds_closed": True,
            "final_destroyers_survived": True,
            "supremacy_case_supported": True}


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
    result = {"proof": "national-observatory-supremacy-zero-cost-e2e-v3", "paid_api_calls": 0,
              "workspace": temp, "runtime": runtime,
              "path_budget": {"workspace_chars": len(temp), "runtime_chars": len(runtime),
                              "windows_longpaths_git": os.name == "nt"}}
    try:
        source_head = clone_disposable(dest)
        result["source_head"] = source_head

        setup = py(os.path.join(dest, "setup_observatory.py"), "--run-id", RUN_ID,
                   "--budget-usd", "25", "--tokens", "10000000", "--calls", "3000", "--days", "3",
                   "--qualification", "3", "--replication", "2", "--holdout", "2", cwd=dest)
        result["setup"] = {"rc": setup.returncode, "tail": ((setup.stdout or "") + (setup.stderr or ""))[-3500:]}
        if setup.returncode != 0:
            raise RuntimeError("setup_observatory failed\n" + result["setup"]["tail"])

        # Directly calibrate the new durable-systems evaluator before the full state machine can
        # depend on it. This is local Docker execution and makes zero provider calls.
        sys_ref = os.path.join(dest, "benchmark", "observatory_systems_reference_candidate.py")
        sys_out = os.path.join(dest, "proof", "systems-reference-calibration.json")
        systems_cal = py(os.path.join(dest, "private-evaluator", "evaluator", "observatory_systems_arena.py"),
                         "--candidate", sys_ref, "--out", sys_out, "--large-events", "5000",
                         cwd=dest, timeout=900)
        result["systems_reference_calibration"] = {
            "rc": systems_cal.returncode,
            "tail": ((systems_cal.stdout or "") + (systems_cal.stderr or ""))[-3500:]}
        if systems_cal.returncode != 0 or not os.path.exists(sys_out) \
                or read_json(sys_out).get("status") != "PASS":
            raise RuntimeError("durable systems reference calibration failed\n"
                               + result["systems_reference_calibration"]["tail"])

        owner_key = os.path.join(dest, "private-evaluator", "owner-held-secrets", "OWNER.key")
        endpoint = f"http://127.0.0.1:{PORT}/chat/completions"
        pre = py(os.path.join(dest, "run_observatory.py"), "--preflight", "--run-id", RUN_ID,
                 "--endpoint", endpoint, "--model", MODEL, "--backend", "subprocess",
                 "--runtime", runtime, "--canonical-repo", target,
                 "--cp1-evidence", cp1, "--prior-cp2", prior, cwd=dest)
        result["preflight"] = {"rc": pre.returncode, "tail": ((pre.stdout or "") + (pre.stderr or ""))[-4500:]}
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
            raise RuntimeError("shared supremacy state-machine rehearsal did not complete")
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
            raise RuntimeError("prior CP2 was visible during independent supremacy search")
        result["cp1_reused_without_api"] = True
        result["prior_cp2_quarantined_during_new_discovery"] = True

        result["supremacy_protocol"] = verify_supremacy_artifacts(runtime, summary, run)

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
