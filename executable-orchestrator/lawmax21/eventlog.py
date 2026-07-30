"""Signed, hash-chained, append-only event log — the ONLY source of truth for run state.

Three structural properties, each killing a v2.0 forgery:

1. Every event carries an Ed25519 signature by the run key. Re-chaining a fabricated
   history no longer verifies, because the attacker cannot produce signatures. The run
   key lives in the owner-held secrets directory, which no candidate sandbox can name.
2. `current.json` is a CACHE, never an authority. `derived_state()` replays the log.
   A hand-written checkpoint is detected and refused, not obeyed.
3. Locking uses a dedicated lock file with a blocking acquire on POSIX and a
   retry-until-timeout acquire on Windows (LK_NBLCK), always at offset 0. Contention
   makes writers WAIT; it never raises after 10 seconds the way LK_LOCK does.
"""
import contextlib
import json
import os
import time

from .canonical import atomic_write_json, canonical_bytes, sha256_bytes, utc

GENESIS = "0" * 64
LOCK_TIMEOUT_S = 120.0


class LogTampered(Exception):
    pass


@contextlib.contextmanager
def file_lock(lock_path, timeout=LOCK_TIMEOUT_S):
    """Exclusive lock on a dedicated file. Blocks (bounded) rather than failing."""
    os.makedirs(os.path.dirname(os.path.abspath(lock_path)), exist_ok=True)
    f = open(lock_path, "a+b")
    try:
        try:
            import fcntl

            deadline = time.monotonic() + timeout
            while True:
                try:
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except OSError:
                    if time.monotonic() >= deadline:
                        raise TimeoutError(f"could not acquire {lock_path} within {timeout}s")
                    time.sleep(0.01)
            try:
                yield
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except ImportError:
            import msvcrt

            deadline = time.monotonic() + timeout
            while True:
                try:
                    f.seek(0)
                    msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError:
                    if time.monotonic() >= deadline:
                        raise TimeoutError(f"could not acquire {lock_path} within {timeout}s")
                    time.sleep(0.01)
            try:
                yield
            finally:
                f.seek(0)  # unlock the SAME byte range that was locked
                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
    finally:
        f.close()


class EventLog:
    def __init__(self, path, signer=None, verifier=None):
        """signer: PrivateIdentity (writers). verifier: PublicIdentity (everyone)."""
        self.path = os.path.abspath(path)
        self.lock_path = self.path + ".lock"
        self.signer = signer
        self.verifier = verifier or (signer.public if signer else None)
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        if not os.path.exists(self.path):
            with open(self.path, "w", encoding="utf-8"):
                pass

    # ---------------------------------------------------------------- writing
    def append(self, kind, actor, payload, reason="", subject_sha256=""):
        if self.signer is None:
            raise LogTampered("this EventLog handle is read-only (no signing identity)")
        with file_lock(self.lock_path):
            prev, seq = self._tail_unlocked()
            body = {
                "seq": seq,
                "utc": utc(),
                "kind": kind,
                "actor": actor,
                "payload": payload,
                "reason": reason,
                "subject_sha256": subject_sha256,
                "prev_hash": prev,
                "signer_key_id": self.signer.key_id,
            }
            body_hash = sha256_bytes(canonical_bytes(body))
            event = {"body": body, "body_hash": body_hash, "signature": self.signer.sign(body)}
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
                f.flush()
                os.fsync(f.fileno())
        return body_hash

    def _tail_unlocked(self):
        prev, seq = GENESIS, 0
        for ev in self._iter_raw():
            prev, seq = ev["body_hash"], ev["body"]["seq"] + 1
        return prev, seq

    # ---------------------------------------------------------------- reading
    def _iter_raw(self):
        with open(self.path, "r", encoding="utf-8") as f:
            for lineno, line in enumerate(f, 1):
                if not line.strip():
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError as e:
                    raise LogTampered(f"line {lineno}: not valid JSON ({e})")

    def verify(self):
        """Full verification: continuity, sequence, body hash AND signature.
        Returns (ok, count, reason)."""
        if self.verifier is None:
            return False, 0, "no verifying key available — cannot certify the log"
        prev, n = GENESIS, 0
        for ev in self._iter_raw():
            if set(ev) != {"body", "body_hash", "signature"}:
                return False, n, f"event {n}: unexpected envelope fields {sorted(set(ev))}"
            b = ev["body"]
            if b.get("seq") != n:
                return False, n, f"event {n}: sequence is {b.get('seq')}"
            if b.get("prev_hash") != prev:
                return False, n, f"event {n}: prev_hash break"
            if sha256_bytes(canonical_bytes(b)) != ev["body_hash"]:
                return False, n, f"event {n}: body hash mismatch"
            if b.get("signer_key_id") != self.verifier.key_id:
                return False, n, f"event {n}: signed by unknown key"
            if not self.verifier.verify(b, ev["signature"]):
                return False, n, f"event {n}: SIGNATURE INVALID — log was rewritten"
            prev, n = ev["body_hash"], n + 1
        return True, n, "ok"

    def events(self):
        ok, n, why = self.verify()
        if not ok:
            raise LogTampered(why)
        return [ev["body"] for ev in self._iter_raw()]

    def head(self):
        prev, seq = self._tail_unlocked()
        return prev, seq


