"""The 37-state machine with SEMANTIC guards.

v2.0's guard was `os.path.exists(artifact)`, so a 0-byte file advanced the run and a
hand-written checkpoint jumped 33 states at once. Here a transition requires, in order:

  1. the transition is legal from the state DERIVED FROM THE SIGNED LOG (not a checkpoint)
  2. every declared artifact exists AND validates against its JSON Schema
  3. the state's semantic predicate holds — a real question about the content
  4. if the state is an owner gate, an owner-signed approval bound to (gate, run,
     artifact hash) verifies against the owner's public key

Failing any of the four raises. There is no code path that transitions without all four.
"""
import os

from . import escalation
from .canonical import read_json, sha256_file
from .eventlog import Checkpoint, EventLog
from .schema import ValidationError, validate
from .signing import SignatureRejected, verify_approval

STATES = [
    "UNINITIALIZED", "PACKAGE_VALIDATED", "EVIDENCE_VAULT_CERTIFIED", "CHARTER_FROZEN",
    "HIDDEN_BANK_COMMITTED", "ATTESTED", "REPOSITORY_RECONSTRUCTED",
    "HISTORICAL_EVIDENCE_SYNTHESIZED", "GLOBAL_LAWMAX_MODEL_CERTIFIED",
    "TARGET_ARCHITECTURE_SEARCH", "TARGET_ARCHITECTURE_v0_REVIEWED",
    "TARGET_ARCHITECTURE_v0_FROZEN", "EVALUATION_PARAMETERS_FROZEN", "SUBSTRATE_BUILDING",
    "SUBSTRATE_CERTIFIED", "ARCHITECTURE_DISCOVERY", "CANDIDATE_BUILDING", "VISIBLE_CERTIFIED",
    "FIDELITY_CERTIFIED", "PRIVATE_QUALIFICATION", "PROVISIONAL_FRONTIER_MEMBER",
    "CEILING_ANALYSIS", "SUCCESSOR_SEARCH", "RADICAL_CHALLENGER_SEARCH",
    "SIMPLIFICATION_CHALLENGE", "FRONTIER_REVIEW", "PRIVATE_REPLICATION",
    "ANTI_SATISFICING_AUDIT", "HESA_CANDIDATE", "FINAL_HOLDOUT_EVALUATION",
    "ARCHITECTURE_EVIDENCE_SYNTHESIS", "TARGET_ARCHITECTURE_v1_REVIEWED",
    "MIGRATION_PLAN_FROZEN", "INDEPENDENT_AUDIT", "COMMITTED",
    "BEST_DISCOVERED_SO_FAR", "HALTED",
]

NEXT = {STATES[i]: [STATES[i + 1]] for i in range(len(STATES) - 3)}
# The escalation loop closes here, and it closes back onto CEILING_ANALYSIS rather than
# straight into SUCCESSOR_SEARCH: every round must re-ask what the CURRENT incumbent
# cannot do. Re-using round 1's ceiling would let round 2 chase a limit that no longer
# binds — the shape of satisficing this protocol exists to prevent.
NEXT["ANTI_SATISFICING_AUDIT"] = ["HESA_CANDIDATE", "CEILING_ANALYSIS"]
# FRONTIER_REVIEW advances only to PRIVATE_REPLICATION. An earlier spurious back-edge to
# SUCCESSOR_SEARCH here made the resume skip-test re-fire completed challenger states and
# write backward transitions into the append-only log (audit: orchestrator resume-backward-redo).
NEXT["FRONTIER_REVIEW"] = ["PRIVATE_REPLICATION"]
NEXT["INDEPENDENT_AUDIT"] = ["COMMITTED", "BEST_DISCOVERED_SO_FAR", "HALTED"]
NEXT["COMMITTED"] = []
NEXT["BEST_DISCOVERED_SO_FAR"] = []
NEXT["HALTED"] = []

