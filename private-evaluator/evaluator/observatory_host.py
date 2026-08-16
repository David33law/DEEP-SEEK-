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
__OBS_ALLOWED = __OBS_REQUIRED + ("extension_probe",)


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


def __obs_extension_probe(args):
    registrar = globals().get("register_change_handler")
    apply_fn = globals().get("apply_change")
    if not callable(registrar) or not callable(apply_fn):
        return {"supported": False, "reason": "no runtime change-handler registry"}
    kind = args["kind"]
    marker = args["marker"]

    def probe_handler(event):
        return {"accepted": True,
                "target_id": event.get("target_id", event.get("canonical_id", "")),
                "change_type": kind,
                "unresolved": [],
                "extension_marker": marker}

    registrar(kind, probe_handler)
    event = dict(args["event"])
    event["kind"] = kind
    result = apply_fn(event)
    return {"supported": True, "result": result, "marker": marker}


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
        if method not in __OBS_ALLOWED:
            out.append({"m": method, "error": "unknown Observatory operation"})
            continue
        try:
            if method == "extension_probe":
                result = __obs_extension_probe(step.get("a", {}))
            else:
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

    def extension_probe(self, kind, marker, event):
        out = self.run_session([{"m": "extension_probe",
                                 "a": {"kind": kind, "marker": marker, "event": event}}])
        if not isinstance(out, list) or len(out) != 1 or out[0].get("m") != "extension_probe":
            return {"supported": False, "reason": "malformed extension-probe envelope"}
        if out[0].get("error"):
            return {"supported": False, "reason": out[0]["error"]}
        return out[0].get("r") or {"supported": False, "reason": "empty extension-probe result"}

    def isolation_report(self):
        rep = self.host.isolation_report()
        rep["profile"] = "national-observatory"
        rep["candidate_receives"] = ["own source code", "one label-free Observatory script per process"]
        return rep
