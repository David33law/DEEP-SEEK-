# 07 — INCREMENTAL ENGINEERING LOOP (v1.0)

## Mandatory cycle (every builder iteration, no exceptions)
observe repository & current state -> select ONE defect or capability gap -> formulate
explicit falsifiable hypothesis (expected observable delta) -> make minimal scoped change ->
compile -> unit tests -> component tests -> integration tests -> inspect exact expected vs
actual -> record regression status -> preserve passing work (commit granularity: every green
step) -> decide next minimal change.

## Objects
- **Defect ticket**: {id, symptom, exact repro, suspected mechanism, evidence refs}.
- **Hypothesis**: {ticket/gap ref, change plan, predicted test deltas, risk, ablation note}.
- **Change record**: {diff ref, tests before/after, regression table, commit id}.

## Prohibitions (hard, audited)
1. Full bundle rewrite per round. 2. Loss of working code (deleting green paths without
review). 3. "Fixes" without a concrete defect ticket. 4. Changing multiple independent
mechanisms in one change without an ablation plan. 5. Hidden/quiet modification of
acceptance thresholds (thresholds live in 17, hash-pinned). 6. Debugging against hidden set.

## Definitions
Minimal scoped change: touches one mechanism/module + its tests; migration scripts count as
part of the change. Progress: see 14. Stagnation: see 14 (mandatory ARCHITECTURE_REVIEW).
