#!/usr/bin/env python3
"""National-scale deterministic workload arena for Observatory architectures.

Runs ``scale_candidate.py`` in network-disabled, read-only-root containers with one writable scale
store. It streams a large deterministic legal-change history in bounded batches, measures throughput
and batch latency, then tests restart, duplicate/reordered idempotence, incremental tail, checkpoint
recovery, partition balance, independent rebuild and one-root publication.
"""
import argparse
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time

from candidate_host import container_runtime

IMAGE = "python:3.11-slim"
REQUIRED_CHANNELS = {"human", "api", "linked_data", "eli", "public_sector", "ai"}
PARTITIONED_MODELS = {
    "source_sharding", "namespace_sharding", "time_partition",
    "distributed_log_partitions", "dataflow_partition", "proof_dag_partition",
    "federated_domains", "hybrid",
}

BOOTSTRAP = r'''
import json, sys, time
first = json.loads(sys.stdin.readline())
src = first["candidate_source"]
partitions = int(first["partition_count"])
ns = {"__name__": "__candidate__"}
try:
    exec(compile(src, "<scale-candidate>", "exec"), ns, ns)
    opener = ns.get("open_scale")
    if not callable(opener): raise RuntimeError("missing open_scale(root_dir, partition_count)")
    scale = opener("/scale", partitions)
except BaseException as exc:
    print(json.dumps({"ok": False, "phase": "open", "error": type(exc).__name__ + ": " + str(exc)}), flush=True)
    raise SystemExit(0)
for line in sys.stdin:
    if not line.strip(): continue
    req = json.loads(line); op = req.get("op")
    if op == "quit": break
    started = time.monotonic()
    try:
        if op == "ingest_batch": result = scale.ingest_batch(req.get("events", []))
        elif op == "state_root": result = scale.state_root()
        elif op == "partition_roots": result = scale.partition_roots()
        elif op == "integrity_check": result = scale.integrity_check()
        elif op == "publish_probe": result = scale.publish_probe()
        elif op == "checkpoint": result = scale.checkpoint()
        elif op == "recover": result = scale.recover()
        elif op == "scale_manifest": result = scale.scale_manifest()
        elif op == "close": result = scale.close()
        else: raise RuntimeError("unknown op: " + str(op))
        print(json.dumps({"ok": True, "op": op, "result": result,
                          "elapsed_seconds": time.monotonic() - started}, ensure_ascii=False), flush=True)
    except BaseException as exc:
        print(json.dumps({"ok": False, "op": op, "phase": "operation",
                          "error": type(exc).__name__ + ": " + str(exc),
                          "elapsed_seconds": time.monotonic() - started}, ensure_ascii=False), flush=True)
'''


def _event(index, total, seed, prefix):
    kinds = ("LEGISLATION", "AMENDMENT", "CORRECTION", "SUSPENSION", "REVIVAL", "REPEAL")
    kind = kinds[index % len(kinds)]
    year, month, day = 1980 + (index % 55), 1 + (index % 12), 1 + (index % 27)
    object_count = max(500, total // 25)
    cid = f"{prefix}-LAW-{index % object_count:08d}:ART-{1 + (index % 120)}"
    payload = hashlib.sha256(f"{seed}|{prefix}|{index}".encode()).hexdigest()[:24]
    return {
        "source_id": f"{prefix}-{seed:08x}-{index:012d}",
        "kind": kind,
        "canonical_id": cid,
        "target_id": cid,
        "publication_time": f"{year:04d}-{month:02d}-{day:02d}",
        "knowledge_time": f"{year:04d}-{month:02d}-{day:02d}",
        "effective_from": f"{year:04d}-{month:02d}-{day:02d}",
        "text": f"payload-{payload}" if kind in ("LEGISLATION", "AMENDMENT", "CORRECTION") else None,
    }


def _batches(total, seed, prefix, batch_size, reverse=False):
    indices = range(total - 1, -1, -1) if reverse else range(total)
    batch = []
    for index in indices:
        batch.append(_event(index, total, seed, prefix))
        if len(batch) >= batch_size:
            yield batch; batch = []
    if batch:
        yield batch


def _argv(runtime, state_dir):
    return [
        runtime, "run", "--rm", "-i", "--network=none", "--read-only",
        "--tmpfs", "/tmp:size=256m", "--memory=3g", "--pids-limit=128",
        "--cap-drop=ALL", "--security-opt", "no-new-privileges",
        "--mount", f"type=bind,source={os.path.abspath(state_dir)},target=/scale",
        "-w", "/tmp", IMAGE, "python3", "-I", "-S", "-B", "-c", BOOTSTRAP,
    ]


def _write_input(path, source, partitions, commands):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps({"candidate_source": source,
                            "partition_count": partitions}, ensure_ascii=False) + "\n")
        for command in commands:
            f.write(json.dumps(command, ensure_ascii=False) + "\n")
        f.write(json.dumps({"op": "quit"}) + "\n")


