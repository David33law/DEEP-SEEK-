"""Single source of truth for the owner-signed National Observatory research protocol.

The setup ceremony and production launcher import this module rather than maintaining duplicated
file lists or mission flags. The protocol bundle is a deterministic census of all load-bearing
profile, orchestration, evaluator, proof and reference files. Production may never use the reduced
zero-cost proof workload.
"""
from __future__ import annotations

import hashlib
import os

PROTOCOL_VERSION = "OBSERVATORY-OMEGA-RESEARCH-PROTOCOL-3"
PROOF_MODE_ENV = "OBSERVATORY_ZERO_COST_PROOF"
PUBLICATION_CHANNELS = ["human", "api", "linked_data", "eli", "public_sector", "ai"]
REQUIRED_NOVELTY_METHODS = [
    "G91-assumption-inversion", "G92-morphological-gap-search",
    "G93-cross-domain-structural-transfer", "G94-surgical-genome-mutation",
    "G95-trusted-boundary-recut", "G96-ontology-and-taxonomy-challenge",
]

MISSION_FLAGS = {
    "all_twelve_layers_required": True,
    "no_silent_legally_material_loss": True,
    "supremacy_search_required": True,
    "no_first_answer_privilege": True,
    "public_supremacy_case_required": True,
    "durable_systems_arena_required": True,
    "distributed_fault_arena_required": True,
    "national_scale_arena_required": True,
    "machine_checked_models_required": True,
    "legal_interoperability_required": True,
    "authoritative_prior_art_challenge_required": True,
    "active_novelty_saturation_required": True,
    "meta_search_required": True,
    "mechanical_genome_coverage_required": True,
    "independent_closure_auditors_required": True,
    "implementation_diversity_required": True,
    "proof_mode_forbidden_in_production": True,
}

SEARCH_POLICY = {
    "novelty_dry_waves_required": 3,
    "meta_search_critics_required": 2,
    "closure_auditors_required": 2,
    "critical_pair_breadth_required": 3,
    "prior_art_critics_required": 3,
    "semantic_distinct_implementations_required": 3,
    "distributed_distinct_implementations_required": 2,
    "scale_distinct_implementations_required": 2,
    "formal_models_required": 2,
    "interoperability_implementations_required": 2,
}

PRODUCTION_WORKLOADS = {
    "distributed": {"qualification": 5000, "replication": 10000, "crown": 50000},
    "scale": {"qualification": 100000, "replication": 250000, "crown": 1000000,
              "partitions": 16, "batch": 5000},
    "formal": {"qualification_depth": 3, "replication_depth": 4, "crown_depth": 5},
    "interoperability": {"qualification_cases": 24, "replication_cases": 48,
                         "crown_cases": 96},
}

# Same handlers and schemas, reduced deterministic workloads for the local zero-cost control proof.
PROOF_WORKLOADS = {
    "distributed": {"qualification": 300, "replication": 600, "crown": 1200},
    "scale": {"qualification": 2000, "replication": 4000, "crown": 8000,
              "partitions": 8, "batch": 500},
    "formal": {"qualification_depth": 2, "replication_depth": 2, "crown_depth": 3},
    "interoperability": {"qualification_cases": 4, "replication_cases": 6,
                         "crown_cases": 8},
}

CONTRACT_FILES = {
    "charter_sha256": "profiles/national-observatory/OBJECTIVE-CHARTER.md",
    "master_system_sha256": "profiles/national-observatory/MASTER-SYSTEM-PROMPT.md",
    "pareto_sha256": "profiles/national-observatory/PARETO-DIMENSIONS.json",
    "evaluator_contract_sha256": "profiles/national-observatory/EVALUATOR-CONTRACT.md",
    "supremacy_contract_sha256": "profiles/national-observatory/SUPREMACY-CONTRACT.md",
    "systems_contract_sha256": "profiles/national-observatory/SYSTEMS-CONTRACT.md",
    "distributed_contract_sha256": "profiles/national-observatory/DISTRIBUTED-SYSTEMS-CONTRACT.md",
    "scale_contract_sha256": "profiles/national-observatory/SCALE-SYSTEMS-CONTRACT.md",
    "formal_model_contract_sha256": "profiles/national-observatory/FORMAL-MODEL-CONTRACT.md",
    "interoperability_contract_sha256": "profiles/national-observatory/INTEROPERABILITY-CONTRACT.md",
    "novelty_search_contract_sha256": "profiles/national-observatory/NOVELTY-SEARCH-CONTRACT.md",
    "prior_art_contract_sha256": "profiles/national-observatory/PRIOR-ART-CHALLENGE-CONTRACT.md",
    "prior_art_manifest_sha256": "profiles/national-observatory/PUBLIC-PRIOR-ART-MANIFEST.json",
    "architecture_protocol_sha256": "profiles/national-observatory/ARCHITECTURE-DISCOVERY-PROTOCOL.md",
}

