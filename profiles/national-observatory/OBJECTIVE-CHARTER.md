# NATIONAL LEGAL OBSERVATORY — OBJECTIVE CHARTER v1

## 1. Mission
The target is a permanent, reconstructable and auditable national-scale observatory of the Greek legal order. It must ingest and preserve primary legal sources, detect every legally material change, reconstruct what law was effective at any requested time, connect jurisprudence to the exact temporal version of the provisions it applies, keep legal doctrine/theory epistemically distinct from binding authority, and publish verifiable human- and machine-readable outputs.

The target is not a news scraper, PDF archive, RAG wrapper, search engine, amendment feed, case-law database, or generic knowledge graph. Those may exist only as subordinate projections or adapters.

## 2. Source classes
The architecture must support at minimum:
- legislation and Government Gazette material, including corrections;
- amendments, repeals, suspensions, revivals, transitional provisions and codifications;
- judicial decisions and their relation to the exact versions of authorities applied;
- legal doctrine/theory as a distinct epistemic class, never silently promoted to binding law;
- provenance and publication metadata required to independently reconstruct every derived assertion.

## 3. Time model
The observatory must distinguish at least:
- source publication time;
- legal/effective time;
- system transaction/knowledge time;
- correction/retraction time.
A query such as “what law applied on date X?” and “what did the system know on date Y about date X?” must be able to return different, justified answers.

## 4. Trusted-path rule
No probabilistic model may authoritatively decide canonical identity, legal effect, temporal succession, provenance validity, or publication state. Models may propose or extract; deterministic and independently checkable mechanisms decide admission to trusted state.

## 5. Historical integrity
No accepted version may be destructively overwritten. Corrections and later discoveries extend the record. Every published current-state representation must be reproducible from preserved evidence plus declared deterministic transformations.

## 6. National-scale success
A winning architecture must demonstrate, under hidden and adversarial replay, high coverage of sources and changes, correct temporal reconstruction, correct canonical identity, correct normative effects, jurisprudence-to-version linkage, doctrine separation, full provenance, deterministic replay, crash recovery, and bounded publication latency.

## 7. Architecture-discovery rule
The experiment searches whole-system architectures. It must not assume event sourcing, a knowledge graph, SQL, Common Lisp everywhere, microservices, a daemon, or any other implementation family in advance. Existing assets may be reused only when measured evidence shows they belong in the strongest surviving design.

## 8. Reused prior evidence
The previously sealed CP1 repository reconstruction may be reused only when its target commit/tree identity is verified. Earlier CP2 architecture research is prior evidence, not a preselected answer: it remains quarantined until the new Observatory design-space reconstruction has independently produced and challenged its own frontier.

## 9. Completion semantics
A first passing design is never final. It is only a provisional frontier member. Final freeze requires dominance review, radical challengers, simplification challenge, replay evidence, failure injection, independent audit, and no surviving evidence-supported higher architecture within the declared resource envelope.
