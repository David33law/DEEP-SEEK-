"""Route formal campaigns through the memory-bounded v3 evaluator."""
import hashlib
import os
import subprocess
import sys

from . import observatory_formal_overlay as formal
from .canonical import read_json
from .handlers import A


def _run(ctx, cid, perspective, label, depth, candidate_path=None):
    path = candidate_path or formal._path(ctx, cid, perspective)
    if not os.path.isfile(path):
        return {"status": "FAIL", "passed": False,
                "reason": "formal model missing"}
    out = A(ctx, "reports", f"formal-{label}-{cid}-{perspective}.json")
    corpus = f"formal|{label}|{ctx.run_id}|{cid}"
    seed = int(hashlib.sha256(corpus.encode()).hexdigest()[:8], 16)
    command = [sys.executable,
               os.path.join(ctx.evaluator_dir, "observatory_formal_arena_v3.py"),
               "--candidate", path, "--out", out, "--seed", str(seed),
               "--depth", str(depth), "--timeout", "14400"]
    for axis, value in formal._expected(ctx, cid).items():
        command.extend(["--expected-" + axis.replace("_", "-"), value])
    result = subprocess.run(command, capture_output=True, text=True)
    if not os.path.exists(out):
        return {"status": "FAIL", "passed": False,
                "reason": "streaming formal evaluator produced no report: "
                          + (result.stdout + result.stderr)[-1600:]}
    report = read_json(out); report["evaluator_returncode"] = result.returncode
    report["evidence_path"] = os.path.relpath(out, ctx.runtime).replace("\\", "/")
    report["candidate_path"] = os.path.relpath(path, ctx.runtime).replace("\\", "/")
    report["shared_hidden_corpus_id"] = hashlib.sha256(corpus.encode()).hexdigest()
    return report


def install(_ctx, handlers):
    formal._run = _run
    return dict(handlers)
