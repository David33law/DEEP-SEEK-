"""Reference pure transition model for calibrating the Observatory formal arena.

It is intentionally small and generic. It proves that the bounded action algebra, bitemporal queries,
conflict observability and exhaustive-trace harness are executable; it is not a preferred production
architecture or an unbounded proof.
"""
import copy
import hashlib
import json

CANONICAL_AUTHORITY_SEAT = "evidence_set"
STATE_DERIVATION_MODEL = "replay_reducer"
TEMPORAL_MODEL = "bitemporal_intervals"
NORMATIVE_EFFECT_MODEL = "typed_directive_interpreter"
CONSISTENCY_COMMIT_MODEL = "single_writer_sequence"
REPLICATION_DISTRIBUTION_MODEL = "single_primary_read_replicas"
TRUSTED_CORE_TOPOLOGY = "state_machine_kernel"
CHANNELS = ["human", "api", "linked_data", "eli", "public_sector", "ai"]


def _canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def _hash(obj):
    return hashlib.sha256(_canonical(obj)).hexdigest()


def initial_state():
    return {
        "sources": {},
        "events": [],
        "unresolved": [],
        "pending": [],
        "partitioned": False,
        "crashed": False,
        "rule_version": "RULE-1",
    }


def _result(state, **kwargs):
    out = {
        "state": state,
        "accepted": False,
        "duplicate": False,
        "pending": False,
        "unresolved": False,
        "reason": "",
    }
    out.update(kwargs)
    return out


def transition(state, action):
    original = copy.deepcopy(state)
    next_state = copy.deepcopy(state)
    kind = str((action or {}).get("type") or "")

    if kind == "PARTITION":
        next_state["partitioned"] = True
        return _result(next_state, accepted=True, reason="partition-entered")
    if kind == "HEAL":
        next_state["partitioned"] = False
        return _result(next_state, accepted=True, reason="partition-healed")
    if kind == "CRASH":
        next_state["crashed"] = True
        return _result(next_state, accepted=True, reason="service-crashed")
    if kind == "RECOVER":
        next_state["crashed"] = False
        return _result(next_state, accepted=True, reason="service-recovered")
    if kind == "RULE_UPGRADE":
        version = str(action.get("rule_version") or "")
        if not version:
            return _result(original, reason="missing-rule-version")
        next_state["rule_version"] = version
        return _result(next_state, accepted=True, reason="rule-upgraded")
    if kind != "ADMIT":
        return _result(original, reason="unknown-action")

    if next_state.get("crashed"):
        return _result(original, reason="service-crashed")
    if next_state.get("partitioned") and action.get("node_group") == "minority":
        pending = copy.deepcopy(action)
        next_state["pending"].append(pending)
        return _result(next_state, pending=True, reason="minority-partition")

    source_id = str(action.get("source_id") or "")
    canonical_id = str(action.get("canonical_id") or "")
    effect = str(action.get("effect") or "")
    if not source_id or not canonical_id or effect not in {
            "SET", "AMEND", "CORRECT", "REPEAL", "REVIVE"}:
        return _result(original, reason="malformed-admission")
    existing = next_state["sources"].get(source_id)
    if existing is not None:
        if _canonical(existing) == _canonical(action):
            return _result(original, accepted=True, duplicate=True,
                           reason="duplicate")
        conflict = {
            "source_id": source_id,
            "canonical_id": canonical_id,
            "existing_sha256": _hash(existing),
            "conflicting_sha256": _hash(action),
        }
        if conflict not in next_state["unresolved"]:
            next_state["unresolved"].append(conflict)
        return _result(next_state, unresolved=True,
                       reason="conflicting-source-id")

    admitted = copy.deepcopy(action)
    next_state["sources"][source_id] = admitted
    next_state["events"].append(admitted)
    return _result(next_state, accepted=True, reason="admitted")


def _authority_view(state):
    return {
        "sources": {key: state["sources"][key]
                    for key in sorted(state.get("sources", {}))},
        "unresolved": sorted(state.get("unresolved", []),
                             key=lambda x: _canonical(x)),
        "rule_version": state.get("rule_version"),
    }


def state_root(state):
    return _hash(_authority_view(state))


def query(state, request):
    canonical_id = str((request or {}).get("canonical_id") or "")
    legal_time = int((request or {}).get("legal_time", -10**18))
    knowledge_time = int((request or {}).get("knowledge_time", -10**18))
    events = [event for event in state.get("events", [])
              if str(event.get("canonical_id")) == canonical_id
              and int(event.get("effective_time", 10**18)) <= legal_time
              and int(event.get("knowledge_time", 10**18)) <= knowledge_time]
    events.sort(key=lambda e: (int(e.get("effective_time", 0)),
                               int(e.get("knowledge_time", 0)),
                               str(e.get("source_id", ""))))
    status, text, last_text = "UNKNOWN", None, None
    evidence = []
    for event in events:
        effect = event.get("effect")
        evidence.append(str(event.get("source_id")))
        if effect in ("SET", "AMEND", "CORRECT"):
            text = event.get("text")
            if text is not None:
                last_text = text
            status = "IN_FORCE"
        elif effect == "REPEAL":
            status, text = "REPEALED", None
        elif effect == "REVIVE":
            status = "IN_FORCE"
            text = event.get("text") if event.get("text") is not None else last_text
            if text is not None:
                last_text = text
    unresolved = [
        "conflicting-source-id:" + row["source_id"]
        for row in state.get("unresolved", [])
        if row.get("canonical_id") == canonical_id
    ]
    return {
        "canonical_id": canonical_id,
        "status": status,
        "text": text,
        "legal_time": legal_time,
        "knowledge_time": knowledge_time,
        "evidence_chain": evidence,
        "unresolved": unresolved,
    }


def publication(state):
    root = state_root(state)
    return {"canonical_root": root,
            "channels": {channel: root for channel in CHANNELS}}


def model_manifest():
    return {
        "canonical_authority_seat": CANONICAL_AUTHORITY_SEAT,
        "state_derivation_model": STATE_DERIVATION_MODEL,
        "temporal_model": TEMPORAL_MODEL,
        "normative_effect_model": NORMATIVE_EFFECT_MODEL,
        "consistency_commit_model": CONSISTENCY_COMMIT_MODEL,
        "replication_distribution_model": REPLICATION_DISTRIBUTION_MODEL,
        "trusted_core_topology": TRUSTED_CORE_TOPOLOGY,
        "commutative_independent_admissions": True,
        "minority_partition_policy": "pending",
        "proof_boundary": (
            "bounded pure-state model of evidence admission, conflict, bitemporal effect, partition, "
            "crash/recovery, rule-version and publication invariants; not an unbounded implementation proof"),
    }
