#!/usr/bin/env python3
"""Hardening layer for the authoritative protocol-v4 E2E proof.

The underlying driver retains the readable gate/resume and artifact verification flow. This module
forces the exact production candidate-isolation backend even for the local provider, requires the
streaming formal evaluator and final setup/preflight routes in the signed census, and independently
checks that every specialized crown report came from the bounded evaluator path.
"""
import json
import os

import prove_complete_observatory_protocol as base

base.REQUIRED_PROTOCOL_FILES.discard(
    "private-evaluator/evaluator/observatory_formal_arena_v2.py")
base.REQUIRED_PROTOCOL_FILES.update({
    "private-evaluator/evaluator/observatory_formal_arena_v3.py",
    "executable-orchestrator/lawmax21/observatory_formal_streaming_routing.py",
    "executable-orchestrator/lawmax21/observatory_setup_v4.py",
    "executable-orchestrator/lawmax21/observatory_preflight_v5.py",
    "executable-orchestrator/tools/prove_observatory_protocol_static_v2.py",
})

_original_py = base.py
_original_verify = base.verify_protocol


def _container_py(path, *args, cwd=None, env=None, timeout=28800):
    values = list(args)
    if os.path.basename(path) == "run_observatory.py" and "--backend" in values:
        index = values.index("--backend")
        if index + 1 >= len(values):
            raise RuntimeError("proof runner has malformed --backend argument")
        values[index + 1] = "container"
    return _original_py(path, *values, cwd=cwd, env=env, timeout=timeout)


def _verify(repo, runtime, source_head, preflight, launch):
    verified = _original_verify(repo, runtime, source_head, preflight, launch)
    backend = (preflight.get("container_backend") or {}).get("backend")
    if backend != "container":
        raise RuntimeError("full E2E proof did not exercise production container isolation")
    mission_files = set((preflight.get("signed_mission") or {}).get(
        "research_protocol_files") or [])
    required = {
        "private-evaluator/evaluator/observatory_formal_arena_v3.py",
        "executable-orchestrator/lawmax21/observatory_formal_streaming_routing.py",
        "executable-orchestrator/lawmax21/observatory_setup_v4.py",
        "executable-orchestrator/lawmax21/observatory_preflight_v5.py",
    }
    missing = sorted(required - mission_files)
    if missing:
        raise RuntimeError("signed protocol omitted final routes: " + ", ".join(missing))
    incumbent = verified["incumbent"]
    formal_paths = [path for path in os.listdir(os.path.join(runtime, "reports"))
                    if path.startswith(f"formal-crown-{incumbent}-")
                    and path.endswith(".json")]
    if len(formal_paths) != 2:
        raise RuntimeError("streaming formal crown report count is not two")
    for name in formal_paths:
        report = json.load(open(os.path.join(runtime, "reports", name), encoding="utf-8"))
        if report.get("behavioral_digest_mode") != "ordered-length-delimited-stream-v1":
            raise RuntimeError(name + ": crown did not use streaming formal digest mode")
    audit = verified["audit"]
    if audit.get("proof_mode") is not True \
            or (audit.get("workload_policy") or {}).get("proof_mode") is not True:
        raise RuntimeError("zero-cost proof workload was not explicitly audited")
    verified["exact_candidate_backend"] = "container"
    verified["streaming_formal_crown_verified"] = True
    return verified


base.py = _container_py
base.verify_protocol = _verify
main = base.main
sha256_file = base.sha256_file

__all__ = ["main", "sha256_file"]


if __name__ == "__main__":
    import sys
    sys.exit(main())
