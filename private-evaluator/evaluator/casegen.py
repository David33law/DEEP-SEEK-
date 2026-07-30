"""Capability-sliced legal case generator. OWNER/INDEPENDENT-PARTY SIDE ONLY.

v2.0's benchmark tested one rule and a token blocklist — a candidate could pass it with
two `if` statements. This generator produces cases whose ground truth requires eight
distinct reasoning mechanisms, each needing a join across a different pair of structures:

  ADMISSION_RISK      fact status x document ownership x contradicting certified fact
  CONSTRAINT_BLOCK    draft surface text x reserved token x forum identity
  TEMPORAL_BAR        event date x deadline trigger x window arithmetic
  DEONTIC_CONFLICT    modality x act identity x authority rank
  DEFEASIBLE_OVERRIDE general rule x more specific rule that defeats it
  CROSS_FORUM_LEAK    proposition identity x stance in a *different* linked forum
  PROVENANCE_GAP      cited document x document register x fact sourcing
  AUTHORITY_STALE     authority status x supersession chain

Every slice also emits DISTRACTORS: spans that look exactly like the risk but are safe
(asserted as a claim rather than a fact; token reserved for *this* forum; event inside
the window; prohibition of lower rank; exception that does not defeat; proposition not
reserved elsewhere; support present; authority still in force). A candidate that flags
on surface pattern alone is punished by SPURIOUS_FLAG on the distractors, so "flag
everything" scores worse than "flag nothing".

Domains are disjoint between the visible suite and the hidden bank, so the hidden set
measures transfer to unseen surface vocabulary rather than memorisation.
"""
import datetime
import random

SLICES = ["ADMISSION_RISK", "CONSTRAINT_BLOCK", "TEMPORAL_BAR", "DEONTIC_CONFLICT",
          "DEFEASIBLE_OVERRIDE", "CROSS_FORUM_LEAK", "PROVENANCE_GAP", "AUTHORITY_STALE"]

DOMAINS = {
    "labour": {
        "attr": ["ώρες υπερωριακής απασχόλησης", "ημερομηνία καταγγελίας", "ύψος αποδοχών"],
        "act": ["καταβολή αποζημίωσης απόλυσης", "χορήγηση αδείας άνευ αποδοχών"],
        "forum": ["ΜΟΝ_ΠΡΩΤ_ΕΡΓ", "ΕΠΙΘ_ΕΡΓΑΣΙΑΣ"],
        "doc": ["σύμβαση εργασίας", "μισθοδοτική κατάσταση", "καταγγελία εργαζομένου"],
    },
    "commercial_lease": {
        "attr": ["μηνιαίο μίσθωμα", "ημερομηνία παράδοσης μισθίου", "εμβαδόν"],
        "act": ["μονομερής αναπροσαρμογή μισθώματος", "υπεκμίσθωση χωρίς συναίνεση"],
        "forum": ["ΕΙΡ_ΜΙΣΘ", "ΜΟΝ_ΠΡΩΤ_ΑΣΦ"],
        "doc": ["μισθωτήριο", "πρωτόκολλο παράδοσης", "εξώδικη δήλωση"],
    },
    "administrative": {
        "attr": ["ημερομηνία κοινοποίησης πράξης", "ύψος προστίμου", "αριθμός αδείας"],
        "act": ["ανάκληση διοικητικής άδειας", "επιβολή προσαυξήσεων"],
        "forum": ["ΔΙΟΙΚ_ΠΡΩΤ", "ΕΠΙΤΡ_ΕΝΔΙΚ_ΠΡΟΣΦ"],
        "doc": ["απόφαση αρχής", "αποδεικτικό επίδοσης", "τεχνική έκθεση"],
    },
    "tax": {
        "attr": ["φορολογητέα ύλη", "ημερομηνία υποβολής δήλωσης", "συντελεστής"],
        "act": ["συμψηφισμός απαίτησης", "παράταση προθεσμίας καταβολής"],
        "forum": ["ΔΕΔ", "ΔΙΟΙΚ_ΕΦ"],
        "doc": ["εκκαθαριστικό", "έκθεση ελέγχου", "δήλωση φορολογουμένου"],
    },
    "family": {
        "attr": ["τόπος διαμονής τέκνου", "ύψος διατροφής", "ημερομηνία διάστασης"],
        "act": ["μεταβολή τόπου διαμονής τέκνου", "εκποίηση κοινού ακινήτου"],
        "forum": ["ΜΟΝ_ΠΡΩΤ_ΟΙΚ", "ΑΣΦ_ΜΕΤΡΑ"],
        "doc": ["ιδιωτικό συμφωνητικό", "έκθεση κοινωνικής υπηρεσίας", "ληξιαρχική πράξη"],
    },
    "criminal_procedure": {
        "attr": ["χρόνος τέλεσης", "ταυτότητα κατόχου", "αξία αντικειμένου"],
        "act": ["άρση απορρήτου επικοινωνιών", "κατάσχεση εγγράφων"],
        "forum": ["ΣΥΜΒ_ΠΛΗΜ", "ΑΝΑΚΡΙΤΗΣ"],
        "doc": ["έκθεση κατάσχεσης", "απολογία", "μηνυτήρια αναφορά"],
    },
}

