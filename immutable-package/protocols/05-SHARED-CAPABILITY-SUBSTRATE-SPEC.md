# 05 — SHARED CAPABILITY SUBSTRATE SPEC (v1.0)
Built ONCE (state SUBSTRATE_BUILDING -> SUBSTRATE_CERTIFIED). Candidates are modules behind
frozen ports; they never fork the substrate. Substrate contains ZERO case A-Box data.

## Elements & contracts
1. **Document/Case object model**: objects per CS-01 spec section E (Entity, IdentityVariant,
   Document(+supersedes), DocumentSpan, ExtractedClaim, CertifiedFact, ContestedFact,
   Allegation, Evidence, Contradiction, TimelineEvent, LegalRule(T-Box), ApplicabilityCondition,
   Argument, Counterargument, AdmissionRisk, StrategicSilence, ClientConstraint, LawyerDecision,
   OpenQuestion, MissingDocument, Deadline, DraftSpan, ProposedEdit, Approval).
   Epistemic states: RAW -> EXTRACTED(p) -> CERTIFIED | CONTESTED; DECIDED for H1 outputs.
2. **Event store**: append-only, hash-chained; every mutation = event {actor, mechanism,
   inputs, prior_state_ref, reason, rollback_ref}. Materialized views rebuildable by replay.
3. **Provenance**: assertion -> {doc, page, span/region, extractor, t, certifier, t2, chain-hash}.
   No object without provenance refs (enforced at write).
4. **Component registry**: {component_id, version, ports_implemented[], health, owner_candidate}.
5. **Capability registry**: ontology_id (03) -> {components[], maturity, last_certification_run}.
6. **Reasoning Ledger**: typed steps of the Charter chain; replayable; every step links
   spans+rules+facts by id; Workspace items may be referenced but marked non-certified.
7. **Checkpoint/rollback**: named checkpoints = event index + view hashes; restore = replay.
8. **Test harness**: runs VD suite; machine-readable report {test, expected, actual, status,
   artifacts}; consumed by state machine.
9. **Resource accounting**: per-call tokens/cost/wall-clock, per-phase ledger, budget alarms.
10. **Human decision gates**: queue of {question, options, context_refs, irreversible?};
    decisions persisted as LawyerDecision events; blocking semantics.
11. **Verification kernel**: pure-function checks (diff==spec, invariants, schema, quote
    exact-match, citation status, token-blocks, checksum validators, ledger integrity);
    every deliverable passes kernel BEFORE gate queue.
12. **Ports for P1 adapters**: Perception, Translation/Alignment, HypothesisGen, StyleDraft,
    AdversarialGen. Adapter output enters ONLY as EXTRACTED(p) with mandatory verification path.

## Type rule (hard)
Analysis engines accept CERTIFIED only; Draft Surgery accepts approved edit-specs only;
kernel runs on every output; H1 never auto-decided. Violations = contract breach events
(visible in selfmodel.report) and build failures.

## Freeze policy
Ports+schemas freeze at SUBSTRATE_CERTIFIED. Changes only via ARCHITECTURE_REVIEW with
migration script + replay test. Reuse from existing repo is REQUIRED where the reality
model (04) scores an existing mechanism maturity >= new proposal.
