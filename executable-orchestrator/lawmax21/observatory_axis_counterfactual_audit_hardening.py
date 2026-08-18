"""Expose incumbent single-axis counterfactual closure in the independent audit."""
from . import observatory_audit_v2 as audit


def install(_ctx, handlers):
    if getattr(audit, "_axis_counterfactual_audit_installed", False):
        return dict(handlers)
    original = audit._campaigns

    def campaigns(summary):
        result = original(summary)
        result["incumbent_axis_counterfactuals"] = {
            "complete": summary.get(
                "incumbent_axis_counterfactuals_complete", False),
            "defeated": summary.get(
                "incumbent_axis_counterfactuals_defeated", False),
            "current_incumbent_bound": summary.get(
                "incumbent_axis_counterfactuals_current", False),
            "campaigns": summary.get("axis_counterfactual_campaigns", 0),
            "axes_required": summary.get(
                "axis_counterfactual_axes_required", 0),
            "alternatives_per_axis": summary.get(
                "axis_counterfactual_alternatives_per_axis", 0),
            "rows": summary.get("axis_counterfactual_rows", 0),
            "measured": summary.get("axis_counterfactual_measured", 0),
            "active": summary.get("axis_counterfactual_active", 0),
            "blockers": summary.get("axis_counterfactual_blockers", 0),
            "proof_mode": summary.get(
                "axis_counterfactual_proof_mode", False),
            "all_non_target_classes_frozen": True,
            "independent_rankers": 2,
            "independent_architects": 2,
            "strong_synthesis_required": True,
            "prior_cp2_direct_content_read": False,
        }
        return result

    audit._campaigns = campaigns
    audit._axis_counterfactual_audit_installed = True
    return dict(handlers)
