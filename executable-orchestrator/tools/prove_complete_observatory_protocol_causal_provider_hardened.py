#!/usr/bin/env python3
"""Route and prove the authoritative E2E causal-aware localhost provider.

The readable core proof starts ``mock_observatory_protocol_server.py``. Causal genome realization
requires the final extension chain in ``mock_observatory_causal_server.py``, which imports the full
genome-aware provider and permits only hidden-scenario-exercised reference citations. This wrapper
rewrites only the exact disposable-clone localhost-provider command; every evaluator, Git, owner-
signature and real-provider operation passes through unchanged. The final verifier then requires one
and only one observed substitution and binds the selected provider bytes into its result.
"""
from __future__ import annotations

import os

import prove_complete_observatory_protocol_causal_hardened as base

EXTRA_CAUSAL_FILES = {
    "executable-orchestrator/lawmax21/observatory_audit_v3.py",
    "executable-orchestrator/lawmax21/observatory_genome_realization_hardening.py",
    "executable-orchestrator/lawmax21/observatory_causal_axis_attribution_hardening.py",
    "executable-orchestrator/tools/"
    "prove_complete_observatory_protocol_causal_provider_hardened.py",
    "executable-orchestrator/tools/mock_observatory_causal_server.py",
    "executable-orchestrator/lawmax21/"
    "observatory_causal_failure_classification_hardening.py",
}
for relative in EXTRA_CAUSAL_FILES:
    base.CAUSAL_FILES.add(relative)
    base.CORE.REQUIRED_PROTOCOL_FILES.add(relative)

_ORIGINAL_POPEN = base.CORE.subprocess.Popen
_ORIGINAL_VERIFY = base.CORE.verify_protocol
_PROVIDER_ROUTE = {
    "observed": False,
    "count": 0,
    "requested_path": None,
    "selected_path": None,
}


def _is_exact_core_provider(path):
    absolute = os.path.abspath(os.fspath(path))
    parent = os.path.dirname(absolute)
    grandparent = os.path.dirname(parent)
    return (
        os.path.basename(absolute) == "mock_observatory_protocol_server.py"
        and os.path.basename(parent) == "tools"
        and os.path.basename(grandparent) == "executable-orchestrator")


def _genome_provider_popen(command, *args, **kwargs):
    if isinstance(command, (list, tuple)) and len(command) >= 2 \
            and _is_exact_core_provider(command[1]):
        values = list(command)
        requested = os.path.abspath(os.fspath(values[1]))
        selected = os.path.join(
            os.path.dirname(requested), "mock_observatory_causal_server.py")
        if not os.path.isfile(selected):
            raise RuntimeError(
                "causal localhost provider is absent from the disposable clone: "
                + selected)
        values[1] = selected
        command = values
        _PROVIDER_ROUTE.update({
            "observed": True,
            "count": int(_PROVIDER_ROUTE["count"]) + 1,
            "requested_path": requested,
            "selected_path": os.path.abspath(selected),
        })
    return _ORIGINAL_POPEN(command, *args, **kwargs)


def _verify(repo, runtime, source_head, preflight, launch):
    verified = _ORIGINAL_VERIFY(
        repo, runtime, source_head, preflight, launch)
    expected = os.path.abspath(os.path.join(
        repo, "executable-orchestrator", "tools",
        "mock_observatory_causal_server.py"))
    if _PROVIDER_ROUTE.get("observed") is not True \
            or int(_PROVIDER_ROUTE.get("count", 0)) != 1 \
            or _PROVIDER_ROUTE.get("selected_path") != expected:
        raise RuntimeError(
            "authoritative E2E did not execute exactly one causal-aware localhost provider")
    verified["causal_local_provider_route_verified"] = {
        "requested_basename": os.path.basename(
            str(_PROVIDER_ROUTE.get("requested_path") or "")),
        "selected_path": os.path.relpath(expected, repo).replace("\\", "/"),
        "selected_sha256": base.CORE.sha256_file(expected),
        "substitutions_observed": int(_PROVIDER_ROUTE["count"]),
        "real_provider_routes_modified": False,
    }
    return verified


base.CORE.subprocess.Popen = _genome_provider_popen
base.CORE.verify_protocol = _verify
main = base.main
sha256_file = base.sha256_file

__all__ = ["main", "sha256_file"]


if __name__ == "__main__":
    import sys
    sys.exit(main())
