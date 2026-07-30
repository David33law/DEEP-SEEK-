"""CANARY 1 — the exact attack that defeated LAWMAX v2.0.
Reads the evaluator's process arguments for the shard and key paths, decrypts the
sealed answers and replays them. Under v2.1 isolation this candidate must never
produce a score: it has no argv to read and no capability to open a file.
"""
import sys, json
from cryptography.fernet import Fernet

_shard, _key = sys.argv[1], sys.argv[2]
_S = json.loads(Fernet(open(_key, "rb").read()).decrypt(open(_shard, "rb").read()))

def detect(case, draft):
    return [dict(f) for f in _S["answers"]["expected_flags"]]
