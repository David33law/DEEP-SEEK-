"""Expose causal genome-ablation receipts in the final independent audit campaign summary."""
from . import observatory_audit_v2 as audit


def install(_ctx, handlers):
    if getattr(audit, "_causal_audit_hardening_installed", False):
        return dict(handlers)
    original = audit._campaigns

    def campaigns(summary):
        result = original(summary)
        controlled = result.setdefault("controlled_genome_realization", {})
        controlled.update({
            "causal_replication": summary.get(
                "genome_causal_ablation_replication_passed", False),
            "causal_crown": summary.get(
                "genome_causal_ablation_crown_passed", False),
            "causal_replication_tasks": summary.get(
                "genome_causal_ablation_replication_tasks", 0),
            "causal_crown_tasks": summary.get(
                "genome_causal_ablation_crown_tasks", 0),
            "causal_replication_negative_controls": summary.get(
                "genome_causal_ablation_replication_controls", 0),
            "causal_crown_negative_controls": summary.get(
                "genome_causal_ablation_crown_controls", 0),
            "causal_definition_set_ablation": True,
            "inert_mutation_controls_required": True,
        })
        result["causal_genome_ablation"] = {
            "replication_passed": controlled["causal_replication"],
            "crown_passed": controlled["causal_crown"],
            "replication_tasks": controlled["causal_replication_tasks"],
            "crown_tasks": controlled["causal_crown_tasks"],
            "replication_negative_controls":
                controlled["causal_replication_negative_controls"],
            "crown_negative_controls":
                controlled["causal_crown_negative_controls"],
            "infrastructure_failure_counts_as_causal_failure": False,
            "exact_mutated_source_receipts_required": True,
        }
        return result

    audit._campaigns = campaigns
    audit._causal_audit_hardening_installed = True
    return dict(handlers)