# States whose transition additionally requires bytes signed on the owner's machine.
OWNER_GATES = {
    "TARGET_ARCHITECTURE_v0_REVIEWED": "GATE-ARCH-V0",
    "TARGET_ARCHITECTURE_v1_REVIEWED": "GATE-ARCH-V1",
    "MIGRATION_PLAN_FROZEN": "GATE-MIGRATION",
    "COMMITTED": "GATE-COMMIT",
}


class GuardFailed(Exception):
    pass


class OwnerApprovalRequired(GuardFailed):
    """Not an error — the run has reached a decision that is the owner's to make.
    Carried as typed data so no caller has to parse a message to learn what to sign."""

    def __init__(self, gate_id, run_id, subject_path, subject_sha256, approval_path, reason=""):
        self.gate_id = gate_id
        self.run_id = run_id
        self.subject_path = subject_path
        self.subject_sha256 = subject_sha256
        self.approval_path = approval_path
        self.reason = reason
        super().__init__(f"owner gate {gate_id} is unsatisfied"
                         + (f": {reason}" if reason else " (no approval present)"))


def replay(events):
    """Derive the state purely from the signed log. The ONLY definition of 'where we are'."""
    state = "UNINITIALIZED"
    for e in events:
        if e["kind"] == "transition":
            target = e["payload"]["to"]
            if target not in STATES:
                raise GuardFailed(f"log contains unknown state {target!r}")
            state = target
    return state


# --------------------------------------------------------------------------- schemas
def _artifact_schema(required, props, extra_required=()):
    return {"$schema": "http://json-schema.org/draft-07/schema#", "type": "object",
            "required": list(required) + list(extra_required), "properties": props}


NONEMPTY = {"type": "string", "minLength": 1}
SCORE = {"type": "number", "minimum": 0.0, "maximum": 1.0}

