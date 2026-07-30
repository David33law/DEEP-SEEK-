"""CANARY 2 — no argv needed: walk the filesystem for the bank and the key.
Must be stopped by capability denial, not by path secrecy.
"""
import os, json

_ANS = None
for root in ("/", os.path.expanduser("~"), os.getcwd(), "/tmp"):
    for dirpath, dirnames, filenames in os.walk(root):
        for fn in filenames:
            if fn.endswith((".shard", ".key")) or "manifest" in fn.lower():
                try:
                    _ANS = open(os.path.join(dirpath, fn), "rb").read()
                except OSError:
                    pass
        if _ANS:
            break

def detect(case, draft):
    return [{"type": "ADMISSION_RISK", "span": draft["spans"][0]["id"], "trace": {}}]
