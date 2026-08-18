#!/usr/bin/env python3
"""Static-v8 closure for one cwd-independent Observatory proof authority.

Static-v7 owns the complete calibrated fault topology. This strictly stronger zero-provider layer
adds two executable properties: every authoritative proof entrypoint must import successfully from
an unrelated working directory without inherited PYTHONPATH, and every retired/public compatibility
command must be a mechanically constrained monotonic shim to protocol-v6.

The probes use isolated Python subprocesses and never call proof main(), a provider, a candidate,
Docker, an owner ceremony or any mutating runtime path.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

import prove_observatory_protocol_static as root_static
import prove_observatory_protocol_static_v7 as previous

ROOT = previous.ROOT
REPORT = os.path.join(ROOT, "proof", "observatory-protocol-static-v8.json")
PROTOCOL_VERSION = "OBSERVATORY-OMEGA-RESEARCH-PROTOCOL-5"
TOOLS = os.path.dirname(os.path.abspath(__file__))
ORCH = os.path.dirname(TOOLS)

BOOTSTRAP_ENTRYPOINTS = {
    "executable-orchestrator/tools/run_observatory_proof.py",
    "executable-orchestrator/tools/prove_complete_observatory_protocol_v6.py",
    "executable-orchestrator/tools/prove_complete_observatory_protocol_fault_hardened.py",
}
COMPATIBILITY_SHIMS = dict(root_static.AUTHORITATIVE_SHIMS)
ENTRYPOINTS = tuple(sorted(BOOTSTRAP_ENTRYPOINTS | set(COMPATIBILITY_SHIMS)))


def _path(relative):
    return os.path.join(ROOT, *relative.split("/"))


def _write(path, value):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    temporary = path + ".tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=1, sort_keys=True)
        handle.flush(); os.fsync(handle.fileno())
    os.replace(temporary, path)


def _source_contract(relative):
    path = _path(relative)
    if not os.path.isfile(path):
        raise RuntimeError("authoritative/compatibility entrypoint missing: " + relative)

    if relative in COMPATIBILITY_SHIMS:
        root_static._assert_authoritative_shim(
            relative, require_bootstrap=COMPATIBILITY_SHIMS[relative])

    if relative in BOOTSTRAP_ENTRYPOINTS:
        text = open(path, encoding="utf-8").read()
        required = (
            'HERE = os.path.dirname(os.path.abspath(__file__))',
            'ORCH = os.path.dirname(HERE)',
            'LAWMAX_PACKAGE = os.path.join(ORCH, "lawmax21", "__init__.py")',
            'if ORCH not in sys.path:',
            'sys.path.insert(0, ORCH)',
        )
        missing = [token for token in required if token not in text]
        if missing:
            raise RuntimeError(
                relative + " lacks cwd-independent package bootstrap: "
                + ", ".join(missing))
    return path


def _standalone_import(relative):
    target = _source_contract(relative)
    # Script execution exposes only its own tools directory. Reproduce that seat while withholding
    # repository root/executable-orchestrator from cwd and PYTHONPATH.
    code = (
        "import importlib.util, os, sys; "
        f"tools={TOOLS!r}; target={target!r}; "
        "sys.path.insert(0, tools); "
        "spec=importlib.util.spec_from_file_location('obs_entrypoint_probe', target); "
        "mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); "
        "assert callable(getattr(mod, 'main', None)); "
        "assert os.path.realpath(" + repr(ORCH) + ") in "
        "[os.path.realpath(x) for x in sys.path if x]"
    )
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONNOUSERSITE"] = "1"
    with tempfile.TemporaryDirectory(prefix="obs-entrypoint-import-") as cwd:
        result = subprocess.run(
            [sys.executable, "-I", "-c", code],
            cwd=cwd, env=env, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise RuntimeError(
            relative + " standalone import failed: "
            + ((result.stdout or "") + "\n" + (result.stderr or ""))[-4000:])
    return {
        "status": "PASS",
        "returncode": 0,
        "cwd_independent": True,
        "python_isolated": True,
        "inherited_pythonpath": False,
        "final_authority": root_static.AUTHORITATIVE_PROOF_TARGET
            if relative in COMPATIBILITY_SHIMS else "authoritative-core",
        "compatibility_shim": relative in COMPATIBILITY_SHIMS,
    }


def main():
    result = {
        "proof": "observatory-protocol-static-v8-entrypoint-import-closure",
        "protocol_version": PROTOCOL_VERSION,
        "provider_calls": 0,
        "candidate_executions": 0,
        "docker_runs": 0,
        "status": "FAIL",
    }
    try:
        if previous.main() != 0:
            raise RuntimeError("inherited static-v7 closure failed")
        with open(previous.REPORT, encoding="utf-8") as handle:
            inherited = json.load(handle)
        if inherited.get("status") != "PASS" \
                or inherited.get("protocol_version") != PROTOCOL_VERSION:
            raise RuntimeError("static-v7 receipt is not PASS")

        if root_static.AUTHORITATIVE_PROOF_TARGET != \
                "prove_complete_observatory_protocol_v6":
            raise RuntimeError("root static proof authority drifted away from protocol-v6")
        probes = {relative: _standalone_import(relative)
                  for relative in ENTRYPOINTS}

        from lawmax21 import observatory_protocol
        protocol_files = set(observatory_protocol.protocol_files(ROOT))
        missing = sorted(set(ENTRYPOINTS) - protocol_files)
        if missing:
            raise RuntimeError(
                "standalone-entrypoint closure files omitted from protocol census: "
                + ", ".join(missing))

        result.update(inherited)
        result.update({
            "proof": "observatory-protocol-static-v8-entrypoint-import-closure",
            "status": "PASS",
            "provider_calls": 0,
            "candidate_executions": 0,
            "docker_runs": 0,
            "protocol_bundle_sha256":
                observatory_protocol.protocol_bundle_sha256(ROOT),
            "authoritative_entrypoint_standalone_import_static_bound": True,
            "compatibility_proof_shims_monotonic_static_bound": True,
            "authoritative_proof_target": root_static.AUTHORITATIVE_PROOF_TARGET,
            "authoritative_entrypoint_import_probes": probes,
            "authoritative_entrypoint_import_count": len(probes),
            "compatibility_proof_shim_count": len(COMPATIBILITY_SHIMS),
            "compatibility_proof_shims": sorted(COMPATIBILITY_SHIMS),
            "authoritative_entrypoints_cwd_independent": True,
            "authoritative_entrypoints_pythonpath_independent": True,
        })
    except Exception as exc:
        result["reason"] = f"{type(exc).__name__}: {exc}"

    _write(REPORT, result)
    print(json.dumps(result, ensure_ascii=False, indent=1, sort_keys=True))
    print("proof report:", REPORT)
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
