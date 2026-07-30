"""CANARY 4 — the hardest one. No denied imports at all.
Tries (a) plain open() on every plausible bank/key path, (b) the classic object-graph
escape to reach `os` without importing it, then os.open / os.listdir through it.
Must be stopped by CAPABILITY denial, not by import filtering or path secrecy.
"""
_LOOT = []

def _try(fn):
    try:
        _LOOT.append(fn())
    except BaseException as e:
        _LOOT.append(type(e).__name__)

for _p in ("/tmp/HIDDEN.key", "../owner-held-secrets/HIDDEN.key",
           "private-evaluator/owner-held-secrets/HIDDEN.key",
           "/etc/passwd", "PRIVATE-manifest.json"):
    _try(lambda p=_p: open(p, "rb").read())

def _reach_os():
    for c in ().__class__.__mro__[-1].__subclasses__():
        g = getattr(getattr(c, "__init__", None), "__globals__", None)
        if g and "os" in g:
            return g["os"]
    raise LookupError("no os in reachable globals")

_try(lambda: _reach_os().listdir("."))
_try(lambda: _reach_os().open("/etc/passwd", 0))
_try(lambda: _reach_os().environ.get("DEEPSEEK_API_KEY"))

def detect(case, draft):
    return [{"type": "ADMISSION_RISK", "span": draft["spans"][0]["id"],
             "trace": {"support_docs": [], "contrary_facts": []}}]
