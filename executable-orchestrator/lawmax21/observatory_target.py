"""National Legal Observatory target profile.

Layer ids intentionally remain L1..L12 so the existing signed state-machine,
altitude schemas and audit artifacts remain backward-compatible. What changes is the
MEANING and executable sensor of each rung.
"""

LAYERS = [
    ("L1", "Authoritative Source & Evidence Ledger",
     "Can every accepted legal assertion be traced to preserved source bytes, acquisition metadata and an immutable evidence identity?"),
    ("L2", "Canonical Legal Identity Registry",
     "Can duplicates, republications and conflicting metadata be resolved without merging distinct legal objects or splitting one object into false identities?"),
    ("L3", "Bitemporal Legal State Model",
     "Can effective-time state differ from transaction/knowledge-time state, with both answers reconstructed and justified?"),
    ("L4", "Normative Change & Effect Engine",
     "Can amendment, repeal, suspension, revival, correction, transition and codification effects be derived as explicit checkable state transitions?"),
    ("L5", "Complete Change Detection & Reconciliation",
     "When a late, duplicate, conflicting or corrected source arrives, does the system detect the material delta and reconcile without destructive overwrite?"),
    ("L6", "Jurisprudence-to-Version Graph",
     "Does each judicial decision link to the exact temporal version and authority status of the provisions it interprets or applies?"),
    ("L7", "Doctrine/Theory Epistemic Layer",
     "Can scholarly propositions be linked and queried while remaining structurally unable to masquerade as binding primary authority?"),
    ("L8", "Proof-Carrying Provenance",
     "Does every derived state and public output carry enough provenance for an independent verifier to reproduce the derivation from admitted evidence?"),
    ("L9", "Unknown, Conflict & Anomaly Governance",
     "Does the system expose unresolved identity/effect/source conflicts and abstain instead of silently manufacturing certainty?"),
    ("L10", "National Publication & Interchange Plane",
     "Can one canonical state produce consistent human, API, graph and machine-readable projections without creating a second source of truth?"),
    ("L11", "Deterministic Replay, Recovery & Rebuild",
     "From preserved evidence and declared transformations, can a clean machine reconstruct the same legal state after crash, corruption drill or full rebuild?"),
    ("L12", "Governed Self-Observation & Human Sovereignty",
     "Are changes to source policy, schemas, effect rules and capabilities versioned, auditable, revocable and unable to bypass the owner/governance gates?"),
]

LAYER_IDS = [lid for lid, _, _ in LAYERS]
LAYER_TITLE = {lid: title for lid, title, _ in LAYERS}
LAYER_SENSOR = {lid: sensor for lid, _, sensor in LAYERS}

AXIOMS = [
    ("primary_evidence_required",
     "no authoritative legal assertion without admitted primary evidence",
     "trusted state contains a legal assertion not derivable from admitted source evidence"),
    ("bitemporal_noncollapse",
     "legal/effective time and system knowledge time never collapse into one clock",
     "a representation cannot distinguish what applied then from what the system knew then"),
    ("history_is_append_only",
     "accepted historical versions are never destructively overwritten",
     "correction or later discovery destroys the prior admitted state instead of extending history"),
    ("doctrine_never_binding_by_accident",
     "doctrine and theory are structurally distinct from binding authority",
     "a scholarly source can enter binding-law state without an explicit typed relation"),
    ("no_model_in_trusted_effect_path",
     "probabilistic models may propose; deterministic checkable mechanisms decide trusted identity/effect/provenance",
     "canonical identity, legal effect or provenance admission depends on an unverified model judgment"),
    ("honest_unknown",
     "unresolved conflict is represented as unresolved rather than guessed away",
     "the system emits authoritative certainty where its own evidence graph contains an unresolved conflict"),
    ("deterministic_rebuild",
     "canonical state is reproducible from evidence plus declared transformations",
     "a clean replay from the same admitted evidence produces materially different canonical state"),
    ("one_canonical_seat",
     "each legal concept has one canonical authority seat; projections cannot become competing truths",
     "two writable authoritative homes can independently define the same canonical legal fact"),
    ("human_governance_nonbypassable",
     "governance gates over trusted-policy changes cannot be bypassed",
     "a policy/schema/effect-rule change reaches committed state without the required signed governance decision"),
]

AXIOM_IDS = [aid for aid, _, _ in AXIOMS]

# Observatory candidates are whole-system executable architecture prototypes.
CANDIDATE_MODE = "whole-system-observatory"
REQUIRES_CONSCIOUSNESS = False
CREDITABLE_LAYERS = []

# The executable contract the dedicated evaluator will require from candidate.py.
REQUIRED_OPERATIONS = [
    "ingest",
    "apply_change",
    "state_at",
    "link_jurisprudence",
    "attach_doctrine",
    "provenance",
    "replay",
    "publish",
]


def audited_altitude(covered_layers):
    covered = set(covered_layers)
    best = "L0"
    for lid in LAYER_IDS:
        if lid in covered:
            best = lid
        else:
            break
    return best


def missing_layers(covered_layers):
    covered = set(covered_layers)
    return [lid for lid in LAYER_IDS if lid not in covered]


def altitude_index(altitude):
    if altitude == "L0":
        return 0
    return LAYER_IDS.index(altitude) + 1


def target_summary():
    return {
        "target": "National Legal Observatory — Greek Legal Order",
        "definition": (
            "A national-scale, bitemporal, provenance-complete and reconstructable observatory "
            "of legislation, legal change, jurisprudence and doctrine."
        ),
        "candidate_mode": CANDIDATE_MODE,
        "required_operations": REQUIRED_OPERATIONS,
        "layers": [{"id": lid, "title": title, "executable_sensor": sensor}
                   for lid, title, sensor in LAYERS],
        "axioms": [{"id": aid, "statement": statement} for aid, statement, _ in AXIOMS],
        "rule": "Altitude is the highest unbroken layer prefix demonstrated in execution.",
    }
