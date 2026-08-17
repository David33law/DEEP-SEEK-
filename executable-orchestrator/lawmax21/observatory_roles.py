"""Role schemas for whole-system National Observatory model work.

Architecture diversity is classified through controlled structural classes. Free-form ``detail``
explains a choice but cannot buy design-space distance merely through synonyms. This prevents
"append-only journal" and "hash-chained ledger" from counting as distinct families unless they
actually choose different load-bearing classes.
"""

ALTITUDES = ["L0","L1","L2","L3","L4","L5","L6","L7","L8","L9","L10","L11","L12"]

GENOME_FIELDS = [
    "canonical_authority_seat",
    "evidence_primitive",
    "identity_model",
    "state_derivation_model",
    "temporal_model",
    "normative_effect_model",
    "consistency_commit_model",
    "replication_distribution_model",
    "trusted_core_topology",
    "provenance_proof_model",
    "publication_topology",
    "governance_evolution_model",
    "scaling_partition_model",
]

GENOME_CLASSES = {
    "canonical_authority_seat": [
        "evidence_set", "ordered_ledger", "replicated_state_machine", "proof_dag",
        "declarative_ir", "canonical_database", "federated_authority_set",
        "derived_state_root", "hybrid", "other"],
    "evidence_primitive": [
        "raw_source_bytes", "signed_source_record", "content_addressed_object",
        "typed_observation", "proof_object", "authority_assertion", "hybrid", "other"],
    "identity_model": [
        "structural_address", "source_declared_identity", "content_identity",
        "composite_identity", "persistent_registry", "theorem_identity",
        "federated_identity", "hybrid", "other"],
    "state_derivation_model": [
        "replay_reducer", "incremental_dataflow", "rule_engine", "event_calculus",
        "verified_compiler", "proof_checker", "replicated_transition_function",
        "query_derived", "hybrid", "other"],
    "temporal_model": [
        "bitemporal_intervals", "multitemporal_intervals", "event_calculus_time",
        "temporal_logic", "transaction_cut_replay", "version_dag_time", "hybrid", "other"],
    "normative_effect_model": [
        "versioned_rule_pack", "event_calculus", "typed_directive_interpreter",
        "theorem_proof", "compiler_transform", "constraint_solver",
        "governed_human_resolution", "hybrid", "other"],
    "consistency_commit_model": [
        "single_writer_sequence", "transactional_database", "consensus_log",
        "quorum_certificate", "deterministic_merge", "content_root_commit",
        "proof_commit", "hybrid", "other"],
    "replication_distribution_model": [
        "single_primary_read_replicas", "sharded_single_writer", "raft_paxos",
        "bft_consensus", "crdt_convergence", "federated_witnesses",
        "independent_replay_replicas", "hybrid", "other"],
    "trusted_core_topology": [
        "monolithic_kernel", "minimal_verifier", "compiler_kernel", "state_machine_kernel",
        "multi_component_tcb", "replicated_tcb", "capability_microkernel", "hybrid", "other"],
    "provenance_proof_model": [
        "hash_chain", "merkle_dag", "signed_receipts", "transparency_log",
        "proof_carrying_derivation", "theorem_certificate", "provenance_graph",
        "hybrid", "other"],
    "publication_topology": [
        "compiled_read_only_projections", "content_addressed_artifacts", "query_views",
        "signed_release_batches", "federated_mirrors", "proof_serving_api", "hybrid", "other"],
    "governance_evolution_model": [
        "signed_rule_packs", "shadow_replay_activation", "threshold_governance",
        "immutable_versioned_core", "capability_policy", "formal_upgrade_proofs",
        "human_adjudication_ledger", "hybrid", "other"],
    "scaling_partition_model": [
        "source_sharding", "namespace_sharding", "time_partition",
        "distributed_log_partitions", "dataflow_partition", "proof_dag_partition",
        "federated_domains", "single_node_scale_up", "hybrid", "other"],
}


def _axis_schema(name):
    return {
        "type": "object", "additionalProperties": False,
        "required": ["class", "detail"],
        "properties": {
            "class": {"enum": GENOME_CLASSES[name]},
            "detail": {"type": "string", "minLength": 10, "maxLength": 5000},
        },
    }


GENOME_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": GENOME_FIELDS,
    "properties": {
        **{k: _axis_schema(k) for k in GENOME_FIELDS},
        "novel_axes": {
            "type": "array", "maxItems": 16,
            "items": {
                "type": "object", "additionalProperties": False,
                "required": ["axis", "choice", "why_load_bearing"],
                "properties": {
                    "axis": {"type": "string", "minLength": 2, "maxLength": 500},
                    "choice": {"type": "string", "minLength": 2, "maxLength": 4000},
                    "why_load_bearing": {"type": "string", "minLength": 10, "maxLength": 8000},
                },
            },
        },
    },
}

