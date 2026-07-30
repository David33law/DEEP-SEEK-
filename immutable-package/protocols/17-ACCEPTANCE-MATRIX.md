# 17 — ACCEPTANCE MATRIX (v1.1; thresholds hash-pinned at OBJECTIVE_FROZEN)

| Layer | Success means | Required evidence | Verifier |
|---|---|---|---|
| Protocol | States traversed with guards honored; no forbidden ops; hidden untouched until freeze | state log + attestation + audit greps | 22 (independent) |
| Engineering | Substrate certified; ACTIVE SLICE green ×2 clean runs (SUBSTRATE-GATE-SET + prereqs + targets, per 25); PRESERVED-REGRESSION-SET green; full VD-00..17 green is a program milestone, NOT a per-candidate gate | harness reports + commits | harness + 22 |
| Capability | New capability proven on HIDDEN transfer with valid traces (answer+trace+provenance all pass) | hidden per-capability matrix | 09 grader + 22 |
| Architecture | Capability causally attributed to declared mechanism | fidelity certificate (11) + ablation deltas (12) | 11/12 artifacts |
| LAWMAX progress | Mechanism integrated: no regressions vs B4 green set; provenance+rollback intact | integration run + VD-15/16/17 | harness + 22 |

**Row 0 — minimum first-cycle success (from Charter §4):** hidden transfer case; system flags
one damaging assertive formulation in OUR draft without case-specific hint; explains
who-benefits + linked forum with sources and trace; proposes safe rewrite preserving our
argument; passes diff/invariant verification; routes final choice to lawyer gate.
Pass = all five elements; partial per ground-truth manifest.

Pinned parameters (set in 24, hashed here at freeze): ablation seed count N; noise floor;
hidden pass thresholds per capability; clean-run count (default 2).
Anti-gaming: mechanical (M) scores may NEVER be aggregated with L/P scores into one number.
