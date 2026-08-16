"""Observatory adapter over the existing hardened CandidateHost.

No second sandbox exists. We append an evaluator-owned adapter to the candidate source so one
ordinary `detect` call executes the entire stateful Observatory script in one isolated process.
The existing candidate_bootstrap.py and CandidateHost therefore remain the single isolation seat.
"""
from candidate_host import CandidateHost

REQUIRED = (
    "ingest", "apply_change", "state_at", "link_jurisprudence",
    "attach_doctrine", "provenance", "replay", "publish",
)

# Appended AFTER candidate code, so this evaluator-owned detect() cannot be replaced by a
# candidate's earlier detect definition. The candidate has no execution turn after this adapter
# is defined except through the calls below.
ADAPTER = r'''

__OBS_REQUIRED = ("ingest", "apply_change", "state_at", "link_jurisprudence",
                  "attach_doctrine", "provenance", "replay", "publish")


def __obs_call(method, args):
    fn = globals().get(method)
    if not callable(fn):
        raise RuntimeError("missing required Observatory operation: " + method)
    if method == "ingest":
        return fn(args["source"])
    if method == "apply_change":
        return fn(args["event"])
    if method == "state_at":
        return fn(args["query"])
    if method == "link_jurisprudence":
        return fn(args["decision"])
    if method == "attach_doctrine":
        return fn(args["document"])
    if method == "provenance":
        return fn(args["query"])
    if method == "replay":
        return fn(args["events"])
    if method == "publish":
        return fn(args["query"])
    raise RuntimeError("unknown Observatory operation: " + method)


def detect(case, draft):
    del draft
    script = case.get("script") if isinstance(case, dict) else None
    if not isinstance(script, list):
        raise RuntimeError("Observatory evaluator requires case.script")
    missing = [name for name in __OBS_REQUIRED if not callable(globals().get(name))]
    if missing:
        raise RuntimeError("missing required Observatory operations: " + ",".join(missing))
    out = []
    for step in script:
        method = step.get("m")
        if method not in __OBS_REQUIRED:
            out.append({"m": method, "error": "unknown Observatory operation"})
            continue
        try:
            result = __obs_call(method, step.get("a", {}))
            out.append({"m": method, "r": result})
        except BaseException as exc:
            out.append({"m": method, "error": type(exc).__name__ + ": " + str(exc)})
    return out
'''


def wrapped_source(candidate_source):
    return candidate_source.rstrip() + "\n" + ADAPTER + "\n"


class ObservatoryCandidateHost:
    """Thin profile adapter; containment is still CandidateHost's existing backend."""
    def __init__(self, candidate_source, backend="subprocess", timeout=60):
        self.raw_source = candidate_source
        self.host = CandidateHost(wrapped_source(candidate_source), backend=backend, timeout=timeout)

    def run_session(self, script):
        # Only label-free operations/arguments are sent. Ground truth stays in observatory_grade.
        return self.host.detect({"script": script}, {})

    def isolation_report(self):
        rep = self.host.isolation_report()
        rep["profile"] = "national-observatory"
        rep["candidate_receives"] = ["own source code", "one label-free Observatory script per process"]
        return rep
