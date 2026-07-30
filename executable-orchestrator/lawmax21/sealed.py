"""Sealed material — what the builder must NEVER be able to see.

The owner's blind studies (metamorphic triads, redteam cases) and any answer key are
EVALUATION material. If the builder/DeepSeek reads them, it overfits to the very cases that
are supposed to measure it blind, and every "improvement" after that is memorisation.

v2.0 had no notion of this boundary, so "read the whole repo" would have leaked the answer
keys straight into the builder's context. Here the boundary is structural and enforced two
ways that cannot both be forgotten:

  1. The coverage ledger (what the builder reads) REFUSES to enrol a sealed path. There is
     no flag to override it — a sealed path is simply not enrollable.
  2. Before any builder-facing context is sent, `assert_clean()` scans it for the fingerprint
     of every sealed case. A leak aborts the call instead of paying to teach the model the
     answers.

A path is sealed if it matches a rule in SEALED_PATTERNS, or if the owner listed it in
SEALED-MANIFEST.json. Sealing is deny-by-default for the categories that carry answers:
blind studies, redteam outputs, evaluation cases, and anything named like an answer key.
"""
import os
import re

from .canonical import read_json, sha256_bytes

# Deny-by-default categories. Two kinds of sealed material:
#
#   (a) EVALUATION cases and answer keys — blind studies, redteam outputs, metamorphic
#       triads. If the builder reads these it overfits to the very cases meant to measure it.
#
#   (b) PRIOR INDEPENDENT DISCOVERIES — the exact list frozen by the owner's CP0 isolation
#       attestation: prior Opus 4.7 study, THIS Opus 4.8 blind study, Candidate G, Codex
#       outputs, and the full 67-requirement Charter before its checkpoint. The whole point
#       of blind discovery is that DeepSeek arrives at its architecture INDEPENDENTLY. If it
#       sees that Opus concluded "four families are truth-makers", it will simply agree, and
#       the independent-convergence signal — the strongest evidence the experiment can
#       produce — is destroyed. So prior conclusions are sealed from the builder and kept for
#       the OWNER to compare against.
#
# Matched against a repo-relative POSIX path, case-insensitive.
SEALED_PATTERNS = [
    # (a) evaluation material
    r"(^|/)blind[-_]?study(/|$)",
    r"(^|/)LAWMAX[-_]?BLIND[-_]?STUDY(/|$)",
    r"(^|/)redteam[-_]?audit",
    r"(^|/)output/redteam",
    r"(^|/)cases?/.*\.(txt|json|md)$",
    r"blind[-_].*\.(txt|json|md)$",
    r"metamorphic[-_].*\.(txt|json|md)$",
    r"(answer|expected|verdict|gold|grade)[-_]?key",
    r"(^|/)private-evaluator/",
    r"(^|/)encrypted-hidden-bank(/|$)",
    r"(^|/)owner-held-secrets(/|$)",
    r"\.shard$", r"\.key$",
    # (b) prior independent discoveries — CP0 isolation list
    r"opus[-_]?4[.\-_]?[78]",                    # Opus 4.7 and 4.8 studies
    r"(^|/)OPUS4[78](/|$)",
    r"candidate[-_]?g\b",
    r"(^|/)codex(/|$)", r"codex[-_].*",
    r"(^|/)dossiers?(/|$)",                      # the 17 synthesis dossiers
    r"67[-_]?requirement", r"full[-_]?charter",
    r"design[-_]?space[-_]?map", r"rejected[-_]?alternatives",
    r"CP[0-6][-_]", r"checkpoint[-_]?[0-6]",
    r"HIDDEN|SEALED",
]

_COMPILED = [re.compile(p, re.IGNORECASE) for p in SEALED_PATTERNS]


class SealBroken(Exception):
    """Sealed material was about to reach the builder. The call is aborted, not logged."""


def _norm(rel):
    return rel.replace("\\", "/").lstrip("./")


def is_sealed(rel, extra_patterns=()):
    p = _norm(rel)
    if any(rx.search(p) for rx in _COMPILED):
        return True
    return any(re.search(pat, p, re.IGNORECASE) for pat in extra_patterns)


def load_manifest(root):
    """Optional owner-authored SEALED-MANIFEST.json at the corpus root: {"sealed": ["path", ...]}.
    Its entries are added to the pattern set — the owner can seal anything by name."""
    mp = os.path.join(root, "SEALED-MANIFEST.json")
    if not os.path.exists(mp):
        return []
    try:
        return [re.escape(_norm(x)) for x in read_json(mp).get("sealed", [])]
    except (ValueError, OSError):
        return []


def partition(root):
    """Split the corpus into (readable, sealed) relative paths. The overseer feeds the
    builder ONLY the readable set."""
    extra = load_manifest(root)
    readable, sealed = [], []
    for r, ds, fs in os.walk(root):
        ds[:] = [d for d in ds if d not in (".git", "__pycache__", "node_modules")]
        for f in fs:
            rel = _norm(os.path.relpath(os.path.join(r, f), root))
            (sealed if is_sealed(rel, extra) else readable).append(rel)
    return sorted(readable), sorted(sealed)


def fingerprints(root, sealed_rels, sample_bytes=4000):
    """A short, content-derived fingerprint of each sealed file, used to detect a leak even
    if the material is paraphrased into a prompt via its distinctive case ids."""
    out = {}
    for rel in sealed_rels:
        p = os.path.join(root, rel)
        try:
            with open(p, "r", encoding="utf-8", errors="ignore") as fh:
                text = fh.read(sample_bytes)
        except OSError:
            continue
        # CASE-ID lines are the leak-critical tokens: they are unique and would let a builder
        # recognise a sealed case. Extract them as the fingerprint.
        ids = re.findall(r"CASE-ID:\s*([A-Za-z0-9_-]+)", text)
        for cid in ids:
            out[cid] = rel
    return out


def assert_clean(text, sealed_fingerprints, where="builder context"):
    """Abort if any sealed case id appears in builder-facing text. Called before every send."""
    hits = [cid for cid in sealed_fingerprints if cid and cid in text]
    if hits:
        raise SealBroken(
            f"{where} contains sealed case id(s) {hits[:5]} — refusing to send. "
            "Evaluation material must never reach the builder.")
    return True
