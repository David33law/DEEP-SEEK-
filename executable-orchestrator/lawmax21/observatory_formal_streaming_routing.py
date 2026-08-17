"""Route formal campaigns through the memory-bounded v3 evaluator."""
import hashlib
import os
import subprocess
import sys

from . import observatory_formal_overlay as formal
from .canonical import atomic_write_json, read_json
from .handlers import A


_EVALUATOR_TAIL_LIMIT = 4000


def _sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run(ctx, cid, perspective, label, depth, candidate_path=None):
    path = candidate_path or formal._path(ctx, cid, perspective)
    if not os.path.isfile(path):
        return {"status": "FAIL", "passed": False,
                "reason": "formal model missing"}
    out = A(ctx, "reports", f"formal-{label}-{cid}-{perspective}.json")
    corpus = f"formal|{label}|{ctx.run_id}|{cid}"
    seed = int(hashlib.sha256(corpus.encode()).hexdigest()[:8], 16)
    command = [
        sys.executable,
        os.path.join(ctx.evaluator_dir, "observatory_formal_arena_v3.py"),
        "--candidate", path, "--out", out, "--seed", str(seed),
        "--depth", str(depth), "--timeout", "14400"]
    for axis, value in formal._expected(ctx, cid).items():
        command.extend(["--expected-" + axis.replace("_", "-"), value])
    result = subprocess.run(command, capture_output=True, text=True)
    process = {
        "evaluator_returncode": result.returncode,
        "evaluator_stdout_tail": (result.stdout or "")[-_EVALUATOR_TAIL_LIMIT:],
        "evaluator_stderr_tail": (result.stderr or "")[-_EVALUATOR_TAIL_LIMIT:],
    }
    if not os.path.exists(out):
        return {
            "status": "FAIL", "passed": False,
            "reason": "streaming formal evaluator produced no report",
            **process,
        }
    report = read_json(out)
    report.update(process)
    report["evidence_path"] = os.path.relpath(
        out, ctx.runtime).replace("\\", "/")
    report["candidate_path"] = os.path.relpath(
        path, ctx.runtime).replace("\\", "/")
    report["candidate_sha256"] = _sha256_file(path)
    report["shared_hidden_corpus_id"] = hashlib.sha256(
        corpus.encode()).hexdigest()
    atomic_write_json(out, report)
    return report


def install(_ctx, handlers):
    formal._run = _run
    return dict(handlers)
