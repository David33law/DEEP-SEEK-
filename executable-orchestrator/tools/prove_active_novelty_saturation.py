#!/usr/bin/env python3
"""Authoritative zero-cost proof for active novelty and meta-search saturation.

The wrapper imports the complete Observatory supremacy proof, substitutes only the contract-rich local
mock extension in the disposable clone, and then verifies that the production handler path ran:

* all six CP2-direct-blind fixed novelty miners;
* two independent meta-search critics per wave;
* mechanical coverage of every non-``other`` class and required critical-pair breadth;
* all generated dynamic coverage/search directives;
* two independent closure auditors per wave;
* an empty backlog, no taxonomy/protocol blockers and three genuinely dry consecutive waves.

No real provider endpoint or credential is used.
"""
import argparse
import glob
import hashlib
import importlib.util
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
BASE_PROOF = os.path.join(HERE, "run_observatory_proof.py")
BASE_REPORT = os.path.join(ROOT, "proof", "national-observatory-zero-cost-e2e.json")
OUT = os.path.join(ROOT, "proof", "active-novelty-zero-cost-proof.json")
EXPECTED_FIXED_METHODS = ["G91", "G92", "G93", "G94", "G95", "G96"]
EXPECTED_META = ["A", "B"]
EXPECTED_CLOSURE = ["A", "B"]


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


def _load_base_proof():
    spec = importlib.util.spec_from_file_location("observatory_base_proof", BASE_PROOF)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run_base_proof(args):
    module = _load_base_proof()
    original_popen = module.subprocess.Popen

    def patched_popen(argv, *pargs, **kwargs):
        command = list(argv) if isinstance(argv, (list, tuple)) else argv
        if isinstance(command, list) and len(command) >= 2 \
                and os.path.basename(str(command[1])) == "mock_observatory_server.py":
            replacement = os.path.join(
                os.path.dirname(os.path.abspath(str(command[1]))),
                "mock_observatory_meta_server.py")
            if not os.path.isfile(replacement):
                raise RuntimeError("meta-search mock extension missing in disposable clone")
            command[1] = replacement
        return original_popen(command, *pargs, **kwargs)

    module.subprocess.Popen = patched_popen
    try:
        return module.main([
            "--canonical-repo", os.path.abspath(args.canonical_repo),
            "--cp1-evidence", os.path.abspath(args.cp1_evidence),
            "--prior-cp2", os.path.abspath(args.prior_cp2),
            "--keep",
        ])
    finally:
        module.subprocess.Popen = original_popen


def _meta_artifact(runtime, round_no):
    path = os.path.join(runtime, "architecture", f"meta-search-wave-r{round_no}.json")
    if not os.path.isfile(path):
        raise RuntimeError(f"meta-search artifact missing for round {round_no}")
    return path, read_json(path)


