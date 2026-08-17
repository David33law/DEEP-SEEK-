#!/usr/bin/env python3
"""Distributed fault arena for a National Legal Observatory architecture.

This evaluator is separate from both the in-memory legal-semantic host and the single-state-directory
durable arena. It executes ``distributed_candidate.py`` in network-disabled, read-only-root
containers with one writable cluster directory and injects process restart, duplicate/reordered
delivery, majority/minority partitions, below-quorum operation, node crash/restart, process death,
node-authority corruption, optional Byzantine equivocation, heal/catch-up and independent rebuild.

The candidate's declared replication and commit classes must exactly match the controlled architecture
genome supplied by the trusted parent. A successful local campaign proves only the explicit bounded
fault model reported here; it never implies an untested internet-scale or third-party deployment.
"""
import argparse
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
import time

from candidate_host import container_runtime

IMAGE = "python:3.11-slim"
NODE_IDS = ["n1", "n2", "n3", "n4", "n5"]
REQUIRED_CHANNELS = {"human", "api", "linked_data", "eli", "public_sector", "ai"}
BFT_MODELS = {"bft_consensus"}
BFT_COMMITS = {"quorum_certificate"}

BOOTSTRAP = r'''
import json, sys
first = json.loads(sys.stdin.readline())
src = first["candidate_source"]
node_ids = first["node_ids"]
ns = {"__name__": "__candidate__"}
try:
    exec(compile(src, "<distributed-candidate>", "exec"), ns, ns)
    opener = ns.get("open_cluster")
    if not callable(opener):
        raise RuntimeError("missing open_cluster(root_dir, node_ids)")
    cluster = opener("/cluster", node_ids)
except BaseException as exc:
    print(json.dumps({"ok": False, "phase": "open", "error": type(exc).__name__ + ": " + str(exc)}), flush=True)
    raise SystemExit(0)
for line in sys.stdin:
    if not line.strip():
        continue
    req = json.loads(line); op = req.get("op")
    if op == "quit": break
    try:
        if op == "submit": result = cluster.submit(req.get("node_id"), req.get("event"))
        elif op == "ingest_batch": result = cluster.ingest_batch(req.get("node_id"), req.get("events", []))
        elif op == "partition": result = cluster.partition(req.get("groups", []))
        elif op == "heal": result = cluster.heal()
        elif op == "roots": result = cluster.roots()
        elif op == "integrity": result = cluster.integrity()
        elif op == "crash": result = cluster.crash(req.get("node_id"))
        elif op == "restart": result = cluster.restart(req.get("node_id"))
        elif op == "recover": result = cluster.recover(req.get("node_id"))
        elif op == "publication_roots": result = cluster.publication_roots()
        elif op == "cluster_manifest": result = cluster.cluster_manifest()
        elif op == "inject_fault":
            fn = getattr(cluster, "inject_fault", None)
            if not callable(fn): raise RuntimeError("missing inject_fault(node_id, fault)")
            result = fn(req.get("node_id"), req.get("fault"))
        elif op == "close": result = cluster.close()
        else: raise RuntimeError("unknown op: " + str(op))
        print(json.dumps({"ok": True, "op": op, "result": result}, ensure_ascii=False), flush=True)
    except BaseException as exc:
        print(json.dumps({"ok": False, "op": op, "phase": "operation", "error": type(exc).__name__ + ": " + str(exc)}, ensure_ascii=False), flush=True)
'''


def _events(n, seed, prefix="DIST"):
    rng = random.Random(seed)
    kinds = ["LEGISLATION", "AMENDMENT", "CORRECTION", "SUSPENSION", "REVIVAL", "REPEAL"]
    out = []
    for i in range(n):
        kind = kinds[i % len(kinds)]
        year, month, day = 2020 + (i % 12), 1 + (i % 12), 1 + (i % 27)
        cid = f"{prefix}-LAW-{i % max(40, n // 20):06d}:ART-{1 + (i % 50)}"
        out.append({
            "source_id": f"{prefix}-{seed:08x}-{i:09d}",
            "kind": kind,
            "canonical_id": cid,
            "target_id": cid,
            "publication_time": f"{year:04d}-{month:02d}-{day:02d}",
            "knowledge_time": f"{year:04d}-{month:02d}-{day:02d}",
            "effective_from": f"{year:04d}-{month:02d}-{day:02d}",
            "text": (f"payload-{prefix}-{i}-{rng.randrange(10**9)}"
                     if kind in ("LEGISLATION", "AMENDMENT", "CORRECTION") else None),
        })
    return out


