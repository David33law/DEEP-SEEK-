"""Role prompts and the response schema each role is held to.

Every reply is validated before it can become an artifact, so a role that answers with
prose, with a partial object, or with a confident claim it was not asked for, produces a
StructuredOutputRejected rather than a state transition.
"""

MASTER_SYSTEM = """You are operating inside the LAWMAX-Ω experimental protocol, v2.1.

Binding rules, in order of authority:
1. Never claim progress you cannot evidence. "I do not know" is an accepted, expected answer.
2. Never produce a result that is merely adequate. If a strictly higher conception exists,
   name it — even when it is more work, and even when it invalidates your previous answer.
3. Every factual claim about the LAWMAX corpus must cite the file and byte range it came from.
4. You never grade yourself. Your output is measured against sealed cases you will not see.
5. Reply with exactly one JSON object matching the schema you are given. No prose outside it.
"""

INGESTION_SCHEMA_REF = "see lawmax21.coverage.INGESTION_SCHEMA"

PROPOSAL_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object", "additionalProperties": False,
    "required": ["family", "trusted_boundary", "mechanisms", "falsifiable_predictions",
                 "why_not_higher", "altitude_claimed"],
    "properties": {
        "family": {"type": "string", "minLength": 3, "maxLength": 80},
        "trusted_boundary": {"type": "string", "minLength": 10},
        "mechanisms": {"type": "array", "minItems": 1, "maxItems": 12,
                       "items": {"type": "object", "additionalProperties": False,
                                 "required": ["name", "purpose", "capability_slices"],
                                 "properties": {"name": {"type": "string", "minLength": 3},
                                                "purpose": {"type": "string", "minLength": 10},
                                                "capability_slices": {"type": "array", "minItems": 1}}}},
        "falsifiable_predictions": {"type": "array", "minItems": 1, "maxItems": 10,
                                    "items": {"type": "string", "minLength": 15}},
        "why_not_higher": {"type": "string", "minLength": 20},
        "altitude_claimed": {"enum": ["L0","L1","L2","L3","L4","L5","L6","L7","L8","L9","L10","L11","L12"]},
        "citations": {"type": "array", "items": {"type": "string"}},
    },
}

BUILD_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object", "additionalProperties": False,
    "required": ["candidate_id", "family", "mechanism", "files"],
    "properties": {
        "candidate_id": {"type": "string", "pattern": "^[A-Za-z0-9_-]{3,40}$"},
        "family": {"type": "string", "minLength": 3},
        "mechanism": {"type": "string", "minLength": 3},
        "rationale": {"type": "string"},
        "files": {"type": "array", "minItems": 1, "maxItems": 20,
                  "items": {"type": "object", "additionalProperties": False,
                            "required": ["path", "content"],
                            "properties": {"path": {"type": "string", "minLength": 1, "maxLength": 200},
                                           "content": {"type": "string", "maxLength": 400000}}}},
    },
}

CEILING_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object", "additionalProperties": False,
    "required": ["cannot_do", "bottleneck", "next_altitude", "evidence", "candidate_families_untried"],
    "properties": {
        "cannot_do": {"type": "array", "minItems": 1, "maxItems": 20,
                      "items": {"type": "string", "minLength": 10}},
        "bottleneck": {"type": "string", "minLength": 10},
        "next_altitude": {"enum": ["L0","L1","L2","L3","L4","L5","L6","L7","L8","L9","L10","L11","L12"]},
        "evidence": {"type": "array", "minItems": 1, "items": {"type": "string", "minLength": 5}},
        "candidate_families_untried": {"type": "array", "items": {"type": "string"}},
    },
}

RECONSTRUCTION_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object", "additionalProperties": False,
    "required": ["items", "unknown"],
    "properties": {
        "items": {"type": "array", "minItems": 1, "maxItems": 400,
                  "items": {"type": "object", "additionalProperties": False,
                            "required": ["path", "status", "evidence"],
                            "properties": {"path": {"type": "string", "minLength": 1},
                                           "status": {"type": "string", "minLength": 3},
                                           "kind": {"type": "string"},
                                           "evidence": {"type": "string", "minLength": 5}}}},
        "unknown": {"type": "array", "items": {"type": "string"}},
    },
}

HISTORY_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object", "additionalProperties": False,
    "required": ["studies", "lessons"],
    "properties": {
        "studies": {"type": "array", "minItems": 3, "items": {"type": "string", "minLength": 2}},
        "lessons": {"type": "array", "minItems": 3, "maxItems": 30,
                    "items": {"type": "object", "additionalProperties": False,
                              "required": ["lesson", "source"],
                              "properties": {"lesson": {"type": "string", "minLength": 10},
                                             "source": {"type": "string", "minLength": 3}}}},
    },
}

SYNTHESIS_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object", "additionalProperties": False,
    "required": ["useful", "decorative", "refuted"],
    "properties": {
        "useful": {"type": "array", "items": {"type": "string"}},
        "decorative": {"type": "array", "items": {"type": "string"}},
        "refuted": {"type": "array", "items": {"type": "string"}},
        "notes": {"type": "string"},
    },
}

MIGRATION_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object", "additionalProperties": False,
    "required": ["waves", "big_bang", "rollback_per_wave"],
    "properties": {
        "big_bang": {"const": False},
        "rollback_per_wave": {"const": True},
        "waves": {"type": "array", "minItems": 3, "maxItems": 20,
                  "items": {"type": "object", "additionalProperties": False,
                            "required": ["id", "scope", "acceptance", "rollback"],
                            "properties": {"id": {"type": "string", "minLength": 1},
                                           "scope": {"type": "string", "minLength": 10},
                                           "acceptance": {"type": "string", "minLength": 10},
                                           "rollback": {"type": "string", "minLength": 10}}}},
    },
}

AUDIT_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object", "additionalProperties": False,
    "required": ["checks", "unresolved"],
    "properties": {
        "checks": {"type": "object", "minProperties": 8},
        "unresolved": {"type": "array", "items": {"type": "string"}},
    },
}

ANTI_SATISFICING_CHECKS = [
    "was a strictly simpler design tested and did it lose on measured evidence?",
    "was a radical challenger from a different family built and measured?",
    "does every retained mechanism change the score when ablated?",
    "is any mechanism retained only because it was proposed first?",
    "were the hidden results obtained without the candidate seeing labels?",
    "is any claimed capability unmeasured by the sealed suite?",
    "does the incumbent's audited altitude match its declared altitude?",
    "is there a named architecture family that was never attempted?",
]


def build_prompt(role, task, context_blocks, schema_hint):
    parts = [f"ROLE: {role}", "", "TASK:", task, ""]
    for name, body in context_blocks:
        parts += [f"--- CONTEXT: {name} ---", body, ""]
    parts += ["Reply with exactly one JSON object satisfying this schema:", schema_hint]
    return "\n".join(parts)
