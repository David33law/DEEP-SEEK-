# National Legal Observatory — National-Scale Systems Contract v1

## 1. Purpose

Correct semantics and fault survival do not establish that an architecture can maintain the Greek legal order over decades, millions of source objects, repeated consolidations and multiple publication projections.

Every architecture that survives semantic, durable and distributed qualification must provide a separate `scale_candidate.py` implementing its declared controlled scaling/partition model. The scale arena measures deterministic large-history ingestion, restart, rebuild, duplication, partition balance, publication consistency, incremental latency and durable storage cost.

A bounded local campaign does not prove a specific national deployment capacity. It proves that the architecture's scaling mechanism is executable, deterministic and measurable under the declared workload. Stronger throughput, geographic or operational claims remain falsifiable limitations.

## 2. Candidate interface

`scale_candidate.py` must export:

```python
def open_scale(root_dir: str, partition_count: int): ...
```

The returned object must implement:

- `ingest_batch(events) -> dict`
- `state_root() -> str`
- `partition_roots() -> dict[str, str]`
- `integrity_check() -> dict`
- `publish_probe() -> dict`
- `checkpoint() -> dict`
- `recover() -> dict`
- `scale_manifest() -> dict`
- `close() -> dict`

Only Python standard-library code is available in the executable arena. No network or model call exists.

## 3. Scale manifest

`scale_manifest()` must return:

- `scaling_partition_model` — exactly the controlled genome class supplied by the parent;
- `partition_count` — the actual number of active partitions;
- `routing_rule` — deterministic routing/partitioning description;
- `authority_files` — relative durable authority files;
- `checkpoint_files` — relative checkpoint/recovery files;
- `publication_channels` — human, api, linked_data, eli, public_sector and ai;
- `complexity_claim` — explicit expected time/space behavior and assumptions.

A generic implementation with a relabelled scaling class is a blueprint-fidelity failure.

## 4. Workload

The evaluator generates deterministic legislation, amendment, correction, suspension, revival and repeal events with realistic repeated legal-object targets and both legal/effective and knowledge time.

Qualification, independent replication and crown campaigns use successively larger fresh workloads and independent seeds. Production defaults are intentionally high and are owner-signed. The zero-cost control proof may use a smaller explicit calibration count but must traverse the same code path.

## 5. Required trials

The arena tests:

1. **large deterministic ingest** — all unique source events are admitted or explicitly unresolved;
2. **restart identity** — process restart preserves the exact canonical root;
3. **duplicate/reordered idempotence** — repeated input does not create a second truth;
4. **incremental tail** — a fresh tail changes the root and remains query/publication consistent;
5. **independent rebuild** — a fresh scale store fed the same canonical event sequence reaches the same root;
6. **checkpoint/recovery** — corruption or deletion of a declared authority file is detected and restored from an independently declared checkpoint, or the store fails closed;
7. **partition roots** — each partition exposes a stable root and the canonical root is deterministically derived from them;
8. **partition balance** — partitioned models must distribute the fixed workload rather than route all authority into a hidden single partition; `single_node_scale_up` is exempt but must state that assumption;
9. **publication consistency** — every required channel exposes the same canonical root;
10. **storage observability** — total durable bytes, bytes/event, batch latency and aggregate throughput are reported.

## 6. Hard and Pareto conditions

The following are hard gates:

- deterministic root equality across restart and independent rebuild;
- no duplicate-created state;
- clean integrity/recovery;
- exact scaling-model identity;
- consistent publication root;
- no silent dropped unique event.

Throughput, p95 batch latency, durable bytes/event and partition balance are Pareto dimensions rather than universal hardware-independent thresholds. A slower architecture may survive only if it offers a non-dominated stronger property.

## 7. Revision and replication

Qualification may drive at most two architecture-preserving scale implementation revisions using aggregate diagnostics. Independent replication and final crown campaigns permit no revision.

A candidate that cannot implement its own scaling model does not enter the frontier. Replacing the declared model with a generic monolithic file is not a valid revision.

## 8. Terminal consequence

`national_scale_qualification_passed`, `national_scale_replication_passed` and `national_scale_crown_passed` are explicit supremacy conditions.

A resource stop before the signed workload completes yields `BEST_DISCOVERED_SO_FAR`, not `COMMITTED`. A passing bounded campaign must disclose its exact event count, partition count, hardware-independent proof boundary and measured performance.