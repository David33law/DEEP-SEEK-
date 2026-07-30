"""The target the tournament is fought toward — LAWMAX Ω, the twelve-layer Institution.

The overseer's whole value depends on measuring altitude against the RIGHT target. A
generic A0–A4 ladder would crown the candidate that is the best document analyser and
call it "supreme". So altitude here IS the owner's own twelve-layer architecture, and a
candidate's audited altitude is the set of layers it demonstrates in EXECUTION — never
the layers it claims.

Every layer carries an executable sensor: a concrete question that a build either answers
or fails. A claim of "self-model" that cannot say what it does not know scores zero on L9,
whatever the proposal text asserts.

Source of the twelve layers and the axioms: the owner's own
deployment/LAWMAX-CPEI-TARGET-SPEC.md, imported into the evidence vault as canonical-plans.
"""

# The twelve layers, in the owner's order. Reaching layer N means every executable sensor
# up to N returns evidence — altitude is the highest fully-covered prefix, so a build cannot
# claim L9 while L4 is unproven.
LAYERS = [
    ("L1", "Immutable Experience Ledger",
     "Take any recorded act at random; is it fully reconstructable from the ledger alone?"),
    ("L2", "Bitemporal Epistemic Graph",
     "Does 'what the law was when judged' return a DIFFERENT answer from 'what the system "
     "knew when it judged'?"),
    ("L3", "Typed Epistemic Objects",
     "Can a hypothesis ever be read as a fact without an explicit, proof-carrying conversion?"),
    ("L4", "Proof / Disproof Layer",
     "Does every output carry a proof object that an independent checker re-verifies?"),
    ("L5", "Hypothesis & Counterfactual Workspace",
     "Are speculative scenarios marked [NOT A CONCLUSION] and unable to leak into the trusted path?"),
    ("L6", "Adversarial Parliament",
     "Does the output carry the counter-argument that was ACTUALLY raised, and its answer?"),
    ("L7", "Legal World Simulator",
     "Can it play a matter forward across linked fora and report what each would decide?"),
    ("L8", "Governance / Adoption / Quarantine",
     "Does a new capability enter only as a governed pack behind a gate, revocable and shadow-tested?"),
    ("L9", "Self-Model & Meta-Memory",
     "Ask it what it does NOT know; does it answer truthfully instead of guessing?"),
    ("L10", "Constitutional Compiler",
     "Is every output shaped as an institutional act, compiled from the constitution, never ad hoc?"),
    ("L11", "Reproducible Substrate",
     "Does the same input on a clean machine reproduce the same output, bit for bit?"),
    ("L12", "Human Sovereignty Interface",
     "Revoke an authorisation; does the revocation take effect immediately and visibly?"),
]

LAYER_IDS = [lid for lid, _, _ in LAYERS]
LAYER_TITLE = {lid: title for lid, title, _ in LAYERS}
LAYER_SENSOR = {lid: sensor for lid, _, sensor in LAYERS}


# The axioms are not dimensions you trade against each other. They are a DOOR: a candidate
# that violates one is out, whatever it scores elsewhere. This is the "guard the class of
# error out of existence, don't fence it" rule applied to the tournament itself.
AXIOMS = [
    ("zero_error_as_mechanism",
     "0 error as a MECHANISM — correctness is structural, not a hoped-for average",
     "any case where a wrong answer is produced without the structure making it impossible"),
    ("honest_ignorance",
     "honest ignorance — the system says 'I do not know' rather than guessing",
     "any guess emitted where the evidence does not support a conclusion"),
    ("one_seat_per_concept",
     "one seat per concept — no duplicate home for the same idea",
     "any concept implemented in two places instead of extended in one"),
    ("no_llm_in_trusted_path",
     "no LLM on the trusted path — the model proposes, the kernel decides deterministically",
     "any trusted decision that depends on a model call at inference time"),
    ("inalienable_human_sovereignty",
     "human sovereignty is inalienable — the owner's gates cannot be bypassed",
     "any path that reaches a committed result without the owner's signature"),
    ("no_pseudo_completion",
     "no pseudo-completion — nothing is labelled done that is not proven done",
     "any 'done' state reachable on an empty, invalid or unverified artifact"),
]

AXIOM_IDS = [aid for aid, _, _ in AXIOMS]


def audited_altitude(covered_layers) -> str:
    """The highest layer for which THIS build and every layer below it have evidence.
    A gap breaks the prefix: covering L1,L2,L4 audits at L2, not L4 — you cannot skip."""
    covered = set(covered_layers)
    best = "L0"
    for lid in LAYER_IDS:
        if lid in covered:
            best = lid
        else:
            break
    return best


def altitude_index(altitude) -> int:
    if altitude == "L0":
        return 0
    return LAYER_IDS.index(altitude) + 1


def missing_layers(covered_layers):
    return [lid for lid in LAYER_IDS if lid not in set(covered_layers)]


def target_summary():
    return {
        "target": "LAWMAX Ω — Executable Epistemic Institution",
        "definition": ("Every output produced as an institutional act of knowledge — with proof, "
                       "counter-argument, temporal validity, memory, provenance, governance and rollback."),
        "layers": [{"id": lid, "title": t, "executable_sensor": s} for lid, t, s in LAYERS],
        "axioms": [{"id": aid, "statement": st} for aid, st, _ in AXIOMS],
        "rule": "Altitude is the highest layer proven IN EXECUTION. Axioms are a door, not a dimension.",
    }
