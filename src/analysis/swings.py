"""
Swing point detection and classification.

Implements Al Brooks fractal/swing detection with future function elimination.
"""

from __future__ import annotations

import logging
from typing import Literal, Optional

import numpy as np
import numpy.typing as npt
import pandas as pd

logger = logging.getLogger(__name__)

from ._structure_utils import (
    DEFAULT_SWING_WINDOW,
    PRICE_TOLERANCE_PCT,
    classify_swing_high,
    classify_swing_low,
    detect_duplicates,
    merge_sorted_events,
)


def detect_swings(
    df: pd.DataFrame,
    window: int = DEFAULT_SWING_WINDOW,
    high_col: str = "high",
    low_col: str = "low",
) -> pd.DataFrame:
    """
    Detect swing highs and lows using Al Brooks fractal method.

    A swing high occurs when a bar's high is the highest among N bars before
    and after it. Signal is shifted forward by N periods to eliminate lookahead bias.

    Args:
        df: DataFrame with OHLC data
        window: Confirmation period (bars before/after for swing detection)
        high_col: Name of high price column
        low_col: Name of low price column

    Returns:
        DataFrame with added columns:
            - swing_high_confirmed: bool (True at confirmation bar)
            - swing_low_confirmed: bool
            - swing_high_price: float (historical high price)
            - swing_low_price: float (historical low price)
            - plot_swing_high: float (for chart visualization)
            - plot_swing_low: float
    """
    df = df.copy()

    highs = df[high_col]
    lows = df[low_col]

    scan_window = 2 * window + 1

    rolling_max = highs.rolling(window=scan_window, center=True, min_periods=1).max()
    rolling_min = lows.rolling(window=scan_window, center=True, min_periods=1).min()

    is_high_raw = (highs == rolling_max) & highs.notna()
    is_low_raw = (lows == rolling_min) & lows.notna()

    is_high_arr = is_high_raw.to_numpy()
    is_low_arr = is_low_raw.to_numpy()

    is_high_dedup = detect_duplicates(is_high_arr)
    is_low_dedup = detect_duplicates(is_low_arr)

    shifted_high_arr = np.roll(is_high_dedup, window)
    shifted_high_arr[:window] = False
    shifted_low_arr = np.roll(is_low_dedup, window)
    shifted_low_arr[:window] = False

    df["swing_high_confirmed"] = shifted_high_arr
    df["swing_low_confirmed"] = shifted_low_arr

    df["swing_high_price"] = highs.shift(window)
    df["swing_low_price"] = lows.shift(window)

    df.loc[~df["swing_high_confirmed"], "swing_high_price"] = np.nan
    df.loc[~df["swing_low_confirmed"], "swing_low_price"] = np.nan

    df["plot_swing_high"] = df["swing_high_price"].shift(-window)
    df["plot_swing_low"] = df["swing_low_price"].shift(-window)

    high_count = shifted_high_arr.sum()
    low_count = shifted_low_arr.sum()
    logger.debug(f"Detected {high_count} swing highs and {low_count} swing lows (window={window})")

    return df


