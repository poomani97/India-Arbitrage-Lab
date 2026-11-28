"""
India Arbitrage Lab
Estimators for the fields the strategies leave at zero:
margin, confidence, fill probability and liquidity.

IMPORTANT: these are transparent HEURISTICS, not exchange data.
- Margin uses flat percentages, not SPAN. Replace with your broker's margin
  API before real money. Defaults are deliberately conservative.
- Confidence and fill probability are uncalibrated scores. Calibrate them on
  paper-trading results before trusting them.
- Liquidity stays 0 (unknown) unless the data row carries a volume column.
Only fields still at their default 0 are filled; values a strategy or data
feed supplied are never overwritten. Every estimate is recorded in
opportunity.metadata["estimates"].
"""

from typing import Any, Dict, Optional

from models.legs import normalize_leg

FUTURES_NAMES = {"FUTURES", "NEAR_FUTURES", "FAR_FUTURES"}
OPTION_NAMES = {"CALL", "PUT"}


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


class MarginModel:
    def __init__(self, futures_pct: float = 0.12, option_sell_pct: float = 0.15):
        self.futures_pct = futures_pct          # placeholder for SPAN, CONFIRM
        self.option_sell_pct = option_sell_pct  # placeholder, CONFIRM

    def estimate(self, opportunity: Any) -> Dict[str, Any]:
        total = 0.0
        for leg in getattr(opportunity, "legs", None) or []:
            norm = normalize_leg(leg, getattr(opportunity, "symbol", ""))
            instrument, side = norm["instrument"], norm["side"]
            price, qty = norm["price"], norm["quantity"]
            if price is None or qty is None:
                return self._fallback(opportunity)
            notional = price * qty
            if instrument in FUTURES_NAMES:
                total += notional * self.futures_pct
            elif instrument in OPTION_NAMES:
                total += notional if side == "BUY" else notional * self.option_sell_pct
            else:
                total += notional               # cash-like: full value, conservative
        if total <= 0:
            return self._fallback(opportunity)
        return {"margin": total, "method": "leg_percentages"}

    @staticmethod
    def _fallback(opportunity: Any) -> Dict[str, Any]:
        capital = float(getattr(opportunity, "capital_required", 0.0) or 0.0)
        return {"margin": capital, "method": "capital_required_fallback"}


def estimate_confidence(opportunity: Any) -> float:
    """0-1. Rewards a large net/gross edge, known costs and a cost cushion."""
    gross = float(getattr(opportunity, "gross_edge", 0.0) or 0.0)
    net = float(getattr(opportunity, "net_edge", 0.0) or 0.0)
    costs = float(getattr(opportunity, "estimated_costs", 0.0) or 0.0)
    buffer = float(getattr(opportunity, "risk_buffer", 0.0) or 0.0)

    if gross <= 0 or net <= 0:
        return 0.0

    breakdown = getattr(opportunity, "cost_breakdown", None) or {}
    cost_known = 1.0 if (breakdown.get("cost_input_provided")
                         or breakdown.get("estimated_costs_per_unit")) and costs > 0 else 0.0
    edge_quality = _clamp(net / gross)
    cushion = _clamp((net / max(costs + buffer, 1e-9)) / 3.0)

    return round(0.4 * edge_quality + 0.4 * cost_known + 0.2 * cushion, 4)


def estimate_fill_probability(opportunity: Any, volume: Optional[float] = None) -> float:
    """0-1. Every leg must fill, so 0.9 ** legs; thin volume lowers it."""
    legs = max(len(getattr(opportunity, "legs", None) or []), 1)
    probability = 0.9 ** legs
    if volume is not None and volume > 0:
        qty = sum(int(leg.get("quantity") or 0) for leg in opportunity.legs)
        participation = qty / volume
        probability *= 1.0 - _clamp(participation * 10.0, 0.0, 0.5)
    return round(_clamp(probability, 0.0, 1.0), 4)


def estimate_liquidity(volume: Optional[float], target_volume: float = 1_000_000.0) -> float:
    """0-100. Unknown (no volume) stays 0 rather than being invented."""
    if volume is None or volume <= 0:
        return 0.0
    return round(_clamp(volume / target_volume, 0.0, 1.0) * 100.0, 2)


class OpportunityEnricher:
    VOLUME_COLUMNS = ("futures_volume", "volume")

    def __init__(self, margin_model: Optional[MarginModel] = None):
        self.margin_model = margin_model or MarginModel()

    def _volume(self, row: Optional[Dict[str, Any]]) -> Optional[float]:
        for name in self.VOLUME_COLUMNS:
            value = (row or {}).get(name)
            try:
                if value is not None and float(value) > 0:
                    return float(value)
            except (TypeError, ValueError):
                continue
        return None

    def enrich(self, opportunity: Any, row: Optional[Dict[str, Any]] = None) -> Any:
        volume = self._volume(row)
        notes: Dict[str, Any] = {"heuristic": True}

        if not opportunity.capital_required:
            gross = 0.0
            for leg in opportunity.legs or []:
                norm = normalize_leg(leg, opportunity.symbol)
                if norm["price"] and norm["quantity"]:
                    gross += norm["price"] * norm["quantity"]
            if gross > 0:
                opportunity.capital_required = gross
                notes["capital"] = "gross leg notional (conservative)"

        if not opportunity.estimated_margin:
            result = self.margin_model.estimate(opportunity)
            opportunity.estimated_margin = float(result["margin"])
            notes["margin"] = result["method"]

        if not opportunity.confidence_score:
            opportunity.confidence_score = estimate_confidence(opportunity)
            notes["confidence"] = "edge_quality+cost_known+cushion"

        if not opportunity.fill_probability:
            opportunity.fill_probability = estimate_fill_probability(opportunity, volume)
            notes["fill_probability"] = "0.9^legs with volume penalty"

        if not opportunity.liquidity_score:
            opportunity.liquidity_score = estimate_liquidity(volume)
            notes["liquidity"] = "from volume" if volume else "unknown (left 0)"

        opportunity.metadata.setdefault("estimates", {}).update(notes)
        return opportunity