def _run_commands(runtime, source, state_dir, partitions, commands,
                  timeout=3600, allow_errors=False):
    os.makedirs(state_dir, exist_ok=True)
    fd, input_path = tempfile.mkstemp(prefix="obs-scale-input-", suffix=".jsonl")
    os.close(fd)
    try:
        _write_input(input_path, source, partitions, commands)
        with open(input_path, "r", encoding="utf-8") as stdin:
            process = subprocess.run(_argv(runtime, state_dir), stdin=stdin,
                                     capture_output=True, text=True, timeout=timeout)
        if process.returncode != 0:
            raise RuntimeError(
                f"scale container exited {process.returncode}: {process.stderr[-1000:]}")
        replies = []
        for line in process.stdout.splitlines():
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if "ok" in obj:
                replies.append(obj)
        if not replies:
            raise RuntimeError("scale candidate produced no protocol result: "
                               + process.stderr[-1000:])
        if not allow_errors:
            bad = [x for x in replies if not x.get("ok")]
            if bad:
                raise RuntimeError("scale candidate error: "
                                   + json.dumps(bad[0], ensure_ascii=False)[:1200])
        return replies
    finally:
        try:
            os.unlink(input_path)
        except OSError:
            pass


def _result(replies, op, occurrence=-1):
    rows = [x for x in replies if x.get("op") == op]
    if not rows:
        raise RuntimeError(f"scale candidate returned no {op} result")
    row = rows[occurrence]
    if not row.get("ok"):
        raise RuntimeError(f"scale candidate {op} failed: {row.get('error')}")
    return row.get("result")


def _latencies(replies, op="ingest_batch"):
    return [float(x.get("elapsed_seconds", 0.0)) for x in replies
            if x.get("op") == op and x.get("ok")]


def _p95(values):
    if not values:
        return math.inf
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1,
                       max(0, math.ceil(0.95 * len(ordered)) - 1))]


def _root(value):
    if not isinstance(value, str) or not value:
        raise RuntimeError("state_root must be a non-empty string")
    return value


def _integrity(value):
    if not isinstance(value, dict) or value.get("ok") is not True:
        raise RuntimeError("integrity_check did not return ok=true")
    return value


def _publication_ok(value, root):
    if not isinstance(value, dict) or value.get("canonical_root") != root:
        return False
    channels = value.get("channels")
    return isinstance(channels, dict) \
        and REQUIRED_CHANNELS.issubset(set(channels)) \
        and all(channels[x] == root for x in REQUIRED_CHANNELS)


