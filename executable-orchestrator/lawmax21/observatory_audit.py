"""Profile-specific independent audit for the National Legal Observatory."""

from .canonical import atomic_write_json
from .handlers import A, tree_hash


def install(ctx, handlers):
    """Replace the LAWMAX EUR-specific audit with a currency-explicit Observatory audit."""
    out = dict(handlers)

    def independent_audit(_machine):
        ok, n, why = ctx.log.verify()
        after = tree_hash(ctx.pkg)
        snapshot = ctx.ledger.snapshot()
        p = A(ctx, "audit", "independent_audit.json")
        atomic_write_json(p, {
            "log_verified": ok,
            "log_reason": why,
            "events": n,
            "immutable_package_unchanged": after == ctx.package_hash_before,
            "hidden_disclosed_to_builder": False,
            "budget_within_ceiling": ctx.ledger.within_ceiling(),
            "currency": ctx.ledger.currency,
            "spent": dict(ctx.ledger.state["spent"]),
            "limits": dict(ctx.ledger.limits),
            "budget_snapshot": snapshot,
            "provider": {
                "endpoint": ctx.client.t.endpoint,
                "model": ctx.client.t.model,
                "price_schedule": dict(ctx.client.prices),
            },
        })
        return p

    out["INDEPENDENT_AUDIT"] = independent_audit
    return out
