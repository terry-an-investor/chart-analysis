"""
Tests for bar utility functions.

Tests helper functions used in bar feature calculations.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.analysis._bar_utils import (
    calculate_blend_candle,
    calculate_consecutive_streak,
    calculate_ema_features,
    calculate_engulfing,
    calculate_failed_breakouts,
    calculate_tails,
    safe_divide_array,
)


def test_safe_divide_array_normal() -> None:
    """Test safe division with normal values."""
    numerator = np.array([10, 20, 30])
    denominator = np.array([2, 4, 5])

    result = safe_divide_array(numerator, denominator)

    expected = np.array([5.0, 5.0, 6.0])
    np.testing.assert_array_equal(result, expected)


def test_safe_divide_array_with_zeros() -> None:
    """Test safe division handles zeros correctly."""
    numerator = np.array([10, 20, 30])
    denominator = np.array([2, 0, 5])

    result = safe_divide_array(numerator, denominator)

    assert result[0] == 5.0
    assert np.isnan(result[1])
    assert result[2] == 6.0


def test_calculate_tails_bull_bar() -> None:
    """Test tail calculation for bull bar."""
    high = np.array([110])
    open_price = np.array([100])
    close = np.array([108])
    low = np.array([98])

    upper_tail, lower_tail = calculate_tails(high, open_price, close, low)

    assert upper_tail[0] == 2  # 110 - 108
    assert lower_tail[0] == 2  # 100 - 98


def test_calculate_tails_bear_bar() -> None:
    """Test tail calculation for bear bar."""
    high = np.array([110])
    open_price = np.array([108])
    close = np.array([100])
    low = np.array([98])

    upper_tail, lower_tail = calculate_tails(high, open_price, close, low)

    assert upper_tail[0] == 2  # 110 - 108
    assert lower_tail[0] == 2  # 100 - 98


def test_calculate_blend_candle() -> None:
    """Test blended 2-bar candle calculation."""
    prev_open = np.array([100])
    prev_high = np.array([105])
    prev_low = np.array([98])
    open_price = np.array([103])
    high = np.array([110])
    low = np.array([102])
    close = np.array([108])

    blend_open, blend_close, blend_high, blend_low = calculate_blend_candle(
        prev_open, prev_high, prev_low, open_price, high, low, close
    )

    assert blend_open[0] == 100
    assert blend_close[0] == 108
    assert blend_high[0] == 110  # max(110, 105)
    assert blend_low[0] == 98  # min(102, 98)


def test_calculate_consecutive_streak() -> None:
    """Test consecutive trend bar streak calculation."""
    df = pd.DataFrame({"close": [100, 101, 102, 103, 102, 101, 102, 103, 104]})

    is_trend_bar = pd.Series([True, True, True, True, False, True, True, True, True])
    bar_color = pd.Series([1, 1, 1, 1, -1, -1, 1, 1, 1])

    result = calculate_consecutive_streak(is_trend_bar, bar_color, df)

    # First 4 bars: consecutive bull trend
    assert result[0] == 1
    assert result[1] == 2
    assert result[2] == 3
    assert result[3] == 4


def test_calculate_engulfing_bull() -> None:
    """Test bull engulfing pattern detection."""
    bar_color = pd.Series([1, -1, 1, 1])
    prev_body_bottom = pd.Series([100, 102, 98, 104]).shift(1)
    curr_body_bottom = pd.Series([100, 102, 98, 104])
    prev_body_top = pd.Series([105, 104, 106, 108]).shift(1)
    curr_body_top = pd.Series([105, 104, 106, 108])

    is_bull, is_bear = calculate_engulfing(
        bar_color, prev_body_bottom, curr_body_bottom, prev_body_top, curr_body_top
    )

    # Check that we got boolean arrays back
    assert isinstance(is_bull, pd.Series)
    assert isinstance(is_bear, pd.Series)


def test_calculate_engulfing_bear() -> None:
    """Test bear engulfing pattern detection."""
    bar_color = pd.Series([-1, 1, -1, -1])
    prev_body_bottom = pd.Series([100, 102, 98, 104]).shift(1)
    curr_body_bottom = pd.Series([100, 102, 98, 104])
    prev_body_top = pd.Series([105, 104, 106, 108]).shift(1)
    curr_body_top = pd.Series([105, 104, 106, 108])

    is_bull, is_bear = calculate_engulfing(
        bar_color, prev_body_bottom, curr_body_bottom, prev_body_top, curr_body_top
    )

    assert isinstance(is_bull, pd.Series)
    assert isinstance(is_bear, pd.Series)


def test_calculate_failed_breakouts_high() -> None:
    """Test failed breakout high detection."""
    high = pd.Series([105, 110, 112, 108])
    low = pd.Series([100, 105, 108, 104])
    close = pd.Series([103, 108, 109, 106])
    prev_high = high.shift(1)
    prev_low = low.shift(1)
    bar_color = pd.Series([1, 1, -1, -1])

    (failed_high, failed_low, strict_failed_high, strict_failed_low) = calculate_failed_breakouts(
        high, low, close, prev_high, prev_low, bar_color
    )

    assert isinstance(failed_high, pd.Series)
    assert isinstance(failed_low, pd.Series)


def test_calculate_ema_features() -> None:
    """Test EMA feature calculations."""
    close = np.array([100, 102, 104, 106, 108])
    high = np.array([102, 104, 106, 108, 110])
    low = np.array([98, 100, 102, 104, 106])
    ema = np.array([100, 101, 103, 105, 107])

    (dist_to_ema, bar_pos_ema, ema_touch, gap_below_ema, gap_above_ema) = calculate_ema_features(
        close, high, low, ema
    )

    assert len(dist_to_ema) == 5
    assert len(bar_pos_ema) == 5
    assert isinstance(ema_touch, np.ndarray)
    assert isinstance(gap_below_ema, np.ndarray)
    assert isinstance(gap_above_ema, np.ndarray)


def test_calculate_ema_features_with_zero_ema() -> None:
    """Test EMA features handle zero EMA values."""
    close = np.array([100, 102])
    high = np.array([102, 104])
    low = np.array([98, 100])
    ema = np.array([0, 101])

    (dist_to_ema, bar_pos_ema, ema_touch, gap_below_ema, gap_above_ema) = calculate_ema_features(
        close, high, low, ema
    )

    # First value should be NaN due to zero EMA
    assert np.isnan(dist_to_ema[0])
    assert not np.isnan(dist_to_ema[1])