def _manifest(runtime, source, state_dir, partitions, expected_model):
    replies = _run_commands(runtime, source, state_dir, partitions,
                            [{"op": "scale_manifest"}, {"op": "close"}], timeout=300)
    manifest = _result(replies, "scale_manifest")
    if not isinstance(manifest, dict):
        raise RuntimeError("scale_manifest must return an object")
    if manifest.get("scaling_partition_model") != expected_model:
        raise RuntimeError(
            f"scaling genome mismatch: {manifest.get('scaling_partition_model')!r} != {expected_model!r}")
    actual = int(manifest.get("partition_count", 0))
    if expected_model == "single_node_scale_up":
        if actual != 1:
            raise RuntimeError("single_node_scale_up must report exactly one active partition")
    elif actual != partitions:
        raise RuntimeError(f"scale candidate reports {actual} partitions, expected {partitions}")
    authority = manifest.get("authority_files")
    if not isinstance(authority, list) or not authority:
        raise RuntimeError("scale_manifest requires non-empty authority_files")
    for rel in authority:
        parts = str(rel).replace("\\", "/").split("/")
        if os.path.isabs(str(rel)) or ".." in parts:
            raise RuntimeError("authority_files must be relative paths")
    checkpoints = manifest.get("checkpoint_files")
    if not isinstance(checkpoints, list) or not checkpoints:
        raise RuntimeError("scale_manifest requires checkpoint_files")
    if not isinstance(manifest.get("routing_rule"), str) or not manifest["routing_rule"].strip():
        raise RuntimeError("scale_manifest requires routing_rule")
    if not isinstance(manifest.get("complexity_claim"), (str, dict)):
        raise RuntimeError("scale_manifest requires complexity_claim")
    if not REQUIRED_CHANNELS.issubset(set(manifest.get("publication_channels") or [])):
        raise RuntimeError("scale_manifest omits required publication channels")
    return manifest


def _storage_bytes(root, files):
    total = 0
    for rel in files:
        path = os.path.abspath(os.path.join(root, str(rel)))
        if not path.startswith(os.path.abspath(root) + os.sep) or not os.path.isfile(path):
            raise RuntimeError(f"declared authority file missing: {rel}")
        total += os.path.getsize(path)
    return total


def _flip(path):
    with open(path, "r+b") as f:
        data = f.read(1)
        if not data:
            raise RuntimeError("cannot corrupt empty authority file")
        f.seek(0); f.write(bytes([data[0] ^ 0x7D])); f.flush(); os.fsync(f.fileno())


def _corruption_recovery(runtime, source, stable, partitions, manifest, work):
    shutil.copytree(stable, work)
    candidates = [x for x in manifest["authority_files"]
                  if "partition" in str(x).lower()]
    rel = str((candidates or manifest["authority_files"])[0])
    victim = os.path.abspath(os.path.join(work, rel))
    _flip(victim)
    first = _run_commands(runtime, source, work, partitions,
                          [{"op": "integrity_check"}, {"op": "recover"},
                           {"op": "integrity_check"}, {"op": "state_root"},
                           {"op": "close"}], timeout=600, allow_errors=True)
    integrities = [x for x in first if x.get("op") == "integrity_check"]
    recover = [x for x in first if x.get("op") == "recover"]
    roots = [x for x in first if x.get("op") == "state_root"]
    passed = bool(recover and recover[-1].get("ok")
                  and isinstance(recover[-1].get("result"), dict)
                  and recover[-1]["result"].get("ok") is True
                  and len(integrities) >= 2 and integrities[-1].get("ok")
                  and isinstance(integrities[-1].get("result"), dict)
                  and integrities[-1]["result"].get("ok") is True
                  and roots and roots[-1].get("ok"))
    return {"passed": passed, "victim": rel,
            "first_integrity_ok": bool(integrities and integrities[0].get("ok")
                                       and isinstance(integrities[0].get("result"), dict)
                                       and integrities[0]["result"].get("ok") is True)}


