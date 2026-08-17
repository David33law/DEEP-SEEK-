#!/usr/bin/env python3
"""Output-bounded and duplicate-correct entrypoint for the national-scale arena."""
import hashlib
import json
import os
import sys

import bounded_subprocess
import observatory_scale_arena as base

bounded_subprocess.install(base.subprocess)


def _stable_event(index, total, seed, prefix):
    del total
    kinds = ("LEGISLATION", "AMENDMENT", "CORRECTION",
             "SUSPENSION", "REVIVAL", "REPEAL")
    kind = kinds[index % len(kinds)]
    year, month, day = 1980 + (index % 55), 1 + (index % 12), 1 + (index % 27)
    # Fixed object cardinality makes a reversed subset byte-identical to its first delivery. The
    # former generator derived canonical_id from the requested subset size, so the "duplicate" test
    # accidentally injected conflicting bytes under the same source_id.
    object_count = 4096
    canonical_id = f"{prefix}-LAW-{index % object_count:08d}:ART-{1 + (index % 120)}"
    payload = hashlib.sha256(f"{seed}|{prefix}|{index}".encode()).hexdigest()[:24]
    return {"source_id": f"{prefix}-{seed:08x}-{index:012d}", "kind": kind,
            "canonical_id": canonical_id, "target_id": canonical_id,
            "publication_time": f"{year:04d}-{month:02d}-{day:02d}",
            "knowledge_time": f"{year:04d}-{month:02d}-{day:02d}",
            "effective_from": f"{year:04d}-{month:02d}-{day:02d}",
            "text": (f"payload-{payload}" if kind in
                     ("LEGISLATION", "AMENDMENT", "CORRECTION") else None)}


base._event = _stable_event


def _arg(argv, name, default):
    values = list(sys.argv[1:] if argv is None else argv)
    try:
        return values[values.index(name) + 1]
    except (ValueError, IndexError):
        return default


def main(argv=None):
    out = _arg(argv, "--out", None)
    events = int(_arg(argv, "--events", 100000))
    result = base.main(argv)
    if out and os.path.isfile(out):
        with open(out, encoding="utf-8") as handle:
            report = json.load(handle)
        elapsed = float(report.get("elapsed_seconds_main_and_tail", 0.0))
        if elapsed > 0:
            report["events_per_second"] = events / elapsed
            report["throughput_scope"] = "primary large-history ingest only"
        with open(out, "w", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=1, sort_keys=True)
    return result


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(json.dumps({"status": "FAIL", "passed": False,
                          "reason": str(exc)}, ensure_ascii=False, indent=1))
        sys.exit(1)
