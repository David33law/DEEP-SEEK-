"""Require the two genome-realization auditors to produce materially independent evidence maps.

Distinct role names, tickets and report hashes are not enough: changing only ``auditor_id`` would
satisfy those checks while reproducing one reasoning trajectory. This hardening compares the actual
per-axis AST-definition citation sets returned by the two auditors. At least four of the thirteen
axes must use a different source-definition map, while both complete maps must separately pass the
trusted source/evidence validator. The shared ``_passes`` predicate is also strengthened so terminal
conditions cannot accept a stored report that omits this independence evidence.
"""
from . import observatory_genome_realization_overlay as genome
from .canonical import atomic_write_json
from .handlers import A

MIN_DIFFERING_AXIS_MAPS = 4


def _axis_map(auditor):
    report = auditor.get("report") or {}
    result = {}
    for row in report.get("axis_reviews") or []:
        axis = row.get("axis")
        citations = tuple(sorted(
            (str(item.get("artifact")), str(item.get("symbol")))
            for item in row.get("source_symbols") or []))
        if axis:
            result[str(axis)] = citations
    return result


def install(_ctx, handlers):
    if getattr(genome, "_cross_auditor_hardening_installed", False):
        return dict(handlers)
    original_audit = genome._audit
    original_passes = genome._passes

    def audit(context, candidate_id, label):
        artifact = original_audit(context, candidate_id, label)
        auditors = artifact.get("auditors") or []
        if len(auditors) != 2:
            raise RuntimeError(
                f"{candidate_id}/{label}: expected exactly two genome auditors")
        maps = [_axis_map(row) for row in auditors]
        required_axes = set(genome.oroles.GENOME_FIELDS)
        if any(set(mapping) != required_axes for mapping in maps):
            raise RuntimeError(
                f"{candidate_id}/{label}: an auditor citation map omits controlled axes")
        differing = sorted(
            axis for axis in genome.oroles.GENOME_FIELDS
            if maps[0][axis] != maps[1][axis])
        if len(differing) < MIN_DIFFERING_AXIS_MAPS:
            raise RuntimeError(
                f"{candidate_id}/{label}: genome auditors differ on only "
                f"{len(differing)} axis citation maps; "
                f"{MIN_DIFFERING_AXIS_MAPS} required")
        artifact["auditor_citation_map_differing_axes"] = differing
        artifact["auditor_citation_map_differing_count"] = len(differing)
        artifact["auditor_citation_maps_independent"] = True
        path = A(
            context, "architecture",
            f"genome-realization-{label}-{candidate_id}.json")
        atomic_write_json(path, artifact)
        return artifact

    def passes(report):
        return (
            original_passes(report)
            and report.get("auditor_citation_maps_independent") is True
            and int(report.get(
                "auditor_citation_map_differing_count", 0))
            >= MIN_DIFFERING_AXIS_MAPS)

    genome._audit = audit
    genome._passes = passes
    genome._cross_auditor_hardening_installed = True
    return dict(handlers)
