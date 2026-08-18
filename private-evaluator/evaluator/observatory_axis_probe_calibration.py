#!/usr/bin/env python3
"""Exhaustive zero-provider calibration for the trusted axis-probe evaluator.

Every allowed ``(group, axis)`` route is executed twice through
``observatory_axis_probe_arena_v2.py``: the exact calibration reference must PASS, while a
mechanically controlled source mutation must produce a valid candidate-origin FAIL with at least one
structured false axis check. The suite persists all 28 pairs, 56 reports and exact source/evaluator
hashes. It calibrates the evaluator path; it does not certify a tournament architecture.

Evaluator child processes are launched with explicit UTF-8 stdin/stdout semantics independent of the
Windows active code page. Baselines are validated before the corresponding mutant is executed, and a
failed route records the exact status/origin/check/process diagnostics instead of only a generic label.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import traceback


HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
EVALUATOR_RELATIVE = (
    "private-evaluator/evaluator/observatory_axis_probe_arena_v2.py")
EVALUATOR = os.path.join(ROOT, *EVALUATOR_RELATIVE.split("/"))
CONTRACT = "observatory-axis-probe-v1"
DEFAULT_EVIDENCE = os.path.join(
    ROOT, "proof", "axis-probe-calibration-evidence")

GROUP_AXES = {
    "semantic": (
        "canonical_authority_seat", "evidence_primitive", "identity_model",
        "state_derivation_model", "temporal_model", "normative_effect_model",
        "provenance_proof_model", "publication_topology",
        "governance_evolution_model"),
    "systems": ("trusted_core_topology",),
    "distributed": (
        "consistency_commit_model", "replication_distribution_model"),
    "scale": ("scaling_partition_model",),
    "formal": (
        "canonical_authority_seat", "evidence_primitive", "identity_model",
        "state_derivation_model", "temporal_model", "normative_effect_model",
        "consistency_commit_model", "replication_distribution_model",
        "trusted_core_topology", "governance_evolution_model"),
    "interoperability": (
        "identity_model", "temporal_model", "normative_effect_model",
        "provenance_proof_model", "publication_topology"),
}
REFERENCES = {
    "semantic": "benchmark/observatory_reference_candidate.py",
    "systems": "benchmark/observatory_systems_reference_candidate.py",
    "distributed": "benchmark/observatory_distributed_reference_candidate.py",
    "scale": "benchmark/observatory_scale_reference_candidate.py",
    "formal": "benchmark/observatory_formal_reference_candidate.py",
    "interoperability": (
        "benchmark/observatory_interoperability_reference_candidate.py"),
}
EXPECTED = {
    "semantic": {},
    "systems": {},
    "distributed": {
        "replication_distribution_model": "single_primary_read_replicas",
        "consistency_commit_model": "single_writer_sequence",
    },
    "scale": {"scaling_partition_model": "source_sharding"},
    "formal": {
        "canonical_authority_seat": "evidence_set",
        "state_derivation_model": "replay_reducer",
        "temporal_model": "bitemporal_intervals",
        "normative_effect_model": "typed_directive_interpreter",
        "consistency_commit_model": "single_writer_sequence",
        "replication_distribution_model": "single_primary_read_replicas",
        "trusted_core_topology": "state_machine_kernel",
    },
    "interoperability": {
        "identity_model": "composite_identity",
        "temporal_model": "bitemporal_intervals",
        "normative_effect_model": "typed_directive_interpreter",
        "provenance_proof_model": "provenance_graph",
        "publication_topology": "compiled_read_only_projections",
    },
}
MUTATIONS = {
    ("semantic", "canonical_authority_seat"): "state_at",
    ("semantic", "evidence_primitive"): "ingest",
    ("semantic", "identity_model"): "state_at",
    ("semantic", "state_derivation_model"): "replay",
    ("semantic", "temporal_model"): "state_at",
    ("semantic", "normative_effect_model"): "apply_change",
    ("semantic", "provenance_proof_model"): "provenance",
    ("semantic", "publication_topology"): "publish",
    ("semantic", "governance_evolution_model"): "register_change_handler",
    ("systems", "trusted_core_topology"): "open_system",
    ("distributed", "consistency_commit_model"): "open_cluster",
    ("distributed", "replication_distribution_model"): "open_cluster",
    ("scale", "scaling_partition_model"): "open_scale",
    ("formal", "canonical_authority_seat"): "state_root",
    ("formal", "evidence_primitive"): "transition",
    ("formal", "identity_model"): "query",
    ("formal", "state_derivation_model"): "transition",
    ("formal", "temporal_model"): "query",
    ("formal", "normative_effect_model"): "transition",
    ("formal", "consistency_commit_model"): "transition",
    ("formal", "replication_distribution_model"): "transition",
    ("formal", "trusted_core_topology"): "publication",
    ("formal", "governance_evolution_model"): "transition",
    ("interoperability", "identity_model"): "project",
    ("interoperability", "temporal_model"): "project",
    ("interoperability", "normative_effect_model"): "project",
    ("interoperability", "provenance_proof_model"): "project",
    ("interoperability", "publication_topology"): "project",
}


def _path(relative):
    return os.path.join(ROOT, *relative.split("/"))


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"))


def _slug(value):
    return "".join(
        char if char.isalnum() or char in ("-", "_") else "-"
        for char in str(value))


def _definitions(source):
    tree = ast.parse(source)
    return {
        node.name for node in ast.walk(tree)
        if isinstance(node, (
            ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}


def _mutant_source(source, symbol, group, axis):
    if symbol not in _definitions(source):
        raise RuntimeError(
            f"calibration mutation symbol absent: {group}/{axis}/{symbol}")
    marker = hashlib.sha256(
        f"axis-probe-calibration|{group}|{axis}|{symbol}".encode()).hexdigest()
    mutated = (
        source.rstrip() + "\n\n"
        "# evaluator-calibration mutation; never used as a tournament candidate\n"
        f"{symbol} = None\n"
        f"__axis_probe_calibration_marker__ = {marker!r}\n")
    compile(mutated, f"<axis-probe-calibration-{group}-{axis}>", "exec")
    return mutated, marker


def _utf8_env():
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return env


def _run(candidate, group, axis, output, seed, expected, timeout):
    command = [
        sys.executable, EVALUATOR,
        "--candidate", candidate,
        "--group", group,
        "--axis", axis,
        "--out", output,
        "--seed", str(seed),
        "--expected-json", _canonical(expected),
    ]
    process = subprocess.run(
        command, capture_output=True, text=True,
        encoding="utf-8", errors="strict", env=_utf8_env(), timeout=timeout)
    if not os.path.isfile(output):
        raise RuntimeError(
            "axis-probe calibration produced no report: "
            + _canonical({
                "group": group, "axis": axis,
                "returncode": process.returncode,
                "stdout_tail": (process.stdout or "")[-2000:],
                "stderr_tail": (process.stderr or "")[-2000:],
            }))
    with open(output, encoding="utf-8") as handle:
        report = json.load(handle)
    if not isinstance(report, dict):
        raise RuntimeError("axis-probe calibration report is not an object")
    report["calibration_process_returncode"] = process.returncode
    report["calibration_stdout_tail"] = (process.stdout or "")[-2000:]
    report["calibration_stderr_tail"] = (process.stderr or "")[-2000:]
    report["calibration_transport_encoding"] = "utf-8"
    temporary = output + ".tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=1, sort_keys=True)
        handle.flush(); os.fsync(handle.fileno())
    os.replace(temporary, output)
    return report


def _valid_report(report, *, baseline, candidate_sha, group, axis,
                  seed, expected_sha):
    checks = report.get("checks") or []
    common = bool(
        report.get("contract") == CONTRACT
        and report.get("valid_execution") is True
        and report.get("group") == group
        and report.get("axis") == axis
        and report.get("probe_id") == f"{CONTRACT}:{group}:{axis}"
        and report.get("seed") == seed
        and report.get("candidate_sha256") == candidate_sha
        and report.get("expected_sha256") == expected_sha
        and report.get("calibration_transport_encoding") == "utf-8"
        and isinstance(checks, list) and checks
        and all(isinstance(row, dict)
                and isinstance(row.get("passed"), bool)
                for row in checks))
    if baseline:
        return bool(
            common
            and report.get("status") == "PASS"
            and report.get("passed") is True
            and report.get("failure_origin") == "none"
            and report.get("calibration_process_returncode") == 0
            and all(row["passed"] is True for row in checks))
    return bool(
        common
        and report.get("status") == "FAIL"
        and report.get("passed") is False
        and report.get("failure_origin") == "candidate_axis_behavior"
        and report.get("calibration_process_returncode") == 1
        and any(row["passed"] is False for row in checks))


def _diagnostic(report, path):
    checks = report.get("checks") or []
    return {
        "report_path": os.path.relpath(path, ROOT).replace("\\", "/"),
        "status": report.get("status"),
        "passed": report.get("passed"),
        "valid_execution": report.get("valid_execution"),
        "failure_origin": report.get("failure_origin"),
        "reason": report.get("reason"),
        "process_returncode": report.get("calibration_process_returncode"),
        "transport_encoding": report.get("calibration_transport_encoding"),
        "failed_checks": [
            str(row.get("id")) for row in checks
            if isinstance(row, dict) and row.get("passed") is False],
        "stdout_tail": (report.get("calibration_stdout_tail") or "")[-1000:],
        "stderr_tail": (report.get("calibration_stderr_tail") or "")[-1000:],
        "detail": report.get("detail"),
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out", default=os.path.join(
            ROOT, "proof", "axis-probe-reference-calibration.json"))
    parser.add_argument("--evidence-dir", default=DEFAULT_EVIDENCE)
    parser.add_argument("--timeout", type=int, default=1800)
    args = parser.parse_args(argv)

    output = os.path.abspath(args.out)
    evidence_dir = os.path.abspath(args.evidence_dir)
    report = {
        "status": "FAIL", "passed": False,
        "calibration": "observatory-axis-probe-exhaustive-v1",
        "axis_probe_contract": CONTRACT,
        "provider_calls": 0,
        "transport_encoding": "utf-8",
        "evaluator": {
            "path": EVALUATOR_RELATIVE,
            "sha256": _sha256(EVALUATOR),
            "bytes": os.path.getsize(EVALUATOR),
        },
        "pairs": [],
    }
    try:
        if not os.path.isfile(EVALUATOR):
            raise RuntimeError("axis-probe v2 evaluator is missing")
        if os.path.isdir(evidence_dir):
            shutil.rmtree(evidence_dir)
        os.makedirs(evidence_dir, exist_ok=True)
        expected_pairs = sum(len(axes) for axes in GROUP_AXES.values())
        if set(MUTATIONS) != {
                (group, axis)
                for group, axes in GROUP_AXES.items() for axis in axes}:
            raise RuntimeError(
                "axis-probe calibration mutation map does not cover the exact route set")

        for group in sorted(GROUP_AXES):
            reference_relative = REFERENCES[group]
            reference_path = _path(reference_relative)
            if not os.path.isfile(reference_path):
                raise RuntimeError(
                    f"axis-probe calibration reference missing: {reference_relative}")
            source = open(reference_path, encoding="utf-8").read()
            compile(source, reference_relative, "exec")
            reference_sha = _sha256(reference_path)
            expected = EXPECTED[group]
            expected_sha = hashlib.sha256(
                _canonical(expected).encode("utf-8")).hexdigest()
            for axis in sorted(GROUP_AXES[group]):
                symbol = MUTATIONS[(group, axis)]
                identity = hashlib.sha256(
                    f"axis-calibration|{group}|{axis}".encode()).hexdigest()
                seed = int(hashlib.sha256(
                    f"axis-calibration-seed|{identity}".encode()).hexdigest()[:8], 16)
                prefix = f"{_slug(group)}--{_slug(axis)}"
                baseline_report_path = os.path.join(
                    evidence_dir, prefix + "--baseline.json")
                mutant_report_path = os.path.join(
                    evidence_dir, prefix + "--mutant.json")
                mutant_source_path = os.path.join(
                    evidence_dir, prefix + "--mutant.py")
                mutant, marker = _mutant_source(
                    source, symbol, group, axis)
                with open(mutant_source_path, "w", encoding="utf-8") as handle:
                    handle.write(mutant)
                mutant_sha = _sha256(mutant_source_path)
                if mutant_sha == reference_sha:
                    raise RuntimeError(
                        f"axis-probe calibration mutation did not change source: {group}/{axis}")

                # Baseline is authoritative calibration of the route. Never spend the mutant
                # execution if the exact passing reference does not first establish a valid probe.
                baseline = _run(
                    reference_path, group, axis, baseline_report_path,
                    seed, expected, args.timeout)
                if not _valid_report(
                        baseline, baseline=True,
                        candidate_sha=reference_sha, group=group, axis=axis,
                        seed=seed, expected_sha=expected_sha):
                    diagnostic = _diagnostic(baseline, baseline_report_path)
                    report["failed_route"] = {
                        "variant": "baseline", "group": group, "axis": axis,
                        **diagnostic}
                    raise RuntimeError(
                        "axis-probe baseline calibration failed: "
                        f"{group}/{axis} :: " + _canonical(diagnostic))

                mutant_report = _run(
                    mutant_source_path, group, axis, mutant_report_path,
                    seed, expected, args.timeout)
                if not _valid_report(
                        mutant_report, baseline=False,
                        candidate_sha=mutant_sha, group=group, axis=axis,
                        seed=seed, expected_sha=expected_sha):
                    diagnostic = _diagnostic(mutant_report, mutant_report_path)
                    report["failed_route"] = {
                        "variant": "mutant", "group": group, "axis": axis,
                        **diagnostic}
                    raise RuntimeError(
                        "axis-probe mutant calibration failed: "
                        f"{group}/{axis} :: " + _canonical(diagnostic))
                if baseline.get("probe_id") != mutant_report.get("probe_id") \
                        or baseline.get("seed") != mutant_report.get("seed") \
                        or baseline.get("expected_sha256") != mutant_report.get(
                            "expected_sha256"):
                    raise RuntimeError(
                        f"axis-probe calibration pair identity drift: {group}/{axis}")
                failed_checks = sorted(
                    str(row.get("id"))
                    for row in mutant_report.get("checks") or []
                    if row.get("passed") is False)
                report["pairs"].append({
                    "task_identity_sha256": identity,
                    "group": group, "axis": axis,
                    "mutation_symbol": symbol,
                    "mutation_marker": marker,
                    "probe_id": baseline["probe_id"],
                    "seed": seed,
                    "expected_sha256": expected_sha,
                    "reference_path": reference_relative,
                    "reference_sha256": reference_sha,
                    "mutant_source_path": os.path.relpath(
                        mutant_source_path, ROOT).replace("\\", "/"),
                    "mutant_source_sha256": mutant_sha,
                    "baseline_report_path": os.path.relpath(
                        baseline_report_path, ROOT).replace("\\", "/"),
                    "baseline_report_sha256": _sha256(
                        baseline_report_path),
                    "mutant_report_path": os.path.relpath(
                        mutant_report_path, ROOT).replace("\\", "/"),
                    "mutant_report_sha256": _sha256(mutant_report_path),
                    "mutant_failed_checks": failed_checks,
                })

        paths = [
            row[key] for row in report["pairs"]
            for key in ("baseline_report_path", "mutant_report_path")]
        identities = {
            row["task_identity_sha256"] for row in report["pairs"]}
        if len(report["pairs"]) != expected_pairs \
                or len(identities) != expected_pairs \
                or len(set(paths)) != 2 * expected_pairs:
            raise RuntimeError(
                "axis-probe calibration pair/report identity census drift")
        report.update({
            "status": "PASS", "passed": True,
            "groups": len(GROUP_AXES),
            "axis_routes": expected_pairs,
            "baseline_reports": expected_pairs,
            "mutant_reports": expected_pairs,
            "valid_probe_pairs": expected_pairs,
            "evidence_dir": os.path.relpath(
                evidence_dir, ROOT).replace("\\", "/"),
            "proof_boundary": (
                "zero-provider calibration of all declared axis-probe routes over fixed "
                "reference sources and controlled missing-entrypoint mutants; not a "
                "tournament architecture proof"),
        })
    except Exception as exc:
        report["reason"] = f"{type(exc).__name__}: {exc}"
        report["traceback"] = traceback.format_exc()[-6000:]

    os.makedirs(os.path.dirname(output), exist_ok=True)
    temporary = output + f".tmp-{os.getpid()}"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=1, sort_keys=True)
        handle.flush(); os.fsync(handle.fileno())
    os.replace(temporary, output)
    # Diagnostic stdout is ASCII-safe; the canonical report remains UTF-8 on disk.
    print(json.dumps(report, ensure_ascii=True, indent=1, sort_keys=True))
    return 0 if report.get("status") == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
