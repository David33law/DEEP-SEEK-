#!/usr/bin/env python3
"""Owner-side signing. Runs on the OWNER's machine, never on the experiment machine.

This is the only producer of the bytes an owner gate accepts. The orchestrator imports
`verify_approval` and nothing else, so there is no path by which a run approves itself.

    # once, to create the identity
    python3 owner_sign.py --init --key ~/lawmax-owner.key --public-out immutable-package/OWNER-PUBLIC-KEY.hex

    # per gate
    python3 owner_sign.py --key ~/lawmax-owner.key --gate GATE-ARCH-V0 --run-id RUN-0001 \
        --subject runtime/gates/v0_subject.json --decision APPROVE --out runtime/gates/GATE-ARCH-V0.approval.json

    # the eleven decisions, once per run
    python3 owner_sign.py --key ~/lawmax-owner.key --run-id RUN-0001 \
        --decisions decisions.json --out OWNER-DECISIONS.signed.json
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from lawmax21.canonical import PROTOCOL_VERSION, atomic_write_json, sha256_file, utc  # noqa: E402
from lawmax21.decisions import DECISION_IDS  # noqa: E402
from lawmax21.signing import generate_private, load_private, make_approval  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--init", action="store_true", help="create a new owner identity")
    ap.add_argument("--key", required=True)
    ap.add_argument("--public-out")
    ap.add_argument("--gate")
    ap.add_argument("--run-id")
    ap.add_argument("--subject")
    ap.add_argument("--decision", choices=("APPROVE", "REJECT"), default="APPROVE")
    ap.add_argument("--reason", default="")
    ap.add_argument("--decisions", help="path to the eleven decisions (unsigned JSON)")
    ap.add_argument("--out")
    a = ap.parse_args(argv)

    if a.init:
        if os.path.exists(a.key):
            print(f"refusing to overwrite an existing key at {a.key}")
            return 1
        ident = generate_private(a.key)
        if a.public_out:
            ident.write_public(a.public_out)
        print(json.dumps({"key_id": ident.key_id, "private": a.key, "public": a.public_out}))
        return 0

    ident = load_private(a.key)

    if a.decisions:
        raw = json.load(open(a.decisions, encoding="utf-8"))
        missing = [d for d in DECISION_IDS if d not in raw]
        if missing:
            print(f"cannot sign: undecided {missing}")
            return 1
        payload = {"kind": "lawmax.owner-decisions", "run_id": a.run_id,
                   "signer_key_id": ident.key_id, "protocol_version": PROTOCOL_VERSION,
                   "utc": utc(), "decisions": raw}
        atomic_write_json(a.out, ident.sign_envelope(payload))
        print(json.dumps({"signed": a.out, "decisions": len(raw), "key_id": ident.key_id}))
        return 0

    if not (a.gate and a.run_id and a.subject and a.out):
        print("need --gate --run-id --subject --out")
        return 1
    env = make_approval(ident, a.gate, a.run_id, sha256_file(a.subject), a.decision, a.reason)
    atomic_write_json(a.out, env)
    print(json.dumps({"signed": a.out, "gate": a.gate, "decision": a.decision,
                      "subject_sha256": env["payload"]["subject_sha256"][:16] + "…"}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
