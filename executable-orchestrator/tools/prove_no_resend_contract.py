#!/usr/bin/env python3
"""Zero-network proof of the provider-response finalization contract.

Exercises exactly the production bug found by the first real V4-Pro run:
1) provider returns 200 + usage;
2) local schema rejects content;
3) spend must still settle exactly once;
4) re-validation under a relaxed schema must use recorded bytes, never another send;
5) an orphan raw response backed by an open reservation must recover without any send.
"""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ORCH = os.path.dirname(HERE)
sys.path.insert(0, ORCH)

from lawmax21.budget import BudgetLedger  # noqa: E402
from lawmax21.canonical import atomic_write_json, utc  # noqa: E402
from lawmax21.client import Client, StructuredOutputRejected  # noqa: E402

PRICE = {
    "model": "deepseek-v4-pro",
    "currency": "USD",
    "input_cache_hit_per_mtok": 0.003625,
    "input_cache_miss_per_mtok": 0.435,
    "output_per_mtok": 0.87,
    "require_cache_split": True,
}
LIMITS = {"currency": "USD", "amount": 1.0, "tokens": 1000000, "calls": 20,
          "wall_clock_days": 1, "successor_reserve_fraction": 0.35,
          "price_schedule": PRICE}
DEFAULTS = {"thinking": {"type": "enabled"}, "reasoning_effort": "max"}
STRICT = {"type": "object", "additionalProperties": False,
          "required": ["x"], "properties": {"x": {"type": "string", "maxLength": 3}}}
RELAXED = {"type": "object", "additionalProperties": False,
           "required": ["x"], "properties": {"x": {"type": "string", "maxLength": 100}}}


def envelope(content):
    pt, ct = 20, 10
    return {
        "id": "proof-response", "object": "chat.completion", "model": "deepseek-v4-pro",
        "choices": [{"index": 0, "finish_reason": "stop",
                     "message": {"role": "assistant", "content": content}}],
        "usage": {"prompt_tokens": pt, "completion_tokens": ct, "total_tokens": pt + ct,
                  "prompt_cache_hit_tokens": 0, "prompt_cache_miss_tokens": pt,
                  "completion_tokens_details": {"reasoning_tokens": 4}},
    }


class FakeTransport:
    endpoint = "http://proof.invalid/chat/completions"
    model = "deepseek-v4-pro"

    def __init__(self, response):
        self.response = response
        self.calls = 0

    def send(self, _body):
        self.calls += 1
        return 200, json.dumps(self.response)


def make_client(root, transport):
    ledger = BudgetLedger(os.path.join(root, "ledger.json"), LIMITS)
    client = Client(transport, os.path.join(root, "raw"), ledger, None, "SYSTEM",
                    prices=PRICE, max_technical_retries=1,
                    request_defaults=DEFAULTS, default_max_tokens=64)
    return client, ledger


def main():
    with tempfile.TemporaryDirectory(prefix="obs-no-resend-") as tmp:
        # Case A: real response is paid, then local schema rejects it.
        t1 = FakeTransport(envelope('{"x":"this-is-longer-than-three"}'))
        c1, l1 = make_client(os.path.join(tmp, "case-a"), t1)
        msgs = [{"role": "user", "content": "test schema rejection"}]
        rejected = False
        try:
            c1.call("architecture-explorer-B", "T1", "a" * 64, msgs,
                    response_schema=STRICT)
        except StructuredOutputRejected:
            rejected = True
        if not rejected:
            raise RuntimeError("strict schema unexpectedly accepted the fake response")
        s1 = l1.snapshot()
        if t1.calls != 1 or s1["spent"]["calls"] != 1 or s1["open_reservations"] != 0:
            raise RuntimeError(
                f"schema rejection accounting wrong: sends={t1.calls}, budget={s1}")

        # Same logical request, broader schema: exact raw bytes must be re-validated, not sent.
        lid, parsed, replayed, _usage = c1.call(
            "architecture-explorer-B", "T1", "a" * 64, msgs, response_schema=RELAXED)
        s2 = l1.snapshot()
        if not replayed or parsed.get("x") != "this-is-longer-than-three":
            raise RuntimeError("recorded schema-rejected response was not reusable under relaxed schema")
        if t1.calls != 1 or s2["spent"]["calls"] != 1:
            raise RuntimeError("re-validation caused a duplicate provider send/charge")

        # Case B: simulate crash after raw response persistence but before settlement/meta.
        t2 = FakeTransport(envelope('{"x":"ok"}'))
        c2, l2 = make_client(os.path.join(tmp, "case-b"), t2)
        msgs2 = [{"role": "user", "content": "orphan raw response"}]
        body = dict(DEFAULTS)
        body.update({"model": t2.model, "max_tokens": 64,
                     "messages": [{"role": "system", "content": "SYSTEM"}] + msgs2})
        identity = c2.identity("architecture-explorer-C", "T2", "b" * 64, body)
        lid2 = c2.logical_id(identity)
        meta_p, req_p, resp_p = c2._paths(lid2)
        est_tokens, est_money = c2._estimate(identity)
        l2.reserve(lid2, "architecture-explorer-C", est_tokens, est_money)
        atomic_write_json(req_p, {"logical_id": lid2, "utc": utc(), "identity": identity})
        atomic_write_json(resp_p, t2.response)
        if os.path.exists(meta_p):
            raise RuntimeError("orphan simulation unexpectedly has meta")

        _lid2, parsed2, replayed2, _usage2 = c2.call(
            "architecture-explorer-C", "T2", "b" * 64, msgs2, response_schema=RELAXED)
        s3 = l2.snapshot()
        if not replayed2 or parsed2.get("x") != "ok":
            raise RuntimeError("orphan recorded response did not recover")
        if t2.calls != 0 or s3["spent"]["calls"] != 1 or s3["open_reservations"] != 0:
            raise RuntimeError(
                f"orphan recovery sent provider bytes or mis-accounted: sends={t2.calls}, budget={s3}")

        print(json.dumps({
            "status": "PASS",
            "real_http_calls": 0,
            "schema_rejection_settled_once": True,
            "schema_revalidation_without_resend": True,
            "orphan_raw_response_recovered_without_resend": True,
            "case_a_logical_id": lid,
            "case_b_logical_id": lid2,
        }, indent=1))
        return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(json.dumps({"status": "FAIL", "real_http_calls": 0,
                          "reason": str(exc)}, indent=1))
        sys.exit(1)
