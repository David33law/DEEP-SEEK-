#!/usr/bin/env python3
"""Final static extension for streaming formal, protocol-v5 and source-bound genome routing."""
import json
import os
import sys

import prove_observatory_protocol_static as base

ROOT = base.ROOT
REPORT = os.path.join(ROOT, "proof", "observatory-protocol-static.json")
EXTRA_MODULES = [
    "lawmax21.observatory_setup_v4",
    "lawmax21.observatory_preflight_v5",
    "lawmax21.observatory_formal_streaming_routing",
    "lawmax21.observatory_scale_hardening",
    "lawmax21.observatory_shared_corpus_hardening",
    "lawmax21.observatory_evaluator_routing_hardening",
    "lawmax21.observatory_build_schema_hardening",
    "lawmax21.observatory_genome_realization_overlay",
    "lawmax21.observatory_genome_evidence_binding_hardening",
]
EXTRA_FILES = {
    "private-evaluator/evaluator/observatory_formal_arena_v3.py",
    "executable-orchestrator/lawmax21/observatory_setup_v4.py",
    "executable-orchestrator/lawmax21/observatory_preflight_v5.py",
    "executable-orchestrator/lawmax21/observatory_formal_streaming_routing.py",
    "executable-orchestrator/lawmax21/observatory_build_schema_hardening.py",
    "executable-orchestrator/lawmax21/observatory_genome_realization_overlay.py",
    "executable-orchestrator/lawmax21/observatory_genome_evidence_binding_hardening.py",
    "profiles/national-observatory/GENOME-REALIZATION-CONTRACT.md",
    "executable-orchestrator/tools/mock_observatory_genome_server.py",
}
for module in EXTRA_MODULES:
    if module not in base.EXPECTED_MODULES:
        base.EXPECTED_MODULES.append(module)
base.EXPECTED_FILES.update(EXTRA_FILES)


def _text(relative):
    return open(
        os.path.join(ROOT, *relative.split("/")), encoding="utf-8").read()


def main():
    code = base.main()
    if code != 0:
        return code
    report = json.load(open(REPORT, encoding="utf-8"))
    try:
        audit = _text(
            "executable-orchestrator/lawmax21/observatory_audit.py")
        ordered = [
            "observatory_build_schema_hardening.install",
            "observatory_shared_corpus_hardening.install",
            "observatory_evaluator_routing_hardening.install",
            "observatory_formal_streaming_routing.install",
            "observatory_scale_hardening.install",
            "observatory_cross_model_workload_hardening.install",
            "observatory_genome_evidence_binding_hardening.install",
            "observatory_prior_art_hardening_overlay.install",
            "base.install",
            "observatory_cross_model_overlay.install",
            "observatory_genome_realization_overlay.install",
            "observatory_phase_gate_hardening.install"]
        positions = [audit.index(token) for token in ordered]
        if positions != sorted(positions):
            raise RuntimeError(
                "final hardening/overlay order is wrong")
        setup = _text("setup_observatory.py")
        launcher = _text(
            "executable-orchestrator/lawmax21/observatory_launcher_v2.py")
        routing = _text(
            "executable-orchestrator/lawmax21/"
            "observatory_formal_streaming_routing.py")
        evaluator_routing = _text(
            "executable-orchestrator/lawmax21/"
            "observatory_evaluator_routing_hardening.py")
        evidence_binding = _text(
            "executable-orchestrator/lawmax21/"
            "observatory_genome_evidence_binding_hardening.py")
        phase = _text(
            "executable-orchestrator/lawmax21/"
            "observatory_phase_gate_hardening.py")
        protocol = _text(
            "executable-orchestrator/lawmax21/observatory_protocol.py")
        if "observatory_setup_v4" not in setup:
            raise RuntimeError("top-level setup does not use setup-v4")
        if "observatory_preflight_v5" not in launcher:
            raise RuntimeError("launcher does not use preflight-v5")
        if "observatory_formal_arena_v3.py" not in routing:
            raise RuntimeError(
                "production formal routing does not use streaming v3")
        if "candidate_sha256" not in routing \
                or "candidate_sha256" not in evaluator_routing:
            raise RuntimeError(
                "specialized evaluator reports are not source-hash-bound")
        if "genome_realization_qualification" not in phase:
            raise RuntimeError(
                "genome realization hard minimum is not phase-aware")
        if "OBSERVATORY-OMEGA-RESEARCH-PROTOCOL-5" not in protocol:
            raise RuntimeError("protocol-v5 binding is absent")
        if "no passing source-bound evidence" not in evidence_binding \
                or "candidate_sha256" not in evidence_binding:
            raise RuntimeError(
                "genome evidence hardening does not reject stale reports")
        build_schema = _text(
            "executable-orchestrator/lawmax21/"
            "observatory_build_schema_hardening.py")
        for path in (
                "candidate.py", "systems_candidate.py",
                "distributed_candidate.py", "scale_candidate.py",
                "formal_candidate.py", "interoperability_candidate.py"):
            if path not in build_schema:
                raise RuntimeError(
                    "strict source schema omitted " + path)
        mock = _text(
            "executable-orchestrator/tools/"
            "mock_observatory_genome_server.py")
        if "genome-realization-auditor-" not in mock \
                or "definitions" not in mock \
                or "PERSISTED EVIDENCE CATALOG" not in mock:
            raise RuntimeError(
                "final local provider does not exercise genome realization")
        report.update({
            "status": "PASS",
            "final_static_extension": "PASS",
            "extra_modules_imported": EXTRA_MODULES,
            "streaming_formal_routing_verified": True,
            "setup_v4_verified": True,
            "preflight_v5_verified": True,
            "strict_build_schema_verified": True,
            "genome_realization_routing_verified": True,
            "genome_evidence_source_binding_verified": True,
            "protocol_v5_verified": True})
    except Exception as exc:
        report["status"] = "FAIL"
        report["reason"] = str(exc)
    with open(REPORT, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False,
                  indent=1, sort_keys=True)
    print(json.dumps(report, ensure_ascii=False,
                     indent=1, sort_keys=True))
    return 0 if report.get("status") == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
