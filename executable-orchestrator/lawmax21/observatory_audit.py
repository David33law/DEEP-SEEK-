"""Profile-specific independent audit for the National Legal Observatory.

Diverse semantic and distributed implementation search, prior-art falsification, active novelty,
meta-search, hardening, taxonomy completion and search integrity are installed here because this is
the final profile layer. They wrap the complete crown search inside the same signed state machine and
final independent audit.
"""

from .canonical import atomic_write_json
from .handlers import A, tree_hash
from . import (observatory_distributed_overlay,
               observatory_implementation_search_overlay,
               observatory_meta_hardening_overlay, observatory_meta_search_overlay,
               observatory_novelty_overlay, observatory_prior_art_overlay,
               observatory_search_integrity_overlay,
               observatory_taxonomy_completion_overlay)


# The limit is a corruption/denial-of-service sanity bound, not an economy policy. Every genuinely
# unseen nonduplicate seed produced by the bounded schemas enters construction in the same wave.
observatory_novelty_overlay.NOVELTY_BUILD_LIMIT = 100_000


def install(ctx, handlers):
    """Install implementation → distributed → prior art → novelty/meta closure → audit."""
    out = observatory_implementation_search_overlay.install(ctx, handlers)
    out = observatory_distributed_overlay.install(ctx, out)
    out = observatory_prior_art_overlay.install(ctx, out)
    out = observatory_novelty_overlay.install(ctx, out)
    out = observatory_meta_search_overlay.install(ctx, out)
    out = observatory_meta_hardening_overlay.install(ctx, out)
    out = observatory_taxonomy_completion_overlay.install(ctx, out)
    out = observatory_search_integrity_overlay.install(ctx, out)

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
            "implementation_search": {
                "groups": supremacy.get("implementation_search_groups", 0),
                "current_candidates": supremacy.get(
                    "implementation_search_current_candidates", 0),
                "minimum_distinct_sources": supremacy.get(
                    "implementation_minimum_distinct_sources", 0),
                "semantic_revision_limit": supremacy.get(
                    "semantic_revision_limit", 0),
                "diversity_proven": supremacy.get(
                    "implementation_diversity_proven", False),
                "semantic_search_closed": supremacy.get(
                    "semantic_implementation_search_closed", False),
                "hidden_cases_disclosed_to_reviser": False,
                "aggregate_diagnostics_only": True,
            },
            "distributed_fault_campaign": {
                "contract": supremacy.get("distributed_contract"),
                "minimum_distinct_sources": supremacy.get(
                    "distributed_minimum_distinct_sources", 0),
                "revision_limit": supremacy.get("distributed_revision_limit", 0),
                "qualification_events": supremacy.get(
                    "distributed_qualification_events", 0),
                "replication_events": supremacy.get(
                    "distributed_replication_events", 0),
                "crown_events": supremacy.get("distributed_crown_events", 0),
                "implementation_diversity_proven": supremacy.get(
                    "distributed_implementation_diversity_proven", False),
                "failure_model_proven": supremacy.get(
                    "distributed_failure_model_proven", False),
                "replication_passed": supremacy.get(
                    "distributed_replication_passed", False),
                "crown_passed": supremacy.get(
                    "distributed_crown_passed", False),
                "candidate_labels_must_match_controlled_genome": True,
                "bounded_local_fault_model_only": True,
            },
            "authoritative_prior_art_challenge": {
                "manifest": "PUBLIC-PRIOR-ART-MANIFEST.json",
                "contract": "PRIOR-ART-CHALLENGE-CONTRACT.md",
                "manifest_sha256": supremacy.get("prior_art_manifest_sha256"),
                "waves": supremacy.get("prior_art_waves", 0),
                "sources": supremacy.get("prior_art_sources", 0),
                "challengers": supremacy.get("prior_art_challengers", 0),
                "blockers": supremacy.get("prior_art_blockers", 0),
                "all_sources_assessed": supremacy.get(
                    "prior_art_all_sources_assessed", False),
                "challengers_measured": supremacy.get(
                    "prior_art_challengers_measured", False),
                "no_blockers": supremacy.get("prior_art_no_blockers", False),
                "opened_only_after_independent_frontier": True,
                "third_party_endorsement_inferred": False,
            },
            "active_novelty_saturation": {
                "contract": supremacy.get("novelty_contract"),
                "meta_search_contract": supremacy.get("meta_search_contract"),
                "meta_search_hardening": "observatory_meta_hardening_overlay.py",
                "taxonomy_completion": "observatory_taxonomy_completion_overlay.py",
                "search_integrity": "observatory_search_integrity_overlay.py",
                "waves": supremacy.get("novelty_waves", 0),
                "dry_waves": supremacy.get("genome_dry_waves", 0),
                "known_controlled_genomes": supremacy.get("known_genomes", 0),
                "methods_expected": supremacy.get("novelty_methods_expected", []),
                "methods_complete": supremacy.get("novelty_methods_complete", False),
                "active_miner_minimum_structural_clusters": (
                    observatory_search_integrity_overlay.MIN_ACTIVE_CLUSTERS),
                "meta_search_closed": supremacy.get("meta_search_closed", False),
                "mechanical_coverage_closed": supremacy.get(
                    "mechanical_coverage_closed", False),
                "independent_closure_closed": supremacy.get(
                    "independent_closure_closed", False),
                "meta_search_critics_complete": supremacy.get(
                    "meta_search_critics_complete", False),
                "closure_auditors_complete": supremacy.get(
                    "closure_auditors_complete", False),
                "closure_auditors_support_final_dry": supremacy.get(
                    "closure_auditors_support_final_dry", False),
                "mechanical_coverage_complete": supremacy.get(
                    "mechanical_coverage_complete", False),
                "protocol_improvements_open": supremacy.get(
                    "protocol_improvements_open", 0),
                "taxonomy_unresolved_count": supremacy.get(
                    "taxonomy_unresolved_count", 0),
                "prior_cp2_direct_blind": supremacy.get(
                    "novelty_prior_cp2_direct_blind", False),
                "open_backlog": supremacy.get("novelty_open_backlog", 0),
                "unresolved": supremacy.get("novelty_unresolved", 0),
                "genome_saturated": supremacy.get("genome_saturated", False),
                "novelty_build_sanity_limit": observatory_novelty_overlay.NOVELTY_BUILD_LIMIT,
                "economy_deferral_allowed": False,
                "failed_dynamic_builds_retry": True,
                "auditor_fact_reproduction_required": True,
                "model_blocking_flag_not_authoritative": True,
                "taxonomy_consensus_required": 2,
                "post_resolution_reformalization_required": True,
            },
        })
        return p

    out["INDEPENDENT_AUDIT"] = independent_audit
    return out
