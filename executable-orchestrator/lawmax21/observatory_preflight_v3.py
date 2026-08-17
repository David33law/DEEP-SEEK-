"""Final protocol preflight using the bounded specialized evaluator entrypoints."""
from . import observatory_preflight_v2 as base

base.SPECIALIZED = {
    "distributed": (
        "benchmark/observatory_distributed_reference_candidate.py",
        "private-evaluator/evaluator/observatory_distributed_arena_v2.py"),
    "scale": (
        "benchmark/observatory_scale_reference_candidate.py",
        "private-evaluator/evaluator/observatory_scale_arena_v2.py"),
    "formal": (
        "benchmark/observatory_formal_reference_candidate.py",
        "private-evaluator/evaluator/observatory_formal_arena_v2.py"),
    "interoperability": (
        "benchmark/observatory_interoperability_reference_candidate.py",
        "private-evaluator/evaluator/observatory_interoperability_arena_v2.py"),
}

PreflightFailed = base.PreflightFailed
run = base.run

__all__ = ["PreflightFailed", "run"]
