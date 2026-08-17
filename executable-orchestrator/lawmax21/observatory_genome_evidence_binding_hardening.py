"""Require every genome-realization evidence citation to bind the exact current source bytes.

The model-facing auditor may cite only passing candidate reports whose recorded candidate SHA-256
matches the semantic/systems/distributed/scale/formal/interoperability source census. Generic
manifests, stale pre-selection reports and failed revisions are removed before prompting and cannot
satisfy a controlled-axis obligation.
"""
from . import observatory_genome_realization_overlay as genome


_REQUIRED = {
    group for groups in genome.REQUIRED_GROUPS.values() for group in groups
}


def _expected(census):
    return {
        "semantic": {census["semantic"]["sha256"]},
        "systems": {census["systems"]["sha256"]},
        "distributed": {census["distributed"]["sha256"]},
        "scale": {census["scale"]["sha256"]},
        "formal": {
            census["formal_A"]["sha256"],
            census["formal_B"]["sha256"]},
        "interoperability": {
            census["interoperability_A"]["sha256"],
            census["interoperability_B"]["sha256"]},
    }


def install(_ctx, handlers):
    if getattr(genome, "_evidence_binding_hardening_installed", False):
        return dict(handlers)
    original_catalog = genome._evidence_catalog
    original_validate = genome._validate

    def evidence_catalog(context, candidate_id):
        catalog = original_catalog(context, candidate_id)
        census = genome._source_census(context, candidate_id)
        expected = _expected(census)
        filtered = {}
        for path, row in catalog.items():
            group = row.get("group")
            if group not in expected:
                continue
            if row.get("status") not in ("PASS", "OK"):
                continue
            if row.get("passed", True) is not True:
                continue
            if row.get("candidate_sha256") not in expected[group]:
                continue
            filtered[path] = row
        present = {row.get("group") for row in filtered.values()}
        missing = sorted(_REQUIRED - present)
        if missing:
            raise RuntimeError(
                f"{candidate_id}: no passing source-bound evidence for groups: "
                + ", ".join(missing))
        return filtered

    def validate(context, candidate_id, report, census, invariants, evidence):
        validated = original_validate(
            context, candidate_id, report, census, invariants, evidence)
        expected = _expected(census)
        by_axis = {
            row.get("axis"): row for row in report.get("axis_reviews") or []}
        for axis, validated_axis in zip(genome.oroles.GENOME_FIELDS, validated):
            row = by_axis[axis]
            for reference in row.get("evidence_refs") or []:
                evidence_row = evidence[reference]
                group = evidence_row.get("group")
                if evidence_row.get("status") not in ("PASS", "OK") \
                        or evidence_row.get("passed", True) is not True:
                    raise RuntimeError(
                        f"{candidate_id}/{axis}: cited evidence is not passing")
                if evidence_row.get("candidate_sha256") not in expected[group]:
                    raise RuntimeError(
                        f"{candidate_id}/{axis}: cited evidence is stale or "
                        f"bound to another {group} source")
            validated_axis["source_bound_evidence"] = True
        return validated

    genome._evidence_catalog = evidence_catalog
    genome._validate = validate
    genome._evidence_binding_hardening_installed = True
    return dict(handlers)
