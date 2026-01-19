"""
Bar features extraction module.

Calculates single-bar and cross-bar features based on Al Brooks Price Action theory.
"""

import numpy as np
import pandas as pd

from ._bar_utils import (
    calculate_blend_candle,
    calculate_consecutive_streak,
    calculate_ema_features,
    calculate_engulfing,
    calculate_failed_breakouts,
    calculate_tails,
    safe_divide_array,
)

DOJI_BODY_THRESHOLD = 0.25
TREND_BAR_THRESHOLD = 0.6
PINBAR_TAIL_THRESHOLD = 0.66
SHAVED_TOLERANCE = 0.02
CLOSE_ON_EXTREME_THRESHOLD = 0.9


def compute_bar_features(
    df: pd.DataFrame,
    doji_threshold: float = DOJI_BODY_THRESHOLD,
    ema_period: int = 20,
) -> pd.DataFrame:
    """
    Calculate bar features for OHLC data.

    Args:
        df: DataFrame with 'open', 'high', 'low', 'close' columns
        doji_threshold: Body percentage threshold for doji detection
        ema_period: EMA period (default 20 per Al Brooks)

    Returns:
        DataFrame with bar features including:
            - Scale features: total_range, body_size, amplitude
            - Shape features: bar_color, body_pct, tail percentages, clv
            - Pattern features: doji, pinbar, trend_bar, etc.
            - Cross-bar features: gap, inside/outside bars, engulfing
            - EMA features: dist_to_ema, bar_pos_ema, touches
    """
    open_price = df["open"]
    high = df["high"]
    low = df["low"]
    close = df["close"]

    total_range = high - low
    body_size = (close - open_price).abs()

    safe_range = np.where(total_range == 0, np.nan, total_range)

    body_pct = body_size / safe_range
    bar_color = np.sign(close - open_price).astype(int)

    upper_tail, lower_tail = calculate_tails(high, open_price, close, low)
    upper_tail_pct = upper_tail / safe_range
    lower_tail_pct = lower_tail / safe_range

    amplitude = total_range / open_price

    avg_range_20 = total_range.rolling(window=20).mean()
    rel_range_to_avg = total_range / avg_range_20
    is_climax_bar = rel_range_to_avg > 2.0

    clv = (2 * close - high - low) / safe_range
    signed_body = (close - open_price) / safe_range

    prev_open = df["open"].shift(1)
    prev_high = df["high"].shift(1)
    prev_low = df["low"].shift(1)
    prev_close = df["close"].shift(1)
    prev_range = prev_high - prev_low

    safe_prev_close = np.where(prev_close == 0, np.nan, prev_close)
    safe_prev_range = np.where(prev_range == 0, np.nan, prev_range)

    gap_ratio = open_price / prev_close
    safe_gap_ratio = np.where((open_price > 0) & (prev_close > 0), gap_ratio, np.nan)
    gap = np.log(safe_gap_ratio)

    day_return_ratio = close / prev_close
    safe_return_ratio = np.where((close > 0) & (prev_close > 0), day_return_ratio, np.nan)
    day_return = np.log(safe_return_ratio)

    true_range = np.maximum(
        total_range, np.maximum((high - prev_close).abs(), (low - prev_close).abs())
    )

    rel_true_range = true_range / safe_prev_close

    safe_tr_val = np.where(true_range == 0, np.nan, true_range)
    movement_efficiency = (close - prev_close).abs() / safe_tr_val

    open_in_body = np.abs(gap) < 0.01

    is_inside = (high <= prev_high) & (low >= prev_low)
    is_outside = ((high >= prev_high) & (low < prev_low)) | ((high > prev_high) & (low <= prev_low))

    gap_type = np.where(open_price > prev_high, 1, np.where(open_price < prev_low, -1, 0))

    overlap_high = np.minimum(high, prev_high)
    overlap_low = np.maximum(low, prev_low)
    overlap_length = np.maximum(0, overlap_high - overlap_low)
    overlap_pct = overlap_length / safe_prev_range

    prev_body_top = np.maximum(prev_open, prev_close)
    curr_body_bottom = np.minimum(open_price, close)
    body_gap = curr_body_bottom - prev_body_top

    shaved_top = upper_tail_pct <= SHAVED_TOLERANCE
    shaved_bottom = lower_tail_pct <= SHAVED_TOLERANCE

    is_trend_bar = body_pct >= TREND_BAR_THRESHOLD
    is_trading_range_bar = ~is_trend_bar

    is_doji = body_pct < doji_threshold

    is_pinbar = (
        (upper_tail_pct > PINBAR_TAIL_THRESHOLD) | (lower_tail_pct > PINBAR_TAIL_THRESHOLD)
    ) & (body_pct < (1 - PINBAR_TAIL_THRESHOLD))

    close_on_extreme = np.abs(clv) > CLOSE_ON_EXTREME_THRESHOLD

    is_strong_bull_reversal = (lower_tail_pct > 0.33) & (clv > 0.6) & (bar_color == 1)

    is_strong_bear_reversal = (upper_tail_pct > 0.33) & (clv < -0.6) & (bar_color == -1)

    trend_streak = calculate_consecutive_streak(is_trend_bar, bar_color, df)

    is_outside_up = is_outside & (close > prev_high)
    is_outside_down = is_outside & (close < prev_low)

    prev_body_bottom = np.minimum(prev_open, prev_close)
    curr_body_top = np.maximum(open_price, close)
    is_bull_engulfing, is_bear_engulfing = calculate_engulfing(
        bar_color, prev_body_bottom, curr_body_bottom, prev_body_top, curr_body_top
    )

    blend_open, blend_close, blend_high, blend_low = calculate_blend_candle(
        prev_open, prev_high, prev_low, open_price, high, low, close
    )
    blend_range = blend_high - blend_low
    safe_blend_range = np.where(blend_range == 0, np.nan, blend_range)

    blend_clv = (2 * blend_close - blend_high - blend_low) / safe_blend_range
    blend_body_size = (blend_close - blend_open).abs()
    blend_body_pct = blend_body_size / safe_blend_range

    (
        failed_breakout_high,
        failed_breakout_low,
        strict_failed_breakout_high,
        strict_failed_breakout_low,
    ) = calculate_failed_breakouts(high, low, close, prev_high, prev_low, bar_color)

    if "ema" in df.columns:
        ema = df["ema"]
    else:
        ema = df["close"].ewm(span=ema_period, adjust=False).mean()

    dist_to_ema, bar_pos_ema, ema_touch, gap_below_ema, gap_above_ema = calculate_ema_features(
        close, high, low, ema
    )

    result_dict = {
        "total_range": total_range,
        "body_size": body_size,
        "amplitude": amplitude,
        "gap": gap,
        "day_return": day_return,
        "true_range": true_range,
        "rel_true_range": rel_true_range,
        "movement_efficiency": movement_efficiency,
        "bar_color": bar_color,
        "body_pct": body_pct,
        "upper_tail_pct": upper_tail_pct,
        "lower_tail_pct": lower_tail_pct,
        "clv": clv,
        "signed_body": signed_body,
        "shaved_top": shaved_top,
        "shaved_bottom": shaved_bottom,
        "is_trend_bar": is_trend_bar,
        "is_trading_range_bar": is_trading_range_bar,
        "is_doji": is_doji,
        "is_pinbar": is_pinbar,
        "close_on_extreme": close_on_extreme,
        "is_inside": is_inside,
        "is_outside": is_outside,
        "gap_type": gap_type,
        "overlap_pct": overlap_pct,
        "open_in_body": open_in_body,
        "body_gap": body_gap,
        "trend_streak": trend_streak,
        "rel_range_to_avg": rel_range_to_avg,
        "is_climax_bar": is_climax_bar,
        "is_strong_bull_reversal": is_strong_bull_reversal,
        "is_strong_bear_reversal": is_strong_bear_reversal,
        "is_outside_up": is_outside_up,
        "is_outside_down": is_outside_down,
        "is_bull_engulfing": is_bull_engulfing,
        "is_bear_engulfing": is_bear_engulfing,
        "blend_open": blend_open,
        "blend_close": blend_close,
        "blend_high": blend_high,
        "blend_low": blend_low,
        "blend_clv": blend_clv,
        "blend_body_pct": blend_body_pct,
        "failed_breakout_high": failed_breakout_high,
        "failed_breakout_low": failed_breakout_low,
        "strict_failed_breakout_high": strict_failed_breakout_high,
        "strict_failed_breakout_low": strict_failed_breakout_low,
        "ema": ema,
        "dist_to_ema": dist_to_ema,
        "bar_pos_ema": bar_pos_ema,
        "ema_touch": ema_touch,
        "gap_below_ema": gap_below_ema,
        "gap_above_ema": gap_above_ema,
    }

    result = pd.DataFrame(result_dict, index=df.index)
    return result


def add_bar_features(
    df: pd.DataFrame,
    doji_threshold: float = DOJI_BODY_THRESHOLD,
    ema_period: int = 20,
    prefix: str = "",
) -> pd.DataFrame:
    """
    Add bar features to existing DataFrame.

    Convenience wrapper that adds feature columns with optional prefix.

    Args:
        df: DataFrame with OHLC data
        doji_threshold: Body percentage threshold for doji detection
        ema_period: EMA period
        prefix: Column name prefix

    Returns:
        Original DataFrame with added feature columns
    """
    features = compute_bar_features(df, doji_threshold, ema_period)

    df = df.copy()
    for col in features.columns:
        df[f"{prefix}{col}"] = features[col].values

    return df
