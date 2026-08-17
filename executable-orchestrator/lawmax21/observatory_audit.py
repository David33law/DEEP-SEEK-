"""Compatibility entrypoint for the final integrated Observatory audit layer."""
from . import observatory_audit_v2 as base
from . import observatory_build_schema_hardening
from . import observatory_cross_model_overlay
from . import observatory_cross_model_workload_hardening
from . import observatory_evaluator_routing_hardening
from . import observatory_formal_streaming_routing
from . import observatory_genome_auditor_diversity_hardening
from . import observatory_genome_evidence_binding_hardening
from . import observatory_genome_realization_overlay
from . import observatory_phase_gate_hardening
from . import observatory_prior_art_hardening_overlay
from . import observatory_scale_hardening
from . import observatory_shared_corpus_hardening


def install(ctx, handlers):
    # Patch shared schema/function seats before any overlay captures them.
    observatory_build_schema_hardening.install(ctx, handlers)
    observatory_genome_auditor_diversity_hardening.install(ctx, handlers)
    observatory_shared_corpus_hardening.install(ctx, handlers)
    observatory_evaluator_routing_hardening.install(ctx, handlers)
    observatory_formal_streaming_routing.install(ctx, handlers)
    observatory_scale_hardening.install(ctx, handlers)
    observatory_cross_model_workload_hardening.install(ctx, handlers)
    observatory_genome_evidence_binding_hardening.install(ctx, handlers)

    # A public-prior-art challenger is not fully measured until every independent executable
    # campaign, including cross-model agreement and controlled-genome realization, has passed.
    required_reports = {
        "cross_model_qualification",
        "genome_realization_qualification",
    }
    present = {
        key for key, _statuses
        in observatory_prior_art_hardening_overlay._REQUIRED_SCORE_REPORTS
    }
    for key in sorted(required_reports - present):
        observatory_prior_art_hardening_overlay._REQUIRED_SCORE_REPORTS += (
            (key, ("PASS",)),)
    observatory_prior_art_hardening_overlay.install(ctx, handlers)

    out = base.install(ctx, handlers)
    out = observatory_cross_model_overlay.install(ctx, out)
    out = observatory_genome_realization_overlay.install(ctx, out)
    observatory_phase_gate_hardening.install(ctx, out)
    return out


__all__ = ["install"]
