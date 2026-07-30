# 28 — TARGET ARCHITECTURE SYNTHESIS PROTOCOL (v1.2)

## The two architectures (hard distinction)
- **Experimental Capability Substrate (05):** neutral shared environment for fair build,
  comparison and ablation of candidate mechanisms. Serves the EXPERIMENT.
- **Production LAWMAX Target Architecture:** the intended final structure of the real
  LAWMAX repository — Common Lisp systems, memory, reasoning kernel, legal modules,
  adapters, runtime. Serves the SYSTEM.
RULE: the experimental substrate is NEVER automatically the target architecture. Promotion
of any substrate element into the target requires an ADR (33) with repository evidence.

## When synthesis runs
After REPOSITORY_RECONSTRUCTED, before any SUBSTRATE_BUILDING or tournament:
SYSTEM_ARCHITECTURE_SYNTHESIS → TARGET_ARCHITECTURE_PROPOSED → TARGET_ARCHITECTURE_REVIEWED
(owner gate) → TARGET_ARCHITECTURE_v0_FROZEN. No repository modifications during synthesis.

## Inputs
REPOSITORY-REALITY-MODEL.{md,json} · HISTORICAL-EXPERIMENT-MAP.json · CP6-E1-POSTMORTEM.md ·
REUSE-REPAIR-REPLACE-MATRIX.json · Charter (00) · Non-goals (01) · Capability ontology (03).

## Mandatory alternatives (minimum three, none preselected)
A1 **Conservative evolutionary restructuring** — maximal reuse of existing Common Lisp architecture.
A2 **Layered institutional restructuring** — explicit trusted kernel / institutional services /
   legal cognition / external adapters layering.
A3 **Port-governed polyglot perimeter** — Common Lisp institutional core; external deterministic
   or probabilistic services allowed ONLY behind strict contracts.
Additional alternatives allowed. FORBIDDEN: preselecting polyglot or total reorganization
without executable repository evidence.

## Evaluation criteria (each alternative, scored with evidence)
charter fit · exploitation of existing assets · technical+epistemic risk · migration cost ·
rollback capability · API independence · auditability · real-time prospects · safe
self-improvement capability · support for capability levels L3/L4/L5/L6.

## Outputs (this phase)
29 (as-is→target gap matrix) · 30 (TARGET v0 .md+.json) · 31 (component/system graph
.json+.dot) · 32 (capability→architecture traceability) · 33 (ADR register, first entries).
TARGET v0 must explicitly list its OPEN ARCHITECTURAL QUESTIONS, each bound to experiments
(32). v0 is a controlled hypothesis, not final truth; it defines what the experiments must answer.

## After the experiments
ARCHITECTURE_EVIDENCE_SYNTHESIS → TARGET_ARCHITECTURE_v1_PROPOSED → _REVIEWED →
MIGRATION_PLAN_FROZEN → RESTRUCTURING_IN_PROGRESS (waves, file 36) → RESTRUCTURING_CERTIFIED.
Outputs: 34, 35, 36, 37, 38, 39. Every capability experiment MUST have a declared impact on
the target architecture (32); experiments without declared impact are not scheduled.

## Grounding status of this pack (honesty clause)
Files 29-31 ship as SCHEMAS/TEMPLATES plus a-priori invariants only. Their as-is content can
be filled EXCLUSIVELY from the REPOSITORY REALITY MODEL, which requires repository access.
Any pre-filled component claims about the existing repo would be fabrication and are absent.
