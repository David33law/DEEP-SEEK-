"""Compositional search — never discard a whole architecture because one part fell short.

The owner's instruction: a candidate that is strong on some mechanisms and weak on one is
not garbage. Its strong parts must survive. So every round, before we crown or continue,
we read the measured field PART BY PART and assemble the best-of-each into a recombinant
that the builder then composes.

Two units of composition, because the target has two axes:
  * capability slices  — which candidate detects each kind of legal risk best
  * target layers      — which candidate demonstrates each of the twelve layers

For each unit we pick the source with the strongest MEASURED evidence (never a claim).
If no single incumbent already owns every winning part, there is a strictly better
composition to attempt — and the successor challenger is directed to build exactly it,
citing which candidate each part came from so the recombination is auditable, not magic.

This does not splice source code blindly (that produces brittle chimaeras). It produces a
BRIEF — "take mechanism X from CAND-A, layer L6 from CAND-B" — and the builder composes a
clean implementation to it. The direction is fully determined by measurement; only the
composition is the model's.
"""
from . import target


def _slice_winner(field, slice_name):
    """The candidate with the highest F1 on this slice, and its score. Ties → deterministic
    by candidate id so the search is reproducible."""
    best, best_score = None, -1.0
    for cid in sorted(field):
        sc = field[cid].get("slice_scores", {}).get(slice_name)
        if sc is None:
            continue
        f1 = sc.get("f1", 0.0)
        if f1 > best_score:
            best, best_score = cid, f1
    return best, best_score


def _layer_winner(field, layer_id):
    """The candidate that demonstrated this layer with the strongest evidence. A layer is
    binary (demonstrated or not), so the winner is any demonstrator, preferring the one
    that also scores higher overall to break ties toward coherence."""
    demos = [cid for cid in sorted(field) if layer_id in set(field[cid].get("layers", []))]
    if not demos:
        return None
    return max(demos, key=lambda c: (field[c].get("macro_f1", 0.0), c))


def brief(field):
    """Read the whole measured field and produce the recombination brief.

    field: {candidate_id: {"slice_scores": {...}, "layers": [...], "macro_f1": float,
                           "family": str}}
    Returns a brief naming, per slice and per layer, the source to inherit from — and
    whether any single existing candidate already dominates (in which case there is nothing
    to recombine and the successor slot is free for a genuinely new idea)."""
    slice_sources, layer_sources = {}, {}
    from .frontier import Frontier  # slices come from the benchmark; import lazily

    slices = _all_slices(field)
    for s in slices:
        winner, score = _slice_winner(field, s)
        if winner is not None:
            slice_sources[s] = {"source": winner, "f1": round(score, 4)}
    for lid in target.LAYER_IDS:
        w = _layer_winner(field, lid)
        if w is not None:
            layer_sources[lid] = {"source": w}

    # Does one candidate already own every winning part? Then recombination adds nothing.
    slice_owners = {v["source"] for v in slice_sources.values()}
    layer_owners = {v["source"] for v in layer_sources.values()}
    all_owners = slice_owners | layer_owners
    dominated_by_one = len(all_owners) <= 1

    # Predicted coverage of the recombinant: the union of every winning part.
    predicted_layers = sorted(layer_sources, key=target.LAYER_IDS.index)
    return {
        "slice_sources": slice_sources,
        "layer_sources": layer_sources,
        "contributing_candidates": sorted(all_owners),
        "recombination_worthwhile": not dominated_by_one and len(all_owners) >= 2,
        "predicted_layer_union": predicted_layers,
        "predicted_altitude": target.audited_altitude(predicted_layers),
        "note": ("no single candidate owns every best part; a composition of "
                 f"{sorted(all_owners)} should dominate the field"
                 if not dominated_by_one else
                 f"{next(iter(all_owners), 'none')} already owns every best part — "
                 "recombination adds nothing; spend the slot on a new idea"),
    }


def _all_slices(field):
    out = set()
    for rec in field.values():
        out.update((rec.get("slice_scores") or {}).keys())
    return sorted(out)


def render_directive(brief_obj, incumbent_id):
    """Human-and-model readable instruction for the successor builder."""
    if not brief_obj["recombination_worthwhile"]:
        return None
    lines = ["Compose a SUCCESSOR by recombination. Inherit each part from the source that "
             "measured best — do not rebuild what already works, and do not discard a strong "
             "part because its parent lost overall:"]
    for s, v in sorted(brief_obj["slice_sources"].items()):
        lines.append(f"  · mechanism for {s}: take the approach from {v['source']} (F1={v['f1']})")
    for lid, v in sorted(brief_obj["layer_sources"].items(), key=lambda kv: target.LAYER_IDS.index(kv[0])):
        lines.append(f"  · {lid} {target.LAYER_TITLE[lid]}: from {v['source']}")
    lines.append(f"The result must beat {incumbent_id} on the sealed cases AND keep the "
                 "trusted core closed to modification (the evolvability gate still applies).")
    return "\n".join(lines)
