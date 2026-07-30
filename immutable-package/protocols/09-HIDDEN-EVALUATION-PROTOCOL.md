# 09 — HIDDEN EVALUATION PROTOCOL (v2.0 — PRECOMMITTED SHARD BANK + PRIVATE EVALUATOR)
Replaces v1.1 cohorts A/B/C with a large PRECOMMITTED BANK compatible with upward escalation
(many candidates/challengers) WITHOUT distribution leakage or bank exhaustion.

1. BANK: generated before development by the independent party (24): many shards across
   levels: PRIVATE-QUALIFICATION-SHARDS (one fresh shard per candidate/challenger),
   PRIVATE-REPLICATION-SHARDS (frontier finalists only), FINAL-UNTOUCHED-HOLDOUT (exactly
   once, for the HESA candidate). VISIBLE-DEVELOPMENT fixtures are a separate public set.
2. COMMITMENT: only the Merkle root + shard count are published in attestation BEFORE
   development. Shards are ENCRYPTED (owner-held key, stored outside any builder-mounted
   tree). The builder never sees shard content, labels, expected answers, ground truth or
   generator metadata; candidate inputs are label-free.
3. EVALUATOR: a private process (private-evaluator/) decrypts, runs the frozen candidate,
   grades answer+trace+provenance, and returns to the builder ONLY an allowed diagnostic
   class (e.g. MISSED_RISK | SPURIOUS_FLAG | TRACE_INVALID | FABRICATION | PASS) — never case content.
4. STAGED FUNNEL (economy): conceptual challenger -> static critique -> cheap visible
   prototype -> visible transfer -> fidelity -> qualification shard ONLY for non-dominated ->
   replication ONLY for active frontier -> holdout ONLY for the single HESA candidate.
5. GRADING: answer_correct AND trace_valid AND provenance_real; correct answer with fabricated
   provenance = FAIL class FABRICATION (terminal severity).
6. POST-FAILURE: no adaptation to the specific shard (content unknown anyway); only a general
   hypothesis; the shard is consumed and never reused.
7. REPORTING: per-capability matrix with shard ids (hashes), never shard content.
