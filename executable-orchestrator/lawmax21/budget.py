"""Budget with teeth: reserve BEFORE the call, settle AFTER it, hard-block on both sides.

v2.0's ledger only added numbers up; nothing consulted it and the default token
estimator returned 0, so the ceiling was decorative. Here the only way to make a paid
call is to hold a reservation, and `reserve()` raises rather than returning a number the
caller may ignore. A reserve for a successor line (protocol 44) is fenced off so the
current architecture cannot consume the budget that pays for its own challenger.
"""
import os

from .canonical import atomic_write_json, read_json, utc
from .eventlog import file_lock


class BudgetExhausted(Exception):
    """Raised INSTEAD of performing the call. There is no 'proceed anyway' argument."""


class StagnationDetected(Exception):
    pass


class BudgetLedger:
    def __init__(self, path, limits):
        """limits: {tokens, eur, calls, successor_reserve_fraction}"""
        self.path = os.path.abspath(path)
        self.lock = self.path + ".lock"
        self.limits = dict(limits)
        frac = float(self.limits.get("successor_reserve_fraction", 0.0))
        if not 0.0 <= frac < 1.0:
            raise ValueError("successor_reserve_fraction must be in [0, 1)")
        self.state = read_json(self.path) if os.path.exists(self.path) else {
            "spent": {"tokens": 0, "eur": 0.0, "calls": 0},
            "reserved": {"tokens": 0, "eur": 0.0},
            "entries": [], "open_reservations": {},
            "progress_windows": [],
        }

    # ---------------------------------------------------------------- limits
    def _cap(self, key, line):
        total = float(self.limits.get(key, 0) or 0)
        if line == "successor":
            return total
        return total * (1.0 - float(self.limits.get("successor_reserve_fraction", 0.0)))

    def committed(self, key):
        return float(self.state["spent"][key]) + float(self.state["reserved"].get(key, 0))

    def remaining(self, line="main"):
        return {k: self._cap(k, line) - self.committed(k) for k in ("tokens", "eur")}

    # ----------------------------------------------------------- reservation
    def reserve(self, reservation_id, role, est_tokens, est_eur, line="main"):
        with file_lock(self.lock):
            self._reload()
            if reservation_id in self.state["open_reservations"]:
                return self.state["open_reservations"][reservation_id]
            if self.limits.get("calls") and self.state["spent"]["calls"] >= self.limits["calls"]:
                raise BudgetExhausted(f"call ceiling reached ({self.limits['calls']})")
            for key, est in (("tokens", est_tokens), ("eur", est_eur)):
                cap = self._cap(key, line)
                if cap and self.committed(key) + est > cap:
                    raise BudgetExhausted(
                        f"{role}: reserving {est} {key} would exceed the {line} ceiling "
                        f"({self.committed(key):.4f} + {est} > {cap:.4f}) — call NOT made"
                    )
            self.state["reserved"]["tokens"] += est_tokens
            self.state["reserved"]["eur"] += est_eur
            rec = {"role": role, "tokens": est_tokens, "eur": est_eur, "line": line, "utc": utc()}
            self.state["open_reservations"][reservation_id] = rec
            self._flush()
            return rec

    def settle(self, reservation_id, actual_tokens, actual_eur, usage=None):
        with file_lock(self.lock):
            self._reload()
            rec = self.state["open_reservations"].pop(reservation_id, None)
            if rec is None:
                raise BudgetExhausted(f"settle without reservation ({reservation_id[:16]}…)")
            self.state["reserved"]["tokens"] -= rec["tokens"]
            self.state["reserved"]["eur"] -= rec["eur"]
            self.state["spent"]["tokens"] += actual_tokens
            self.state["spent"]["eur"] += actual_eur
            self.state["spent"]["calls"] += 1
            self.state["entries"].append({
                "utc": utc(), "role": rec["role"], "line": rec["line"],
                "estimated": {"tokens": rec["tokens"], "eur": rec["eur"]},
                "actual": {"tokens": actual_tokens, "eur": actual_eur},
                "usage": usage or {},
            })
            self._flush()
            over = []
            for key in ("tokens", "eur"):
                cap = self._cap(key, rec["line"])
                if cap and self.state["spent"][key] > cap:
                    over.append(f"{key}: {self.state['spent'][key]:.4f} > {cap:.4f}")
            if over:
                raise BudgetExhausted("POST-CALL OVERRUN — halting run: " + "; ".join(over))
            return self.state["spent"]

    def release(self, reservation_id):
        """Call failed: give the reservation back so a technical error costs nothing."""
        with file_lock(self.lock):
            self._reload()
            rec = self.state["open_reservations"].pop(reservation_id, None)
            if rec:
                self.state["reserved"]["tokens"] -= rec["tokens"]
                self.state["reserved"]["eur"] -= rec["eur"]
                self._flush()

    # ------------------------------------------------------- progress windows
    def close_window(self, window_id, best_score, min_delta, max_stagnant):
        """Protocol 14: spending must buy progress. N flat windows force escalation."""
        with file_lock(self.lock):
            self._reload()
            w = self.state["progress_windows"]
            prev = w[-1]["best_score"] if w else None
            improved = prev is None or (best_score - prev) >= min_delta
            w.append({"window": window_id, "best_score": best_score, "improved": improved,
                      "spent_tokens": self.state["spent"]["tokens"], "utc": utc()})
            self._flush()
            stagnant = 0
            for entry in reversed(w):
                if entry["improved"]:
                    break
                stagnant += 1
            if stagnant >= max_stagnant:
                raise StagnationDetected(
                    f"{stagnant} consecutive windows without >= {min_delta} improvement — "
                    "current architecture line must yield to successor/radical search"
                )
            return {"stagnant_windows": stagnant, "improved": improved}

    # ---------------------------------------------------------------- persist
    def _reload(self):
        if os.path.exists(self.path):
            self.state = read_json(self.path)

    def _flush(self):
        atomic_write_json(self.path, self.state)

    def snapshot(self):
        return {"limits": self.limits, "spent": dict(self.state["spent"]),
                "reserved": dict(self.state["reserved"]),
                "remaining_main": self.remaining("main"),
                "successor_reserve_eur": float(self.limits.get("eur", 0))
                * float(self.limits.get("successor_reserve_fraction", 0.0)),
                "open_reservations": len(self.state["open_reservations"])}
