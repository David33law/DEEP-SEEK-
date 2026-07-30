# 11 — ARCHITECTURE FIDELITY GATE (v1.0)
Runs BEFORE hidden evaluation, on frozen candidate. Failing candidates return to development
WITHOUT consuming hidden budget.

Checks:
1. Declared mechanism EXISTS and is EXERCISED: code path coverage proof on the claimed module
   during visible runs (not just file presence).
2. LOAD-BEARING, not decorative: targeted ablation (12) flips outcomes on the claimed
   capabilities; zero-delta ablation = decorative = FAIL.
3. No silent architecture swap: runtime trace attests the declared mechanism produced the
   results (mechanism ids stamped into reasoning-ledger steps).
4. Ablation genuinely disables (no hidden fallback that re-implements the capability).
5. No hard-coded case patterns: static scan (case strings/regex constants) + reviewer pass +
   variance across regenerated fixtures.
6. No oracle / external hidden dependency: container network-off proof + dependency manifest audit.
Output: fidelity certificate {candidate, checks, evidence refs} -> state FIDELITY_CERTIFIED.
