"""Reference implementation for calibrating the distributed Observatory arena.

This is deliberately a simple single-primary/read-replica construction. It proves that the generic
cluster contract and fault injector are executable; it is not a preferred production architecture.
"""
import hashlib
import json
import os
import tempfile

REPLICATION_MODEL = "single_primary_read_replicas"
COMMIT_MODEL = "single_writer_sequence"
CHANNELS = ["human", "api", "linked_data", "eli", "public_sector", "ai"]


def _canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def _root(events, order):
    return hashlib.sha256(_canonical({
        "order": list(order),
        "events": [events[x] for x in order],
    })).hexdigest()


def _atomic(path, obj):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".tmp-", dir=os.path.dirname(os.path.abspath(path)))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"))
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, path)
        try:
            dfd = os.open(os.path.dirname(os.path.abspath(path)), os.O_RDONLY)
            try:
                os.fsync(dfd)
            finally:
                os.close(dfd)
        except OSError:
            pass
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def _read(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


class Cluster:
    def __init__(self, root_dir, node_ids):
        self.root_dir = os.path.abspath(root_dir)
        self.node_ids = [str(x) for x in node_ids]
        if len(self.node_ids) < 3 or len(set(self.node_ids)) != len(self.node_ids):
            raise ValueError("cluster requires at least three unique node IDs")
        os.makedirs(os.path.join(self.root_dir, "nodes"), exist_ok=True)
        self.state_path = os.path.join(self.root_dir, "cluster.json")
        if os.path.exists(self.state_path):
            self.state = _read(self.state_path)
            if self.state.get("node_ids") != self.node_ids:
                raise RuntimeError("node identity set changed across restart")
        else:
            self.state = {
                "node_ids": self.node_ids,
                "events": {},
                "order": [],
                "partitions": [self.node_ids],
                "crashed": [],
                "generation": 0,
            }
            self._persist()
        self.heal()

    def _persist(self):
        self.state["generation"] = int(self.state.get("generation", 0)) + 1
        _atomic(self.state_path, self.state)

    def _node_path(self, node_id):
        return os.path.join(self.root_dir, "nodes", f"{node_id}.json")

    def _canonical_root(self):
        return _root(self.state["events"], self.state["order"])

    def _snapshot(self):
        return {
            "events": self.state["events"],
            "order": self.state["order"],
            "root": self._canonical_root(),
            "generation": self.state["generation"],
        }

    def _sync_node(self, node_id):
        if node_id in self.state.get("crashed", []):
            return
        _atomic(self._node_path(node_id), self._snapshot())

    def _group(self, node_id):
        for group in self.state.get("partitions", []):
            if node_id in group:
                return list(group)
        return []

    def _quorum(self):
        return len(self.node_ids) // 2 + 1

    def _safe_group(self, node_id):
        active = [x for x in self._group(node_id)
                  if x not in self.state.get("crashed", [])]
        return active if len(active) >= self._quorum() else []

    def submit(self, node_id, event):
        node_id = str(node_id)
        if node_id not in self.node_ids:
            raise ValueError("unknown node")
        if node_id in self.state.get("crashed", []):
            return {"accepted": False, "pending": False, "reason": "node-crashed"}
        safe = self._safe_group(node_id)
        if not safe:
            return {"accepted": False, "pending": True,
                    "reason": "partition-without-quorum"}
        if not isinstance(event, dict) or not event.get("source_id"):
            return {"accepted": False, "pending": False, "reason": "malformed-event"}
        source_id = str(event["source_id"])
        existing = self.state["events"].get(source_id)
        if existing is not None:
            if _canonical(existing) == _canonical(event):
                return {"accepted": True, "duplicate": True,
                        "canonical_root": self._canonical_root()}
            return {"accepted": False, "pending": False,
                    "reason": "conflicting-source-id", "unresolved": True}
        self.state["events"][source_id] = event
        self.state["order"].append(source_id)
        self._persist()
        for target in safe:
            self._sync_node(target)
        return {"accepted": True, "duplicate": False,
                "canonical_root": self._canonical_root()}

    def ingest_batch(self, node_id, events):
        results = [self.submit(node_id, event) for event in list(events or [])]
        return {
            "accepted": sum(1 for x in results if x.get("accepted")),
            "pending": sum(1 for x in results if x.get("pending")),
            "rejected": sum(1 for x in results
                            if not x.get("accepted") and not x.get("pending")),
            "results": results,
            "canonical_root": self._canonical_root(),
        }

    def partition(self, groups):
        groups = [[str(x) for x in group] for group in groups]
        flattened = [x for group in groups for x in group]
        if sorted(flattened) != sorted(self.node_ids) or len(flattened) != len(set(flattened)):
            raise ValueError("partition groups must cover every node exactly once")
        self.state["partitions"] = groups
        self._persist()
        return {"ok": True, "groups": groups, "quorum": self._quorum()}

    def heal(self):
        self.state["partitions"] = [list(self.node_ids)]
        self._persist()
        for node_id in self.node_ids:
            self._sync_node(node_id)
        return {"ok": True, "canonical_root": self._canonical_root()}

    def roots(self):
        roots = {}
        for node_id in self.node_ids:
            if node_id in self.state.get("crashed", []):
                roots[node_id] = "CRASHED"
                continue
            path = self._node_path(node_id)
            try:
                snapshot = _read(path)
                computed = _root(snapshot["events"], snapshot["order"])
                roots[node_id] = computed if computed == snapshot.get("root") else "CORRUPT"
            except Exception:
                roots[node_id] = "CORRUPT"
        return roots

    def integrity(self):
        canonical = self._canonical_root()
        nodes = {}
        ok = True
        for node_id, root in self.roots().items():
            node_ok = root in (canonical, "CRASHED")
            nodes[node_id] = {"ok": node_ok, "root": root}
            ok = ok and node_ok
        return {"ok": ok, "canonical_root": canonical, "nodes": nodes}

    def crash(self, node_id):
        node_id = str(node_id)
        crashed = set(self.state.get("crashed", []))
        crashed.add(node_id)
        self.state["crashed"] = sorted(crashed)
        self._persist()
        return {"ok": True, "node_id": node_id}

    def restart(self, node_id):
        node_id = str(node_id)
        crashed = set(self.state.get("crashed", []))
        crashed.discard(node_id)
        self.state["crashed"] = sorted(crashed)
        self._persist()
        self._sync_node(node_id)
        return {"ok": True, "node_id": node_id,
                "root": self._canonical_root()}

    def recover(self, node_id):
        node_id = str(node_id)
        if node_id in self.state.get("crashed", []):
            return {"ok": False, "reason": "node-crashed"}
        self._sync_node(node_id)
        return {"ok": True, "node_id": node_id,
                "root": self._canonical_root()}

    def publication_roots(self):
        root = self._canonical_root()
        return {"canonical_root": root,
                "channels": {channel: root for channel in CHANNELS}}

    def cluster_manifest(self):
        return {
            "replication_model": REPLICATION_MODEL,
            "commit_model": COMMIT_MODEL,
            "node_authority_files": {
                node_id: [f"nodes/{node_id}.json"] for node_id in self.node_ids
            },
            "cluster_authority_files": ["cluster.json"],
            "fault_assumptions": {
                "writer": "one logical primary authority",
                "quorum": self._quorum(),
                "minority_writes": "explicitly pending",
                "byzantine_faults": 0,
            },
            "canonical_root_rule": (
                "SHA-256 of the canonical accepted source-id order and event objects in cluster.json"),
            "publication_channels": list(CHANNELS),
        }

    def close(self):
        self._persist()
        return {"ok": True, "canonical_root": self._canonical_root()}


def open_cluster(root_dir, node_ids):
    return Cluster(root_dir, node_ids)
