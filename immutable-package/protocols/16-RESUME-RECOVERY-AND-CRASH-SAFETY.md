# 16 — RESUME, RECOVERY AND CRASH SAFETY (v1.0)

- **Atomic writes**: tmp file + flush/fsync + rename, same volume; never partial JSON/MD.
- **Checkpoints**: {state-machine state, event seq, view hashes, open tickets, budget
  snapshot}; written on every state transition and every K events (K pinned in 20).
- **Resume**: read last valid checkpoint; verify chain-head; replay events > seq; re-enter
  state handler idempotently. Paid successful calls are replayed from raw-api store, never re-called.
- **Crash classes & behavior**: process kill (resume normal); disk-full (halt with evidence,
  no truncation of chain); API failure (retry with backoff under budget; store every attempt);
  container failure (rebuild from pinned image digest); corruption detected (restore last
  checkpoint whose hashes verify; quarantine corrupt segment — preserved, not deleted).
- **Evidence preservation on every failure**: freeze the failing run dir read-only
  (runs/<ts>.FAILED/), including stdout/stderr files, before any recovery action.
- **Backups**: automatic pre-patch backup of any file about to be modified (patch id-linked);
  session log append-only; no history rewrites (no rebase/force ops on experiment root).
