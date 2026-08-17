# NATIONAL LEGAL OBSERVATORY — DURABLE SYSTEMS CONTRACT v1

## Purpose

The semantic-kernel arena proves legal semantics in an isolated in-memory candidate. It cannot establish that a national architecture is durable, recoverable or operationally scalable. A finalist therefore needs a second implementation artifact, `systems_candidate.py`, evaluated independently under real writable persistence inside a network-disabled container.

This arena does not replace the semantic evaluator. Both must pass for an evidence-supported supremacy claim.

## Required entry point

`systems_candidate.py` must define:

```python
open_system(state_dir: str) -> object
```

`state_dir` is the only persistent writable directory. The returned object must implement:

- `ingest_batch(events)` — durably admit a batch of JSON-compatible evidence/change records; duplicate delivery must not create duplicate canonical records;
- `state_root()` — return a deterministic non-empty string committing to the durable canonical state represented by the admitted batch history;
- `integrity_check()` — return a dict containing at least `{"ok": bool}` and may include diagnostics; it must not report OK when its own durable authoritative state is detectably corrupted;
- `recover()` — attempt recovery using the architecture's declared durable recovery mechanism and return a dict containing at least `{"ok": bool}`;
- `publish_probe()` — return a dict containing `canonical_root` equal to `state_root()` and `channels` containing `human`, `api`, `linked_data`, `eli`, `public_sector`, `ai`;
- `durability_manifest()` — return an object containing non-empty relative `authority_files`, optional `recovery_files`, a textual `consistency_model`, and boolean `transaction_order_semantic`; this declaration is evaluator input for fault injection, not proof by assertion;
- `close()` — flush/close all owned durable state.

Implementations may expose additional methods. They may use Python's standard library, including SQLite. No network or model call exists in the arena.

`authority_files` must identify the persistent bytes whose corruption could invalidate canonical authority. They must be relative paths beneath `state_dir`; hiding authoritative state from the evaluator is a contract violation. `recovery_files` identify independent persistent material used to reconstruct or restore authority.

## Durable invariants

1. **Restart identity.** Clean close/reopen of the same state directory returns the same canonical root.
2. **Duplicate idempotence.** Re-admitting an identical batch cannot create a second canonical object or alter the canonical root merely because transport delivered a duplicate.
3. **Crash readability.** Forced process termination during a large admission may leave either the previous durable prefix or a later fully committed prefix, but restart may not silently serve structurally corrupted state as valid.
4. **Corruption observability.** If evaluator fault injection mutates bytes in the candidate's declared persistent authority files, integrity verification must not silently return OK. Recovery may restore from independently preserved durable material; otherwise the system must fail closed and require deterministic rebuild.
5. **Deterministic rebuild semantics.** Equivalent admitted durable event sets on fresh state directories must produce the same canonical root when the architecture claims order-independent canonicalization. If the architecture makes transaction order semantically load-bearing, that fact must be explicit in its formalization and the evaluator records the claim rather than assuming commutativity.
6. **Concurrent-access integrity.** Concurrent attempts against the same state directory may serialize, accept, or explicitly reject/retry according to the architecture's consistency model; they may not corrupt the canonical state or produce two independently authoritative roots.
7. **Large-history operation.** The implementation must process a large deterministic synthetic history without manual correction and expose measured throughput/latency rather than an untested scale claim.
8. **Projection identity.** Publication probes after restart/rebuild must bind all declared channels to the current canonical root. A projection may never become an independently writable truth seat.
9. **No hidden external dependency.** The candidate may not require network services, credentials, host state outside `state_dir`, or probabilistic model calls to preserve trusted durable semantics.
10. **Fail closed.** Unsupported recovery, unknown on-disk format, corruption, or incompatible upgrade must be observable; silently constructing a new empty truth is a failure.

## What this arena does not prove by itself

A single-machine container cannot prove real national traffic volume, Byzantine multi-datacenter behavior, governmental governance adoption, or every filesystem/hardware failure. Those remain explicit external/deployment claims. The arena exists to prevent an in-memory prototype from being mislabeled as a proven production architecture and to mechanically exercise the durable claims that are constructible locally.

## Supremacy consequence

If the surviving architecture cannot produce a systems candidate that passes this arena, `systems_arena_passed` is false and `COMMITTED` is structurally unreachable. The valid terminal label is `BEST_DISCOVERED_SO_FAR` until the durable claim is closed.
