# 14 — BUDGET, PROGRESS AND STOP CONDITIONS (v1.3)

## Attempt-limit semantics (change vs v1.0)
- FORBIDDEN: arbitrary caps on ENGINEERING ITERATIONS (e.g. MAX_ENGINEERING_ATTEMPTS=3,
  "three huge attempts", per-candidate try counters). Audit greps for iteration-cap patterns
  in builder logic and prompts.
- REQUIRED: bounded TECHNICAL retries with backoff for transient failures:
  MAX_API_RETRIES, MAX_PARSE_RETRIES, MAX_CONTAINER_START_RETRIES, MAX_ATOMIC_WRITE_RETRIES
  (values pinned in config, logged per retry). Unbounded technical retry loops are ALSO forbidden.
Distinction test: does the counter limit *how many times the builder may try to improve the
system* (forbidden) or *how many times a mechanical operation may be re-attempted before
raising* (required)?

## Resource model
Budgets (values from 24, pinned at OBJECTIVE_FROZEN): total API tokens; total cost EUR;
wall-clock; Docker CPU-hours; storage; human-gate windows. Ledger per call (15); alarms
50/80/95%; 10% audit reserve. Development continues while measurable progress exists.

## Progress: new gate passed | defect closed | score improvement | regression reduction |
fidelity increase | generalization to new development seed | (v1.3) frontier advance:
new non-dominated member, successful challenger, resolved anti-satisficing finding,
ceiling raised with evidence.
## Windows & stagnation (unchanged): 2 consecutive zero-progress windows → mandatory
ARCHITECTURE_REVIEW (continue | refactor | fork | replace mechanism | freeze line as
documented failure) — mechanically documented, owner notified.
## Stop conditions (v1.3 — supersede earlier list)
Stopping by attempt counts: FORBIDDEN. Legal stops only (40 §3): verified target attainment ·
documented frontier exhaustion · evidenced architectural impossibility (ADR) · explicit
resource-budget exhaustion (output labeled BEST_DISCOVERED_SO_FAR). Plus unchanged safety
halts: frozen-invariant violation → rollback+ticket; terminal violations → HALTED; owner halt.
Escalation rounds draw from the SAME budget; a reserve share for challenger rounds is an
owner decision (24 §11).
