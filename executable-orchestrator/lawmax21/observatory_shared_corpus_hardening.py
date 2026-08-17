"""Ensure independent formal/interoperability implementations face the same hidden corpus.

Source generation remains independent. Agreement is meaningful only when both implementations are
run against the same hidden seed; perspective-specific seeds made equal implementations produce
unrelated digests and rendered the agreement gate unreachable.
"""
import hashlib
import os
import subprocess
import sys

from . import observatory_formal_overlay as formal
from . import observatory_interoperability_overlay as interop
from .canonical import read_json
from .handlers import A


def _formal_run(ctx, cid, perspective, label, depth, candidate_path=None):
    path = candidate_path or formal._path(ctx, cid, perspective)
    if not os.path.isfile(path):
        return {"status": "FAIL", "passed": False, "reason": "formal model missing"}
    out = A(ctx, "reports", f"formal-{label}-{cid}-{perspective}.json")
    seed = int(hashlib.sha256(
        f"formal|{label}|{ctx.run_id}|{cid}".encode()).hexdigest()[:8], 16)
    command = [sys.executable,
               os.path.join(ctx.evaluator_dir, "observatory_formal_arena.py"),
               "--candidate", path, "--out", out, "--seed", str(seed),
               "--depth", str(depth), "--timeout", "14400"]
    for axis, value in formal._expected(ctx, cid).items():
        command.extend(["--expected-" + axis.replace("_", "-"), value])
    result = subprocess.run(command, capture_output=True, text=True)
    if not os.path.exists(out):
        return {"status": "FAIL", "passed": False,
                "reason": "formal evaluator produced no report: "
                          + (result.stdout + result.stderr)[-1600:]}
    report = read_json(out); report["evaluator_returncode"] = result.returncode
    report["evidence_path"] = os.path.relpath(out, ctx.runtime).replace("\\", "/")
    report["candidate_path"] = os.path.relpath(path, ctx.runtime).replace("\\", "/")
    report["shared_hidden_corpus_id"] = hashlib.sha256(
        f"formal|{label}|{ctx.run_id}|{cid}".encode()).hexdigest()
    return report


def _interop_run(ctx, cid, perspective, label, cases, candidate_path=None):
    path = candidate_path or interop._path(ctx, cid, perspective)
    if not os.path.isfile(path):
        return {"status": "FAIL", "passed": False,
                "reason": "interoperability candidate missing"}
    out = A(ctx, "reports", f"interoperability-{label}-{cid}-{perspective}.json")
    seed = int(hashlib.sha256(
        f"interop|{label}|{ctx.run_id}|{cid}".encode()).hexdigest()[:8], 16)
    command = [sys.executable,
               os.path.join(ctx.evaluator_dir, "observatory_interoperability_arena.py"),
               "--candidate", path, "--out", out, "--seed", str(seed),
               "--cases", str(cases)]
    for axis, value in interop._expected(ctx, cid).items():
        command.extend(["--expected-" + axis.replace("_", "-"), value])
    result = subprocess.run(command, capture_output=True, text=True)
    if not os.path.exists(out):
        return {"status": "FAIL", "passed": False,
                "reason": "interoperability evaluator produced no report: "
                          + (result.stdout + result.stderr)[-1600:]}
    report = read_json(out); report["evaluator_returncode"] = result.returncode
    report["evidence_path"] = os.path.relpath(out, ctx.runtime).replace("\\", "/")
    report["candidate_path"] = os.path.relpath(path, ctx.runtime).replace("\\", "/")
    report["shared_hidden_corpus_id"] = hashlib.sha256(
        f"interop|{label}|{ctx.run_id}|{cid}".encode()).hexdigest()
    return report


def install(_ctx, handlers):
    formal._run = _formal_run
    interop._run = _interop_run
    return dict(handlers)
