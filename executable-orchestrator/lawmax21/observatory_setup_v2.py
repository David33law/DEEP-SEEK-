"""Final owner ceremony wrapper with hash-bound specialized calibration evidence."""
import os
from . import observatory_protocol
from . import observatory_setup as base
from .canonical import atomic_write_json, read_json

ROWS = {
 "distributed": ("benchmark/observatory_distributed_reference_candidate.py", "private-evaluator/evaluator/observatory_distributed_arena.py", "proof/distributed-reference-calibration.json"),
 "scale": ("benchmark/observatory_scale_reference_candidate.py", "private-evaluator/evaluator/observatory_scale_arena.py", "proof/scale-reference-calibration.json"),
 "formal": ("benchmark/observatory_formal_reference_candidate.py", "private-evaluator/evaluator/observatory_formal_arena.py", "proof/formal-reference-calibration.json"),
 "interoperability": ("benchmark/observatory_interoperability_reference_candidate.py", "private-evaluator/evaluator/observatory_interoperability_arena.py", "proof/interoperability-reference-calibration.json")}
_original = base._calibrate_specialized_references


def _path(relative):
    return os.path.join(base.ROOT, *relative.split("/"))


def _calibrate():
    visible = _original(); sources = {}; campaigns = {}
    for label, (reference, evaluator, report_rel) in ROWS.items():
        sources[label] = {relative: observatory_protocol.file_sha256(_path(relative))
                          for relative in (reference, evaluator)}
        report_path = _path(report_rel); report = read_json(report_path)
        campaigns[label] = {"status": report.get("status"),
                            "passed": report.get("passed", report.get("status") in ("PASS", "OK")),
                            "report_path": report_rel,
                            "report_sha256": observatory_protocol.file_sha256(report_path)}
    atomic_write_json(os.path.join(base.PROOF, "observatory-specialized-calibration-receipt.json"),
                      {"protocol_version": observatory_protocol.PROTOCOL_VERSION,
                       "protocol_bundle_sha256": observatory_protocol.protocol_bundle_sha256(base.ROOT),
                       "proof_mode": observatory_protocol.proof_mode(),
                       "sources": sources, "campaigns": campaigns, "provider_calls": 0})
    return visible


base._calibrate_specialized_references = _calibrate
main = base.main
__all__ = ["main"]
