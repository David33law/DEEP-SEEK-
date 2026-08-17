"""Persist exact candidate-source identity in every hidden semantic report.

The executable-genome auditor may use a semantic report only when the report itself records the
SHA-256 of the exact candidate.py bytes evaluated. Filename coincidence or current in-memory state is
not sufficient evidence. This wrapper modifies no scores; it only makes the evaluator receipt
self-identifying and independently recheckable.
"""
import hashlib
import os
from types import MethodType

from .canonical import atomic_write_json
from .handlers import A


def _sha256_bytes(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def install(ctx, handlers):
    if getattr(ctx, "_semantic_evidence_binding_installed", False):
        return dict(handlers)
    original = ctx.measure_hidden

    def measure_hidden(self, candidate_id, level):
        report = original(candidate_id, level)
        candidate = self.candidates.get(candidate_id) or {}
        source = candidate.get("source")
        if not isinstance(source, str) or not source:
            raise RuntimeError(
                f"{candidate_id}: hidden semantic evaluation has no candidate source bytes")
        candidate_path = A(self, "candidate-src", f"{candidate_id}.py")
        if not os.path.isfile(candidate_path):
            raise RuntimeError(
                f"{candidate_id}: hidden semantic candidate file is missing")
        with open(candidate_path, encoding="utf-8") as handle:
            persisted = handle.read()
        source_sha256 = _sha256_bytes(source)
        persisted_sha256 = _sha256_bytes(persisted)
        if source_sha256 != persisted_sha256:
            raise RuntimeError(
                f"{candidate_id}: in-memory and persisted semantic source bytes diverge")
        output = A(
            self, "reports",
            f"observatory-hidden-{level}-{candidate_id}.json")
        report["candidate_path"] = os.path.relpath(
            candidate_path, self.runtime).replace("\\", "/")
        report["candidate_sha256"] = source_sha256
        report["evidence_path"] = os.path.relpath(
            output, self.runtime).replace("\\", "/")
        atomic_write_json(output, report)
        return report

    ctx.measure_hidden = MethodType(measure_hidden, ctx)
    ctx._semantic_evidence_binding_installed = True
    return dict(handlers)
