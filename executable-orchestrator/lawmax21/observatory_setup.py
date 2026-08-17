"""Owner ceremony and zero-provider-call calibration for the Observatory protocol."""
from __future__ import annotations

import argparse
import json
import os
import secrets
import shutil
import subprocess
import sys

from . import observatory_protocol
from .canonical import atomic_write_json, read_json

ORCH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(ORCH)
TOOLS = os.path.join(ORCH, "tools")
EVALUATOR = os.path.join(ROOT, "private-evaluator", "evaluator")
SECRETS = os.path.join(ROOT, "private-evaluator", "owner-held-secrets")
PROFILE = os.path.join(ROOT, "profiles", "national-observatory")
PROOF = os.path.join(ROOT, "proof")

PRICE_SCHEDULE = {
    "model": "deepseek-v4-pro", "currency": "USD",
    "input_cache_hit_per_mtok": 0.003625,
    "input_cache_miss_per_mtok": 0.435,
    "output_per_mtok": 0.87, "require_cache_split": True,
    "source": "https://api-docs.deepseek.com/quick_start/pricing",
    "verified_date": "2026-08-17"}


def _run(argv, timeout=14400):
    result = subprocess.run([sys.executable, *argv], capture_output=True,
                            text=True, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError("FAILED: " + " ".join(argv) + "\n"
                           + result.stdout[-4000:] + "\n" + result.stderr[-4000:])
    return result


def _git(*args):
    result = subprocess.run(["git", "-C", ROOT, *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError("git failed: " + result.stderr.strip())
    return result.stdout.strip()


def _compile_protocol():
    compiled = 0
    parsed_json = 0
    for relative in observatory_protocol.protocol_files(ROOT):
        path = os.path.join(ROOT, *relative.split("/"))
        if relative.endswith(".py"):
            compile(open(path, encoding="utf-8").read(), relative, "exec")
            compiled += 1
        elif relative.endswith(".json"):
            read_json(path); parsed_json += 1
    return {"python_files_compiled": compiled, "json_files_parsed": parsed_json,
            "protocol_files": len(observatory_protocol.protocol_files(ROOT)),
            "bundle_sha256": observatory_protocol.protocol_bundle_sha256(ROOT)}


def _mission():
    return observatory_protocol.mission_binding(ROOT, _git)


def _decisions(budget_usd, tokens, calls, days):
    return {
        "D01_BUDGET": {"decided": True, "value": {
            "currency": "USD", "amount": float(budget_usd),
            "price_schedule": dict(PRICE_SCHEDULE), "tokens": int(tokens),
            "calls": int(calls), "wall_clock_days": int(days),
            "successor_reserve_fraction": 0.35}},
        "D02_HIDDEN_SET_AUTHORITY": {"decided": True,
            "value": "encrypted hidden replay bank; grader hashes frozen at creation"},
        "D03_RUNTIME_DIRECTION": {"decided": True,
            "value": "architecture and production substrate remain measured outputs"},
        "D04_PACKAGE_AUTHOR_REPO_ACCESS": {"decided": True,
            "value": "isolated exact target + sealed CP1 reuse; no target remote"},
        "D05_PII_FIXTURE_POLICY": {"decided": True,
            "value": "synthetic legal-history fixtures; no client PII"},
        "D06_GATE_CADENCE": {"decided": True,
            "value": "owner reviews architecture, migration, integration and crown gates"},
        "D07_ACCEPTANCE_THRESHOLDS": {"decided": True, "value": {
            "hidden_pass_rate": 0.98, "min_slice_f1": 0.98, "clean_runs": 2,
            "ablation_min_drop": 0.20, "progress_min_delta": 0.002,
            "max_stagnant_windows": 4, "best_of_n": 4, "revision_rounds": 2,
            **observatory_protocol.SEARCH_POLICY}},
        "D08_OFFMACHINE_BACKUP": {"decided": True,
            "value": "encrypted off-machine signed-log/checkpoint/final-evidence copy"},
        "D09_ROW0_TARGET": {"decided": True, "value": _mission()},
        "D10_CS01_FIXTURE_LICENCE": {"decided": True,
            "value": "synthetic Observatory replay fixtures only"},
        "D11_CHALLENGER_RESERVE": {"decided": True, "value": {
            "fraction": 0.35,
            "critic_contexts": "independent proposer/builder/reviser/destroyer/prior-art/novelty/meta/audit contexts"}}}


def _hard_failures(scores, specification):
    failures = []
    for dimension in specification:
        key = dimension["id"]
        if key not in scores or dimension.get("hard_minimum") is None:
            continue
        value = float(scores[key]); minimum = float(dimension["hard_minimum"])
        if dimension["direction"] == "higher" and value < minimum:
            failures.append((key, value, minimum))
        if dimension["direction"] == "lower" and value > minimum:
            failures.append((key, value, minimum))
    return failures


def _assert_report(path, label):
    report = read_json(path)
    if report.get("status") not in ("PASS", "OK") or report.get("passed") is False:
        raise RuntimeError(label + " calibration failed: " + json.dumps(
            report, ensure_ascii=False)[:3000])
    return report


def _calibrate_specialized_references():
    os.makedirs(PROOF, exist_ok=True)
    outputs = {}
    distributed_out = os.path.join(PROOF, "distributed-reference-calibration.json")
    _run([os.path.join(EVALUATOR, "observatory_distributed_arena.py"),
          "--candidate", os.path.join(ROOT, "benchmark",
                                      "observatory_distributed_reference_candidate.py"),
          "--out", distributed_out,
          "--expected-replication-model", "single_primary_read_replicas",
          "--expected-commit-model", "single_writer_sequence",
          "--large-events", str(observatory_protocol.workload(
              "distributed", "qualification"))])
    outputs["distributed"] = _assert_report(distributed_out, "distributed")

    scale_out = os.path.join(PROOF, "scale-reference-calibration.json")
    scale_events = observatory_protocol.workload("scale", "qualification")
    _run([os.path.join(EVALUATOR, "observatory_scale_arena.py"),
          "--candidate", os.path.join(ROOT, "benchmark",
                                      "observatory_scale_reference_candidate.py"),
          "--out", scale_out, "--expected-scaling-model", "source_sharding",
          "--events", str(scale_events), "--tail-events", str(max(1000, scale_events // 10)),
          "--partitions", str(observatory_protocol.workload("scale", "partitions")),
          "--batch-size", str(observatory_protocol.workload("scale", "batch"))])
    outputs["scale"] = _assert_report(scale_out, "scale")

    formal_out = os.path.join(PROOF, "formal-reference-calibration.json")
    _run([os.path.join(EVALUATOR, "observatory_formal_arena.py"),
          "--candidate", os.path.join(ROOT, "benchmark",
                                      "observatory_formal_reference_candidate.py"),
          "--out", formal_out,
          "--expected-canonical-authority-seat", "evidence_set",
          "--expected-state-derivation-model", "replay_reducer",
          "--expected-temporal-model", "bitemporal_intervals",
          "--expected-normative-effect-model", "typed_directive_interpreter",
          "--expected-consistency-commit-model", "single_writer_sequence",
          "--expected-replication-distribution-model", "single_primary_read_replicas",
          "--expected-trusted-core-topology", "state_machine_kernel",
          "--depth", str(observatory_protocol.workload("formal", "qualification_depth"))])
    outputs["formal"] = _assert_report(formal_out, "formal")

    interop_out = os.path.join(PROOF, "interoperability-reference-calibration.json")
    _run([os.path.join(EVALUATOR, "observatory_interoperability_arena.py"),
          "--candidate", os.path.join(ROOT, "benchmark",
                                      "observatory_interoperability_reference_candidate.py"),
          "--out", interop_out,
          "--expected-identity-model", "composite_identity",
          "--expected-temporal-model", "bitemporal_intervals",
          "--expected-normative-effect-model", "typed_directive_interpreter",
          "--expected-provenance-proof-model", "provenance_graph",
          "--expected-publication-topology", "compiled_read_only_projections",
          "--cases", str(observatory_protocol.workload(
              "interoperability", "qualification_cases"))])
    outputs["interoperability"] = _assert_report(interop_out, "interoperability")
    return {name: {"status": report.get("status"),
                   "evidence": os.path.relpath(report.get("candidate", ""), ROOT)
                   if report.get("candidate") else None}
            for name, report in outputs.items()}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default="OBS-RUN-0001")
    parser.add_argument("--budget-usd", type=float, default=500.0)
    parser.add_argument("--tokens", type=int, default=250_000_000)
    parser.add_argument("--calls", type=int, default=20_000)
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--qualification", type=int, default=12)
    parser.add_argument("--replication", type=int, default=8)
    parser.add_argument("--holdout", type=int, default=6)
    args = parser.parse_args(argv)

    sys.path.insert(0, EVALUATOR)
    import observatory_harness
    protocol_report = _compile_protocol()
    os.makedirs(SECRETS, exist_ok=True)
    owner_key = os.path.join(SECRETS, "OWNER.key")
    owner_pub = os.path.join(ROOT, "immutable-package", "OWNER-PUBLIC-KEY.hex")
    if not os.path.exists(owner_key):
        _run([os.path.join(TOOLS, "owner_sign.py"), "--init", "--key", owner_key,
              "--public-out", owner_pub])
        print("· generated owner keypair")
    else:
        print("· owner key already present — reusing")
    _run([os.path.join(TOOLS, "generate_protocol19.py")])
    _run([os.path.join(TOOLS, "make_manifest.py")])
    protocol_report = _compile_protocol()

    unsigned = os.path.join(ROOT, "observatory-decisions.unsigned.json")
    atomic_write_json(unsigned, _decisions(args.budget_usd, args.tokens,
                                           args.calls, args.days))
    _run([os.path.join(TOOLS, "owner_sign.py"), "--key", owner_key,
          "--run-id", args.run_id, "--decisions", unsigned,
          "--out", os.path.join(ROOT, "OWNER-DECISIONS.signed.json")])
    os.remove(unsigned)
    print("· signed exact protocol HEAD/tree/files/contracts/workloads into D09")

    visible = os.path.join(ROOT, "benchmark", "observatory-visible-suite.json")
    observatory_harness.build_visible_suite(visible)
    bank = os.path.join(ROOT, "private-evaluator", "observatory-hidden-bank")
    if os.path.isdir(bank):
        shutil.rmtree(bank)
    hidden_key = os.path.join(SECRETS, "OBSERVATORY-HIDDEN.key")
    if os.path.exists(hidden_key):
        os.remove(hidden_key)
    _run([os.path.join(EVALUATOR, "observatory_bank_builder.py"),
          "--bank", bank, "--key", hidden_key,
          "--seed", str(secrets.randbelow(2**31 - 2) + 1),
          "--qualification", str(args.qualification),
          "--replication", str(args.replication), "--holdout", str(args.holdout)])

    reference = os.path.join(ROOT, "benchmark", "observatory_reference_candidate.py")
    source = open(reference, encoding="utf-8").read()
    suite = read_json(visible)
    specification = read_json(os.path.join(PROFILE, "PARETO-DIMENSIONS.json"))
    visible_report = observatory_harness.run_suite(source, suite, "subprocess")
    if _hard_failures(visible_report["dimension_scores"], specification):
        raise RuntimeError("visible semantic evaluator calibration failed")
    if not observatory_harness.fidelity(source, suite, "subprocess").get("mechanism_exercised"):
        raise RuntimeError("visible causal-fidelity calibration failed")
    hidden_out = os.path.join(PROOF, "observatory-hidden-calibration.json")
    os.makedirs(PROOF, exist_ok=True)
    _run([os.path.join(EVALUATOR, "observatory_evaluate.py"), "--bank", bank,
          "--key", hidden_key, "--candidate", reference, "--level", "qualification",
          "--backend", "subprocess", "--out", hidden_out])
    hidden = read_json(hidden_out)
    if hidden.get("status") != "OK" or _hard_failures(
            hidden.get("dimension_scores", {}), specification):
        raise RuntimeError("hidden semantic evaluator calibration failed")
    if not all(row.get("verdict") == "DENIED" for row in hidden.get("canaries", [])):
        raise RuntimeError("hidden isolation canaries were not all denied")
    specialized = _calibrate_specialized_references()

    print("\nOBSERVATORY SETUP: PASS")
    print("run-id:", args.run_id)
    print("runner-head:", _git("rev-parse", "HEAD"))
    print("protocol-version:", observatory_protocol.PROTOCOL_VERSION)
    print("protocol-files:", protocol_report["protocol_files"])
    print("protocol-bundle-sha256:", protocol_report["bundle_sha256"])
    print("workload-mode:", "PROOF" if observatory_protocol.proof_mode() else "PRODUCTION")
    print("specialized-calibrations:", json.dumps(specialized, sort_keys=True))
    print("No DeepSeek/API call was made.")
    return 0