def classify_swings(df: pd.DataFrame, tolerance_pct: float = PRICE_TOLERANCE_PCT) -> pd.DataFrame:
    """
    Classify swings as HH, LH, HL, LL, DT, or DB.

    Maintains major swing points as structural support/resistance levels.

    Args:
        df: DataFrame with swing detection results
        tolerance_pct: Price tolerance for identifying double tops/bottoms

    Returns:
        DataFrame with added columns:
            - swing_type: str (HH, LH, HL, LL, DT, DB)
            - major_high: float (current resistance level)
            - major_low: float (current support level)
    """
    if "swing_high_confirmed" not in df.columns:
        df = detect_swings(df)

    df = df.copy()

    df["swing_type"] = pd.Series([np.nan] * len(df), dtype=object)
    df["major_high"] = np.nan
    df["major_low"] = np.nan

    last_h_price = -np.inf
    last_l_price = np.inf

    current_major_high = np.nan
    current_major_low = np.nan

    high_indices = df.index[df["swing_high_confirmed"]].tolist()
    low_indices = df.index[df["swing_low_confirmed"]].tolist()

    events = merge_sorted_events(high_indices, low_indices)

    for idx, event_type in events:
        if event_type == "high":
            curr_price = df.at[idx, "swing_high_price"]
            label = classify_swing_high(curr_price, last_h_price, tolerance_pct)

            last_h_price = curr_price
            df.at[idx, "swing_type"] = label

            current_major_high = curr_price
            df.at[idx, "major_high"] = current_major_high
            df.at[idx, "major_low"] = current_major_low

        elif event_type == "low":
            curr_price = df.at[idx, "swing_low_price"]
            label = classify_swing_low(curr_price, last_l_price, tolerance_pct)

            last_l_price = curr_price
            df.at[idx, "swing_type"] = label

            current_major_low = curr_price
            df.at[idx, "major_low"] = current_major_low
            df.at[idx, "major_high"] = current_major_high

    df["major_high"] = df["major_high"].ffill()
    df["major_low"] = df["major_low"].ffill()

    return df


def classify_swings_v2(
    df: pd.DataFrame, tolerance_pct: float = PRICE_TOLERANCE_PCT
) -> pd.DataFrame:
    """
    Classify swings with breakout confirmation logic.

    Major levels only update after price breaks through them, following
    Al Brooks principle: major low rises only after new high confirmation.

    Args:
        df: DataFrame with swing detection results
        tolerance_pct: Price tolerance for double tops/bottoms

    Returns:
        DataFrame with columns:
            - swing_type: str
            - major_high, major_low: float
            - trend_bias: int (1=Bull, -1=Bear, 0=Neutral)
    """
    if "swing_high_confirmed" not in df.columns:
        df = detect_swings(df)

    df = df.copy()

    df["swing_type"] = pd.Series([np.nan] * len(df), dtype=object)
    df["major_high"] = np.nan
    df["major_low"] = np.nan
    df["trend_bias"] = 0

    last_h_price = -np.inf
    last_l_price = np.inf

    candidate_major_low = np.nan
    candidate_major_high = np.nan

    first_valid_high = df["high"].dropna().iloc[0] if df["high"].notna().any() else np.nan
    first_valid_low = df["low"].dropna().iloc[0] if df["low"].notna().any() else np.nan
    active_major_high = first_valid_high
    active_major_low = first_valid_low

    curr_bias = 0

    high_indices = df.index[df["swing_high_confirmed"]].tolist()
    low_indices = df.index[df["swing_low_confirmed"]].tolist()
    events = merge_sorted_events(high_indices, low_indices)

    for idx, event_type in events:
        if event_type == "high":
            price = df.at[idx, "swing_high_price"]

            label = classify_swing_high(price, last_h_price, tolerance_pct)
            last_h_price = price
            df.at[idx, "swing_type"] = label

            candidate_major_high = price

            if curr_bias == 1:
                if price > active_major_high:
                    if pd.notna(candidate_major_low) and candidate_major_low > active_major_low:
                        active_major_low = candidate_major_low
                    active_major_high = price
            elif curr_bias == -1:
                if price > active_major_high:
                    curr_bias = 1
                    if pd.notna(candidate_major_low):
                        active_major_low = candidate_major_low
                    active_major_high = price
            else:
                active_major_high = price
                if label == "HH":
                    curr_bias = 1

        elif event_type == "low":
            price = df.at[idx, "swing_low_price"]

            label = classify_swing_low(price, last_l_price, tolerance_pct)
            last_l_price = price
            df.at[idx, "swing_type"] = label

            candidate_major_low = price

            if curr_bias == -1:
                if price < active_major_low:
                    if pd.notna(candidate_major_high) and candidate_major_high < active_major_high:
                        active_major_high = candidate_major_high
                    active_major_low = price
            elif curr_bias == 1:
                if price < active_major_low:
                    curr_bias = -1
                    if pd.notna(candidate_major_high):
                        active_major_high = candidate_major_high
                    active_major_low = price
            else:
                active_major_low = price
                if label == "LL":
                    curr_bias = -1

        df.at[idx, "major_high"] = active_major_high
        df.at[idx, "major_low"] = active_major_low
        df.at[idx, "trend_bias"] = curr_bias

    df["major_high"] = df["major_high"].ffill()
    df["major_low"] = df["major_low"].ffill()
    df["trend_bias"] = df["trend_bias"].ffill().fillna(0).astype(int)

    return df


