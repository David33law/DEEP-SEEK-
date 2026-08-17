"""Role schemas whose meaning differs for the whole-system Observatory profile."""

# Whole-system architecture descriptions are intentionally allowed to be rich. The evaluator
# proves behaviour later; this schema should enforce structure, not compress a national-scale
# architecture into arbitrary few-hundred-character fields.
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
        "altitude_claimed": {"enum": ["L0","L1","L2","L3","L4","L5","L6","L7","L8","L9","L10","L11","L12"]},
        "citations": {"type": "array", "maxItems": 128,
                      "items": {"type": "string", "maxLength": 4000}},
    },
}
