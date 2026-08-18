"""Bind cross-model qualification/replication/crown to the signed history counts."""
import hashlib
import os
import sys

from . import observatory_cross_model_overlay as cross
from . import observatory_protocol
from . import observatory_utf8_process as utf8_process
from .canonical import read_json
from .handlers import A


def _history_count(label):
    key = {"qualification": "qualification_histories",
           "replication": "replication_histories",
           "crown": "crown_histories"}[label]
    return observatory_protocol.workload("cross_model", key)


def _run(ctx, cid, label):
    semantic = A(ctx, "candidate-src", f"{cid}.py")
    formal_paths = [cross.formal._path(ctx, cid, perspective)
                    for perspective, _temperature, _directive
                    in cross.formal.FORMAL_PERSPECTIVES]
    interop_paths = [cross.interop._path(ctx, cid, perspective)
                     for perspective, _temperature, _directive
                     in cross.interop.PERSPECTIVES]
    paths = [semantic, *formal_paths, *interop_paths]
    missing = [path for path in paths if not os.path.isfile(path)]
    if missing:
        return {"status": "FAIL", "passed": False,
                "reason": "cross-model source missing: " + ", ".join(missing)}
    out = A(ctx, "reports", f"cross-model-{label}-{cid}.json")
    seed = int(hashlib.sha256(
        f"cross-model|{label}|{ctx.run_id}|{cid}".encode()).hexdigest()[:8], 16)
    command = [sys.executable,
               os.path.join(ctx.evaluator_dir, "observatory_cross_model_arena_v2.py"),
               "--semantic", semantic, "--seed", str(seed),
               "--histories", str(_history_count(label)), "--out", out]
    for path in formal_paths:
        command.extend(["--formal", path])
    for path in interop_paths:
        command.extend(["--interoperability", path])
    result = utf8_process.run(command, capture_output=True)
    if not os.path.isfile(out):
        return {"status": "FAIL", "passed": False,
                "reason": "cross-model evaluator produced no report: "
                          + (result.stdout + result.stderr)[-1600:],
                "evaluator_transport_encoding": utf8_process.ENCODING}
    report = read_json(out)
    report["evaluator_returncode"] = result.returncode
    report["evaluator_transport_encoding"] = utf8_process.ENCODING
    report["evidence_path"] = os.path.relpath(out, ctx.runtime).replace("\\", "/")
    report["signed_history_count"] = _history_count(label)
    return report


def install(_ctx, handlers):
    cross._run = _run
    return dict(handlers)
