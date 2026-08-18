#!/usr/bin/env python3
"""Trusted axis-specific behavioral probe arena for causal genome ablation.

This arena does not replace the semantic, durable, distributed, scale, formal or interoperability
campaigns. It supplies the missing causal attribution primitive: for one exact candidate source and
one controlled axis it executes a small hidden probe through the same container-isolated candidate
interface used by the corresponding full evaluator.

A report is evidence only when ``valid_execution`` is true. Missing container engines, parent timeout,
nonzero container transport exit, output flooding, host encoding/decoding failures and evaluator
defects are ``INVALID``. Candidate load/operation errors reached through the axis-specific probe are
valid behavioral failures. The orchestrator must compare an inert baseline control and the exact
load-bearing mutant under the same probe ID; this file alone never decides causal credit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import traceback
import xml.etree.ElementTree as ET

from candidate_host import container_runtime
import observatory_casegen as casegen
import observatory_harness as semantic_harness
import observatory_systems_arena as systems
import observatory_distributed_arena as distributed
import observatory_scale_arena as scale
import observatory_interoperability_arena as interop


CONTRACT = "observatory-axis-probe-v1"
FORMAL_IMAGE = "python:3.11-slim"
REQUIRED_CHANNELS = {"human", "api", "linked_data", "eli", "public_sector", "ai"}
GROUP_AXES = {
    "semantic": {
        "canonical_authority_seat", "evidence_primitive", "identity_model",
        "state_derivation_model", "temporal_model", "normative_effect_model",
        "provenance_proof_model", "publication_topology",
        "governance_evolution_model"},
    "systems": {"trusted_core_topology"},
    "distributed": {
        "consistency_commit_model", "replication_distribution_model"},
    "scale": {"scaling_partition_model"},
    "formal": {
        "canonical_authority_seat", "evidence_primitive", "identity_model",
        "state_derivation_model", "temporal_model", "normative_effect_model",
        "consistency_commit_model", "replication_distribution_model",
        "trusted_core_topology", "governance_evolution_model"},
    "interoperability": {
        "identity_model", "temporal_model", "normative_effect_model",
        "provenance_proof_model", "publication_topology"},
}
SEMANTIC_DIMENSIONS = {
    "canonical_authority_seat": (
        "canonical_identity_accuracy", "honest_unknown_rate",
        "publication_projection_consistency"),
    "evidence_primitive": (
        "source_coverage", "change_detection_recall", "provenance_completeness"),
    "identity_model": (
        "canonical_identity_accuracy", "jurisprudence_temporal_link_accuracy"),
    "state_derivation_model": (
        "replay_determinism", "recovery_success"),
    "temporal_model": (
        "temporal_reconstruction_accuracy", "jurisprudence_temporal_link_accuracy"),
    "normative_effect_model": ("normative_effect_accuracy",),
    "provenance_proof_model": ("provenance_completeness",),
    "publication_topology": ("publication_projection_consistency",),
}
_INFRASTRUCTURE_MARKERS = (
    "requires docker", "requires docker/podman", "container runtime unavailable",
    "no container runtime", "container exited", "failed or flooded output",
    "timed out", "timeoutexpired", "permission denied while trying to connect",
    "cannot connect to docker", "error during connect", "no such image",
    "manifest unknown", "out of memory", "oomkilled", "exit code 137",
    "unicodeencodeerror", "unicodedecodeerror", "charmap codec",
    "character maps to <undefined>",
)
_HOST_INFRASTRUCTURE_EXCEPTIONS = (
    UnicodeError,
    OSError,
    subprocess.SubprocessError,
)


def _sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"))


def _check(identifier, passed, detail=None):
    return {"id": identifier, "passed": bool(passed),
            "detail": detail if detail is not None else {}}


def _candidate_failure(exc):
    """Return True only when the failure is attributable to candidate behavior.

    Host process/pipe/codec failures are evaluator infrastructure and must never earn causal credit.
    The textual markers retain fail-closed handling for wrappers that normalize an infrastructure
    exception into RuntimeError before it reaches this classifier.
    """
    if isinstance(exc, _HOST_INFRASTRUCTURE_EXCEPTIONS):
        return False
    text = (type(exc).__name__ + ": " + str(exc)).lower()
    return not any(marker in text for marker in _INFRASTRUCTURE_MARKERS)


def _semantic_probe(source, axis, seed, runtime, _expected):
    if axis == "governance_evolution_model":
        host = semantic_harness.ObservatoryCandidateHost(
            source, backend="container", timeout=90)
        digest = hashlib.sha256(
            f"axis-governance|{seed}".encode()).hexdigest()
        kind = "AXIS_EXT_" + digest[:16].upper()
        marker = digest[16:32]
        event = {
            "source_id": "AXIS-SRC-" + digest[32:40],
            "canonical_id": "AXIS:GOVERNANCE",
            "target_id": "AXIS:GOVERNANCE",
            "knowledge_time": "2037-01-01",
            "effective_from": "2037-01-01",
        }
        response = host.extension_probe(kind, marker, event)
        result = response.get("result") if isinstance(response, dict) else None
        checks = [
            _check("extension-supported", isinstance(response, dict)
                   and response.get("supported") is True, response),
            _check("extension-accepted", isinstance(result, dict)
                   and result.get("accepted") is True, result),
            _check("extension-kind-preserved", isinstance(result, dict)
                   and result.get("change_type") == kind, result),
            _check("extension-marker-preserved", isinstance(result, dict)
                   and result.get("extension_marker") == marker, result),
        ]
        return checks, {"probe_family": "semantic-extension"}

    dimensions = SEMANTIC_DIMENSIONS[axis]
    seeds = [
        int(hashlib.sha256(
            f"semantic-axis|{axis}|{seed}|{index}".encode()).hexdigest()[:8], 16)
        for index in range(4)]
    suite = {
        "suite": "observatory-axis-semantic-hidden-v1",
        "seeds": seeds,
        "scenarios": [
            casegen.make_scenario(value, f"AXIS-{axis}-{index:02d}")
            for index, value in enumerate(seeds)],
    }
    report = semantic_harness.run_suite(
        source, suite, backend="container", timeout=90)
    scores = report.get("dimension_scores") or {}
    checks = [
        _check("semantic-dimension:" + dimension,
               float(scores.get(dimension, 0.0)) >= 1.0,
               {"score": scores.get(dimension), "required": 1.0})
        for dimension in dimensions]
    checks.append(_check(
        "semantic-probe-executed",
        len(report.get("scenario_statuses") or []) == len(seeds),
        {"scenario_statuses": report.get("scenario_statuses")}))
    return checks, {
        "probe_family": "semantic-hidden-scenarios",
        "dimension_scores": {key: scores.get(key) for key in dimensions},
        "scenario_statuses": report.get("scenario_statuses") or [],
    }


def _systems_probe(source, _axis, seed, runtime, _expected):
    temp = tempfile.mkdtemp(prefix="obs-axis-systems-")
    try:
        state = os.path.join(temp, "state")
        events = systems._events(96, seed)
        replies = systems._session(
            runtime, source, state,
            [{"op": "ingest_batch", "events": events},
             {"op": "state_root"}, {"op": "integrity_check"},
             {"op": "publish_probe"}, {"op": "durability_manifest"},
             {"op": "close"}], timeout=180)
        root = systems._result(replies, "state_root")
        integrity = systems._result(replies, "integrity_check")
        publication = systems._result(replies, "publish_probe")
        manifest = systems._result(replies, "durability_manifest")
        reopened_root, reopened_integrity, reopened_publication = systems._root(
            runtime, source, state)
        checks = [
            _check("durable-root", isinstance(root, str) and bool(root), root),
            _check("durable-integrity", isinstance(integrity, dict)
                   and integrity.get("ok") is True, integrity),
            _check("durable-publication-root", isinstance(publication, dict)
                   and publication.get("canonical_root") == root, publication),
            _check("durable-publication-channels", isinstance(publication, dict)
                   and REQUIRED_CHANNELS.issubset(
                       set(publication.get("channels") or [])), publication),
            _check("durable-manifest-authority", isinstance(manifest, dict)
                   and bool(manifest.get("authority_files")), manifest),
            _check("durable-restart-root", reopened_root == root,
                   {"before": root, "after": reopened_root}),
            _check("durable-restart-integrity", isinstance(reopened_integrity, dict)
                   and reopened_integrity.get("ok") is True, reopened_integrity),
            _check("durable-restart-publication",
                   isinstance(reopened_publication, dict)
                   and reopened_publication.get("canonical_root") == root,
                   reopened_publication),
        ]
        return checks, {"probe_family": "durable-trusted-core"}
    finally:
        shutil.rmtree(temp, ignore_errors=True)


def _distributed_probe(source, axis, seed, runtime, expected):
    temp = tempfile.mkdtemp(prefix="obs-axis-distributed-")
    try:
        state = os.path.join(temp, "cluster")
        replication_model = expected.get("replication_distribution_model")
        commit_model = expected.get("consistency_commit_model")
        manifest = distributed._manifest(
            runtime, source, state, replication_model, commit_model)
        baseline = distributed._events(64, seed, "AXIS-DIST")
        first = distributed._session(
            runtime, source, state,
            [{"op": "ingest_batch", "node_id": "n1", "events": baseline},
             {"op": "integrity"}, {"op": "roots"}, {"op": "close"}],
            timeout=240)
        root = distributed._canonical_root(
            distributed._result(first, "integrity"))
        roots = distributed._result(first, "roots")
        baseline_converged = distributed._roots_converged(roots, root)

        if axis == "consistency_commit_model":
            minority_event = distributed._events(
                1, seed + 1, "AXIS-MINORITY")[0]
            majority_event = distributed._events(
                1, seed + 2, "AXIS-MAJORITY")[0]
            partition = distributed._session(
                runtime, source, state,
                [{"op": "partition",
                  "groups": [["n1", "n2", "n3"], ["n4", "n5"]]},
                 {"op": "submit", "node_id": "n4", "event": minority_event},
                 {"op": "submit", "node_id": "n1", "event": majority_event},
                 {"op": "heal"}, {"op": "integrity"},
                 {"op": "roots"}, {"op": "close"}], timeout=240)
            minority = distributed._result(partition, "submit", 0)
            majority = distributed._result(partition, "submit", 1)
            healed_root = distributed._canonical_root(
                distributed._result(partition, "integrity"))
            below = distributed._session(
                runtime, source, state,
                [{"op": "crash", "node_id": "n1"},
                 {"op": "crash", "node_id": "n2"},
                 {"op": "crash", "node_id": "n3"},
                 {"op": "submit", "node_id": "n4",
                  "event": distributed._events(
                      1, seed + 3, "AXIS-NOQUORUM")[0]},
                 {"op": "restart", "node_id": "n1"},
                 {"op": "restart", "node_id": "n2"},
                 {"op": "restart", "node_id": "n3"},
                 {"op": "heal"}, {"op": "integrity"},
                 {"op": "close"}], timeout=240)
            no_quorum = distributed._result(below, "submit")
            checks = [
                _check("commit-manifest", manifest.get("commit_model") == commit_model,
                       manifest),
                _check("commit-baseline-convergence", baseline_converged),
                _check("commit-minority-rejected",
                       not distributed._accepted(minority), minority),
                _check("commit-majority-accepted",
                       distributed._accepted(majority), majority),
                _check("commit-heal-root", bool(healed_root), healed_root),
                _check("commit-below-quorum-rejected",
                       not distributed._accepted(no_quorum), no_quorum),
            ]
            return checks, {"probe_family": "distributed-commit"}

        fault = distributed._session(
            runtime, source, state,
            [{"op": "crash", "node_id": "n5"}, {"op": "roots"},
             {"op": "restart", "node_id": "n5"}, {"op": "heal"},
             {"op": "integrity"}, {"op": "roots"}, {"op": "close"}],
            timeout=240)
        crashed = distributed._result(fault, "roots", 0)
        recovered_root = distributed._canonical_root(
            distributed._result(fault, "integrity"))
        recovered_roots = distributed._result(fault, "roots", 1)
        checks = [
            _check("replication-manifest",
                   manifest.get("replication_model") == replication_model,
                   manifest),
            _check("replication-baseline-convergence", baseline_converged,
                   {"root": root, "roots": roots}),
            _check("replication-crash-observed",
                   isinstance(crashed, dict) and crashed.get("n5") == "CRASHED",
                   crashed),
            _check("replication-restart-convergence",
                   distributed._roots_converged(
                       recovered_roots, recovered_root),
                   {"root": recovered_root, "roots": recovered_roots}),
        ]
        return checks, {"probe_family": "distributed-replication"}
    finally:
        shutil.rmtree(temp, ignore_errors=True)


def _scale_probe(source, _axis, seed, runtime, expected):
    temp = tempfile.mkdtemp(prefix="obs-axis-scale-")
    try:
        model = expected.get("scaling_partition_model")
        partitions = 1 if model == "single_node_scale_up" else 4
        state = os.path.join(temp, "scale")
        manifest = scale._manifest(
            runtime, source, state, partitions, model)
        events = [scale._event(index, 256, seed, "AXIS-SCALE")
                  for index in range(256)]
        commands = [
            {"op": "ingest_batch", "events": events[index:index + 64]}
            for index in range(0, len(events), 64)]
        commands.extend([
            {"op": "state_root"}, {"op": "integrity_check"},
            {"op": "partition_roots"}, {"op": "publish_probe"},
            {"op": "checkpoint"}, {"op": "close"}])
        replies = scale._run_commands(
            runtime, source, state, partitions, commands, timeout=300)
        root = scale._root(scale._result(replies, "state_root"))
        integrity = scale._integrity(
            scale._result(replies, "integrity_check"))
        partition_roots = scale._result(replies, "partition_roots")
        publication = scale._result(replies, "publish_probe")
        accepted = sum(
            int((row.get("result") or {}).get("accepted", 0))
            for row in replies
            if row.get("op") == "ingest_batch" and row.get("ok"))
        restarted = scale._run_commands(
            runtime, source, state, partitions,
            [{"op": "state_root"}, {"op": "integrity_check"},
             {"op": "partition_roots"}, {"op": "close"}], timeout=180)
        root_after = scale._root(scale._result(restarted, "state_root"))
        partition_after = scale._result(restarted, "partition_roots")
        expected_partition_count = int(manifest.get("partition_count", 0))
        checks = [
            _check("scale-manifest-model",
                   manifest.get("scaling_partition_model") == model, manifest),
            _check("scale-events-accepted", accepted == len(events),
                   {"accepted": accepted, "expected": len(events)}),
            _check("scale-root", bool(root), root),
            _check("scale-integrity", integrity.get("ok") is True, integrity),
            _check("scale-partition-count", isinstance(partition_roots, dict)
                   and len(partition_roots) == expected_partition_count,
                   partition_roots),
            _check("scale-publication",
                   scale._publication_ok(publication, root), publication),
            _check("scale-restart-root", root_after == root,
                   {"before": root, "after": root_after}),
            _check("scale-restart-partitions", partition_after == partition_roots,
                   {"before": partition_roots, "after": partition_after}),
        ]
        return checks, {"probe_family": "scale-partition"}
    finally:
        shutil.rmtree(temp, ignore_errors=True)


FORMAL_PROBE = r'''
import copy, hashlib, json, sys, traceback
req=json.loads(sys.stdin.read()); source=req["source"]; expected=req["expected"]
axis=req["axis"]; seed=int(req["seed"]); ns={"__name__":"__candidate__"}
out={"valid_execution":True,"checks":[],"detail":{}}
def check(name,value,detail=None):
 out["checks"].append({"id":name,"passed":bool(value),"detail":detail or {}})
def admit(sid,cid,k,e,effect,text=None,group="majority"):
 return {"type":"ADMIT","source_id":sid,"canonical_id":cid,
         "knowledge_time":k,"effective_time":e,"effect":effect,
         "text":text,"node_group":group}
try:
 exec(compile(source,"<axis-formal-candidate>","exec"),ns,ns)
 required=["initial_state","transition","state_root","query","publication","model_manifest"]
 missing=[name for name in required if not callable(ns.get(name))]
 if missing: raise RuntimeError("missing functions: "+", ".join(missing))
 initial_state=ns["initial_state"]; transition=ns["transition"]
 state_root=ns["state_root"]; query=ns["query"]
 publication=ns["publication"]; manifest=ns["model_manifest"]()
 check("manifest-axis",isinstance(manifest,dict) and manifest.get(axis)==expected.get(axis),
       {"observed":manifest.get(axis) if isinstance(manifest,dict) else None,
        "expected":expected.get(axis)})
 token=hashlib.sha256(f"{axis}|{seed}".encode()).hexdigest()
 A="AXIS-A-"+token[:8]; B="AXIS-B-"+token[8:16]
 SA="AXIS-SA-"+token[16:24]; SB="AXIS-SB-"+token[24:32]
 t0=token[32:40]; t1=token[40:48]; t2=token[48:56]
 def step(state,action):
  result=transition(copy.deepcopy(state),copy.deepcopy(action))
  if not isinstance(result,dict) or not isinstance(result.get("state"),dict):
   raise RuntimeError("malformed transition result")
  return result
 if axis=="canonical_authority_seat":
  state=initial_state(); first=step(state,admit(SA,A,1,1,"SET",t0)); state=first["state"]
  conflict=step(state,admit(SA,A,1,1,"SET",t1)); state=conflict["state"]
  q=query(copy.deepcopy(state),{"canonical_id":A,"legal_time":10,"knowledge_time":10})
  check("authority-first-admitted",first.get("accepted") is True,first)
  check("authority-conflict-unresolved",conflict.get("unresolved") is True,conflict)
  check("authority-not-overwritten",isinstance(q,dict) and q.get("text")==t0,q)
  check("authority-conflict-observable",isinstance(q,dict) and bool(q.get("unresolved")),q)
 elif axis=="evidence_primitive":
  state=initial_state(); first=step(state,admit(SA,A,1,1,"SET",t0)); state=first["state"]
  before=state_root(copy.deepcopy(state)); dup=step(state,admit(SA,A,1,1,"SET",t0));
  after=state_root(copy.deepcopy(dup["state"])); q=query(copy.deepcopy(state),
      {"canonical_id":A,"legal_time":10,"knowledge_time":10})
  check("evidence-admitted",first.get("accepted") is True,first)
  check("evidence-chain",isinstance(q,dict) and SA in (q.get("evidence_chain") or []),q)
  check("evidence-duplicate",dup.get("duplicate") is True,dup)
  check("evidence-duplicate-root",before==after,{"before":before,"after":after})
 elif axis=="identity_model":
  state=initial_state()
  for event in (admit(SA,A,1,1,"SET",t0),admit(SB,B,1,1,"SET",t1)):
   state=step(state,event)["state"]
  qa=query(copy.deepcopy(state),{"canonical_id":A,"legal_time":10,"knowledge_time":10})
  qb=query(copy.deepcopy(state),{"canonical_id":B,"legal_time":10,"knowledge_time":10})
  check("identity-a",isinstance(qa,dict) and qa.get("canonical_id")==A and qa.get("text")==t0,qa)
  check("identity-b",isinstance(qb,dict) and qb.get("canonical_id")==B and qb.get("text")==t1,qb)
  check("identity-distinct",qa.get("canonical_id")!=qb.get("canonical_id"),{"a":qa,"b":qb})
 elif axis=="state_derivation_model":
  state=initial_state(); action=admit(SA,A,1,1,"SET",t0)
  one=step(state,action); two=step(state,action)
  check("derivation-deterministic",json.dumps(one,sort_keys=True)==json.dumps(two,sort_keys=True))
  state=one["state"]; before=state_root(copy.deepcopy(state)); dup=step(state,action)
  check("derivation-duplicate-root",state_root(copy.deepcopy(dup["state"]))==before)
  s1=initial_state(); s1=step(s1,action)["state"]; s1=step(s1,admit(SB,B,1,1,"SET",t1))["state"]
  s2=initial_state(); s2=step(s2,admit(SB,B,1,1,"SET",t1))["state"]; s2=step(s2,action)["state"]
  check("derivation-order",state_root(s1)==state_root(s2),{"root_ab":state_root(s1),"root_ba":state_root(s2)})
 elif axis=="temporal_model":
  state=initial_state()
  for event in (admit(SA,A,1,1,"SET",t0),admit(SA+"-AM",A,3,3,"AMEND",t1),
                admit(SA+"-CO",A,5,2,"CORRECT",t2)):
   state=step(state,event)["state"]
  q24=query(copy.deepcopy(state),{"canonical_id":A,"legal_time":2,"knowledge_time":4})
  q26=query(copy.deepcopy(state),{"canonical_id":A,"legal_time":2,"knowledge_time":6})
  q44=query(copy.deepcopy(state),{"canonical_id":A,"legal_time":4,"knowledge_time":4})
  q46=query(copy.deepcopy(state),{"canonical_id":A,"legal_time":4,"knowledge_time":6})
  check("temporal-bitemporal",q24.get("text")==t0 and q26.get("text")==t2
        and q44.get("text")==t1 and q46.get("text")==t1,
        {"q24":q24,"q26":q26,"q44":q44,"q46":q46})
 elif axis=="normative_effect_model":
  state=initial_state()
  for event in (admit(SA,A,1,1,"SET",t0),admit(SA+"-R",A,2,2,"REPEAL"),
                admit(SA+"-V",A,3,3,"REVIVE")):
   state=step(state,event)["state"]
  repealed=query(copy.deepcopy(state),{"canonical_id":A,"legal_time":2,"knowledge_time":10})
  revived=query(copy.deepcopy(state),{"canonical_id":A,"legal_time":4,"knowledge_time":10})
  check("effect-repeal",repealed.get("status")=="REPEALED",repealed)
  check("effect-revival",revived.get("status")=="IN_FORCE" and revived.get("text")==t0,revived)
 elif axis=="consistency_commit_model":
  state=initial_state(); state=step(state,{"type":"PARTITION"})["state"]
  minority=step(state,admit(SA,A,1,1,"SET",t0,"minority"))
  majority=step(minority["state"],admit(SB,B,1,1,"SET",t1,"majority"))
  check("commit-minority-not-accepted",minority.get("accepted") is not True,minority)
  check("commit-majority-accepted",majority.get("accepted") is True,majority)
 elif axis=="replication_distribution_model":
  state=initial_state(); state=step(state,admit(SA,A,1,1,"SET",t0))["state"]
  root=state_root(copy.deepcopy(state)); crashed=step(state,{"type":"CRASH"})
  denied=step(crashed["state"],admit(SB,B,2,2,"SET",t1))
  recovered=step(denied["state"],{"type":"RECOVER"})
  check("replication-crash-root",state_root(crashed["state"])==root)
  check("replication-admission-denied",denied.get("accepted") is not True,denied)
  check("replication-recovery-root",state_root(recovered["state"])==root)
 elif axis=="trusted_core_topology":
  state=initial_state(); root1=state_root(copy.deepcopy(state)); root2=state_root(copy.deepcopy(state))
  pub=publication(copy.deepcopy(state)); channels=pub.get("channels") if isinstance(pub,dict) else None
  check("trusted-root-deterministic",isinstance(root1,str) and root1 and root1==root2)
  check("trusted-publication-root",isinstance(pub,dict) and pub.get("canonical_root")==root1,pub)
  check("trusted-publication-channels",isinstance(channels,dict) and
        all(channels.get(name)==root1 for name in ("human","api","linked_data","eli","public_sector","ai")),channels)
  check("trusted-proof-boundary",isinstance(manifest,dict) and bool(manifest.get("proof_boundary")),manifest)
 elif axis=="governance_evolution_model":
  state=initial_state(); state=step(state,admit(SA,A,1,1,"SET",t0))["state"]
  before=query(copy.deepcopy(state),{"canonical_id":A,"legal_time":10,"knowledge_time":10})
  upgraded=step(state,{"type":"RULE_UPGRADE","rule_version":"AXIS-RULE-"+token[:8]})
  after=query(copy.deepcopy(upgraded["state"],{"canonical_id":A,"legal_time":10,"knowledge_time":10})
  check("governance-upgrade-accepted",upgraded.get("accepted") is True,upgraded)
  check("governance-nonretroactive",(before.get("status"),before.get("text"),before.get("evidence_chain"))==
        (after.get("status"),after.get("text"),after.get("evidence_chain")),{"before":before,"after":after})
 else: raise RuntimeError("unsupported formal axis: "+axis)
 out["passed"]=bool(out["checks"]) and all(row["passed"] for row in out["checks"])
except BaseException as exc:
 out["passed"]=False; out["failure_origin"]="candidate_axis_behavior"
 out["reason"]=type(exc).__name__+": "+str(exc)
 out["traceback"]=traceback.format_exc()[-4000:]
print(json.dumps(out,ensure_ascii=False,sort_keys=True))
'''


def _formal_probe(source, axis, seed, runtime, expected):
    payload = json.dumps({
        "source": source, "axis": axis, "seed": seed,
        "expected": expected}, ensure_ascii=False)
    command = [
        runtime, "run", "--rm", "-i", "--network=none", "--read-only",
        "--tmpfs", "/tmp:size=128m", "--memory=1g", "--pids-limit=64",
        "--cap-drop=ALL", "--security-opt", "no-new-privileges",
        "-w", "/tmp", FORMAL_IMAGE, "python3", "-I", "-S", "-B",
        "-c", FORMAL_PROBE]
    process = subprocess.run(
        command, input=payload, capture_output=True, text=True, timeout=240)
    if process.returncode != 0:
        raise RuntimeError(
            f"formal axis-probe container exited {process.returncode}: "
            + process.stderr[-1000:])
    rows = [line for line in process.stdout.splitlines() if line.strip()]
    if not rows:
        raise RuntimeError("formal axis-probe candidate produced no result")
    result = json.loads(rows[-1])
    if result.get("valid_execution") is not True:
        raise RuntimeError("formal axis-probe did not execute validly")
    return result.get("checks") or [], {
        "probe_family": "formal-axis-transition",
        "candidate_reason": result.get("reason"),
        "candidate_traceback": result.get("traceback"),
    }


def _xml_names(xml_text):
    root = ET.fromstring(xml_text)
    return root, {node.tag.split("}")[-1] for node in root.iter()}


def _interoperability_probe(source, axis, seed, runtime, expected):
    manifest = interop._call(runtime, source, "manifest")
    if not isinstance(manifest, dict):
        raise RuntimeError("interoperability manifest must return an object")
    bundle = interop._bundle(seed % 31, seed)
    first = interop._call(runtime, source, "project", bundle)
    second = interop._call(runtime, source, "project", bundle)
    checks = [
        _check("interop-manifest-axis", manifest.get(axis) == expected.get(axis),
               {"observed": manifest.get(axis), "expected": expected.get(axis)}),
        _check("interop-deterministic", _canonical(first) == _canonical(second)),
    ]
    root = bundle["canonical_root"]
    provision = bundle["provision"]
    work = bundle["work"]["id"]
    expression = bundle["expression"]["id"]
    manifestation = bundle["manifestation"]["id"]
    version = provision["version_id"]

    if axis == "identity_model":
        for key in ("human", "api", "public_sector", "ai"):
            value = first.get(key) or {}
            checks.append(_check(
                "identity-common-" + key,
                value.get("work_id") == work
                and value.get("expression_id") == expression
                and value.get("manifestation_id") == manifestation
                and value.get("provision_version_id") == version, value))
        graph = (first.get("linked_data") or {}).get("@graph") or []
        ids = {row.get("@id") for row in graph if isinstance(row, dict)}
        checks.append(_check("identity-linked-data",
                             {work, expression, manifestation, version}.issubset(ids),
                             {"ids": sorted(str(value) for value in ids)}))
        eli = first.get("eli") or {}
        checks.append(_check(
            "identity-eli",
            (eli.get("legal_resource") or {}).get("@id") == work
            and (eli.get("legal_expression") or {}).get("@id") == expression
            and (eli.get("manifestation") or {}).get("@id") == manifestation,
            eli))
    elif axis == "temporal_model":
        expected_temporal = {
            "valid_from": provision["valid_from"],
            "valid_to": provision.get("valid_to"),
            "knowledge_time": bundle["expression"]["knowledge_time"],
        }
        for key in ("human", "api", "public_sector", "ai"):
            value = first.get(key) or {}
            checks.append(_check(
                "temporal-common-" + key,
                all(value.get(field) == expected_value
                    for field, expected_value in expected_temporal.items()), value))
        eli_provision = (first.get("eli") or {}).get("provision") or {}
        checks.append(_check(
            "temporal-eli",
            eli_provision.get("valid_from") == provision["valid_from"]
            and eli_provision.get("valid_to") == provision.get("valid_to"),
            eli_provision))
        lrml, _names = _xml_names(first.get("legalruleml"))
        temporal = [node for node in lrml.iter()
                    if node.tag.endswith("TemporalCharacteristic")]
        checks.append(_check(
            "temporal-legalruleml", len(temporal) == 1
            and temporal[0].attrib.get("effectiveFrom") == provision["valid_from"]
            and temporal[0].attrib.get("knowledgeTime")
            == bundle["expression"]["knowledge_time"],
            [node.attrib for node in temporal]))
    elif axis == "normative_effect_model":
        expected_impacts = sorted((
            row["id"], row["effect"], row["target_version_id"],
            row["effective_from"], row["source_id"])
            for row in bundle["impacts"])
        eli_impacts = sorted((
            row.get("id"), row.get("effect"), row.get("target"),
            row.get("effective_from"), row.get("source_id"))
            for row in (first.get("eli") or {}).get("impacts", []))
        checks.append(_check("effect-eli", eli_impacts == expected_impacts,
                             {"observed": eli_impacts,
                              "expected": expected_impacts}))
        linked = (first.get("linked_data") or {}).get("@graph") or []
        linked_impacts = [row for row in linked
                          if row.get("@type") == "obs:NormativeImpact"]
        checks.append(_check("effect-linked-data",
                             len(linked_impacts) == len(expected_impacts),
                             linked_impacts))
        _akn, akn_names = _xml_names(first.get("akoma_ntoso"))
        _lrml, lrml_names = _xml_names(first.get("legalruleml"))
        checks.append(_check("effect-akoma-ntoso", "textualMod" in akn_names,
                             sorted(akn_names)))
        checks.append(_check("effect-legalruleml", "Association" in lrml_names,
                             sorted(lrml_names)))
    elif axis == "provenance_proof_model":
        provenance = first.get("provenance") or {}
        entities = {row.get("id"): row.get("sha256")
                    for row in provenance.get("entities", [])}
        expected_evidence = {row["id"]: row["sha256"]
                             for row in bundle["evidence"]}
        used = {row.get("used")
                for row in provenance.get("wasDerivedFrom", [])}
        checks.append(_check("provenance-root",
                             provenance.get("canonical_root") == root,
                             provenance))
        checks.append(_check("provenance-entities",
                             all(entities.get(key) == value
                                 for key, value in expected_evidence.items()),
                             entities))
        checks.append(_check("provenance-derivations",
                             set(expected_evidence).issubset(used),
                             {"used": sorted(str(value) for value in used)}))
    elif axis == "publication_topology":
        checks.append(_check("publication-outputs",
                             set(first) == interop.REQUIRED_OUTPUTS,
                             {"outputs": sorted(first)}))
        for key in ("human", "api", "public_sector", "ai",
                    "linked_data", "eli", "provenance"):
            value = first.get(key) or {}
            checks.append(_check(
                "publication-root-" + key,
                value.get("canonical_root") == root, value))
        checks.append(_check("publication-xml-akoma",
                             isinstance(first.get("akoma_ntoso"), str)
                             and bool(first.get("akoma_ntoso"))))
        checks.append(_check("publication-xml-legalruleml",
                             isinstance(first.get("legalruleml"), str)
                             and bool(first.get("legalruleml"))))
    else:
        raise RuntimeError("unsupported interoperability axis: " + axis)
    return checks, {"probe_family": "interoperability-projection"}


PROBES = {
    "semantic": _semantic_probe,
    "systems": _systems_probe,
    "distributed": _distributed_probe,
    "scale": _scale_probe,
    "formal": _formal_probe,
    "interoperability": _interoperability_probe,
}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--group", choices=tuple(sorted(GROUP_AXES)), required=True)
    parser.add_argument("--axis", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--expected-json", default="{}")
    args = parser.parse_args(argv)

    source_path = os.path.abspath(args.candidate)
    report = {
        "contract": CONTRACT,
        "status": "INVALID",
        "passed": False,
        "valid_execution": False,
        "failure_origin": "infrastructure_or_harness",
        "group": args.group,
        "axis": args.axis,
        "probe_id": f"{CONTRACT}:{args.group}:{args.axis}",
        "seed": args.seed,
        "candidate_path": source_path,
        "candidate_sha256": None,
        "checks": [],
    }
    exit_code = 2
    try:
        if args.axis not in GROUP_AXES[args.group]:
            raise RuntimeError(
                f"axis {args.axis!r} is not valid for group {args.group!r}")
        if not os.path.isfile(source_path):
            raise RuntimeError("axis-probe candidate source is missing")
        report["candidate_sha256"] = _sha256_file(source_path)
        expected = json.loads(args.expected_json)
        if not isinstance(expected, dict):
            raise RuntimeError("axis-probe expected-json must be an object")
        report["expected_sha256"] = hashlib.sha256(
            _canonical(expected).encode("utf-8")).hexdigest()
        runtime = container_runtime()
        if not runtime:
            raise RuntimeError("axis-probe arena requires docker/podman")
        source = open(source_path, encoding="utf-8").read()
        try:
            checks, detail = PROBES[args.group](
                source, args.axis, args.seed, runtime, expected)
        except subprocess.TimeoutExpired:
            raise
        except Exception as exc:
            if not _candidate_failure(exc):
                raise
            checks = [_check(
                "axis-probe-candidate-operation", False,
                {"error": type(exc).__name__ + ": " + str(exc)})]
            detail = {
                "candidate_exception": type(exc).__name__ + ": " + str(exc),
                "candidate_traceback": traceback.format_exc()[-4000:],
            }
        passed = bool(checks) and all(row.get("passed") is True for row in checks)
        report.update({
            "status": "PASS" if passed else "FAIL",
            "passed": passed,
            "valid_execution": True,
            "failure_origin": "none" if passed else "candidate_axis_behavior",
            "checks": checks,
            "detail": detail,
            "runtime": runtime,
            "backend": "container",
            "proof_boundary": (
                "one bounded hidden axis probe over exact candidate bytes; causal credit "
                "requires an independently passing inert control and failing mutant under "
                "the same probe ID"),
        })
        exit_code = 0 if passed else 1
    except subprocess.TimeoutExpired as exc:
        report["reason"] = "axis-probe parent timeout: " + str(exc)
    except Exception as exc:
        report["reason"] = type(exc).__name__ + ": " + str(exc)
        report["traceback"] = traceback.format_exc()[-4000:]
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=1, sort_keys=True)
    # stdout is diagnostic transport, not the canonical report. Keep it ASCII-only so a Windows
    # parent with a legacy console code page cannot fail while decoding evaluator diagnostics.
    print(json.dumps(report, ensure_ascii=True, indent=1, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
