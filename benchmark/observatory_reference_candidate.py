"""Reference implementation for the VISIBLE National Observatory replay suite.

Calibration only. This proves the evaluator can recognise the minimum semantic contract; it is
not an architecture candidate for the tournament and is never copied into builder prompts.
"""
import hashlib
import json

_sources = []
_changes = []
_doctrine = []
_conflicts = []
_custom_handlers = {}
_seen_semantic = set()


def _time_le(a, b):
    return bool(a) and bool(b) and str(a) <= str(b)


def _semantic_key(source):
    return (source.get("kind"), source.get("canonical_id"), source.get("target_id"),
            source.get("effective_from"), source.get("effective_to"), source.get("text"))


def register_change_handler(kind, fn):
    if not isinstance(kind, str) or not kind or not callable(fn):
        raise ValueError("invalid change-handler registration")
    _custom_handlers[kind] = fn
    return True


def ingest(source):
    kind = source.get("kind")
    cid = source.get("canonical_id", "")
    sid = source.get("source_id", "")
    if kind == "CONFLICTING_SOURCE":
        _conflicts.append(dict(source))
        return {"accepted": False, "canonical_id": cid, "evidence_id": sid,
                "deduplicated": False, "unresolved": [f"conflict:{sid}"]}
    key = _semantic_key(source)
    duplicate = key in _seen_semantic
    if not duplicate:
        _seen_semantic.add(key)
        _sources.append(dict(source))
    return {"accepted": True, "canonical_id": cid, "evidence_id": sid,
            "deduplicated": duplicate, "unresolved": []}


def apply_change(event):
    kind = event.get("kind", "")
    if kind in _custom_handlers:
        return _custom_handlers[kind](dict(event))
    if kind not in {"AMENDMENT", "CORRECTION", "SUSPENSION", "REVIVAL", "REPEAL"}:
        return {"accepted": False, "target_id": event.get("target_id", ""),
                "change_type": kind, "unresolved": [f"unknown-change:{kind}"]}
    _changes.append(dict(event))
    return {"accepted": True, "target_id": event.get("target_id", event.get("canonical_id", "")),
            "change_type": kind, "unresolved": []}


def _applicable(records, cid, legal_time, knowledge_time):
    out = []
    for e in records:
        ecid = e.get("canonical_id") or e.get("target_id")
        if ecid != cid:
            continue
        if not _time_le(e.get("knowledge_time") or e.get("publication_time"), knowledge_time):
            continue
        eff = e.get("effective_from") or e.get("publication_time")
        if eff and not _time_le(eff, legal_time):
            continue
        out.append(e)
    return out


def _state(query):
    cid = query.get("canonical_id", "")
    legal_time = query.get("legal_time", "")
    knowledge_time = query.get("knowledge_time", "")
    base = _applicable(_sources, cid, legal_time, knowledge_time)
    changes = _applicable(_changes, cid, legal_time, knowledge_time)
    ordered = base + changes
    ordered.sort(key=lambda e: (e.get("effective_from") or e.get("publication_time") or "",
                                e.get("knowledge_time") or e.get("publication_time") or "",
                                {"LEGISLATION": 0, "AMENDMENT": 1, "CORRECTION": 2,
                                 "SUSPENSION": 3, "REVIVAL": 4, "REPEAL": 5}.get(e.get("kind"), 9)))
    text = None
    status = "UNKNOWN"
    chain = []
    for e in ordered:
        kind = e.get("kind")
        if kind in ("LEGISLATION", "AMENDMENT", "CORRECTION"):
            text = e.get("text")
            status = "ACTIVE"
        elif kind == "SUSPENSION" and text is not None:
            status = "SUSPENDED"
        elif kind == "REVIVAL" and text is not None:
            status = "ACTIVE"
        elif kind == "REPEAL" and text is not None:
            status = "REPEALED"
        sid = e.get("source_id")
        if sid and sid not in chain:
            chain.append(sid)

    unresolved = []
    for c in _conflicts:
        if (c.get("canonical_id") == cid
                and _time_le(c.get("knowledge_time") or c.get("publication_time"), knowledge_time)
                and _time_le(c.get("effective_from") or c.get("publication_time"), legal_time)):
            unresolved.append(f"conflict:{c.get('source_id')}")
    if unresolved:
        status = "CONFLICT"
    return {"canonical_id": cid, "status": status, "text": text,
            "legal_time": legal_time, "knowledge_time": knowledge_time,
            "evidence_chain": chain, "unresolved": unresolved}


def state_at(query):
    return _state(query)


def link_jurisprudence(decision):
    links, unresolved = [], []
    legal_time = decision.get("decision_time", "")
    knowledge_time = decision.get("knowledge_time", legal_time)
    for cid in decision.get("applies", []):
        s = _state({"canonical_id": cid, "legal_time": legal_time,
                    "knowledge_time": knowledge_time})
        if s["status"] in ("UNKNOWN", "CONFLICT") or not s["evidence_chain"]:
            unresolved.append(cid)
            continue
        links.append({"canonical_id": cid, "version_evidence_id": s["evidence_chain"][-1]})
    return {"decision_id": decision.get("decision_id", decision.get("source_id", "")),
            "links": links, "unresolved": unresolved}


def attach_doctrine(document):
    _doctrine.append(dict(document))
    return {"doctrine_id": document.get("doctrine_id", document.get("source_id", "")),
            "epistemic_type": "DOCTRINE", "changes_binding_state": False,
            "links": list(document.get("links", []))}


def provenance(query):
    s = _state(query)
    return {"canonical_id": s["canonical_id"], "evidence_chain": s["evidence_chain"],
            "complete": s["status"] not in ("UNKNOWN", "CONFLICT") and bool(s["evidence_chain"])}


def _normalised_binding_event(e):
    kind = e.get("kind")
    if kind not in {"LEGISLATION", "AMENDMENT", "CORRECTION", "SUSPENSION", "REVIVAL", "REPEAL"}:
        return None
    return {"kind": kind, "canonical_id": e.get("canonical_id") or e.get("target_id"),
            "effective_from": e.get("effective_from"), "effective_to": e.get("effective_to"),
            "text": e.get("text")}


def replay(events):
    canonical = []
    seen = set()
    objects = set()
    for e in events:
        n = _normalised_binding_event(e)
        if n is None:
            continue
        key = json.dumps(n, sort_keys=True, separators=(",", ":"))
        if key in seen:
            continue
        seen.add(key)
        canonical.append(n)
        if n.get("canonical_id"):
            objects.add(n["canonical_id"])
    canonical.sort(key=lambda x: json.dumps(x, sort_keys=True, separators=(",", ":")))
    raw = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {"state_root": hashlib.sha256(raw).hexdigest(), "objects": len(objects), "unresolved": []}


def publish(query):
    s = _state(query)
    return {
        "canonical_id": s["canonical_id"],
        "status": s["status"],
        "text": s["text"],
        "evidence_chain": s["evidence_chain"],
        "projection": {
            "canonical_id": s["canonical_id"],
            "status": s["status"],
            "legal_time": s["legal_time"],
            "knowledge_time": s["knowledge_time"],
            "channels": ["human", "api", "linked_data", "eli", "public_sector", "ai"],
            "unresolved": s["unresolved"],
        },
    }
