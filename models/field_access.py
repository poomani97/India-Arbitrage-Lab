"""
India Arbitrage Lab
Field access helper

The Opportunity model uses the names confidence_score, liquidity_score,
capital_required, estimated_margin and opportunity_score, while the
qualification, ranking and risk modules were written against the short
names confidence, liquidity, capital, margin and score. This helper reads
either spelling, from objects or dicts, so both keep working.

Units: confidence and fill_probability are fractions from 0 to 1.
"""

from typing import Any

_MISSING = object()

FIELD_ALIASES = {
    "confidence": ("confidence_score",),
    "liquidity": ("liquidity_score",),
    "capital": ("capital_required",),
    "margin": ("estimated_margin",),
    "score": ("opportunity_score",),
}


def get_field(obj: Any, key: str, default: Any = None) -> Any:
    names = (key,) + FIELD_ALIASES.get(key, ())

    for name in names:
        if isinstance(obj, dict):
            value = obj.get(name, _MISSING)
        else:
            value = getattr(obj, name, _MISSING)

        if value is not _MISSING:
            return value

    return default