VISIBLE_DOMAINS = ["labour", "commercial_lease", "administrative"]
HIDDEN_DOMAINS = ["tax", "family", "criminal_procedure"]


def _d(rng, base, delta):
    return (base + datetime.timedelta(days=delta)).isoformat()


def make_case(rng: random.Random, cid: str, domain: str):
    D = DOMAINS[domain]
    base = datetime.date(2024, 1, 1) + datetime.timedelta(days=rng.randint(0, 700))
    f_main, f_other = D["forum"][0], D["forum"][1]
    attr_a, attr_b = rng.sample(D["attr"], 2)
    act_x, act_y = D["act"][0], D["act"][1]
    tok = f"ΘΕΜΑ-{rng.randint(1000, 9999)}"
    tok_safe = f"ΘΕΜΑ-{rng.randint(1000, 9999)}"
    v1, v2 = f"{rng.randint(10, 99)}", f"{rng.randint(100, 999)}"

    docs = [
        {"id": f"D{cid}-OPP", "owner": "opponent", "kind": rng.choice(D["doc"]), "date": _d(rng, base, -30)},
        {"id": f"D{cid}-CERT", "owner": "court", "kind": rng.choice(D["doc"]), "date": _d(rng, base, -20)},
        {"id": f"D{cid}-CLI", "owner": "client", "kind": rng.choice(D["doc"]), "date": _d(rng, base, -10)},
    ]
    facts = [
        # contested, sourced only from the opponent, contradicted by a certified fact
        {"id": f"F{cid}-1", "attribute": attr_a, "value": v1, "status": "CONTESTED", "sources": [f"D{cid}-OPP"]},
        {"id": f"F{cid}-2", "attribute": attr_a, "value": v2, "status": "CERTIFIED", "sources": [f"D{cid}-CERT"]},
        # safe counterpart: contested but NOT contradicted, and client-sourced
        {"id": f"F{cid}-3", "attribute": attr_b, "value": v1, "status": "CONTESTED", "sources": [f"D{cid}-CLI"]},
    ]
    authorities = [
        {"id": f"A{cid}-GEN", "rank": 2, "kind": "contract", "status": "IN_FORCE", "scope": "general",
         "norm": {"modality": "OBLIGATION", "act": act_x}, "defeated_by": [], "superseded_by": None},
        {"id": f"A{cid}-HIGH", "rank": 5, "kind": "statute", "status": "IN_FORCE", "scope": "general",
         "norm": {"modality": "PROHIBITION", "act": act_x}, "defeated_by": [], "superseded_by": None},
        {"id": f"A{cid}-LOWPROH", "rank": 1, "kind": "contract", "status": "IN_FORCE", "scope": "general",
         "norm": {"modality": "PROHIBITION", "act": act_y}, "defeated_by": [], "superseded_by": None},
        {"id": f"A{cid}-OBLY", "rank": 3, "kind": "regulation", "status": "IN_FORCE", "scope": "general",
         "norm": {"modality": "OBLIGATION", "act": act_y}, "defeated_by": [], "superseded_by": None},
        {"id": f"A{cid}-DEFEATED", "rank": 2, "kind": "regulation", "status": "IN_FORCE", "scope": "general",
         "norm": {"modality": "PERMISSION", "act": act_y}, "defeated_by": [f"A{cid}-SPECIAL"], "superseded_by": None},
        {"id": f"A{cid}-SPECIAL", "rank": 2, "kind": "regulation", "status": "IN_FORCE", "scope": "specific",
         "norm": {"modality": "PROHIBITION", "act": act_y}, "defeated_by": [], "superseded_by": None},
        {"id": f"A{cid}-STALE", "rank": 4, "kind": "statute", "status": "SUPERSEDED", "scope": "general",
         "norm": {"modality": "PERMISSION", "act": act_x}, "defeated_by": [], "superseded_by": f"A{cid}-NEW"},
        {"id": f"A{cid}-NEW", "rank": 4, "kind": "statute", "status": "IN_FORCE", "scope": "general",
         "norm": {"modality": "PERMISSION", "act": act_x}, "defeated_by": [], "superseded_by": None},
    ]
    deadlines = [
        {"id": f"T{cid}-1", "forum": f_main, "trigger_event": f"E{cid}-TRIG",
         "trigger_date": _d(rng, base, 0), "window_days": 60},
    ]
    events = [
        {"id": f"E{cid}-TRIG", "date": _d(rng, base, 0), "kind": "αφετηρία προθεσμίας"},
        {"id": f"E{cid}-LATE", "date": _d(rng, base, 61 + rng.randint(1, 200)), "kind": "επίδικη πράξη"},
        {"id": f"E{cid}-INTIME", "date": _d(rng, base, rng.randint(1, 55)), "kind": "επίδικη πράξη"},
    ]
    constraints = [
        {"id": f"C{cid}-1", "reserved_tokens": [tok], "reserved_for_forum": f_other},
        {"id": f"C{cid}-2", "reserved_tokens": [tok_safe], "reserved_for_forum": f_main},
    ]
    positions = [
        {"id": f"P{cid}-RES", "forum": f_other, "proposition": "ευθύνη εκ της κύριας συμβάσεως", "stance": "RESERVED"},
        {"id": f"P{cid}-OPEN", "forum": f_other, "proposition": "ύπαρξη εγγράφου τύπου", "stance": "ASSERTED"},
    ]

    case = {"case_id": cid, "domain": domain, "forum": f_main, "linked_fora": [f_main, f_other],
            "documents": docs, "facts": facts, "authorities": authorities, "deadlines": deadlines,
            "events": events, "constraints": constraints, "positions": positions}

    S = []

    def span(sid, text, **kw):
        s = {"id": sid, "text": text, "assertion_mode": kw.pop("mode", "argument"),
             "asserts_fact": kw.pop("fact", None), "support": kw.pop("support", []),
             "relies_on_authority": kw.pop("auth", None), "relies_on_event": kw.pop("event", None),
             "proposition": kw.pop("prop", None)}
        assert not kw, kw
        S.append(s)
        return sid

    span("S00", "Επί του παραδεκτού και της νομιμοποιήσεως.")
    # 1 ADMISSION_RISK (+ distractor S02)
    span("S01", f"Βεβαιώνεται ότι {attr_a} ανέρχεται σε {v1}.", mode="fact",
         fact=f"F{cid}-1", support=[f"D{cid}-OPP"])
    span("S02", f"Ισχυρίζεται ο αντίδικος ότι {attr_a} ανέρχεται σε {v1}, όπερ αρνούμεθα.",
         mode="claim", fact=f"F{cid}-1", support=[f"D{cid}-OPP"])
    # 2 CONSTRAINT_BLOCK (+ distractor S04)
    span("S03", f"Ως προς το {tok} επιφυλασσόμεθα παντός δικαιώματος.", mode="reservation")
    span("S04", f"Ως προς το {tok_safe} αναπτύσσουμε κατωτέρω.", mode="reservation")
    # 3 TEMPORAL_BAR (+ distractor S06)
    span("S05", "Η επίδικη πράξη ελήφθη εμπροθέσμως.", mode="argument", event=f"E{cid}-LATE")
    span("S06", "Ομοίως εμπροθέσμως ελήφθη και η προγενέστερη πράξη.", mode="argument", event=f"E{cid}-INTIME")
    # 4 DEONTIC_CONFLICT (+ distractor S08)
    span("S07", f"Αναλαμβάνουμε την υποχρέωση για {act_x}.", mode="argument", auth=f"A{cid}-GEN")
    span("S08", f"Αναλαμβάνουμε την υποχρέωση για {act_y}.", mode="argument", auth=f"A{cid}-OBLY")
    # 5 DEFEASIBLE_OVERRIDE (+ distractor: S08 already safe; add explicit safe general rule)
    span("S09", f"Κατά τον γενικό κανόνα επιτρέπεται {act_y}.", mode="argument", auth=f"A{cid}-DEFEATED")
    span("S10", f"Κατά τον ειδικό κανόνα απαγορεύεται {act_y}.", mode="argument", auth=f"A{cid}-SPECIAL")
    # 6 CROSS_FORUM_LEAK (+ distractor S12)
    span("S11", "Δεχόμαστε ότι υφίσταται ευθύνη εκ της κύριας συμβάσεως.", mode="fact",
         prop="ευθύνη εκ της κύριας συμβάσεως")
    span("S12", "Δεχόμαστε ότι υφίσταται έγγραφο τύπου.", mode="fact", prop="ύπαρξη εγγράφου τύπου")
    # 7 PROVENANCE_GAP (+ distractor S14)
    span("S13", f"Όπως προκύπτει εκ του εγγράφου, {attr_b} είναι {v1}.", mode="fact",
         fact=f"F{cid}-3", support=[f"D{cid}-GHOST"])
    span("S14", f"Όπως προκύπτει εκ του εγγράφου, {attr_b} είναι {v1}.", mode="fact",
         fact=f"F{cid}-3", support=[f"D{cid}-CLI"])
    # 8 AUTHORITY_STALE (+ distractor S16)
    span("S15", f"Βάσει της ισχύουσας διατάξεως επιτρέπεται {act_x}.", mode="argument", auth=f"A{cid}-STALE")
    span("S16", f"Βάσει της ισχύουσας διατάξεως επιτρέπεται {act_x}.", mode="argument", auth=f"A{cid}-NEW")
    span("S99", "Διά ταύτα αιτούμεθα.")

    rng.shuffle(S)
    draft = {"draft_id": f"DR{cid}", "forum": f_main, "spans": S}
    answers = {"expected_flags": ground_truth(case, draft)}
    return case, draft, answers


