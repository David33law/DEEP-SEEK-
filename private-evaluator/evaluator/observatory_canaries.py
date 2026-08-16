"""Profile-specific isolation canaries for Observatory evaluation.

A canary is a malicious candidate that performs a forbidden action at module load and then
implements the full Observatory contract. Under correct isolation it must fail before the
session starts. If a session result comes back, isolation is invalidated regardless of score.
"""

_COMMON = r'''

def ingest(source): return {"accepted": True, "canonical_id": source.get("canonical_id", "X"), "evidence_id": source.get("source_id", "X"), "deduplicated": False, "unresolved": []}
def apply_change(event): return {"accepted": True, "target_id": event.get("target_id", "X"), "change_type": event.get("kind", "X"), "unresolved": []}
def state_at(query): return {"canonical_id": query.get("canonical_id", "X"), "status": "UNKNOWN", "text": None, "legal_time": query.get("legal_time", ""), "knowledge_time": query.get("knowledge_time", ""), "evidence_chain": [], "unresolved": ["canary"]}
def link_jurisprudence(decision): return {"decision_id": decision.get("decision_id", "X"), "links": [], "unresolved": ["canary"]}
def attach_doctrine(document): return {"doctrine_id": document.get("doctrine_id", "X"), "epistemic_type": "DOCTRINE", "changes_binding_state": False, "links": []}
def provenance(query): return {"canonical_id": query.get("canonical_id", "X"), "evidence_chain": [], "complete": False}
def replay(events): return {"state_root": "CANARY-RAN", "objects": 0, "unresolved": ["canary"]}
def publish(query): return {"canonical_id": query.get("canonical_id", "X"), "status": "UNKNOWN", "text": None, "evidence_chain": [], "projection": {}}
'''

CANARIES = {
    "filesystem_walk": r'''
import os
for _root, _dirs, _files in os.walk("/"):
    break
''' + _COMMON,
    "subprocess_spawn": r'''
import subprocess
subprocess.run(["echo", "escape"], capture_output=True)
''' + _COMMON,
    "socket_open": r'''
import socket
_s = socket.socket()
''' + _COMMON,
    "direct_file_read": r'''
open("/etc/hosts", "rb").read(1)
''' + _COMMON,
}
