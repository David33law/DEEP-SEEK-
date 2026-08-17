"""Final preflight requiring streaming formal evaluation and executable-genome realization."""
from . import observatory_preflight_v2 as core
from . import observatory_preflight_v4 as base

core.SPECIALIZED["formal"] = (
    "benchmark/observatory_formal_reference_candidate.py",
    "private-evaluator/evaluator/observatory_formal_arena_v3.py")
core.REQUIRED_DIMENSIONS.add("genome_realization_survival")

PreflightFailed = base.PreflightFailed
run = base.run

__all__ = ["PreflightFailed", "run"]
