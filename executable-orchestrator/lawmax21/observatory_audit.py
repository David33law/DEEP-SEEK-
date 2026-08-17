"""Compatibility entrypoint for the final integrated Observatory audit layer."""
from . import observatory_audit_v2 as base
from . import observatory_build_schema_hardening
from . import observatory_cross_model_overlay
from . import observatory_cross_model_workload_hardening
from . import observatory_evaluator_routing_hardening
from . import observatory_formal_streaming_routing
from . import observatory_genome_auditor_diversity_hardening
from . import observatory_genome_cross_auditor_hardening
from . import observatory_genome_evidence_binding_hardening
from . import observatory_genome_realization_overlay
from . import observatory_phase_gate_hardening
from . import observatory_prior_art_hardening_overlay
from . import observatory_scale_hardening
from . import observatory_semantic_evidence_binding_hardening
from . import observatory_shared_corpus_hardening
from . import observatory_supremacy_dossier_overlay


def install(ctx, handlers):
    # Patch shared schemas and the two genuinely independent genome-auditor model-call profiles
    # before any overlay captures ctx.ask or constructs handler closures.
    observatory_build_schema_hardening.install(ctx, handlers)
    observatory_genome_auditor_diversity_hardening.install(ctx, handlers)
    observatory_shared_corpus_hardening.install(ctx, handlers)
    observatory_evaluator_routing_hardening.install(ctx, handlers)
    observatory_semantic_evidence_binding_hardening.install(ctx, handlers)
    observatory_formal_streaming_routing.install(ctx, handlers)
    observatory_scale_hardening.install(ctx, handlers)
    observatory_cross_model_workload_hardening.install(ctx, handlers)

    # Tighten the genome auditor before its handler wrappers are constructed. Every citation must
    # bind an actual definition and passing exact-source report, and the two auditors must produce
    # materially different per-axis citation maps rather than duplicated prose with different IDs.
    observatory_genome_evidence_binding_hardening.install(ctx, handlers)
    observatory_genome_cross_auditor_hardening.install(ctx, handlers)

    # Public-prior-art challengers are not fully measured until all executable campaigns pass.
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

    # Build the complete semantic/durable/distributed/scale/formal/interoperability/search stack,
    # then add cross-model, executable-genome and deterministic final-dossier gates around the same
    # signed state-machine handlers.
    out = base.install(ctx, handlers)
    out = observatory_cross_model_overlay.install(ctx, out)
    out = observatory_genome_realization_overlay.install(ctx, out)
    out = observatory_supremacy_dossier_overlay.install(ctx, out)

    # Hard minima become active only after the corresponding report exists; once active they remain
    # ordinary fail-closed Pareto gates.
    observatory_phase_gate_hardening.install(ctx, out)
    return out


__all__ = ["install"]
