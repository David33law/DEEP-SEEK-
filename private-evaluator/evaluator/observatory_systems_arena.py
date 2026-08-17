#!/usr/bin/env python3
"""Durable-systems arena for a National Observatory finalist.

This evaluator is intentionally separate from the in-memory legal-semantics CandidateHost. It
executes ``systems_candidate.py`` inside network-disabled, read-only-root containers with one
explicit writable state directory, then injects restart, duplicate-delivery, concurrency, crash,
corruption and large-rebuild conditions.
"""
import argparse
import concurrent.futures
import hashlib
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
REQUIRED_CHANNELS = {"human", "api", "linked_data", "eli", "public_sector", "ai"}

BOOTSTRAP = r'''
import json, sys, traceback
first = json.loads(sys.stdin.readline())
src = first["candidate_source"]
ns = {"__name__": "__candidate__"}
try:
    exec(compile(src, "<systems-candidate>", "exec"), ns, ns)
    opener = ns.get("open_system")
    if not callable(opener):
        raise RuntimeError("missing open_system(state_dir)")
    system = opener("/state")
except BaseException as exc:
    print(json.dumps({"ok": False, "phase": "open", "error": type(exc).__name__ + ": " + str(exc)}), flush=True)
    raise SystemExit(0)

for line in sys.stdin:
    if not line.strip():
        continue
    req = json.loads(line)
    op = req.get("op")
    if op == "quit":
        break
    try:
        if op == "ingest_batch":
            result = system.ingest_batch(req.get("events", []))
        elif op == "state_root":
            result = system.state_root()
        elif op == "integrity_check":
            result = system.integrity_check()
        elif op == "recover":
            result = system.recover()
        elif op == "publish_probe":
            result = system.publish_probe()
        elif op == "durability_manifest":
            result = system.durability_manifest()
        elif op == "close":
            result = system.close()
        else:
            raise RuntimeError("unknown op: " + str(op))
        print(json.dumps({"ok": True, "op": op, "result": result}, ensure_ascii=False), flush=True)
    except BaseException as exc:
        print(json.dumps({"ok": False, "op": op, "phase": "operation", "error": type(exc).__name__ + ": " + str(exc)}, ensure_ascii=False), flush=True)
'''


def _events(n, seed):
    rng = random.Random(seed)
    kinds = ["LEGISLATION", "AMENDMENT", "CORRECTION", "SUSPENSION", "REVIVAL", "REPEAL"]
    out = []
    for i in range(n):
        year = 2020 + (i % 12)
        month = 1 + (i % 12)
        day = 1 + (i % 27)
        kind = kinds[i % len(kinds)]
        cid = f"SYS-LAW-{i % max(50, n // 20):06d}:ART-{1 + (i % 40)}"
        out.append({
            "source_id": f"SYS-{seed:08x}-{i:09d}",
            "kind": kind,
            "canonical_id": cid,
            "target_id": cid,
            "publication_time": f"{year:04d}-{month:02d}-{day:02d}",
            "knowledge_time": f"{year:04d}-{month:02d}-{day:02d}",
            "effective_from": f"{year:04d}-{month:02d}-{day:02d}",
            "text": f"payload-{i}-{rng.randrange(10**9)}" if kind in ("LEGISLATION", "AMENDMENT", "CORRECTION") else None,
        })
    return out


def _argv(runtime, state_dir):
    return [
        runtime, "run", "--rm", "-i",
        "--network=none", "--read-only", "--tmpfs", "/tmp:size=128m",
        "--memory=2g", "--pids-limit=128", "--cap-drop=ALL",
        "--security-opt", "no-new-privileges",
        "--mount", f"type=bind,source={os.path.abspath(state_dir)},target=/state",
        "-w", "/tmp", IMAGE, "python3", "-I", "-S", "-B", "-c", BOOTSTRAP,
    ]


def _body(source, commands):
    lines = [json.dumps({"candidate_source": source}, ensure_ascii=False)]
    lines.extend(json.dumps(x, ensure_ascii=False) for x in commands)
    lines.append(json.dumps({"op": "quit"}))
    return "\n".join(lines) + "\n"


