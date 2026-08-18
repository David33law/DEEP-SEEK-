# NATIONAL LEGAL OBSERVATORY — DURABLE SYSTEMS CONTRACT v2

## 1. Purpose

The semantic-kernel arena proves legal semantics in an isolated in-memory candidate. It cannot
establish that a national architecture is durable, recoverable or operationally usable. Every
surviving architecture therefore needs a second implementation artifact, `systems_candidate.py`,
evaluated independently under real writable persistence inside a network-disabled container.

The durable reference and evaluator are themselves calibrated during the owner ceremony before a
production launch is permitted. The qualification, replication, crown and forced-crash workloads are
part of the owner-signed Observatory workload policy. An evaluator default may not silently replace
the signed workload.

This arena does not replace the semantic evaluator. Both must pass for an evidence-supported
supremacy claim.

## 2. Required entry point

`systems_candidate.py` must define:

```python
open_system(state_dir: str) -> object
```

`state_dir` is the only persistent writable directory. The returned object must implement:

- `ingest_batch(events)` — durably admit a batch of JSON-compatible evidence/change records;
  duplicate delivery must not create duplicate canonical records;
- `state_root()` — return a deterministic non-empty string committing to the durable canonical state
  represented by the admitted history;
- `integrity_check()` — return a dict containing at least `{"ok": bool}` and may include diagnostics;
  it must not report OK when its own authoritative durable state is detectably corrupted;
- `recover()` — attempt recovery using the architecture's declared durable recovery mechanism and
  return a dict containing at least `{"ok": bool}`;
- `publish_probe()` — return `canonical_root` equal to `state_root()` and `channels` containing
  `human`, `api`, `linked_data`, `eli`, `public_sector`, `ai`;
- `durability_manifest()` — return non-empty relative `authority_files`, optional relative
  `recovery_files`, a textual `consistency_model`, and boolean `transaction_order_semantic`;
- `close()` — flush/close all owned durable state.

Implementations may expose additional methods. They may use Python's standard library, including
SQLite. No network or model call exists in this arena.

## 3. Authority and recovery files

`authority_files` identify the persistent bytes whose corruption could invalidate canonical
authority. They must be relative paths beneath `state_dir`; hiding authoritative state from the
evaluator is a contract violation. `recovery_files` identify independent persistent material used to
reconstruct or restore authority.

A manifest path must not be absolute, contain `..`, escape `state_dir`, alias another declared
load-bearing file, or refer to a missing file at the time the trusted evaluator inspects it. A
candidate may not rely on undeclared host state, credentials, services or writable paths to preserve
canonical authority.

## 4. Durable invariants

1. **Restart identity.** Clean close/reopen of the same state directory returns the same canonical
   root.
2. **Duplicate idempotence.** Re-admitting an identical batch cannot create a second canonical object
   or alter the canonical root merely because transport delivered a duplicate.
3. **Crash readability.** Forced process termination during a large admission may leave either the
   previous durable prefix or a later fully committed prefix, but restart may not silently serve
   structurally corrupted state as valid.
4. **Corruption observability.** If fault injection mutates bytes in a declared persistent authority
   file, integrity verification must not silently return OK. Recovery may restore from independently
   preserved durable material; otherwise the system must fail closed and require deterministic
   rebuild.
5. **Deterministic rebuild semantics.** Equivalent admitted durable event sets on fresh state
   directories must produce the same canonical root when the architecture claims order-independent
   canonicalization. If transaction order is semantically load-bearing, that fact must be explicit.
6. **Concurrent-access integrity.** Concurrent attempts against the same state directory may
   serialize, accept, or explicitly reject/retry according to the consistency model; they may not
   corrupt canonical state or produce two independently authoritative roots.
7. **Large-history operation.** The implementation must process the owner-signed deterministic
   history without manual correction and expose measured throughput/latency rather than an untested
   scale claim.
8. **Projection identity.** Publication probes after restart/rebuild must bind every required channel
   to the current canonical root. A projection may never become an independently writable truth seat.
9. **No hidden external dependency.** Trusted durable semantics may not depend on network services,
   credentials, host state outside `state_dir`, or probabilistic model calls.
10. **Fail closed.** Unsupported recovery, unknown on-disk format, corruption, incompatible upgrade,
    ambiguous process-death evidence or a surviving writer is observable failure, never a PASS.

## 5. Authoritative whole-process crash evidence

A whole-process crash counts only when the trusted evaluator:

1. creates the candidate as a uniquely named ephemeral container;
2. proves that the candidate container reached running state;
3. delivers the forced-crash workload to that running container;
4. invokes the container runtime's kill operation against that exact container;
5. obtains a successful runtime-kill result; and
6. confirms that the candidate container is absent before the durable state directory is reopened.

Killing, disconnecting or timing out only the local Docker/Podman CLI client is **not** process-crash
evidence. The CLI may exit while the actual container remains alive and continues writing to the bind
mount. Starting recovery while such an orphan is alive would create two writers over one state
directory and invalidates the trial.

The evaluator must persist a crash receipt containing at least:

- `actual_container_kill_required=true`;
- `container_started=true`;
- `workload_delivered=true`;
- `runtime_kill_returncode=0`;
- `runtime_kill_succeeded=true`;
- `container_absent_before_recovery=true`;
- `cli_process_kill_counts_as_evidence=false`.

A missing field, failed runtime kill, ambiguous container state, surviving container or concurrent
mutation before recovery makes the crash test FAIL. Cleanup of a local CLI process after the runtime
kill is permitted but cannot earn evidence.

## 6. Calibration and signed workloads

Before the owner ceremony is complete, the exact bounded `observatory_systems_arena_v2.py` used by
production must pass the exact reference `observatory_systems_reference_candidate.py`. The
hash-bound specialized calibration receipt and preflight source census must contain both files and the
calibration report.

The owner-signed protocol specifies:

- qualification event count;
- independent replication event count;
- crown event count; and
- forced-crash event count.

Production routing must pass the signed forced-crash count explicitly to the evaluator. Proof mode
may use a reduced signed qualification/replication/crown workload but may not weaken the crash
semantics or substitute a CLI-only termination.

## 7. Isolation

The evaluator executes candidates in network-disabled containers with a read-only root filesystem,
one explicit writable state directory, bounded memory and process count, no inherited secrets and no
model calls. Crash trials use a unique container identity and confirm its disappearance before reuse
of the writable state directory.

## 8. Proof boundary

A single-machine container campaign cannot prove real national traffic volume, Byzantine
multi-datacenter behavior, every filesystem/controller/hardware fault, government adoption or every
operational incident. Those remain explicit deployment/external claims. The arena proves only the
signed, executed fault and durability model and prevents an in-memory or CLI-kill simulation from
being mislabeled as durable evidence.

## 9. Supremacy consequence

If the surviving architecture cannot produce a systems candidate that passes qualification,
independent replication and crown under the exact signed protocol, `systems_arena_passed` cannot be
true and `COMMITTED` is structurally unreachable. The valid terminal label remains
`BEST_DISCOVERED_SO_FAR` until the durable claim is closed.
