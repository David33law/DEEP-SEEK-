"""National Observatory escalation semantics over the shared escalation ledger.

The control loop and signed log are shared with LAWMAX. This profile changes only the target
meaning: all twelve Observatory layers must be demonstrated directly by executable/profile-
specific evidence. LAWMAX-only consciousness and institution-credit fields do not exist in the
Observatory terminal proof contract.
"""
from .escalation import EscalationLedger
from . import observatory_target as target


OBSERVATORY_PROOF_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "ceiling_proven", "conditions", "rounds", "incumbent", "untried_families",
        "audited_altitude", "highest_evidenced_altitude", "terminal_state",
        "layers_unreached", "evolvability", "axioms_upheld",
    ],
    "properties": {
        "ceiling_proven": {"type": "boolean"},
        "conditions": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "dryness", "attacked_by_radical", "simplification_tested",
                "families_exhausted", "altitude_saturated", "all_layers_reached",
                "evolvable_without_refactor",
            ],
            "properties": {
                "dryness": {"type": "boolean"},
                "attacked_by_radical": {"type": "boolean"},
                "simplification_tested": {"type": "boolean"},
                "families_exhausted": {"type": "boolean"},
                "altitude_saturated": {"type": "boolean"},
                "all_layers_reached": {"type": "boolean"},
                "evolvable_without_refactor": {"type": "boolean"},
            },
        },
        "rounds": {"type": "integer", "minimum": 1},
        "incumbent": {"type": "string", "minLength": 1},
        "untried_families": {"type": "array"},
        "audited_altitude": {"enum": ["L0"] + target.LAYER_IDS},
        "highest_evidenced_altitude": {"enum": ["L0"] + target.LAYER_IDS},
        "terminal_state": {"enum": ["COMMITTED", "BEST_DISCOVERED_SO_FAR", "HALTED"]},
        "stopped_because": {"type": "string"},
        "unreached": {"type": "array"},
        "layers_unreached": {"type": "array"},
        "evolvability": {"enum": ["EVOLVABLE", "NEEDS_REFACTOR", "UNTESTED"]},
        "axioms_upheld": {"type": "boolean"},
        "floor": {"type": ["number", "null"]},
    },
}


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
            "floor": self.s.get("floor"),
            "terminal_state": "COMMITTED" if proven else (
                "HALTED" if self.s["stopped_because"] == "blocking-failure" else "BEST_DISCOVERED_SO_FAR"),
            "stopped_because": self.s["stopped_because"] or "ceiling",
            "unreached": [f"{lid} · {target.LAYER_TITLE[lid]}" for lid in missing],
        }


def install_state_semantics(states_module):
    """Install profile-local terminal schemas/guard without replacing the shared state machine.

    This runs only in the Observatory launcher process. Ordinary LAWMAX processes continue to use
    escalation.PROOF_SCHEMA and the original LAWMAX COMMITTED semantic guard unchanged.
    """
    original = states_module.SEMANTIC["COMMITTED"]
    for terminal in ("COMMITTED", "BEST_DISCOVERED_SO_FAR", "HALTED"):
        states_module.SCHEMAS[terminal] = OBSERVATORY_PROOF_SCHEMA

    def committed(rt, art):
        if getattr(rt, "profile_id", "lawmax") != "national-observatory":
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

    states_module.SEMANTIC["COMMITTED"] = committed
    return original