# --------------------------------------------------------------------------- ground truth
def ground_truth(case, draft):
    """The reference semantics. Frozen BEFORE the hidden bank is generated (protocol 09)."""
    docs = {d["id"]: d for d in case["documents"]}
    facts = {f["id"]: f for f in case["facts"]}
    auths = {a["id"]: a for a in case["authorities"]}
    events = {e["id"]: e for e in case["events"]}
    forum = draft["forum"]
    out = []

    for s in draft["spans"]:
        sid = s["id"]

        # 7 PROVENANCE_GAP — cited document is not in the register
        if any(d not in docs for d in s.get("support", [])):
            out.append({"type": "PROVENANCE_GAP", "span": sid})
            continue

        # 1 ADMISSION_RISK
        fid = s.get("asserts_fact")
        if s.get("assertion_mode") == "fact" and fid in facts:
            f = facts[fid]
            opp_only = f["sources"] and all(docs[d]["owner"] == "opponent" for d in f["sources"] if d in docs)
            contradicted = any(g["attribute"] == f["attribute"] and g["value"] != f["value"]
                               and g["status"] == "CERTIFIED" for g in case["facts"])
            if f["status"] != "CERTIFIED" and opp_only and contradicted:
                out.append({"type": "ADMISSION_RISK", "span": sid})
                continue

        # 2 CONSTRAINT_BLOCK
        blocked = False
        for c in case["constraints"]:
            if c["reserved_for_forum"] != forum and any(t in s["text"] for t in c["reserved_tokens"]):
                out.append({"type": "CONSTRAINT_BLOCK", "span": sid})
                blocked = True
                break
        if blocked:
            continue

        # 3 TEMPORAL_BAR
        eid = s.get("relies_on_event")
        barred = False
        if eid in events:
            ev = datetime.date.fromisoformat(events[eid]["date"])
            for d in case["deadlines"]:
                if d["forum"] != forum:
                    continue
                trig = datetime.date.fromisoformat(d["trigger_date"])
                if (ev - trig).days > d["window_days"]:
                    out.append({"type": "TEMPORAL_BAR", "span": sid})
                    barred = True
                    break
        if barred:
            continue

        aid = s.get("relies_on_authority")
        if aid in auths:
            a = auths[aid]
            # 8 AUTHORITY_STALE
            if a["status"] == "SUPERSEDED":
                out.append({"type": "AUTHORITY_STALE", "span": sid})
                continue
            # 4 DEONTIC_CONFLICT
            if a["norm"]["modality"] == "OBLIGATION":
                if any(b["norm"]["modality"] == "PROHIBITION" and b["norm"]["act"] == a["norm"]["act"]
                       and b["status"] == "IN_FORCE" and b["rank"] > a["rank"] for b in case["authorities"]):
                    out.append({"type": "DEONTIC_CONFLICT", "span": sid})
                    continue
            # 5 DEFEASIBLE_OVERRIDE
            if a["scope"] == "general" and a["defeated_by"]:
                if any(auths[b]["status"] == "IN_FORCE" and auths[b]["scope"] == "specific"
                       for b in a["defeated_by"] if b in auths):
                    out.append({"type": "DEFEASIBLE_OVERRIDE", "span": sid})
                    continue

        # 6 CROSS_FORUM_LEAK
        prop = s.get("proposition")
        if prop and s.get("assertion_mode") == "fact":
            if any(p["proposition"] == prop and p["forum"] != forum and p["stance"] == "RESERVED"
                   for p in case["positions"]):
                out.append({"type": "CROSS_FORUM_LEAK", "span": sid})
                continue

    return sorted(out, key=lambda f: (f["span"], f["type"]))


def generate(seed, domains, n_per_domain, prefix):
    rng = random.Random(seed)
    out = []
    for domain in domains:
        for i in range(n_per_domain):
            cid = f"{prefix}{domain[:3].upper()}{i:03d}"
            out.append((domain,) + make_case(rng, cid, domain))
    return out
