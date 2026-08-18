#!/usr/bin/env python3
"""Contract-compatible hardening of ``observatory_axis_probe_arena``.

Version 2 keeps the exact ``observatory-axis-probe-v1`` report contract and isolation path. Semantic
probe thresholds are loaded from the same owner-signed ``PARETO-DIMENSIONS.json`` used by frontier
admission, eliminating a duplicated policy seat. Formal state-derivation probes require admission
order convergence only when the candidate manifest explicitly claims independent admissions are
commutative. All other baseline/mutant identity and fail-closed behavior remains in the base arena.
"""
from __future__ import annotations

import hashlib
import json
import os

import observatory_axis_probe_arena as base


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
PARETO_PATH = os.path.join(
    ROOT, "profiles", "national-observatory", "PARETO-DIMENSIONS.json")
_REQUIRED_SEMANTIC_DIMENSIONS = sorted({
    dimension
    for dimensions in base.SEMANTIC_DIMENSIONS.values()
    for dimension in dimensions})


def _load_hard_minima():
    if not os.path.isfile(PARETO_PATH):
        raise RuntimeError(
            "axis-probe v2 cannot locate owner-signed Pareto dimensions")
    with open(PARETO_PATH, encoding="utf-8") as handle:
        rows = json.load(handle)
    if not isinstance(rows, list):
        raise RuntimeError("Pareto dimensions must be a JSON array")
    by_id = {
        row.get("id"): row for row in rows
        if isinstance(row, dict) and row.get("id")}
    minima = {}
    for dimension in _REQUIRED_SEMANTIC_DIMENSIONS:
        row = by_id.get(dimension) or {}
        value = row.get("hard_minimum")
        if row.get("direction") != "higher" \
                or not isinstance(value, (int, float)):
            raise RuntimeError(
                "axis probe has no higher-is-better signed hard minimum for "
                + dimension)
        minima[dimension] = float(value)
    return minima


SEMANTIC_HARD_MINIMA = _load_hard_minima()
_ORIGINAL_SEMANTIC_PROBE = base._semantic_probe


def _semantic_probe(source, axis, seed, runtime, expected):
    if axis == "governance_evolution_model":
        return _ORIGINAL_SEMANTIC_PROBE(
            source, axis, seed, runtime, expected)
    dimensions = base.SEMANTIC_DIMENSIONS[axis]
    seeds = [
        int(hashlib.sha256(
            f"semantic-axis|{axis}|{seed}|{index}".encode()).hexdigest()[:8], 16)
        for index in range(4)]
    suite = {
        "suite": "observatory-axis-semantic-hidden-v2",
        "seeds": seeds,
        "scenarios": [
            base.casegen.make_scenario(value, f"AXIS-{axis}-{index:02d}")
            for index, value in enumerate(seeds)],
    }
    report = base.semantic_harness.run_suite(
        source, suite, backend="container", timeout=90)
    scores = report.get("dimension_scores") or {}
    checks = []
    for dimension in dimensions:
        required = SEMANTIC_HARD_MINIMA[dimension]
        checks.append(base._check(
            "semantic-dimension:" + dimension,
            float(scores.get(dimension, 0.0)) + 1e-12 >= required,
            {"score": scores.get(dimension), "required": required}))
    statuses = report.get("scenario_statuses") or []
    checks.append(base._check(
        "semantic-probe-executed",
        len(statuses) == len(seeds)
        and all(value != "CANDIDATE_ERROR" for value in statuses),
        {"scenario_statuses": statuses}))
    return checks, {
        "probe_family": "semantic-hidden-scenarios-v2",
        "pareto_path": os.path.relpath(PARETO_PATH, ROOT).replace("\\", "/"),
        "hard_minima": {
            key: SEMANTIC_HARD_MINIMA[key] for key in dimensions},
        "dimension_scores": {key: scores.get(key) for key in dimensions},
        "scenario_statuses": statuses,
    }


_OLD_DERIVATION = ''' elif axis=="state_derivation_model":
  state=initial_state(); action=admit(SA,A,1,1,"SET",t0)
  one=step(state,action); two=step(state,action)
  check("derivation-deterministic",json.dumps(one,sort_keys=True)==json.dumps(two,sort_keys=True))
  state=one["state"]; before=state_root(copy.deepcopy(state)); dup=step(state,action)
  check("derivation-duplicate-root",state_root(copy.deepcopy(dup["state"]))==before)
  s1=initial_state(); s1=step(s1,action)["state"]; s1=step(s1,admit(SB,B,1,1,"SET",t1))["state"]
  s2=initial_state(); s2=step(s2,admit(SB,B,1,1,"SET",t1))["state"]; s2=step(s2,action)["state"]
  check("derivation-order",state_root(s1)==state_root(s2),{"root_ab":state_root(s1),"root_ba":state_root(s2)})
'''
_NEW_DERIVATION = ''' elif axis=="state_derivation_model":
  state=initial_state(); action=admit(SA,A,1,1,"SET",t0)
  one=step(state,action); two=step(state,action)
  check("derivation-deterministic",json.dumps(one,sort_keys=True)==json.dumps(two,sort_keys=True))
  state=one["state"]; before=state_root(copy.deepcopy(state)); dup=step(state,action)
  check("derivation-duplicate-root",state_root(copy.deepcopy(dup["state"]))==before)
  replay1=initial_state(); replay1=step(replay1,action)["state"]
  replay2=initial_state(); replay2=step(replay2,action)["state"]
  check("derivation-replay-root",state_root(replay1)==state_root(replay2),
        {"root_1":state_root(replay1),"root_2":state_root(replay2)})
  if manifest.get("commutative_independent_admissions") is True:
   s1=initial_state(); s1=step(s1,action)["state"]; s1=step(s1,admit(SB,B,1,1,"SET",t1))["state"]
   s2=initial_state(); s2=step(s2,admit(SB,B,1,1,"SET",t1))["state"]; s2=step(s2,action)["state"]
   check("derivation-order-claimed",state_root(s1)==state_root(s2),
         {"root_ab":state_root(s1),"root_ba":state_root(s2)})
  else:
   check("derivation-order-not-claimed",True,
         {"commutative_independent_admissions":manifest.get("commutative_independent_admissions")})
'''
if _OLD_DERIVATION not in base.FORMAL_PROBE:
    raise RuntimeError(
        "axis-probe v2 cannot locate the formal state-derivation seat")
base.FORMAL_PROBE = base.FORMAL_PROBE.replace(
    _OLD_DERIVATION, _NEW_DERIVATION, 1)
base._semantic_probe = _semantic_probe
base.PROBES["semantic"] = _semantic_probe

main = base.main

__all__ = [
    "main", "SEMANTIC_HARD_MINIMA", "PARETO_PATH",
]


if __name__ == "__main__":
    import sys
    sys.exit(main())
