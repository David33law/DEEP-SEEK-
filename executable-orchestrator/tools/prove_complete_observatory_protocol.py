#!/usr/bin/env python3
"""Authoritative zero-cost E2E proof for the owner-signed Observatory protocol v5.

The proof clones the exact committed runner, enables only the explicit reduced proof workload,
performs the owner ceremony and all local evaluator calibrations, drives the real shared state machine
through every owner gate against the complete localhost provider, verifies every semantic, durable,
distributed, scale, formal, interoperability, cross-model, prior-art, novelty and executable-genome
artifact, and then proves every terminal condition fail-closed. It never contacts the real DeepSeek
endpoint.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ORCH = os.path.dirname(HERE)
ROOT = os.path.dirname(ORCH)
RUN_ID = "OBS-PROTOCOL-PROOF-V5-0001"
MODEL = "deepseek-v4-pro"
PROTOCOL_VERSION = "OBSERVATORY-OMEGA-RESEARCH-PROTOCOL-5"
PROOF_ENV = "OBSERVATORY_ZERO_COST_PROOF"

EXPECTED_NEW_CONDITIONS = {
    "implementation_diversity_proven",
    "semantic_implementation_search_closed",
    "distributed_implementation_diversity_proven",
    "distributed_failure_model_proven",
    "distributed_replication_passed",
    "distributed_crown_passed",
    "scale_implementation_diversity_proven",
    "national_scale_qualification_passed",
    "national_scale_replication_passed",
    "national_scale_crown_passed",
    "machine_checked_models_passed",
    "independent_model_agreement",
    "formal_replication_passed",
    "formal_crown_passed",
    "legal_interoperability_passed",
    "interoperability_implementations_agree",
    "interoperability_replication_passed",
    "interoperability_crown_passed",
    "cross_model_consistency_passed",
    "cross_model_replication_passed",
    "cross_model_crown_passed",
    "genome_realization_proven",
    "genome_realization_replication_passed",
    "genome_realization_crown_passed",
    "prior_art_all_sources_assessed",
    "prior_art_challengers_measured",
    "prior_art_no_blockers",
}

REQUIRED_PROTOCOL_FILES = {
    "profiles/national-observatory/GENOME-REALIZATION-CONTRACT.md",
    "executable-orchestrator/lawmax21/observatory_protocol.py",
    "executable-orchestrator/lawmax21/observatory_audit.py",
    "executable-orchestrator/lawmax21/observatory_build_schema_hardening.py",
    "executable-orchestrator/lawmax21/observatory_semantic_evidence_binding_hardening.py",
    "executable-orchestrator/lawmax21/observatory_implementation_search_overlay.py",
    "executable-orchestrator/lawmax21/observatory_distributed_overlay.py",
    "executable-orchestrator/lawmax21/observatory_scale_overlay.py",
    "executable-orchestrator/lawmax21/observatory_formal_overlay.py",
    "executable-orchestrator/lawmax21/observatory_formal_streaming_routing.py",
    "executable-orchestrator/lawmax21/observatory_interoperability_overlay.py",
    "executable-orchestrator/lawmax21/observatory_cross_model_overlay.py",
    "executable-orchestrator/lawmax21/observatory_genome_realization_overlay.py",
    "executable-orchestrator/lawmax21/observatory_genome_auditor_diversity_hardening.py",
    "executable-orchestrator/lawmax21/observatory_genome_evidence_binding_hardening.py",
    "executable-orchestrator/lawmax21/observatory_prior_art_overlay.py",
    "executable-orchestrator/lawmax21/observatory_novelty_overlay.py",
    "private-evaluator/evaluator/bounded_subprocess.py",
    "private-evaluator/evaluator/observatory_systems_arena_v2.py",
    "private-evaluator/evaluator/observatory_distributed_arena_v2.py",
    "private-evaluator/evaluator/observatory_scale_arena_v2.py",
    "private-evaluator/evaluator/observatory_formal_arena_v3.py",
    "private-evaluator/evaluator/observatory_interoperability_arena_v2.py",
    "private-evaluator/evaluator/observatory_cross_model_arena_v2.py",
    "executable-orchestrator/tools/mock_observatory_protocol_server.py",
    "executable-orchestrator/tools/prove_terminal_condition_closure.py",
    "executable-orchestrator/tools/prove_observatory_protocol_static_v3.py",
    "executable-orchestrator/tools/prove_complete_observatory_protocol_v3.py",
}


def read_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path, value):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=1, sort_keys=True)


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_argv(*args):
    command = ["git"]
    if os.name == "nt":
        command += ["-c", "core.longpaths=true"]
    return command + list(args)


def run(command, *, cwd=None, env=None, timeout=28800):
    return subprocess.run(
        command, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)


def py(path, *args, cwd=None, env=None, timeout=28800):
    return run([sys.executable, path, *args], cwd=cwd, env=env, timeout=timeout)


def short_workspace():
    if os.name != "nt":
        return tempfile.mkdtemp(prefix="observatory-protocol-v5-")
    drive = os.environ.get("SystemDrive") or os.path.splitdrive(os.getcwd())[0] or "C:"
    parent = os.environ.get("OBSERVATORY_PROOF_TMP_ROOT") or os.path.join(
        drive + os.sep, "obs-pf")
    os.makedirs(parent, exist_ok=True)
    return tempfile.mkdtemp(prefix="v5-", dir=parent)


def clone_exact(destination):
    watched = [
        "profiles/national-observatory",
        "run_observatory.py",
        "setup_observatory.py",
        "executable-orchestrator/lawmax21",
        "private-evaluator/evaluator",
        "benchmark",
        "executable-orchestrator/tools",
    ]
    status = run(git_argv(
        "-C", ROOT, "status", "--porcelain", "--untracked-files=all", "--", *watched))
    if status.returncode != 0 or (status.stdout or "").strip():
        raise RuntimeError(
            "source checkout has uncommitted protocol drift:\n"
            + (status.stdout or status.stderr)[:5000])
    head_result = run(git_argv("-C", ROOT, "rev-parse", "HEAD"))
    if head_result.returncode != 0:
        raise RuntimeError(head_result.stderr or "git rev-parse failed")
    head = head_result.stdout.strip()
    clone = run(git_argv(
        "clone", "--no-hardlinks", "--quiet", ROOT, destination))
    if clone.returncode != 0:
        raise RuntimeError("disposable clone failed: " + clone.stderr)
    checkout = run(git_argv(
        "-C", destination, "checkout", "--quiet", "--detach", head))
    if checkout.returncode != 0:
        raise RuntimeError("disposable checkout failed: " + checkout.stderr)
    actual = run(git_argv("-C", destination, "rev-parse", "HEAD"))
    if actual.returncode != 0 or actual.stdout.strip() != head:
        raise RuntimeError("disposable proof did not pin the exact source HEAD")
    return head


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_port(port, seconds=30):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.3):
                return True
        except OSError:
            time.sleep(0.1)
    return False


def resume_args(arguments):
    output, skip = [], False
    for value in arguments:
        if skip:
            skip = False
            continue
        if value == "--launch":
            output.append("--resume")
        elif value == "--crash-after":
            skip = True
        else:
            output.append(value)
    return output


def drive_launch(repo, target, cp1, prior, runtime, owner_key, endpoint, env):
    runner = os.path.join(repo, "run_observatory.py")
    signer = os.path.join(
        repo, "executable-orchestrator", "tools", "owner_sign.py")
    arguments = [
        "--launch", "--run-id", RUN_ID, "--endpoint", endpoint,
        "--model", MODEL, "--backend", "container",
        "--canonical-repo", target, "--cp1-evidence", cp1,
        "--prior-cp2", prior, "--runtime", runtime,
        "--max-rounds", "12", "--crash-after", "6",
    ]
    transcript, gates = [], []
    crash_seen = False
    for attempt in range(160):
        result = py(runner, *arguments, cwd=repo, env=env, timeout=28800)
        combined = (result.stdout or "") + "\n" + (result.stderr or "")
        transcript.append({
            "attempt": attempt,
            "returncode": result.returncode,
            "stdout_tail": (result.stdout or "")[-5000:],
            "stderr_tail": (result.stderr or "")[-5000:],
        })
        if result.returncode == 10:
            info = read_json(os.path.join(
                runtime, "gates", "AWAITING-OWNER.json"))
            signed = py(
                signer, "--key", owner_key, "--gate", info["awaiting"],
                "--run-id", RUN_ID, "--subject", info["subject"],
                "--decision", "APPROVE", "--out", info["approval_expected_at"],
                cwd=repo, env=env, timeout=300)
            if signed.returncode != 0:
                raise RuntimeError(
                    "owner gate signing failed: "
                    + signed.stdout + signed.stderr)
            gates.append(info["awaiting"])
            arguments = resume_args(arguments)
            continue
        if result.returncode == 0:
            return {
                "completed": True,
                "crash_seen": crash_seen,
                "gates": gates,
                "transcript": transcript,
            }
        if not crash_seen and "SIMULATED CRASH" in combined:
            crash_seen = True
            arguments = resume_args(arguments)
            continue
        return {
            "completed": False,
            "crash_seen": crash_seen,
            "gates": gates,
            "transcript": transcript,
        }
    return {
        "completed": False,
        "crash_seen": crash_seen,
        "gates": gates,
        "transcript": transcript,
    }


def parse_json_output(text):
    stripped = (text or "").strip()
    try:
        return json.loads(stripped)
    except Exception:
        decoder = json.JSONDecoder()
        best = None
        for index, char in enumerate(stripped):
            if char != "{":
                continue
            try:
                value, end = decoder.raw_decode(stripped[index:])
                if stripped[index + end:].strip() == "":
                    best = value
            except Exception:
                continue
        if best is None:
            raise RuntimeError("command produced no parseable JSON object")
        return best


def numbered(paths, expression):
    rows = []
    regex = re.compile(expression)
    for path in paths:
        match = regex.search(os.path.basename(path))
        if match:
            rows.append((int(match.group(1)), path))
    return [path for _number, path in sorted(rows)]


def assert_pass(path, label):
    if not os.path.isfile(path):
        raise RuntimeError(label + " report missing: " + path)
    report = read_json(path)
    if report.get("status") not in ("PASS", "OK") \
            or report.get("passed", True) is not True:
        raise RuntimeError(
            label + " did not pass: "
            + json.dumps(report, ensure_ascii=False)[:2500])
    return report


def verify_ledger(runtime):
    ledger = read_json(os.path.join(runtime, "budget", "ledger.json"))
    entries = ledger.get("entries") or []
    if not entries:
        raise RuntimeError("local provider ledger contains no settled calls")
    for index, entry in enumerate(entries):
        usage = entry.get("usage") or {}
        if entry.get("currency") != "USD" \
                or usage.get("billing_currency") != "USD":
            raise RuntimeError(f"ledger entry {index} is not USD-accounted")
        hit, miss, prompt = (
            usage.get("prompt_cache_hit_tokens"),
            usage.get("prompt_cache_miss_tokens"),
            usage.get("prompt_tokens"),
        )
        if None in (hit, miss, prompt) \
                or int(hit) + int(miss) != int(prompt):
            raise RuntimeError(
                f"ledger entry {index} lacks exact cache split")
        if float(usage.get("billing_amount", -1.0)) < 0.0:
            raise RuntimeError(
                f"ledger entry {index} lacks nonnegative billing amount")
    return {
        "settled_local_calls": len(entries),
        "real_paid_api_calls": 0,
        "local_provider_accounting_verified": True,
    }


def _verify_genome_report(path, label, incumbent):
    report = assert_pass(path, label)
    if report.get("candidate_id") != incumbent \
            or report.get("consensus") is not True \
            or report.get("all_axes_realized") is not True \
            or report.get("verified_axis_count") != 13:
        raise RuntimeError(label + " did not prove all thirteen axes")
    auditors = report.get("auditors") or []
    if len(auditors) != 2 \
            or len({row.get("auditor_id") for row in auditors}) != 2 \
            or len({row.get("logical_id") for row in auditors}) != 2 \
            or len({row.get("report_sha256") for row in auditors}) != 2:
        raise RuntimeError(label + " does not contain two independent auditors")
    for auditor in auditors:
        axes = auditor.get("validated_axes") or []
        if len(axes) != 13:
            raise RuntimeError(label + ": auditor did not validate thirteen axes")
        for axis in axes:
            if axis.get("source_bound_evidence") is not True \
                    or not axis.get("verified_symbols") \
                    or not axis.get("verified_invariant_ids") \
                    or not axis.get("verified_evidence"):
                raise RuntimeError(
                    f"{label}/{axis.get('axis')}: executable evidence is incomplete")
    return report


def verify_protocol(repo, runtime, source_head, preflight, launch):
    summary = read_json(os.path.join(
        runtime, "reports", "run_summary.json"))
    if summary.get("final_state") != "COMMITTED" \
            or summary.get("log_verified") is not True:
        raise RuntimeError(
            "run did not finish COMMITTED with a verified signed log")
    escalation = summary.get("escalation") or {}
    conditions = escalation.get("conditions") or {}
    if not conditions or any(value is not True for value in conditions.values()):
        raise RuntimeError(
            "terminal conditions are incomplete: "
            + ", ".join(
                key for key, value in conditions.items()
                if value is not True))
    missing_new = sorted(EXPECTED_NEW_CONDITIONS - set(conditions))
    if missing_new:
        raise RuntimeError(
            "protocol-v5 terminal conditions absent: "
            + ", ".join(missing_new))
    supremacy = escalation.get("supremacy") or {}
    missing_supremacy = sorted(
        key for key in EXPECTED_NEW_CONDITIONS
        if supremacy.get(key) is not True)
    if missing_supremacy:
        raise RuntimeError(
            "protocol-v5 supremacy summary is incomplete: "
            + ", ".join(missing_supremacy))

    mission = preflight.get("signed_mission") or {}
    if mission.get("protocol_version") != PROTOCOL_VERSION:
        raise RuntimeError("signed mission is not protocol v5")
    if mission.get("runner_head") != source_head:
        raise RuntimeError(
            "signed mission is not bound to proof source HEAD")
    for flag in (
        "cross_model_consistency_required",
        "executable_genome_realization_required",
        "strict_executable_source_schema_required",
        "bounded_candidate_output_required",
        "authoritative_prior_art_challenge_required",
        "terminal_negative_proof_required",
        "proof_mode_forbidden_in_production",
    ):
        if mission.get(flag) is not True:
            raise RuntimeError("signed mission flag missing: " + flag)
    protocol_files = set(mission.get("research_protocol_files") or [])
    missing_files = sorted(REQUIRED_PROTOCOL_FILES - protocol_files)
    if missing_files:
        raise RuntimeError(
            "signed protocol census omitted: " + ", ".join(missing_files))
    if preflight.get("proof_mode") is not True:
        raise RuntimeError(
            "zero-cost proof did not run under explicit proof mode")
    if (preflight.get("container_backend") or {}).get("backend") != "container":
        raise RuntimeError(
            "full proof did not preflight the production container backend")

    receipt = read_json(os.path.join(
        repo, "proof", "observatory-specialized-calibration-receipt.json"))
    if receipt.get("proof_mode") is not True \
            or receipt.get("provider_calls") != 0:
        raise RuntimeError(
            "specialized calibration receipt has wrong mode/provider count")
    if receipt.get("protocol_bundle_sha256") != mission.get(
            "research_protocol_bundle_sha256"):
        raise RuntimeError(
            "specialized calibration receipt is not bound to signed protocol")
    for label in ("distributed", "scale", "formal", "interoperability"):
        row = (receipt.get("campaigns") or {}).get(label) or {}
        if row.get("status") not in ("PASS", "OK") \
                or row.get("passed") is not True:
            raise RuntimeError(label + " reference calibration did not pass")
        report_path = os.path.join(repo, *row["report_path"].split("/"))
        if row.get("report_sha256") != sha256_file(report_path):
            raise RuntimeError(label + " reference calibration hash drift")

    audit = read_json(os.path.join(
        runtime, "audit", "independent_audit.json"))
    if audit.get("protocol_version") != PROTOCOL_VERSION \
            or audit.get("proof_mode") is not True:
        raise RuntimeError(
            "independent audit has wrong protocol/mode")
    if not audit.get("immutable_package_unchanged") \
            or audit.get("hidden_disclosed_to_builder") is not False \
            or audit.get("hidden_cases_disclosed_to_reviser") is not False:
        raise RuntimeError(
            "independent audit failed immutable/hidden guarantees")
    if (audit.get("supremacy_conditions") or {}) != conditions:
        raise RuntimeError(
            "independent audit did not reproduce terminal conditions exactly")
    genome_campaign = (audit.get("campaigns") or {}).get(
        "controlled_genome_realization") or {}
    if genome_campaign.get("qualification") is not True \
            or genome_campaign.get("replication") is not True \
            or genome_campaign.get("crown") is not True \
            or genome_campaign.get("auditors") != 2 \
            or genome_campaign.get("axes") != 13:
        raise RuntimeError(
            "independent audit did not reproduce genome-realization closure")

    forest = read_json(os.path.join(
        runtime, "architecture", "search_forest.json"))
    fsum = forest.get("summary") or {}
    if fsum.get("lineages") != 15 \
            or fsum.get("general_lineages") != 6 \
            or fsum.get("anti_attractor_lineages") != 9 \
            or int(fsum.get("seeds", 0)) < 90 \
            or int(fsum.get("selected_finalists", 0)) < 12 \
            or fsum.get("prior_cp2_visible") is not False:
        raise RuntimeError(
            "search forest is not the required independent 15-lineage forest")
    proposals = read_json(os.path.join(
        runtime, "architecture", "proposals.json"))
    if proposals.get("prior_cp2_visible") is not False \
            or len(proposals.get("proposals") or []) < 12:
        raise RuntimeError(
            "complete proposal frontier is too small or CP2-contaminated")
    built = read_json(os.path.join(
        runtime, "candidates", "built.json"))
    if built.get("complete_blueprint_handoff") is not True \
            or built.get("formalization_handoff") is not True \
            or len(built.get("built") or []) < 2:
        raise RuntimeError(
            "complete blueprint/formalization handoff failed")

    incumbent = escalation["incumbent"]
    assert_pass(os.path.join(
        runtime, "reports", f"systems-crown-{incumbent}.json"),
        "durable crown")
    assert_pass(os.path.join(
        runtime, "reports", f"distributed-crown-{incumbent}.json"),
        "distributed crown")
    assert_pass(os.path.join(
        runtime, "reports", f"scale-crown-{incumbent}.json"),
        "scale crown")
    cross = assert_pass(os.path.join(
        runtime, "reports", f"cross-model-crown-{incumbent}.json"),
        "cross-model crown")

    expected_histories = int(
        (mission.get("production_workloads") or {})
        .get("cross_model", {}).get("crown_histories", 0))
    proof_histories = int(
        (audit.get("workload_policy") or {})
        .get("cross_model", {}).get("crown_histories", 0))
    if cross.get("histories") != proof_histories \
            or expected_histories <= proof_histories:
        raise RuntimeError(
            "cross-model crown did not preserve the signed proof/production boundary")

    formal_crown = glob.glob(os.path.join(
        runtime, "reports", f"formal-crown-{incumbent}-*.json"))
    interop_crown = glob.glob(os.path.join(
        runtime, "reports",
        f"interoperability-crown-{incumbent}-*.json"))
    if len(formal_crown) != 2 or len(interop_crown) != 2:
        raise RuntimeError(
            "independent formal/interoperability crown evidence count is wrong")
    formal_reports = [assert_pass(path, "formal crown") for path in formal_crown]
    interop_reports = [assert_pass(
        path, "interoperability crown") for path in interop_crown]
    if len({row.get("behavioral_digest") for row in formal_reports}) != 1 \
            or None in {row.get("behavioral_digest") for row in formal_reports}:
        raise RuntimeError("independent formal crowns disagree")
    if any(row.get("behavioral_digest_mode")
           != "ordered-length-delimited-stream-v1"
           for row in formal_reports):
        raise RuntimeError("formal crown did not use streaming digest mode")
    if len({row.get("semantic_digest") for row in interop_reports}) != 1 \
            or None in {row.get("semantic_digest") for row in interop_reports}:
        raise RuntimeError("independent interoperability crowns disagree")

    architecture = os.path.join(runtime, "architecture")
    genome_reports = {
        label: _verify_genome_report(os.path.join(
            architecture,
            f"genome-realization-{label}-{incumbent}.json"),
            f"genome realization {label}", incumbent)
        for label in ("qualification", "replication", "crown")
    }

    prior_paths = numbered(glob.glob(os.path.join(
        runtime, "architecture", "prior-art-round*.json")), r"round(\d+)")
    if not prior_paths:
        raise RuntimeError("authoritative prior-art campaign is missing")
    prior = read_json(prior_paths[-1])
    if prior.get("all_sources_assessed") is not True \
            or prior.get("challengers_measured") is not True \
            or prior.get("no_blockers") is not True \
            or prior.get("blockers") \
            or prior.get("unresolved"):
        raise RuntimeError(
            "authoritative prior-art campaign did not close")
    for critic in prior.get("critics") or []:
        for review in (critic.get("report") or {}).get(
                "source_reviews") or []:
            if review.get("disposition") == "SATISFIED":
                verified = review.get("verified_evidence") or []
                if not verified:
                    raise RuntimeError(
                        "SATISFIED prior-art review has no verified evidence")
                for evidence in verified:
                    path = os.path.join(
                        runtime, *evidence["path"].split("/"))
                    if not os.path.isfile(path) \
                            or sha256_file(path) != evidence["sha256"]:
                        raise RuntimeError(
                            "prior-art verified evidence hash mismatch")

    novelty_paths = numbered(glob.glob(os.path.join(
        runtime, "architecture", "novelty-wave-r*.json")), r"r(\d+)")
    if len(novelty_paths) < 3:
        raise RuntimeError("fewer than three active novelty waves exist")
    for path in novelty_paths[-3:]:
        wave = read_json(path)
        ledger = wave.get("ledger_wave") or {}
        if ledger.get("dry") is not True \
                or ledger.get("methods_complete") is not True \
                or ledger.get("backlog_count") != 0 \
                or ledger.get("unresolved_count") != 0 \
                or ledger.get("prior_cp2_direct_content_read") is not False:
            raise RuntimeError("final novelty waves are not genuinely dry")
        match = re.search(r"r(\d+)\.json$", path)
        if not match:
            raise RuntimeError("novelty wave filename is malformed")
        meta = read_json(os.path.join(
            runtime, "architecture",
            f"meta-search-wave-r{match.group(1)}.json"))
        if len(meta.get("meta_critics") or []) != 2 \
                or len(meta.get("closure_auditors") or []) != 2 \
                or (meta.get("coverage_after") or {}).get(
                    "complete") is not True:
            raise RuntimeError(
                "meta-search/closure evidence is incomplete")

    lower = read_json(os.path.join(
        runtime, "architecture", "lower_bounds.json"))
    destroyers = read_json(os.path.join(
        runtime, "architecture", "final_destroyers.json"))
    case = read_json(os.path.join(
        runtime, "architecture", "SUPREMACY-CASE.json"))
    if lower.get("closed") is not True \
            or destroyers.get("survived") is not True \
            or case.get("mechanically_supported") is not True \
            or case.get("third_party_endorsement_claimed") is not False:
        raise RuntimeError(
            "lower-bound/destroyer/public supremacy evidence did not close")

    required_gates = {
        "GATE-ARCH-V0", "GATE-ARCH-V1",
        "GATE-MIGRATION", "GATE-COMMIT"}
    if not required_gates.issubset(set(launch.get("gates") or [])):
        raise RuntimeError("proof did not traverse all owner gates")

    reality = read_json(os.path.join(
        runtime, "reality", "REPOSITORY-REALITY-MODEL.json"))
    history = read_json(os.path.join(
        runtime, "reality", "HISTORICAL-EXPERIMENT-MAP.json"))
    if reality.get("repository_archaeology_api_calls") != 0 \
            or history.get("prior_cp2_content_read") is not False:
        raise RuntimeError(
            "CP1 reuse / pre-frontier CP2 quarantine failed")

    return {
        "summary": summary,
        "audit": audit,
        "incumbent": incumbent,
        "conditions": sorted(conditions),
        "search_forest": fsum,
        "prior_art_sources": prior.get("source_count"),
        "novelty_waves": len(novelty_paths),
        "cross_model_histories": cross.get("histories"),
        "genome_realization": {
            label: {
                "genome_sha256": report.get("genome_sha256"),
                "contract_sha256": report.get("contract_sha256"),
                "auditors": len(report.get("auditors") or []),
            }
            for label, report in genome_reports.items()
        },
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--canonical-repo", required=True)
    parser.add_argument("--cp1-evidence", required=True)
    parser.add_argument("--prior-cp2", required=True)
    parser.add_argument("--keep", action="store_true")
    args = parser.parse_args(argv)

    target, cp1, prior = map(os.path.abspath, (
        args.canonical_repo, args.cp1_evidence, args.prior_cp2))
    workspace = short_workspace()
    repo = os.path.join(workspace, "r")
    runtime = os.path.join(workspace, "rt")
    mock = None
    env = dict(os.environ)
    env[PROOF_ENV] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    result = {
        "proof": "complete-observatory-protocol-zero-cost-e2e-v5",
        "protocol_version": PROTOCOL_VERSION,
        "paid_api_calls": 0,
        "workspace": workspace,
        "runtime": runtime,
        "status": "FAIL",
    }
    try:
        source_head = clone_exact(repo)
        result["source_head"] = source_head

        setup = py(
            os.path.join(repo, "setup_observatory.py"),
            "--run-id", RUN_ID,
            "--budget-usd", "500",
            "--tokens", "500000000",
            "--calls", "100000",
            "--days", "7",
            "--qualification", "3",
            "--replication", "2",
            "--holdout", "2",
            cwd=repo, env=env, timeout=28800)
        result["setup"] = {
            "returncode": setup.returncode,
            "tail": (setup.stdout + setup.stderr)[-8000:],
        }
        if setup.returncode != 0:
            raise RuntimeError(
                "owner ceremony/calibration failed:\n"
                + result["setup"]["tail"])

        port = free_port()
        endpoint = f"http://127.0.0.1:{port}/chat/completions"
        preflight = py(
            os.path.join(repo, "run_observatory.py"),
            "--preflight", "--run-id", RUN_ID,
            "--endpoint", endpoint,
            "--model", MODEL,
            "--backend", "container",
            "--runtime", runtime,
            "--canonical-repo", target,
            "--cp1-evidence", cp1,
            "--prior-cp2", prior,
            cwd=repo, env=env, timeout=1800)
        result["preflight"] = {
            "returncode": preflight.returncode,
            "tail": (preflight.stdout + preflight.stderr)[-8000:],
        }
        if preflight.returncode != 0:
            raise RuntimeError(
                "protocol preflight failed:\n"
                + result["preflight"]["tail"])
        preflight_report = parse_json_output(preflight.stdout)

        mock_script = os.path.join(
            repo, "executable-orchestrator", "tools",
            "mock_observatory_protocol_server.py")
        mock = subprocess.Popen(
            [sys.executable, mock_script, "--port", str(port)],
            cwd=repo, env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL)
        if not wait_port(port):
            raise RuntimeError(
                "complete protocol localhost provider did not start")

        launch_env = dict(env)
        launch_env["DEEPSEEK_API_KEY"] = "local-proof-not-a-real-key"
        owner_key = os.path.join(
            repo, "private-evaluator", "owner-held-secrets", "OWNER.key")
        launch = drive_launch(
            repo, target, cp1, prior, runtime,
            owner_key, endpoint, launch_env)
        result["launch"] = launch
        if not launch["completed"] or not launch["crash_seen"]:
            raise RuntimeError(
                "shared state-machine launch/crash-resume did not complete")

        verified = verify_protocol(
            repo, runtime, source_head, preflight_report, launch)
        result["protocol_verification"] = {
            key: value for key, value in verified.items()
            if key not in ("summary", "audit")}
        result["run_summary"] = verified["summary"]
        result["independent_audit"] = verified["audit"]
        result["accounting"] = verify_ledger(runtime)

        guard_out = os.path.join(
            runtime, "proof", "terminal-condition-closure.json")
        guard = py(
            os.path.join(
                repo, "executable-orchestrator", "tools",
                "prove_terminal_condition_closure.py"),
            "--runtime", runtime,
            "--run-id", RUN_ID,
            "--canonical-repo", target,
            "--cp1-evidence", cp1,
            "--prior-cp2", prior,
            "--endpoint", endpoint,
            "--out", guard_out,
            cwd=repo, env=launch_env, timeout=3600)
        result["terminal_guard"] = {
            "returncode": guard.returncode,
            "tail": (guard.stdout + guard.stderr)[-8000:],
        }
        if guard.returncode != 0 \
                or read_json(guard_out).get("status") != "PASS":
            raise RuntimeError(
                "terminal condition negative proof failed:\n"
                + result["terminal_guard"]["tail"])
        result["terminal_guard_proof"] = read_json(guard_out)
        result["status"] = "PASS"
    except Exception as exc:
        result["reason"] = str(exc)
    finally:
        if mock is not None:
            mock.terminate()
            try:
                mock.wait(timeout=5)
            except subprocess.TimeoutExpired:
                mock.kill()
                mock.wait()
        os.environ.pop("DEEPSEEK_API_KEY", None)
        output = os.path.join(
            ROOT, "proof", "complete-observatory-protocol-e2e.json")
        write_json(output, result)
        print(json.dumps(
            result, ensure_ascii=False, indent=1, sort_keys=True))
        print("proof report:", output)
        if args.keep or result.get("status") != "PASS":
            print("disposable proof directory retained:", workspace)
        else:
            shutil.rmtree(workspace, ignore_errors=True)
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
