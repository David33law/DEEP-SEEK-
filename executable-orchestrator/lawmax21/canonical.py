"""Canonical serialisation. ONE seat for "what are the bytes of this object".

Every hash in LAWMAX v2.1 is taken over `canonical_bytes(obj)`. There is no second
way to serialise for hashing, so two components can never disagree about an id.
"""
import hashlib
import json
import os
import tempfile

PROTOCOL_VERSION = "2.1.0"


def canonical_bytes(obj) -> bytes:
    """Deterministic UTF-8 bytes: sorted keys, no insignificant whitespace, no NaN."""
    return json.dumps(
        obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def sha256_obj(obj) -> str:
    return hashlib.sha256(canonical_bytes(obj)).hexdigest()


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def utc() -> str:
    import datetime

    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="microseconds")


def _fsync_dir(path):
    d = os.path.dirname(os.path.abspath(path)) or "."
    try:
        fd = os.open(d, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError:
        pass  # not supported on this platform/filesystem


def atomic_write_bytes(path, data: bytes):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(os.path.abspath(path)))
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
        _fsync_dir(path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def atomic_write_json(path, obj):
    """JSON artifacts on disk are pretty-printed for humans but hashed canonically."""
    atomic_write_bytes(path, json.dumps(obj, ensure_ascii=False, indent=1, sort_keys=True).encode("utf-8"))


def atomic_write_text(path, text: str):
    atomic_write_bytes(path, text.encode("utf-8"))


def read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
