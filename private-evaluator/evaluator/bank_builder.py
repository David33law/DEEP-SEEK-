#!/usr/bin/env python3
"""Hidden bank generator. INDEPENDENT PARTY ONLY — never present on a builder machine.

Protocol 09 requires the hidden set to be produced *after* the graders are frozen, so
that no one can shape the questions around a known answer. This tool enforces that
mechanically: it records the SHA-256 of the grading semantics (grade.py, casegen.py) in
GRADER-FREEZE.json at build time, and the evaluator refuses to grade if those files have
changed since. Tuning the grader to a candidate therefore invalidates the bank instead
of improving the score.
"""
import argparse
import hashlib
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cryptography.fernet import Fernet

import casegen

HERE = os.path.dirname(os.path.abspath(__file__))
GRADER_FILES = ("grade.py", "casegen.py")


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
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
    return {f: sha256_file(os.path.join(HERE, f)) for f in GRADER_FILES}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build the encrypted hidden bank (independent party).")
    ap.add_argument("--bank", required=True)
    ap.add_argument("--key", required=True, help="Fernet key file. MOVE IT OUT OF EVERY BUILDER TREE.")
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--qualification", type=int, default=9)
    ap.add_argument("--replication", type=int, default=6)
    ap.add_argument("--holdout", type=int, default=3)
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

    manifest = {"levels": {}, "shard_hashes": [], "slices": casegen.SLICES,
                "domains": casegen.HIDDEN_DOMAINS, "seed_committed": True}
    rng = random.Random(a.seed)
    for level, n in (("qualification", a.qualification), ("replication", a.replication),
                     ("holdout", a.holdout)):
        ids = []
        per_domain = max(1, n // len(casegen.HIDDEN_DOMAINS))
        built = 0
        for domain in casegen.HIDDEN_DOMAINS:
            for i in range(per_domain):
                if built >= n:
                    break
                cid = f"{level[:4].upper()}{domain[:3].upper()}{i:03d}"
                case, draft, answers = casegen.make_case(rng, cid, domain)
                blob = json.dumps({"case": case, "draft": draft, "answers": answers},
                                  ensure_ascii=False, sort_keys=True).encode("utf-8")
                enc = fer.encrypt(blob)
                sid = hashlib.sha256(enc).hexdigest()
                with open(os.path.join(a.bank, sid + ".shard"), "wb") as f:
                    f.write(enc)
                ids.append(sid)
                manifest["shard_hashes"].append(sid)
                built += 1
        manifest["levels"][level] = ids

    manifest["merkle_root"] = merkle_root(manifest["shard_hashes"])
    with open(os.path.join(a.bank, "PRIVATE-manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1, sort_keys=True)
    with open(os.path.join(a.bank, "GRADER-FREEZE.json"), "w", encoding="utf-8") as f:
        json.dump({"frozen_at_build": grader_freeze(),
                   "rule": "the evaluator refuses to grade if these hashes change"},
                  f, indent=1, sort_keys=True)
    public = {"merkle_root": manifest["merkle_root"],
              "counts": {k: len(v) for k, v in manifest["levels"].items()},
              "slices": casegen.SLICES,
              "discloses": "counts and commitment only — no case content, no domains, no answers"}
    with open(os.path.join(a.bank, "PUBLIC-commitment.json"), "w", encoding="utf-8") as f:
        json.dump(public, f, indent=1, sort_keys=True)
    print(json.dumps(public, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
