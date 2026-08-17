#!/usr/bin/env python3
"""Authoritative zero-cost proof for active design-space saturation.

This wrapper executes the complete Observatory supremacy proof in a retained disposable workspace,
then verifies that the production handler path ran every CP2-direct-blind novelty method, persisted
its controlled-genome evidence, drained all deferred/unresolved work and achieved three genuinely
dry consecutive waves. It never contacts the real provider.
"""
import argparse
import glob
import hashlib
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
BASE_PROOF = os.path.join(HERE, "run_observatory_proof.py")
BASE_REPORT = os.path.join(ROOT, "proof", "national-observatory-zero-cost-e2e.json")
OUT = os.path.join(ROOT, "proof", "active-novelty-zero-cost-proof.json")
EXPECTED_METHODS = ["G91", "G92", "G93", "G94", "G95", "G96"]


def read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path, obj):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1, sort_keys=True)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verify(runtime):
    summary = read_json(os.path.join(runtime, "reports", "run_summary.json"))
    supremacy = (summary.get("escalation") or {}).get("supremacy") or {}
    if int(supremacy.get("genome_dry_waves", 0)) < 3:
        raise RuntimeError("terminal summary lacks three active novelty dry waves")
    if int(supremacy.get("novelty_waves", 0)) < 3:
        raise RuntimeError("terminal summary lacks active novelty-wave evidence")
    if supremacy.get("novelty_methods_complete") is not True:
        raise RuntimeError("terminal summary says the novelty method portfolio was incomplete")
    if supremacy.get("novelty_prior_cp2_direct_blind") is not True:
        raise RuntimeError("terminal summary does not certify direct CP2 blindness")
    if int(supremacy.get("novelty_open_backlog", -1)) != 0:
        raise RuntimeError("terminal summary retains a novelty backlog")
    if int(supremacy.get("novelty_unresolved", -1)) != 0:
        raise RuntimeError("terminal summary retains unresolved novelty genomes")
    if supremacy.get("genome_saturated") is not True:
        raise RuntimeError("terminal summary does not prove controlled-genome saturation")

    paths = sorted(glob.glob(os.path.join(runtime, "architecture", "novelty-wave-r*.json")))
    if len(paths) < 3:
        raise RuntimeError(f"expected at least three novelty-wave artifacts, found {len(paths)}")
    contract = os.path.join(ROOT, "profiles", "national-observatory",
                            "NOVELTY-SEARCH-CONTRACT.md")
    contract_hash = sha256_file(contract)
    waves = []
    for path in paths:
        obj = read_json(path)
        methods = obj.get("methods_completed") or []
        if methods != EXPECTED_METHODS:
            raise RuntimeError(f"{os.path.basename(path)} has wrong novelty portfolio: {methods}")
        if obj.get("prior_cp2_direct_content_read") is not False:
            raise RuntimeError(f"{os.path.basename(path)} read direct CP2 content")
        if obj.get("contract_sha256") != contract_hash:
            raise RuntimeError(f"{os.path.basename(path)} is not bound to the current novelty contract")
        miner_codes = [x.get("code") for x in obj.get("miners", [])]
        if miner_codes != EXPECTED_METHODS:
            raise RuntimeError(f"{os.path.basename(path)} did not execute all six miners")
        ledger = obj.get("ledger_wave") or {}
        if ledger.get("methods_complete") is not True:
            raise RuntimeError(f"{os.path.basename(path)} ledger marks methods incomplete")
        if ledger.get("prior_cp2_direct_content_read") is not False:
            raise RuntimeError(f"{os.path.basename(path)} ledger marks a CP2-direct leak")
        waves.append({
            "path": os.path.relpath(path, runtime).replace("\\", "/"),
            "dry": ledger.get("dry") is True,
            "new_count": int(ledger.get("new_count", 0)),
            "admitted": len(ledger.get("admitted_genomes") or []),
            "backlog": int(ledger.get("backlog_count", 0)),
            "unresolved": int(ledger.get("unresolved_count", 0)),
        })

    for wave in waves[-3:]:
        if not wave["dry"] or wave["new_count"] != 0 or wave["admitted"] != 0 \
                or wave["backlog"] != 0 or wave["unresolved"] != 0:
            raise RuntimeError("the final three novelty waves are not genuinely dry")

    audit = read_json(os.path.join(runtime, "audit", "independent_audit.json"))
    active = audit.get("active_novelty_saturation") or {}
    if active.get("methods_complete") is not True \
            or active.get("prior_cp2_direct_blind") is not True \
            or int(active.get("open_backlog", -1)) != 0 \
            or int(active.get("unresolved", -1)) != 0 \
            or active.get("genome_saturated") is not True:
        raise RuntimeError("independent audit did not certify active novelty saturation")

    return {
        "supremacy_summary": supremacy,
        "wave_count": len(waves),
        "waves": waves,
        "final_three_dry": True,
        "methods": EXPECTED_METHODS,
        "contract_sha256": contract_hash,
        "independent_audit_certified": True,
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--canonical-repo", required=True)
    ap.add_argument("--cp1-evidence", required=True)
    ap.add_argument("--prior-cp2", required=True)
    ap.add_argument("--keep", action="store_true")
    a = ap.parse_args(argv)

    result = {"proof": "active-novelty-saturation-zero-cost-v1", "paid_api_calls": 0}
    workspace = None
    try:
        cmd = [sys.executable, BASE_PROOF,
               "--canonical-repo", os.path.abspath(a.canonical_repo),
               "--cp1-evidence", os.path.abspath(a.cp1_evidence),
               "--prior-cp2", os.path.abspath(a.prior_cp2),
               "--keep"]
        run = subprocess.run(cmd, capture_output=True, text=True, timeout=7200)
        result["base_proof"] = {
            "returncode": run.returncode,
            "stdout_tail": (run.stdout or "")[-5000:],
            "stderr_tail": (run.stderr or "")[-5000:],
        }
        if not os.path.exists(BASE_REPORT):
            raise RuntimeError("base supremacy proof report was not produced")
        base = read_json(BASE_REPORT)
        result["base_status"] = base.get("status")
        result["source_head"] = base.get("source_head")
        result["runtime"] = base.get("runtime")
        result["workspace"] = base.get("workspace")
        workspace = base.get("workspace")
        if run.returncode != 0 or base.get("status") != "PASS":
            raise RuntimeError("base supremacy proof failed: " + str(base.get("reason") or "unknown"))
        if int(base.get("paid_api_calls", -1)) != 0:
            raise RuntimeError("base proof reports nonzero paid API calls")
        runtime = os.path.abspath(base["runtime"])
        result["active_novelty"] = verify(runtime)
        result["status"] = "PASS"
    except Exception as exc:
        result["status"] = "FAIL"
        result["reason"] = str(exc)
    finally:
        write_json(OUT, result)
        print(json.dumps(result, ensure_ascii=False, indent=1, sort_keys=True))
        print("proof report:", OUT)
        if result.get("status") == "PASS" and workspace and not a.keep:
            shutil.rmtree(workspace, ignore_errors=True)
        elif workspace:
            print("disposable proof directory retained:", workspace)
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
