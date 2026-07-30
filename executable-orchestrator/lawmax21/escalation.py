"""Mandatory upward escalation (protocols 40–45), as a control structure rather than a wish.

The supreme law of this project is that nothing mediocre may be delivered: if a strictly
higher conception exists, the current one does not qualify. Protocols 40–45 describe that.
v2.0 encoded it as states the runner walked past exactly once, in a straight line, so the
first candidate that scored well became the answer.

Here the loop is the control flow, and leaving it requires a PROOF OF CEILING:

    A. dryness      — K consecutive rounds in which no new candidate dominated the incumbent
    B. attacked     — a radical challenger was actually built and measured, and lost
    C. simplified   — a simplification challenge was actually built and measured
    D. exhausted    — no untried architecture family remains in the register
    E. altitude     — the incumbent's AUDITED altitude equals the highest altitude for which
                      any evidence exists in this run (self-declaration is ignored)

Only when A–E all hold may the run end in COMMITTED. If the loop stops for any other
reason — budget, wall clock, stagnation, a blocking failure — the terminal state is
BEST_DISCOVERED_SO_FAR or HALTED. The system is permitted to run out of resources; it is
not permitted to call the result supreme when it did not prove it was.
"""
from . import target
from .canonical import atomic_write_json, read_json, utc

# Altitude is NOT a generic scale. It is the owner's own twelve-layer Institution, so the
# tournament cannot crown "a better document analyser" and call it supreme. A generic ladder
# would cap the outcome at the ladder's own altitude — the exact satisficing this protocol
# exists to prevent.
ALTITUDE_LADDER = ["L0"] + target.LAYER_IDS

# The institution-only layers — the ones a sandboxed detector cannot exhibit and that integration
# credit may grant. Every other layer is earned through sandbox altitude evidence, never credited.
INSTITUTION_LAYERS = ["L1", "L2", "L7", "L8", "L10"]

ALTITUDE_EVIDENCE = dict({"L0": "reproduces current behaviour; no layer proven"},
                         **{lid: target.LAYER_TITLE[lid] for lid in target.LAYER_IDS})

PROOF_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "additionalProperties": False,
    "required": ["ceiling_proven", "conditions", "rounds", "incumbent", "untried_families",
                 "audited_altitude", "highest_evidenced_altitude", "terminal_state",
                 "layers_unreached", "evolvability", "axioms_upheld", "consciousness"],
    "properties": {
        "ceiling_proven": {"type": "boolean"},
        "conditions": {
            "type": "object", "additionalProperties": False,
            "required": ["dryness", "attacked_by_radical", "simplification_tested",
                         "families_exhausted", "altitude_saturated", "all_layers_reached",
                         "evolvable_without_refactor", "consciousness_real"],
            "properties": {
                "dryness": {"type": "boolean"}, "attacked_by_radical": {"type": "boolean"},
                "simplification_tested": {"type": "boolean"}, "families_exhausted": {"type": "boolean"},
                "altitude_saturated": {"type": "boolean"}, "all_layers_reached": {"type": "boolean"},
                "evolvable_without_refactor": {"type": "boolean"}, "consciousness_real": {"type": "boolean"},
            },
        },
        "rounds": {"type": "integer", "minimum": 1},
        "incumbent": {"type": "string", "minLength": 1},
        "untried_families": {"type": "array"},
        "audited_altitude": {"enum": ALTITUDE_LADDER},
        "highest_evidenced_altitude": {"enum": ALTITUDE_LADDER},
        "terminal_state": {"enum": ["COMMITTED", "BEST_DISCOVERED_SO_FAR", "HALTED"]},
        "stopped_because": {"type": "string"},
        "unreached": {"type": "array"},
        "layers_unreached": {"type": "array"},
        "evolvability": {"enum": ["EVOLVABLE", "NEEDS_REFACTOR", "UNTESTED"]},
        "axioms_upheld": {"type": "boolean"},
        "consciousness": {"type": "string"},
        "floor": {"type": ["number", "null"]},
        "integration_attested": {"type": "boolean"},
        "integration_credited_candidate": {"type": ["string", "null"]},
        "credited_layers": {"type": "array"},
    },
}