def _argv(runtime, cluster_dir):
    return [
        runtime, "run", "--rm", "-i", "--network=none", "--read-only",
        "--tmpfs", "/tmp:size=128m", "--memory=2g", "--pids-limit=128",
        "--cap-drop=ALL", "--security-opt", "no-new-privileges",
        "--mount", f"type=bind,source={os.path.abspath(cluster_dir)},target=/cluster",
        "-w", "/tmp", IMAGE, "python3", "-I", "-S", "-B", "-c", BOOTSTRAP,
    ]


def _body(source, commands):
    lines = [json.dumps({"candidate_source": source, "node_ids": NODE_IDS}, ensure_ascii=False)]
    lines.extend(json.dumps(x, ensure_ascii=False) for x in commands)
    lines.append(json.dumps({"op": "quit"}))
    return "\n".join(lines) + "\n"


def _session(runtime, source, cluster_dir, commands, timeout=240, allow_errors=False):
    os.makedirs(cluster_dir, exist_ok=True)
    p = subprocess.run(_argv(runtime, cluster_dir), input=_body(source, commands),
                       capture_output=True, text=True, timeout=timeout)
    if p.returncode != 0:
        raise RuntimeError(f"distributed container exited {p.returncode}: {p.stderr[-800:]}")
    replies = []
    for line in p.stdout.splitlines():
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if "ok" in obj:
            replies.append(obj)
    if not replies:
        raise RuntimeError("distributed candidate produced no protocol result: " + p.stderr[-800:])
    if not allow_errors:
        bad = [x for x in replies if not x.get("ok")]
        if bad:
            raise RuntimeError("distributed candidate error: "
                               + json.dumps(bad[0], ensure_ascii=False)[:1000])
    return replies


def _result(replies, op, occurrence=-1):
    rows = [x for x in replies if x.get("op") == op]
    if not rows:
        raise RuntimeError(f"distributed candidate returned no {op} result")
    row = rows[occurrence]
    if not row.get("ok"):
        raise RuntimeError(f"distributed candidate {op} failed: {row.get('error')}")
    return row.get("result")


def _accepted(result):
    return isinstance(result, dict) and result.get("accepted") is True


def _canonical_root(integrity):
    if not isinstance(integrity, dict) or integrity.get("ok") is not True:
        raise RuntimeError("cluster integrity did not return ok=true")
    root = integrity.get("canonical_root")
    if not isinstance(root, str) or not root:
        raise RuntimeError("cluster integrity lacks non-empty canonical_root")
    return root


def _roots_converged(roots, canonical, allow_fault_markers=False):
    if not isinstance(roots, dict) or set(roots) != set(NODE_IDS):
        return False
    allowed = {canonical}
    if allow_fault_markers:
        allowed.update({"CRASHED", "CORRUPT", "FAULTY", "EXCLUDED"})
    return all(value in allowed for value in roots.values()) \
        and any(value == canonical for value in roots.values())


def _publication_ok(publication, canonical):
    if not isinstance(publication, dict) or publication.get("canonical_root") != canonical:
        return False
    channels = publication.get("channels")
    if isinstance(channels, dict):
        return REQUIRED_CHANNELS.issubset(set(channels)) \
            and all(channels[x] == canonical for x in REQUIRED_CHANNELS)
    return False


