"""Final launcher entrypoint with candidate identity and owner-signature hardening.

``observatory_launcher_v2`` retains the readable production launcher, while this final seat binds its
actual ``observatory_audit`` global to ``observatory_audit_v3`` before any context is built. The v3
audit injects the explicit candidate ID into both genome-auditor prompts and then delegates to the
complete causal/dossier topology. The same seat also wraps the foundational dossier builder so owner
public-key, signed-decisions and approval-signature verification remain installed before the final
INDEPENDENT_AUDIT handler captures it.
"""
from . import observatory_audit_v3 as final_audit
from . import observatory_launcher_v2 as base
from . import observatory_owner_gate_signature_hardening as owner_signatures
from . import observatory_supremacy_dossier_hardening as foundation


# ``launcher_v2.base`` is the real ``observatory_launcher`` module. Its ``build_context`` function
# resolves the module-global ``observatory_audit`` at execution time, so binding that exact seat here
# makes audit-v3 load-bearing for --preflight, --launch and --resume rather than a dead compatibility
# module that merely imports successfully.
_launcher = getattr(base, "base", None)
if _launcher is None or not hasattr(_launcher, "build_context"):
    raise RuntimeError("final launcher cannot locate the production build_context seat")
_launcher.observatory_audit = final_audit
_launcher._final_observatory_audit_v3_bound = True


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
