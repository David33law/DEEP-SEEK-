# 37 — COMPATIBILITY, CUTOVER & ROLLBACK PLAN (v1.2)
Parallel-run protocol (Wave 5): identical certified inputs through OLD and NEW paths;
deterministic output diff; equivalence report {identical | improved-with-evidence |
degraded(BLOCKING)}. Degradations block cutover — no exceptions without owner gate + ADR.
Cutover (Wave 6): entry criteria = Wave 5 report clean + rollback checkpoint armed + owner
gate. Procedure: repoint entry points; keep old path dormant-but-restorable for the pinned
observation window; self-model updated same commit (38 gate G5).
Rollback triggers: any frozen-invariant violation · regression on preserved set · ledger/
provenance integrity failure · owner command. Rollback = restore checkpoint + repoint entry
points back + incident record; rollback is a TESTED path (drill during Wave 1), not a hope.
Retirement precondition: see 39 — equivalence/superiority proven, reachability of retired
code removed and verified by scan.