class EscalationLedger:
    def __init__(self, path, dry_rounds_required=2):
        self.path = path
        self.K = dry_rounds_required
        self.s = read_json(path) if _exists(path) else {
            "rounds": [], "incumbent": None, "incumbent_score": None,
            "families_tried": [], "families_known": [], "radical_attacks": [],
            "simplification_attempts": [], "altitude_evidence": {}, "stopped_because": None,
            "consciousness": {}, "floor": None, "floor_history": [],
            "integration_credit": {"layers": [], "consciousness_full": False, "attested": False},
        }

    # ------------------------------------------------------------------ rounds
    def declare_families(self, families):
        for f in families:
            if f not in self.s["families_known"]:
                self.s["families_known"].append(f)
        self._flush()

    def untried_families(self):
        return sorted(set(self.s["families_known"]) - set(self.s["families_tried"]))

    def record_round(self, round_id, candidates, winner, winner_score, kinds):
        """kinds: {candidate_id: 'baseline'|'successor'|'radical'|'simplification'}"""
        prev = self.s["incumbent_score"]
        improved = prev is None or winner_score > prev
        for c in candidates:
            fam = kinds.get(c, {}).get("family") if isinstance(kinds.get(c), dict) else None
            if fam and fam not in self.s["families_tried"]:
                self.s["families_tried"].append(fam)
        for c, meta in kinds.items():
            kind = meta["kind"] if isinstance(meta, dict) else meta
            if kind == "radical":
                self.s["radical_attacks"].append({"candidate": c, "round": round_id})
            if kind == "simplification":
                self.s["simplification_attempts"].append({"candidate": c, "round": round_id})
        self.s["rounds"].append({
            "round": round_id, "candidates": list(candidates), "winner": winner,
            "winner_score": winner_score, "improved_on_incumbent": improved, "utc": utc(),
        })
        if improved:
            self.s["incumbent"], self.s["incumbent_score"] = winner, winner_score
        self._flush()
        return improved

    def record_altitude_evidence(self, candidate_id, altitude, evidence_ref):
        self.s["altitude_evidence"].setdefault(altitude, []).append(
            {"candidate": candidate_id, "evidence": evidence_ref})
        self._flush()

    def layers_covered(self, candidate_id):
        """Layers this candidate DEMONSTRATED in execution. What it claimed is never
        consulted, and the owner-credited institution layers are NOT folded in here — this
        is the pure sandbox-measured set. `all_covered` adds the attested credit on top."""
        return [rung for rung in target.LAYER_IDS
                if any(e["candidate"] == candidate_id
                       for e in self.s["altitude_evidence"].get(rung, []))]

    def all_covered(self, candidate_id):
        """Everything that counts as reached for THIS incumbent: the layers a sandboxed
        detector demonstrated, PLUS the institution layers (L1,L2,L7,L8,L10) the owner has
        actually built and signed an integration attestation for. Before any attestation the
        credit is empty, so this equals the measured set during the whole tournament — the
        crediting only opens once the owner has done the real integration work, and ONLY for the
        candidate the integration was measured and signed FOR (bound credit; a different
        incumbent gets nothing)."""
        return self.layers_covered(candidate_id) + self.credited_layers_for(candidate_id)

    def audited_altitude(self, candidate_id):
        """Highest UNBROKEN prefix of the twelve layers. A build that proves L9 while L4
        is unproven audits below L4 — an institution with a hole in its middle is not
        standing on the layer above the hole. The attested institution layers count here
        too, so a fully-integrated incumbent can actually saturate the ladder; without the
        attestation L1/L2 are missing and the prefix honestly collapses to L0."""
        return target.audited_altitude(self.all_covered(candidate_id))

    def highest_evidenced_altitude(self):
        anyone = [rung for rung in target.LAYER_IDS if self.s["altitude_evidence"].get(rung)]
        # Attested institution layers are evidence too (the owner's signed integration), so
        # the "highest anyone reached" ladder and the incumbent's audited ladder are measured
        # against the SAME layer set — otherwise altitude_saturated could never hold at L12.
        # This uses the RAW credit (the credited candidate genuinely reached those layers, so it
        # is "someone's" evidence); what an ARBITRARY incumbent may claim is the bound set above.
        return target.audited_altitude(anyone + self.credited_layers_raw())

    def record_evolvability(self, candidate_id, verdict):
        self.s.setdefault("evolvability", {})[candidate_id] = verdict
        self._flush()

    def record_axiom_violation(self, candidate_id, axiom_id, detail):
        self.s.setdefault("axiom_violations", []).append(
            {"candidate": candidate_id, "axiom": axiom_id, "detail": detail, "utc": utc()})
        self._flush()

    def record_consciousness(self, candidate_id, verdict):
        self.s.setdefault("consciousness", {})[candidate_id] = verdict
        self._flush()

    def credit_integration(self, candidate_id, layers, consciousness_full):
        """Credit the institution-only layers (L1,L2,L7,L8,L10) and full consciousness AFTER the
        owner has built the winning architecture as a running institution and signed the
        integration attestation — BOUND to the candidate that was measured.

        The credit helps ONLY that candidate. Crediting X's institution can never open the door
        for a different incumbent Y (audit v2.3-critical: the credit was global and unbound, so
        an owner's signature over X's genuine institution could crown a mere detector Y that
        demonstrated no institution layer). The crown therefore requires ONE candidate to be, at
        once, the tournament incumbent AND the measured-and-signed institution — a detector that
        is not that same candidate stays structurally uncrownable."""
        # Only the institution-only layers are ever creditable via integration (audit v2.3 round 2:
        # a measurement was accepted verbatim, so a report listing L3/L99/ZZZ would have credited
        # them). The sandbox-demonstrable layers are earned through altitude_evidence, never here.
        layers = sorted(set(layers) & set(INSTITUTION_LAYERS))
        self.s["integration_credit"] = {"candidate_id": candidate_id,
                                        "layers": layers,
                                        "consciousness_full": bool(consciousness_full),
                                        "attested": True}
        self._flush()

    def credit_from_measurement(self, candidate_id, measurement):
        """Evidence-bound credit for a NAMED candidate: take ONLY the institution layers the
        MEASUREMENT demonstrated and full consciousness ONLY if every dimension measured passed.
        The one seat the runner and the proof both use — a fake institution's measurement lists
        nothing (credits nothing even under a valid signature), and the credit is bound to
        `candidate_id` so it cannot be borrowed by another incumbent."""
        m = measurement or {}
        layers = list(m.get("layers_demonstrated", []))
        full = bool(m.get("consciousness_full"))
        self.credit_integration(candidate_id, layers, full)
        return layers, full

    def _credit(self):
        return self.s.get("integration_credit") or {}

    def credited_candidate(self):
        return self._credit().get("candidate_id")

    def credited_layers_raw(self):
        """The institution layers the credited candidate demonstrated — evidence that SOME
        candidate reached them (for the 'highest anyone reached' ladder and for reporting).
        NOT the same as what counts for an arbitrary incumbent; see credited_layers_for."""
        return list(self._credit().get("layers", []))

    def credited_layers_for(self, incumbent):
        """Institution-layer credit that counts for THIS incumbent: only when the credit was
        measured and signed for this very candidate. Bound, so no other candidate can borrow it."""
        c = self._credit()
        return list(c.get("layers", [])) if incumbent and c.get("candidate_id") == incumbent else []

    def credited_consciousness_for(self, incumbent):
        """Full-consciousness credit counts for THIS incumbent only if it was measured+signed
        for this very candidate — a detector cannot borrow an institution's consciousness."""
        c = self._credit()
        return bool(c.get("consciousness_full")) and bool(incumbent) and c.get("candidate_id") == incumbent

    def below_floor(self, score):
        """The bar rose: a candidate scoring below the established floor does not advance.
        This is the enforcement the floor lacked — it recorded but rejected nothing."""
        f = self.s.get("floor")
        return f is not None and score < f

    def ratchet_floor(self, score):
        """The bar RISES. Today's LAWMAX is the starting floor, not a passing mark; each
        winner lifts it. A later candidate below the floor is not progress — the run keeps
        cutting until something clears an ever-higher bar. The floor never descends."""
        prev = self.s.get("floor")
        if prev is None or score > prev:
            self.s["floor"] = score
            self.s["floor_history"].append(score)
            self._flush()
        return self.s["floor"]

    def incumbent_consciousness(self):
        inc = self.s["incumbent"]
        return (self.s.get("consciousness") or {}).get(inc, "NOT_DEMONSTRATED")

    def incumbent_evolvability(self):
        inc = self.s["incumbent"]
        return (self.s.get("evolvability") or {}).get(inc, "UNTESTED")

    def axioms_upheld(self):
        inc = self.s["incumbent"]
        return not any(v["candidate"] == inc for v in self.s.get("axiom_violations", []))

    # -------------------------------------------------------------- the decision
    def dry_rounds(self):
        n = 0
        for r in reversed(self.s["rounds"]):
            if r["improved_on_incumbent"]:
                break
            n += 1
        return n

    def must_continue(self):
        """The question asked at the top of every round. False only with a ceiling proof."""
        c = self.conditions()
        if all(c.values()):
            return False, "ceiling proven: " + ", ".join(k for k in c)
        unmet = [k for k, v in c.items() if not v]
        return True, "escalation still required — unmet: " + ", ".join(unmet)

    def conditions(self):
        inc = self.s["incumbent"]
        return {
            "dryness": self.dry_rounds() >= self.K,
            "attacked_by_radical": bool(self.s["radical_attacks"]),
            "simplification_tested": bool(self.s["simplification_attempts"]),
            "families_exhausted": not self.untried_families(),
            "altitude_saturated": bool(inc) and self.audited_altitude(inc) == self.highest_evidenced_altitude(),
            # The two that stop us calling a better parser "the Institution":
            "all_layers_reached": bool(inc) and not target.missing_layers(self.all_covered(inc)),
            "evolvable_without_refactor": self.incumbent_evolvability() == "EVOLVABLE",
            # The "invincible AND super-smart" gate: the crown needs the REAL consciousness
            # probe passed — today's dumb LAWMAX, which cannot, is structurally uncrownable. The
            # full-consciousness credit must be measured+signed for THIS incumbent, not borrowed
            # from another candidate (audit v2.3-critical: bound credit).
            "consciousness_real": self.incumbent_consciousness() == "REAL"
                and self.credited_consciousness_for(inc),
        }

    def stop(self, because):
        self.s["stopped_because"] = because
        self._flush()

    def proof(self):
        """The artifact the COMMITTED guard reads. It cannot be produced any other way."""
        c = self.conditions()
        proven = (all(c.values()) and self.axioms_upheld()
                  and self.s["stopped_because"] in (None, "ceiling"))
        inc = self.s["incumbent"] or ""
        # layers_unreached MUST count the attested institution layers exactly as conditions()
        # does, or COMMITTED is unreachable by construction: the guard would forever see
        # L1/L2/L7/L8/L10 as "unreached" even after the owner signed for them (audit: liveness
        # hole — the crown could never be granted, for any candidate, ever).
        covered = self.all_covered(inc) if inc else []
        missing = target.missing_layers(covered)
        unreached = [f"{lid} · {target.LAYER_TITLE[lid]}" for lid in missing]
        return {
            "ceiling_proven": proven,
            "conditions": c,
            "rounds": max(1, len(self.s["rounds"])),
            "incumbent": inc or "NONE",
            "untried_families": self.untried_families(),
            "audited_altitude": self.audited_altitude(inc) if inc else "L0",
            "highest_evidenced_altitude": self.highest_evidenced_altitude(),
            "layers_unreached": missing,
            "evolvability": self.incumbent_evolvability(),
            "axioms_upheld": self.axioms_upheld(),
            "consciousness": self.incumbent_consciousness(),
            "floor": self.s.get("floor"),
            "integration_attested": self._credit().get("attested", False),
            "integration_credited_candidate": self.credited_candidate(),
            "credited_layers": self.credited_layers_for(inc),
            "terminal_state": "COMMITTED" if proven else (
                "HALTED" if self.s["stopped_because"] == "blocking-failure" else "BEST_DISCOVERED_SO_FAR"),
            "stopped_because": self.s["stopped_because"] or "ceiling",
            "unreached": unreached,
        }

    def _flush(self):
        atomic_write_json(self.path, self.s)


