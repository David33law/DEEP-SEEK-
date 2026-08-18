"""Route all specialized candidate evaluators through output-bounded v2 entrypoints.

Every dynamic specialized receipt is source-bound to the exact candidate and carries the bounded
process witness. Durable and distributed process-death workloads are explicit owner-bound inputs;
production cannot silently fall back to evaluator defaults. Trusted parent/evaluator subprocesses use
the canonical strict UTF-8 process seat so host locale cannot alter legal/candidate text transport.
"""
import hashlib
import os
import sys

from . import observatory_crown_overlay as crown
from . import observatory_distributed_overlay as distributed
from . import observatory_formal_overlay as formal
from . import observatory_interoperability_overlay as interop
from . import observatory_protocol as protocol
from . import observatory_scale_overlay as scale
from . import observatory_utf8_process as utf8_process
from .canonical import atomic_write_json, read_json
from .handlers import A


_EVALUATOR_TAIL_LIMIT = 4000


def _sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _process_receipt(result):
    return {
        "evaluator_returncode": result.returncode,
        "evaluator_stdout_tail": (result.stdout or "")[-_EVALUATOR_TAIL_LIMIT:],
        "evaluator_stderr_tail": (result.stderr or "")[-_EVALUATOR_TAIL_LIMIT:],
        "evaluator_transport_encoding": utf8_process.ENCODING,
    }


def _finish(ctx, out, result, path):
    process = _process_receipt(result)
    if not os.path.exists(out):
        return {
            "status": "FAIL", "passed": False,
            "reason": "bounded evaluator produced no report",
            **process,
        }
    report = read_json(out)
    report.update(process)
    report["evidence_path"] = os.path.relpath(
        out, ctx.runtime).replace("\\", "/")
    report["candidate_path"] = os.path.relpath(
        path, ctx.runtime).replace("\\", "/")
    report["candidate_sha256"] = _sha256_file(path)
    atomic_write_json(out, report)
    return report


def _run(command):
    return utf8_process.run(command, capture_output=True)


def _systems(ctx, cid, label, events):
    path = crown._systems_path(ctx, cid)
    if not os.path.exists(path):
        return {"status": "FAIL", "passed": False,
                "reason": "systems candidate missing"}
    out = A(ctx, "reports", f"systems-{label}-{cid}.json")
    seed = int(hashlib.sha256(
        f"systems|{label}|{ctx.run_id}|{cid}".encode()).hexdigest()[:8], 16)
    crash_events = protocol.workload("systems", "crash_events")
    result = _run([
        sys.executable,
        os.path.join(ctx.evaluator_dir, "observatory_systems_arena_v2.py"),
        "--candidate", path, "--out", out, "--seed", str(seed),
        "--large-events", str(events),
        "--crash-events", str(crash_events)])
    report = _finish(ctx, out, result, path)
    report["owner_signed_large_events"] = int(events)
    report["owner_signed_crash_events"] = int(crash_events)
    if report.get("evidence_path"):
        atomic_write_json(out, report)
    return report


def _distributed(ctx, cid, label, events):
    path = distributed._distributed_path(ctx, cid)
    if not os.path.isfile(path):
        return {"status": "FAIL", "passed": False,
                "reason": "distributed candidate missing"}
    out = A(ctx, "reports", f"distributed-{label}-{cid}.json")
    seed = int(hashlib.sha256(
        f"distributed|{label}|{ctx.run_id}|{cid}".encode()).hexdigest()[:8], 16)
    crash_events = protocol.workload("distributed", "crash_events")
    result = _run([
        sys.executable,
        os.path.join(ctx.evaluator_dir, "observatory_distributed_arena_v2.py"),
        "--candidate", path, "--out", out,
        "--expected-replication-model", distributed._model(
            ctx, cid, "replication_distribution_model"),
        "--expected-commit-model", distributed._model(
            ctx, cid, "consistency_commit_model"),
        "--seed", str(seed), "--large-events", str(events),
        "--crash-events", str(crash_events)])
    report = _finish(ctx, out, result, path)
    report["owner_signed_large_events"] = int(events)
    report["owner_signed_crash_events"] = int(crash_events)
    if report.get("evidence_path"):
        atomic_write_json(out, report)
    return report


