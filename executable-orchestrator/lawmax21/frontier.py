"""Pareto frontier and the dominance gate — where the candidates actually fight.

A candidate is admitted only with a complete measured vector: every dimension of
PARETO-DIMENSIONS.json, each above its hard minimum. Dominance is strict and uses the
per-dimension noise floor, so a candidate is never dethroned by measurement jitter.

The gate answers the question that decides the run: *is there anything strictly better?*
"""
from .canonical import read_json


class DimensionMissing(Exception):
    pass


class Frontier:
    def __init__(self, dims_path):
        self.spec = read_json(dims_path)
        self.dims = [d["id"] for d in self.spec]
        self.by_id = {d["id"]: d for d in self.spec}
        self.members = {}

    # -------------------------------------------------------------- admission
    def _check(self, vec):
        missing = [d for d in self.dims if d not in vec]
        if missing:
            raise DimensionMissing(f"measurement incomplete: {missing}")
        below = []
        for d in self.dims:
            spec, v = self.by_id[d], vec[d]
            hard = spec.get("hard_minimum")
            if hard is None:
                continue
            if spec["direction"] == "higher" and v < hard:
                below.append(f"{d}={v} < {hard}")
            if spec["direction"] == "lower" and v > hard:
                below.append(f"{d}={v} > {hard}")
        return below

    def add(self, member):
        below = self._check(member["dimension_vector"])
        if below:
            member = dict(member, status="REJECTED_HARD_MINIMUM", reason="; ".join(below))
            self.members[member["candidate_id"]] = member
            return member
        member = dict(member, status="ACTIVE", reason="")
        self.members[member["candidate_id"]] = member
        self._recompute()
        return self.members[member["candidate_id"]]

    # -------------------------------------------------------------- dominance
    def _beats(self, a, b, d):
        """Strictly better on dimension d, by more than the noise floor."""
        spec = self.by_id[d]
        nf = spec.get("noise_floor") or 0
        av, bv = a[d], b[d]
        return (av - bv) > nf if spec["direction"] == "higher" else (bv - av) > nf

    def _not_worse(self, a, b, d):
        spec = self.by_id[d]
        nf = spec.get("noise_floor") or 0
        av, bv = a[d], b[d]
        return (av - bv) >= -nf if spec["direction"] == "higher" else (bv - av) >= -nf

    def dominates(self, a_id, b_id):
        a = self.members[a_id]["dimension_vector"]
        b = self.members[b_id]["dimension_vector"]
        return (all(self._not_worse(a, b, d) for d in self.dims)
                and any(self._beats(a, b, d) for d in self.dims))

    def _recompute(self):
        live = [m for m in self.members.values() if m["status"] in ("ACTIVE", "DOMINATED")]
        for m in live:
            m["status"] = "ACTIVE"
        for m in live:
            for other in live:
                if other["candidate_id"] == m["candidate_id"]:
                    continue
                if self.dominates(other["candidate_id"], m["candidate_id"]):
                    m["status"] = "DOMINATED"
                    m["reason"] = f"dominated by {other['candidate_id']}"
                    break

    # ------------------------------------------------------------------ report
    def non_dominated(self):
        return sorted(mid for mid, m in self.members.items() if m["status"] == "ACTIVE")

    def head_to_head(self, primary="legal_capability", secondary="cross_domain_transfer"):
        """Ranking used to name a single HESA candidate among the non-dominated set."""
        act = self.non_dominated()
        if not act:
            return None, 0.0
        ranked = sorted(act, key=lambda m: (self.members[m]["dimension_vector"][primary],
                                            self.members[m]["dimension_vector"][secondary]),
                        reverse=True)
        best = ranked[0]
        if len(ranked) == 1:
            # Lead over the OTHER non-dominated members only. Comparing against rejected /
            # dominated members produced a negative, meaningless margin (audit: frontier-math).
            rest = [m for m in act if m != best]
            if not rest:
                return best, 0.0
            margin = min(self.members[best]["dimension_vector"][primary]
                         - self.members[r]["dimension_vector"][primary] for r in rest)
            return best, round(margin, 6)
        margin = (self.members[best]["dimension_vector"][primary]
                  - self.members[ranked[1]]["dimension_vector"][primary])
        return best, round(margin, 6)

    def report(self):
        return {mid: {"status": m["status"], "reason": m.get("reason", ""),
                      "mechanism": m.get("mechanism"), "declared_altitude": m.get("declared_altitude"),
                      "dimension_vector": m["dimension_vector"]}
                for mid, m in sorted(self.members.items())}
