#!/usr/bin/env python3
"""Build encrypted hidden replay banks for the National Legal Observatory profile."""
import argparse
import hashlib
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cryptography.fernet import Fernet
import observatory_casegen as casegen

HERE = os.path.dirname(os.path.abspath(__file__))
GRADER_FILES = ("observatory_grade.py", "observatory_casegen.py", "observatory_host.py", "observatory_canaries.py")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def merkle_root(hashes):
    layer = sorted(hashes)
    if not layer:
        return "0" * 64
    while len(layer) > 1:
        if len(layer) % 2:
            layer.append(layer[-1])
        layer = [hashlib.sha256((layer[i] + layer[i + 1]).encode()).hexdigest()
                 for i in range(0, len(layer), 2)]
    return layer[0]


def grader_freeze():
    return {name: sha256_file(os.path.join(HERE, name)) for name in GRADER_FILES}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--bank", required=True)
    ap.add_argument("--key", required=True)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--qualification", type=int, default=8)
    ap.add_argument("--replication", type=int, default=5)
    ap.add_argument("--holdout", type=int, default=4)
    a = ap.parse_args(argv)

    os.makedirs(a.bank, exist_ok=True)
    if os.path.exists(a.key):
        key = open(a.key, "rb").read()
    else:
        key = Fernet.generate_key()
        os.makedirs(os.path.dirname(os.path.abspath(a.key)), exist_ok=True)
        with open(a.key, "wb") as f:
            f.write(key)
        try:
            os.chmod(a.key, 0o600)
        except OSError:
            pass
    fer = Fernet(key)
    rng = random.Random(a.seed)

    manifest = {
        "profile": "national-observatory",
        "schema": "national-observatory-hidden-bank-v1",
        "levels": {}, "shard_hashes": [],
        "dimensions": list(casegen.DIMENSIONS),
        "seed_committed": True,
    }
    for level, n in (("qualification", a.qualification),
                     ("replication", a.replication),
                     ("holdout", a.holdout)):
        ids = []
        for i in range(n):
            scenario_seed = rng.randrange(1, 2**31 - 1)
            scenario = casegen.make_scenario(scenario_seed, f"{level[:4].upper()}-{i:04d}")
            blob = json.dumps(scenario, ensure_ascii=False, sort_keys=True,
                              separators=(",", ":")).encode("utf-8")
            enc = fer.encrypt(blob)
            sid = hashlib.sha256(enc).hexdigest()
            with open(os.path.join(a.bank, sid + ".shard"), "wb") as f:
                f.write(enc)
            ids.append(sid)
            manifest["shard_hashes"].append(sid)
        manifest["levels"][level] = ids

    manifest["merkle_root"] = merkle_root(manifest["shard_hashes"])
    with open(os.path.join(a.bank, "PRIVATE-manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1, sort_keys=True)
    with open(os.path.join(a.bank, "GRADER-FREEZE.json"), "w", encoding="utf-8") as f:
        json.dump({"profile": "national-observatory", "frozen_at_build": grader_freeze(),
                   "rule": "any grader/host/canary drift invalidates this hidden bank"},
                  f, indent=1, sort_keys=True)
    public = {
        "profile": "national-observatory",
        "merkle_root": manifest["merkle_root"],
        "counts": {k: len(v) for k, v in manifest["levels"].items()},
        "dimensions": list(casegen.DIMENSIONS),
        "discloses": "counts, dimensions and commitment only; no scenario ids/content/answers",
    }
    with open(os.path.join(a.bank, "PUBLIC-commitment.json"), "w", encoding="utf-8") as f:
        json.dump(public, f, indent=1, sort_keys=True)
    print(json.dumps(public, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
