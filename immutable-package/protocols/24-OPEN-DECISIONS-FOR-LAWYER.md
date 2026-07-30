# 24 — ΑΝΟΙΚΤΕΣ ΑΠΟΦΑΣΕΙΣ ΠΟΥ ΑΠΑΙΤΟΥΝ ΤΟΝ ΔΙΚΗΓΟΡΟ-ΙΔΙΟΚΤΗΤΗ (πριν το launch)

1. **Budget αριθμοί** (μπαίνουν στο 14 και κλειδώνουν): συνολικό κόστος API (EUR), συνολικά
   tokens, wall-clock ημέρες, μέγεθος resource window, ποσοστό reserve. Χωρίς αυτά δεν
   υπάρχει ούτε ορισμός στασιμότητας ούτε stop conditions.
2. **Ποιος παράγει και σφραγίζει το hidden set** (09): πρέπει να είναι ανεξάρτητος από τον
   builder (DeepSeek). Ρεαλιστικές επιλογές: (α) Claude παράγει, owner σφραγίζει hash·
   (β) ChatGPT παράγει, owner σφραγίζει· (γ) deterministic generator script + owner. Η
   επιλογή καταγράφεται στο attestation.
3. **Runtime απόφαση μετά το REPOSITORY REALITY MODEL**: διατήρηση Common Lisp πυρήνα και
   ενίσχυση, ή polyglot substrate πίσω από ports; (Η απόφαση ΔΕΝ προλαμβάνεται από το πακέτο.)
4. **Πρόσβαση του συντάκτη του πακέτου στο repository** για v1.1 GROUNDED ANNEX (προαιρετικό
   αλλά συνιστώμενο: θα δέσει CP0–CP6/E1/tournaments με το 06 με πραγματικά στοιχεία).
5. **Πολιτική PII fixtures**: επιβεβαίωση ότι ΟΛΑ τα fixtures βγαίνουν ανωνυμοποιημένα και
   ότι το πραγματικό υλικό της υπόθεσης μένει εκτός πειραματικού μηχανήματος ή σε
   κρυπτογραφημένο χώρο εκτός mounts.
6. **Διαθεσιμότητα gates**: πόσο συχνά απαντάς σε ουρά εγκρίσεων (καθημερινά; ανά 48ωρο;)
   — καθορίζει τον σχεδιασμό blocking/non-blocking εργασίας.
7. **Κατώφλια αποδοχής** (17 pinned parameters): N seeds ablation, noise floor, hidden pass
   thresholds ανά capability, αριθμός clean runs (default 2).
8. **Χώρος backups εκτός μηχανήματος** (R8): πού αντιγράφονται checkpoints/events.
9. **Έγκριση του Row 0 στόχου** ως ελάχιστης επιτυχίας 1ου κύκλου (Charter §4) — ή αλλαγή του.
10. **Άδεια χρήσης CS-01 ανωνυμοποιημένων fixtures** στο visible suite (02 §CS-01).
11. **(v1.3) Κλιμάκωση**: ποσοστό budget δεσμευμένο για challenger rounds (πρόταση: 25-35%)·
    και ποιος στελεχώνει τα ανεξάρτητα critic contexts (ξεχωριστά DeepSeek contexts με
    διαφορετικά role prompts, ή δεύτερο μοντέλο, ή συνδυασμός) — ο builder δεν πιστοποιεί
    ποτέ τον εαυτό του.
