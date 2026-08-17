"""Final setup wrapper using the same bounded evaluator entrypoints as production."""
import os

from . import observatory_protocol
from . import observatory_setup as core
from . import observatory_setup_v2 as wrapper
from .canonical import atomic_write_json, read_json

CAMPAIGNS = {
    "distributed": {
        "reference": "benchmark/observatory_distributed_reference_candidate.py",
        "evaluator": "private-evaluator/evaluator/observatory_distributed_arena_v2.py",
        "report": "proof/distributed-reference-calibration.json",
        "args": lambda: [
            "--expected-replication-model", "single_primary_read_replicas",
            "--expected-commit-model", "single_writer_sequence",
            "--large-events", str(observatory_protocol.workload(
                "distributed", "qualification"))]},
    "scale": {
        "reference": "benchmark/observatory_scale_reference_candidate.py",
        "evaluator": "private-evaluator/evaluator/observatory_scale_arena_v2.py",
        "report": "proof/scale-reference-calibration.json",
        "args": lambda: [
            "--expected-scaling-model", "source_sharding",
            "--events", str(observatory_protocol.workload("scale", "qualification")),
            "--tail-events", str(max(1000, observatory_protocol.workload(
                "scale", "qualification") // 10)),
            "--partitions", str(observatory_protocol.workload("scale", "partitions")),
            "--batch-size", str(observatory_protocol.workload("scale", "batch"))]},
    "formal": {
        "reference": "benchmark/observatory_formal_reference_candidate.py",
        "evaluator": "private-evaluator/evaluator/observatory_formal_arena_v2.py",
        "report": "proof/formal-reference-calibration.json",
        "args": lambda: [
            "--expected-canonical-authority-seat", "evidence_set",
            "--expected-state-derivation-model", "replay_reducer",
            "--expected-temporal-model", "bitemporal_intervals",
            "--expected-normative-effect-model", "typed_directive_interpreter",
            "--expected-consistency-commit-model", "single_writer_sequence",
            "--expected-replication-distribution-model", "single_primary_read_replicas",
            "--expected-trusted-core-topology", "state_machine_kernel",
            "--depth", str(observatory_protocol.workload(
                "formal", "qualification_depth"))]},
    "interoperability": {
        "reference": "benchmark/observatory_interoperability_reference_candidate.py",
        "evaluator": "private-evaluator/evaluator/observatory_interoperability_arena_v2.py",
        "report": "proof/interoperability-reference-calibration.json",
        "args": lambda: [
            "--expected-identity-model", "composite_identity",
            "--expected-temporal-model", "bitemporal_intervals",
            "--expected-normative-effect-model", "typed_directive_interpreter",
            "--expected-provenance-proof-model", "provenance_graph",
            "--expected-publication-topology", "compiled_read_only_projections",
            "--cases", str(observatory_protocol.workload(
                "interoperability", "qualification_cases"))]},
}


def _path(relative):
    return os.path.join(core.ROOT, *relative.split("/"))


def _calibrate():
    visible, receipt_campaigns, sources = {}, {}, {}
    os.makedirs(core.PROOF, exist_ok=True)
    for label, row in CAMPAIGNS.items():
        reference, evaluator, report = map(_path, (
            row["reference"], row["evaluator"], row["report"]))
        core._run([evaluator, "--candidate", reference, "--out", report,
                   *row["args"]()])
        parsed = core._assert_report(report, label)
        visible[label] = {"status": parsed.get("status"),
                          "report": row["report"]}
        sources[label] = {
            row["reference"]: observatory_protocol.file_sha256(reference),
            row["evaluator"]: observatory_protocol.file_sha256(evaluator)}
        receipt_campaigns[label] = {
            "status": parsed.get("status"),
            "passed": parsed.get("passed", parsed.get("status") in ("PASS", "OK")),
            "report_path": row["report"],
            "report_sha256": observatory_protocol.file_sha256(report)}
    atomic_write_json(os.path.join(
        core.PROOF, "observatory-specialized-calibration-receipt.json"), {
            "protocol_version": observatory_protocol.PROTOCOL_VERSION,
            "protocol_bundle_sha256": observatory_protocol.protocol_bundle_sha256(core.ROOT),
            "proof_mode": observatory_protocol.proof_mode(),
            "sources": sources, "campaigns": receipt_campaigns,
            "provider_calls": 0})
    return visible


core._calibrate_specialized_references = _calibrate
main = wrapper.main
__all__ = ["main"]
