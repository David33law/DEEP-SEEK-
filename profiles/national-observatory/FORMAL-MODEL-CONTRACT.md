# National Legal Observatory — Machine-Checked Model Contract v1

## 1. Purpose

Natural-language formalizations and executable examples are not machine-checked architecture proofs. Every architecture that survives implementation search must therefore provide two independently generated bounded transition models of its authority, identity, temporal/effect, commit, publication and recovery semantics.

The model arena performs exhaustive finite-trace exploration and directed bitemporal/effect scenarios using randomized hidden identifiers. It proves only the declared bounded model. A successful result does not prove an unbounded implementation or external deployment; it establishes that the architecture's claimed invariants are internally coherent and mechanically falsifiable over the tested state space.

## 2. Candidate interface

`formal_candidate.py` must export pure, deterministic functions:

```python
def initial_state() -> dict: ...
def transition(state: dict, action: dict) -> dict: ...
def state_root(state: dict) -> str: ...
def query(state: dict, query: dict) -> dict: ...
def publication(state: dict) -> dict: ...
def model_manifest() -> dict: ...
```

`transition` returns:

```json
{
  "state": {},
  "accepted": false,
  "duplicate": false,
  "pending": false,
  "unresolved": false,
  "reason": "..."
}
```

The input state must not be mutated. All outputs must be JSON serializable. The same state/action pair must produce byte-identical canonical JSON.

## 3. Controlled actions

The evaluator supplies only these action types:

- `ADMIT` — source evidence with `source_id`, `canonical_id`, `knowledge_time`, `effective_time`, `effect`, `text` and `node_group`;
- `PARTITION` — enter a majority/minority partition;
- `HEAL` — restore connectivity;
- `CRASH` — crash the authoritative transition service;
- `RECOVER` — recover it without inventing or silently losing a committed legal state;
- `RULE_UPGRADE` — install a versioned rule pack for future governed transitions.

Allowed `effect` values are `SET`, `AMEND`, `CORRECT`, `REPEAL` and `REVIVE`.

## 4. Required observation semantics

`state_root(state)` identifies committed canonical authority only. Transient process, partition or cache state may not create a second canonical root.

`query(state, q)` receives `canonical_id`, `legal_time` and `knowledge_time` and returns:

- `canonical_id`;
- `status` — `IN_FORCE`, `REPEALED` or `UNKNOWN`;
- `text` or null;
- `legal_time` and `knowledge_time` echoed;
- `evidence_chain` — ordered source IDs used;
- `unresolved` — explicit unresolved reasons.

`publication(state)` returns one `canonical_root` and a map for human, api, linked_data, eli, public_sector and ai. Every channel must equal `state_root(state)`.

## 5. Mandatory invariants

The bounded evaluator checks at least:

1. deterministic transition and query results;
2. input-state immutability;
3. duplicate evidence idempotence;
4. conflicting bytes under one source ID never overwrite committed evidence silently;
5. minority-partition submissions do not become committed canonical state;
6. crash and recovery preserve the last committed root;
7. publication channels never diverge from the canonical root;
8. legal/effective time and knowledge time remain independent;
9. a late-discovered correction affects queries only after its knowledge time and from its legal effective time;
10. repeal and revival reconstruct correctly;
11. rule upgrade cannot retroactively mutate prior query answers without new governed evidence;
12. independent evidence orderings that are declared commutative by the manifest converge;
13. all unresolved conflicts remain observable;
14. every manifest controlled class matches the parent architecture genome.

## 6. Exhaustive finite exploration

The evaluator generates hidden identifiers, texts and dates, then explores all action traces up to a declared depth over a finite alphabet containing admissions, duplicates, conflicts, partitions, majority/minority submissions, crash/recovery and rule upgrades.

Every visited state is canonicalized and deduplicated. The report records trace count, state count, counterexamples and a deterministic behavioral digest. Two independently generated formal models of the same architecture must both pass and produce the same behavioral digest.

## 7. Model manifest

`model_manifest()` must report exactly these controlled classes from the parent genome:

- `canonical_authority_seat`;
- `state_derivation_model`;
- `temporal_model`;
- `normative_effect_model`;
- `consistency_commit_model`;
- `replication_distribution_model`;
- `trusted_core_topology`.

It must also report:

- `commutative_independent_admissions` — boolean;
- `minority_partition_policy` — `reject` or `pending`;
- `proof_boundary` — a precise statement of what the bounded model does and does not prove.

A relabelled generic model is a fidelity failure.

## 8. Revision and independence

Two model implementations are generated under independent role contexts. If one fails, at most one architecture-preserving revision may use the aggregate counterexample classes and traces; hidden generator code is not shown.

Both final models must pass and agree on the behavioral digest. One model cannot certify the other.

## 9. Terminal consequence

`machine_checked_models_passed` and `independent_model_agreement` are explicit supremacy conditions.

A counterexample, model disagreement, uncontrolled class mismatch or unmodelled load-bearing claim blocks `COMMITTED`. Resource exhaustion yields only `BEST_DISCOVERED_SO_FAR`.