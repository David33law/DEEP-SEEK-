# 30 — TARGET LAWMAX ARCHITECTURE v0 (v1.2) — TEMPLATE + A-PRIORI INVARIANTS
STATUS: skeleton with charter-derived invariants. Component content is UNKNOWN until the
REPOSITORY REALITY MODEL exists; filling it without repo evidence is forbidden (28 honesty clause).

## Mandatory sections (to be completed by the builder during synthesis)
institutional+technical invariants · trusted kernel boundary · deliberation workspace ·
certified reasoning ledger · epistemic layer · provenance & event-sourced memory ·
legal-rule & subsumption layer · argumentation/adversarial layer · self-model & capability
registry · safe self-improvement laboratory · document/case services · domain-module
boundary · external-model adapter boundary · human authority gates · runtime/deployment
boundary (candidate: NixOS — OPEN, ties to decision 24#3) · real-time interface boundary ·
full data flows · full dependency directions · forbidden dependencies · failure containment zones.

## A-priori invariants (commitable NOW, independent of repo content)
I1 The certified Reasoning Ledger is append-only and writable ONLY through the trusted kernel.
I2 The Deliberation Workspace can never write the Ledger directly; promotion requires
   verification kernel pass and/or human gate.
I3 External-model adapters (P1) never mutate state; their outputs enter as EXTRACTED(p) only.
I4 The trusted kernel has ZERO dependencies on adapters, UI, or external services;
   dependency arrows point inward only (adapters → services → kernel interfaces, never reverse).
I5 H1 authority lives outside the machine: no code path may commit an H1 decision object
   except the human gate service.
I6 Hidden evaluation material is unreachable from any production or builder path.
I7 Every component declares exactly one rollback unit; no component spans two failure
   containment zones.
I8 Deterministic (D1/D2) certified capabilities must run with all external AI adapters
   disabled (API-independence invariant).
I9 Case A-Box data never enters kernel/services code or configuration.
I10 Self-improvement changes touch production only through the migration-wave machinery (36).

## Per-component descriptor (mandatory schema)
purpose · current repository source (reality ref) · target system/package · inputs · outputs ·
contracts · state owned · trusted/untrusted status · capabilities served (ontology ids) ·
tests · rollback unit · migration requirement.

## Open architectural questions (v0 must enumerate; examples of REQUIRED form)
OQ-01 Can the existing argument subsystem support cross-forum admission-risk detection
      (RETAIN+EXTEND) or is replacement justified? → bound to SLICE-1 experiments (32).
OQ-02 Which existing persistence mechanism, if any, satisfies I1/I2 without wrapping?
OQ-03 Is a polyglot perimeter (A3) necessary for perception adapters, or does A1 suffice?
(Questions OQ-xx are illustrative in FORM; the real list derives from the reality model.)
