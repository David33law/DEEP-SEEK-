"""National Observatory escalation semantics over the shared escalation ledger.

Search-loop closure and final supremacy closure are separate. Architecture-search admission is
also profile-specific: family-name inequality is not diversity. The v0 search artifact must contain
at least twelve pairwise structurally distinct controlled genomes and must still be blind to CP2.
"""
from .escalation import EscalationLedger
from . import observatory_target as target
from . import observatory_roles as oroles


SUPREMACY_KEYS = [
    "search_forest_executed",
    "genome_saturated",
    "recombination_tested",
    "systems_arena_passed",
    "lower_bound_closed",
    "destroyer_survived",
    "public_supremacy_case",
]

SEARCH_SUPREMACY_KEYS = [
    "search_forest_executed",
    "genome_saturated",
    "recombination_tested",
]

OBSERVATORY_PROOF_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "ceiling_proven", "conditions", "rounds", "incumbent", "untried_families",
        "audited_altitude", "highest_evidenced_altitude", "terminal_state",
        "layers_unreached", "evolvability", "axioms_upheld", "supremacy",
    ],
    "properties": {
        "ceiling_proven": {"type": "boolean"},
        "conditions": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "dryness", "attacked_by_radical", "simplification_tested",
                "families_exhausted", "altitude_saturated", "all_layers_reached",
                "evolvable_without_refactor", *SUPREMACY_KEYS,
            ],
            "properties": {
                "dryness": {"type": "boolean"},
                "attacked_by_radical": {"type": "boolean"},
                "simplification_tested": {"type": "boolean"},
                "families_exhausted": {"type": "boolean"},
                "altitude_saturated": {"type": "boolean"},
                "all_layers_reached": {"type": "boolean"},
                "evolvable_without_refactor": {"type": "boolean"},
                **{k: {"type": "boolean"} for k in SUPREMACY_KEYS},
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
        "supremacy": {
            "type": "object", "additionalProperties": True,
            "required": SUPREMACY_KEYS + ["genome_dry_waves", "known_genomes"],
            "properties": {
                **{k: {"type": "boolean"} for k in SUPREMACY_KEYS},
                "genome_dry_waves": {"type": "integer", "minimum": 0},
                "known_genomes": {"type": "integer", "minimum": 0},
                "third_party_endorsement_claimed": {"const": False},
            },
        },
    },
}


class ObservatoryEscalationLedger(EscalationLedger):
    GENOME_DRY_WAVES_REQUIRED = 3

    def _sup(self):
        s = self.s.setdefault("supremacy", {})
        s.setdefault("known_genomes", [])
        s.setdefault("search_waves", [])
        s.setdefault("recombinations", [])
        s.setdefault("systems_arena", {})
        s.setdefault("lower_bound", {})
        s.setdefault("destroyer", {})
        s.setdefault("public_case", {})
        return s

    def record_search_wave(self, label, genome_ids):
        sup = self._sup()
        before = set(sup["known_genomes"])
        ordered = []
        for g in genome_ids:
            g = str(g)
            if g not in ordered:
                ordered.append(g)
        new = [g for g in ordered if g not in before]
        for g in new:
            sup["known_genomes"].append(g)
        sup["search_waves"].append({"label": str(label), "genomes": ordered,
                                    "new_genomes": new, "new_count": len(new)})
        self._flush()
        return len(new)

    def genome_dry_waves(self):
        n = 0
        for w in reversed(self._sup()["search_waves"]):
            if int(w.get("new_count", 0)) != 0:
                break
            n += 1
        return n

    def record_recombination(self, candidate_id, genome_id, evidence_ref):
        self._sup()["recombinations"].append({"candidate": candidate_id,
                                               "genome": str(genome_id),
                                               "evidence": str(evidence_ref)})
        self._flush()

    def record_systems_arena(self, candidate_id, passed, evidence_ref):
        self._sup()["systems_arena"][candidate_id] = {
            "passed": bool(passed), "evidence": str(evidence_ref)}
        self._flush()

    def record_lower_bound(self, candidate_id, closed, evidence_ref):
        self._sup()["lower_bound"][candidate_id] = {
            "closed": bool(closed), "evidence": str(evidence_ref)}
        self._flush()

    def record_destroyer(self, candidate_id, survived, evidence_ref):
        self._sup()["destroyer"][candidate_id] = {
            "survived": bool(survived), "evidence": str(evidence_ref)}
        self._flush()

    def record_supremacy_case(self, candidate_id, supported, evidence_ref,
                              third_party_endorsement_claimed=False):
        self._sup()["public_case"][candidate_id] = {
            "supported": bool(supported), "evidence": str(evidence_ref),
            "third_party_endorsement_claimed": bool(third_party_endorsement_claimed)}
        self._flush()

    def _base_search_conditions(self):
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

    def _supremacy_conditions(self):
        inc = self.s["incumbent"]
        sup = self._sup()
        systems = sup["systems_arena"].get(inc, {}) if inc else {}
        lower = sup["lower_bound"].get(inc, {}) if inc else {}
        destroyer = sup["destroyer"].get(inc, {}) if inc else {}
        case = sup["public_case"].get(inc, {}) if inc else {}
        return {
            "search_forest_executed": bool(sup["search_waves"]),
            "genome_saturated": self.genome_dry_waves() >= self.GENOME_DRY_WAVES_REQUIRED,
            "recombination_tested": bool(sup["recombinations"]),
            "systems_arena_passed": bool(systems.get("passed")),
            "lower_bound_closed": bool(lower.get("closed")),
            "destroyer_survived": bool(destroyer.get("survived")),
            "public_supremacy_case": bool(case.get("supported"))
                and not bool(case.get("third_party_endorsement_claimed")),
        }

    def search_conditions(self):
        c = self._base_search_conditions()
        sup = self._supremacy_conditions()
        for key in SEARCH_SUPREMACY_KEYS:
            c[key] = sup[key]
        return c

    def must_continue(self):
        c = self.search_conditions()
        if all(c.values()):
            return False, "search ceiling proven: " + ", ".join(k for k in c)
        unmet = [k for k, v in c.items() if not v]
        return True, "search escalation still required — unmet: " + ", ".join(unmet)

    def conditions(self):
        c = self._base_search_conditions()
        c.update(self._supremacy_conditions())
        return c

    def audited_altitude(self, candidate_id):
        return target.audited_altitude(self.layers_covered(candidate_id))

    def highest_evidenced_altitude(self):
        anyone = [lid for lid in target.LAYER_IDS if self.s["altitude_evidence"].get(lid)]
        return target.audited_altitude(anyone)

    def all_covered(self, candidate_id):
        return self.layers_covered(candidate_id)

    def supremacy_summary(self):
        sup = self._sup()
        cond = self._supremacy_conditions()
        public = sup["public_case"].get(self.s.get("incumbent"), {}) if self.s.get("incumbent") else {}
        return {
            **cond,
            "genome_dry_waves": self.genome_dry_waves(),
            "known_genomes": len(sup["known_genomes"]),
            "search_waves": len(sup["search_waves"]),
            "recombinations": len(sup["recombinations"]),
            "third_party_endorsement_claimed": bool(public.get("third_party_endorsement_claimed", False)),
        }

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
            "supremacy": self.supremacy_summary(),
            "terminal_state": "COMMITTED" if proven else (
                "HALTED" if self.s["stopped_because"] == "blocking-failure" else "BEST_DISCOVERED_SO_FAR"),
            "stopped_because": self.s["stopped_because"] or "ceiling",
            "unreached": [f"{lid} · {target.LAYER_TITLE[lid]}" for lid in missing],
        }


