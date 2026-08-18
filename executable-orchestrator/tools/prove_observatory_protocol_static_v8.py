#!/usr/bin/env python3
"""Static-v8 closure for one proof authority and locale-independent trusted transport.

Static-v7 owns the complete calibrated fault topology. This strictly stronger zero-provider layer
adds: cwd/PYTHONPATH-independent authoritative imports, mechanically constrained monotonic legacy
shims, and executable proof that Unicode legal/candidate text is transported as strict UTF-8 rather
than through the host locale. Host codec/process failures must be infrastructure-invalid and can
never become causal evidence.

The probes never call proof main(), a provider, a candidate, Docker, an owner ceremony or a mutating
runtime path. The only child execution is an isolated Python UTF-8 round-trip over trusted text I/O.
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
EVALUATOR = os.path.join(ROOT, "private-evaluator", "evaluator")

BOOTSTRAP_ENTRYPOINTS = {
    "executable-orchestrator/tools/run_observatory_proof.py",
    "executable-orchestrator/tools/prove_complete_observatory_protocol_v6.py",
    "executable-orchestrator/tools/prove_complete_observatory_protocol_fault_hardened.py",
}
COMPATIBILITY_SHIMS = dict(root_static.AUTHORITATIVE_SHIMS)
ENTRYPOINTS = tuple(sorted(BOOTSTRAP_ENTRYPOINTS | set(COMPATIBILITY_SHIMS)))

UTF8_PROCESS = "executable-orchestrator/lawmax21/observatory_utf8_process.py"
UTF8_ORCHESTRATOR_ROUTES = {
    "executable-orchestrator/lawmax21/observatory_setup.py",
    "executable-orchestrator/lawmax21/observatory_evaluator_routing_hardening.py",
    "executable-orchestrator/lawmax21/observatory_formal_streaming_routing.py",
    "executable-orchestrator/lawmax21/observatory_cross_model_workload_hardening.py",
    "executable-orchestrator/lawmax21/observatory_causal_behavioral_probe_hardening.py",
}
UTF8_EVALUATOR_ROUTES = {
    "private-evaluator/evaluator/observatory_axis_probe_arena.py",
    "private-evaluator/evaluator/observatory_axis_probe_arena_v2.py",
    "private-evaluator/evaluator/observatory_axis_probe_calibration.py",
    "private-evaluator/evaluator/observatory_systems_arena_v2.py",
    "private-evaluator/evaluator/observatory_distributed_arena_v2.py",
}
CAUSAL_CLASSIFIER = (
    "executable-orchestrator/lawmax21/"
    "observatory_causal_failure_classification_hardening.py")
FAULT_E2E = (
    "executable-orchestrator/tools/"
    "prove_complete_observatory_protocol_fault_hardened.py")


def _path(relative):
    return os.path.join(ROOT, *relative.split("/"))


def _text(relative):
    with open(_path(relative), encoding="utf-8") as handle:
        return handle.read()


def _require(text, tokens, label):
    missing = [token for token in tokens if token not in text]
    if missing:
        raise RuntimeError(label + " lacks: " + ", ".join(missing))


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
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    with tempfile.TemporaryDirectory(prefix="obs-entrypoint-import-") as cwd:
        result = subprocess.run(
            [sys.executable, "-I", "-c", code],
            cwd=cwd, env=env, capture_output=True, text=True,
            encoding="utf-8", errors="strict", timeout=120)
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
        "transport_encoding": "utf-8",
        "final_authority": root_static.AUTHORITATIVE_PROOF_TARGET
            if relative in COMPATIBILITY_SHIMS else "authoritative-core",
        "compatibility_shim": relative in COMPATIBILITY_SHIMS,
    }


def _verify_utf8_topology():
    process = _text(UTF8_PROCESS)
    _require(process, (
        'ENCODING = "utf-8"',
        'result["PYTHONIOENCODING"] = ENCODING',
        'result["PYTHONUTF8"] = "1"',
        'encoding=ENCODING',
        'errors="strict"'),
        "canonical UTF-8 process seat")

    for relative in UTF8_ORCHESTRATOR_ROUTES:
        text = _text(relative)
        _require(text, (
            "observatory_utf8_process",
            "utf8_process"),
            relative + " UTF-8 routing")

    evaluator_v2 = _text(
        "private-evaluator/evaluator/observatory_axis_probe_arena_v2.py")
    _require(evaluator_v2, (
        "import bounded_subprocess",
        "bounded_subprocess.install(base.subprocess)"),
        "axis-probe bounded UTF-8 transport")

    axis_base = _text(
        "private-evaluator/evaluator/observatory_axis_probe_arena.py")
    _require(axis_base, (
        '"unicodeencodeerror"', '"unicodedecodeerror"',
        '"charmap codec"', "_HOST_INFRASTRUCTURE_EXCEPTIONS",
        "UnicodeError", "subprocess.SubprocessError",
        "ensure_ascii=True"),
        "axis-probe infrastructure classification")

    calibration = _text(
        "private-evaluator/evaluator/observatory_axis_probe_calibration.py")
    _require(calibration, (
        'env["PYTHONIOENCODING"] = "utf-8"',
        'env["PYTHONUTF8"] = "1"',
        'encoding="utf-8", errors="strict"',
        'report["calibration_transport_encoding"] = "utf-8"',
        'report["failed_route"]',
        '"transport_encoding": "utf-8"'),
        "axis-probe calibration UTF-8 transport")
    if calibration.index("baseline = _run(") >= calibration.index("mutant_report = _run("):
        raise RuntimeError("axis calibration no longer validates baseline before mutant execution")
    baseline_validation = calibration.index("if not _valid_report(", calibration.index("baseline = _run("))
    mutant_execution = calibration.index("mutant_report = _run(")
    if baseline_validation >= mutant_execution:
        raise RuntimeError("axis calibration mutant may execute before baseline validity is known")

    for relative in (
            "private-evaluator/evaluator/observatory_systems_arena_v2.py",
            "private-evaluator/evaluator/observatory_distributed_arena_v2.py"):
        text = _text(relative)
        _require(text, (
            'encoding="utf-8"', 'errors="strict"',
            'report["transport_encoding"] = "utf-8"',
            "ensure_ascii=True"),
            relative + " crash UTF-8 transport")

    classifier = _text(CAUSAL_CLASSIFIER)
    _require(classifier, (
        '"unicodeencodeerror"', '"unicodedecodeerror"',
        '"charmap codec"',
        '"host_locale_failure_cannot_earn_causal_credit": True'),
        "generic causal Unicode classification")

    fault = _text(FAULT_E2E)
    _require(fault, (
        "def _utf8_core_run",
        'result["PYTHONIOENCODING"] = "utf-8"',
        'result["PYTHONUTF8"] = "1"',
        'encoding="utf-8"', 'errors="strict"',
        "CORE.run = _utf8_core_run",
        'verified["trusted_process_transport_utf8_verified"] = True'),
        "complete E2E UTF-8 transport")

    return {
        "canonical_process_seat": UTF8_PROCESS,
        "orchestrator_routes": sorted(UTF8_ORCHESTRATOR_ROUTES),
        "evaluator_routes": sorted(UTF8_EVALUATOR_ROUTES),
        "causal_classifier": CAUSAL_CLASSIFIER,
        "e2e_route": FAULT_E2E,
    }


def _unicode_roundtrip():
    from lawmax21 import observatory_utf8_process as utf8_process
    payload = "Νόμος·Ελληνικό δίκαιο·δοκιμή UTF-8·§"
    child = utf8_process.run(
        [sys.executable, "-c",
         "import sys; data=sys.stdin.read(); sys.stdout.write(data)"],
        input=payload, capture_output=True, timeout=30)
    if child.returncode != 0 or child.stdout != payload or child.stderr:
        raise RuntimeError("trusted UTF-8 child round-trip failed")
    return {
        "status": "PASS", "encoding": utf8_process.ENCODING,
        "characters": len(payload), "bytes": len(payload.encode("utf-8")),
    }


def _unicode_failure_classifier():
    if EVALUATOR not in sys.path:
        sys.path.insert(0, EVALUATOR)
    import observatory_axis_probe_arena as axis_probe
    error = UnicodeEncodeError(
        "cp1252", "Ν", 0, 1, "character maps to <undefined>")
    if axis_probe._candidate_failure(error) is not False:
        raise RuntimeError("host UnicodeEncodeError can still earn candidate causal credit")
    decode_error = UnicodeDecodeError(
        "cp1252", b"\x81", 0, 1, "character maps to <undefined>")
    if axis_probe._candidate_failure(decode_error) is not False:
        raise RuntimeError("host UnicodeDecodeError can still earn candidate causal credit")
    return {
        "status": "PASS",
        "unicode_encode_error": "infrastructure_or_harness",
        "unicode_decode_error": "infrastructure_or_harness",
        "candidate_causal_credit": False,
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
        utf8_topology = _verify_utf8_topology()
        utf8_roundtrip = _unicode_roundtrip()
        unicode_classifier = _unicode_failure_classifier()

        from lawmax21 import observatory_protocol
        protocol_files = set(observatory_protocol.protocol_files(ROOT))
        required_files = set(ENTRYPOINTS) | {UTF8_PROCESS, *UTF8_ORCHESTRATOR_ROUTES,
                                            *UTF8_EVALUATOR_ROUTES, CAUSAL_CLASSIFIER,
                                            FAULT_E2E}
        missing = sorted(required_files - protocol_files)
        if missing:
            raise RuntimeError(
                "static-v8 closure files omitted from protocol census: "
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
            "trusted_utf8_process_static_bound": True,
            "production_evaluator_utf8_static_bound": True,
            "axis_probe_utf8_transport_static_bound": True,
            "axis_calibration_utf8_static_bound": True,
            "fault_crash_utf8_static_bound": True,
            "e2e_utf8_transport_static_bound": True,
            "host_unicode_failure_noncausal_static_bound": True,
            "utf8_unicode_roundtrip_static_bound": True,
            "utf8_transport_topology": utf8_topology,
            "utf8_unicode_roundtrip": utf8_roundtrip,
            "unicode_failure_classifier": unicode_classifier,
        })
    except Exception as exc:
        result["reason"] = f"{type(exc).__name__}: {exc}"

    _write(REPORT, result)
    print(json.dumps(result, ensure_ascii=True, indent=1, sort_keys=True))
    print("proof report:", REPORT)
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
