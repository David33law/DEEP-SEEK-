#!/usr/bin/env python3
"""Hidden cross-model legal-state consistency arena.

Compares one selected semantic implementation, two independently qualified bounded transition models
and two independently qualified interoperability projections over the same randomized legal history.
It compares normalized legal observations, not unrelated candidate-defined root algorithms.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys

import bounded_subprocess
from candidate_host import container_runtime
from observatory_host import ObservatoryCandidateHost

bounded_subprocess.install(subprocess)
IMAGE = "python:3.11-slim"

FORMAL_BOOTSTRAP = r'''
import copy,json,sys
req=json.loads(sys.stdin.read()); ns={"__name__":"__candidate__"}
try:
 exec(compile(req["source"],"<formal-candidate>","exec"),ns,ns)
 state=ns["initial_state"](); results=[]
 for action in req["actions"]:
  row=ns["transition"](copy.deepcopy(state),copy.deepcopy(action)); state=row["state"]
  results.append({k:row.get(k) for k in ("accepted","duplicate","pending","unresolved","reason")})
 observations=[]
 for query in req["queries"]:
  observations.append(ns["query"](copy.deepcopy(state),copy.deepcopy(query)))
 out={"manifest":ns["model_manifest"](),"results":results,"observations":observations,
      "root":ns["state_root"](copy.deepcopy(state)),
      "publication":ns["publication"](copy.deepcopy(state))}
 print(json.dumps({"ok":True,"result":out},ensure_ascii=False,sort_keys=True))
except BaseException as exc:
 print(json.dumps({"ok":False,"error":type(exc).__name__+": "+str(exc)},ensure_ascii=False))
'''

INTEROP_BOOTSTRAP = r'''
import copy,json,sys
req=json.loads(sys.stdin.read()); ns={"__name__":"__candidate__"}
try:
 exec(compile(req["source"],"<interoperability-candidate>","exec"),ns,ns)
 out=ns["project"](copy.deepcopy(req["bundle"]))
 print(json.dumps({"ok":True,"result":out},ensure_ascii=False,sort_keys=True))
except BaseException as exc:
 print(json.dumps({"ok":False,"error":type(exc).__name__+": "+str(exc)},ensure_ascii=False))
'''


def _canon(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"))


def _digest(value):
    return hashlib.sha256(_canon(value).encode("utf-8")).hexdigest()


def _container(runtime, bootstrap, request, timeout=180):
    command = [runtime, "run", "--rm", "-i", "--network=none", "--read-only",
               "--tmpfs", "/tmp:size=128m", "--memory=2g", "--pids-limit=96",
               "--cap-drop=ALL", "--security-opt", "no-new-privileges",
               "-w", "/tmp", IMAGE, "python3", "-I", "-S", "-B", "-c", bootstrap]
    result = subprocess.run(command, input=json.dumps(request, ensure_ascii=False),
                            capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError("cross-model container exited nonzero: " + result.stderr[-800:])
    rows = []
    for line in result.stdout.splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if "ok" in row:
            rows.append(row)
    if not rows or rows[-1].get("ok") is not True:
        raise RuntimeError((rows[-1].get("error") if rows else result.stderr[-800:])
                           or "cross-model candidate produced no result")
    return rows[-1]["result"]


def _history(seed):
    token = hashlib.sha256(f"cross|{seed}".encode()).hexdigest()
    cid = "LAW-" + token[:16]
    ids = {name: name + "-" + token[start:start+12] for name, start in
           (("BASE", 0), ("AMEND", 8), ("CORR", 16), ("REPEAL", 24),
            ("REVIVE", 32), ("CONFLICT", 40), ("DOCTRINE", 48), ("DECISION", 52))}
    texts = {name: name.lower() + "-" + token[start:start+16] for name, start in
             (("BASE", 4), ("AMEND", 20), ("CORR", 36), ("CONFLICT", 44))}
    base = {"source_id": ids["BASE"], "kind": "LEGISLATION", "canonical_id": cid,
            "publication_time": "2020-01-01", "knowledge_time": "2020-01-01",
            "effective_from": "2020-01-01", "text": texts["BASE"]}
    amendment = {"source_id": ids["AMEND"], "kind": "AMENDMENT", "canonical_id": cid,
                 "target_id": cid, "publication_time": "2021-01-01",
                 "knowledge_time": "2021-01-01", "effective_from": "2021-01-01",
                 "text": texts["AMEND"]}
    correction = {"source_id": ids["CORR"], "kind": "CORRECTION", "canonical_id": cid,
                  "target_id": cid, "publication_time": "2022-01-01",
                  "knowledge_time": "2022-01-01", "effective_from": "2020-06-01",
                  "text": texts["CORR"]}
    repeal = {"source_id": ids["REPEAL"], "kind": "REPEAL", "canonical_id": cid,
              "target_id": cid, "publication_time": "2023-01-01",
              "knowledge_time": "2023-01-01", "effective_from": "2023-01-01"}
    revival = {"source_id": ids["REVIVE"], "kind": "REVIVAL", "canonical_id": cid,
               "target_id": cid, "publication_time": "2024-01-01",
               "knowledge_time": "2024-01-01", "effective_from": "2024-01-01"}
    conflict = {"source_id": ids["CONFLICT"], "kind": "CONFLICTING_SOURCE",
                "canonical_id": cid, "publication_time": "2025-01-01",
                "knowledge_time": "2025-01-01", "effective_from": "2020-01-01",
                "text": texts["CONFLICT"]}
    queries = {
        "pre_correction": {"canonical_id": cid, "legal_time": "2020-07-01",
                           "knowledge_time": "2021-06-01"},
        "post_correction": {"canonical_id": cid, "legal_time": "2020-07-01",
                            "knowledge_time": "2022-06-01"},
        "post_amendment": {"canonical_id": cid, "legal_time": "2022-06-01",
                           "knowledge_time": "2022-06-01"},
        "post_repeal": {"canonical_id": cid, "legal_time": "2023-06-01",
                        "knowledge_time": "2023-06-01"},
        "post_revival": {"canonical_id": cid, "legal_time": "2024-06-01",
                         "knowledge_time": "2024-06-01"},
        "post_conflict": {"canonical_id": cid, "legal_time": "2025-06-01",
                         "knowledge_time": "2025-06-01"}}
    return {"token": token, "canonical_id": cid, "ids": ids, "texts": texts,
            "base": base, "amendment": amendment, "correction": correction,
            "repeal": repeal, "revival": revival, "conflict": conflict,
            "queries": queries}


def _semantic(source, history):
    q = history["queries"]; ids = history["ids"]
    decision = {"decision_id": ids["DECISION"], "source_id": ids["DECISION"],
                "decision_time": "2022-06-01", "knowledge_time": "2022-06-01",
                "applies": [history["canonical_id"]]}
    doctrine = {"doctrine_id": ids["DOCTRINE"], "source_id": ids["DOCTRINE"],
                "kind": "DOCTRINE", "links": [history["canonical_id"]],
                "text": "scholarly-" + history["token"][:12]}
    events = [history[x] for x in ("base", "amendment", "correction", "repeal", "revival")]
    script = [
        {"m": "ingest", "a": {"source": history["base"]}},
        {"m": "ingest", "a": {"source": history["base"]}},
        {"m": "apply_change", "a": {"event": history["amendment"]}},
        {"m": "state_at", "a": {"query": q["pre_correction"]}},
        {"m": "apply_change", "a": {"event": history["correction"]}},
        {"m": "state_at", "a": {"query": q["pre_correction"]}},
        {"m": "state_at", "a": {"query": q["post_correction"]}},
        {"m": "state_at", "a": {"query": q["post_amendment"]}},
        {"m": "link_jurisprudence", "a": {"decision": decision}},
        {"m": "provenance", "a": {"query": q["post_amendment"]}},
        {"m": "publish", "a": {"query": q["post_amendment"]}},
        {"m": "replay", "a": {"events": events}},
        {"m": "replay", "a": {"events": list(events)}},
        {"m": "apply_change", "a": {"event": history["repeal"]}},
        {"m": "state_at", "a": {"query": q["post_repeal"]}},
        {"m": "apply_change", "a": {"event": history["revival"]}},
        {"m": "state_at", "a": {"query": q["post_revival"]}},
        {"m": "attach_doctrine", "a": {"document": doctrine}},
        {"m": "state_at", "a": {"query": q["post_revival"]}},
        {"m": "ingest", "a": {"source": history["conflict"]}},
        {"m": "state_at", "a": {"query": q["post_conflict"]}}]
    responses = ObservatoryCandidateHost(source, backend="container", timeout=120).run_session(script)
    if not isinstance(responses, list) or len(responses) != len(script):
        raise RuntimeError("semantic candidate returned malformed cross-model session")
    values = []
    for index, row in enumerate(responses):
        if not isinstance(row, dict) or row.get("error"):
            raise RuntimeError(f"semantic step {index} failed: {row}")
        values.append(row.get("r"))
    expected = {
        3: ("ACTIVE", history["texts"]["BASE"]),
        5: ("ACTIVE", history["texts"]["BASE"]),
        6: ("ACTIVE", history["texts"]["CORR"]),
        7: ("ACTIVE", history["texts"]["AMEND"]),
        14: ("REPEALED", None),
        16: ("ACTIVE", history["texts"]["AMEND"]),
        18: ("ACTIVE", history["texts"]["AMEND"])}
    checks = {}
    for index, (status, text) in expected.items():
        row = values[index] or {}
        checks[f"state-{index}"] = row.get("status") == status \
            and (text is None or row.get("text") == text)
    checks["duplicate-idempotent"] = bool((values[1] or {}).get("deduplicated"))
    links = (values[8] or {}).get("links") or []
    checks["historical-judgment-version"] = bool(
        links and links[0].get("version_evidence_id") == ids["AMEND"])
    chain = set((values[9] or {}).get("evidence_chain") or [])
    checks["provenance-complete"] = {ids["BASE"], ids["CORR"], ids["AMEND"]}.issubset(chain)
    publication = values[10] or {}; projection = publication.get("projection") or {}
    channels = projection.get("channels") or []
    checks["semantic-publication-one-state"] = (
        publication.get("canonical_id") == history["canonical_id"]
        and publication.get("status") == "ACTIVE"
        and publication.get("text") == history["texts"]["AMEND"]
        and {"human", "api", "linked_data", "eli", "public_sector", "ai"}.issubset(set(channels)))
    checks["semantic-replay-deterministic"] = (
        (values[11] or {}).get("state_root")
        and (values[11] or {}).get("state_root") == (values[12] or {}).get("state_root"))
    checks["doctrine-nonbinding"] = (
        (values[17] or {}).get("changes_binding_state") is False
        and (values[16] or {}).get("status") == (values[18] or {}).get("status")
        and (values[16] or {}).get("text") == (values[18] or {}).get("text"))
    conflict = values[20] or {}
    checks["conflict-observable"] = (
        conflict.get("status") == "CONFLICT" and bool(conflict.get("unresolved")))
    if not all(checks.values()):
        raise RuntimeError("semantic cross-model witness failed: "
                           + ", ".join(k for k, v in checks.items() if not v))
    observations = {
        "pre_correction": values[3], "post_correction": values[6],
        "post_amendment": values[7], "post_repeal": values[14],
        "post_revival": values[16], "post_conflict": values[20]}
    return {"checks": checks, "observations": observations,
            "judgment": values[8], "provenance": values[9],
            "publication": publication, "replay": values[11]}


def _formal(source, history, runtime):
    ids, texts = history["ids"], history["texts"]
    actions = [
        {"type": "ADMIT", "source_id": ids["BASE"],
         "canonical_id": history["canonical_id"], "knowledge_time": 1,
         "effective_time": 1, "effect": "SET", "text": texts["BASE"],
         "node_group": "majority"},
        {"type": "ADMIT", "source_id": ids["BASE"],
         "canonical_id": history["canonical_id"], "knowledge_time": 1,
         "effective_time": 1, "effect": "SET", "text": texts["BASE"],
         "node_group": "majority"},
        {"type": "ADMIT", "source_id": ids["AMEND"],
         "canonical_id": history["canonical_id"], "knowledge_time": 3,
         "effective_time": 3, "effect": "AMEND", "text": texts["AMEND"],
         "node_group": "majority"},
        {"type": "ADMIT", "source_id": ids["CORR"],
         "canonical_id": history["canonical_id"], "knowledge_time": 4,
         "effective_time": 2, "effect": "CORRECT", "text": texts["CORR"],
         "node_group": "majority"},
        {"type": "ADMIT", "source_id": ids["REPEAL"],
         "canonical_id": history["canonical_id"], "knowledge_time": 5,
         "effective_time": 5, "effect": "REPEAL", "text": None,
         "node_group": "majority"},
        {"type": "ADMIT", "source_id": ids["REVIVE"],
         "canonical_id": history["canonical_id"], "knowledge_time": 6,
         "effective_time": 6, "effect": "REVIVE", "text": None,
         "node_group": "majority"},
        {"type": "ADMIT", "source_id": ids["BASE"],
         "canonical_id": history["canonical_id"], "knowledge_time": 7,
         "effective_time": 1, "effect": "SET", "text": texts["CONFLICT"],
         "node_group": "majority"}]
    queries = [{"canonical_id": history["canonical_id"],
                "legal_time": legal, "knowledge_time": knowledge}
               for legal, knowledge in ((2, 3), (2, 5), (4, 5), (5, 6), (7, 7))]
    return _container(runtime, FORMAL_BOOTSTRAP,
                      {"source": source, "actions": actions, "queries": queries})


def _normalize_formal(result):
    rows = result.get("observations") or []
    if len(rows) != 5:
        raise RuntimeError("formal cross-model witness returned wrong observation count")
    status = lambda value: "ACTIVE" if value == "IN_FORCE" else value
    normalized = [{"status": status(row.get("status")), "text": row.get("text"),
                   "evidence": sorted(row.get("evidence_chain") or []),
                   "unresolved": sorted(row.get("unresolved") or [])} for row in rows]
    publication = result.get("publication") or {}
    if publication.get("canonical_root") != result.get("root"):
        raise RuntimeError("formal publication root diverged")
    return normalized


def _bundle(history, semantic):
    state = semantic["observations"]["post_amendment"]
    replay_root = semantic["replay"]["state_root"]
    token = history["token"]; cid = history["canonical_id"]
    work = "https://law.example/eli/nomos/2020/" + token[:8]
    expression = work + "/ell@2022-06-01"; manifestation = expression + "/json"
    version = cid + "@2021-01-01"
    evidence = [{"id": source_id,
                 "sha256": hashlib.sha256(source_id.encode()).hexdigest(),
                 "uri": "https://evidence.example/" + source_id}
                for source_id in state.get("evidence_chain") or []]
    return {"canonical_root": replay_root,
            "work": {"id": work, "title": "Νόμος " + token[:8], "jurisdiction": "GR"},
            "expression": {"id": expression, "version": "2022-06-01",
                           "language": "ell", "knowledge_time": "2022-06-01"},
            "manifestation": {"id": manifestation, "media_type": "application/json"},
            "provision": {"id": cid, "version_id": version, "eid": "art_1",
                          "number": "1", "text": state.get("text"),
                          "status": state.get("status"), "valid_from": "2021-01-01",
                          "valid_to": None},
            "impacts": [{"id": "IMP-" + history["ids"][name], "effect": effect,
                         "target_version_id": version, "effective_from": effective,
                         "source_id": history["ids"][name]}
                        for name, effect, effective in (
                            ("AMEND", "AMEND", "2021-01-01"),
                            ("CORR", "CORRECT", "2020-06-01"))],
            "decision": {"id": history["ids"]["DECISION"],
                         "ecli": "ECLI:GR:AREIOSPAGOS:2022:" + token[:6],
                         "legal_time": "2022-06-01",
                         "applicable_provision_version_id": version},
            "evidence": evidence,
            "doctrine": [{"id": history["ids"]["DOCTRINE"],
                          "proposition": "ερμηνευτική θέση", "binding": False}],
            "unknowns": []}


def _interop(source, bundle, runtime):
    return _container(runtime, INTEROP_BOOTSTRAP,
                      {"source": source, "bundle": bundle})


def _normalize_interop(output, bundle):
    common = []
    for key in ("human", "api", "public_sector", "ai"):
        row = output.get(key) or {}
        common.append((row.get("canonical_root"), row.get("work_id"),
                       row.get("expression_id"), row.get("manifestation_id"),
                       row.get("provision_id"), row.get("provision_version_id"),
                       row.get("status"), row.get("text")))
    if len(set(common)) != 1:
        raise RuntimeError("interoperability implementations contain channel-local legal states")
    expected = (bundle["canonical_root"], bundle["work"]["id"],
                bundle["expression"]["id"], bundle["manifestation"]["id"],
                bundle["provision"]["id"], bundle["provision"]["version_id"],
                bundle["provision"]["status"], bundle["provision"]["text"])
    if common[0] != expected:
        raise RuntimeError("interoperability projection disagrees with semantic legal state")
    return {"common": common[0],
            "eli_impacts": sorted((row.get("id"), row.get("effect"), row.get("target"),
                                   row.get("effective_from"), row.get("source_id"))
                                  for row in (output.get("eli") or {}).get("impacts", [])),
            "provenance_root": (output.get("provenance") or {}).get("canonical_root")}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--semantic", required=True)
    parser.add_argument("--formal", action="append", required=True)
    parser.add_argument("--interoperability", action="append", required=True)
    parser.add_argument("--seed", type=int, default=9902026)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    report = {"status": "FAIL", "passed": False, "seed": args.seed,
              "counterexamples": [], "root_algorithms_compared": False}
    try:
        if len(args.formal) != 2 or len(args.interoperability) != 2:
            raise RuntimeError("cross-model arena requires exactly two formal and two interoperability sources")
        runtime = container_runtime()
        if not runtime:
            raise RuntimeError("cross-model arena requires docker/podman")
        history = _history(args.seed)
        semantic = _semantic(open(args.semantic, encoding="utf-8").read(), history)
        formal_rows = [_formal(open(path, encoding="utf-8").read(), history, runtime)
                       for path in args.formal]
        formal_normalized = [_normalize_formal(row) for row in formal_rows]
        expected = [
            {"status": "ACTIVE", "text": history["texts"]["BASE"]},
            {"status": "ACTIVE", "text": history["texts"]["CORR"]},
            {"status": "ACTIVE", "text": history["texts"]["AMEND"]},
            {"status": "REPEALED", "text": None},
            {"status": "ACTIVE", "text": history["texts"]["AMEND"]}]
        for model in formal_normalized:
            for index, row in enumerate(model):
                if row["status"] != expected[index]["status"] \
                        or (expected[index]["text"] is not None
                            and row["text"] != expected[index]["text"]):
                    raise RuntimeError(f"formal model disagrees at cut {index}: {row}")
            if not model[-1]["unresolved"]:
                raise RuntimeError("formal model hid conflicting evidence")
        if _canon(formal_normalized[0]) != _canon(formal_normalized[1]):
            raise RuntimeError("independent formal models disagree on the shared witness")
        bundle = _bundle(history, semantic)
        interop_outputs = [_interop(open(path, encoding="utf-8").read(), bundle, runtime)
                           for path in args.interoperability]
        interop_normalized = [_normalize_interop(row, bundle) for row in interop_outputs]
        if _canon(interop_normalized[0]) != _canon(interop_normalized[1]):
            raise RuntimeError("independent interoperability implementations disagree")
        report.update({"status": "PASS", "passed": True,
                       "semantic_digest": _digest(semantic["observations"]),
                       "formal_digest": _digest(formal_normalized[0]),
                       "interoperability_digest": _digest(interop_normalized[0]),
                       "semantic_checks": semantic["checks"],
                       "formal_models": len(formal_rows),
                       "interoperability_implementations": len(interop_outputs),
                       "proof_boundary": (
                           "shared hidden legal-observation witness; unrelated root byte algorithms "
                           "are deliberately not equated")})
    except Exception as exc:
        report["reason"] = str(exc)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=1, sort_keys=True)
    print(json.dumps(report, ensure_ascii=False, indent=1))
    return 0 if report.get("passed") is True else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(json.dumps({"status": "FAIL", "passed": False,
                          "reason": str(exc)}, ensure_ascii=False, indent=1))
        sys.exit(1)
