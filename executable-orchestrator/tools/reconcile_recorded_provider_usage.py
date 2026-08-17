#!/usr/bin/env python3
"""Offline reconciliation of provider responses already recorded on disk.

This tool performs ZERO HTTP calls. It exists for the exact crash/rejection boundary where the
provider returned an accepted response and usage, but local parsing failed before the ledger/meta
were finalised. It settles only responses that already have a matching OPEN reservation, appends a
signed api-call accounting event if absent, and writes recovery metadata. It never marks the model
content as schema-accepted and never resends provider bytes.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ORCH = os.path.dirname(HERE)
ROOT = os.path.dirname(ORCH)
sys.path.insert(0, ORCH)

from lawmax21.budget import BudgetLedger  # noqa: E402
from lawmax21.canonical import atomic_write_json, read_json, sha256_obj, utc  # noqa: E402
from lawmax21.client import extract_usage  # noqa: E402
from lawmax21 import decisions as dec  # noqa: E402
from lawmax21.eventlog import EventLog  # noqa: E402
from lawmax21.signing import load_private, load_public  # noqa: E402


def _already_logged(log, lid):
    return any(e.get("kind") == "api-call"
               and (e.get("payload") or {}).get("logical_id") == lid
               for e in log.events())


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=ROOT)
    ap.add_argument("--runtime", required=True)
    ap.add_argument("--run-id", required=True)
    a = ap.parse_args(argv)

    root = os.path.abspath(a.root)
    runtime = os.path.abspath(a.runtime)
    raw = os.path.join(runtime, "raw-api")
    req_dir = os.path.join(raw, "requests")
    resp_dir = os.path.join(raw, "responses")
    meta_dir = os.path.join(raw, "meta")
    if not os.path.isdir(resp_dir):
        raise RuntimeError(f"no recorded response directory: {resp_dir}")

    pub = load_public(os.path.join(root, "immutable-package", "OWNER-PUBLIC-KEY.hex"))
    D = dec.load(os.path.join(root, "OWNER-DECISIONS.signed.json"), pub, a.run_id)
    budget = dict(D.budget)
    schedule = budget.get("price_schedule")
    if not isinstance(schedule, dict):
        raise RuntimeError("signed D01 has no currency-explicit price schedule")
    ledger = BudgetLedger(os.path.join(runtime, "budget", "ledger.json"), budget)

    run_key_path = os.path.join(root, "private-evaluator", "owner-held-secrets",
                                f"RUN-{a.run_id}.key")
    if not os.path.exists(run_key_path):
        raise RuntimeError(f"run signing key missing: {run_key_path}")
    log = EventLog(os.path.join(runtime, "state", "events.jsonl"),
                   signer=load_private(run_key_path))

    os.makedirs(meta_dir, exist_ok=True)
    recovered = []
    skipped_final = 0

    for name in sorted(os.listdir(resp_dir)):
        if not name.endswith(".response.json"):
            continue
        lid = name[:-len(".response.json")]
        meta_p = os.path.join(meta_dir, lid + ".json")
        if os.path.exists(meta_p):
            skipped_final += 1
            continue
        req_p = os.path.join(req_dir, lid + ".request.json")
        if not os.path.exists(req_p):
            raise RuntimeError(f"recorded response {lid[:16]}… has no matching raw request")
        req = read_json(req_p)
        identity = req.get("identity") or {}
        if req.get("logical_id") != lid or sha256_obj(identity) != lid:
            raise RuntimeError(f"raw request identity mismatch for {lid[:16]}…")
        response = read_json(os.path.join(resp_dir, name))
        usage = extract_usage(response, schedule)

        if ledger.is_open(lid):
            ledger.settle(lid, usage["total_tokens"], usage["billing_amount"], usage=usage)
        elif not ledger.is_settled(lid):
            raise RuntimeError(
                f"recorded response {lid[:16]}… is not backed by an open/settled reservation; "
                "refusing to invent accounting")

        role = identity.get("role", "unknown")
        ticket = identity.get("ticket", "unknown")
        if not _already_logged(log, lid):
            log.append("api-call", "provider-reconciliation",
                       {"logical_id": lid, "role": role, "ticket": ticket,
                        "model": identity.get("model"), "endpoint": identity.get("endpoint"),
                        "usage": usage, "content_schema_status": "NOT_ACCEPTED"},
                       reason="offline reconciliation of already-recorded provider response; no resend",
                       subject_sha256=lid)

        atomic_write_json(meta_p, {
            "logical_id": lid,
            "role": role,
            "ticket": ticket,
            "utc": utc(),
            "status": 200,
            "usage": usage,
            "identity_sha256": sha256_obj(identity),
            "provider_accepted": True,
            "parse_status": "RECOVERED_NOT_ACCEPTED_FOR_EXPERIMENT",
            "recovered_without_resend": True,
        })
        recovered.append({"logical_id": lid, "role": role, "ticket": ticket,
                          "usage": usage})

    ok, events, why = log.verify()
    if not ok:
        raise RuntimeError(f"signed log failed after reconciliation: {why}")
    snap = ledger.snapshot()
    result = {
        "status": "PASS",
        "http_calls_made": 0,
        "run_id": a.run_id,
        "recovered": recovered,
        "already_finalized_responses": skipped_final,
        "signed_log_verified": True,
        "signed_log_events": events,
        "budget": snap,
    }
    print(json.dumps(result, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(json.dumps({"status": "FAIL", "http_calls_made": 0,
                          "reason": str(exc)}, ensure_ascii=False, indent=1))
        sys.exit(1)
