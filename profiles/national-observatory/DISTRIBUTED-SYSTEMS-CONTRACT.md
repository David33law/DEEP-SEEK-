# National Legal Observatory — Distributed Systems Contract v2

## 1. Purpose

The durable single-state-directory arena proves local persistence, crash handling, corruption recovery and deterministic rebuild. It cannot prove a candidate's claims about replication, federation, sharding, quorum commit, consensus, partition behavior or split-view resistance.

Every architecture must therefore provide a separate `distributed_candidate.py` implementing its declared controlled replication and commit model under an executable deterministic cluster contract.

This is a bounded fault campaign, not a claim that a local simulation proves an internet-scale deployment. Any load-bearing distributed claim outside the contract remains explicitly unproved and blocks supremacy unless supported by a machine-checkable model or additional evidence.

## 2. Candidate interface

`distributed_candidate.py` must export:

```python
def open_cluster(root_dir: str, node_ids: list[str]): ...
```

The returned object must implement:

- `submit(node_id, event) -> dict`
- `ingest_batch(node_id, events) -> dict`
- `partition(groups) -> dict`
- `heal() -> dict`
- `roots() -> dict[str, str]`
- `integrity() -> dict`
- `crash(node_id) -> dict`
- `restart(node_id) -> dict`
- `recover(node_id) -> dict`
- `publication_roots() -> dict`
- `cluster_manifest() -> dict`
- `close() -> dict`

The implementation may serialize operations or reject writes that cannot be committed safely. It may not acknowledge mutually incompatible canonical histories as committed.

`ingest_batch` may implement a single durable batch transition. If it does, per-event admission semantics must remain deterministic, and a process death during serialization must leave either the previous durable canonical authority or the fully committed batch. A partially serialized canonical authority is never acceptable.

## 3. Manifest

`cluster_manifest()` must return:

- `replication_model` — one controlled `replication_distribution_model` class;
- `commit_model` — one controlled `consistency_commit_model` class;
- `node_authority_files` — relative durable authority files per node;
- `cluster_authority_files` — relative durable files that carry canonical cluster authority;
- `fault_assumptions` — explicit quorum/synchrony/failure assumptions;
- `canonical_root_rule` — how the one canonical root is determined;
- `publication_channels` — human, api, linked_data, eli, public_sector and ai.

The reported controlled classes must match the architecture genome supplied to the builder. A label mismatch or generic substitution is a fidelity failure.

## 4. Required behavior

The evaluator will test at least:

1. **healthy convergence** — accepted events converge to one root across five nodes;
2. **duplicate and reordered delivery** — retries do not create a second truth;
3. **majority/minority partition** — the minority cannot create a conflicting committed canonical history;
4. **heal and catch-up** — nodes converge after partitions and missed delivery;
5. **node crash/restart** — durable accepted state survives process and node restarts;
6. **whole-process crash** — reopening the cluster preserves or fail-closes the last durable commit;
7. **node corruption** — corruption is detected and recovered or the node is excluded without corrupting canonical publication;
8. **independent rebuild** — a fresh cluster fed the accepted canonical event set produces the same root;
9. **publication consistency** — every required channel reports the same committed root;
10. **fault assumption honesty** — writes outside the declared safe regime are rejected or remain explicitly pending, never silently committed.

### Whole-process crash evidence

A whole-process crash counts only when the trusted evaluator kills the **actual named candidate container** through the container runtime and confirms that the container no longer exists before recovery starts. Killing or disconnecting only the local Docker/Podman CLI client is not crash evidence, because it can leave an orphaned container writing concurrently to the same authority files.

Recovery must therefore begin only after the crashed candidate container is confirmed absent. A surviving writer, ambiguous container state, failed runtime kill, or concurrent mutation of the recovery bind mount is a failed/invalid crash trial, never a PASS.

## 5. Isolation

The evaluator runs inside network-disabled containers with a read-only root filesystem, one explicit writable cluster directory, bounded memory and process count, no inherited secrets and no model calls.

Crash trials use a unique ephemeral container identity, explicit runtime kill, and absence verification before reuse of the writable cluster directory.

## 6. Revision and replication

Qualification may trigger up to two architecture-preserving distributed implementation revisions based on aggregate fault reports. Independent replication and final crown campaigns permit no revision.

A candidate that cannot implement its declared distributed model does not enter the frontier. Replacing it with a generic single-primary store is not a repair.

## 7. Terminal consequence

`distributed_failure_model_proven` and `distributed_crown_passed` are explicit supremacy conditions.

A local bounded campaign supports only the exact tested fault model. Stronger geographical, Byzantine, operational or performance claims remain limitations or require additional proof. Resource exhaustion cannot convert an untested distributed claim into `COMMITTED`.
