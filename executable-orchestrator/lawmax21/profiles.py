"""Selectable experiment target profiles.

The default remains the historical LAWMAX tournament. A profile changes the target,
measurement dimensions and candidate semantics without creating a second orchestrator.
The LAWMAX immutable-package remains byte-for-byte sealed; additive profiles live under
profiles/ and carry their own package manifest.
"""
from dataclasses import dataclass
import os

from . import target as lawmax_target
from . import observatory_target


@dataclass(frozen=True)
class Profile:
    id: str
    target: object
    pareto_relpath: str
    primary_dimension: str
    secondary_dimension: str
    candidate_mode: str
    requires_consciousness: bool
    creditable_layers: tuple
    charter_relpath: str | None = None
    master_system_relpath: str | None = None

    def pareto_path(self, root):
        return os.path.join(root, self.pareto_relpath)

    def charter_path(self, root):
        return os.path.join(root, self.charter_relpath) if self.charter_relpath else None

    def master_system_path(self, root):
        return os.path.join(root, self.master_system_relpath) if self.master_system_relpath else None


PROFILES = {
    "lawmax": Profile(
        id="lawmax",
        target=lawmax_target,
        pareto_relpath=os.path.join("immutable-package", "manifests", "PARETO-DIMENSIONS.json"),
        primary_dimension="legal_capability",
        secondary_dimension="cross_domain_transfer",
        candidate_mode="capability-mechanism",
        requires_consciousness=True,
        creditable_layers=("L1", "L2", "L7", "L8", "L10"),
        charter_relpath=os.path.join("immutable-package", "canonical-charter",
                                    "00-LAWMAX-SYSTEM-OBJECTIVE-CHARTER.md"),
        master_system_relpath=None,
    ),
    "national-observatory": Profile(
        id="national-observatory",
        target=observatory_target,
        pareto_relpath=os.path.join("profiles", "national-observatory", "PARETO-DIMENSIONS.json"),
        primary_dimension="temporal_reconstruction_accuracy",
        secondary_dimension="source_coverage",
        candidate_mode=observatory_target.CANDIDATE_MODE,
        requires_consciousness=observatory_target.REQUIRES_CONSCIOUSNESS,
        creditable_layers=tuple(observatory_target.CREDITABLE_LAYERS),
        charter_relpath=os.path.join("profiles", "national-observatory", "OBJECTIVE-CHARTER.md"),
        master_system_relpath=os.path.join("profiles", "national-observatory", "MASTER-SYSTEM-PROMPT.md"),
    ),
}

ALIASES = {
    "observatory": "national-observatory",
    "national_legal_observatory": "national-observatory",
    "national-observatory-omega": "national-observatory",
}


def resolve(profile_id="lawmax"):
    key = ALIASES.get(profile_id, profile_id)
    if key not in PROFILES:
        raise ValueError(f"unknown experiment profile {profile_id!r}; available: {sorted(PROFILES)}")
    return PROFILES[key]


def available():
    return tuple(sorted(PROFILES))
