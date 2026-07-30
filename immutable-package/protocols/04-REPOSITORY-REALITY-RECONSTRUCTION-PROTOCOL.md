# 04 — REPOSITORY REALITY RECONSTRUCTION PROTOCOL (v1.1)
HARD RULE (v1.1): ARCHITECTURE_DISCOVERY is UNREACHABLE until REPOSITORY-REALITY-MODEL.{md,json},
HISTORICAL-EXPERIMENT-MAP.json, CP6-E1-POSTMORTEM.md and REUSE-REPAIR-REPLACE-MATRIX.json exist
with executable evidence (grounded annex). No exceptions.
Runs FIRST (state ATTESTED -> REPOSITORY_RECONSTRUCTED). No design, no code changes allowed before its output exists.

## Purpose
The existing LAWMAX repository (Common Lisp systems/packages, mirror, capability registry,
provenance/contract/rollback/event mechanisms, subsumption/epistemic/deontic/dialogue
components, prior architecture tournaments, CP0–CP6, eight CP6 candidates, failed E1,
machine results, boundary violations, ablation results, raw artefacts, completion audit)
is NOT assumed empty and NOT assumed rewrite-worthy. The builder must reconstruct reality
with executable evidence before proposing anything.

## Procedure (each step emits evidence records)
1. Inventory: enumerate systems/packages (e.g. *.asd, package manifests), entry points,
   scripts, data dirs, docs, tournament/CP artefact dirs. Evidence: file lists + hashes.
2. Loadability: attempt load/compile per system in isolation. Evidence: exact command,
   full output, exit status.
3. Test reality: discover and run existing test suites per system. Evidence: pass/fail
   counts, failing test names, runtime.
4. Reachability: from declared entry points, trace which components are production-reachable
   vs orphaned. Evidence: call/require graph extraction method + result.
5. History mining: parse CP0–CP6 records, the eight CP6 candidates, E1 failure records,
   machine results, boundary violations, ablations, completion audits into a structured
   HISTORY table: {artefact, claim made, evidence present?, result, lesson}.
6. Maturity scoring: for every mechanism: maturity 0-3 (ontology scale) + repair cost estimate.

## Output: REPOSITORY-REALITY-MODEL.md (+ .json twin)
Per item: {path, kind, loads?, tests?, reachable?, status: production-reachable |
working-isolated | legacy | dead | broken-repairable, reuse recommendation,
already-more-mature-than-new-proposals? (bool + argument), evidence refs}.
Plus: TOP-10 reusable assets, TOP-10 repair candidates, explicit UNKNOWN list.

## Rules
- No claim without executable evidence; absence of evidence => UNKNOWN, never guessed.
- Discovery protocol (06) MUST cite this model when accepting/rejecting reuse of prior
  candidates; "rewrite from scratch" requires model-based justification per component.
- The model is versioned; later corrections are appended, never silently edited.
- Language/runtime decision (keep Common Lisp core vs polyglot substrate) is an OPEN
  DECISION (file 24) taken only AFTER this model exists.
