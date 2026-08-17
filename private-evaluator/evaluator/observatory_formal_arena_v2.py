#!/usr/bin/env python3
"""Output-bounded entrypoint for the bounded formal-model arena."""
import sys
import bounded_subprocess
import observatory_formal_arena as base

bounded_subprocess.install(base.subprocess)

if __name__ == "__main__":
    try:
        sys.exit(base.main())
    except Exception as exc:
        import json
        print(json.dumps({"status": "FAIL", "passed": False,
                          "reason": str(exc)}, ensure_ascii=False, indent=1))
        sys.exit(1)
