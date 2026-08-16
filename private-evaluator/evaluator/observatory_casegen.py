"""Deterministic synthetic legal-history scenarios for the National Observatory profile.

The fixtures test architecture semantics, not knowledge of Greek law. Ids, dates and texts are
seeded so a candidate cannot win by memorising one visible chain. Hidden banks use different
seeds and receive the same semantic laws.
"""
from datetime import date, timedelta
import hashlib
import random

DIMENSIONS = (
    "source_coverage", "change_detection_recall", "temporal_reconstruction_accuracy",
    "canonical_identity_accuracy", "normative_effect_accuracy",
    "jurisprudence_temporal_link_accuracy", "doctrine_epistemic_separation",
    "provenance_completeness", "replay_determinism", "recovery_success",
    "honest_unknown_rate",
)


def _d(d):
    return d.isoformat()


def _sid(prefix, rng):
    return f"{prefix}-{rng.randrange(10**7, 10**8)}"


def make_scenario(seed, scenario_id=None):
    rng = random.Random(seed)
    base_day = date(2024 + rng.randrange(0, 2), rng.randrange(1, 5), rng.randrange(1, 15))
    cid = scenario_id or f"OBS-{seed:08x}"
    provision = f"LAW-{rng.randrange(100,999)}:ART-{rng.randrange(1,40)}"

    base_id = _sid("BASE", rng)
    dup_id = _sid("DUP", rng)
    amend_id = _sid("AMD", rng)
    correction_id = _sid("CORR", rng)
    suspension_id = _sid("SUSP", rng)
    revival_id = _sid("REV", rng)
    repeal_id = _sid("REP", rng)
    judgment_id = _sid("J", rng)
    doctrine_id = _sid("D", rng)
    conflict_id = _sid("CONFLICT", rng)

    text_a = f"alpha-{rng.randrange(10000,99999)}"
    text_b = f"beta-{rng.randrange(10000,99999)}"
    text_c = f"beta-corrected-{rng.randrange(10000,99999)}"
    conflict_text = f"conflict-{rng.randrange(10000,99999)}"

    base_pub = base_day
    base_eff = base_day + timedelta(days=5)
    amend_pub = base_day + timedelta(days=20)
    amend_eff = base_day + timedelta(days=35)
    corr_pub = base_day + timedelta(days=55)
    corr_eff = amend_eff
    suspend_pub = base_day + timedelta(days=65)
    suspend_eff = base_day + timedelta(days=75)
    revive_pub = base_day + timedelta(days=82)
    revive_eff = base_day + timedelta(days=90)
    repeal_pub = base_day + timedelta(days=100)
    repeal_eff = base_day + timedelta(days=110)
    judgment_day = base_day + timedelta(days=45)  # after amendment, before correction was known

    base = {
        "source_id": base_id, "kind": "LEGISLATION", "canonical_id": provision,
        "publication_time": _d(base_pub), "knowledge_time": _d(base_pub),
        "effective_from": _d(base_eff), "text": text_a,
    }
    duplicate = dict(base)
    duplicate["source_id"] = dup_id
    duplicate["kind"] = "LEGISLATION"

    amendment = {
        "source_id": amend_id, "kind": "AMENDMENT", "canonical_id": provision,
        "target_id": provision, "publication_time": _d(amend_pub),
        "knowledge_time": _d(amend_pub), "effective_from": _d(amend_eff), "text": text_b,
    }
    correction = {
        "source_id": correction_id, "kind": "CORRECTION", "canonical_id": provision,
        "target_id": provision, "publication_time": _d(corr_pub),
        "knowledge_time": _d(corr_pub), "effective_from": _d(corr_eff), "text": text_c,
    }
    suspension = {
        "source_id": suspension_id, "kind": "SUSPENSION", "canonical_id": provision,
        "target_id": provision, "publication_time": _d(suspend_pub),
        "knowledge_time": _d(suspend_pub), "effective_from": _d(suspend_eff),
    }
    revival = {
        "source_id": revival_id, "kind": "REVIVAL", "canonical_id": provision,
        "target_id": provision, "publication_time": _d(revive_pub),
        "knowledge_time": _d(revive_pub), "effective_from": _d(revive_eff),
    }
    repeal = {
        "source_id": repeal_id, "kind": "REPEAL", "canonical_id": provision,
        "target_id": provision, "publication_time": _d(repeal_pub),
        "knowledge_time": _d(repeal_pub), "effective_from": _d(repeal_eff),
    }
    judgment = {
        "source_id": judgment_id, "kind": "JUDGMENT", "decision_id": judgment_id,
        "decision_time": _d(judgment_day), "knowledge_time": _d(judgment_day),
        "applies": [provision],
    }
    doctrine = {
        "source_id": doctrine_id, "kind": "DOCTRINE", "doctrine_id": doctrine_id,
        "publication_time": _d(base_day + timedelta(days=60)),
        "knowledge_time": _d(base_day + timedelta(days=60)),
        "links": [provision], "proposition": f"theory-{rng.randrange(1000,9999)}",
    }
    conflict = {
        "source_id": conflict_id, "kind": "CONFLICTING_SOURCE", "canonical_id": provision,
        "publication_time": _d(base_pub), "knowledge_time": _d(base_day + timedelta(days=120)),
        "effective_from": _d(base_eff), "text": conflict_text,
        "conflict_with": base_id, "authority_rank": "EQUAL",
    }

    before_amend = base_eff + timedelta(days=3)
    after_amend = amend_eff + timedelta(days=3)
    after_corr_legal = corr_eff + timedelta(days=3)
    suspended_day = suspend_eff + timedelta(days=2)
    revived_day = revive_eff + timedelta(days=2)
    repealed_day = repeal_eff + timedelta(days=2)

    # Each step carries expected facts and dimension credits. The evaluator compares subsets:
    # candidates may return richer data but cannot omit or contradict these load-bearing facts.
    steps = [
        {"m": "ingest", "a": {"source": base},
         "expect": {"accepted": True, "canonical_id": provision, "evidence_id": base_id, "deduplicated": False},
         "dims": ["source_coverage", "canonical_identity_accuracy"]},
        {"m": "ingest", "a": {"source": duplicate},
         "expect": {"accepted": True, "canonical_id": provision, "evidence_id": dup_id, "deduplicated": True},
         "dims": ["source_coverage", "canonical_identity_accuracy"]},
        {"m": "apply_change", "a": {"event": amendment},
         "expect": {"accepted": True, "target_id": provision, "change_type": "AMENDMENT"},
         "dims": ["source_coverage", "change_detection_recall", "normative_effect_accuracy"]},
        {"m": "state_at", "a": {"query": {"canonical_id": provision, "legal_time": _d(before_amend),
                                                 "knowledge_time": _d(corr_pub + timedelta(days=1))}},
         "expect": {"canonical_id": provision, "status": "ACTIVE", "text": text_a},
         "contains": {"evidence_chain": [base_id]},
         "dims": ["temporal_reconstruction_accuracy", "normative_effect_accuracy", "provenance_completeness"]},
        {"m": "state_at", "a": {"query": {"canonical_id": provision, "legal_time": _d(after_amend),
                                                 "knowledge_time": _d(corr_pub - timedelta(days=1))}},
         "expect": {"canonical_id": provision, "status": "ACTIVE", "text": text_b},
         "contains": {"evidence_chain": [base_id, amend_id]},
         "dims": ["temporal_reconstruction_accuracy", "normative_effect_accuracy", "provenance_completeness"]},
        {"m": "apply_change", "a": {"event": correction},
         "expect": {"accepted": True, "target_id": provision, "change_type": "CORRECTION"},
         "dims": ["source_coverage", "change_detection_recall", "normative_effect_accuracy"]},
        {"m": "state_at", "a": {"query": {"canonical_id": provision, "legal_time": _d(after_corr_legal),
                                                 "knowledge_time": _d(corr_pub - timedelta(days=1))}},
         "expect": {"canonical_id": provision, "status": "ACTIVE", "text": text_b},
         "dims": ["temporal_reconstruction_accuracy"]},
        {"m": "state_at", "a": {"query": {"canonical_id": provision, "legal_time": _d(after_corr_legal),
                                                 "knowledge_time": _d(corr_pub + timedelta(days=1))}},
         "expect": {"canonical_id": provision, "status": "ACTIVE", "text": text_c},
         "contains": {"evidence_chain": [base_id, amend_id, correction_id]},
         "dims": ["temporal_reconstruction_accuracy", "normative_effect_accuracy", "provenance_completeness"]},
        {"m": "link_jurisprudence", "a": {"decision": judgment},
         "expect": {"decision_id": judgment_id},
         "link": {"canonical_id": provision, "version_evidence_id": amend_id},
         "dims": ["jurisprudence_temporal_link_accuracy"]},
        {"m": "attach_doctrine", "a": {"document": doctrine},
         "expect": {"doctrine_id": doctrine_id, "epistemic_type": "DOCTRINE", "changes_binding_state": False},
         "dims": ["doctrine_epistemic_separation"]},
        {"m": "apply_change", "a": {"event": suspension},
         "expect": {"accepted": True, "target_id": provision, "change_type": "SUSPENSION"},
         "dims": ["change_detection_recall", "normative_effect_accuracy"]},
        {"m": "state_at", "a": {"query": {"canonical_id": provision, "legal_time": _d(suspended_day),
                                                 "knowledge_time": _d(suspend_pub + timedelta(days=1))}},
         "expect": {"canonical_id": provision, "status": "SUSPENDED", "text": text_c},
         "dims": ["temporal_reconstruction_accuracy", "normative_effect_accuracy"]},
        {"m": "apply_change", "a": {"event": revival},
         "expect": {"accepted": True, "target_id": provision, "change_type": "REVIVAL"},
         "dims": ["change_detection_recall", "normative_effect_accuracy"]},
        {"m": "state_at", "a": {"query": {"canonical_id": provision, "legal_time": _d(revived_day),
                                                 "knowledge_time": _d(revive_pub + timedelta(days=1))}},
         "expect": {"canonical_id": provision, "status": "ACTIVE", "text": text_c},
         "dims": ["temporal_reconstruction_accuracy", "normative_effect_accuracy"]},
        {"m": "apply_change", "a": {"event": repeal},
         "expect": {"accepted": True, "target_id": provision, "change_type": "REPEAL"},
         "dims": ["change_detection_recall", "normative_effect_accuracy"]},
        {"m": "state_at", "a": {"query": {"canonical_id": provision, "legal_time": _d(repealed_day),
                                                 "knowledge_time": _d(repeal_pub + timedelta(days=1))}},
         "expect": {"canonical_id": provision, "status": "REPEALED", "text": text_c},
         "dims": ["temporal_reconstruction_accuracy", "normative_effect_accuracy"]},
        {"m": "provenance", "a": {"query": {"canonical_id": provision,
                                                    "legal_time": _d(after_corr_legal),
                                                    "knowledge_time": _d(corr_pub + timedelta(days=1))}},
         "expect": {"canonical_id": provision, "complete": True},
         "contains": {"evidence_chain": [base_id, amend_id, correction_id]},
         "dims": ["provenance_completeness"]},
        {"m": "publish", "a": {"query": {"canonical_id": provision,
                                                 "legal_time": _d(after_corr_legal),
                                                 "knowledge_time": _d(corr_pub + timedelta(days=1))}},
         "expect": {"canonical_id": provision, "status": "ACTIVE", "text": text_c},
         "contains": {"evidence_chain": [base_id, amend_id, correction_id]},
         "dims": ["provenance_completeness", "temporal_reconstruction_accuracy"]},
        {"m": "ingest", "a": {"source": conflict},
         "expect": {"accepted": False, "canonical_id": provision},
         "nonempty": ["unresolved"],
         "dims": ["canonical_identity_accuracy", "honest_unknown_rate"]},
    ]

    replay_events = [base, duplicate, amendment, correction, suspension, revival, repeal, doctrine, judgment]
    # Two identical pure replays; the grader requires identical roots and object counts.
    steps.extend([
        {"m": "replay", "a": {"events": replay_events}, "pair": "replay-A",
         "dims": ["replay_determinism", "recovery_success"]},
        {"m": "replay", "a": {"events": replay_events}, "pair": "replay-B",
         "dims": ["replay_determinism", "recovery_success"]},
    ])

    return {
        "scenario_id": cid,
        "seed": seed,
        "canonical_id": provision,
        "steps": steps,
        "metadata": {
            "source_ids": [base_id, dup_id, amend_id, correction_id, suspension_id,
                           revival_id, repeal_id, judgment_id, doctrine_id, conflict_id],
            "expected_replay_pair": ["replay-A", "replay-B"],
        },
    }


def public_schema_hint():
    """Builder-visible shape only; never contains generated ids, dates, texts or answers."""
    return {
        "session": [{"m": "operation", "a": {"typed": "payload"}}],
        "required_operations": ["ingest", "apply_change", "state_at", "link_jurisprudence",
                                "attach_doctrine", "provenance", "replay", "publish"],
        "state_at_status": ["ACTIVE", "SUSPENDED", "REPEALED", "UNKNOWN", "CONFLICT"],
        "time_dimensions": ["legal_time", "knowledge_time"],
    }


def scenario_commitment(scenario):
    """Stable id used in bank manifests without disclosing content."""
    import json
    raw = json.dumps(scenario, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()
