"""The eleven owner decisions of protocol 24, as a frozen and SIGNED precondition.

v2.0 listed them in prose and launched anyway. Here they are a schema with eleven
required entries, signed by the owner key. `--launch` loads them before anything else;
an unsigned, incomplete or altered decision file stops the run before a single call.

Because the budget ceiling, the stagnation definition and the challenger reserve all
come from this file, "we forgot to decide" can no longer become "we spent the money".
"""
import os

from .canonical import read_json, sha256_obj
from .schema import ValidationError, validate
from .signing import SignatureRejected

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

BUDGET_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object", "additionalProperties": False,
    "required": ["eur", "tokens", "calls", "wall_clock_days", "successor_reserve_fraction"],
    "properties": {
        "eur": {"type": "number", "exclusiveMinimum": 0},
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
        # How hard the extraction pushes the builder. Owner-controlled, budget-bounded.
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
        validate(p["decisions"]["D01_BUDGET"]["value"], BUDGET_SCHEMA)
        validate(p["decisions"]["D07_ACCEPTANCE_THRESHOLDS"]["value"], THRESHOLDS_SCHEMA)
    except ValidationError as e:
        raise DecisionsRejected(f"budget/thresholds unusable: {e}")
    undecided = [k for k, v in p["decisions"].items() if not v.get("decided")]
    if undecided:
        raise DecisionsRejected(f"undecided: {undecided}")
    return OwnerDecisions(p)
