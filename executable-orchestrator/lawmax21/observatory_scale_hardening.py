"""Correct scale-implementation diversity after architecture-preserving revisions.

The base scale search computed the distinct-source count before revisions. A failed initial family
could therefore remain permanently rejected even when a revision produced a second distinct source
and passed every scale fault. This hook recomputes the final set and canonicalizes the selected source
only when the measured report passes.
"""
import os
import shutil

from . import observatory_scale_overlay as scale


def install(_ctx, handlers):
    if getattr(scale, "_scale_diversity_hardening_installed", False):
        return dict(handlers)
    original = scale._qualify

    def qualify(context, candidate_id, allow_revision=True):
        result = original(context, candidate_id, allow_revision=allow_revision)
        variants = result.get("variants") or []
        distinct = len({row.get("source_sha256") for row in variants
                        if row.get("source_sha256")})
        result["distinct_source_hashes"] = distinct
        selected = result.get("selected_perspective")
        selected_report = result.get("selected_report") or {}
        can_pass = bool(selected
                        and selected_report.get("status") == "PASS"
                        and selected_report.get("passed") is True
                        and distinct >= scale.MIN_DISTINCT_SCALE_IMPLEMENTATIONS)
        result["status"] = "PASS" if can_pass else "FAIL"
        result["passed"] = can_pass
        if can_pass:
            source_path = scale._path(context, candidate_id, selected)
            canonical_path = scale._path(context, candidate_id)
            if not os.path.isfile(source_path):
                raise RuntimeError(
                    f"{candidate_id}: selected scale source is missing: {source_path}")
            shutil.copyfile(source_path, canonical_path)
            context.candidates[candidate_id]["scale_candidate_path"] = canonical_path
            context.candidates[candidate_id]["scale_source_sha256"] = result.get(
                "selected_source_sha256")
            context.candidates[candidate_id]["scale_qualified"] = True
        else:
            context.candidates[candidate_id]["scale_qualified"] = False
        context.record_score(candidate_id, "scale_qualification", result)
        context._save_arena()
        return result

    scale._qualify = qualify
    scale._scale_diversity_hardening_installed = True
    return dict(handlers)