def _session(runtime, source, state_dir, commands, timeout=180, allow_errors=False):
    os.makedirs(state_dir, exist_ok=True)
    p = subprocess.run(_argv(runtime, state_dir), input=_body(source, commands),
                       capture_output=True, text=True, timeout=timeout)
    if p.returncode != 0:
        raise RuntimeError(f"systems container exited {p.returncode}: {p.stderr[-500:]}")
    replies = []
    for line in p.stdout.splitlines():
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if "ok" in obj:
            replies.append(obj)
    if not replies:
        raise RuntimeError(f"systems candidate produced no protocol result: {p.stderr[-500:]}")
    if not allow_errors:
        bad = [x for x in replies if not x.get("ok")]
        if bad:
            raise RuntimeError("systems candidate error: " + json.dumps(bad[0], ensure_ascii=False)[:800])
    return replies


def _result(replies, op):
    xs = [x for x in replies if x.get("op") == op]
    if not xs:
        raise RuntimeError(f"systems candidate returned no {op} result")
    if not xs[-1].get("ok"):
        raise RuntimeError(f"systems candidate {op} failed: {xs[-1].get('error')}")
    return xs[-1].get("result")


def _root(runtime, source, state_dir):
    rep = _session(runtime, source, state_dir,
                   [{"op": "state_root"}, {"op": "integrity_check"},
                    {"op": "publish_probe"}, {"op": "close"}])
    root = _result(rep, "state_root")
    integrity = _result(rep, "integrity_check")
    publication = _result(rep, "publish_probe")
    if not isinstance(root, str) or not root:
        raise RuntimeError("state_root must be a non-empty string")
    if not isinstance(integrity, dict) or integrity.get("ok") is not True:
        raise RuntimeError("integrity_check did not return ok=true")
    if not isinstance(publication, dict) or publication.get("canonical_root") != root:
        raise RuntimeError("publish_probe is not bound to the canonical root")
    if not REQUIRED_CHANNELS.issubset(set(publication.get("channels") or [])):
        raise RuntimeError("publish_probe omitted required national publication channels")
    return root, integrity, publication


def _manifest(runtime, source, state_dir):
    rep = _session(runtime, source, state_dir,
                   [{"op": "durability_manifest"}, {"op": "close"}])
    m = _result(rep, "durability_manifest")
    if not isinstance(m, dict):
        raise RuntimeError("durability_manifest must return an object")
    authority = m.get("authority_files")
    if not isinstance(authority, list) or not authority:
        raise RuntimeError("durability_manifest requires non-empty authority_files")
    return m


