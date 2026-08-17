"""Role schemas for whole-system National Observatory model work.

These schemas enforce structure and boundedness, not arbitrary brevity. They are installed only by
the Observatory launcher; historical LAWMAX schema byte-semantics remain untouched.
"""

ALTITUDES = ["L0","L1","L2","L3","L4","L5","L6","L7","L8","L9","L10","L11","L12"]

PROPOSAL_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object", "additionalProperties": False,
    "required": ["family", "trusted_boundary", "mechanisms", "falsifiable_predictions",
                 "why_not_higher", "altitude_claimed"],
    "properties": {
        "family": {"type": "string", "minLength": 3, "maxLength": 2048},
        "trusted_boundary": {"type": "string", "minLength": 20, "maxLength": 30000},
        "mechanisms": {"type": "array", "minItems": 1, "maxItems": 32,
                       "items": {"type": "string", "minLength": 3, "maxLength": 12000}},
        "falsifiable_predictions": {"type": "array", "minItems": 3, "maxItems": 64,
                                    "items": {"type": "string", "minLength": 15, "maxLength": 12000}},
        "why_not_higher": {"type": "string", "minLength": 20, "maxLength": 30000},
        "altitude_claimed": {"enum": ALTITUDES},
        "citations": {"type": "array", "maxItems": 128,
                      "items": {"type": "string", "maxLength": 4000}},
    },
}

BUILD_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object", "additionalProperties": False,
    "required": ["candidate_id", "family", "mechanism", "files"],
    "properties": {
        "candidate_id": {"type": "string", "pattern": "^[A-Za-z0-9_-]{3,40}$"},
        "family": {"type": "string", "minLength": 3, "maxLength": 4000},
        "mechanism": {"type": "string", "minLength": 3, "maxLength": 20000},
        "rationale": {"type": "string", "maxLength": 50000},
        "files": {"type": "array", "minItems": 1, "maxItems": 64,
                  "items": {"type": "object", "additionalProperties": False,
                            "required": ["path", "content"],
                            "properties": {
                                "path": {"type": "string", "minLength": 1, "maxLength": 512},
                                "content": {"type": "string", "maxLength": 1800000}
                            }}},
    },
}

CEILING_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object", "additionalProperties": False,
    "required": ["cannot_do", "bottleneck", "next_altitude", "evidence", "candidate_families_untried"],
    "properties": {
        "cannot_do": {"type": "array", "minItems": 1, "maxItems": 64,
                      "items": {"type": "string", "minLength": 10, "maxLength": 20000}},
        "bottleneck": {"type": "string", "minLength": 10, "maxLength": 30000},
        "next_altitude": {"enum": ALTITUDES},
        "evidence": {"type": "array", "minItems": 1, "maxItems": 128,
                     "items": {"type": "string", "minLength": 5, "maxLength": 12000}},
        "candidate_families_untried": {"type": "array", "maxItems": 64,
                                       "items": {"type": "string", "maxLength": 4000}},
    },
}

SYNTHESIS_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object", "additionalProperties": False,
    "required": ["useful", "decorative", "refuted"],
    "properties": {
        "useful": {"type": "array", "maxItems": 128,
                   "items": {"type": "string", "maxLength": 20000}},
        "decorative": {"type": "array", "maxItems": 128,
                       "items": {"type": "string", "maxLength": 20000}},
        "refuted": {"type": "array", "maxItems": 128,
                    "items": {"type": "string", "maxLength": 20000}},
        "notes": {"type": "string", "maxLength": 50000},
    },
}

MIGRATION_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object", "additionalProperties": False,
    "required": ["waves", "big_bang", "rollback_per_wave"],
    "properties": {
        "big_bang": {"const": False},
        "rollback_per_wave": {"const": True},
        "waves": {"type": "array", "minItems": 3, "maxItems": 64,
                  "items": {"type": "object", "additionalProperties": False,
                            "required": ["id", "scope", "acceptance", "rollback"],
                            "properties": {
                                "id": {"type": "string", "minLength": 1, "maxLength": 200},
                                "scope": {"type": "string", "minLength": 10, "maxLength": 30000},
                                "acceptance": {"type": "string", "minLength": 10, "maxLength": 30000},
                                "rollback": {"type": "string", "minLength": 10, "maxLength": 30000}
                            }}},
    },
}

AUDIT_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object", "additionalProperties": False,
    "required": ["checks", "unresolved"],
    "properties": {
        "checks": {"type": "object", "minProperties": 8},
        "unresolved": {"type": "array", "maxItems": 128,
                       "items": {"type": "string", "maxLength": 12000}},
    },
}