def _ingest_commands(total, seed, prefix, batch_size, reverse=False,
                     checkpoint=False):
    commands = [{"op": "ingest_batch", "events": batch}
                for batch in _batches(total, seed, prefix, batch_size, reverse)]
    commands.extend([{"op": "state_root"}, {"op": "integrity_check"},
                     {"op": "partition_roots"}, {"op": "publish_probe"}])
    if checkpoint:
        commands.append({"op": "checkpoint"})
    commands.append({"op": "close"})
    return commands


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--expected-scaling-model", required=True)
    ap.add_argument("--seed", type=int, default=9402026)
    ap.add_argument("--events", type=int, default=100000)
    ap.add_argument("--tail-events", type=int, default=10000)
    ap.add_argument("--partitions", type=int, default=16)
    ap.add_argument("--batch-size", type=int, default=5000)
    ap.add_argument("--timeout", type=int, default=7200)
    args = ap.parse_args(argv)

    runtime = container_runtime()
    if not runtime:
        raise RuntimeError("scale arena requires docker/podman")
    source = open(args.candidate, encoding="utf-8").read()
    partitions = 1 if args.expected_scaling_model == "single_node_scale_up" \
        else max(2, args.partitions)
    temp = tempfile.mkdtemp(prefix="obs-scale-")
    report = {"status": "FAIL", "passed": False, "backend": "container",
              "runtime": runtime, "image": IMAGE,
              "candidate": os.path.abspath(args.candidate),
              "expected_scaling_model": args.expected_scaling_model,
              "events": args.events, "tail_events": args.tail_events,
              "partitions_requested": partitions, "batch_size": args.batch_size}
    try:
        stable = os.path.join(temp, "stable")
        manifest = _manifest(runtime, source, stable, partitions,
                             args.expected_scaling_model)
        started = time.monotonic()
        main_replies = _run_commands(
            runtime, source, stable, partitions,
            _ingest_commands(args.events, args.seed, "SCALE", args.batch_size,
                             checkpoint=True), timeout=args.timeout)
        elapsed = time.monotonic() - started
        batch_results = [_result([row], "ingest_batch") for row in main_replies
                         if row.get("op") == "ingest_batch" and row.get("ok")]
        accepted = sum(int(x.get("accepted", 0)) for x in batch_results
                       if isinstance(x, dict))
        unresolved = sum(int(x.get("unresolved", 0)) for x in batch_results
                         if isinstance(x, dict))
        root1 = _root(_result(main_replies, "state_root"))
        integrity1 = _integrity(_result(main_replies, "integrity_check"))
        partition_roots1 = _result(main_replies, "partition_roots")
        publication1 = _result(main_replies, "publish_probe")
        no_silent_drop = accepted == args.events and unresolved == 0 \
            and int(integrity1.get("event_count", -1)) == args.events
        publication_consistency = _publication_ok(publication1, root1)

        restart = _run_commands(runtime, source, stable, partitions,
                                [{"op": "state_root"}, {"op": "integrity_check"},
                                 {"op": "publish_probe"}, {"op": "close"}], timeout=600)
        restart_root = _root(_result(restart, "state_root"))
        restart_identity = restart_root == root1 \
            and _integrity(_result(restart, "integrity_check")).get("canonical_root") == root1

        duplicate_count = min(args.events, max(1000, args.batch_size * 2))
        duplicate = _run_commands(
            runtime, source, stable, partitions,
            _ingest_commands(duplicate_count, args.seed, "SCALE", args.batch_size,
                             reverse=True), timeout=1200)
        duplicate_root = _root(_result(duplicate, "state_root"))
        duplicate_idempotence = duplicate_root == root1

        tail = _run_commands(
            runtime, source, stable, partitions,
            _ingest_commands(args.tail_events, args.seed + 1, "TAIL", args.batch_size,
                             checkpoint=True), timeout=1800)
        tail_results = [_result([row], "ingest_batch") for row in tail
                        if row.get("op") == "ingest_batch" and row.get("ok")]
        tail_accepted = sum(int(x.get("accepted", 0)) for x in tail_results
                            if isinstance(x, dict))
        root2 = _root(_result(tail, "state_root"))
        integrity2 = _integrity(_result(tail, "integrity_check"))
        incremental_tail = root2 != root1 and tail_accepted == args.tail_events \
            and int(integrity2.get("event_count", -1)) == args.events + args.tail_events
        tail_publication = _publication_ok(_result(tail, "publish_probe"), root2)

        counts = integrity2.get("partition_counts") or {}
        nonempty = [int(x) for x in counts.values() if int(x) > 0]
        partition_count_ok = isinstance(partition_roots1, dict) \
            and len(partition_roots1) == int(manifest["partition_count"])
        if args.expected_scaling_model in PARTITIONED_MODELS:
            balance_ratio = (max(nonempty) / min(nonempty)) if nonempty else math.inf
            partition_balance = len(nonempty) >= min(4, int(manifest["partition_count"])) \
                and balance_ratio <= 4.0
        else:
            balance_ratio = 1.0 if nonempty else math.inf
            partition_balance = len(nonempty) == 1

        storage_bytes = _storage_bytes(stable, manifest["authority_files"])
        total_events = args.events + args.tail_events
        bytes_per_event = storage_bytes / max(total_events, 1)

        corruption = _corruption_recovery(
            runtime, source, stable, partitions, manifest,
            os.path.join(temp, "corrupt"))

        rebuilt = os.path.join(temp, "rebuilt")
        commands = _ingest_commands(args.events, args.seed, "SCALE", args.batch_size)
        commands = commands[:-5] + [
            {"op": "ingest_batch", "events": batch}
            for batch in _batches(args.tail_events, args.seed + 1, "TAIL", args.batch_size)
        ] + [{"op": "state_root"}, {"op": "integrity_check"},
             {"op": "partition_roots"}, {"op": "publish_probe"}, {"op": "close"}]
        rebuild = _run_commands(runtime, source, rebuilt, partitions,
                                commands, timeout=args.timeout)
        rebuild_root = _root(_result(rebuild, "state_root"))
        deterministic_rebuild = rebuild_root == root2 \
            and _integrity(_result(rebuild, "integrity_check")).get("event_count") == total_events
        rebuild_publication = _publication_ok(_result(rebuild, "publish_probe"), rebuild_root)

        batch_latencies = _latencies(main_replies) + _latencies(tail)
        p95_batch = _p95(batch_latencies)
        throughput = total_events / max(elapsed, 1e-9)
        tests = {
            "manifest_matches_controlled_genome": True,
            "no_silent_unique_event_drop": no_silent_drop,
            "restart_identity": restart_identity,
            "duplicate_reordered_idempotence": duplicate_idempotence,
            "incremental_tail_changes_root": incremental_tail,
            "partition_root_count": partition_count_ok,
            "partition_balance": partition_balance,
            "publication_consistency": publication_consistency and tail_publication,
            "checkpoint_corruption_recovery": corruption,
            "deterministic_independent_rebuild": deterministic_rebuild,
            "rebuild_publication_consistency": rebuild_publication,
        }
        simple = [x for x in tests.values() if isinstance(x, bool)]
        passed = all(simple) and corruption.get("passed") is True
        report.update({
            "status": "PASS" if passed else "FAIL", "passed": passed,
            "manifest": manifest, "tests": tests,
            "canonical_root": root2,
            "total_unique_events": total_events,
            "elapsed_seconds_main_and_tail": elapsed,
            "events_per_second": throughput,
            "batch_latency_p95_seconds": p95_batch,
            "batch_latency_samples": len(batch_latencies),
            "authority_storage_bytes": storage_bytes,
            "bytes_per_event": bytes_per_event,
            "partition_nonempty": len(nonempty),
            "partition_balance_ratio": balance_ratio,
            "proof_boundary": (
                "bounded local container workload; exact event count and measurements are evidence, "
                "not a claim about untested national hardware or geographic deployment"),
        })
    finally:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=1, sort_keys=True)
        shutil.rmtree(temp, ignore_errors=True)
    print(json.dumps(report, ensure_ascii=False, indent=1))
    return 0 if report.get("status") == "PASS" else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(json.dumps({"status": "FAIL", "passed": False,
                          "reason": str(exc)}, ensure_ascii=False, indent=1))
        sys.exit(1)