def _manifest(runtime, source, cluster_dir, expected_replication, expected_commit):
    rep = _session(runtime, source, cluster_dir,
                   [{"op": "cluster_manifest"}, {"op": "close"}])
    manifest = _result(rep, "cluster_manifest")
    if not isinstance(manifest, dict):
        raise RuntimeError("cluster_manifest must return an object")
    if manifest.get("replication_model") != expected_replication:
        raise RuntimeError(
            f"replication genome mismatch: {manifest.get('replication_model')!r} != {expected_replication!r}")
    if manifest.get("commit_model") != expected_commit:
        raise RuntimeError(
            f"commit genome mismatch: {manifest.get('commit_model')!r} != {expected_commit!r}")
    node_files = manifest.get("node_authority_files")
    if not isinstance(node_files, dict) or set(node_files) != set(NODE_IDS):
        raise RuntimeError("cluster_manifest requires node_authority_files for all nodes")
    for node_id, files in node_files.items():
        if not isinstance(files, list) or not files:
            raise RuntimeError(f"node {node_id} has no declared authority files")
        for rel in files:
            parts = str(rel).replace("\\", "/").split("/")
            if os.path.isabs(str(rel)) or ".." in parts:
                raise RuntimeError("node authority files must be relative cluster paths")
    assumptions = manifest.get("fault_assumptions")
    if not isinstance(assumptions, dict) or not assumptions:
        raise RuntimeError("cluster_manifest requires explicit fault_assumptions")
    if not isinstance(manifest.get("canonical_root_rule"), str) \
            or not manifest["canonical_root_rule"].strip():
        raise RuntimeError("cluster_manifest requires canonical_root_rule")
    channels = set(manifest.get("publication_channels") or [])
    if not REQUIRED_CHANNELS.issubset(channels):
        raise RuntimeError("cluster_manifest omits required publication channels")
    policy = manifest.get("partition_write_policy")
    if policy not in {"reject_without_quorum", "pending_until_safe", "deterministic_merge"}:
        raise RuntimeError("cluster_manifest requires a supported partition_write_policy")
    return manifest


