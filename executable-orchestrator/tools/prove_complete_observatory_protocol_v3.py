#!/usr/bin/env python3
"""Authoritative proof entrypoint: protocol-v5 static closure followed by hardened full E2E.

The static phase proves that all protocol-v5 mechanisms are connected to the signed mission and final
proof path. Only after that receipt passes does the existing hardened disposable-clone E2E execute.
No real DeepSeek endpoint is used by either phase.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

import prove_complete_observatory_protocol_hardened as e2e

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
STATIC = os.path.join(HERE, "prove_observatory_protocol_static_v3.py")
STATIC_REPORT = os.path.join(ROOT, "proof", "observatory-protocol-static-v5.json")
E2E_REPORT = os.path.join(ROOT, "proof", "complete-observatory-protocol-e2e.json")


def main(argv=None) -> int:
    static_run = subprocess.run(
        [sys.executable, STATIC],
        capture_output=True,
        text=True,
        timeout=3600,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    if static_run.returncode != 0:
        print(static_run.stdout)
        print(static_run.stderr, file=sys.stderr)
        return static_run.returncode
    with open(STATIC_REPORT, encoding="utf-8") as handle:
        static = json.load(handle)
    if static.get("status") != "PASS" \
            or static.get("protocol_version") != \
            "OBSERVATORY-OMEGA-RESEARCH-PROTOCOL-5":
        print(json.dumps(static, ensure_ascii=False, indent=1, sort_keys=True))
        return 1

    code = e2e.main(argv)
    if os.path.isfile(E2E_REPORT):
        with open(E2E_REPORT, encoding="utf-8") as handle:
            report = json.load(handle)
        report["static_protocol_v5_closure"] = {
            "status": static.get("status"),
            "protocol_version": static.get("protocol_version"),
            "protocol_bundle_sha256": static.get("protocol_bundle_sha256"),
            "protocol_files": static.get("protocol_files"),
            "genome_axes": static.get("genome_axes"),
            "genome_auditors": static.get("genome_auditors"),
            "genome_terminal_conditions": static.get("genome_terminal_conditions"),
            "strict_one_file_build_schema": static.get(
                "strict_one_file_build_schema"),
            "source_bound_evidence_required": static.get(
                "source_bound_evidence_required"),
            "report_sha256": e2e.sha256_file(STATIC_REPORT),
        }
        with open(E2E_REPORT, "w", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=1, sort_keys=True)
    return code


if __name__ == "__main__":
    sys.exit(main())
