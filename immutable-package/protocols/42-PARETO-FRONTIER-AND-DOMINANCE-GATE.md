# 42 — PARETO FRONTIER & DOMINANCE GATE (v1.3)
No winner by aggregate score. The frontier is maintained over 12 dimensions:
legal capability · transfer · auditability · provenance · deterministic independence ·
safety · rollback · self-improvement potential · real-time viability · migration cost ·
trusted-kernel complexity · external-model dependence.
Definitions: candidate X DOMINATES Y iff X is no worse on every dimension (beyond the noise
floors pinned in 17) and strictly better on ≥1. The ACTIVE FRONTIER = all non-dominated
members. Frontier updates are ledger events with full dimension vectors (46).
FREEZE RULE: a candidate may freeze ONLY after a dominance review against ALL active frontier
members AND all challengers of its round; the review artifact lists every pairwise verdict
with evidence refs. Aggregating M-level with L-level scores into one number remains forbidden (17).
