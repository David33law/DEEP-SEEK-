"""Compatibility entrypoint for the final integrated Observatory audit layer."""
from . import observatory_audit_v2 as base
from . import observatory_cross_model_overlay
from . import observatory_evaluator_routing_hardening
from . import observatory_phase_gate_hardening
from . import observatory_prior_art_hardening_overlay
from . import observatory_shared_corpus_hardening


def install(ctx, handlers):
    observatory_shared_corpus_hardening.install(ctx, handlers)
    observatory_evaluator_routing_hardening.install(ctx, handlers)
    if not any(key == "cross_model_qualification"
               for key, _statuses in
               observatory_prior_art_hardening_overlay._REQUIRED_SCORE_REPORTS):
        observatory_prior_art_hardening_overlay._REQUIRED_SCORE_REPORTS += (
            ("cross_model_qualification", ("PASS",)),)
    observatory_prior_art_hardening_overlay.install(ctx, handlers)
    out = base.install(ctx, handlers)
    out = observatory_cross_model_overlay.install(ctx, out)
    observatory_phase_gate_hardening.install(ctx, out)
    return out


__all__ = ["install"]
