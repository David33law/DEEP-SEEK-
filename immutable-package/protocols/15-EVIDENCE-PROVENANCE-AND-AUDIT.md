# 15 — EVIDENCE, PROVENANCE AND AUDIT (v1.0)

- **Event log**: append-only JSONL; each event {seq, t, actor(model/tool/human), mechanism,
  inputs_hash, outputs_hash, prior_ref, reason, budget_delta}; hash-chained (prev_hash field);
  daily chain-head anchored into audit/attestation.json.
- **Raw API evidence**: every model call -> {request_id (unique per logical request), full
  request, full raw response} written IMMEDIATELY to runs/<ts>/raw-api/ before any parsing.
  Idempotent replay: a successful paid call is NEVER re-issued; resume reads the stored response.
- **Decision provenance**: every gate decision {question, options, context refs, decision,
  decider, t} as events; strategic consequences link back to decisions.
- **Artifact hashing**: every produced file hashed; reports reference hashes, not paths only.
- **Reasoning-ledger integrity checks** (run in VD-17 and pre-audit): dangling span refs,
  orphan facts, cycles, mechanism-stamp gaps, fabricated-provenance probes.
- **Audit queries that MUST be answerable**: who introduced fact F and on what basis; which
  facts support draft sentence S; what changed between checkpoints A and B and why; what did
  candidate X cost; which capabilities improved in window W; were hidden files touched (mtime
  + hash + access log)?
