# 22 — INDEPENDENT COMPLETION AUDIT SPEC (v1.0)
Auditor: NOT the builder model — deterministic audit scripts + (optionally) a different
model or the owner. Runs read-only. Output: audit report + pass/fail per item.

Checklist:
1. State log: every transition has guard evidence + required artifacts; no undeclared edges.
2. Hash chain verifies end-to-end; attestation matches (HEAD, pack hash, image digests).
3. Hidden integrity: sealed manifest hash unchanged since commitment; no access before
   CANDIDATE_FROZEN (mtimes/access logs); regenerations properly re-committed.
4. Budget ledger: sums match raw-api evidence; no re-paid successful calls; no MAX_ATTEMPTS
   patterns in code/prompts (grep proof).
5. Threshold integrity: 17 hashes unchanged; test expectations unmodified post-freeze
   (git history proof).
6. Fidelity/ablation artifacts complete and internally consistent (deltas recomputable).
7. Trace-grading spot checks: sampled hidden answers re-verified for provenance reality —
   any fabrication = terminal flag.
8. A-Box quarantine: grep for CS-01 identifiers in core/fixtures-generators = zero hits.
9. Certification commit: exists, separate from builder identity, references audit report hash.
10. (v1.3) Escalation compliance: every frozen candidate has dominance dossier (42) +
    anti-satisficing report (43) with zero unresolved findings; altitude declarations (41)
    match audited evidence; frontier memory (46) internally consistent; builder-certifier
    separation proven (role/context logs); forbidden status language ("final/supreme/ανώτατο")
    absent; budget-exhaustion outputs labeled BEST_DISCOVERED_SO_FAR.
Verdict classes: CLEAN | CLEAN-WITH-FINDINGS | PROTOCOL-VIOLATION | TERMINAL-VIOLATION.
