"""Final launcher with audit-v3, owner-signature and axis-calibration hardening.

``observatory_launcher_v2`` retains the readable production launcher. This final seat binds the real
``observatory_launcher`` module to ``observatory_audit_v3`` and ``observatory_preflight_v6`` before
any context is built. Production launch/resume therefore cannot bypass candidate-identity injection,
causal/dossier topology, portable owner-signature verification or exhaustive axis-probe calibration.
"""
from . import observatory_audit_v3 as final_audit
from . import observatory_launcher_v2 as base
from . import observatory_owner_gate_signature_hardening as owner_signatures
from . import observatory_preflight_v6 as final_preflight
from . import observatory_supremacy_dossier_hardening as foundation


# ``launcher_v2.base`` is the real ``observatory_launcher`` module. Its functions resolve these
# module globals at execution time, so binding the exact seats here makes them load-bearing for
# --preflight, --launch and --resume rather than dead compatibility imports.
_launcher = getattr(base, "base", None)
if _launcher is None or not hasattr(_launcher, "build_context"):
    raise RuntimeError("final launcher cannot locate the production build_context seat")
_launcher.observatory_audit = final_audit
_launcher.observatory_preflight = final_preflight
_launcher._final_observatory_audit_v3_bound = True
_launcher._final_observatory_preflight_v6_bound = True


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
