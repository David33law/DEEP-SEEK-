"""Expose causal genome-ablation and exact axis-probe receipts in the final audit."""
from . import observatory_audit_v2 as audit


PROBE_CONTRACT = "observatory-axis-probe-v1"
PROBE_EVALUATOR = "observatory_axis_probe_arena_v2.py"


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
            "axis_specific_attribution_required": summary.get(
                "genome_axis_specific_attribution_required", False),
            "axis_specific_replication_passed": summary.get(
                "genome_axis_specific_replication_passed", False),
            "axis_specific_crown_passed": summary.get(
                "genome_axis_specific_crown_passed", False),
            "axis_specific_replication_tasks": summary.get(
                "genome_axis_specific_replication_tasks", 0),
            "axis_specific_replication_attributed": summary.get(
                "genome_axis_specific_replication_attributed", 0),
            "axis_specific_crown_tasks": summary.get(
                "genome_axis_specific_crown_tasks", 0),
            "axis_specific_crown_attributed": summary.get(
                "genome_axis_specific_crown_attributed", 0),
            "definition_semantics_required": summary.get(
                "genome_definition_semantic_attribution_required", False),
            "axis_behavioral_failure_required": summary.get(
                "genome_axis_behavioral_failure_required", False),
            "definition_semantics_replication_checked": summary.get(
                "genome_definition_semantic_replication_checked", False),
            "definition_semantics_crown_checked": summary.get(
                "genome_definition_semantic_crown_checked", False),
            "definition_semantics_replication_tasks": summary.get(
                "genome_definition_semantic_replication_tasks", 0),
            "definition_semantics_replication_failure_scoped": summary.get(
                "genome_definition_semantic_replication_failure_scoped", 0),
            "definition_semantics_replication_behavioral": summary.get(
                "genome_definition_semantic_replication_behavioral", 0),
            "definition_semantics_crown_tasks": summary.get(
                "genome_definition_semantic_crown_tasks", 0),
            "definition_semantics_crown_failure_scoped": summary.get(
                "genome_definition_semantic_crown_failure_scoped", 0),
            "definition_semantics_crown_behavioral": summary.get(
                "genome_definition_semantic_crown_behavioral", 0),
            "axis_behavioral_probe_required": summary.get(
                "genome_axis_behavioral_probe_required", False),
            "axis_behavioral_probe_contract": summary.get(
                "genome_axis_behavioral_probe_contract"),
            "axis_behavioral_probe_evaluator": summary.get(
                "genome_axis_behavioral_probe_evaluator"),
            "axis_behavioral_probe_replication_checked": summary.get(
                "genome_axis_behavioral_probe_replication_checked", False),
            "axis_behavioral_probe_crown_checked": summary.get(
                "genome_axis_behavioral_probe_crown_checked", False),
            "axis_behavioral_probe_replication_tasks": summary.get(
                "genome_axis_behavioral_probe_replication_tasks", 0),
            "axis_behavioral_probe_replication_pairs": summary.get(
                "genome_axis_behavioral_probe_replication_pairs", 0),
            "axis_behavioral_probe_crown_tasks": summary.get(
                "genome_axis_behavioral_probe_crown_tasks", 0),
            "axis_behavioral_probe_crown_pairs": summary.get(
                "genome_axis_behavioral_probe_crown_pairs", 0),
            "causal_definition_set_ablation": True,
            "inert_mutation_controls_required": True,
        })
        all_axis_specific = bool(
            controlled["axis_specific_attribution_required"] is True
            and controlled["axis_specific_replication_passed"] is True
            and controlled["axis_specific_crown_passed"] is True
            and int(controlled["axis_specific_replication_tasks"]) > 0
            and int(controlled["axis_specific_crown_tasks"]) > 0
            and int(controlled["axis_specific_replication_tasks"])
            == int(controlled["axis_specific_replication_attributed"])
            and int(controlled["axis_specific_crown_tasks"])
            == int(controlled["axis_specific_crown_attributed"]))
        all_definition_semantics = bool(
            controlled["definition_semantics_required"] is True
            and controlled["axis_behavioral_failure_required"] is True
            and controlled["definition_semantics_replication_checked"] is True
            and controlled["definition_semantics_crown_checked"] is True
            and int(controlled["definition_semantics_replication_tasks"]) > 0
            and int(controlled["definition_semantics_crown_tasks"]) > 0
            and int(controlled["definition_semantics_replication_tasks"])
            == int(controlled[
                "definition_semantics_replication_failure_scoped"])
            == int(controlled[
                "definition_semantics_replication_behavioral"])
            and int(controlled["definition_semantics_crown_tasks"])
            == int(controlled[
                "definition_semantics_crown_failure_scoped"])
            == int(controlled[
                "definition_semantics_crown_behavioral"]))
        all_probe_pairs = bool(
            controlled["axis_behavioral_probe_required"] is True
            and controlled["axis_behavioral_probe_contract"] == PROBE_CONTRACT
            and controlled["axis_behavioral_probe_evaluator"] == PROBE_EVALUATOR
            and controlled["axis_behavioral_probe_replication_checked"] is True
            and controlled["axis_behavioral_probe_crown_checked"] is True
            and int(controlled["axis_behavioral_probe_replication_tasks"]) > 0
            and int(controlled["axis_behavioral_probe_crown_tasks"]) > 0
            and int(controlled["axis_behavioral_probe_replication_tasks"])
            == int(controlled["axis_behavioral_probe_replication_pairs"])
            == int(controlled["causal_replication_tasks"])
            and int(controlled["axis_behavioral_probe_crown_tasks"])
            == int(controlled["axis_behavioral_probe_crown_pairs"])
            == int(controlled["causal_crown_tasks"]))
        result["causal_genome_ablation"] = {
            "replication_passed": controlled["causal_replication"],
            "crown_passed": controlled["causal_crown"],
            "replication_tasks": controlled["causal_replication_tasks"],
            "crown_tasks": controlled["causal_crown_tasks"],
            "replication_negative_controls":
                controlled["causal_replication_negative_controls"],
            "crown_negative_controls":
                controlled["causal_crown_negative_controls"],
            "axis_specific_attribution_required": controlled[
                "axis_specific_attribution_required"],
            "all_tasks_axis_specifically_attributed": all_axis_specific,
            "replication_axis_specific_tasks": controlled[
                "axis_specific_replication_attributed"],
            "crown_axis_specific_tasks": controlled[
                "axis_specific_crown_attributed"],
            "cited_definition_semantics_required": controlled[
                "definition_semantics_required"],
            "axis_specific_behavioral_failure_required": controlled[
                "axis_behavioral_failure_required"],
            "all_tasks_definition_semantics_checked":
                all_definition_semantics,
            "all_tasks_axis_behaviorally_falsified":
                bool(all_definition_semantics and all_probe_pairs),
            "replication_definition_semantics_tasks": controlled[
                "definition_semantics_replication_failure_scoped"],
            "crown_definition_semantics_tasks": controlled[
                "definition_semantics_crown_failure_scoped"],
            "replication_axis_behavioral_failures": controlled[
                "definition_semantics_replication_behavioral"],
            "crown_axis_behavioral_failures": controlled[
                "definition_semantics_crown_behavioral"],
            "axis_behavioral_probe_required": controlled[
                "axis_behavioral_probe_required"],
            "axis_behavioral_probe_contract": controlled[
                "axis_behavioral_probe_contract"],
            "axis_behavioral_probe_evaluator": controlled[
                "axis_behavioral_probe_evaluator"],
            "all_tasks_have_baseline_mutant_probe_pairs": all_probe_pairs,
            "replication_axis_probe_tasks": controlled[
                "axis_behavioral_probe_replication_tasks"],
            "replication_axis_probe_pairs": controlled[
                "axis_behavioral_probe_replication_pairs"],
            "crown_axis_probe_tasks": controlled[
                "axis_behavioral_probe_crown_tasks"],
            "crown_axis_probe_pairs": controlled[
                "axis_behavioral_probe_crown_pairs"],
            "diagnostic_failure_attribution_is_sufficient": False,
            "removed_definition_name_is_sufficient": False,
            "group_failure_path_is_sufficient": False,
            "whole_success_receipt_searched": False,
            "infrastructure_failure_counts_as_causal_failure": False,
            "exact_mutated_source_receipts_required": True,
        }
        return result

    audit._campaigns = campaigns
    audit._causal_audit_hardening_installed = True
    return dict(handlers)
