"""Ed25519 identities: owner (offline, human authority) and run (per-launch, machine).

Structural point: nothing in this module can *create* an owner approval. It can only
verify one. The orchestrator therefore has no code path by which it approves itself —
an owner gate can be satisfied only by bytes signed on the owner's own machine by
`tools/owner_sign.py`, which is never invoked by the runner.
"""
import os
import stat

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from .canonical import PROTOCOL_VERSION, atomic_write_bytes, atomic_write_json, canonical_bytes, sha256_bytes, utc

APPROVAL_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "additionalProperties": False,
    "required": ["payload", "signature"],
    "properties": {
        "signature": {"type": "string", "pattern": "^[0-9a-f]{128}$"},
        "payload": {
            "type": "object",
            "additionalProperties": False,
            "required": ["kind", "gate_id", "run_id", "subject_sha256", "decision",
                         "signer_key_id", "protocol_version", "utc"],
            "properties": {
                "kind": {"const": "lawmax.owner-approval"},
                "gate_id": {"type": "string", "minLength": 1},
                "run_id": {"type": "string", "minLength": 1},
                "subject_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
                "decision": {"enum": ["APPROVE", "REJECT"]},
                "reason": {"type": "string"},
                "signer_key_id": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
                "protocol_version": {"type": "string"},
                "utc": {"type": "string", "minLength": 20},
            },
        },
    },
}


class SignatureRejected(Exception):
    pass


def key_id(public_bytes: bytes) -> str:
    return sha256_bytes(public_bytes)


def generate_private(path) -> "PrivateIdentity":
    k = Ed25519PrivateKey.generate()
    raw = k.private_bytes_raw()
    atomic_write_bytes(path, raw)
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)  # 0600 where the platform honours it
    except OSError:
        pass
    return PrivateIdentity(k)


def load_private(path) -> "PrivateIdentity":
    with open(path, "rb") as f:
        raw = f.read()
    if len(raw) != 32:
        raise SignatureRejected(f"{path}: expected a 32-byte Ed25519 seed, got {len(raw)} bytes")
    return PrivateIdentity(Ed25519PrivateKey.from_private_bytes(raw))


def load_public(path) -> "PublicIdentity":
    with open(path, "r", encoding="utf-8") as f:
        hexed = f.read().strip()
    try:
        raw = bytes.fromhex(hexed)
    except ValueError:
        raise SignatureRejected(f"{path}: public key must be 64 hex characters")
    if len(raw) != 32:
        raise SignatureRejected(f"{path}: expected a 32-byte Ed25519 public key")
    return PublicIdentity(Ed25519PublicKey.from_public_bytes(raw))


class PublicIdentity:
    def __init__(self, pk: Ed25519PublicKey):
        self._pk = pk
        self.public_raw = pk.public_bytes_raw()
        self.key_id = key_id(self.public_raw)

    def verify(self, payload_obj, signature_hex: str) -> bool:
        try:
            self._pk.verify(bytes.fromhex(signature_hex), canonical_bytes(payload_obj))
            return True
        except (InvalidSignature, ValueError):
            return False


class PrivateIdentity:
    def __init__(self, sk: Ed25519PrivateKey):
        self._sk = sk
        self.public = PublicIdentity(sk.public_key())
        self.key_id = self.public.key_id

    def write_public(self, path):
        atomic_write_bytes(path, (self.public.public_raw.hex() + "\n").encode("ascii"))

    def sign(self, payload_obj) -> str:
        return self._sk.sign(canonical_bytes(payload_obj)).hex()

    def sign_envelope(self, payload_obj) -> dict:
        return {"payload": payload_obj, "signature": self.sign(payload_obj)}


def make_approval(identity: PrivateIdentity, gate_id, run_id, subject_sha256, decision, reason=""):
    payload = {
        "kind": "lawmax.owner-approval",
        "gate_id": gate_id,
        "run_id": run_id,
        "subject_sha256": subject_sha256,
        "decision": decision,
        "signer_key_id": identity.key_id,
        "protocol_version": PROTOCOL_VERSION,
        "utc": utc(),
    }
    if reason:
        payload["reason"] = reason
    return identity.sign_envelope(payload)


def verify_approval(envelope, owner: PublicIdentity, gate_id, run_id, subject_sha256):
    """Returns the payload, or raises. Every field is bound — an approval for one gate,
    one run and one artifact cannot be replayed onto another."""
    from .schema import ValidationError, validate

    try:
        validate(envelope, APPROVAL_SCHEMA)
    except ValidationError as e:
        raise SignatureRejected(f"approval artifact malformed: {e}")
    p = envelope["payload"]
    if p["signer_key_id"] != owner.key_id:
        raise SignatureRejected(f"approval signed by unknown key {p['signer_key_id'][:16]}…")
    if not owner.verify(p, envelope["signature"]):
        raise SignatureRejected("approval signature does not verify")
    if p["gate_id"] != gate_id:
        raise SignatureRejected(f"approval is for gate {p['gate_id']!r}, not {gate_id!r}")
    if p["run_id"] != run_id:
        raise SignatureRejected(f"approval is for run {p['run_id']!r}, not {run_id!r}")
    if p["subject_sha256"] != subject_sha256:
        raise SignatureRejected("approval is bound to a different artifact hash")
    if p["protocol_version"] != PROTOCOL_VERSION:
        raise SignatureRejected(f"approval protocol {p['protocol_version']} != {PROTOCOL_VERSION}")
    if p["decision"] != "APPROVE":
        raise SignatureRejected(f"owner decision is {p['decision']}")
    return p


def write_approval(path, envelope):
    atomic_write_json(path, envelope)
