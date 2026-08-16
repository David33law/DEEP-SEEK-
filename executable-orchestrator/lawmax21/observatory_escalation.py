"""National Observatory escalation semantics over the shared escalation ledger.

The control loop and signed log are shared with LAWMAX. This profile changes only the target
meaning: no consciousness/integration credit is required, and all twelve Observatory layers must
be demonstrated directly by executable/profile-specific evidence.
"""
from .escalation import EscalationLedger
from . import observatory_target as target


class ObservatoryEscalationLedger(EscalationLedger):
    def conditions(self):
        inc = self.s["incumbent"]
        covered = self.layers_covered(inc) if inc else []
        return {
            "dryness": self.dry_rounds() >= self.K,
            "attacked_by_radical": bool(self.s["radical_attacks"]),
            "simplification_tested": bool(self.s["simplification_attempts"]),
            "families_exhausted": not self.untried_families(),
            "altitude_saturated": bool(inc) and target.audited_altitude(covered) == self.highest_evidenced_altitude(),
            "all_layers_reached": bool(inc) and not target.missing_layers(covered),
            "evolvable_without_refactor": self.incumbent_evolvability() == "EVOLVABLE",
            # Legacy proof-schema key retained for compatibility. True here means the condition
            # is NOT APPLICABLE to this profile, not that consciousness was measured.
            "consciousness_real": True,
        }

    def audited_altitude(self, candidate_id):
        return target.audited_altitude(self.layers_covered(candidate_id))

    def highest_evidenced_altitude(self):
        anyone = [lid for lid in target.LAYER_IDS if self.s["altitude_evidence"].get(lid)]
        return target.audited_altitude(anyone)

    def all_covered(self, candidate_id):
        return self.layers_covered(candidate_id)

    def proof(self):
        conditions = self.conditions()
        proven = (all(conditions.values()) and self.axioms_upheld()
                  and self.s["stopped_because"] in (None, "ceiling"))
        inc = self.s["incumbent"] or ""
        covered = self.layers_covered(inc) if inc else []
        missing = target.missing_layers(covered)
        return {
            "ceiling_proven": proven,
            "conditions": conditions,
            "rounds": max(1, len(self.s["rounds"])),
            "incumbent": inc or "NONE",
            "untried_families": self.untried_families(),
            "audited_altitude": target.audited_altitude(covered) if inc else "L0",
            "highest_evidenced_altitude": self.highest_evidenced_altitude(),
            "layers_unreached": missing,
            "evolvability": self.incumbent_evolvability(),
            "axioms_upheld": self.axioms_upheld(),
            "consciousness": "NOT_REQUIRED_BY_PROFILE",
            "floor": self.s.get("floor"),
            "integration_attested": False,
            "integration_credited_candidate": None,
            "credited_layers": [],
            "terminal_state": "COMMITTED" if proven else (
                "HALTED" if self.s["stopped_because"] == "blocking-failure" else "BEST_DISCOVERED_SO_FAR"),
            "stopped_because": self.s["stopped_because"] or "ceiling",
            "unreached": [f"{lid} · {target.LAYER_TITLE[lid]}" for lid in missing],
        }


def install_state_semantics(states_module):
    """Install one profile-local COMMITTED semantic guard without replacing the state machine."""
    def committed(rt, art):
        if getattr(rt, "profile_id", "lawmax") != "national-observatory":
            # Delegate to the original LAWMAX guard captured before replacement.
            return original(rt, art)
        if art["terminal_state"] != "COMMITTED":
            raise states_module.GuardFailed("Observatory escalation proof does not conclude COMMITTED")
        if not art["ceiling_proven"]:
            raise states_module.GuardFailed("Observatory COMMITTED requires a proof of ceiling")
        unmet = [k for k, v in art["conditions"].items() if not v]
        if unmet:
            raise states_module.GuardFailed(f"Observatory COMMITTED blocked — unmet: {unmet}")
        if art["untried_families"]:
            raise states_module.GuardFailed(
                f"Observatory COMMITTED blocked — untried architecture families remain: {art['untried_families']}")
        if art["audited_altitude"] != art["highest_evidenced_altitude"]:
            raise states_module.GuardFailed("Observatory incumbent has not saturated the evidenced altitude")
        if art["layers_unreached"]:
            raise states_module.GuardFailed(
                "Observatory COMMITTED blocked — unreached target layers: " + ", ".join(art["layers_unreached"]))
        if art["evolvability"] != "EVOLVABLE":
            raise states_module.GuardFailed("Observatory COMMITTED requires measured evolvability")
        if not art["axioms_upheld"]:
            raise states_module.GuardFailed("Observatory COMMITTED blocked — target axiom violated")
        if art.get("consciousness") != "NOT_REQUIRED_BY_PROFILE":
            raise states_module.GuardFailed("Observatory proof must explicitly mark consciousness as not required")

    original = states_module.SEMANTIC["COMMITTED"]
    states_module.SEMANTIC["COMMITTED"] = committed
    return original
