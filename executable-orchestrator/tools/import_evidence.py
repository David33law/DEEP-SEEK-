#!/usr/bin/env python3
"""Import a real source into the evidence vault and print exactly what the owner must sign.

Copying files in is not enough: preflight rejects an unattested source. This tool copies,
hashes, and emits the single command that binds those bytes to the owner's key. If the
material later changes by one byte, the attestation stops verifying and launch stops.

    python3 import_evidence.py --source ~/lawmax --into lawmax-current
    # then, on the owner machine:
    python3 owner_sign.py --key <owner.key> --gate VAULT-lawmax-current --run-id VAULT \
        --subject <printed hash file> --decision APPROVE --out <vault>/lawmax-current/SOURCE-ATTESTATION.json
"""
import argparse
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ORCH = os.path.dirname(HERE)
ROOT = os.path.dirname(ORCH)
sys.path.insert(0, ORCH)

from lawmax21.preflight import ATTESTATION_NAME, REQUIRED_VAULT_SOURCES, source_tree_hash  # noqa: E402
from lawmax21.signing import make_approval  # noqa: E402
from lawmax21.canonical import atomic_write_json  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", help="directory to import (omit with --attest-only)")
    ap.add_argument("--into", required=True, choices=sorted(REQUIRED_VAULT_SOURCES))
    ap.add_argument("--vault", default=os.path.join(ROOT, "evidence-vault"))
    ap.add_argument("--sign-with", help="owner private key — ONLY on the owner machine")
    ap.add_argument("--clear", action="store_true", help="replace the destination contents")
    ap.add_argument("--attest-only", action="store_true",
                    help="the material is already in place; hash and attest it as it stands")
    a = ap.parse_args(argv)

    dest = os.path.join(a.vault, a.into)
    n = 0
    if not a.attest_only:
        if not a.source:
            print("need --source, or --attest-only for material already in the vault")
            return 1
        if os.path.realpath(a.source) == os.path.realpath(dest):
            print("--source and the vault destination are the same directory; "
                  "use --attest-only to attest material that is already in place")
            return 1
        if a.clear and os.path.isdir(dest):
            shutil.rmtree(dest)
        os.makedirs(dest, exist_ok=True)
        for r, ds, fs in os.walk(a.source):
            ds[:] = [d for d in ds if d not in (".git", "__pycache__", "node_modules", ".venv")]
            for f in fs:
                src = os.path.join(r, f)
                out = os.path.join(dest, os.path.relpath(src, a.source))
                os.makedirs(os.path.dirname(out), exist_ok=True)
                shutil.copy2(src, out)
                n += 1
    else:
        os.makedirs(dest, exist_ok=True)
        n = sum(len(fs) for _, _, fs in os.walk(dest))

    h = source_tree_hash(dest)
    info = {"source": a.into, "files_imported": n, "tree_sha256": h,
            "description": REQUIRED_VAULT_SOURCES[a.into]}
    if a.sign_with:
        from lawmax21.signing import load_private
        env = make_approval(load_private(a.sign_with), f"VAULT-{a.into}", "VAULT", h, "APPROVE",
                            reason=REQUIRED_VAULT_SOURCES[a.into])
        atomic_write_json(os.path.join(dest, ATTESTATION_NAME), env)
        info["attested"] = True
    else:
        info["next_step"] = (
            f"on the owner machine, sign tree_sha256 {h} as gate VAULT-{a.into}, run-id VAULT, "
            f"and place the result at {os.path.join(dest, ATTESTATION_NAME)}")
    print(json.dumps(info, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
