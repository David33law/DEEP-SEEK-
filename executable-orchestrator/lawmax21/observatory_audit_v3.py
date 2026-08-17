"""Final integrated audit installer for Observatory protocol v5.

This wrapper installs explicit candidate-identity binding before the two genome-realization auditors,
then delegates to the compatibility audit topology. It exists as a separately importable final seat so
static proof can verify the hardening without mutating historical modules.
"""
from . import observatory_audit as base
from . import observatory_genome_realization_hardening


def install(ctx, handlers):
    observatory_genome_realization_hardening.install(ctx, handlers)
    return base.install(ctx, handlers)


__all__ = ["install"]
