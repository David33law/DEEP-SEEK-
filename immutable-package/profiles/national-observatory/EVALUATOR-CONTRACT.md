# NATIONAL LEGAL OBSERVATORY — EXECUTABLE EVALUATOR CONTRACT v1

A whole-system candidate is still delivered as `candidate.py`, but it is not a document-risk detector. The evaluator runs it in the existing isolated candidate process and requires a stateful `observatory_session` interface.

## Required callable operations
The module must define all of the following callables:

- `ingest(source)`
- `apply_change(event)`
- `state_at(query)`
- `link_jurisprudence(decision)`
- `attach_doctrine(document)`
- `provenance(query)`
- `replay(events)`
- `publish(query)`

State may live only in process memory during one evaluator session. The candidate receives no filesystem, network, hidden bank path, expected answer or API key.

## Canonical input vocabulary
A source/event object uses typed JSON fields. The hidden generator varies ids, dates, texts and arrival order, but preserves these semantics:

- `source_id`: immutable evidence identity supplied by the fixture;
- `kind`: one of `LEGISLATION`, `AMENDMENT`, `CORRECTION`, `SUSPENSION`, `REVIVAL`, `REPEAL`, `JUDGMENT`, `DOCTRINE`, `CONFLICTING_SOURCE`;
- `canonical_id`: legal object/provision identity asserted by the fixture;
- `publication_time` and `knowledge_time`;
- `effective_from`, optional `effective_to`;
- `text` when the event establishes or replaces provision text;
- `target_id` for change events;
- explicit relation fields for judgments and doctrine.

## Required output shapes
### ingest
`{"accepted": bool, "canonical_id": str, "evidence_id": str, "deduplicated": bool, "unresolved": [str,...]}`

### apply_change
`{"accepted": bool, "target_id": str, "change_type": str, "unresolved": [str,...]}`

### state_at
`{"canonical_id": str, "status": "ACTIVE|SUSPENDED|REPEALED|UNKNOWN|CONFLICT", "text": str|null, "legal_time": str, "knowledge_time": str, "evidence_chain": [str,...], "unresolved": [str,...]}`

### link_jurisprudence
`{"decision_id": str, "links": [{"canonical_id": str, "version_evidence_id": str}], "unresolved": [str,...]}`

### attach_doctrine
`{"doctrine_id": str, "epistemic_type": "DOCTRINE", "changes_binding_state": false, "links": [str,...]}`

### provenance
`{"canonical_id": str, "evidence_chain": [str,...], "complete": bool}`

### replay
`{"state_root": str, "objects": int, "unresolved": [str,...]}`. The root algorithm is candidate-defined, but two clean replays of identical events must be byte-identical and semantically equivalent event sets must reconstruct the same canonical legal state.

### publish
`{"canonical_id": str, "status": str, "text": str|null, "evidence_chain": [str,...], "projection": object}`. The projection may vary; canonical state fields may not.

## Hard semantic requirements
1. Effective time and knowledge time are both honored.
2. A correction learned later can change the reconstructed legal state for an earlier legal time without falsifying what the system knew before the correction arrived.
3. Duplicate evidence does not create a second canonical object.
4. Equal-authority conflicting evidence produces `CONFLICT`/unresolved state rather than guessed certainty.
5. Suspension, revival and repeal are explicit legal statuses.
6. A judgment links to the version knowable/applicable at the decision's declared legal/knowledge cut.
7. Doctrine never changes binding state.
8. Provenance contains every source needed for the returned canonical state.
9. Replay is deterministic.
10. Candidate code executes with external network/model access unavailable; therefore any architecture requiring a model on the trusted effect path fails structurally.

## Scoring rule
The hidden evaluator produces the Observatory Pareto vector. Hard-minimum failure rejects the candidate before dominance comparison. No prose claim can substitute for an executable result.
