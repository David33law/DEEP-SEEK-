"""Make hard-minimum evaluation phase-aware.

Semantic implementation selection occurs before scale, bounded-formal and interoperability sources
exist. Their hard dimensions must not reject every semantic implementation as zero before those
architecture-level campaigns run. The later overlays have their own fail-closed qualification,
frontier, replication and crown gates.
"""
from . import observatory_implementation_search_overlay as implementation

_DOWNSTREAM = {
    "scale_qualification": {
        "national_scale_survival", "scale_events_per_second",
        "scale_batch_latency_p95", "scale_bytes_per_event"},
    "formal_qualification": {
        "machine_checked_model_survival", "formal_trace_coverage"},
    "interoperability_qualification": {
        "legal_interoperability_survival", "interoperability_case_coverage"},
}


def install(_ctx, handlers):
    if getattr(implementation, "_phase_gate_hardening_installed", False):
        return dict(handlers)
    original = implementation._hard_failures

    def hard_failures(context, candidate_id):
        failures = list(original(context, candidate_id))
        scores = context.scores.get(candidate_id) or {}
        inactive = set()
        for report_key, dimensions in _DOWNSTREAM.items():
            if not scores.get(report_key):
                inactive.update(dimensions)
        return [failure for failure in failures
                if failure.get("dimension") not in inactive]

    implementation._hard_failures = hard_failures
    implementation._phase_gate_hardening_installed = True
    return dict(handlers)
