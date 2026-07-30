# LAWMAX EXPERIMENT PACK v1.3 (PROTOCOL) — INDEX, DEPENDENCY MAP, EXECUTION ORDER
(v1.3 = v1.2 + Mandatory Upward Escalation & Anti-Satisficing Addendum, αρχεία 40-47)
Author: Claude (empirical executor of CASE STUDY 01 — DIMITRIADIS) · 2026-07-28
Consumers: D. (lawyer/owner), ChatGPT (co-designer), DeepSeek V4 Pro (builder).

## Grounding statement (read first)
This package is **repository-agnostic by design**. Its author has NOT seen the existing
LAWMAX repository (Common Lisp systems, CP0–CP6, the eight CP6 candidates, failed E1,
tournament records). Per file 04, grounding in repository reality is performed AT RUNTIME
by the builder, with executable evidence. Nothing in this pack asserts repo facts.
If the owner grants repository access to the author, a v1.1 GROUNDED ANNEX will be issued
(pre-filled reality model + mapping of CP6 candidates to the discovery protocol).

## Files
- INDEX.md (this file: dependency map, execution order)
- 00-LAWMAX-SYSTEM-OBJECTIVE-CHARTER.md  [EL]
- 01-LAWMAX-NON-GOALS-AND-BOUNDARIES.md  [EL]
- 02-EMPIRICAL-CASE-STUDY-REGISTER.md    [EL]
- 03-LAWMAX-CAPABILITY-ONTOLOGY.yaml     [EN]
- 04-REPOSITORY-REALITY-RECONSTRUCTION-PROTOCOL.md [EN]
- 05-SHARED-CAPABILITY-SUBSTRATE-SPEC.md [EN]
- 06-ARCHITECTURE-DISCOVERY-PROTOCOL.md  [EN]
- 07-INCREMENTAL-ENGINEERING-LOOP.md     [EN]
- 08-VISIBLE-DEVELOPMENT-SUITE-SPEC.md   [EN]
- 09-HIDDEN-EVALUATION-PROTOCOL.md       [EN]
- 10-TRANSFER-CASE-GENERATION-SPEC.md    [EN/EL]
- 11-ARCHITECTURE-FIDELITY-GATE.md       [EN]
- 12-CAUSAL-ABLATION-PROTOCOL.md         [EN]
- 13-BASELINES-AND-REFERENCE-IMPLEMENTATIONS.md [EN]
- 14-BUDGET-PROGRESS-AND-STOP-CONDITIONS.md [EN]
- 15-EVIDENCE-PROVENANCE-AND-AUDIT.md    [EN]
- 16-RESUME-RECOVERY-AND-CRASH-SAFETY.md [EN]
- 17-ACCEPTANCE-MATRIX.md                [EN]
- 18-DEEPSEEK-MASTER-SYSTEM-PROMPT.md    [EN]
- 19-DEEPSEEK-RUNNER-STATE-MACHINE.md    [EN]
- 20-EXPERIMENT-FILESYSTEM-LAYOUT.md     [EN]
- 21-POWERSHELL-LAUNCH-AND-RECOVERY-SPEC.md [EN] (v1.1: filename corrected per review; implementation lives in the Executable Scaffold zip)
- 22-INDEPENDENT-COMPLETION-AUDIT-SPEC.md [EN]
- 23-RISK-REGISTER.md                    [EL/EN]
- 24-OPEN-DECISIONS-FOR-LAWYER.md        [EL] ← requires owner's answers BEFORE launch
- 25-CAPABILITY-DEPENDENCY-MATRIX.yaml   [EN] (v1.1: slice gating source of truth)
- 26-CONTEXT-COMPILER-SPEC.md            [EN] (v1.1)
- 27-V1.1-CHANGELOG-AND-REVIEW-RESPONSE.md [EL/EN] (v1.1, με προσάρτημα v1.2)
- 28-LAWMAX-TARGET-ARCHITECTURE-SYNTHESIS-PROTOCOL.md [EN] (v1.2)
- 29-AS-IS-TO-TARGET-GAP-MATRIX.yaml [EN] (v1.2, schema/template)
- 30-TARGET-LAWMAX-ARCHITECTURE-v0.md + .json [EN] (v1.2, template + a-priori invariants)
- 31-TARGET-COMPONENT-AND-SYSTEM-GRAPH.json + .dot [EN] (v1.2, layer level)
- 32-CAPABILITY-TO-ARCHITECTURE-TRACEABILITY.yaml [EN] (v1.2)
- 33-ARCHITECTURE-DECISION-REGISTER/ [EN] (v1.2, ADR-0000 in)
- 34-TARGET-LAWMAX-ARCHITECTURE-v1-EVIDENCE-REVISED.md + .json [EN] (v1.2, post-experiment)
- 35-EXPERIMENT-TO-ARCHITECTURE-DECISION-MATRIX.yaml [EN] (v1.2)
- 36-LAWMAX-RESTRUCTURING-AND-MIGRATION-ROADMAP.md + .json [EN] (v1.2, waves 0-7)
- 37-COMPATIBILITY-CUTOVER-AND-ROLLBACK-PLAN.md [EN] (v1.2)
- 38-RESTRUCTURING-ACCEPTANCE-GATES.md [EN] (v1.2, G1-G9)
- 39-DEPRECATION-AND-LEGACY-RETIREMENT-REGISTER.yaml [EN] (v1.2)
- 40-MANDATORY-UPWARD-ESCALATION-PROTOCOL.md [EN] (v1.3)
- 41-ARCHITECTURE-ALTITUDE-LADDER.yaml [EN] (v1.3)
- 42-PARETO-FRONTIER-AND-DOMINANCE-GATE.md [EN] (v1.3)
- 43-ANTI-SATISFICING-AUDIT-SPEC.md [EN] (v1.3)
- 44-SUCCESSOR-AND-RADICAL-CHALLENGER-PROTOCOL.md [EN] (v1.3)
- 45-ARCHITECTURE-CEILING-ANALYSIS-SPEC.md [EN] (v1.3)
- 46-FRONTIER-MEMORY-SCHEMA.json [EN] (v1.3)
- 47-HIGHEST-EVIDENCE-SUPPORTED-ARCHITECTURE-REPORT.md [EN] (v1.3)
Companion evidence file (already delivered separately): LAWMAX_Reverse_Engineering_Spec.md = CASE STUDY 01.

