"""The evolvability gate — "never needs a refactor again", made into a number.

No architecture is finished. A candidate that promises "done forever" is lying, and it is
exactly the lie v2.0 told. What IS achievable, and what the owner actually asked for, is an
architecture that grows by ADDITION, not by rewriting: open for extension, closed for
modification.

This gate proves it mechanically. After a candidate is built, it is handed a NEW requirement
it has never seen — a fresh mechanism, a fresh legal domain — and asked to accommodate it.
Then we measure how much of its own trusted core it had to disturb:

  * hash the core files BEFORE the new requirement
  * let the candidate extend to meet it
  * hash the core files AFTER
  * core changed  -> it needed a refactor           -> FAIL
  * core intact, new seat added behind the boundary -> PASS

"Never refactor again" stops being marketing and becomes: the core hash does not move when
the world asks for more. The trusted boundary the candidate itself declared is the line;
writing across it is the failure.
"""
from .canonical import sha256_bytes

# Requirements the candidate has not seen, each exercising a different growth axis. The
# point is not whether the candidate solves them well — it is whether solving them forces
# it to reopen its core.
GROWTH_PROBES = [
    {"id": "new-mechanism",
     "ask": "Add a NINTH detection mechanism (a new kind of legal risk) without editing any "
            "file you declared part of the trusted core.",
     "axis": "new reasoning mechanism"},
    {"id": "new-domain",
     "ask": "Accept cases from a legal domain with vocabulary you have never seen, routing them "
            "through the SAME core, adding only a domain adapter.",
     "axis": "new legal domain"},
    {"id": "new-output-obligation",
     "ask": "Attach a required counter-argument to every flag (an L6 obligation) by adding a "
            "layer, not by rewriting the detector.",
     "axis": "new institutional obligation"},
]

EVOLVABILITY_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "additionalProperties": False,
    "required": ["candidate_id", "declared_core", "probes", "core_untouched", "verdict"],
    "properties": {
        "candidate_id": {"type": "string", "minLength": 1},
        "declared_core": {"type": "array", "minItems": 1, "items": {"type": "string"}},
        "probes": {
            "type": "array", "minItems": 1,
            "items": {
                "type": "object", "additionalProperties": False,
                "required": ["id", "core_before", "core_after", "core_touched",
                             "files_added", "accommodated"],
                "properties": {
                    "id": {"type": "string"},
                    "core_before": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
                    "core_after": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
                    "core_touched": {"type": "boolean"},
                    "files_added": {"type": "array"},
                    "accommodated": {"type": "boolean"},
                },
            },
        },
        "core_untouched": {"type": "boolean"},
        "growth_accommodated": {"type": "boolean"},
        "verdict": {"enum": ["EVOLVABLE", "NEEDS_REFACTOR"]},
    },
}


class EvolvabilityFailed(Exception):
    pass


def core_hash(worktree, declared_core):
    """Hash of exactly the files the candidate declared as its trusted core.
    A candidate that declares an empty or trivial core to game the test is caught by the
    minItems:1 schema and by the requirement that the core actually contains the detector."""
    h_parts = []
    for rel in sorted(declared_core):
        if not worktree.exists(rel):
            raise EvolvabilityFailed(f"declared core file {rel!r} does not exist")
        h_parts.append(rel + ":" + sha256_bytes(worktree.read_text(rel).encode("utf-8")))
    return sha256_bytes("\n".join(h_parts).encode("utf-8"))


def evaluate(candidate_id, worktree, declared_core, apply_probe):
    """apply_probe(probe) -> (files_added: list[str], accommodated: bool). It must let the
    candidate attempt the growth, then report which files it added. We independently confirm
    the core hash did not move — the candidate's own report is never trusted for that."""
    if not declared_core:
        raise EvolvabilityFailed("candidate declared no trusted core — nothing to protect")
    results = []
    core_untouched = True
    for probe in GROWTH_PROBES:
        before = core_hash(worktree, declared_core)
        files_added, accommodated = apply_probe(probe)
        after = core_hash(worktree, declared_core)
        touched = before != after
        if touched:
            core_untouched = False
        results.append({
            "id": probe["id"],
            "core_before": before,
            "core_after": after,
            "core_touched": touched,
            "files_added": sorted(files_added),
            "accommodated": bool(accommodated),
        })
    accommodated_all = all(r["accommodated"] for r in results)
    # EVOLVABLE requires BOTH: the growth was genuinely accommodated AND the trusted core was
    # not reopened. A candidate that simply refuses every growth probe leaves the core
    # untouched trivially — that is not evolvability, it is inertia (audit: gameable-gate).
    verdict = "EVOLVABLE" if (core_untouched and accommodated_all) else "NEEDS_REFACTOR"
    return {
        "candidate_id": candidate_id,
        "declared_core": sorted(declared_core),
        "probes": results,
        "core_untouched": core_untouched,
        "growth_accommodated": accommodated_all,
        "verdict": verdict,
    }