class Checkpoint:
    """A cache in front of the log. Reading it CANNOT advance the run: the cached
    state is accepted only when it matches the log replay exactly."""

    def __init__(self, path, log: EventLog, replay):
        self.path = os.path.abspath(path)
        self.log = log
        self.replay = replay  # callable(events) -> state string

    def derived(self):
        """State, transition count, and the hash of the LAST TRANSITION event.

        The anchor is the last transition, not the last event: the log also carries
        api-call records, which legitimately arrive between transitions. Anchoring on the
        total event count would make an honest run look tampered with, and a guard that
        cries wolf gets disabled — which is how a real forgery would eventually slip past.
        """
        events = self.log.events()  # raises LogTampered on any forgery
        transitions = [e for e in events if e["kind"] == "transition"]
        anchor = transitions[-1]["prev_hash"] if transitions else GENESIS
        if transitions:
            from .canonical import canonical_bytes
            anchor = sha256_bytes(canonical_bytes(transitions[-1]))
        return self.replay(events), len(transitions), anchor

    def read(self):
        """The SIGNED LOG is authoritative; the checkpoint is only a cache. A checkpoint that
        is BEHIND the log is normal crash state (power loss between append and checkpoint
        write) — we roll forward to the log and refresh the cache. A checkpoint that claims
        MORE transitions than the log, or disagrees at the same count, is a forgery (someone
        hand-wrote current.json to jump ahead) — that we refuse. This distinguishes an honest
        crash from tampering, which the earlier version conflated."""
        state, n_transitions, anchor = self.derived()
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    cached = json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                raise LogTampered(f"checkpoint unreadable: {e}")
            c_n = cached.get("transitions")
            if isinstance(c_n, int) and c_n > n_transitions:
                raise LogTampered(
                    f"checkpoint claims {c_n} transitions but the signed log has only "
                    f"{n_transitions} — a checkpoint AHEAD of the log is forgery; refusing to run")
            if c_n == n_transitions and \
                    (cached.get("state"), cached.get("anchor")) != (state, anchor):
                raise LogTampered(
                    f"checkpoint disagrees with the signed log at the same transition count "
                    f"({cached.get('state')!r} vs {state!r}) — refusing to run")
            if c_n != n_transitions:
                self.write()   # stale cache behind the log: roll forward, refresh
        return state

    def write(self):
        state, n_transitions, anchor = self.derived()
        atomic_write_json(self.path, {"state": state, "transitions": n_transitions,
                                      "anchor": anchor, "utc": utc()})
        return state
