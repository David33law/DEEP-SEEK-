# 13 — BASELINES AND REFERENCE IMPLEMENTATIONS (v1.0)

## Systems under equal end-to-end conditions
B0 **Deterministic reference implementations**: prove each VD test is solvable (may be
   per-test, non-general); existence proof for the suite, excluded from capability claims.
B1 **Simple deterministic baseline**: substrate + D1/D2 engines only, no P1 adapters.
   Expected: strong on VD-05/06/07/13/14/15/16/17, fails perception/L-level — this failure
   VALIDATES the zone map, so it must be reported, not hidden.
B2 **LLM+tools, no LAWMAX kernel**: raw model with tool access, no certification gates,
   no ledger. The "wrapper" strawman made concrete.
B3 **LLM + verification kernel + human gates** (the CS-01 modus operandi, systematized).
B4 **Current LAWMAX repository as-is** (per reality model; whatever loads and runs).
C* **Candidates**: substrate + candidate mechanism (one per candidate).

## Equality conditions (audited)
Same transport; same execution language profile where feasible; same Docker isolation
(network-off); same CPU/RAM; same persistence rules; same inputs/fixtures/seeds; same
verification pipeline; same timeout policy; same budgets per run class.

## Claim licensing
"Mechanical integrity" claims: beat/equal B1 on M-level tests. "Legal intelligence" claims:
beat B2 AND B3 on L-level capabilities with valid traces (not just answers). "LAWMAX
progress": beat B4 without regressions on B4's green set. Every claim cites the matrix (17).
