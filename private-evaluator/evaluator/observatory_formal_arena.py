#!/usr/bin/env python3
"""Bounded machine-checked transition-model arena for Observatory architectures.

The candidate model executes inside a network-disabled, read-only container. The in-container harness
uses hidden randomized identifiers and exhaustively enumerates a finite action alphabet, while also
running directed bitemporal, repeal/revival, conflict, partition, crash/recovery, rule-upgrade and
commutativity scenarios. The report is a bounded proof artifact, never an unbounded implementation
or deployment claim.
"""
import argparse
import json
import os
import subprocess
import sys

from candidate_host import container_runtime

IMAGE = "python:3.11-slim"
MANIFEST_FIELDS = [
    "canonical_authority_seat", "state_derivation_model", "temporal_model",
    "normative_effect_model", "consistency_commit_model",
    "replication_distribution_model", "trusted_core_topology",
]

HARNESS = r'''
import copy, hashlib, itertools, json, random, sys, traceback
payload = json.loads(sys.stdin.read())
source = payload["candidate_source"]
expected = payload["expected_manifest"]
seed = int(payload["seed"]); depth = int(payload["depth"])
ns = {"__name__": "__candidate__"}
report = {"status": "FAIL", "passed": False, "seed": seed, "depth": depth,
          "counterexamples": [], "directed": {}}

def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"))
def digest(obj):
    return hashlib.sha256(canonical(obj).encode("utf-8")).hexdigest()
def fail(kind, detail, trace=None):
    if len(report["counterexamples"]) < 128:
        report["counterexamples"].append({"kind": kind, "detail": detail,
                                           "trace": list(trace or [])})
def serializable(obj, where):
    try: canonical(obj); return True
    except Exception as exc:
        fail("non-json", where + ": " + type(exc).__name__ + ": " + str(exc)); return False

try:
    exec(compile(source, "<formal-candidate>", "exec"), ns, ns)
    required = ["initial_state", "transition", "state_root", "query",
                "publication", "model_manifest"]
    missing = [name for name in required if not callable(ns.get(name))]
    if missing: raise RuntimeError("missing functions: " + ", ".join(missing))
    initial_state = ns["initial_state"]; transition = ns["transition"]
    state_root = ns["state_root"]; query = ns["query"]
    publication = ns["publication"]; model_manifest = ns["model_manifest"]

    manifest = model_manifest()
    if not isinstance(manifest, dict): raise RuntimeError("model_manifest must return object")
    for key, value in expected.items():
        if manifest.get(key) != value:
            raise RuntimeError(f"manifest mismatch {key}: {manifest.get(key)!r} != {value!r}")
    if manifest.get("minority_partition_policy") not in ("reject", "pending"):
        raise RuntimeError("minority_partition_policy must be reject or pending")
    if not isinstance(manifest.get("commutative_independent_admissions"), bool):
        raise RuntimeError("manifest lacks commutative_independent_admissions boolean")
    if not isinstance(manifest.get("proof_boundary"), str) or not manifest["proof_boundary"].strip():
        raise RuntimeError("manifest lacks proof_boundary")
    report["manifest"] = manifest

    rng = random.Random(seed)
    A = "LAW-" + hashlib.sha256(f"A|{seed}".encode()).hexdigest()[:12]
    B = "LAW-" + hashlib.sha256(f"B|{seed}".encode()).hexdigest()[:12]
    C = "LAW-" + hashlib.sha256(f"C|{seed}".encode()).hexdigest()[:12]
    SA = "SRC-" + hashlib.sha256(f"SA|{seed}".encode()).hexdigest()[:16]
    SB = "SRC-" + hashlib.sha256(f"SB|{seed}".encode()).hexdigest()[:16]
    SC = "SRC-" + hashlib.sha256(f"SC|{seed}".encode()).hexdigest()[:16]
    texts = [hashlib.sha256(f"text|{seed}|{i}".encode()).hexdigest()[:20]
             for i in range(8)]

    def admit(source_id, canonical_id, k, e, effect, text=None, group="majority"):
        return {"type": "ADMIT", "source_id": source_id,
                "canonical_id": canonical_id, "knowledge_time": k,
                "effective_time": e, "effect": effect, "text": text,
                "node_group": group}

    actions = [
        admit(SA, A, 1, 1, "SET", texts[0]),
        admit(SA, A, 1, 1, "SET", texts[0]),
        admit(SA, A, 1, 1, "SET", texts[1]),
        admit(SA + "-AM", A, 3, 3, "AMEND", texts[2]),
        admit(SA + "-CO", A, 5, 2, "CORRECT", texts[3]),
        admit(SA + "-RE", A, 4, 4, "REPEAL"),
        admit(SA + "-RV", A, 6, 5, "REVIVE"),
        admit(SB, B, 2, 2, "SET", texts[4]),
        {"type": "PARTITION"},
        admit(SC, C, 2, 2, "SET", texts[5], "minority"),
        admit(SC, C, 2, 2, "SET", texts[6], "majority"),
        {"type": "HEAL"}, {"type": "CRASH"}, {"type": "RECOVER"},
        {"type": "RULE_UPGRADE", "rule_version": "RULE-" + str(2 + seed % 97)},
    ]
    action_codes = ["SET-A", "DUP-A", "CONFLICT-A", "AMEND-A", "CORRECT-A",
                    "REPEAL-A", "REVIVE-A", "SET-B", "PARTITION", "MINORITY-C",
                    "MAJORITY-C", "HEAL", "CRASH", "RECOVER", "RULE-UPGRADE"]

    def checked_transition(state, action, trace):
        before = copy.deepcopy(state); before_bytes = canonical(before)
        out1 = transition(copy.deepcopy(state), copy.deepcopy(action))
        out2 = transition(copy.deepcopy(state), copy.deepcopy(action))
        if canonical(out1) != canonical(out2):
            fail("nondeterministic-transition", canonical(action), trace)
        if canonical(state) != before_bytes:
            fail("input-state-mutated", canonical(action), trace)
        if not isinstance(out1, dict) or not isinstance(out1.get("state"), dict):
            fail("malformed-transition-result", canonical(out1), trace)
            return {"state": before, "accepted": False, "duplicate": False,
                    "pending": False, "unresolved": False, "reason": "malformed"}
        for key in ("accepted", "duplicate", "pending", "unresolved"):
            if not isinstance(out1.get(key), bool):
                fail("malformed-transition-flag", key, trace)
        serializable(out1, "transition result")
        return out1

    def checked_query(state, request, trace):
        first = query(copy.deepcopy(state), copy.deepcopy(request))
        second = query(copy.deepcopy(state), copy.deepcopy(request))
        if canonical(first) != canonical(second):
            fail("nondeterministic-query", canonical(request), trace)
        required = {"canonical_id", "status", "text", "legal_time",
                    "knowledge_time", "evidence_chain", "unresolved"}
        if not isinstance(first, dict) or not required.issubset(first):
            fail("malformed-query", canonical(first), trace)
        return first

    def checked_publication(state, trace):
        root = state_root(copy.deepcopy(state))
        if not isinstance(root, str) or not root:
            fail("malformed-root", repr(root), trace)
        pub = publication(copy.deepcopy(state))
        required = {"human", "api", "linked_data", "eli", "public_sector", "ai"}
        channels = pub.get("channels") if isinstance(pub, dict) else None
        if not isinstance(pub, dict) or pub.get("canonical_root") != root \
                or not isinstance(channels, dict) or not required.issubset(channels) \
                or any(channels[x] != root for x in required):
            fail("publication-root-divergence", canonical(pub), trace)
        return root, pub

    def run_actions(sequence, label):
        state = initial_state(); serializable(state, "initial state")
        external_partitioned = False; external_crashed = False
        results = []
        for index in sequence:
            action = actions[index]; code = action_codes[index]
            trace = [action_codes[x] for x in sequence[:len(results)+1]]
            root_before = state_root(copy.deepcopy(state))
            prior_queries = {
                obj: checked_query(state, {"canonical_id": obj,
                    "legal_time": 10, "knowledge_time": 10}, trace)
                for obj in (A, B, C)}
            out = checked_transition(state, action, trace)
            state = out["state"]; root_after = state_root(copy.deepcopy(state))
            if out.get("duplicate") and root_after != root_before:
                fail("duplicate-changed-root", code, trace)
            if out.get("unresolved"):
                after_q = checked_query(state, {"canonical_id": action.get("canonical_id", A),
                    "legal_time": 10, "knowledge_time": 10}, trace)
                before_q = prior_queries.get(action.get("canonical_id", A))
                if before_q and (after_q.get("status"), after_q.get("text")) != \
                        (before_q.get("status"), before_q.get("text")):
                    fail("conflict-overwrote-legal-state", code, trace)
                if not after_q.get("unresolved"):
                    fail("conflict-not-observable", code, trace)
            if external_partitioned and action.get("type") == "ADMIT" \
                    and action.get("node_group") == "minority":
                if out.get("accepted") or root_after != root_before:
                    fail("minority-write-committed", code, trace)
            if action.get("type") in ("CRASH", "RECOVER") and root_after != root_before:
                fail("crash-recovery-changed-authority-root", code, trace)
            if external_crashed and action.get("type") == "ADMIT" and out.get("accepted"):
                fail("admission-accepted-while-crashed", code, trace)
            if action.get("type") == "RULE_UPGRADE":
                for obj in (A, B, C):
                    after = checked_query(state, {"canonical_id": obj,
                        "legal_time": 10, "knowledge_time": 10}, trace)
                    before = prior_queries[obj]
                    if (after.get("status"), after.get("text"), after.get("evidence_chain")) != \
                            (before.get("status"), before.get("text"), before.get("evidence_chain")):
                        fail("rule-upgrade-retroactivity", obj, trace)
            checked_publication(state, trace)
            if action.get("type") == "PARTITION": external_partitioned = True
            elif action.get("type") == "HEAL": external_partitioned = False
            elif action.get("type") == "CRASH": external_crashed = True
            elif action.get("type") == "RECOVER": external_crashed = False
            results.append({"code": code, "accepted": bool(out.get("accepted")),
                            "duplicate": bool(out.get("duplicate")),
                            "pending": bool(out.get("pending")),
                            "unresolved": bool(out.get("unresolved"))})
        observations = []
        for obj in (A, B, C):
            for legal, knowledge in ((2, 2), (2, 6), (4, 4), (10, 10)):
                q = checked_query(state, {"canonical_id": obj,
                    "legal_time": legal, "knowledge_time": knowledge}, list(label))
                observations.append({"object": obj, "legal": legal, "knowledge": knowledge,
                                     "status": q.get("status"), "text": q.get("text"),
                                     "evidence_chain": q.get("evidence_chain"),
                                     "unresolved": q.get("unresolved")})
        return state, {"sequence": [action_codes[x] for x in sequence],
                       "results": results, "observations": observations}

    # Directed bitemporal correction and amendment scenario.
    state = initial_state()
    directed_actions = [
        admit(SA + "-D1", A, 1, 1, "SET", texts[0]),
        admit(SA + "-D2", A, 3, 3, "AMEND", texts[2]),
        admit(SA + "-D3", A, 5, 2, "CORRECT", texts[3]),
    ]
    for idx, action in enumerate(directed_actions):
        state = checked_transition(state, action, ["BT", str(idx)])["state"]
    q24 = checked_query(state, {"canonical_id": A, "legal_time": 2, "knowledge_time": 4}, ["BT"])
    q26 = checked_query(state, {"canonical_id": A, "legal_time": 2, "knowledge_time": 6}, ["BT"])
    q44 = checked_query(state, {"canonical_id": A, "legal_time": 4, "knowledge_time": 4}, ["BT"])
    q46 = checked_query(state, {"canonical_id": A, "legal_time": 4, "knowledge_time": 6}, ["BT"])
    bitemporal = (q24.get("text") == texts[0] and q26.get("text") == texts[3]
                  and q44.get("text") == texts[2] and q46.get("text") == texts[2])
    if not bitemporal: fail("bitemporal-directed-failure", canonical([q24,q26,q44,q46]), ["BT"])
    report["directed"]["bitemporal"] = bitemporal

    state = initial_state()
    for action in [admit(SA+"-R1", A, 1, 1, "SET", texts[0]),
                   admit(SA+"-R2", A, 2, 2, "REPEAL"),
                   admit(SA+"-R3", A, 3, 3, "REVIVE")]:
        state = checked_transition(state, action, ["REPEAL-REVIVE"])["state"]
    qr = checked_query(state, {"canonical_id": A, "legal_time": 2, "knowledge_time": 10}, ["RR"])
    qv = checked_query(state, {"canonical_id": A, "legal_time": 4, "knowledge_time": 10}, ["RR"])
    revive = qr.get("status") == "REPEALED" and qv.get("status") == "IN_FORCE" \
        and qv.get("text") == texts[0]
    if not revive: fail("repeal-revival-failure", canonical([qr,qv]), ["RR"])
    report["directed"]["repeal_revival"] = revive

    if manifest.get("commutative_independent_admissions"):
        s1, _ = run_actions((0, 7), ["COMMUTE-AB"])
        s2, _ = run_actions((7, 0), ["COMMUTE-BA"])
        commute = state_root(s1) == state_root(s2)
        if not commute: fail("independent-admission-noncommutativity", "A/B roots differ", ["COMMUTE"])
        report["directed"]["commutative_independent_admissions"] = commute
    else:
        report["directed"]["commutative_independent_admissions"] = "NOT_CLAIMED"

    behavior = []
    unique_states = set()
    trace_count = 0
    for length in range(1, depth + 1):
        for sequence in itertools.product(range(len(actions)), repeat=length):
            state, observation = run_actions(sequence, [action_codes[x] for x in sequence])
            unique_states.add(digest(state))
            behavior.append(observation)
            trace_count += 1
    report["trace_count"] = trace_count
    report["unique_state_count"] = len(unique_states)
    report["behavioral_digest"] = digest(behavior)
    report["manifest_digest"] = digest(manifest)
    report["passed"] = not report["counterexamples"]
    report["status"] = "PASS" if report["passed"] else "FAIL"
    report["proof_boundary"] = manifest.get("proof_boundary")
except BaseException as exc:
    report["status"] = "FAIL"; report["passed"] = False
    report["reason"] = type(exc).__name__ + ": " + str(exc)
    report["traceback"] = traceback.format_exc()[-4000:]
print(json.dumps(report, ensure_ascii=False, sort_keys=True))
'''


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate", required=True)
    ap.add_argument("--out", required=True)
    for field in MANIFEST_FIELDS:
        ap.add_argument("--expected-" + field.replace("_", "-"), required=True)
    ap.add_argument("--seed", type=int, default=9702026)
    ap.add_argument("--depth", type=int, default=4)
    ap.add_argument("--timeout", type=int, default=7200)
    args = ap.parse_args(argv)

    runtime = container_runtime()
    if not runtime:
        raise RuntimeError("formal model arena requires docker/podman")
    source = open(args.candidate, encoding="utf-8").read()
    expected = {field: getattr(args, "expected_" + field) for field in MANIFEST_FIELDS}
    payload = json.dumps({"candidate_source": source, "expected_manifest": expected,
                          "seed": args.seed, "depth": args.depth}, ensure_ascii=False)
    command = [
        runtime, "run", "--rm", "-i", "--network=none", "--read-only",
        "--tmpfs", "/tmp:size=256m", "--memory=3g", "--pids-limit=128",
        "--cap-drop=ALL", "--security-opt", "no-new-privileges",
        "-w", "/tmp", IMAGE, "python3", "-I", "-S", "-B", "-c", HARNESS,
    ]
    result = subprocess.run(command, input=payload, capture_output=True,
                            text=True, timeout=args.timeout)
    if result.returncode != 0:
        report = {"status": "FAIL", "passed": False,
                  "reason": f"formal container exited {result.returncode}",
                  "stderr": result.stderr[-2000:]}
    else:
        lines = [line for line in result.stdout.splitlines() if line.strip()]
        try:
            report = json.loads(lines[-1])
        except Exception as exc:
            report = {"status": "FAIL", "passed": False,
                      "reason": "formal arena produced no JSON report: " + str(exc),
                      "stdout_tail": result.stdout[-2000:],
                      "stderr_tail": result.stderr[-2000:]}
    report["backend"] = "container"
    report["runtime"] = runtime
    report["image"] = IMAGE
    report["candidate"] = os.path.abspath(args.candidate)
    report["expected_manifest"] = expected
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1, sort_keys=True)
    print(json.dumps(report, ensure_ascii=False, indent=1))
    return 0 if report.get("status") == "PASS" and report.get("passed") is True else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(json.dumps({"status": "FAIL", "passed": False,
                          "reason": str(exc)}, ensure_ascii=False, indent=1))
        sys.exit(1)