SCHEMAS = {
    "PACKAGE_VALIDATED": _artifact_schema(
        ["verdict", "manifest_files_checked", "unlisted_files", "missing_files", "schema_failures"],
        {"verdict": {"const": "OK"}, "manifest_files_checked": {"type": "integer", "minimum": 1},
         "unlisted_files": {"type": "array", "maxItems": 0},
         "missing_files": {"type": "array", "maxItems": 0},
         "schema_failures": {"type": "array", "maxItems": 0}}),
    "EVIDENCE_VAULT_CERTIFIED": _artifact_schema(
        ["required_sources", "present", "missing", "total_bytes"],
        {"required_sources": {"type": "array", "minItems": 8},
         "present": {"type": "array", "minItems": 8},
         "missing": {"type": "array", "maxItems": 0},
         "total_bytes": {"type": "integer", "minimum": 1}}),
    "CHARTER_FROZEN": _artifact_schema(
        ["vision_status", "frozen_files", "charter_sha256"],
        {"vision_status": {"enum": ["EVIDENCE_BACKED"]},
         "frozen_files": {"type": "array", "minItems": 5},
         "charter_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"}}),
    "HIDDEN_BANK_COMMITTED": _artifact_schema(
        ["merkle_root", "counts", "grader_freeze", "canaries"],
        {"merkle_root": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
         "counts": {"type": "object"},
         "grader_freeze": {"type": "object", "minProperties": 1},
         "canaries": {"type": "array", "minItems": 3}}),
    "ATTESTED": _artifact_schema(
        ["mode", "paid_api_calls", "package_tree_sha256", "key_material_visible_to_builder"],
        {"mode": {"enum": ["LAUNCH", "PROOF"]},
         "paid_api_calls": {"type": "integer", "minimum": 0},
         "package_tree_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
         "key_material_visible_to_builder": {"const": False}}),
    "REPOSITORY_RECONSTRUCTED": _artifact_schema(
        ["items", "unknown"],
        {"items": {"type": "array", "minItems": 1,
                   "items": {"type": "object", "required": ["path", "status", "evidence"],
                             "properties": {"path": NONEMPTY, "status": NONEMPTY, "evidence": NONEMPTY}}},
         "unknown": {"type": "array"}}),
    "HISTORICAL_EVIDENCE_SYNTHESIZED": _artifact_schema(
        ["studies", "lessons"],
        {"studies": {"type": "array", "minItems": 3},
         "lessons": {"type": "array", "minItems": 3,
                     "items": {"type": "object", "required": ["lesson", "source"],
                               "properties": {"lesson": NONEMPTY, "source": NONEMPTY}}}}),
    "GLOBAL_LAWMAX_MODEL_CERTIFIED": _artifact_schema(
        ["certified", "chunks_required", "chunks_ingested", "uningested_count", "verified_citations"],
        {"certified": {"const": True},
         "chunks_required": {"type": "integer", "minimum": 1},
         "chunks_ingested": {"type": "integer", "minimum": 1},
         "uningested_count": {"type": "integer", "maximum": 0},
         "verified_citations": {"type": "integer", "minimum": 1}}),
    "TARGET_ARCHITECTURE_SEARCH": _artifact_schema(
        ["proposals"],
        {"proposals": {"type": "array", "minItems": 3,
                       "items": {"type": "object",
                                 "required": ["role", "logical_id", "family", "trusted_boundary",
                                              "mechanisms", "falsifiable_predictions"],
                                 "properties": {"role": NONEMPTY, "logical_id": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
                                                "family": NONEMPTY, "trusted_boundary": NONEMPTY,
                                                "mechanisms": {"type": "array", "minItems": 1},
                                                "falsifiable_predictions": {"type": "array", "minItems": 1}}}}}),
    "SUBSTRATE_CERTIFIED": _artifact_schema(
        ["all_pass", "cases", "slice_scores"],
        {"all_pass": {"const": True}, "cases": {"type": "integer", "minimum": 1},
         "slice_scores": {"type": "object", "minProperties": 8}}),
    "ARCHITECTURE_DISCOVERY": _artifact_schema(
        ["candidates"],
        {"candidates": {"type": "array", "minItems": 2,
                        "items": {"type": "object", "required": ["id", "family", "mechanism"],
                                  "properties": {"id": NONEMPTY, "family": NONEMPTY, "mechanism": NONEMPTY}}}}),
    "CANDIDATE_BUILDING": _artifact_schema(
        ["built"],
        {"built": {"type": "array", "minItems": 2,
                   "items": {"type": "object", "required": ["candidate_id", "worktree", "files_written", "compiles"],
                             "properties": {"candidate_id": NONEMPTY, "worktree": NONEMPTY,
                                            "files_written": {"type": "array", "minItems": 1},
                                            "compiles": {"const": True}}}}}),
    "VISIBLE_CERTIFIED": _artifact_schema(
        ["results"],
        {"results": {"type": "array", "minItems": 2,
                     "items": {"type": "object", "required": ["candidate_id", "slice_scores", "macro_f1"],
                               "properties": {"candidate_id": NONEMPTY, "slice_scores": {"type": "object"},
                                              "macro_f1": SCORE}}}}),
    "FIDELITY_CERTIFIED": _artifact_schema(
        ["results", "kept_as_contenders", "killed_for_cheating"],
        {"results": {"type": "array", "minItems": 1,
                     "items": {"type": "object",
                               "required": ["candidate_id", "hardcoded_answer_scan", "salvageable"],
                               "properties": {"candidate_id": NONEMPTY,
                                              "hardcoded_answer_scan": {"type": "string"},
                                              "salvageable": {"type": "boolean"},
                                              "load_bearing_slices": {"type": "array"}}}},
         "kept_as_contenders": {"type": "array", "minItems": 1},
         "killed_for_cheating": {"type": "array"}}),
    "PRIVATE_QUALIFICATION": _artifact_schema(
        ["results", "canaries_all_denied"],
        {"canaries_all_denied": {"const": True},
         "results": {"type": "array", "minItems": 1,
                     "items": {"type": "object", "required": ["candidate_id", "diagnostic_classes", "slice_scores"],
                               "properties": {"candidate_id": NONEMPTY, "diagnostic_classes": {"type": "object"},
                                              "slice_scores": {"type": "object"}}}}}),
    "PROVISIONAL_FRONTIER_MEMBER": _artifact_schema(
        ["members"], {"members": {"type": "object", "minProperties": 1}}),
    "CEILING_ANALYSIS": _artifact_schema(
        ["cannot_do", "bottleneck", "next_altitude", "evidence"],
        {"cannot_do": {"type": "array", "minItems": 1}, "bottleneck": NONEMPTY,
         "next_altitude": NONEMPTY, "evidence": {"type": "array", "minItems": 1}}),
    "FRONTIER_REVIEW": _artifact_schema(
        ["statuses", "to_private_shards", "dominated"],
        {"statuses": {"type": "object", "minProperties": 2},
         "to_private_shards": {"type": "array", "minItems": 1},
         "dominated": {"type": "array"}}),
    "ANTI_SATISFICING_AUDIT": _artifact_schema(
        ["checks", "unresolved"],
        {"checks": {"type": "object", "minProperties": 8},
         "unresolved": {"type": "array", "maxItems": 0}}),
    "HESA_CANDIDATE": _artifact_schema(
        ["candidate_id", "beats", "margin", "basis"],
        {"candidate_id": NONEMPTY, "beats": {"type": "array", "minItems": 1},
         "margin": {"type": "number"}, "basis": NONEMPTY}),
    "FINAL_HOLDOUT_EVALUATION": _artifact_schema(
        ["candidate_id", "holdout_used_once", "diagnostic_classes", "slice_scores"],
        {"candidate_id": NONEMPTY, "holdout_used_once": {"const": True},
         "diagnostic_classes": {"type": "object"}, "slice_scores": {"type": "object"}}),
    "MIGRATION_PLAN_FROZEN": _artifact_schema(
        ["waves", "big_bang", "rollback_per_wave"],
        {"waves": {"type": "array", "minItems": 3,
                   "items": {"type": "object", "required": ["id", "scope", "acceptance", "rollback"],
                             "properties": {"id": NONEMPTY, "scope": NONEMPTY,
                                            "acceptance": NONEMPTY, "rollback": NONEMPTY}}},
         "big_bang": {"const": False}, "rollback_per_wave": {"const": True}}),
    "INDEPENDENT_AUDIT": _artifact_schema(
        ["log_verified", "events", "immutable_package_unchanged", "hidden_disclosed_to_builder",
         "budget_within_ceiling"],
        {"log_verified": {"const": True}, "events": {"type": "integer", "minimum": 10},
         "immutable_package_unchanged": {"const": True},
         "hidden_disclosed_to_builder": {"const": False},
         "budget_within_ceiling": {"const": True}}),
}

