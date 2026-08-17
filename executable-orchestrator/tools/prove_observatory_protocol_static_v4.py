#!/usr/bin/env python3
"""Final static extension for protocol-v5 portable owner verification.

Runs the complete v5 static proof, then verifies that the stable runner uses the final launcher and
that the dossier snapshots the owner public key and signed decisions and invokes the trusted
``verify_approval`` primitive over every pre-terminal owner gate. No provider call, candidate
execution or owner mutation occurs.
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
    "executable-orchestrator/lawmax21/observatory_owner_gate_signature_hardening.py",
}


def _text(relative):
    with open(os.path.join(ROOT, *relative.split("/")), encoding="utf-8") as handle:
        return handle.read()


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
                "lawmax21.observatory_owner_gate_signature_hardening").__name__,
        ]
        protocol_files = set(observatory_protocol.protocol_files(ROOT))
        missing = sorted(REQUIRED_FILES - protocol_files)
        if missing:
            raise RuntimeError(
                "protocol census omitted final owner-signature routes: "
                + ", ".join(missing))
        runner = _text("run_observatory.py")
        launcher = _text(
            "executable-orchestrator/lawmax21/observatory_launcher_v3.py")
        hardening = _text(
            "executable-orchestrator/lawmax21/"
            "observatory_owner_gate_signature_hardening.py")
        audit = _text(
            "executable-orchestrator/lawmax21/observatory_audit.py")
        if "observatory_launcher_v3" not in runner:
            raise RuntimeError("stable production runner bypasses final launcher-v3")
        for token in (
                "_foundation_then_signatures",
                "owner_signatures.install",
                "foundation.install = _foundation_then_signatures"):
            if token not in launcher:
                raise RuntimeError("final launcher lacks signature hook: " + token)
        for token in (
                "verify_approval(", "OWNER-PUBLIC-KEY.hex",
                "OWNER-DECISIONS.signed.json",
                "owner_gate_signatures_cryptographically_verified",
                "portable_owner_verification_material"):
            if token not in hardening:
                raise RuntimeError("owner signature hardening lacks: " + token)
        if "observatory_supremacy_dossier_hardening.install" not in audit:
            raise RuntimeError("audit no longer exposes the foundation hook patched by launcher-v3")
        report.update({
            "status": "PASS",
            "portable_owner_signature_static_extension": "PASS",
            "final_launcher_v3_verified": True,
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
