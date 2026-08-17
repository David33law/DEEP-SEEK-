"""Strict executable-source schema shared by semantic and specialized builders.

Specialized builders previously reused a semantic schema whose accepted path surface was implicit.
This module makes the complete source boundary explicit: one source file, one of the six declared
candidate interfaces, no extra response fields and a bounded source size. Downstream installers still
require the exact filename appropriate to their role, so accepting the union here cannot substitute
one interface for another.
"""
from . import observatory_roles
from . import roles

_ALLOWED_PATHS = [
    "candidate.py", "systems_candidate.py", "distributed_candidate.py",
    "scale_candidate.py", "formal_candidate.py", "interoperability_candidate.py"]

BUILD_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object", "additionalProperties": False,
    "required": ["candidate_id", "family", "mechanism", "rationale", "files"],
    "properties": {
        "candidate_id": {"type": "string", "minLength": 2, "maxLength": 160},
        "family": {"type": "string", "minLength": 3, "maxLength": 4000},
        "mechanism": {"type": "string", "minLength": 3, "maxLength": 12000},
        "rationale": {"type": "string", "minLength": 20, "maxLength": 60000},
        "files": {
            "type": "array", "minItems": 1, "maxItems": 1,
            "items": {
                "type": "object", "additionalProperties": False,
                "required": ["path", "content"],
                "properties": {
                    "path": {"enum": list(_ALLOWED_PATHS)},
                    "content": {"type": "string", "minLength": 20,
                                "maxLength": 2000000}}}}}}


def install(_ctx, handlers):
    observatory_roles.BUILD_SCHEMA = BUILD_SCHEMA
    roles.BUILD_SCHEMA = BUILD_SCHEMA
    return dict(handlers)
