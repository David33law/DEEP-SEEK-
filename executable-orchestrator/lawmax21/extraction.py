"""Extraction engine — pull the builder's best, not its first draft.

A model's first answer is rarely its ceiling. Three mechanisms here force it higher, and
all three are MEASURED, so none is decorative:

  1. best-of-N        — generate N diverse attempts for a build slot, measure every one on
                        the sealed cases, keep the winner. Diversity comes from varying the
                        sampling temperature and a per-attempt framing, so the N are genuinely
                        different architectures rather than one answer rephrased.
  2. targeted revision — a candidate that is not dominant is handed its EXACT failure (which
                        sealed classes it missed, which ablation did not move, which layer
                        sensor returned nothing) and asked to fix precisely that while keeping
                        what worked. Iterated up to R times, stopping as soon as it stops
                        improving — no wasted calls.
  3. reach-first       — before building up from the current baseline, the builder is asked to
                        describe the SUPREME system for the task, then build toward it. Building
                        toward a ceiling beats building up from a floor.

N and R are owner-signed budget decisions, not hard-coded — the owner controls how hard the
extraction pushes, and the budget ledger stops it before overspend.
"""


def diversity_framing(i, n):
    """A distinct angle per attempt, so best-of-N explores rather than repeats."""
    angles = [
        "Prioritise correctness above all: every flag must be provable.",
        "Prioritise coverage: reach mechanisms the field has not yet covered.",
        "Prioritise the higher layers: build counter-arguments, gap-reporting and revocation in.",
        "Prioritise simplicity: the least machinery that still reaches the frontier.",
        "Prioritise transfer: work on domains and vocabulary you were not shown.",
        "Take the riskiest coherent design you can defend on measured evidence.",
    ]
    return angles[i % len(angles)]


def temperature_for(i, n, base=0.0, spread=0.8):
    """Attempt 0 is deterministic (a solid anchor); the rest fan out for diversity."""
    if n <= 1:
        return base
    return round(base + spread * (i / (n - 1)), 3)


def failure_brief(measured):
    """Turn a measured result into a precise, actionable critique for revision. Names what
    to fix, never hands over the answers — only the candidate's OWN measured shortfalls."""
    lines = []
    cls = measured.get("diagnostic_classes", {})
    if cls.get("MISSED_RISK"):
        lines.append(f"You missed {cls['MISSED_RISK']} real risk(s) — a mechanism is absent or too narrow.")
    if cls.get("SPURIOUS_FLAG"):
        lines.append(f"You raised {cls['SPURIOUS_FLAG']} spurious flag(s) — a mechanism fires on safe spans.")
    if cls.get("TRACE_INVALID"):
        lines.append(f"{cls['TRACE_INVALID']} flag(s) carried no valid proof — every flag needs its join.")
    if cls.get("FABRICATION"):
        lines.append(f"{cls['FABRICATION']} flag(s) cited things that do not exist — never invent ids.")
    weak = [s for s, d in (measured.get("slice_scores") or {}).items() if d.get("f1", 1.0) < 0.7]
    if weak:
        lines.append(f"Weak on these mechanisms (F1 < 0.7): {', '.join(sorted(weak))}. Strengthen exactly these.")
    missing_layers = measured.get("layers_missing", [])
    if missing_layers:
        lines.append(f"Higher layers not yet demonstrated: {', '.join(missing_layers)}. "
                     "Add the capability the sensor checks — do not fake it.")
    if not lines:
        lines.append("You are close. Find one more real improvement without breaking what works.")
    return "\n".join("  - " + ln for ln in lines)


def best_of(attempts_scores, score_fn):
    """Given [(candidate_id, measured), ...], return the id with the highest score. Ties break
    deterministically by id so selection is reproducible."""
    best, best_score = None, float("-inf")
    for cid, measured in sorted(attempts_scores, key=lambda t: t[0]):
        sc = score_fn(measured)
        if sc > best_score:
            best, best_score = cid, sc
    return best, best_score


def composite_score(measured):
    """The single number best-of-N and revision climb: capability, plus a real bonus for each
    higher layer demonstrated, minus a penalty for any safety violation. Rewards reaching UP,
    not just detecting well — so the extraction pressure points toward the twelve-layer target."""
    slices = measured.get("slice_scores") or {}
    capability = sum(v.get("f1", 0.0) for v in slices.values()) / max(1, len(slices))
    layers = len(measured.get("higher_layers_demonstrated", []))
    cls = measured.get("diagnostic_classes", {})
    safety_penalty = 0.25 * cls.get("FABRICATION", 0)
    return round(capability + 0.15 * layers - safety_penalty, 5)
