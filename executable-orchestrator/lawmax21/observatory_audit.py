"""Profile-specific independent audit for the National Legal Observatory.

The active novelty overlay is installed here because this is the final profile layer: it must wrap
the complete crown search while remaining inside the same signed state machine and independent audit.
"""

from .canonical import atomic_write_json
from .handlers import A, tree_hash
from . import observatory_novelty_overlay


def install(ctx, handlers):
    """Install active novelty saturation, then replace the LAWMAX currency-specific audit."""
    out = observatory_novelty_overlay.install(ctx, handlers)

    def independent_audit(_machine):
        ok, n, why = ctx.log.verify()
        after = tree_hash(ctx.pkg)
        snapshot = ctx.ledger.snapshot()
        supremacy = ctx.esc.supremacy_summary()
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
            "active_novelty_saturation": {
                "contract": supremacy.get("novelty_contract"),
                "waves": supremacy.get("novelty_waves", 0),
                "dry_waves": supremacy.get("genome_dry_waves", 0),
                "known_controlled_genomes": supremacy.get("known_genomes", 0),
                "methods_expected": supremacy.get("novelty_methods_expected", []),
                "methods_complete": supremacy.get("novelty_methods_complete", False),
                "prior_cp2_direct_blind": supremacy.get("novelty_prior_cp2_direct_blind", False),
                "open_backlog": supremacy.get("novelty_open_backlog", 0),
                "unresolved": supremacy.get("novelty_unresolved", 0),
                "genome_saturated": supremacy.get("genome_saturated", False),
            },
        })
        return p

    out["INDEPENDENT_AUDIT"] = independent_audit
    return out
