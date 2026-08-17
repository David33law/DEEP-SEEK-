"""Final launcher entrypoint with cryptographic owner-gate dossier verification installed.

The final audit calls ``observatory_supremacy_dossier_hardening.install`` before constructing the
INDEPENDENT_AUDIT handler. Wrap that exact install seat so the portable owner-public-key and signed-
decisions snapshots plus independent approval-signature verification are applied after foundational
dossier binding and before the dossier handler captures the builder.
"""
from . import observatory_launcher_v2 as base
from . import observatory_owner_gate_signature_hardening as owner_signatures
from . import observatory_supremacy_dossier_hardening as foundation


if not getattr(foundation, "_owner_signature_launcher_patch_installed", False):
    _original_foundation_install = foundation.install

    def _foundation_then_signatures(ctx, handlers):
        out = _original_foundation_install(ctx, handlers)
        owner_signatures.install(ctx, handlers)
        return out

    foundation.install = _foundation_then_signatures
    foundation._owner_signature_launcher_patch_installed = True


main = base.main

__all__ = ["main"]
