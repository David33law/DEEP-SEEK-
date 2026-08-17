"""Reference implementation for calibrating the Observatory national-scale arena.

It uses deterministic source-ID sharding and atomic JSON snapshots. It is intentionally simple and
is not a preferred national implementation; the purpose is to prove the generic scale contract,
rebuild, checkpoint/recovery and measurement path.
"""
import hashlib
import json
import os
import shutil
import tempfile

SCALING_PARTITION_MODEL = "source_sharding"
CHANNELS = ["human", "api", "linked_data", "eli", "public_sector", "ai"]


def _canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def _hash(obj):
    return hashlib.sha256(_canonical(obj)).hexdigest()


def _atomic(path, obj):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".tmp-", dir=os.path.dirname(os.path.abspath(path)))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"))
            f.flush(); os.fsync(f.fileno())
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


class ScaleStore:
    def __init__(self, root_dir, partition_count):
        self.root_dir = os.path.abspath(root_dir)
        self.partition_count = int(partition_count)
        if self.partition_count < 1 or self.partition_count > 1024:
            raise ValueError("partition_count outside supported range")
        self.partitions_dir = os.path.join(self.root_dir, "partitions")
        self.checkpoint_dir = os.path.join(self.root_dir, "checkpoint")
        self.meta_path = os.path.join(self.root_dir, "scale-meta.json")
        os.makedirs(self.partitions_dir, exist_ok=True)
        if os.path.exists(self.meta_path):
            meta = _read(self.meta_path)
            if int(meta.get("partition_count", -1)) != self.partition_count:
                raise RuntimeError("partition count changed across restart")
        else:
            _atomic(self.meta_path, {
                "partition_count": self.partition_count,
                "scaling_partition_model": SCALING_PARTITION_MODEL,
                "generation": 0,
            })
        for index in range(self.partition_count):
            path = self._partition_path(index)
            if not os.path.exists(path):
                _atomic(path, {"events": {}})

    def _partition_path(self, index):
        return os.path.join(self.partitions_dir, f"p{index:04d}.json")

    def _partition_index(self, source_id):
        digest = hashlib.sha256(str(source_id).encode("utf-8")).digest()
        return int.from_bytes(digest[:8], "big") % self.partition_count

    def _partition(self, index):
        obj = _read(self._partition_path(index))
        if not isinstance(obj, dict) or not isinstance(obj.get("events"), dict):
            raise RuntimeError(f"malformed partition {index}")
        return obj

    def _save_partition(self, index, obj):
        _atomic(self._partition_path(index), obj)

    def ingest_batch(self, events):
        working = {}
        results = []
        for event in list(events or []):
            if not isinstance(event, dict) or not event.get("source_id"):
                results.append({"accepted": False, "unresolved": False,
                                "reason": "malformed-event"})
                continue
            source_id = str(event["source_id"])
            index = self._partition_index(source_id)
            if index not in working:
                working[index] = self._partition(index)
            current = working[index]["events"].get(source_id)
            if current is None:
                working[index]["events"][source_id] = event
                results.append({"accepted": True, "duplicate": False,
                                "partition": index})
            elif _canonical(current) == _canonical(event):
                results.append({"accepted": True, "duplicate": True,
                                "partition": index})
            else:
                results.append({"accepted": False, "unresolved": True,
                                "reason": "conflicting-source-id", "partition": index})
        for index, obj in working.items():
            self._save_partition(index, obj)
        meta = _read(self.meta_path)
        meta["generation"] = int(meta.get("generation", 0)) + 1
        _atomic(self.meta_path, meta)
        return {
            "accepted": sum(1 for x in results if x.get("accepted")),
            "duplicates": sum(1 for x in results if x.get("duplicate")),
            "unresolved": sum(1 for x in results if x.get("unresolved")),
            "results": results,
            "canonical_root": self.state_root(),
        }

    def partition_roots(self):
        roots = {}
        for index in range(self.partition_count):
            obj = self._partition(index)
            roots[f"p{index:04d}"] = _hash({
                "events": {key: obj["events"][key]
                           for key in sorted(obj["events"])}
            })
        return roots

    def state_root(self):
        roots = self.partition_roots()
        return _hash({"partition_roots": {key: roots[key] for key in sorted(roots)}})

    def integrity_check(self):
        counts = {}
        try:
            roots = self.partition_roots()
            for index in range(self.partition_count):
                obj = self._partition(index)
                counts[f"p{index:04d}"] = len(obj["events"])
            root = _hash({"partition_roots": {key: roots[key] for key in sorted(roots)}})
            return {"ok": True, "canonical_root": root,
                    "partition_roots": roots, "partition_counts": counts,
                    "event_count": sum(counts.values())}
        except Exception as exc:
            return {"ok": False, "reason": type(exc).__name__ + ": " + str(exc),
                    "partition_counts": counts}

    def publish_probe(self):
        root = self.state_root()
        return {"canonical_root": root,
                "channels": {channel: root for channel in CHANNELS}}

    def checkpoint(self):
        temp = self.checkpoint_dir + ".new"
        if os.path.exists(temp):
            shutil.rmtree(temp)
        os.makedirs(temp, exist_ok=True)
        files = ["scale-meta.json"] + [
            f"partitions/p{index:04d}.json" for index in range(self.partition_count)
        ]
        hashes = {}
        for rel in files:
            source = os.path.join(self.root_dir, *rel.split("/"))
            target = os.path.join(temp, *rel.split("/"))
            os.makedirs(os.path.dirname(target), exist_ok=True)
            shutil.copyfile(source, target)
            with open(target, "rb") as f:
                hashes[rel] = hashlib.sha256(f.read()).hexdigest()
        _atomic(os.path.join(temp, "CHECKPOINT.json"), {
            "canonical_root": self.state_root(),
            "files": hashes,
        })
        if os.path.exists(self.checkpoint_dir):
            shutil.rmtree(self.checkpoint_dir)
        os.replace(temp, self.checkpoint_dir)
        return {"ok": True, "canonical_root": self.state_root(),
                "files": sorted(hashes)}

    def recover(self):
        manifest_path = os.path.join(self.checkpoint_dir, "CHECKPOINT.json")
        if not os.path.exists(manifest_path):
            return {"ok": False, "reason": "checkpoint-missing"}
        manifest = _read(manifest_path)
        for rel, expected in manifest.get("files", {}).items():
            source = os.path.join(self.checkpoint_dir, *rel.split("/"))
            with open(source, "rb") as f:
                actual = hashlib.sha256(f.read()).hexdigest()
            if actual != expected:
                return {"ok": False, "reason": "checkpoint-corrupt", "file": rel}
        for rel in manifest["files"]:
            source = os.path.join(self.checkpoint_dir, *rel.split("/"))
            target = os.path.join(self.root_dir, *rel.split("/"))
            os.makedirs(os.path.dirname(target), exist_ok=True)
            shutil.copyfile(source, target)
        integrity = self.integrity_check()
        return {"ok": integrity.get("ok") is True
                      and integrity.get("canonical_root") == manifest.get("canonical_root"),
                "canonical_root": integrity.get("canonical_root")}

    def scale_manifest(self):
        return {
            "scaling_partition_model": SCALING_PARTITION_MODEL,
            "partition_count": self.partition_count,
            "routing_rule": "SHA-256(source_id) first 64 bits modulo partition_count",
            "authority_files": ["scale-meta.json"] + [
                f"partitions/p{index:04d}.json" for index in range(self.partition_count)
            ],
            "checkpoint_files": ["checkpoint/CHECKPOINT.json"],
            "publication_channels": list(CHANNELS),
            "complexity_claim": {
                "routing": "O(1) per event",
                "partition_update": "O(size of one partition snapshot) in this calibration implementation",
                "root": "O(partition_count) after partition roots are read",
                "assumptions": "local filesystem, atomic rename, fsync and bounded partition count",
            },
        }

    def close(self):
        return {"ok": True, "canonical_root": self.state_root()}


def open_scale(root_dir, partition_count):
    return ScaleStore(root_dir, partition_count)
