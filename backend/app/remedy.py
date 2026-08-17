"""Deterministic statutory damages.

Where Massachusetts law fixes a remedy (treble the security deposit, up to three
months' rent for quiet-enjoyment or reprisal), we compute it in code from figures
extracted into the document metadata rather than trusting the model's arithmetic.
Statutes without a fixed formula (e.g. c.93A actual damages) return no amount and
the model's estimate stands.
"""
import re
from dataclasses import dataclass
from typing import Callable, Optional


@dataclass
class Damages:
    amount: Optional[float]
    basis: str


def money(value: Optional[str]) -> Optional[float]:
    """Parse a currency-ish string like '$1,500' or '1500.00' into a float, or None."""
    if not value:
        return None
    cleaned = re.sub(r"[^0-9.]", "", value)
    if not cleaned or cleaned == ".":
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _treble_deposit(inp: dict) -> Optional[Damages]:
    dep = inp.get("security_deposit")
    if not dep:
        return None
    return Damages(3 * dep, "Treble the security deposit under M.G.L. c.186 §15B(6)(e).")


def _three_months_rent(reason: str, cite: str) -> Callable[[dict], Optional[Damages]]:
    def rule(inp: dict) -> Optional[Damages]:
        rent = inp.get("monthly_rent")
        if not rent:
            return None
        return Damages(3 * rent, f"Up to three months' rent for {reason} under {cite}.")
    return rule


# Keyed by statute id (matches Statute.id / the corpus).
_RULES: dict[str, Callable[[dict], Optional[Damages]]] = {
    "186-15B": _treble_deposit,
    "186-14": _three_months_rent("breach of quiet enjoyment", "M.G.L. c.186 §14"),
    "186-18": _three_months_rent("unlawful reprisal", "M.G.L. c.186 §18"),
}


def compute_damages(statute_id: str, inputs: dict) -> Damages:
    """Return the statutory damages for `statute_id` given extracted `inputs`
    (`security_deposit`, `monthly_rent` as floats). Amount is None when no fixed
    remedy applies or the needed input is missing."""
    rule = _RULES.get((statute_id or "").strip())
    if rule is None:
        return Damages(None, "")
    result = rule(inputs)
    return result if result is not None else Damages(None, "")