def classify_swings_v3(
    df: pd.DataFrame, window: int = DEFAULT_SWING_WINDOW, tolerance_pct: float = PRICE_TOLERANCE_PCT
) -> pd.DataFrame:
    """
    Classify swings with bar-by-bar close-based breakout detection.

    Uses closing price (not high/low) to confirm breakouts, filtering
    false breaks. Levels disappear after breakthrough until new structure forms.

    Args:
        df: DataFrame with OHLC data
        window: Swing detection window
        tolerance_pct: Price tolerance for double tops/bottoms

    Returns:
        DataFrame with columns:
            - swing_type: str
            - major_high, major_low: float (active only during trend)
            - market_trend: int (1=Bull, -1=Bear, 0=Neutral)
    """
    if "swing_high_confirmed" not in df.columns:
        df = detect_swings(df, window=window)

    df = df.copy()

    df["swing_type"] = pd.Series([np.nan] * len(df), dtype=object)
    df["major_high"] = np.nan
    df["major_low"] = np.nan
    df["market_trend"] = 0

    last_h_price = -np.inf
    last_l_price = np.inf

    last_swing_high = np.nan
    last_swing_low = np.nan

    initial_high = df["high"].iloc[:window].max() if len(df) > window else df["high"].max()
    initial_low = df["low"].iloc[:window].min() if len(df) > window else df["low"].min()
    active_high = initial_high
    active_low = initial_low

    trend = 0

    closes = df["close"].values
    highs = df["high"].values
    lows = df["low"].values
    swing_high_confirmed = df["swing_high_confirmed"].values
    swing_low_confirmed = df["swing_low_confirmed"].values
    swing_high_prices = df["swing_high_price"].values
    swing_low_prices = df["swing_low_price"].values

    major_high_arr = np.full(len(df), np.nan)
    major_low_arr = np.full(len(df), np.nan)
    trend_arr = np.zeros(len(df), dtype=int)
    swing_type_arr = np.empty(len(df), dtype=object)
    swing_type_arr[:] = np.nan

    for i in range(len(df)):
        if swing_high_confirmed[i]:
            price = swing_high_prices[i]
            swing_type_arr[i] = classify_swing_high(price, last_h_price, tolerance_pct)

            last_h_price = price
            last_swing_high = price

            if trend == -1:
                active_high = price

        if swing_low_confirmed[i]:
            price = swing_low_prices[i]
            swing_type_arr[i] = classify_swing_low(price, last_l_price, tolerance_pct)

            last_l_price = price
            last_swing_low = price

            if trend == 1:
                active_low = price

        if not np.isnan(active_high) and closes[i] > active_high:
            trend = 1
            if not np.isnan(last_swing_low):
                active_low = last_swing_low
            active_high = np.nan

        elif not np.isnan(active_low) and closes[i] < active_low:
            trend = -1
            if not np.isnan(last_swing_high):
                active_high = last_swing_high
            active_low = np.nan

        if trend == 1:
            major_low_arr[i] = active_low
        elif trend == -1:
            major_high_arr[i] = active_high
        else:
            major_high_arr[i] = active_high
            major_low_arr[i] = active_low

        trend_arr[i] = trend

    df["swing_type"] = swing_type_arr
    df["major_high"] = major_high_arr
    df["major_low"] = major_low_arr
    df["market_trend"] = trend_arr

    df["major_high"] = df["major_high"].ffill()
    df["major_low"] = df["major_low"].ffill()

    return df
