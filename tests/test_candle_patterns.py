import pandas as pd
import pytest

from analytics.candle_patterns import PATTERN_NAMES, detect_patterns, pattern_counts


def candles(rows):
    return pd.DataFrame(rows, columns=["open", "high", "low", "close"])


def test_doji():
    out = detect_patterns(candles([[100, 105, 95, 100.5]]))
    assert out["doji"].iloc[0]


def test_hammer_after_a_fall():
    rows = [[110, 111, 109, 109.5], [109, 110, 107, 107.5], [107, 108, 105, 105.5],
            [105, 106, 103, 103.5], [103, 103.6, 98, 103.5]]
    assert detect_patterns(candles(rows))["hammer"].iloc[-1]


def test_same_hammer_shape_without_prior_fall_is_ignored():
    rows = [[100, 101, 99, 100]] * 4 + [[103, 103.6, 98, 103.5]]
    assert not detect_patterns(candles(rows))["hammer"].iloc[-1]


def test_shooting_star_after_a_rise():
    rows = [[100, 101, 99.5, 100.5], [101, 102, 100.5, 101.5], [102, 103, 101.5, 102.5],
            [103, 104, 102.5, 103.5], [104, 110, 103.9, 104.3]]
    assert detect_patterns(candles(rows))["shooting_star"].iloc[-1]


def test_engulfing_pair():
    bull = detect_patterns(candles([[105, 106, 99, 100], [99, 108, 98, 107]]))
    assert bull["bullish_engulfing"].iloc[-1] and not bull["bearish_engulfing"].iloc[-1]
    bear = detect_patterns(candles([[100, 106, 99, 105], [106, 107, 97, 98]]))
    assert bear["bearish_engulfing"].iloc[-1] and not bear["bullish_engulfing"].iloc[-1]


def test_morning_and_evening_star():
    morning = detect_patterns(candles([[110, 111, 99, 100], [99, 100, 98, 99.5], [100, 109, 99.5, 108]]))
    assert morning["morning_star"].iloc[-1]
    evening = detect_patterns(candles([[100, 111, 99, 110], [111, 112, 110.5, 111.2], [110, 110.5, 101, 102]]))
    assert evening["evening_star"].iloc[-1]


def test_output_shape_and_counts():
    out = detect_patterns(candles([[100, 101, 99, 100.5]] * 6))
    assert list(out.columns) == PATTERN_NAMES and len(out) == 6
    assert set(pattern_counts(out)) == set(PATTERN_NAMES)


def test_missing_column_rejected():
    with pytest.raises(ValueError):
        detect_patterns(pd.DataFrame({"open": [1], "close": [1]}))
