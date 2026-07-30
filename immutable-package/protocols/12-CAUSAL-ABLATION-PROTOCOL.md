# 12 — CAUSAL ABLATION PROTOCOL (v1.0)

Contract per candidate: FULL mechanism enabled vs SAME system with ONLY that mechanism
disabled (substrate flag; adapter returns "capability unavailable", not a rival heuristic).

Forbidden ablations: crashing the program; changing transport; removing shared infrastructure;
alternate fallback that masks the delta.

Measurement: per-capability delta table (ontology ids) across >= N seeds/fixtures (N pinned in
17); report both aggregate and WHICH capabilities moved; ablation runs use identical budgets/
pipeline (13). Causality claim allowed ONLY if: mechanism-on wins the claimed capabilities AND
fidelity gate 11 passed AND deltas exceed pinned noise floor.
Artifacts: ablation config, run logs, delta table, conclusion -> state ABLATION_EVALUATED.
