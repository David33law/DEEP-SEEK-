#!/usr/bin/env python3
"""Memory-bounded entrypoint for the exhaustive bounded formal-model arena.

The underlying arena used to retain the complete observation object for every trace before hashing.
At crown depth five this could consume gigabytes. This wrapper preserves ordered digest semantics
with a length-delimited streaming SHA-256 accumulator and retains only unique state digests and
bounded counterexamples.
"""
import json
import sys

import bounded_subprocess
import observatory_formal_arena as base

_OLD = '''    behavior = []
    unique_states = set()
    trace_count = 0
    for length in range(1, depth + 1):
        for sequence in itertools.product(range(len(actions)), repeat=length):
            state, observation = run_actions(sequence, [action_codes[x] for x in sequence])
            unique_states.add(digest(state))
            behavior.append(observation)
            trace_count += 1
    report["trace_count"] = trace_count
    report["unique_state_count"] = len(unique_states)
    report["behavioral_digest"] = digest(behavior)
'''
_NEW = '''    behavior_digest = hashlib.sha256()
    unique_states = set()
    trace_count = 0
    for length in range(1, depth + 1):
        for sequence in itertools.product(range(len(actions)), repeat=length):
            state, observation = run_actions(sequence, [action_codes[x] for x in sequence])
            unique_states.add(digest(state))
            encoded = canonical(observation).encode("utf-8")
            behavior_digest.update(len(encoded).to_bytes(8, "big"))
            behavior_digest.update(encoded)
            trace_count += 1
    report["trace_count"] = trace_count
    report["unique_state_count"] = len(unique_states)
    report["behavioral_digest"] = behavior_digest.hexdigest()
    report["behavioral_digest_mode"] = "ordered-length-delimited-stream-v1"
'''
if _OLD not in base.HARNESS:
    raise RuntimeError("formal arena streaming patch no longer matches the signed base harness")
base.HARNESS = base.HARNESS.replace(_OLD, _NEW, 1)
bounded_subprocess.install(base.subprocess)

if __name__ == "__main__":
    try:
        sys.exit(base.main())
    except Exception as exc:
        print(json.dumps({"status": "FAIL", "passed": False,
                          "reason": str(exc)}, ensure_ascii=False, indent=1))
        sys.exit(1)
