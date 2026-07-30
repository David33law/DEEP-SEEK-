# 20 — EXPERIMENT FILESYSTEM LAYOUT (v1.0)

```
EXPERIMENT_ROOT/                 # the ONLY writable area outside the repo (clean-tree exemption)
  package/                       # this pack, read-only after launch (hash-pinned)
  state/current.json             # checkpoint (atomic)
  state/events.jsonl             # hash-chained event log (append-only)
  audit/attestation.json         # HEAD, branch, image digests, hidden manifest hash, pack hash
  repo/                          # existing LAWMAX repository (git; no remotes)
  substrate/                     # substrate code (if separated from repo per reality model)
  candidates/<cand-id>/          # one dir per candidate mechanism
  fixtures/visible/              # VD fixtures (anonymized CS-01 + synthetic)
  fixtures/hidden-SEALED/        # sealed hidden set: encrypted/out-of-container; hash in attestation
  runs/<ts>/{raw-api/,logs/,reports/}   # per run; stdout/stderr FILE-backed here
  checkpoints/<seq>/             # named checkpoints (event seq + view hashes)
  budget/ledger.jsonl            # resource accounting
  gates/queue.jsonl gates/decisions.jsonl
  backups/<patch-id>/            # automatic pre-patch backups
```
Rules: atomic writes everywhere; checkpoint every state transition and every K=500 events;
runs/*.FAILED/ frozen read-only; nothing deleted, only quarantined; repo/ history never
rewritten; sealed dir excluded from any builder-readable mount.
