"""Final protocol preflight using the bounded specialized evaluator entrypoints.

The source census deliberately matches the owner-ceremony specialized calibration set.  A launch is
refused if the durable systems reference/evaluator pair or any other specialized pair differs from
the hash-bound calibration receipt.
"""
from . import observatory_preflight_v2 as base

base.SPECIALIZED = {
    "systems": (
        "benchmark/observatory_systems_reference_candidate.py",
        "private-evaluator/evaluator/observatory_systems_arena_v2.py"),
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
