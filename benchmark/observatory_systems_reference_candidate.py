"""Reference implementation for durable-systems arena calibration only.

This is not a tournament candidate. It demonstrates that the evaluator can recognise durable,
idempotent, restartable state using only the standard library. SQLite is used as the durable
transaction engine and an independent SQLite backup is refreshed after each admitted batch.
"""
import hashlib
import json
import os
import shutil
import sqlite3

CHANNELS = ["human", "api", "linked_data", "eli", "public_sector", "ai"]


def _canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class DurableSystem:
    def __init__(self, state_dir):
        self.state_dir = os.path.abspath(state_dir)
        os.makedirs(self.state_dir, exist_ok=True)
        self.db = os.path.join(self.state_dir, "authority.sqlite3")
        self.backup = os.path.join(self.state_dir, "recovery.sqlite3")
        self.conn = None
        self._open_with_recovery()

    def _connect(self, path):
        c = sqlite3.connect(path, timeout=30.0, isolation_level=None)
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA synchronous=FULL")
        c.execute("PRAGMA busy_timeout=30000")
        c.execute("CREATE TABLE IF NOT EXISTS events (source_id TEXT PRIMARY KEY, payload TEXT NOT NULL, digest TEXT NOT NULL)")
        c.execute("CREATE TABLE IF NOT EXISTS metadata (k TEXT PRIMARY KEY, v TEXT NOT NULL)")
        return c

    @staticmethod
    def _integrity_conn(conn):
        try:
            row = conn.execute("PRAGMA integrity_check").fetchone()
            if not row or row[0] != "ok":
                return False
            for payload, digest in conn.execute("SELECT payload, digest FROM events"):
                if _digest(payload) != digest:
                    return False
            return True
        except sqlite3.DatabaseError:
            return False

    def _open_with_recovery(self):
        try:
            self.conn = self._connect(self.db)
            if self._integrity_conn(self.conn):
                return
        except sqlite3.DatabaseError:
            self.conn = None
        if self.conn is not None:
            try:
                self.conn.close()
            except Exception:
                pass
            self.conn = None
        if os.path.exists(self.backup):
            shutil.copy2(self.backup, self.db)
            self.conn = self._connect(self.db)
            if self._integrity_conn(self.conn):
                return
            self.conn.close()
            self.conn = None
        # New empty state is valid only when no pre-existing authority/recovery material exists.
        existing = [x for x in os.listdir(self.state_dir) if x.endswith((".sqlite3", ".sqlite3-wal", ".sqlite3-shm"))]
        if existing:
            raise RuntimeError("durable authority is corrupt and no valid recovery copy exists")
        self.conn = self._connect(self.db)
        self._backup()

    def _backup(self):
        tmp = self.backup + f".tmp-{os.getpid()}"
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
            dest = sqlite3.connect(tmp)
            try:
                self.conn.backup(dest)
                dest.execute("PRAGMA synchronous=FULL")
                dest.commit()
            finally:
                dest.close()
            os.replace(tmp, self.backup)
        finally:
            if os.path.exists(tmp):
                try:
                    os.remove(tmp)
                except OSError:
                    pass

    def ingest_batch(self, events):
        if not isinstance(events, list):
            raise ValueError("events must be a list")
        self.conn.execute("BEGIN IMMEDIATE")
        inserted = 0
        try:
            for event in events:
                sid = str(event.get("source_id") or "")
                if not sid:
                    raise ValueError("event missing source_id")
                payload = _canonical(event)
                dig = _digest(payload)
                row = self.conn.execute("SELECT payload FROM events WHERE source_id=?", (sid,)).fetchone()
                if row is not None:
                    if row[0] != payload:
                        raise ValueError("same source_id delivered with different payload")
                    continue
                self.conn.execute("INSERT INTO events(source_id,payload,digest) VALUES(?,?,?)", (sid, payload, dig))
                inserted += 1
            self.conn.execute("COMMIT")
        except BaseException:
            self.conn.execute("ROLLBACK")
            raise
        self._backup()
        return {"accepted": inserted, "duplicates": len(events) - inserted}

    def state_root(self):
        h = hashlib.sha256()
        for sid, digest in self.conn.execute("SELECT source_id,digest FROM events ORDER BY source_id"):
            h.update(sid.encode("utf-8")); h.update(b"\x00"); h.update(digest.encode("ascii")); h.update(b"\n")
        return h.hexdigest()

    def integrity_check(self):
        ok = self._integrity_conn(self.conn)
        return {"ok": bool(ok), "engine": "sqlite-full+payload-sha256"}

    def recover(self):
        if self._integrity_conn(self.conn):
            return {"ok": True, "mode": "already-valid"}
        try:
            self.conn.close()
        except Exception:
            pass
        if not os.path.exists(self.backup):
            return {"ok": False, "mode": "no-recovery-copy"}
        shutil.copy2(self.backup, self.db)
        self.conn = self._connect(self.db)
        ok = self._integrity_conn(self.conn)
        return {"ok": bool(ok), "mode": "sqlite-backup"}

    def publish_probe(self):
        return {"canonical_root": self.state_root(), "channels": list(CHANNELS)}

    def durability_manifest(self):
        return {
            "authority_files": ["authority.sqlite3"],
            "recovery_files": ["recovery.sqlite3"],
            "consistency_model": "SQLite BEGIN IMMEDIATE serialized durable batch commit",
            "transaction_order_semantic": False,
        }

    def close(self):
        if self.conn is not None:
            self.conn.execute("PRAGMA wal_checkpoint(FULL)")
            self._backup()
            self.conn.close()
            self.conn = None
        return {"ok": True}


def open_system(state_dir):
    return DurableSystem(state_dir)
