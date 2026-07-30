# 10 — TRANSFER CASE GENERATION SPEC (v1.0)
Goal: same ABSTRACT capabilities as CS-01, different surface. Each generated case ships a
sealed ground-truth manifest {planted defects, expected findings, expected traces, scoring}.

## Categories (>=4, per request)
- **TC-A Εταιρική διαφορά**: θάνατος εταίρου -> ενεργοποίηση κανόνα, προθεσμία (π.χ.
  τετράμηνο), διακλαδώσεις αναλόγως ενεργειών εταιρείας/κληρονόμων, εξαιρέσεις, αξιώσεις.
  Tests: rule.execute, deadline.monitor, subsume.trace, epistemic.classify (missing corporate acts).
- **TC-B Ποινική υπεράσπιση**: αντιφατικές καταθέσεις, αλυσίδα κατοχής πειστηρίων, παγίδα
  ομολογίας μέσα σε δικό μας υπόμνημα. Tests: contradiction.detect, timeline.reconstruct,
  admission.detect, omission.plan (τι ΔΕΝ προβάλλεται προδικαστικά).
- **TC-C Διαχρονικό δίκαιο**: πράξη/ζημία στο μεταίχμιο παλαιού/νέου καθεστώτος, μεταβατικές
  διατάξεις, ευμενέστερη ρύθμιση. Tests: rule versions/validity intervals, supersedence.resolve,
  subsume.trace με χρονική επιλογή κανόνα (isomorphic στο ΚΟΚ-παλαιό/νέο μοτίβο του CS-01).
- **TC-D Αντικρουόμενα αποδεικτικά**: δύο επίσημα έγγραφα σε ευθεία σύγκρουση ΧΩΡΙΣ σαφές
  supersedence. Σωστή έξοδος: conflict object + escalation + conditional paths — ΟΧΙ αυθαίρετη
  επίλυση. Tests: contradiction.detect, epistemic.classify, human-gate routing (isomorphic
  στο δίδυμο-μετρήσεων και στο αριστερά/δεξιά μοτίβο του CS-01).

## Isomorphism map (mandatory per case)
Table: CS-01 abstract pattern -> TC surface element (e.g. "corrective doc supersedence" ->
"διορθωτική πράξη ΓΕΜΗ"; "admission trap via opponent-sourced fact" -> "παραδοχή γνώσης σε
εταιρικό εξώδικο"). Purpose: prove capability transfer, not memorization.

## Generation checklist
Fresh names/numbers (validators-consistent, synthetic ΑΦΜ-format with valid check digits but
non-real ranges where possible); zero CS-01 strings (grep-enforced); difficulty knobs
(#conflicts, trace depth, noise docs); PII: none real; generator seed + logs archived sealed.