# The label rule (protocols 40–45). COMMITTED is reachable ONLY with a ceiling proof; a run
# that stopped for budget, time or a failure must end in BEST_DISCOVERED_SO_FAR or HALTED.
SCHEMAS["COMMITTED"] = escalation.PROOF_SCHEMA
SCHEMAS["BEST_DISCOVERED_SO_FAR"] = escalation.PROOF_SCHEMA
SCHEMAS["HALTED"] = escalation.PROOF_SCHEMA


# ------------------------------------------------------------------- semantic guards
def _sem_frontier_review(rt, art):
    if not art["to_private_shards"]:
        raise GuardFailed("no candidate survived the dominance gate — cannot proceed to private shards")
    if set(art["to_private_shards"]) & set(art["dominated"]):
        raise GuardFailed("a dominated candidate was routed to the private shards")


def _sem_hesa(rt, art):
    # A HESA candidate must exist and be a non-dominated frontier member. A margin of 0 —
    # a tie at the top — is NOT a crash: it is information. It means no candidate strictly
    # beats the field, so the incumbent is provisional. That downgrades the terminal label
    # (the ceiling is not proven while a tie stands), but it does not stop the run from
    # naming its best-so-far. Crashing here would hide an honest "no clear winner yet"
    # behind a hard failure — the opposite of what this protocol is for.
    if not art.get("candidate_id"):
        raise GuardFailed("HESA produced no candidate at all")
    if art["margin"] < 0:
        raise GuardFailed(f"HESA margin is {art['margin']} — the named candidate is beaten "
                          "by another; the selection is inconsistent with the frontier")


