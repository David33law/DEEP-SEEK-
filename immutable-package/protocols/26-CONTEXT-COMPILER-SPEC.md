# 26 — DETERMINISTIC CONTEXT COMPILER SPEC (v1.1)
Problem: the repository, logs and case studies exceed any per-call context. Re-sending
everything wastes tokens, loses continuity, repeats analysis.

## Contract
Input: {current state, active slice, selected defect/gap ticket}.
Output: MINIMAL EVIDENCE PACKAGE (MEP), deterministic for identical inputs:
  {state summary, active capability + matrix row (25), exact defect ticket, relevant source
   slice (dependency-sliced files only), applicable contracts/ports, test expected vs actual
   (verbatim), prior accepted changes touching the slice (ids+diff summaries), budget state}.
Properties: content-addressed (MEP hash), logical_request_id = f(ticket, MEP hash);
same logical id => answer served from api_cache, never re-paid. MEP composition logged
(files+hashes included), so any builder claim can be traced to what it actually saw.
Selection rules: dependency slice via import/require graph from the ticket's mechanism;
hard caps per section with overflow -> explicit "TRUNCATED, request narrower ticket" marker
(never silent truncation). Prompts contain NOTHING outside the MEP except the master prompt.
