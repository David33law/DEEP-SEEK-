"""Fail-closed hardening for the authoritative prior-art challenge.

The base overlay obtains independent source assessments and constructs challenger genomes. This hook
makes two additional facts mechanical: SATISFIED claims must cite existing persisted run evidence,
and a challenger is not "measured" until semantic, durable, distributed, scale, formal and legal-
interoperability qualification have all passed.
"""
import os

from . import observatory_prior_art_overlay as prior
from .canonical import atomic_write_json, read_json, sha256_obj
from .handlers import A

_REQUIRED_SCORE_REPORTS = (
    ("hidden_qualification", ("OK", "PASS")),
    ("systems_qualification", ("PASS",)),
    ("distributed_qualification", ("PASS",)),
    ("scale_qualification", ("PASS",)),
    ("formal_qualification", ("PASS",)),
    ("interoperability_qualification", ("PASS",)),
)


def _report_passes(report, statuses):
    return isinstance(report, dict) \
        and report.get("status") in statuses \
        and report.get("passed", True) is True


def _fully_measured(ctx, cid):
    if not cid or cid not in ctx.candidates:
        return False
    scores = ctx.scores.get(cid) or {}
    return all(_report_passes(scores.get(key), statuses)
               for key, statuses in _REQUIRED_SCORE_REPORTS)


def _safe_evidence(ctx, relative):
    relative = str(relative or "").replace("\\", "/")
    if not relative or relative.startswith("/") \
            or ".." in relative.split("/"):
        return None
    absolute = os.path.abspath(os.path.join(ctx.runtime, *relative.split("/")))
    if not absolute.startswith(os.path.abspath(ctx.runtime) + os.sep) \
            or not os.path.isfile(absolute):
        return None
    from .canonical import sha256_file
    return {"path": relative, "sha256": sha256_file(absolute),
            "bytes": os.path.getsize(absolute)}


def _collect_evidence(value, output):
    if isinstance(value, dict):
        evidence = value.get("evidence_path")
        if isinstance(evidence, str):
            output.add(evidence.replace("\\", "/"))
        for nested in value.values():
            _collect_evidence(nested, output)
    elif isinstance(value, list):
        for nested in value:
            _collect_evidence(nested, output)


def install(_ctx, handlers):
    if getattr(prior, "_prior_art_hardening_installed", False):
        return dict(handlers)

    original_measured = prior._measured
    original_frontier_context = prior.crownmod._frontier_design_context
    original_install = prior.install

    def measured(context, candidate_id):
        return _fully_measured(context, candidate_id)

    def frontier_context(context):
        rows = original_frontier_context(context)
        for row in rows:
            candidate_id = row.get("candidate_id")
            refs = set()
            _collect_evidence(context.scores.get(candidate_id) or {}, refs)
            verified = [record for record in
                        (_safe_evidence(context, ref) for ref in sorted(refs))
                        if record is not None]
            row["persisted_evidence_refs"] = verified
            row["all_required_arenas_measured"] = _fully_measured(
                context, candidate_id)
        return rows

    def hardened_install(context, base_handlers):
        out = original_install(context, base_handlers)
        original_ceiling = out["CEILING_ANALYSIS"]

        def ceiling(machine):
            path = original_ceiling(machine)
            campaign_path = A(
                context, "architecture", f"prior-art-round{context.round}.json")
            campaign = read_json(campaign_path)
            blockers = list(campaign.get("blockers") or [])
            verified_records = []
            for critic in campaign.get("critics") or []:
                tag = critic.get("tag")
                for review in (critic.get("report") or {}).get("source_reviews") or []:
                    if review.get("disposition") != "SATISFIED":
                        continue
                    verified = []
                    invalid = []
                    for reference in review.get("evidence_refs") or []:
                        record = _safe_evidence(context, reference)
                        if record is None:
                            invalid.append(reference)
                        else:
                            verified.append(record)
                            verified_records.append(record)
                    review["verified_evidence"] = verified
                    if invalid:
                        blockers.append({
                            "kind": "invalid_prior_art_evidence_reference",
                            "critic": tag,
                            "source_id": review.get("source_id"),
                            "invalid_references": invalid})
            for row in campaign.get("challengers") or []:
                cid = row.get("candidate_id")
                row["measured"] = _fully_measured(context, cid)
                row["measurement_requirements"] = [key
                    for key, _statuses in _REQUIRED_SCORE_REPORTS]
            unique = {sha256_obj(record): record for record in verified_records}
            campaign["verified_evidence_catalog"] = [unique[key]
                                                     for key in sorted(unique)]
            campaign["verified_evidence_catalog_sha256"] = sha256_obj(
                campaign["verified_evidence_catalog"])
            campaign["challengers_measured"] = bool(all(
                row.get("measured") for row in campaign.get("challengers") or []))
            campaign["blockers"] = blockers
            campaign["no_blockers"] = not blockers and not campaign.get("unresolved")
            atomic_write_json(campaign_path, campaign)
            context.esc.record_prior_art_wave({
                **campaign,
                "evidence": os.path.relpath(
                    campaign_path, context.runtime).replace("\\", "/")})
            ceiling_artifact = read_json(path)
            ceiling_artifact.setdefault("authoritative_prior_art", {}).update({
                "verified_evidence_catalog_sha256": campaign[
                    "verified_evidence_catalog_sha256"],
                "all_required_arenas_required": True,
                "invalid_evidence_blockers": len([x for x in blockers
                    if x.get("kind") == "invalid_prior_art_evidence_reference"])})
            atomic_write_json(path, ceiling_artifact)
            return path

        out["CEILING_ANALYSIS"] = ceiling
        return out

    prior._measured = measured
    prior.crownmod._frontier_design_context = frontier_context
    prior.install = hardened_install
    prior._prior_art_hardening_installed = True
    return dict(handlers)