## Dependency map
00 ← (root; everything cites it)
01 ← 00
02 ← 00, LAWMAX_Reverse_Engineering_Spec.md
03 ← 02 (capabilities evidenced by CS-01)
04 ← 00,01 (first executable phase; produces REPOSITORY-REALITY-MODEL.md)
05 ← 03,04 (substrate implements ontology ports; reuses per reality model)
06 ← 03,04,05 (candidates target ontology gaps on frozen substrate)
07 ← 05,06 (loop operates on substrate+candidate)
08 ← 03,05,10 (visible fixtures) · 09 ← 03,10,11 (hidden) · 10 ← 02,03
11 ← 06,12 · 12 ← 06,08 · 13 ← 05,08,09 · 14 ← 07,19 · 15 ← 05 · 16 ← 15,19,20,21
17 ← 03,08,09,11,12,13,14 · 18 ← ALL protocols · 19 ← 14,16,17 · 20 ← 15,16 · 21 ← 16,19,20 · 22 ← 15,17,19
23,24 ← ALL.

## Recommended execution order
Phase 0 (human): answer 24-OPEN-DECISIONS; freeze budget numbers into 14; independent party
generates & seals hidden set per 09/10 (hash committed into audit/attestation.json).
Phase 1: builder bootstrap per 18/19 → ATTESTED → run 04 → REPOSITORY_RECONSTRUCTED.
Phase 1.5 (v1.2): SYSTEM_ARCHITECTURE_SYNTHESIS per 28 → TARGET v0 (29-33) → owner review → v0 FROZEN. Καμία κατασκευή substrate/tournament πριν από αυτό.
Phase 2: OBJECTIVE_FROZEN (00/01/03 hashes recorded) → build/certify substrate per 05, gated by 08 subset (VD-13..17).
Phase 3: architecture discovery per 06 → candidate build per 07 → visible gates per 08.
Phase 4: fidelity gate 11 → freeze → hidden 09 → ablation 12 → transfer per 10 → acceptance per 17.
Phase 4 (v1.3 loop): κάθε επιτυχών candidate → frontier → ceiling (45) → successors/challengers (44) → Pareto/dominance (42) → anti-satisficing audit (43) → escalate ή freeze. Μετά: Phase 4.5 (v1.2): ARCHITECTURE_EVIDENCE_SYNTHESIS → TARGET v1 (34,35) → MIGRATION_PLAN_FROZEN (36,37,38).
Phase 5: RESTRUCTURING waves 0-7 → G1-G9 → RESTRUCTURING_CERTIFIED → independent audit 22 → COMMITTED (or REJECTED_WITH_EVIDENCE / ARCHITECTURE_REVIEW per 14).

## Day-1 shortlist (anti-bureaucracy note)
The six files that must be RIGHT before anything else matters: 04, 05, 07, 08, 14, 21.
The rest exist to keep days 3–30 honest. Do not let the operating system eat the project.
