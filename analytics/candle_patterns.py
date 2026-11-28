"""
India Arbitrage Lab
Basic candlestick pattern detection (plain pandas, no extra libraries).

Rules are textbook and simple. They flag the SHAPE of recent candles only;
hammer / shooting star also check a short prior move (close 1 bar ago versus
4 bars ago). They are not signals by themselves and are not tested for profit.

detect_patterns(df) needs open, high, low, close and returns a DataFrame of
True/False columns with the same index.
"""

import pandas as pd

PATTERN_NAMES = [
    "doji", "hammer", "shooting_star",
    "bullish_engulfing", "bearish_engulfing",
    "morning_star", "evening_star",
]

BULLISH = {"hammer", "bullish_engulfing", "morning_star"}
BEARISH = {"shooting_star", "bearish_engulfing", "evening_star"}


def detect_patterns(df: pd.DataFrame) -> pd.DataFrame:
    for column in ("open", "high", "low", "close"):
        if column not in df.columns:
            raise ValueError(f"Missing column: {column}")

    o, h, l, c = (df[x].astype(float) for x in ("open", "high", "low", "close"))
    body = (c - o).abs()
    rng = h - l
    upper = h - pd.concat([o, c], axis=1).max(axis=1)
    lower = pd.concat([o, c], axis=1).min(axis=1) - l
    bull, bear = c > o, c < o

    fell = c.shift(1) < c.shift(4)
    rose = c.shift(1) > c.shift(4)

    out = pd.DataFrame(index=df.index)
    out["doji"] = (rng > 0) & (body <= 0.1 * rng)
    out["hammer"] = (body > 0) & (lower >= 2 * body) & (upper <= 0.5 * body) & fell
    out["shooting_star"] = (body > 0) & (upper >= 2 * body) & (lower <= 0.5 * body) & rose

    po, pc, pb = o.shift(1), c.shift(1), body.shift(1)
    out["bullish_engulfing"] = (pc < po) & bull & (o <= pc) & (c >= po) & (body > pb)
    out["bearish_engulfing"] = (pc > po) & bear & (o >= pc) & (c <= po) & (body > pb)

    o2, c2, b2 = o.shift(2), c.shift(2), body.shift(2)
    small_mid = body.shift(1) <= 0.3 * b2
    out["morning_star"] = (c2 < o2) & small_mid & bull & (c > (o2 + c2) / 2) & (b2 > 0)
    out["evening_star"] = (c2 > o2) & small_mid & bear & (c < (o2 + c2) / 2) & (b2 > 0)

    return out.fillna(False).astype(bool)[PATTERN_NAMES]


def pattern_counts(patterns: pd.DataFrame) -> dict:
    return {name: int(patterns[name].sum()) for name in patterns.columns}