def _scale(ctx, cid, label, events, candidate_path=None):
    path = candidate_path or scale._path(ctx, cid)
    if not os.path.isfile(path):
        return {"status": "FAIL", "passed": False,
                "reason": "scale candidate missing"}
    out = A(ctx, "reports", f"scale-{label}-{cid}.json")
    seed = int(hashlib.sha256(
        f"scale|{label}|{ctx.run_id}|{cid}".encode()).hexdigest()[:8], 16)
    tail = max(1000, min(50000, max(1, events // 10)))
    result = _run([
        sys.executable,
        os.path.join(ctx.evaluator_dir, "observatory_scale_arena_v2.py"),
        "--candidate", path, "--out", out,
        "--expected-scaling-model", scale._model(ctx, cid),
        "--seed", str(seed), "--events", str(events),
        "--tail-events", str(tail), "--partitions", str(scale.SCALE_PARTITIONS),
        "--batch-size", str(scale.SCALE_BATCH), "--timeout", "14400"])
    return _finish(ctx, out, result, path)


def _formal(ctx, cid, perspective, label, depth, candidate_path=None):
    path = candidate_path or formal._path(ctx, cid, perspective)
    if not os.path.isfile(path):
        return {"status": "FAIL", "passed": False,
                "reason": "formal model missing"}
    out = A(ctx, "reports", f"formal-{label}-{cid}-{perspective}.json")
    corpus = f"formal|{label}|{ctx.run_id}|{cid}"
    seed = int(hashlib.sha256(corpus.encode()).hexdigest()[:8], 16)
    command = [
        sys.executable,
        os.path.join(ctx.evaluator_dir, "observatory_formal_arena_v2.py"),
        "--candidate", path, "--out", out, "--seed", str(seed),
        "--depth", str(depth), "--timeout", "14400"]
    for axis, value in formal._expected(ctx, cid).items():
        command.extend(["--expected-" + axis.replace("_", "-"), value])
    result = _run(command)
    report = _finish(ctx, out, result, path)
    report["shared_hidden_corpus_id"] = hashlib.sha256(
        corpus.encode()).hexdigest()
    if report.get("evidence_path"):
        atomic_write_json(out, report)
    return report


def _interop(ctx, cid, perspective, label, cases, candidate_path=None):
    path = candidate_path or interop._path(ctx, cid, perspective)
    if not os.path.isfile(path):
        return {"status": "FAIL", "passed": False,
                "reason": "interoperability candidate missing"}
    out = A(ctx, "reports", f"interoperability-{label}-{cid}-{perspective}.json")
    corpus = f"interop|{label}|{ctx.run_id}|{cid}"
    seed = int(hashlib.sha256(corpus.encode()).hexdigest()[:8], 16)
    command = [
        sys.executable,
        os.path.join(ctx.evaluator_dir, "observatory_interoperability_arena_v2.py"),
        "--candidate", path, "--out", out, "--seed", str(seed),
        "--cases", str(cases)]
    for axis, value in interop._expected(ctx, cid).items():
        command.extend(["--expected-" + axis.replace("_", "-"), value])
    result = _run(command)
    report = _finish(ctx, out, result, path)
    report["shared_hidden_corpus_id"] = hashlib.sha256(
        corpus.encode()).hexdigest()
    if report.get("evidence_path"):
        atomic_write_json(out, report)
    return report


def install(_ctx, handlers):
    crown._run_systems = _systems
    distributed._run = _distributed
    scale._run = _scale
    formal._run = _formal
    interop._run = _interop
    return dict(handlers)