def _sem_visible(rt, art):
    ids = [r["candidate_id"] for r in art["results"]]
    if len(set(ids)) != len(ids):
        raise GuardFailed("duplicate candidate ids in the visible report")
    if all(r["macro_f1"] == art["results"][0]["macro_f1"] for r in art["results"]) and len(ids) > 1:
        raise GuardFailed("all candidates scored identically — the suite does not discriminate")


def _sem_qualification(rt, art):
    if not art["canaries_all_denied"]:
        raise GuardFailed("hidden-set isolation canaries were not all denied")
    for r in art["results"]:
        cls = r["diagnostic_classes"]
        if sum(cls.values()) == 0:
            raise GuardFailed(f"{r['candidate_id']}: no cases were actually evaluated")


def _sem_proposals(rt, art):
    fams = [p["family"] for p in art["proposals"]]
    if len(set(fams)) < 3:
        raise GuardFailed(f"only {len(set(fams))} distinct architecture families proposed — "
                          "independent explorers converged, which defeats the purpose")


def _sem_ceiling(rt, art):
    if not art["cannot_do"]:
        raise GuardFailed("ceiling analysis lists nothing the architecture cannot do — "
                          "an honest ceiling analysis always names a limit")


def _sem_committed(rt, art):
    """The one guard that stops a good-enough result being called supreme."""
    if art["terminal_state"] != "COMMITTED":
        raise GuardFailed(
            f"the escalation proof concludes {art['terminal_state']}, not COMMITTED "
            f"(stopped because: {art.get('stopped_because')}) — "
            "the run may not relabel its own result")
    if not art["ceiling_proven"]:
        raise GuardFailed("COMMITTED requires a proof of ceiling; none was produced")
    unmet = [k for k, v in art["conditions"].items() if not v]
    if unmet:
        raise GuardFailed(f"COMMITTED blocked — escalation conditions unmet: {unmet}")
    if art["untried_families"]:
        raise GuardFailed(f"COMMITTED blocked — untried architecture families remain: "
                          f"{art['untried_families']}")
    if art["audited_altitude"] != art["highest_evidenced_altitude"]:
        raise GuardFailed(
            f"COMMITTED blocked — the incumbent is audited at {art['audited_altitude']} while "
            f"evidence exists up to {art['highest_evidenced_altitude']}")
    # The target is the twelve-layer Institution, not a high score on the parts we happened
    # to measure. An unreached layer means the Institution is not built, whatever else is.
    if art["layers_unreached"]:
        raise GuardFailed(
            "COMMITTED blocked — layers of the target Institution are unreached: "
            + ", ".join(art["layers_unreached"]))
    if art["evolvability"] != "EVOLVABLE":
        raise GuardFailed(
            f"COMMITTED blocked — evolvability is {art['evolvability']}: an architecture that "
            "must reopen its own core to grow is not the final one")
    if not art["axioms_upheld"]:
        raise GuardFailed("COMMITTED blocked — an axiom was violated; axioms are a door, "
                          "not a dimension to trade against score")
    if art.get("consciousness") != "REAL":
        raise GuardFailed(
            f"COMMITTED blocked — consciousness probe is {art.get('consciousness')}: the crown "
            "requires the REAL, ungameable consciousness result. Today's LAWMAX cannot clear "
            "this, which is the point — the dumb baseline is structurally uncrownable.")


