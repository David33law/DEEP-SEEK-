"""Role schemas whose meaning differs for the whole-system Observatory profile."""

PROPOSAL_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object", "additionalProperties": False,
    "required": ["family", "trusted_boundary", "mechanisms", "falsifiable_predictions",
                 "why_not_higher", "altitude_claimed"],
    "properties": {
        "family": {"type": "string", "minLength": 3, "maxLength": 120},
        "trusted_boundary": {"type": "string", "minLength": 20, "maxLength": 4000},
        # For whole-system candidates the mechanism field names the architecture-level
        # composition, not a list of micro-capability objects. Detailed purpose/coverage lives
        # in the trusted-boundary narrative and falsifiable predictions and is later proven by
        # executable replay, not trusted from this proposal.
        "mechanisms": {"type": "array", "minItems": 1, "maxItems": 12,
                       "items": {"type": "string", "minLength": 3, "maxLength": 300}},
        "falsifiable_predictions": {"type": "array", "minItems": 3, "maxItems": 20,
                                    "items": {"type": "string", "minLength": 15}},
        "why_not_higher": {"type": "string", "minLength": 20},
        "altitude_claimed": {"enum": ["L0","L1","L2","L3","L4","L5","L6","L7","L8","L9","L10","L11","L12"]},
        "citations": {"type": "array", "items": {"type": "string"}},
    },
}
