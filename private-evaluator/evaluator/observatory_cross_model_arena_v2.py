#!/usr/bin/env python3
"""Multi-history wrapper for the hidden cross-model consistency arena."""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import shutil

import bounded_subprocess

bounded_subprocess.install(subprocess)
HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, "observatory_cross_model_arena.py")


def _sha(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--semantic", required=True)
    parser.add_argument("--formal", action="append", required=True)
    parser.add_argument("--interoperability", action="append", required=True)
    parser.add_argument("--seed", type=int, default=9902026)
    parser.add_argument("--histories", type=int, default=4)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    if len(args.formal) != 2 or len(args.interoperability) != 2:
        raise RuntimeError("exactly two formal and two interoperability sources are required")
    if args.histories < 1 or args.histories > 128:
        raise RuntimeError("cross-model history count outside signed bounded range")
    rows = []
    temp = tempfile.mkdtemp(prefix="obs-cross-model-")
    try:
        for index in range(args.histories):
            seed = int(hashlib.sha256(f"{args.seed}|{index}".encode()).hexdigest()[:8], 16)
            out = os.path.join(temp, f"history-{index:03d}.json")
            command = [sys.executable, BASE, "--semantic", args.semantic,
                       "--seed", str(seed), "--out", out]
            for path in args.formal:
                command.extend(["--formal", path])
            for path in args.interoperability:
                command.extend(["--interoperability", path])
            result = subprocess.run(command, capture_output=True, text=True, timeout=1800,
                                    max_stdout_bytes=4 * 1024 * 1024,
                                    max_stderr_bytes=1 * 1024 * 1024)
            if not os.path.isfile(out):
                rows.append({"index": index, "seed": seed, "status": "FAIL",
                             "passed": False,
                             "reason": "history report missing: "
                                       + (result.stdout + result.stderr)[-800:]})
                continue
            with open(out, encoding="utf-8") as handle:
                report = json.load(handle)
            rows.append({"index": index, "seed": seed,
                         "status": report.get("status"),
                         "passed": report.get("passed") is True,
                         "report_sha256": _sha(out),
                         "semantic_digest": report.get("semantic_digest"),
                         "formal_digest": report.get("formal_digest"),
                         "interoperability_digest": report.get("interoperability_digest"),
                         "reason": report.get("reason")})
        passed = len(rows) == args.histories and all(row["passed"] for row in rows)
        aggregate = hashlib.sha256(json.dumps(
            rows, ensure_ascii=False, sort_keys=True,
            separators=(",", ":")).encode()).hexdigest()
        report = {"status": "PASS" if passed else "FAIL", "passed": passed,
                  "histories": args.histories,
                  "histories_passed": sum(1 for row in rows if row["passed"]),
                  "aggregate_digest": aggregate, "reports": rows,
                  "root_algorithms_compared": False,
                  "proof_boundary": (
                      "multiple shared hidden legal-observation histories; unrelated root byte "
                      "algorithms are deliberately not equated")}
    finally:
        shutil.rmtree(temp, ignore_errors=True)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=1, sort_keys=True)
    print(json.dumps(report, ensure_ascii=False, indent=1))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(json.dumps({"status": "FAIL", "passed": False,
                          "reason": str(exc)}, ensure_ascii=False, indent=1))
        sys.exit(1)