EXPLICIT_FILES = {
    "run_observatory.py", "setup_observatory.py",
    "executable-orchestrator/orchestrator.py",
    "executable-orchestrator/tools/generate_protocol19.py",
    "executable-orchestrator/tools/make_manifest.py",
    "executable-orchestrator/tools/owner_sign.py",
}
SCAN_ROOTS = (
    "profiles/national-observatory",
    "executable-orchestrator/lawmax21",
    "private-evaluator/evaluator",
)
SCAN_PREFIXES = (
    ("benchmark", "observatory_"),
    ("executable-orchestrator/tools", "mock_observatory"),
    ("executable-orchestrator/tools", "run_observatory"),
    ("executable-orchestrator/tools", "prove_"),
)
ALLOWED_SUFFIXES = (".py", ".md", ".json", ".txt", ".toml", ".yaml", ".yml")


def proof_mode():
    return os.environ.get(PROOF_MODE_ENV, "").strip() == "1"


def workload(section, key):
    policy = PROOF_WORKLOADS if proof_mode() else PRODUCTION_WORKLOADS
    return int(policy[section][key])


def file_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _eligible(path):
    name = os.path.basename(path)
    return (not name.startswith(".") and "__pycache__" not in path
            and path.endswith(ALLOWED_SUFFIXES))


def protocol_files(root):
    files = set(EXPLICIT_FILES)
    for relative_root in SCAN_ROOTS:
        absolute_root = os.path.join(root, *relative_root.split("/"))
        if not os.path.isdir(absolute_root):
            raise RuntimeError("research protocol root missing: " + relative_root)
        for current, directories, names in os.walk(absolute_root):
            directories[:] = sorted(x for x in directories
                                    if x != "__pycache__" and not x.startswith("."))
            for name in sorted(names):
                absolute = os.path.join(current, name)
                if _eligible(absolute):
                    files.add(os.path.relpath(absolute, root).replace("\\", "/"))
    for relative_root, prefix in SCAN_PREFIXES:
        absolute_root = os.path.join(root, *relative_root.split("/"))
        if not os.path.isdir(absolute_root):
            raise RuntimeError("research protocol root missing: " + relative_root)
        for name in sorted(os.listdir(absolute_root)):
            absolute = os.path.join(absolute_root, name)
            if os.path.isfile(absolute) and name.startswith(prefix) and _eligible(absolute):
                files.add(relative_root + "/" + name)
    ordered = sorted(files)
    missing = [rel for rel in ordered
               if not os.path.isfile(os.path.join(root, *rel.split("/")))]
    if missing:
        raise RuntimeError("research protocol files missing: " + ", ".join(missing))
    return ordered


def protocol_bundle_sha256(root):
    digest = hashlib.sha256()
    for relative in protocol_files(root):
        digest.update(relative.encode("utf-8")); digest.update(b"\0")
        digest.update(bytes.fromhex(file_sha256(
            os.path.join(root, *relative.split("/")))))
    return digest.hexdigest()


def contract_hashes(root):
    return {key: file_sha256(os.path.join(root, *relative.split("/")))
            for key, relative in CONTRACT_FILES.items()}


def mission_binding(root, git_value):
    mission = {
        "protocol_version": PROTOCOL_VERSION,
        "target": "National Legal Observatory — canonical Greek legal information infrastructure",
        **MISSION_FLAGS, **SEARCH_POLICY,
        "novelty_methods": list(REQUIRED_NOVELTY_METHODS),
        "publication_channels": list(PUBLICATION_CHANNELS),
        "production_workloads": PRODUCTION_WORKLOADS,
        "runner_head": git_value("rev-parse", "HEAD"),
        "runner_tree": git_value("rev-parse", "HEAD^{tree}"),
        "research_protocol_files": protocol_files(root),
        "research_protocol_bundle_sha256": protocol_bundle_sha256(root),
    }
    mission.update(contract_hashes(root))
    return mission


def validate_mission(root, mission, git_value):
    expected = mission_binding(root, git_value)
    missing = [key for key, value in expected.items() if mission.get(key) != value]
    extra = sorted(set(mission) - set(expected))
    if missing or extra:
        detail = []
        if missing:
            detail.append("mismatched: " + ", ".join(missing))
        if extra:
            detail.append("unexpected: " + ", ".join(extra))
        raise RuntimeError("signed Observatory mission drift — " + "; ".join(detail))
    return expected