def integration_credit_gate(esc, subject, subject_sha, approval, owner_pub, run_id, remeasure):
    """THE one seat for evidence-bound integration credit — shared verbatim by the runner
    (handlers.credit_integration_if_attested) and the adversarial proof (audit v2.3 round 3: the
    proof used to re-implement this, so a regression in the real gate would not have been caught).

    Two independent authorities, neither forgeable alone, and the measurement is RE-DERIVED rather
    than trusted:
      1. the owner's Ed25519 signature over the exact subject (inalienable human sovereignty);
      2. a FRESH re-measurement of the named candidate — `remeasure(candidate_id)` — that must MATCH
         the measurement the owner signed. The signed report is advisory; a fabricated one (claiming
         layers a detector never earned) fails the match and credits nothing.
    Credit is then taken from the fresh measurement, bound to the candidate, restricted to the
    institution layers. Returns True iff credit was applied."""
    from .signing import SignatureRejected, verify_approval
    if approval is None:
        return False
    try:
        verify_approval(approval, owner_pub, "GATE-INTEGRATION", run_id, subject_sha)
    except SignatureRejected:
        return False
    cid = subject.get("candidate_id")
    if not cid:
        return False
    signed = subject.get("institution_measurement") or {}
    fresh = remeasure(cid)
    if not isinstance(fresh, dict):
        return False
    if (sorted(fresh.get("layers_demonstrated", [])) != sorted(signed.get("layers_demonstrated", []))
            or bool(fresh.get("consciousness_full")) != bool(signed.get("consciousness_full"))):
        return False   # the signed report does not match the re-derived truth — refuse
    esc.credit_from_measurement(cid, fresh)
    return True


def _exists(p):
    import os
    return os.path.exists(p)
