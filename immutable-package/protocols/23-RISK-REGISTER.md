# 23 — RISK REGISTER (v1.0) — πιθανότητα/επίπτωση Χ→Υ (H/M/L), μετριασμός

- R1 Η μετα-διαδικασία τρώει το budget πριν γραφτεί ουσία (H/H): day-1 shortlist στο INDEX·
  όριο 15% budget για φάσεις 0-2· πρώτο capability target = Row 0 του 17, όχι «όλα».
- R2 Overfitting/contamination στα benchmarks (M/H): σφράγιση+hash πριν την ανάπτυξη,
  regeneration μετά από αποτυχία, isomorphism tables, grep κατά CS-01 strings, transfer test.
- R3 Fabricated provenance/αποτελέσματα από builder (M/TERMINAL): trace-grading, ledger
  probes (VD-17), audit spot checks, terminal violation policy.
- R4 Διαρροή hidden set (M/H): sealed εκτός container mounts, access logs, attestation hashes,
  απαγόρευση αναφοράς σε prompts/logs.
- R5 Πρόωρο πάγωμα λάθος substrate (M/H): substrate cert απαιτεί μόνο VD-13..17 πυρήνα·
  αλλαγές ports επιτρεπτές ΜΟΝΟ μέσω ARCHITECTURE_REVIEW με migration+replay απόδειξη.
- R6 Διαρροή PII της πραγματικής υπόθεσης (M/H): καραντίνα A-Box (01 §3), ανωνυμοποίηση
  fixtures, audit item 8. Ανθρώπινος έλεγχος πριν βγει οτιδήποτε από το μηχάνημα.
- R7 Τριβή Common Lisp οικοσυστήματος με τον builder (M/M): η απόφαση runtime ΜΕΤΑ το
  reality model (24)· επιτρεπτό polyglot substrate πίσω από ports· ΟΧΙ δογματική επανεγγραφή.
- R8 Απώλεια μηχανήματος/δίσκου (L/H): backups εκτός EXPERIMENT_ROOT, περιοδικά archives
  των checkpoints+events (χειροκίνητα από owner — βλ. 24).
- R9 Αστάθεια/κόστος API (M/M): idempotent replay, εκθετικό backoff, 10% reserve, alarms.
- R10 «Επιτυχία» με λάθος νόημα (M/H): 5 στρώματα του 17, απαγόρευση ενιαίου σκορ M+L,
  γλωσσικός κανόνας: ουδέποτε «κατανοεί/συνειδητοποιεί» σε reports — μόνο μετρήσιμες ικανότητες.
- R11 Ο runner ως single point of failure (M/M): state machine + resume + independent audit·
  ο runner ΔΕΝ βαθμολογεί — μόνο εκτελεί.
- R12 Νομική/δεοντολογική έκθεση από αυτοματοποίηση κρίσεων (L/H): H1 lockout (01 §2),
  όλα τα legal outputs ως ΠΡΟΤΑΣΕΙΣ προς δικηγόρο με provenance.
