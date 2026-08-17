#!/usr/bin/env python3
"""Final proof entrypoint: static protocol proof followed by the full v4 E2E proof."""
import json
import os
import subprocess
import sys

import prove_complete_observatory_protocol as base

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
STATIC = os.path.join(HERE, "prove_observatory_protocol_static.py")
STATIC_REPORT = os.path.join(ROOT, "proof", "observatory-protocol-static.json")
E2E_REPORT = os.path.join(ROOT, "proof", "complete-observatory-protocol-e2e.json")


def main(argv=None):
    result = subprocess.run([sys.executable, STATIC], capture_output=True,
                            text=True, timeout=1800,
                            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    if result.returncode != 0:
        print(result.stdout); print(result.stderr, file=sys.stderr)
        return result.returncode
    static = json.load(open(STATIC_REPORT, encoding="utf-8"))
    if static.get("status") != "PASS":
        print(json.dumps(static, ensure_ascii=False, indent=1)); return 1
    code = base.main(argv)
    if os.path.isfile(E2E_REPORT):
        e2e = json.load(open(E2E_REPORT, encoding="utf-8"))
        e2e["static_protocol_proof"] = {
            "status": static.get("status"),
            "protocol_bundle_sha256": static.get("protocol_bundle_sha256"),
            "protocol_files": static.get("protocol_files"),
            "python_files_compiled": static.get("python_files_compiled"),
            "report_sha256": base.sha256_file(STATIC_REPORT)}
        with open(E2E_REPORT, "w", encoding="utf-8") as handle:
            json.dump(e2e, handle, ensure_ascii=False, indent=1, sort_keys=True)
    return code


if __name__ == "__main__":
    sys.exit(main())
