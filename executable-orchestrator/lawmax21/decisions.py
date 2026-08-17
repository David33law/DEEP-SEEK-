"""The eleven owner decisions of protocol 24, frozen and signed before any paid call.

Budget decisions support the historical LAWMAX EUR contract and a currency-explicit contract used
by provider profiles. A currency-explicit budget carries its provider price schedule inside the
owner-signed payload so accounting rules cannot drift silently after the ceremony.
"""
import os

from .canonical import read_json, sha256_obj
from .schema import ValidationError, validate

DECISION_IDS = [
    "D01_BUDGET", "D02_HIDDEN_SET_AUTHORITY", "D03_RUNTIME_DIRECTION",
    "D04_PACKAGE_AUTHOR_REPO_ACCESS", "D05_PII_FIXTURE_POLICY", "D06_GATE_CADENCE",
    "D07_ACCEPTANCE_THRESHOLDS", "D08_OFFMACHINE_BACKUP", "D09_ROW0_TARGET",
    "D10_CS01_FIXTURE_LICENCE", "D11_CHALLENGER_RESERVE",
]

DECISIONS_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "additionalProperties": False,
    "required": ["payload", "signature"],
    "properties": {
        "signature": {"type": "string", "pattern": "^[0-9a-f]{128}$"},
        "payload": {
            "type": "object",
            "additionalProperties": False,
            "required": ["kind", "run_id", "signer_key_id", "protocol_version", "utc", "decisions"],
            "properties": {
                "kind": {"const": "lawmax.owner-decisions"},
                "run_id": {"type": "string", "minLength": 1},
                "signer_key_id": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
                "protocol_version": {"type": "string"},
                "utc": {"type": "string", "minLength": 20},
                "decisions": {
                    "type": "object",
                    "required": DECISION_IDS,
                    "additionalProperties": False,
                    "propertyNames": {"enum": DECISION_IDS},
                    "patternProperties": {
                        "^D[0-9]{2}_": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["decided", "value"],
                            "properties": {
                                "decided": {"const": True},
                                "value": {},
                                "note": {"type": "string"},
                            },
                        }
                    },
                },
            },
        },
    },
}

PRICE_SCHEDULE_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object", "additionalProperties": False,
    "required": ["model", "currency", "input_cache_hit_per_mtok",
                 "input_cache_miss_per_mtok", "output_per_mtok",
                 "require_cache_split", "source", "verified_date"],
    "properties": {
        "model": {"type": "string", "minLength": 1},
        "currency": {"type": "string", "pattern": "^[A-Z]{3}$"},
        "input_cache_hit_per_mtok": {"type": "number", "minimum": 0},
        "input_cache_miss_per_mtok": {"type": "number", "minimum": 0},
        "output_per_mtok": {"type": "number", "minimum": 0},
        "require_cache_split": {"const": True},
        "source": {"type": "string", "minLength": 1},
        "verified_date": {"type": "string", "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}$"},
    },
}

BUDGET_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object", "additionalProperties": False,
    "required": ["tokens", "calls", "wall_clock_days", "successor_reserve_fraction"],
    "properties": {
        # Historical LAWMAX budget seat.
        "eur": {"type": "number", "exclusiveMinimum": 0},
        # Currency-explicit seat for new provider profiles.
        "currency": {"type": "string", "pattern": "^[A-Z]{3}$"},
        "amount": {"type": "number", "exclusiveMinimum": 0},
        "price_schedule": PRICE_SCHEDULE_SCHEMA,
        "tokens": {"type": "integer", "exclusiveMinimum": 0},
        "calls": {"type": "integer", "exclusiveMinimum": 0},
        "wall_clock_days": {"type": "integer", "exclusiveMinimum": 0},
        "successor_reserve_fraction": {"type": "number", "minimum": 0.1, "maximum": 0.6},
    },
}

THRESHOLDS_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object", "additionalProperties": False,
    "required": ["hidden_pass_rate", "min_slice_f1", "clean_runs", "ablation_min_drop",
                 "progress_min_delta", "max_stagnant_windows"],
    "properties": {
        "hidden_pass_rate": {"type": "number", "minimum": 0.5, "maximum": 1.0},
        "min_slice_f1": {"type": "number", "minimum": 0.5, "maximum": 1.0},
        "clean_runs": {"type": "integer", "minimum": 1},
        "ablation_min_drop": {"type": "number", "minimum": 0.05},
        "progress_min_delta": {"type": "number", "minimum": 0.0},
        "max_stagnant_windows": {"type": "integer", "minimum": 1},
        "best_of_n": {"type": "integer", "minimum": 1, "maximum": 8},
        "revision_rounds": {"type": "integer", "minimum": 0, "maximum": 5},
    },
}


class DecisionsRejected(Exception):
    pass


class OwnerDecisions:
    def __init__(self, payload):
        self.payload = payload
        self.d = {k: v["value"] for k, v in payload["decisions"].items()}

    @property
    def budget(self):
        return self.d["D01_BUDGET"]

    @property
    def thresholds(self):
        return self.d["D07_ACCEPTANCE_THRESHOLDS"]

    @property
    def challenger_reserve(self):
        return self.d["D11_CHALLENGER_RESERVE"]

    def summary(self):
        return {k: (v if not isinstance(v, (dict, list)) else "…structured…") for k, v in self.d.items()}

    def sha256(self):
        return sha256_obj(self.payload)


def _validate_budget_contract(b):
    legacy = "eur" in b
    explicit = all(k in b for k in ("currency", "amount", "price_schedule"))
    if legacy == explicit:
        raise DecisionsRejected(
            "budget must use exactly one monetary contract: legacy eur OR currency+amount+price_schedule")
    if explicit:
        schedule = b["price_schedule"]
        if str(b["currency"]).upper() != str(schedule["currency"]).upper():
            raise DecisionsRejected("budget currency does not match signed provider price schedule")


def load(path, owner_public, run_id):
    if not os.path.exists(path):
        raise DecisionsRejected(
            f"the eleven owner decisions are not present at {path} — "
            "protocol 24 requires them frozen and signed BEFORE any API call")
    env = read_json(path)
    try:
        validate(env, DECISIONS_SCHEMA)
    except ValidationError as e:
        raise DecisionsRejected(f"decision file malformed: {e}")
    p = env["payload"]
    if p["signer_key_id"] != owner_public.key_id:
        raise DecisionsRejected("decisions signed by a key that is not the owner's")
    if not owner_public.verify(p, env["signature"]):
        raise DecisionsRejected("decision signature does not verify — the file was altered")
    if p["run_id"] != run_id:
        raise DecisionsRejected(f"decisions are frozen for run {p['run_id']!r}, not {run_id!r}")
    try:
        b = p["decisions"]["D01_BUDGET"]["value"]
        validate(b, BUDGET_SCHEMA)
        validate(p["decisions"]["D07_ACCEPTANCE_THRESHOLDS"]["value"], THRESHOLDS_SCHEMA)
        _validate_budget_contract(b)
    except ValidationError as e:
        raise DecisionsRejected(f"budget/thresholds unusable: {e}")
    undecided = [k for k, v in p["decisions"].items() if not v.get("decided")]
    if undecided:
        raise DecisionsRejected(f"undecided: {undecided}")
    return OwnerDecisions(p)