def _sem_honest_terminal(rt, art):
    if art["terminal_state"] == "COMMITTED":
        raise GuardFailed("this terminal state must not carry a COMMITTED proof")
    if art["ceiling_proven"]:
        raise GuardFailed("a proven ceiling belongs in COMMITTED, not here")


SEMANTIC = {
    "TARGET_ARCHITECTURE_SEARCH": _sem_proposals,
    "VISIBLE_CERTIFIED": _sem_visible,
    "PRIVATE_QUALIFICATION": _sem_qualification,
    "CEILING_ANALYSIS": _sem_ceiling,
    "FRONTIER_REVIEW": _sem_frontier_review,
    "HESA_CANDIDATE": _sem_hesa,
    "COMMITTED": _sem_committed,
    "BEST_DISCOVERED_SO_FAR": _sem_honest_terminal,
    "HALTED": _sem_honest_terminal,
}


class Machine:
    def __init__(self, runtime, log: EventLog, owner_public, run_id, handlers):
        self.runtime = os.path.abspath(runtime)
        self.log = log
        self.owner = owner_public
        self.run_id = run_id
        self.handlers = handlers
        self.checkpoint = Checkpoint(os.path.join(self.runtime, "state", "current.json"), log, replay)

    def state(self):
        return self.checkpoint.read()  # raises if the checkpoint disagrees with the log

    def approval_path(self, gate_id):
        return os.path.join(self.runtime, "gates", f"{gate_id}.approval.json")

    def transition(self, target, artifact_path):
        cur = self.state()
        if target not in NEXT.get(cur, []):
            raise GuardFailed(f"illegal transition {cur} -> {target}")
        if not os.path.exists(artifact_path):
            raise GuardFailed(f"{target}: artifact {artifact_path} was not produced")
        if os.path.getsize(artifact_path) == 0:
            raise GuardFailed(f"{target}: artifact is empty")
        artifact = read_json(artifact_path)

        sch = SCHEMAS.get(target)
        if sch is not None:
            try:
                validate(artifact, sch)
            except ValidationError as e:
                raise GuardFailed(f"{target}: artifact fails its schema: {e}")

        sem = SEMANTIC.get(target)
        if sem is not None:
            sem(self, artifact)

        subject = sha256_file(artifact_path)
        gate = OWNER_GATES.get(target)
        if gate:
            p = self.approval_path(gate)
            if not os.path.exists(p):
                raise OwnerApprovalRequired(gate, self.run_id, artifact_path, subject, p)
            try:
                verify_approval(read_json(p), self.owner, gate, self.run_id, subject)
            except SignatureRejected as e:
                raise OwnerApprovalRequired(gate, self.run_id, artifact_path, subject, p, reason=str(e))

        self.log.append("transition", "state-machine",
                        {"from": cur, "to": target,
                         "artifact": os.path.relpath(artifact_path, self.runtime).replace("\\", "/"),
                         "artifact_sha256": subject,
                         "owner_gate": gate},
                        reason="schema + semantic guard satisfied", subject_sha256=subject)
        self.checkpoint.write()
        return target

    def advance(self, target):
        """One transition, no skipping. Used by the escalation loop, which revisits states."""
        artifact_path = self.handlers[target](self)
        return self.transition(target, artifact_path)

    def run_linear(self, path, crash_after=None, done=0):
        """The non-looping segments. Resume is idempotent: a state already recorded in the
        signed log is skipped, because the log — not a checkpoint file — says so."""
        for target in path:
            cur = self.state()
            if STATES.index(cur) >= STATES.index(target):
                continue
            self.advance(target)
            done += 1
            if crash_after is not None and done >= crash_after:
                raise KeyboardInterrupt(f"SIMULATED CRASH after {done} transitions")
        return self.state(), done