def verify(runtime):
    summary = read_json(os.path.join(runtime, "reports", "run_summary.json"))
    supremacy = (summary.get("escalation") or {}).get("supremacy") or {}
    required_true = [
        "genome_saturated",
        "novelty_methods_complete",
        "novelty_prior_cp2_direct_blind",
        "meta_search_critics_complete",
        "closure_auditors_complete",
        "closure_auditors_support_final_dry",
        "mechanical_coverage_complete",
    ]
    missing = [key for key in required_true if supremacy.get(key) is not True]
    if missing:
        raise RuntimeError("terminal supremacy summary lacks: " + ", ".join(missing))
    if int(supremacy.get("genome_dry_waves", 0)) < 3:
        raise RuntimeError("terminal summary lacks three complete active dry waves")
    if int(supremacy.get("novelty_waves", 0)) < 3:
        raise RuntimeError("terminal summary lacks novelty-wave evidence")
    if int(supremacy.get("novelty_open_backlog", -1)) != 0:
        raise RuntimeError("terminal summary retains a novelty backlog")
    if int(supremacy.get("novelty_unresolved", -1)) != 0:
        raise RuntimeError("terminal summary retains unresolved novelty/meta work")
    if int(supremacy.get("protocol_improvements_open", -1)) != 0:
        raise RuntimeError("terminal summary retains an attainable protocol improvement")
    if int(supremacy.get("taxonomy_unresolved_count", -1)) != 0:
        raise RuntimeError("terminal summary retains an unresolved taxonomy extension")

    paths = sorted(glob.glob(os.path.join(runtime, "architecture", "novelty-wave-r*.json")))
    if len(paths) < 3:
        raise RuntimeError(f"expected at least three novelty-wave artifacts, found {len(paths)}")
    contract = os.path.join(ROOT, "profiles", "national-observatory",
                            "NOVELTY-SEARCH-CONTRACT.md")
    contract_hash = sha256_file(contract)
    waves = []
    for path in paths:
        obj = read_json(path)
        fixed = obj.get("methods_completed") or []
        if fixed != EXPECTED_FIXED_METHODS:
            raise RuntimeError(f"{os.path.basename(path)} has wrong fixed novelty portfolio: {fixed}")
        if obj.get("prior_cp2_direct_content_read") is not False:
            raise RuntimeError(f"{os.path.basename(path)} read direct CP2 content")
        if obj.get("contract_sha256") != contract_hash:
            raise RuntimeError(f"{os.path.basename(path)} is not bound to the current contract")
        miner_codes = [x.get("code") for x in obj.get("miners", [])]
        if miner_codes != EXPECTED_FIXED_METHODS:
            raise RuntimeError(f"{os.path.basename(path)} did not execute all fixed miners")

        round_no = int(obj.get("round"))
        meta_path, meta = _meta_artifact(runtime, round_no)
        if meta.get("contract_sha256") != contract_hash:
            raise RuntimeError(f"{os.path.basename(meta_path)} is not bound to current contract")
        if meta.get("prior_cp2_direct_content_read") is not False:
            raise RuntimeError(f"{os.path.basename(meta_path)} read direct CP2 content")
        critics = [x.get("tag") for x in meta.get("meta_critics", [])]
        auditors = [x.get("tag") for x in meta.get("closure_auditors", [])]
        if critics != EXPECTED_META:
            raise RuntimeError(f"{os.path.basename(meta_path)} lacks two independent meta critics")
        if auditors != EXPECTED_CLOSURE:
            raise RuntimeError(f"{os.path.basename(meta_path)} lacks two independent closure auditors")
        if (meta.get("coverage_after") or {}).get("complete") is not True:
            raise RuntimeError(f"{os.path.basename(meta_path)} did not close mechanical coverage")
        if meta.get("protocol_blockers"):
            raise RuntimeError(f"{os.path.basename(meta_path)} retains protocol blockers")
        if meta.get("taxonomy_unresolved"):
            raise RuntimeError(f"{os.path.basename(meta_path)} retains taxonomy blockers")
        for miner in meta.get("dynamic_miners", []):
            if miner.get("unmet_obligations"):
                raise RuntimeError(f"{os.path.basename(meta_path)} has an unmet dynamic obligation")

        ledger = meta.get("ledger_wave") or {}
        if ledger.get("methods_complete") is not True:
            raise RuntimeError(f"{os.path.basename(meta_path)} marks the complete portfolio incomplete")
        if ledger.get("meta_critics_complete") is not True \
                or ledger.get("closure_auditors_complete") is not True:
            raise RuntimeError(f"{os.path.basename(meta_path)} lacks meta/closure completion")
        waves.append({
            "round": round_no,
            "novelty_path": os.path.relpath(path, runtime).replace("\\", "/"),
            "meta_path": os.path.relpath(meta_path, runtime).replace("\\", "/"),
            "dry": ledger.get("dry") is True,
            "new_count": int(ledger.get("new_count", 0)),
            "admitted": len(ledger.get("admitted_genomes") or []),
            "backlog": int(ledger.get("backlog_count", 0)),
            "unresolved": int(ledger.get("unresolved_count", 0)),
            "dynamic_miners": len(meta.get("dynamic_miners", [])),
        })

    for wave in waves[-3:]:
        if not wave["dry"] or wave["new_count"] != 0 or wave["admitted"] != 0 \
                or wave["backlog"] != 0 or wave["unresolved"] != 0:
            raise RuntimeError("the final three novelty/meta waves are not genuinely dry")

    audit = read_json(os.path.join(runtime, "audit", "independent_audit.json"))
    active = audit.get("active_novelty_saturation") or {}
    audit_required = [
        "methods_complete", "meta_search_critics_complete", "closure_auditors_complete",
        "closure_auditors_support_final_dry", "mechanical_coverage_complete",
        "prior_cp2_direct_blind", "genome_saturated",
    ]
    audit_missing = [key for key in audit_required if active.get(key) is not True]
    if audit_missing:
        raise RuntimeError("independent audit lacks: " + ", ".join(audit_missing))
    if int(active.get("open_backlog", -1)) != 0 \
            or int(active.get("unresolved", -1)) != 0 \
            or int(active.get("protocol_improvements_open", -1)) != 0 \
            or int(active.get("taxonomy_unresolved_count", -1)) != 0:
        raise RuntimeError("independent audit retains novelty/meta closure blockers")

    return {
        "supremacy_summary": supremacy,
        "wave_count": len(waves),
        "waves": waves,
        "final_three_dry": True,
        "fixed_methods": EXPECTED_FIXED_METHODS,
        "meta_critics": EXPECTED_META,
        "closure_auditors": EXPECTED_CLOSURE,
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

    result = {"proof": "active-novelty-meta-saturation-zero-cost-v2", "paid_api_calls": 0}
    workspace = None
    try:
        rc = _run_base_proof(a)
        result["base_proof_returncode"] = rc
        if not os.path.exists(BASE_REPORT):
            raise RuntimeError("base supremacy proof report was not produced")
        base = read_json(BASE_REPORT)
        result["base_status"] = base.get("status")
        result["source_head"] = base.get("source_head")
        result["runtime"] = base.get("runtime")
        result["workspace"] = base.get("workspace")
        workspace = base.get("workspace")
        if rc != 0 or base.get("status") != "PASS":
            raise RuntimeError("base supremacy proof failed: "
                               + str(base.get("reason") or "unknown"))
        if int(base.get("paid_api_calls", -1)) != 0:
            raise RuntimeError("base proof reports nonzero paid API calls")
        result["active_novelty_meta"] = verify(os.path.abspath(base["runtime"]))
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
