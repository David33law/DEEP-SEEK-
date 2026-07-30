# 08 — VISIBLE DEVELOPMENT SUITE SPEC (v1.1 — CAPABILITY-SLICED)
Change vs v1.0: the all-green VD-01..17 precondition for candidate freeze is ABOLISHED.
Gating is per capability slice. Full-suite green remains only a LONG-HORIZON milestone.

## Gate sets
- **SUBSTRATE-GATE-SET (always required, small):** VD-13 (draft surgery+diff), VD-15
  (persistence), VD-16 (rollback), VD-17 (ledger integrity), plus schema self-test VD-00.
- **CAPABILITY-DEPENDENCY-MATRIX:** file 25 declares, per capability: prerequisites,
  target tests, non-regression set, and tests IRRELEVANT for the cycle (explicitly listed
  so their absence is a decision, not an accident).
- **CANDIDATE-SPECIFIC-GATE-SET:** target tests of the claimed capability + its prerequisites.
- **PRESERVED-REGRESSION-SET:** everything ever green stays green (auto-accumulating).

## Freeze rule (replaces v1.0 rule)
CANDIDATE_FROZEN requires: SUBSTRATE-GATE-SET green + candidate's prerequisite tests green +
candidate target tests green ×2 consecutive clean runs + PRESERVED-REGRESSION-SET green.
Nothing else. First admission-risk cycle explicitly does NOT require scan ingestion (VD-01),
timelines (VD-04), full deadline engine (VD-07) — see matrix.

## Test catalog VD-00..VD-17
VD-00 schemas/self-test; VD-01 ingestion; VD-02 entity resolution; VD-03 contradiction;
VD-04 timeline; VD-05 arithmetic/plausibility; VD-06 supersedence; VD-07 rule/deadline;
VD-08 subsumption trace; VD-09 epistemic uncertainty; VD-10 admission-risk (10a detect,
10b safe-rewrite verified); VD-11 strategic omission (11a direct block, 11b indirect);
VD-12 constraint/self-model compliance; VD-13 draft surgery+diff; VD-14 citation/quote
faithfulness; VD-15 persistence; VD-16 rollback; VD-17 ledger integrity.
Acceptance cores as in v1.0 (unchanged semantics), now referenced by slices.

## Feedback contract (unchanged)
Full visibility: exact inputs, expected, actual, traces, protocol errors, provenance
failures, invariant violations, regression diffs. Machine-readable report per run.
Hidden material NEVER used for debugging.
