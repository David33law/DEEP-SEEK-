"""Final setup entrypoint using the memory-bounded formal v3 evaluator."""
from . import observatory_setup_v3 as base

base.CAMPAIGNS["formal"]["evaluator"] = (
    "private-evaluator/evaluator/observatory_formal_arena_v3.py")
main = base.main

__all__ = ["main"]