PROPOSAL_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object", "additionalProperties": False,
    "required": ["family", "genome", "trusted_boundary", "mechanisms", "falsifiable_predictions",
                 "why_not_higher", "altitude_claimed"],
    "properties": {
        "family": {"type": "string", "minLength": 3, "maxLength": 2048},
        "genome": GENOME_SCHEMA,
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

SEARCH_SEED_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["seed_id", "family", "thesis", "genome", "mechanisms",
                 "decisive_advantages", "assumptions", "failure_modes", "why_not_higher"],
    "properties": {
        "seed_id": {"type": "string", "pattern": "^[A-Za-z0-9_-]{2,48}$"},
        "family": {"type": "string", "minLength": 3, "maxLength": 2000},
        "thesis": {"type": "string", "minLength": 30, "maxLength": 12000},
        "genome": GENOME_SCHEMA,
        "mechanisms": {"type": "array", "minItems": 3, "maxItems": 20,
                       "items": {"type": "string", "minLength": 5, "maxLength": 5000}},
        "decisive_advantages": {"type": "array", "minItems": 2, "maxItems": 16,
                                "items": {"type": "string", "minLength": 10, "maxLength": 6000}},
        "assumptions": {"type": "array", "minItems": 2, "maxItems": 20,
                        "items": {"type": "string", "minLength": 5, "maxLength": 6000}},
        "failure_modes": {"type": "array", "minItems": 2, "maxItems": 20,
                          "items": {"type": "string", "minLength": 10, "maxLength": 6000}},
        "why_not_higher": {"type": "string", "minLength": 20, "maxLength": 12000},
    },
}

SEARCH_LINEAGE_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object", "additionalProperties": False,
    "required": ["lineage", "candidates", "rejected", "finalist_ids", "exhaustion_note"],
    "properties": {
        "lineage": {"type": "string", "minLength": 3, "maxLength": 1000},
        "candidates": {"type": "array", "minItems": 4, "maxItems": 10,
                       "items": SEARCH_SEED_SCHEMA},
        "rejected": {
            "type": "array", "minItems": 2, "maxItems": 20,
            "items": {
                "type": "object", "additionalProperties": False,
                "required": ["idea", "reason"],
                "properties": {
                    "idea": {"type": "string", "minLength": 3, "maxLength": 5000},
                    "reason": {"type": "string", "minLength": 10, "maxLength": 8000},
                },
            },
        },
        "finalist_ids": {"type": "array", "minItems": 1, "maxItems": 3,
                         "items": {"type": "string", "maxLength": 48}},
        "exhaustion_note": {"type": "string", "minLength": 30, "maxLength": 12000},
    },
}

FORMALIZATION_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object", "additionalProperties": False,
    "required": ["formalization_id", "invariant_set", "authority_model", "state_transition_model",
                 "proof_obligations", "failure_semantics", "recovery_obligations",
                 "publication_invariants", "governance_invariants", "forbidden_shortcuts",
                 "unproven_claims"],
    "properties": {
        "formalization_id": {"type": "string", "pattern": "^[A-Za-z0-9_.:-]{3,128}$"},
        "invariant_set": {
            "type": "array", "minItems": 8, "maxItems": 80,
            "items": {
                "type": "object", "additionalProperties": False,
                "required": ["id", "statement", "failure_condition", "observable"],
                "properties": {
                    "id": {"type": "string", "pattern": "^INV-[A-Za-z0-9_-]{2,80}$"},
                    "statement": {"type": "string", "minLength": 10, "maxLength": 12000},
                    "failure_condition": {"type": "string", "minLength": 10, "maxLength": 12000},
                    "observable": {"type": "string", "minLength": 10, "maxLength": 12000},
                },
            },
        },
        "authority_model": {"type": "string", "minLength": 30, "maxLength": 30000},
        "state_transition_model": {"type": "string", "minLength": 30, "maxLength": 30000},
        "proof_obligations": {"type": "array", "minItems": 5, "maxItems": 64,
                              "items": {"type": "string", "minLength": 10, "maxLength": 12000}},
        "failure_semantics": {"type": "array", "minItems": 5, "maxItems": 64,
                              "items": {"type": "string", "minLength": 10, "maxLength": 12000}},
        "recovery_obligations": {"type": "array", "minItems": 3, "maxItems": 32,
                                 "items": {"type": "string", "minLength": 10, "maxLength": 12000}},
        "publication_invariants": {"type": "array", "minItems": 3, "maxItems": 32,
                                   "items": {"type": "string", "minLength": 10, "maxLength": 12000}},
        "governance_invariants": {"type": "array", "minItems": 3, "maxItems": 32,
                                  "items": {"type": "string", "minLength": 10, "maxLength": 12000}},
        "forbidden_shortcuts": {"type": "array", "minItems": 4, "maxItems": 48,
                                "items": {"type": "string", "minLength": 10, "maxLength": 12000}},
        "unproven_claims": {"type": "array", "maxItems": 64,
                            "items": {"type": "string", "minLength": 5, "maxLength": 12000}},
    },
}