def install_state_semantics(states_module):
    """Install Observatory-only proposal and terminal semantics into the shared state machine."""
    original_committed = states_module.SEMANTIC["COMMITTED"]
    original_proposals = states_module.SEMANTIC.get("TARGET_ARCHITECTURE_SEARCH")
    for terminal in ("COMMITTED", "BEST_DISCOVERED_SO_FAR", "HALTED"):
        states_module.SCHEMAS[terminal] = OBSERVATORY_PROOF_SCHEMA

    def proposals(rt, art):
        if getattr(rt, "profile_id", "lawmax") != "national-observatory":
            if original_proposals:
                return original_proposals(rt, art)
            return None
        if art.get("search_mode") != "SUPREMACY_SEARCH_FOREST_V1":
            raise states_module.GuardFailed("Observatory search did not use the supremacy search forest")
        if art.get("prior_cp2_visible") is not False:
            raise states_module.GuardFailed("prior CP2 was visible before the independent frontier")
        props = art.get("proposals") or []
        if len(props) < 12:
            raise states_module.GuardFailed(f"supremacy search produced only {len(props)} structural finalists")

        def sig(p):
            g = p.get("genome")
            if not isinstance(g, dict):
                raise states_module.GuardFailed("architecture proposal is missing controlled genome")
            out = []
            for axis in oroles.GENOME_FIELDS:
                value = g.get(axis)
                if not isinstance(value, dict) or value.get("class") not in oroles.GENOME_CLASSES[axis]:
                    raise states_module.GuardFailed(f"proposal has invalid controlled genome axis {axis}")
                out.append(value["class"])
            return tuple(out)

        signatures = [(p.get("seed_id"), sig(p)) for p in props]
        for i, (aid, a) in enumerate(signatures):
            for bid, b in signatures[i + 1:]:
                distance = sum(1 for x, y in zip(a, b) if x != y)
                if distance < 2:
                    raise states_module.GuardFailed(
                        f"structural finalists {aid!r}/{bid!r} differ on only {distance} controlled genome axes")
        return None

    def committed(rt, art):
        if getattr(rt, "profile_id", "lawmax") != "national-observatory":
            return original_committed(rt, art)
        if art["terminal_state"] != "COMMITTED":
            raise states_module.GuardFailed("Observatory escalation proof does not conclude COMMITTED")
        if not art["ceiling_proven"]:
            raise states_module.GuardFailed("Observatory COMMITTED requires a proof of supremacy ceiling")
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
        sup = art.get("supremacy") or {}
        if any(not sup.get(k) for k in SUPREMACY_KEYS):
            raise states_module.GuardFailed("Observatory COMMITTED blocked — supremacy evidence incomplete")
        if sup.get("third_party_endorsement_claimed"):
            raise states_module.GuardFailed(
                "Observatory COMMITTED blocked — unsupported third-party endorsement claim")

    states_module.SEMANTIC["TARGET_ARCHITECTURE_SEARCH"] = proposals
    states_module.SEMANTIC["COMMITTED"] = committed
    return original_committed
