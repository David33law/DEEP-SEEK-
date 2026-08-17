# NATIONAL LEGAL OBSERVATORY — OBJECTIVE CHARTER v2

## 1. Mission
The target is a permanent, reconstructable, auditable and nationally authoritative observatory of the Greek legal order. It must ingest and preserve primary legal sources, detect every legally material change, reconstruct what law was effective at any requested time, connect jurisprudence to the exact temporal version of the provisions it applies, keep legal doctrine/theory epistemically distinct from binding authority, and publish verifiable human- and machine-readable outputs.

The end state is not merely an internally correct legal database. It is the strongest evidence-supported national legal information infrastructure that can be built from the available public/legal source universe: one canonical legal authority layer from which humans, public institutions, European/interoperability systems and AI systems can consume the Greek legal order without creating competing sources of truth.

The target is not a news scraper, PDF archive, RAG wrapper, search engine, amendment feed, case-law database, generic knowledge graph or LLM agent. Those may exist only as subordinate projections, adapters or tools around the canonical legal state.

## 2. Completeness obligation — no silent legally material loss
The architecture must be designed so that no legally material change can silently escape detection, attribution, temporal-effect analysis, provenance or publication.

A legally material item includes, at minimum, a new enactment, amendment, repeal, suspension, revival, correction, corrigendum, transitional rule, commencement rule, codification/republication event, authoritative metadata correction, conflicting authoritative source, judicial decision with authority/version relevance, or other source event capable of changing what an informed legal user should conclude.

Unknown, unavailable or conflicting evidence may remain explicitly unresolved. Silent omission is not an acceptable representation of uncertainty.

The experiment cannot prove literal omniscience over sources it was never given. It must instead select an architecture whose mechanisms make omissions observable, reconcilable and auditable and whose measured recall on injected legally material changes is complete.

## 3. Source classes
The architecture must support at minimum:
- legislation and Government Gazette (ΦΕΚ) material, including corrections and republications;
- amendments, repeals, suspensions, revivals, commencement provisions, transitional provisions and codifications;
- judicial decisions and their relation to the exact versions and authority status of provisions applied or interpreted;
- legal doctrine/theory as a distinct epistemic class, never silently promoted to binding law;
- provenance, acquisition and publication metadata required to independently reconstruct every derived assertion;
- later-discovered, duplicate and conflicting source material without destructive overwrite.

## 4. Time model
The observatory must distinguish at least:
- source publication time;
- legal/effective time;
- system transaction/knowledge time;
- correction/retraction/discovery time.

A query such as “what law applied on date X?” and “what did the system know on date Y about date X?” must be able to return different, justified answers.

## 5. Trusted-path rule
No probabilistic model may authoritatively decide canonical identity, legal effect, temporal succession, provenance validity or committed publication state. Models may propose, extract, classify or generate candidates; deterministic and independently checkable mechanisms decide admission to trusted state.

## 6. Historical integrity
No accepted version may be destructively overwritten. Corrections and later discoveries extend the record. Every published current-state representation must be reproducible from preserved evidence plus declared deterministic transformations, including the ability to reconstruct what the system previously knew or published.

## 7. National publication and interoperability objective
One canonical state must be capable of producing mutually consistent projections for:
- human legal use;
- stable APIs and bulk/open-data exchange;
- graph/linked-data representations;
- ELI-compatible identifiers/metadata and other applicable Greek/EU legal-information interchange requirements;
- machine-readable legal feeds suitable for AI retrieval, grounding and verification;
- future public-sector or governmental publication without replacing the canonical authority seat.

The architecture must separate canonical truth from projections. A website, API, ELI/linked-data graph, government-facing endpoint or AI-facing feed may never become an independently writable competing legal truth.

## 8. National-scale success
A winning architecture must demonstrate, under hidden and adversarial replay:
- complete detection of injected legally material source/change events;
- correct canonical identity and deduplication;
- correct temporal reconstruction;
- correct normative effects;
- jurisprudence-to-exact-version linkage;
- doctrine/theory separation;
- complete proof-carrying provenance;
- explicit unknown/conflict handling;
- deterministic replay, crash recovery and rebuild;
- consistent publication projections and bounded publication latency;
- governed evolution without reopening the trusted core for every new source/change type.

The architecture must remain credible at national scale: millions of source objects and long-lived legal history must not require a second canonical system or manual reconstruction of ordinary change semantics.

## 9. Architecture-discovery rule
The experiment searches whole-system architectures. It must not assume event sourcing, a knowledge graph, SQL, Common Lisp everywhere, microservices, a daemon, a particular database or any other implementation family in advance. Existing assets may be reused only when measured evidence shows they belong in the strongest surviving design.

## 10. Reused prior evidence
The previously sealed CP1 repository reconstruction may be reused only when its target commit/tree identity is verified. Earlier CP2 architecture research is prior evidence, not a preselected answer: it remains quarantined until the new Observatory design-space reconstruction has independently produced and challenged its own frontier.

## 11. Completion semantics
A first passing design is never final. It is only a provisional frontier member. Final freeze requires dominance review, radical challengers, simplification challenge, replay evidence, failure injection, independent audit and no surviving evidence-supported higher architecture within the declared resource envelope.

A result that exhausts budget before those conditions close is BEST_DISCOVERED_SO_FAR, never silently promoted to a final national architecture.