def _crash(runtime, source, state_dir, events, delay=0.15):
    cmd = [{"op": "ingest_batch", "events": events}]
    p = subprocess.Popen(_argv(runtime, state_dir), stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    payload = _body(source, cmd)
    try:
        p.stdin.write(payload)
        p.stdin.flush()
    except (BrokenPipeError, OSError):
        pass
    time.sleep(delay)
    try:
        p.kill()
    except OSError:
        pass
    try:
        p.communicate(timeout=10)
    except subprocess.TimeoutExpired:
        p.kill()
        p.communicate()


def _flip_file(path):
    with open(path, "r+b") as f:
        data = f.read()
        if not data:
            raise RuntimeError(f"cannot corrupt empty authority file {path}")
        pos = min(len(data) - 1, max(0, len(data) // 2))
        old = data[pos]
        f.seek(pos)
        f.write(bytes([old ^ 0x5A]))
        f.flush()
        os.fsync(f.fileno())


def _corruption_trial(runtime, source, stable_state, work):
    shutil.copytree(stable_state, work)
    original_root, _, _ = _root(runtime, source, work)
    manifest = _manifest(runtime, source, work)
    rel = manifest["authority_files"][0]
    if os.path.isabs(rel) or ".." in rel.replace("\\", "/").split("/"):
        raise RuntimeError("durability_manifest authority_files must be relative state paths")
    victim = os.path.abspath(os.path.join(work, rel))
    if not victim.startswith(os.path.abspath(work) + os.sep) or not os.path.isfile(victim):
        raise RuntimeError(f"declared authority file does not exist: {rel}")
    _flip_file(victim)

    rep = _session(runtime, source, work,
                   [{"op": "integrity_check"}, {"op": "state_root"}, {"op": "close"}],
                   allow_errors=True)
    integ = [x for x in rep if x.get("op") == "integrity_check"]
    root_replies = [x for x in rep if x.get("op") == "state_root"]
    auto_recovered = bool(integ and integ[-1].get("ok") and isinstance(integ[-1].get("result"), dict)
                          and integ[-1]["result"].get("ok") is True
                          and root_replies and root_replies[-1].get("ok")
                          and root_replies[-1].get("result") == original_root)
    detected = bool(integ and (not integ[-1].get("ok")
                               or not (isinstance(integ[-1].get("result"), dict)
                                       and integ[-1]["result"].get("ok") is True)))
    if auto_recovered:
        return {"passed": True, "detected_or_auto_recovered": True,
                "recovered": True, "victim": rel, "mode": "automatic"}

    # Explicit recovery is required if corruption remains observable.
    rep2 = _session(runtime, source, work,
                    [{"op": "recover"}, {"op": "integrity_check"},
                     {"op": "state_root"}, {"op": "close"}], allow_errors=True)
    recover = [x for x in rep2 if x.get("op") == "recover"]
    integrity = [x for x in rep2 if x.get("op") == "integrity_check"]
    roots = [x for x in rep2 if x.get("op") == "state_root"]
    recovered = bool(recover and recover[-1].get("ok")
                     and isinstance(recover[-1].get("result"), dict)
                     and recover[-1]["result"].get("ok") is True
                     and integrity and integrity[-1].get("ok")
                     and isinstance(integrity[-1].get("result"), dict)
                     and integrity[-1]["result"].get("ok") is True
                     and roots and roots[-1].get("ok")
                     and roots[-1].get("result") == original_root)
    return {"passed": bool(detected and recovered), "detected_or_auto_recovered": detected,
            "recovered": recovered, "victim": rel, "mode": "explicit"}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=7302026)
    ap.add_argument("--large-events", type=int, default=50000)
    a = ap.parse_args(argv)

    runtime = container_runtime()
    if not runtime:
        raise RuntimeError("durable systems arena requires docker/podman container runtime")
    source = open(a.candidate, encoding="utf-8").read()
    temp = tempfile.mkdtemp(prefix="obs-systems-")
    report = {"status": "FAIL", "backend": "container", "runtime": runtime,
              "image": IMAGE, "candidate": os.path.abspath(a.candidate)}
    try:
        base = os.path.join(temp, "stable")
        small = _events(2000, a.seed)
        start = time.monotonic()
        rep = _session(runtime, source, base,
                       [{"op": "ingest_batch", "events": small},
                        {"op": "state_root"}, {"op": "integrity_check"},
                        {"op": "publish_probe"}, {"op": "close"}], timeout=240)
        root1 = _result(rep, "state_root")
        integrity1 = _result(rep, "integrity_check")
        publish1 = _result(rep, "publish_probe")
        initial_ok = (isinstance(root1, str) and bool(root1)
                      and isinstance(integrity1, dict) and integrity1.get("ok") is True
                      and isinstance(publish1, dict) and publish1.get("canonical_root") == root1
                      and REQUIRED_CHANNELS.issubset(set(publish1.get("channels") or [])))

        root2, _, _ = _root(runtime, source, base)
        restart_identity = root2 == root1

        rep_dup = _session(runtime, source, base,
                           [{"op": "ingest_batch", "events": small},
                            {"op": "state_root"}, {"op": "close"}], timeout=240)
        duplicate_identity = _result(rep_dup, "state_root") == root1

        # Concurrent access: implementations may serialize or explicitly reject/retry some writers,
        # but the durable state must remain internally valid afterwards.
        concurrent_batches = [_events(500, a.seed + 100 + i) for i in range(4)]
        def one(batch):
            try:
                rr = _session(runtime, source, base,
                              [{"op": "ingest_batch", "events": batch}, {"op": "close"}],
                              timeout=180, allow_errors=True)
                return any(x.get("op") == "ingest_batch" and x.get("ok") for x in rr)
            except Exception:
                return False
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
            concurrent_results = list(ex.map(one, concurrent_batches))
        _root_after_concurrency, integ_after_concurrency, _ = _root(runtime, source, base)
        concurrent_integrity = bool(any(concurrent_results) and integ_after_concurrency.get("ok") is True)

        # Forced process death during a large write must not turn torn bytes into valid authority.
        crash_state = os.path.join(temp, "crash")
        _session(runtime, source, crash_state,
                 [{"op": "ingest_batch", "events": _events(1000, a.seed + 200)}, {"op": "close"}],
                 timeout=180)
        _crash(runtime, source, crash_state, _events(20000, a.seed + 201))
        try:
            _crash_root, crash_integrity_rep, _ = _root(runtime, source, crash_state)
            crash_integrity = crash_integrity_rep.get("ok") is True
        except Exception:
            crash_integrity = False

        corruption = _corruption_trial(runtime, source, base, os.path.join(temp, "corrupt"))

        large = _events(max(1000, a.large_events), a.seed + 300)
        r1 = os.path.join(temp, "large-a")
        r2 = os.path.join(temp, "large-b")
        t0 = time.monotonic()
        _session(runtime, source, r1,
                 [{"op": "ingest_batch", "events": large}, {"op": "close"}], timeout=900)
        large_root1, large_integrity1, large_pub1 = _root(runtime, source, r1)
        t1 = time.monotonic()
        _session(runtime, source, r2,
                 [{"op": "ingest_batch", "events": large}, {"op": "close"}], timeout=900)
        large_root2, large_integrity2, large_pub2 = _root(runtime, source, r2)
        t2 = time.monotonic()
        deterministic_rebuild = large_root1 == large_root2
        large_integrity = large_integrity1.get("ok") is True and large_integrity2.get("ok") is True
        publication_consistency = (large_pub1.get("canonical_root") == large_root1
                                   and large_pub2.get("canonical_root") == large_root2
                                   and REQUIRED_CHANNELS.issubset(set(large_pub1.get("channels") or []))
                                   and REQUIRED_CHANNELS.issubset(set(large_pub2.get("channels") or [])))
        elapsed = (t1 - t0) + (t2 - t1)
        throughput = (2 * len(large)) / max(elapsed, 1e-9)

        passed = all([
            initial_ok, restart_identity, duplicate_identity, concurrent_integrity,
            crash_integrity, corruption["passed"], deterministic_rebuild,
            large_integrity, publication_consistency,
        ])
        report.update({
            "status": "PASS" if passed else "FAIL",
            "passed": passed,
            "tests": {
                "initial_durable_state": initial_ok,
                "restart_identity": restart_identity,
                "duplicate_idempotence": duplicate_identity,
                "concurrent_access_integrity": concurrent_integrity,
                "crash_restart_integrity": crash_integrity,
                "corruption_detection_recovery": corruption,
                "deterministic_large_rebuild": deterministic_rebuild,
                "large_history_integrity": large_integrity,
                "publication_root_consistency": publication_consistency,
            },
            "large_history": {"events_per_rebuild": len(large),
                              "two_rebuild_seconds": elapsed,
                              "events_per_second_aggregate": throughput,
                              "root": large_root1},
            "small_history_seconds": time.monotonic() - start,
        })
    finally:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        with open(a.out, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=1, sort_keys=True)
        shutil.rmtree(temp, ignore_errors=True)
    print(json.dumps(report, ensure_ascii=False, indent=1))
    return 0 if report.get("status") == "PASS" else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        fail = {"status": "FAIL", "passed": False, "reason": str(exc)}
        print(json.dumps(fail, ensure_ascii=False, indent=1))
        try:
            if "a" in locals():
                os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
                with open(a.out, "w", encoding="utf-8") as f:
                    json.dump(fail, f, ensure_ascii=False, indent=1, sort_keys=True)
        except Exception:
            pass
        sys.exit(1)
