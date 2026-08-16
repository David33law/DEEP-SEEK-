"""Fail-closed preflight for the National Legal Observatory profile."""
import json
import os
import platform
import subprocess
import sys

from .canonical import read_json
from . import preflight as base

PreflightFailed = base.PreflightFailed


def _git(repo, *args):
    r = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise PreflightFailed(f"git {' '.join(args)} failed for {repo}: {r.stderr.strip()[:500]}")
    return r.stdout.strip()


def _find_one(root, name):
    hits = []
    for r, _ds, fs in os.walk(root):
        if name in fs:
            hits.append(os.path.join(r, name))
    if len(hits) != 1:
        raise PreflightFailed(f"expected exactly one {name!r} under {root}, found {len(hits)}")
    return hits[0]


def _profile_paths(root):
    return {
        "profile": os.path.join(root, "profiles", "national-observatory"),
        "bank": os.path.join(root, "private-evaluator", "observatory-hidden-bank"),
        "key": os.path.join(root, "private-evaluator", "owner-held-secrets", "OBSERVATORY-HIDDEN.key"),
        "suite": os.path.join(root, "benchmark", "observatory-visible-suite.json"),
        "reference": os.path.join(root, "benchmark", "observatory_reference_candidate.py"),
    }


def run(root, orchestrator_root, runtime, require_vault=True, owner_public=None):
    problems = []
    v = base.check_python()
    if v:
        problems.append(v)
    problems += base.check_dependencies()
    lock = base.check_lock_concurrency(os.path.join(runtime, "state", "observatory-preflight.lock"))
    if lock:
        problems.append(lock)
    # This checks the historical LAWMAX immutable-package. Observatory files live outside it,
    # so a profile run cannot silently invalidate the old seal.
    problems += base.check_package(orchestrator_root)

    P = _profile_paths(root)
    required_profile = ["OBJECTIVE-CHARTER.md", "PARETO-DIMENSIONS.json",
                        "ARCHITECTURE-DISCOVERY-PROTOCOL.md", "MASTER-SYSTEM-PROMPT.md",
                        "EVALUATOR-CONTRACT.md", "TARGET-BASELINE.json"]
    for name in required_profile:
        if not os.path.isfile(os.path.join(P["profile"], name)):
            problems.append(f"Observatory profile file missing: {name}")

    canonical_repo = os.environ.get("OBSERVATORY_CANONICAL_REPO", "")
    cp1_evidence = os.environ.get("OBSERVATORY_CP1_EVIDENCE", "")
    prior_cp2 = os.environ.get("OBSERVATORY_PRIOR_CP2", "")
    baseline = None
    try:
        baseline = read_json(os.path.join(P["profile"], "TARGET-BASELINE.json"))
    except Exception as exc:  # noqa: BLE001
        problems.append(f"TARGET-BASELINE unreadable: {exc}")

    target_report = {}
    if require_vault:
        if not canonical_repo or not os.path.isdir(os.path.join(canonical_repo, ".git")):
            problems.append("OBSERVATORY_CANONICAL_REPO is missing or not a Git checkout")
        elif baseline:
            try:
                head = _git(canonical_repo, "rev-parse", "HEAD")
                tree = _git(canonical_repo, "rev-parse", "HEAD^{tree}")
                dirty = _git(canonical_repo, "status", "--porcelain")
                remotes = _git(canonical_repo, "remote")
                target_report = {"head": head, "tree": tree, "dirty": bool(dirty),
                                 "remote_count": len([x for x in remotes.splitlines() if x.strip()])}
                if head != baseline["target_commit"] or tree != baseline["target_tree"]:
                    problems.append("canonical repository commit/tree does not match sealed CP1 baseline")
                if dirty:
                    problems.append("canonical repository working tree is dirty")
                if remotes.strip():
                    problems.append("canonical repository has remotes; target must remain isolated")
            except PreflightFailed as exc:
                problems.append(str(exc))

        if not cp1_evidence or not os.path.isdir(cp1_evidence):
            problems.append("OBSERVATORY_CP1_EVIDENCE is missing")
        elif baseline:
            try:
                receipt_p = os.path.join(cp1_evidence, "SEALED-VERIFICATION-RECEIPT.json")
                receipt = read_json(receipt_p)
                source = receipt.get("source_target", {})
                if source.get("commit") != baseline["target_commit"] or source.get("tree") != baseline["target_tree"]:
                    problems.append("CP1 sealed receipt is not bound to the target baseline")
                _find_one(cp1_evidence, "CP1-REPOSITORY-RECONSTRUCTION.md")
            except Exception as exc:  # noqa: BLE001
                problems.append(f"CP1 evidence rejected: {exc}")

        if not prior_cp2 or not os.path.isdir(prior_cp2):
            problems.append("OBSERVATORY_PRIOR_CP2 is missing")
        elif baseline:
            try:
                receipt = read_json(os.path.join(prior_cp2, "SEALED-VERIFICATION-RECEIPT.json"))
                p = receipt.get("prior_study", {})
                e = baseline["prior_cp2"]
                if p.get("model") != e["expected_model"] or int(p.get("dossiers", -1)) != e["expected_dossiers"]:
                    problems.append("prior CP2 receipt model/dossier identity mismatch")
                if p.get("machine_verdict") != e["expected_verdict"] or bool(p.get("cp3_started")) != e["expected_cp3_started"]:
                    problems.append("prior CP2 receipt verdict/CP3 state mismatch")
                archive = receipt.get("archive", {})
                if archive.get("sha256") != e["expected_archive_sha256"]:
                    problems.append("prior CP2 archive hash does not match profile baseline")
            except Exception as exc:  # noqa: BLE001
                problems.append(f"prior CP2 evidence rejected: {exc}")

        for label in ("bank", "key", "suite", "reference"):
            if not os.path.exists(P[label]):
                problems.append(f"Observatory {label} missing: {P[label]}")
        if os.path.exists(P["bank"]):
            try:
                pub = read_json(os.path.join(P["bank"], "PUBLIC-commitment.json"))
                if pub.get("profile") != "national-observatory":
                    problems.append("hidden bank belongs to a different profile")
                evaluator = os.path.join(root, "private-evaluator", "evaluator")
                if evaluator not in sys.path:
                    sys.path.insert(0, evaluator)
                import observatory_evaluate
                observatory_evaluate.check_grader_freeze(P["bank"])
            except Exception as exc:  # noqa: BLE001
                problems.append(f"Observatory hidden bank rejected: {exc}")
        if os.path.exists(P["suite"]):
            try:
                suite = read_json(P["suite"])
                if suite.get("suite") != "national-observatory-visible-replay-v1" or not suite.get("scenarios"):
                    problems.append("visible Observatory replay suite is malformed")
            except Exception as exc:  # noqa: BLE001
                problems.append(f"visible suite unreadable: {exc}")
        if os.path.exists(P["reference"]):
            try:
                compile(open(P["reference"], encoding="utf-8").read(), "<observatory-reference>", "exec")
            except Exception as exc:  # noqa: BLE001
                problems.append(f"Observatory reference candidate does not compile: {exc}")

    report = {
        "profile": "national-observatory",
        "python": platform.python_version(),
        "canonical_target": target_report,
        "cp1_evidence": cp1_evidence or None,
        "prior_cp2": prior_cp2 or None,
        "prior_cp2_visibility": (baseline or {}).get("prior_cp2", {}).get("visibility"),
        "profile_paths": P,
        "problems": problems,
        "ok": not problems,
    }
    if problems:
        raise PreflightFailed("\n  - ".join(["Observatory preflight refused to launch:"] + problems))
    return report