def _crash_process(runtime, source, cluster_dir, events, delay=0.015):
    p = subprocess.Popen(_argv(runtime, cluster_dir), stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        p.stdin.write(_body(source, [{"op": "ingest_batch", "node_id": "n1",
                                     "events": events}]))
        p.stdin.flush()
    except (BrokenPipeError, OSError):
        pass
    time.sleep(delay)
    observed = p.poll() is None
    if observed:
        try:
            p.kill()
        except OSError:
            pass
    try:
        p.communicate(timeout=15)
    except subprocess.TimeoutExpired:
        p.kill(); p.communicate()
    return observed


def _flip_first_byte(path):
    with open(path, "r+b") as f:
        byte = f.read(1)
        if not byte:
            raise RuntimeError(f"cannot corrupt empty authority file {path}")
        f.seek(0); f.write(bytes([byte[0] ^ 0x5A])); f.flush(); os.fsync(f.fileno())


def _corruption_trial(runtime, source, stable, manifest, work):
    shutil.copytree(stable, work)
    files = manifest["node_authority_files"]["n5"]
    rel = str(files[0])
    victim = os.path.abspath(os.path.join(work, rel))
    if not victim.startswith(os.path.abspath(work) + os.sep) or not os.path.isfile(victim):
        raise RuntimeError(f"declared node authority file does not exist: {rel}")
    _flip_first_byte(victim)
    first = _session(runtime, source, work,
                     [{"op": "integrity"}, {"op": "roots"}, {"op": "close"}],
                     allow_errors=True)
    integ_rows = [x for x in first if x.get("op") == "integrity"]
    root_rows = [x for x in first if x.get("op") == "roots"]
    auto = False
    if integ_rows and integ_rows[-1].get("ok") and root_rows and root_rows[-1].get("ok"):
        integ = integ_rows[-1].get("result")
        roots = root_rows[-1].get("result")
        if isinstance(integ, dict) and integ.get("ok") is True:
            canonical = integ.get("canonical_root")
            auto = _roots_converged(roots, canonical)
    if auto:
        return {"passed": True, "mode": "automatic", "victim": rel,
                "detected_or_recovered": True}

    second = _session(runtime, source, work,
                      [{"op": "recover", "node_id": "n5"},
                       {"op": "heal"}, {"op": "integrity"},
                       {"op": "roots"}, {"op": "close"}], allow_errors=True)
    recover_rows = [x for x in second if x.get("op") == "recover"]
    integ_rows = [x for x in second if x.get("op") == "integrity"]
    root_rows = [x for x in second if x.get("op") == "roots"]
    recovered = False
    if recover_rows and recover_rows[-1].get("ok") and integ_rows and integ_rows[-1].get("ok") \
            and root_rows and root_rows[-1].get("ok"):
        integ = integ_rows[-1].get("result")
        roots = root_rows[-1].get("result")
        if isinstance(integ, dict) and integ.get("ok") is True:
            recovered = _roots_converged(roots, integ.get("canonical_root"))
    return {"passed": recovered, "mode": "explicit", "victim": rel,
            "detected_or_recovered": recovered}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--expected-replication-model", required=True)
    ap.add_argument("--expected-commit-model", required=True)
    ap.add_argument("--seed", type=int, default=9102026)
    ap.add_argument("--large-events", type=int, default=20000)
    args = ap.parse_args(argv)

    runtime = container_runtime()
    if not runtime:
        raise RuntimeError("distributed arena requires docker/podman")
    source = open(args.candidate, encoding="utf-8").read()
    temp = tempfile.mkdtemp(prefix="obs-distributed-")
    report = {
        "status": "FAIL", "passed": False, "backend": "container",
        "runtime": runtime, "image": IMAGE, "candidate": os.path.abspath(args.candidate),
        "expected_replication_model": args.expected_replication_model,
        "expected_commit_model": args.expected_commit_model,
        "node_ids": list(NODE_IDS),
    }
    try:
        stable = os.path.join(temp, "stable")
        manifest = _manifest(runtime, source, stable,
                             args.expected_replication_model, args.expected_commit_model)
        baseline = _events(1000, args.seed)
        start = time.monotonic()
        first = _session(runtime, source, stable,
                         [{"op": "ingest_batch", "node_id": "n1", "events": baseline},
                          {"op": "integrity"}, {"op": "roots"},
                          {"op": "publication_roots"}, {"op": "close"}], timeout=360)
        batch_result = _result(first, "ingest_batch")
        integrity = _result(first, "integrity")
        canonical = _canonical_root(integrity)
        roots = _result(first, "roots")
        publication = _result(first, "publication_roots")
        baseline_accepted = isinstance(batch_result, dict) \
            and int(batch_result.get("accepted", -1)) == len(baseline)
        healthy_convergence = _roots_converged(roots, canonical)
        publication_consistency = _publication_ok(publication, canonical)

        restart = _session(runtime, source, stable,
                           [{"op": "integrity"}, {"op": "roots"}, {"op": "close"}])
        restart_integrity = _result(restart, "integrity")
        restart_root = _canonical_root(restart_integrity)
        process_restart_identity = restart_root == canonical \
            and _roots_converged(_result(restart, "roots"), restart_root)

        duplicates = _session(runtime, source, stable,
                              [{"op": "ingest_batch", "node_id": "n2",
                                "events": list(reversed(baseline))},
                               {"op": "integrity"}, {"op": "close"}], timeout=360)
        duplicate_idempotence = _canonical_root(_result(duplicates, "integrity")) == canonical

        conflict_id = f"PARTITION-CONFLICT-{args.seed}"
        minority_event = {
            "source_id": conflict_id, "kind": "LEGISLATION",
            "canonical_id": "PARTITION:LAW", "target_id": "PARTITION:LAW",
            "publication_time": "2031-01-01", "knowledge_time": "2031-01-01",
            "effective_from": "2031-01-01", "text": "minority-branch",
        }
        majority_event = dict(minority_event); majority_event["text"] = "majority-branch"
        partition = _session(runtime, source, stable,
                             [{"op": "partition", "groups": [["n1", "n2", "n3"], ["n4", "n5"]]},
                              {"op": "submit", "node_id": "n4", "event": minority_event},
                              {"op": "submit", "node_id": "n1", "event": majority_event},
                              {"op": "heal"}, {"op": "integrity"}, {"op": "roots"},
                              {"op": "publication_roots"}, {"op": "close"}], timeout=360)
        minority = _result(partition, "submit", 0)
        majority = _result(partition, "submit", 1)
        partition_integrity = _result(partition, "integrity")
        partition_root = _canonical_root(partition_integrity)
        minority_fail_closed = not _accepted(minority)
        majority_committed = _accepted(majority)
        partition_heal_convergence = _roots_converged(
            _result(partition, "roots"), partition_root)
        partition_publication = _publication_ok(
            _result(partition, "publication_roots"), partition_root)

        below = _session(runtime, source, stable,
                         [{"op": "crash", "node_id": "n1"},
                          {"op": "crash", "node_id": "n2"},
                          {"op": "crash", "node_id": "n3"},
                          {"op": "submit", "node_id": "n4",
                           "event": _events(1, args.seed + 11, "NOQUORUM")[0]},
                          {"op": "restart", "node_id": "n1"},
                          {"op": "restart", "node_id": "n2"},
                          {"op": "restart", "node_id": "n3"},
                          {"op": "heal"}, {"op": "integrity"},
                          {"op": "roots"}, {"op": "close"}], timeout=360)
        no_quorum = _result(below, "submit")
        below_quorum_fail_closed = not _accepted(no_quorum)
        below_root = _canonical_root(_result(below, "integrity"))
        below_recovery = _roots_converged(_result(below, "roots"), below_root)

        node = _session(runtime, source, stable,
                        [{"op": "crash", "node_id": "n5"}, {"op": "roots"},
                         {"op": "restart", "node_id": "n5"}, {"op": "heal"},
                         {"op": "integrity"}, {"op": "roots"}, {"op": "close"}])
        crashed_roots = _result(node, "roots", 0)
        node_crash_observed = crashed_roots.get("n5") == "CRASHED"
        node_root = _canonical_root(_result(node, "integrity"))
        node_restart_convergence = _roots_converged(_result(node, "roots", 1), node_root)

        accepted_events = list(baseline) + [majority_event]
        byzantine_required = (args.expected_replication_model in BFT_MODELS
                              or args.expected_commit_model in BFT_COMMITS)
        byzantine_passed = True
        byzantine_detail = {"required": byzantine_required, "tested": False}
        if byzantine_required:
            byz_event = _events(1, args.seed + 12, "BYZ")[0]
            byz = _session(runtime, source, stable,
                           [{"op": "inject_fault", "node_id": "n5", "fault": "equivocate_root"},
                            {"op": "submit", "node_id": "n1", "event": byz_event},
                            {"op": "integrity"}, {"op": "roots"},
                            {"op": "recover", "node_id": "n5"}, {"op": "heal"},
                            {"op": "integrity"}, {"op": "roots"}, {"op": "close"}],
                           timeout=360, allow_errors=True)
            inject = [x for x in byz if x.get("op") == "inject_fault"]
            submit = [x for x in byz if x.get("op") == "submit"]
            integrities = [x for x in byz if x.get("op") == "integrity"]
            roots_rows = [x for x in byz if x.get("op") == "roots"]
            byzantine_passed = bool(inject and inject[-1].get("ok")
                                    and submit and submit[-1].get("ok")
                                    and _accepted(submit[-1].get("result"))
                                    and len(integrities) >= 2 and integrities[-1].get("ok")
                                    and integrities[-1].get("result", {}).get("ok") is True
                                    and len(roots_rows) >= 2 and roots_rows[-1].get("ok")
                                    and _roots_converged(
                                        roots_rows[-1].get("result"),
                                        integrities[-1].get("result", {}).get("canonical_root")))
            byzantine_detail = {"required": True, "tested": True,
                                "passed": byzantine_passed}
            if byzantine_passed:
                accepted_events.append(byz_event)

        crash_state = os.path.join(temp, "process-crash")
        _session(runtime, source, crash_state,
                 [{"op": "ingest_batch", "node_id": "n1",
                   "events": _events(500, args.seed + 20, "CRASHBASE")},
                  {"op": "close"}], timeout=240)
        process_crash_observed = _crash_process(
            runtime, source, crash_state,
            _events(max(20000, args.large_events), args.seed + 21, "CRASHLOAD"))
        try:
            crash_rep = _session(runtime, source, crash_state,
                                 [{"op": "heal"}, {"op": "integrity"},
                                  {"op": "roots"}, {"op": "close"}], timeout=360)
            crash_root = _canonical_root(_result(crash_rep, "integrity"))
            process_crash_recovery = process_crash_observed \
                and _roots_converged(_result(crash_rep, "roots"), crash_root)
        except Exception:
            process_crash_recovery = False

        corruption = _corruption_trial(
            runtime, source, stable, manifest, os.path.join(temp, "corrupt"))

        rebuilt = os.path.join(temp, "rebuild")
        rebuild_rep = _session(runtime, source, rebuilt,
                               [{"op": "ingest_batch", "node_id": "n1",
                                 "events": accepted_events},
                                {"op": "integrity"}, {"op": "roots"},
                                {"op": "publication_roots"}, {"op": "close"}], timeout=600)
        rebuild_root = _canonical_root(_result(rebuild_rep, "integrity"))
        final_rep = _session(runtime, source, stable,
                             [{"op": "integrity"}, {"op": "roots"},
                              {"op": "publication_roots"}, {"op": "close"}])
        final_root = _canonical_root(_result(final_rep, "integrity"))
        independent_rebuild = rebuild_root == final_root
        final_convergence = _roots_converged(_result(final_rep, "roots"), final_root)
        final_publication = _publication_ok(
            _result(final_rep, "publication_roots"), final_root)

        elapsed = time.monotonic() - start
        tests = {
            "manifest_matches_controlled_genome": True,
            "baseline_all_events_accepted": baseline_accepted,
            "healthy_convergence": healthy_convergence,
            "process_restart_identity": process_restart_identity,
            "duplicate_reordered_idempotence": duplicate_idempotence,
            "minority_partition_fail_closed": minority_fail_closed,
            "majority_partition_commit": majority_committed,
            "partition_heal_convergence": partition_heal_convergence,
            "partition_publication_consistency": partition_publication,
            "below_quorum_fail_closed": below_quorum_fail_closed,
            "below_quorum_recovery": below_recovery,
            "node_crash_observed": node_crash_observed,
            "node_restart_convergence": node_restart_convergence,
            "whole_process_crash_recovery": process_crash_recovery,
            "node_corruption_detection_recovery": corruption,
            "byzantine_equivocation": byzantine_detail,
            "independent_rebuild": independent_rebuild,
            "final_convergence": final_convergence,
            "final_publication_consistency": final_publication,
        }
        simple = [value for value in tests.values() if isinstance(value, bool)]
        passed = all(simple) and corruption.get("passed") is True \
            and (not byzantine_required or byzantine_passed)
        report.update({
            "status": "PASS" if passed else "FAIL",
            "passed": passed,
            "manifest": manifest,
            "tests": tests,
            "accepted_canonical_events": len(accepted_events),
            "canonical_root": final_root,
            "elapsed_seconds": elapsed,
            "events_per_second_baseline": len(baseline) / max(elapsed, 1e-9),
            "tested_fault_model": {
                "nodes": len(NODE_IDS),
                "crash_faults": True,
                "partition_groups": [3, 2],
                "below_quorum": True,
                "storage_corruption": True,
                "byzantine_equivocation": byzantine_required,
            },
            "proof_boundary": (
                "bounded local container simulation; stronger geographical, operational, Byzantine "
                "or performance claims require additional evidence"),
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
