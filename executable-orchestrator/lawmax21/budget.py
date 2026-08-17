"""Budget with teeth: reserve BEFORE the call, settle AFTER it, hard-block on both sides.

The ledger is currency-explicit. Historical LAWMAX runs retain their legacy ``eur`` contract;
new profiles may use ``currency`` + ``amount`` without lying about the provider's billing unit.
Every new settlement is bound to its logical request id so crash recovery can prove that a
recorded provider response was already charged and must never be re-sent.
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
        """Accept legacy {eur,...} or currency-explicit {currency, amount,...} limits."""
        self.path = os.path.abspath(path)
        self.lock = self.path + ".lock"
        self.limits = dict(limits)
        frac = float(self.limits.get("successor_reserve_fraction", 0.0))
        if not 0.0 <= frac < 1.0:
            raise ValueError("successor_reserve_fraction must be in [0, 1)")

        explicit = "amount" in self.limits or "currency" in self.limits
        legacy = "eur" in self.limits
        if explicit and legacy:
            raise ValueError("budget cannot mix legacy eur with currency-explicit amount")
        if explicit:
            if "amount" not in self.limits or not self.limits.get("currency"):
                raise ValueError("currency-explicit budget requires both currency and amount")
            self.money_key = "amount"
            self.currency = str(self.limits["currency"]).upper()
        elif legacy:
            self.money_key = "eur"
            self.currency = "EUR"
        else:
            raise ValueError("budget requires either legacy eur or currency + amount")

        self.state = read_json(self.path) if os.path.exists(self.path) else {
            "spent": {"tokens": 0, self.money_key: 0.0, "calls": 0},
            "reserved": {"tokens": 0, self.money_key: 0.0},
            "entries": [], "open_reservations": {},
            "progress_windows": [],
            "currency": self.currency,
            "money_key": self.money_key,
        }
        self._assert_state_contract()

    def _assert_state_contract(self):
        mk = self.money_key
        if mk not in self.state.get("spent", {}) or mk not in self.state.get("reserved", {}):
            raise ValueError(
                f"budget ledger monetary contract changed across resume: expected key {mk!r}")
        state_currency = self.state.get("currency")
        if state_currency and str(state_currency).upper() != self.currency:
            raise ValueError(
                f"budget ledger currency changed across resume: {state_currency} -> {self.currency}")

    # ---------------------------------------------------------------- limits
    def _cap(self, key, line):
        total = float(self.limits.get(key, 0) or 0)
        if line == "successor":
            return total
        return total * (1.0 - float(self.limits.get("successor_reserve_fraction", 0.0)))

    def committed(self, key):
        return float(self.state["spent"][key]) + float(self.state["reserved"].get(key, 0))

    def remaining(self, line="main"):
        return {k: self._cap(k, line) - self.committed(k)
                for k in ("tokens", self.money_key)}

    def within_ceiling(self):
        return (float(self.state["spent"]["tokens"]) <= float(self.limits.get("tokens", 0) or 0)
                and float(self.state["spent"][self.money_key])
                <= float(self.limits.get(self.money_key, 0) or 0))

    # -------------------------------------------------------- settlement state
    def is_open(self, reservation_id):
        self._reload()
        return reservation_id in self.state.get("open_reservations", {})

    def is_settled(self, reservation_id):
        self._reload()
        return any(e.get("reservation_id") == reservation_id
                   for e in self.state.get("entries", []))

    # ----------------------------------------------------------- reservation
    def reserve(self, reservation_id, role, est_tokens, est_money, line="main"):
        with file_lock(self.lock):
            self._reload()
            if reservation_id in self.state["open_reservations"]:
                return self.state["open_reservations"][reservation_id]
            if any(e.get("reservation_id") == reservation_id for e in self.state.get("entries", [])):
                raise BudgetExhausted(
                    f"logical request {reservation_id[:16]}… is already settled — refusing duplicate reservation")
            if self.limits.get("calls") and self.state["spent"]["calls"] >= self.limits["calls"]:
                raise BudgetExhausted(f"call ceiling reached ({self.limits['calls']})")
            for key, est in (("tokens", est_tokens), (self.money_key, est_money)):
                cap = self._cap(key, line)
                if cap and self.committed(key) + est > cap:
                    unit = self.currency if key == self.money_key else key
                    raise BudgetExhausted(
                        f"{role}: reserving {est} {unit} would exceed the {line} ceiling "
                        f"({self.committed(key):.4f} + {est} > {cap:.4f}) — call NOT made"
                    )
            self.state["reserved"]["tokens"] += est_tokens
            self.state["reserved"][self.money_key] += est_money
            rec = {"role": role, "tokens": est_tokens, self.money_key: est_money,
                   "currency": self.currency, "line": line, "utc": utc()}
            self.state["open_reservations"][reservation_id] = rec
            self._flush()
            return rec

    def settle(self, reservation_id, actual_tokens, actual_money, usage=None):
        with file_lock(self.lock):
            self._reload()
            # Idempotent crash recovery: if settlement was durably recorded but the caller
            # crashed before writing its metadata, returning the existing spend is correct;
            # charging it again would be false accounting.
            if any(e.get("reservation_id") == reservation_id for e in self.state.get("entries", [])):
                return self.state["spent"]
            rec = self.state["open_reservations"].pop(reservation_id, None)
            if rec is None:
                raise BudgetExhausted(f"settle without reservation ({reservation_id[:16]}…)")
            self.state["reserved"]["tokens"] -= rec["tokens"]
            self.state["reserved"][self.money_key] -= rec[self.money_key]
            self.state["spent"]["tokens"] += actual_tokens
            self.state["spent"][self.money_key] += actual_money
            self.state["spent"]["calls"] += 1
            self.state["entries"].append({
                "reservation_id": reservation_id,
                "utc": utc(), "role": rec["role"], "line": rec["line"],
                "currency": self.currency,
                "estimated": {"tokens": rec["tokens"], self.money_key: rec[self.money_key]},
                "actual": {"tokens": actual_tokens, self.money_key: actual_money},
                "usage": usage or {},
            })
            self._flush()
            over = []
            for key in ("tokens", self.money_key):
                cap = self._cap(key, rec["line"])
                if cap and self.state["spent"][key] > cap:
                    unit = self.currency if key == self.money_key else key
                    over.append(f"{unit}: {self.state['spent'][key]:.4f} > {cap:.4f}")
            if over:
                raise BudgetExhausted("POST-CALL OVERRUN — halting run: " + "; ".join(over))
            return self.state["spent"]

    def release(self, reservation_id):
        """Call failed before an accepted provider response: give the reservation back."""
        with file_lock(self.lock):
            self._reload()
            rec = self.state["open_reservations"].pop(reservation_id, None)
            if rec:
                self.state["reserved"]["tokens"] -= rec["tokens"]
                self.state["reserved"][self.money_key] -= rec[self.money_key]
                self._flush()

    # ------------------------------------------------------- progress windows
    def close_window(self, window_id, best_score, min_delta, max_stagnant):
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
            self._assert_state_contract()

    def _flush(self):
        atomic_write_json(self.path, self.state)

    def snapshot(self):
        reserve = (float(self.limits.get(self.money_key, 0) or 0)
                   * float(self.limits.get("successor_reserve_fraction", 0.0)))
        out = {"limits": self.limits, "currency": self.currency,
               "spent": dict(self.state["spent"]),
               "reserved": dict(self.state["reserved"]),
               "remaining_main": self.remaining("main"),
               "successor_reserve_amount": reserve,
               "open_reservations": len(self.state["open_reservations"])}
        if self.money_key == "eur":
            out["successor_reserve_eur"] = reserve
        return out