BLUEPRINT_FIDELITY_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object", "additionalProperties": False,
    "required": ["faithful", "preserved_invariant_ids", "violated_invariant_ids", "evidence",
                 "blocking_reasons"],
    "properties": {
        "faithful": {"type": "boolean"},
        "preserved_invariant_ids": {"type": "array", "items": {"type": "string", "maxLength": 100}},
        "violated_invariant_ids": {"type": "array", "items": {"type": "string", "maxLength": 100}},
        "evidence": {"type": "array", "minItems": 1, "maxItems": 80,
                     "items": {"type": "string", "minLength": 5, "maxLength": 12000}},
        "blocking_reasons": {"type": "array", "maxItems": 40,
                             "items": {"type": "string", "minLength": 5, "maxLength": 12000}},
    },
}

DESTROYER_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object", "additionalProperties": False,
    "required": ["survives_prebuild", "fatal_flaws", "challenged_assumptions", "attack_plan",
                 "violated_invariant_ids", "missing_evidence"],
    "properties": {
        "survives_prebuild": {"type": "boolean"},
        "fatal_flaws": {"type": "array", "maxItems": 32,
                        "items": {"type": "string", "minLength": 5, "maxLength": 12000}},
        "challenged_assumptions": {"type": "array", "minItems": 3, "maxItems": 40,
                                   "items": {"type": "string", "minLength": 5, "maxLength": 12000}},
        "attack_plan": {"type": "array", "minItems": 5, "maxItems": 64,
                        "items": {"type": "string", "minLength": 10, "maxLength": 12000}},
        "violated_invariant_ids": {"type": "array", "items": {"type": "string", "maxLength": 100}},
        "missing_evidence": {"type": "array", "maxItems": 40,
                             "items": {"type": "string", "minLength": 5, "maxLength": 12000}},
    },
}

LOWER_BOUND_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object", "additionalProperties": False,
    "required": ["fundamental_limits", "attainable_improvements", "unresolved"],
    "properties": {
        "fundamental_limits": {
            "type": "array", "minItems": 3, "maxItems": 40,
            "items": {
                "type": "object", "additionalProperties": False,
                "required": ["id", "claim", "class", "argument", "crossing_requirement"],
                "properties": {
                    "id": {"type": "string", "maxLength": 100},
                    "claim": {"type": "string", "minLength": 10, "maxLength": 12000},
                    "class": {"enum": ["information", "distributed_systems", "legal_evidence", "governance", "computational", "other"]},
                    "argument": {"type": "string", "minLength": 20, "maxLength": 20000},
                    "crossing_requirement": {"type": "string", "minLength": 10, "maxLength": 12000},
                },
            },
        },
        "attainable_improvements": {"type": "array", "maxItems": 40,
                                    "items": {"type": "string", "minLength": 5, "maxLength": 12000}},
        "unresolved": {"type": "array", "maxItems": 40,
                       "items": {"type": "string", "minLength": 5, "maxLength": 12000}},
    },
}

SUPREMACY_CASE_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object", "additionalProperties": False,
    "required": ["candidate_id", "claim_level", "architecture_thesis", "measured_alternatives",
                 "destroyed_families", "load_bearing_mechanisms", "arena_evidence", "lower_bounds",
                 "why_frontier_team_would_choose", "falsifiers", "limitations",
                 "third_party_endorsement_claimed"],
    "properties": {
        "candidate_id": {"type": "string", "minLength": 1, "maxLength": 100},
        "claim_level": {"enum": ["EVIDENCE_SUPPORTED_SUPREMACY", "BEST_DISCOVERED_SO_FAR", "NOT_SUPPORTED"]},
        "architecture_thesis": {"type": "string", "minLength": 50, "maxLength": 30000},
        "measured_alternatives": {"type": "array", "minItems": 2, "maxItems": 128,
                                  "items": {"type": "string", "minLength": 5, "maxLength": 12000}},
        "destroyed_families": {"type": "array", "minItems": 1, "maxItems": 128,
                               "items": {"type": "string", "minLength": 5, "maxLength": 12000}},
        "load_bearing_mechanisms": {"type": "array", "minItems": 3, "maxItems": 128,
                                    "items": {"type": "string", "minLength": 5, "maxLength": 12000}},
        "arena_evidence": {"type": "array", "minItems": 3, "maxItems": 128,
                           "items": {"type": "string", "minLength": 5, "maxLength": 12000}},
        "lower_bounds": {"type": "array", "minItems": 1, "maxItems": 64,
                         "items": {"type": "string", "minLength": 5, "maxLength": 12000}},
        "why_frontier_team_would_choose": {"type": "string", "minLength": 50, "maxLength": 30000},
        "falsifiers": {"type": "array", "minItems": 3, "maxItems": 64,
                       "items": {"type": "string", "minLength": 10, "maxLength": 12000}},
        "limitations": {"type": "array", "maxItems": 64,
                        "items": {"type": "string", "minLength": 5, "maxLength": 12000}},
        "third_party_endorsement_claimed": {"const": False},
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
