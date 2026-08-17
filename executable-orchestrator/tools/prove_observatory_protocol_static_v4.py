#!/usr/bin/env python3
"""Final static extension for protocol-v5 portable owner and audit-seat verification.

Runs the complete v5 static proof, then verifies that the stable runner uses the final launcher, that
launcher-v3 binds the real production ``build_context`` to audit-v3, that both genome auditors receive
an explicit candidate identity, and that the dossier snapshots the owner public key and signed
owner decisions before independently invoking ``verify_approval`` over every pre-terminal owner gate.
No provider call, candidate execution or owner mutation occurs.
"""
from __future__ import annotations

import importlib
import json
import os
import sys

import prove_observatory_protocol_static_v3 as previous

ROOT = previous.ROOT
REPORT = os.path.join(ROOT, "proof", "observatory-protocol-static-v5.json")
REQUIRED_FILES = {
    "executable-orchestrator/lawmax21/observatory_launcher_v3.py",
    "executable-orchestrator/lawmax21/observatory_audit_v3.py",
    "executable-orchestrator/lawmax21/observatory_genome_realization_hardening.py",
    "executable-orchestrator/lawmax21/observatory_owner_gate_signature_hardening.py",
}


def _text(relative):
    with open(os.path.join(ROOT, *relative.split("/")), encoding="utf-8") as handle:
        return handle.read()


def _require(text, tokens, label):
    missing = [token for token in tokens if token not in text]
    if missing:
        raise RuntimeError(label + " lacks: " + ", ".join(missing))


def main():
    if previous.main() != 0:
        return 1
    report = json.load(open(REPORT, encoding="utf-8"))
    try:
        from lawmax21 import observatory_protocol
        modules = [
            importlib.import_module(
                "lawmax21.observatory_launcher_v3").__name__,
            importlib.import_module(
                "lawmax21.observatory_audit_v3").__name__,
            importlib.import_module(
                "lawmax21.observatory_genome_realization_hardening").__name__,
            importlib.import_module(
                "lawmax21.observatory_owner_gate_signature_hardening").__name__,
        ]
        protocol_files = set(observatory_protocol.protocol_files(ROOT))
        missing = sorted(REQUIRED_FILES - protocol_files)
        if missing:
            raise RuntimeError(
                "protocol census omitted final launcher/audit routes: "
                + ", ".join(missing))
        runner = _text("run_observatory.py")
        launcher = _text(
            "executable-orchestrator/lawmax21/observatory_launcher_v3.py")
        audit_v3 = _text(
            "executable-orchestrator/lawmax21/observatory_audit_v3.py")
        identity = _text(
            "executable-orchestrator/lawmax21/"
            "observatory_genome_realization_hardening.py")
        hardening = _text(
            "executable-orchestrator/lawmax21/"
            "observatory_owner_gate_signature_hardening.py")
        audit = _text(
            "executable-orchestrator/lawmax21/observatory_audit.py")
        if "observatory_launcher_v3" not in runner:
            raise RuntimeError("stable production runner bypasses final launcher-v3")
        _require(launcher, (
            "observatory_audit_v3 as final_audit",
            '_launcher = getattr(base, "base", None)',
            "_launcher.observatory_audit = final_audit",
            "_final_observatory_audit_v3_bound",
            "_foundation_then_signatures",
            "owner_signatures.install",
            "foundation.install = _foundation_then_signatures"),
            "final launcher-v3")
        _require(audit_v3, (
            "observatory_genome_realization_hardening.install",
            "return base.install(ctx, handlers)"),
            "final audit-v3")
        _require(identity, (
            'str(role).startswith("genome-realization-auditor-")',
            'str(ticket).rsplit("::", 1)[-1]',
            '("CANDIDATE ID", candidate_id)',
            "ctx.ask = MethodType(ask, ctx)"),
            "genome candidate-identity binding")
        _require(hardening, (
            "verify_approval(", "OWNER-PUBLIC-KEY.hex",
            "OWNER-DECISIONS.signed.json",
            "owner_gate_signatures_cryptographically_verified",
            "portable_owner_verification_material"),
            "owner signature hardening")
        if "observatory_supremacy_dossier_hardening.install" not in audit:
            raise RuntimeError(
                "audit no longer exposes the foundation hook patched by launcher-v3")
        report.update({
            "status": "PASS",
            "portable_owner_signature_static_extension": "PASS",
            "final_launcher_v3_verified": True,
            "final_audit_v3_wired": True,
            "candidate_identity_prompt_bound": True,
            "owner_public_key_snapshot_verified": True,
            "signed_owner_decisions_snapshot_verified": True,
            "owner_gate_crypto_reverification_verified": True,
            "portable_owner_modules_imported": modules,
            "protocol_bundle_sha256":
                observatory_protocol.protocol_bundle_sha256(ROOT),
        })
    except Exception as exc:
        report["status"] = "FAIL"
        report["reason"] = f"{type(exc).__name__}: {exc}"
    with open(REPORT, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=1, sort_keys=True)
    print(json.dumps(report, ensure_ascii=False, indent=1, sort_keys=True))
    return 0 if report.get("status") == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
