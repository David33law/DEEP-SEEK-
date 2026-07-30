#!/usr/bin/env python3
"""Measure a candidate's RUNNING INSTITUTION — layers L1,L2,L7,L8,L10 and consciousness dims
1,2,8,9 — with the contrastive, stateful sensors in institution_probe.py.

The candidate runs in the same isolation as the hidden-set grader (fresh sandboxed process per
session; no key, no network, no filesystem). This tool holds NO ground truth beyond what the
sensors construct themselves, and it credits nothing — it only reports what was measured. The
runner turns that measured report into layer credit, and only the owner's signature authorises
it. A fake institution (constants, stubs, the right-shaped dict) measures every layer false.
"""
import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import institution_probe  # noqa: E402
from candidate_host import CandidateHost  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate", required=True)
    ap.add_argument("--backend", choices=("subprocess", "container"), default="subprocess")
    ap.add_argument("--seed", type=int, default=0,
                    help="per-run secret seed; the candidate never receives it, so it cannot "
                         "memorise the trial vectors")
    ap.add_argument("--op-timeout", type=int, default=15,
                    help="per-session wall timeout (s); institution sessions are sub-second, so a "
                         "stalling candidate is cut off quickly")
    ap.add_argument("--budget-seconds", type=int, default=120,
                    help="aggregate wall budget (s) for the whole measurement; past it, remaining "
                         "layers measure not-demonstrated (audit v2.3: DoS-amplification cap)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)

    with open(a.candidate, "r", encoding="utf-8") as f:
        src = f.read()
    host = CandidateHost(src, backend=a.backend, timeout=a.op_timeout)
    deadline = time.monotonic() + a.budget_seconds
    rep = institution_probe.run(host, seed=a.seed, deadline=deadline)

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump({"status": "OK", "isolation": host.isolation_report(),
                   "institution_measurement": rep}, f, ensure_ascii=False, indent=1, sort_keys=True)
    print(json.dumps({"status": "OK", "layers_demonstrated": rep["layers_demonstrated"],
                      "dims_passed": rep["dims_passed"],
                      "consciousness_full": rep["consciousness_full"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
