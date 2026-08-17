"""Final preflight with cross-model legal consistency in the required Pareto census."""
from . import observatory_preflight_v2 as core
from . import observatory_preflight_v3 as base

core.REQUIRED_DIMENSIONS.add("cross_model_consistency_survival")
PreflightFailed = base.PreflightFailed
run = base.run

__all__ = ["PreflightFailed", "run"]
