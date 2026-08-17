"""Compatibility entrypoint for the final integrated Observatory audit layer."""
from . import observatory_audit_v2 as base
from . import observatory_prior_art_hardening_overlay


def install(ctx, handlers):
    observatory_prior_art_hardening_overlay.install(ctx, handlers)
    return base.install(ctx, handlers)


__all__ = ["install"]
