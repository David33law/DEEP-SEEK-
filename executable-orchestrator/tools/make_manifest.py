#!/usr/bin/env python3
"""Regenerate PACK-MANIFEST.sha256.json over EVERY file in the immutable package.

v2.0's manifest listed 79 of 80 files and nothing read it. This tool is the only writer,
validate_package.py is the only reader, and the count is asserted both ways.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ORCH = os.path.dirname(HERE)
ROOT = os.path.dirname(ORCH)
PKG = os.path.join(ROOT, "immutable-package")
sys.path.insert(0, ORCH)

from lawmax21.canonical import sha256_file  # noqa: E402

MANIFEST_NAME = "PACK-MANIFEST.sha256.json"


def main():
    files = {}
    for r, ds, fs in os.walk(PKG):
        ds[:] = [d for d in ds if d != "__pycache__"]
        for f in sorted(fs):
            rel = os.path.relpath(os.path.join(r, f), PKG).replace("\\", "/")
            if rel == MANIFEST_NAME:
                continue
            files[rel] = sha256_file(os.path.join(r, f))
    manifest = {"algorithm": "sha256-full-64hex", "file_count": len(files),
                "covers": "every file under immutable-package/ except the manifest itself",
                "files": dict(sorted(files.items()))}
    with open(os.path.join(PKG, MANIFEST_NAME), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1, sort_keys=True)
    print(f"PACK-MANIFEST: {len(files)} files hashed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
