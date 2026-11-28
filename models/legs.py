"""
India Arbitrage Lab
Standard leg format and executability checks.

Strategies describe legs in different ways (side vs action, price vs
market_price). normalize_leg() reads all of them into one shape:
    instrument, side (BUY/SELL), price, quantity, contract_key, problems

The strategies' own safety flags are RESPECTED, never overridden:
observation-only legs, legs without a side, execution_enabled=False, an
unverified hedge, or observation_only metadata make an opportunity
non-executable. research_only / live_trading_allowed=False block LIVE
brokers only (live_problems); the paper account may still trade them.

contract_key separates contracts that share an instrument name, e.g.
the 25900 call and the 26100 call of a box spread, or NSE vs BSE.
"""

from typing import Any, Dict, List

KNOWN_INSTRUMENTS = {"CASH", "FUTURES", "NEAR_FUTURES", "FAR_FUTURES", "CALL", "PUT", "ETF"}


def _date_part(value: Any) -> str:
    return str(value)[:10] if value not in (None, "") else ""


def normalize_leg(leg: Dict[str, Any], default_symbol: str = "") -> Dict[str, Any]:
    instrument = str(leg.get("instrument") or leg.get("symbol") or "").strip().upper()
    problems: List[str] = []

    raw_side = str(leg.get("side") or leg.get("action") or "").strip().upper()
    side = raw_side if raw_side in ("BUY", "SELL") else ""

    if not side:
        if "RESEARCH" in raw_side or "OBSERVATION" in raw_side:
            problems.append(f"Leg is {raw_side} only; the strategy does not allow trading it.")
        else:
            problems.append("Leg has no BUY/SELL side.")

    if leg.get("execution_enabled") is False:
        problems.append("Leg has execution_enabled=False.")

    price = leg.get("price", leg.get("market_price"))
    try:
        price = float(price)
        if not price > 0:
            raise ValueError
    except (TypeError, ValueError):
        price = None
        problems.append("Leg has no valid price.")

    quantity = leg.get("quantity")
    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
        problems.append("Leg quantity must be a positive integer.")
        quantity = None

    if not instrument:
        problems.append("Leg has no instrument.")

    if instrument in KNOWN_INSTRUMENTS:
        base = str(leg.get("symbol") or default_symbol).strip().upper()
        parts = [base, instrument]
    else:
        parts = [instrument]          # e.g. NIFTY / BANKNIFTY legs: instrument is the symbol
    if leg.get("strike") not in (None, ""):
        parts.append(f"{float(leg['strike']):g}")
    expiry = _date_part(leg.get("expiry") or leg.get("expiry_date"))
    if expiry:
        parts.append(expiry)
    if leg.get("exchange"):
        parts.append(str(leg["exchange"]).upper())

    return {
        "instrument": instrument,
        "side": side,
        "price": price,
        "quantity": quantity,
        "contract_key": ":".join(p for p in parts if p),
        "problems": problems,
        "research_only": bool(leg.get("research_only")),
    }


def executable_problems(opportunity: Any, allow_single_leg: bool = False) -> List[str]:
    """Reasons this opportunity cannot be traded. Empty list = executable."""
    reasons: List[str] = []
    legs = getattr(opportunity, "legs", None) or []
    metadata = getattr(opportunity, "metadata", None) or {}

    if not legs:
        return ["Opportunity has no legs."]

    for leg in legs:
        reasons.extend(normalize_leg(leg, getattr(opportunity, "symbol", ""))["problems"])

    if metadata.get("observation_only"):
        reasons.append("Strategy marks this opportunity observation_only.")
    if metadata.get("complete_hedge_verified") is False:
        reasons.append("Hedge is not verified as complete.")
    if len(legs) < 2 and not allow_single_leg:
        reasons.append("Single-leg opportunity would be unhedged (allow_single_leg is off).")

    return list(dict.fromkeys(reasons))


def live_problems(opportunity: Any) -> List[str]:
    """Extra reasons that block LIVE (real-money) trading only.

    A strategy that says research_only or live_trading_allowed=False may
    still be traded on the paper account; it must never reach a live broker.
    """
    reasons: List[str] = []
    metadata = getattr(opportunity, "metadata", None) or {}

    if metadata.get("research_only"):
        reasons.append("Strategy marks this opportunity research_only (paper only).")
    if metadata.get("live_trading_allowed") is False:
        reasons.append("Strategy does not allow live trading.")
    for leg in getattr(opportunity, "legs", None) or []:
        if leg.get("research_only"):
            reasons.append("A leg is flagged research_only (paper only).")
            break

    return reasons
