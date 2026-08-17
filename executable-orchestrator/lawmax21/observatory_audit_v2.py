"""Integrated final profile layer and independent audit for the National Legal Observatory."""
from .canonical import atomic_write_json
from .handlers import A, tree_hash
from . import (observatory_distributed_overlay, observatory_formal_overlay,
               observatory_implementation_search_overlay, observatory_interoperability_overlay,
               observatory_meta_hardening_overlay, observatory_meta_search_overlay,
               observatory_novelty_overlay, observatory_prior_art_overlay,
               observatory_protocol, observatory_scale_overlay,
               observatory_search_integrity_overlay,
               observatory_taxonomy_completion_overlay,
               observatory_workload_policy)

observatory_novelty_overlay.NOVELTY_BUILD_LIMIT = 100_000


def _campaigns(s):
    return {
        "semantic_implementation": {
            "diversity": s.get("implementation_diversity_proven", False),
            "closed": s.get("semantic_implementation_search_closed", False),
            "groups": s.get("implementation_search_groups", 0),
            "minimum_distinct_sources": s.get("implementation_minimum_distinct_sources", 0),
            "revision_limit": s.get("semantic_revision_limit", 0)},
        "distributed": {
            "diversity": s.get("distributed_implementation_diversity_proven", False),
            "qualification": s.get("distributed_failure_model_proven", False),
            "replication": s.get("distributed_replication_passed", False),
            "crown": s.get("distributed_crown_passed", False),
            "contract": s.get("distributed_contract")},
        "national_scale": {
            "diversity": s.get("scale_implementation_diversity_proven", False),
            "qualification": s.get("national_scale_qualification_passed", False),
            "replication": s.get("national_scale_replication_passed", False),
            "crown": s.get("national_scale_crown_passed", False),
            "contract": s.get("scale_contract")},
        "machine_checked_models": {
            "qualification": s.get("machine_checked_models_passed", False),
            "agreement": s.get("independent_model_agreement", False),
            "replication": s.get("formal_replication_passed", False),
            "crown": s.get("formal_crown_passed", False),
            "contract": s.get("formal_contract")},
        "legal_interoperability": {
            "qualification": s.get("legal_interoperability_passed", False),
            "agreement": s.get("interoperability_implementations_agree", False),
            "replication": s.get("interoperability_replication_passed", False),
            "crown": s.get("interoperability_crown_passed", False),
            "contract": s.get("interoperability_contract")},
        "cross_model_consistency": {
            "qualification": s.get("cross_model_consistency_passed", False),
            "replication": s.get("cross_model_replication_passed", False),
            "crown": s.get("cross_model_crown_passed", False),
            "qualification_histories": s.get("cross_model_qualification_histories", 0),
            "replication_histories": s.get("cross_model_replication_histories", 0),
            "crown_histories": s.get("cross_model_crown_histories", 0),
            "contract": s.get("cross_model_contract")},
        "controlled_genome_realization": {
            "qualification": s.get("genome_realization_proven", False),
            "replication": s.get("genome_realization_replication_passed", False),
            "crown": s.get("genome_realization_crown_passed", False),
            "auditors": s.get("genome_realization_auditors", 0),
            "axes": s.get("genome_realization_axes", 0),
            "contract": s.get("genome_realization_contract")},
        "prior_art": {
            "all_sources_assessed": s.get("prior_art_all_sources_assessed", False),
            "challengers_measured": s.get("prior_art_challengers_measured", False),
            "no_blockers": s.get("prior_art_no_blockers", False),
            "sources": s.get("prior_art_sources", 0),
            "manifest_sha256": s.get("prior_art_manifest_sha256")},
        "active_novelty": {
            "genome_saturated": s.get("genome_saturated", False),
            "dry_waves": s.get("genome_dry_waves", 0),
            "methods_complete": s.get("novelty_methods_complete", False),
            "meta_search_closed": s.get("meta_search_closed", False),
            "mechanical_coverage_closed": s.get("mechanical_coverage_closed", False),
            "independent_closure_closed": s.get("independent_closure_closed", False),
            "cp2_direct_blind": s.get("novelty_prior_cp2_direct_blind", False),
            "open_backlog": s.get("novelty_open_backlog", 0),
            "unresolved": s.get("novelty_unresolved", 0)}}


def install(ctx, handlers):
    workload = observatory_workload_policy.apply()
    out = observatory_implementation_search_overlay.install(ctx, handlers)
    out = observatory_distributed_overlay.install(ctx, out)
    out = observatory_scale_overlay.install(ctx, out)
    out = observatory_formal_overlay.install(ctx, out)
    out = observatory_interoperability_overlay.install(ctx, out)
    out = observatory_prior_art_overlay.install(ctx, out)
    out = observatory_novelty_overlay.install(ctx, out)
    out = observatory_meta_search_overlay.install(ctx, out)
    out = observatory_meta_hardening_overlay.install(ctx, out)
    out = observatory_taxonomy_completion_overlay.install(ctx, out)
    out = observatory_search_integrity_overlay.install(ctx, out)

    def independent_audit(_machine):
        verified, event_count, log_reason = ctx.log.verify()
        summary = ctx.esc.supremacy_summary()
        conditions = ctx.esc._supremacy_conditions()
        path = A(ctx, "audit", "independent_audit.json")
        atomic_write_json(path, {
            "protocol_version": observatory_protocol.PROTOCOL_VERSION,
            "proof_mode": observatory_protocol.proof_mode(),
            "workload_policy": workload,
            "log_verified": verified, "log_reason": log_reason,
            "events": event_count,
            "immutable_package_unchanged": tree_hash(ctx.pkg) == ctx.package_hash_before,
            "hidden_disclosed_to_builder": False,
            "hidden_cases_disclosed_to_reviser": False,
            "budget_within_ceiling": ctx.ledger.within_ceiling(),
            "currency": ctx.ledger.currency,
            "spent": dict(ctx.ledger.state["spent"]),
            "limits": dict(ctx.ledger.limits),
            "provider": {"endpoint": ctx.client.t.endpoint, "model": ctx.client.t.model,
                         "price_schedule": dict(ctx.client.prices)},
            "supremacy_conditions": conditions,
            "unmet_supremacy_conditions": sorted(k for k, v in conditions.items() if not v),
            "supremacy_summary": summary,
            "campaigns": _campaigns(summary),
            "claim_boundaries": {
                "third_party_endorsement_inferred": False,
                "full_external_standard_certification_claimed": False,
                "unbounded_formal_proof_claimed": False,
                "untested_geographic_scale_claimed": False,
                "resource_exhaustion_counts_as_ceiling": False}})
        return path

    out["INDEPENDENT_AUDIT"] = independent_audit
    return out
