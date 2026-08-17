"""Diversify the two controlled-genome auditors at the actual model-call seat.

Auditor A follows invariant-to-code proof obligations at deterministic temperature. Auditor B follows
failure/removal/falsifier analysis with an independently sampled response. Both remain constrained by
the same strict schema and deterministic citation validator; diversity cannot weaken admission.
"""
from types import MethodType


PROFILES = {
    "genome-realization-auditor-A": {
        "temperature": 0.0,
        "directive": (
            "INDEPENDENT AUDITOR A — invariant-to-code perspective. Start from each frozen INV-* "
            "obligation and prove the shortest exact chain to AST definitions and passing executable "
            "evidence. Reject any axis whose chain is incomplete. ")},
    "genome-realization-auditor-B": {
        "temperature": 0.35,
        "directive": (
            "INDEPENDENT AUDITOR B — counterexample/removal perspective. For every axis attempt to "
            "show that the declared class is merely a label, stale artifact or non-load-bearing "
            "mechanism; approve it only if the supplied definitions, removal failure, falsifier and "
            "passing source-bound evidence defeat that attack. ")},
}


def install(ctx, handlers):
    if getattr(ctx, "_genome_auditor_diversity_installed", False):
        return dict(handlers)
    original = ctx.ask

    def ask(self, role, ticket, task, context_blocks, schema,
            line="main", temperature=0.0):
        profile = PROFILES.get(role)
        if profile:
            task = profile["directive"] + task
            temperature = profile["temperature"]
        return original(
            role, ticket, task, context_blocks, schema,
            line=line, temperature=temperature)

    ctx.ask = MethodType(ask, ctx)
    ctx._genome_auditor_profiles = {
        role: dict(profile) for role, profile in PROFILES.items()}
    ctx._genome_auditor_diversity_installed = True
    return dict(handlers)
