"""
Market structure analysis module.

Integrates swing detection, classification, and reversal detection to identify
trend structure following Al Brooks price action methodology.
"""

from typing import Tuple

import numpy as np
import pandas as pd

from ._structure_utils import DEFAULT_SWING_WINDOW, PRICE_TOLERANCE_PCT
from .reversals import (
    detect_climax_reversal,
    detect_consecutive_reversal,
    merge_structure_with_events,
)
from .swings import (
    classify_swings,
    classify_swings_v2,
    classify_swings_v3,
    detect_swings,
)


def compute_trend_state(df: pd.DataFrame, lookback: int = 2) -> pd.DataFrame:
    """
    Compute trend state: Always In Long/Short/Neutral.

    Trend definition (Al Brooks):
    - Bull: Recent HH + HL (higher highs and higher lows)
    - Bear: Recent LL + LH (lower lows and lower highs)
    - Neutral: Mixed structure or transition period

    Args:
        df: DataFrame with swing classification results
        lookback: Number of recent swing points to evaluate

    Returns:
        DataFrame with added columns:
            - market_trend: int (1=Bull, -1=Bear, 0=Neutral)
            - last_swing_types: str (debug info)
    """
    if "swing_type" not in df.columns:
        df = classify_swings(df)

    df = df.copy()

    df["market_trend"] = 0
    df["last_swing_types"] = ""

    swing_indices = df.index[df["swing_type"].notna()].tolist()

    if len(swing_indices) < lookback:
        return df

    current_trend = 0
    last_types = []

    swing_ptr = 0

    for i in df.index:
        while swing_ptr < len(swing_indices) and swing_indices[swing_ptr] <= i:
            swing_type = df.at[swing_indices[swing_ptr], "swing_type"]
            last_types.append(swing_type)
            if len(last_types) > lookback * 2:
                last_types.pop(0)
            swing_ptr += 1

        if len(last_types) >= lookback:
            recent_highs = [t for t in last_types if t in ("HH", "LH", "DT")]
            recent_lows = [t for t in last_types if t in ("HL", "LL", "DB")]

            if recent_highs and recent_lows:
                last_high = recent_highs[-1]
                last_low = recent_lows[-1]

                if last_high == "HH" and last_low == "HL":
                    current_trend = 1
                elif last_high == "LH" and last_low == "LL":
                    current_trend = -1
                else:
                    current_trend = 0

        df.at[i, "market_trend"] = current_trend
        df.at[i, "last_swing_types"] = ",".join(last_types[-4:])

    return df


def compute_market_structure(
    df: pd.DataFrame, swing_window: int = DEFAULT_SWING_WINDOW, trend_lookback: int = 2
) -> pd.DataFrame:
    """
    Complete market structure pipeline.

    Executes:
    1. detect_swings() - Identify swing points
    2. classify_swings() - Classify and mark major levels
    3. compute_trend_state() - Determine trend direction

    Args:
        df: DataFrame with OHLC data
        swing_window: Swing confirmation period
        trend_lookback: Trend evaluation lookback

    Returns:
        DataFrame with all structure features
    """
    result = detect_swings(df, window=swing_window)
    result = classify_swings(result)
    result = compute_trend_state(result, lookback=trend_lookback)

    return result


def add_structure_features(
    df: pd.DataFrame,
    swing_window: int = DEFAULT_SWING_WINDOW,
    trend_lookback: int = 2,
    prefix: str = "struct_",
) -> pd.DataFrame:
    """
    Add structure features to existing DataFrame.

    Convenience wrapper that adds structure columns with optional prefix.

    Args:
        df: DataFrame with OHLC data
        swing_window: Swing confirmation period
        trend_lookback: Trend evaluation lookback
        prefix: Column name prefix

    Returns:
        Original DataFrame with added structure columns
    """
    features = compute_market_structure(
        df, swing_window=swing_window, trend_lookback=trend_lookback
    )

    feature_cols = [
        "swing_high_confirmed",
        "swing_low_confirmed",
        "swing_high_price",
        "swing_low_price",
        "swing_type",
        "major_high",
        "major_low",
        "market_trend",
        "last_swing_types",
    ]

    for col in feature_cols:
        if col in features.columns:
            df[f"{prefix}{col}"] = features[col].values

    return df


__all__ = [
    "DEFAULT_SWING_WINDOW",
    "PRICE_TOLERANCE_PCT",
    "detect_swings",
    "classify_swings",
    "classify_swings_v2",
    "classify_swings_v3",
    "compute_trend_state",
    "compute_market_structure",
    "add_structure_features",
    "detect_climax_reversal",
    "detect_consecutive_reversal",
    "merge_structure_with_events",
]
