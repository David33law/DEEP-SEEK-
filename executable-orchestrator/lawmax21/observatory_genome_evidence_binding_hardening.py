"""Require every genome-realization evidence citation to bind exact current source bytes.

The auditor may cite only passing reports whose recorded candidate SHA-256 matches the current source
census. Generic manifests, stale pre-selection reports and failed revisions are removed before the
prompt. A declaration also fails when all thirteen architecture axes collapse onto a handful of
generic entrypoints: each auditor must expose a mechanically diverse definition map.
"""
from collections import Counter

from . import observatory_genome_realization_overlay as genome


_REQUIRED = {
    group for groups in genome.REQUIRED_GROUPS.values() for group in groups
}
MIN_UNIQUE_DEFINITION_CITATIONS = 8
MAX_AXES_PER_DEFINITION = 4


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
        definition_use = Counter()
        for axis, validated_axis in zip(genome.oroles.GENOME_FIELDS, validated):
            row = by_axis[axis]
            axis_pairs = set()
            for citation in row.get("source_symbols") or []:
                pair = (citation.get("artifact"), citation.get("symbol"))
                axis_pairs.add(pair)
                definition_use[pair] += 1
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
            validated_axis["distinct_definition_citations"] = len(axis_pairs)

        if len(definition_use) < MIN_UNIQUE_DEFINITION_CITATIONS:
            raise RuntimeError(
                f"{candidate_id}: genome auditor collapsed thirteen axes onto only "
                f"{len(definition_use)} distinct AST definitions; "
                f"{MIN_UNIQUE_DEFINITION_CITATIONS} required")
        overused = sorted(
            f"{artifact}:{symbol}={count}"
            for (artifact, symbol), count in definition_use.items()
            if count > MAX_AXES_PER_DEFINITION)
        if overused:
            raise RuntimeError(
                f"{candidate_id}: generic definition citation overuse: "
                + ", ".join(overused))
        for validated_axis in validated:
            validated_axis["auditor_definition_diversity"] = {
                "unique_definition_citations": len(definition_use),
                "maximum_axes_per_definition": max(definition_use.values()),
                "minimum_unique_required": MIN_UNIQUE_DEFINITION_CITATIONS,
                "maximum_reuse_allowed": MAX_AXES_PER_DEFINITION,
            }
        return validated

    genome._evidence_catalog = evidence_catalog
    genome._validate = validate
    genome._evidence_binding_hardening_installed = True
    return dict(handlers)
