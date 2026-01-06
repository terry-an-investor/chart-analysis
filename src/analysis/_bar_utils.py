"""Utility functions for bar feature calculations."""

import numpy as np
import pandas as pd


def safe_divide_array(numerator, denominator):
    """Safely divide arrays, returning NaN for zero denominators."""
    return np.where(denominator == 0, np.nan, numerator / denominator)


def calculate_tails(high, open_price, close, low):
    """Calculate upper and lower tail sizes."""
    upper_tail = high - np.maximum(open_price, close)
    lower_tail = np.minimum(open_price, close) - low
    return upper_tail, lower_tail


def calculate_blend_candle(prev_open, prev_high, prev_low, open_price, high, low, close):
    """Calculate blended (2-bar merged) candle values."""
    blend_open = prev_open
    blend_close = close
    blend_high = np.maximum(high, prev_high)
    blend_low = np.minimum(low, prev_low)
    return blend_open, blend_close, blend_high, blend_low


def calculate_consecutive_streak(is_trend_bar, bar_color, df):
    """Calculate consecutive trend bar streak."""
    trend_dir = is_trend_bar.astype(int) * bar_color
    streak_group = (trend_dir != trend_dir.shift(1)).cumsum()
    trend_streak_raw = df.groupby(streak_group)["close"].cumcount() + 1
    return np.where(is_trend_bar, trend_streak_raw, 0)


def calculate_engulfing(bar_color, prev_body_bottom, curr_body_bottom, prev_body_top, curr_body_top):
    """Calculate bull and bear engulfing patterns."""
    is_bull_engulfing = (
        (bar_color == 1) &
        (bar_color.shift(1) == -1) &
        (curr_body_bottom <= prev_body_bottom) &
        (curr_body_top >= prev_body_top)
    )
    
    is_bear_engulfing = (
        (bar_color == -1) &
        (bar_color.shift(1) == 1) &
        (curr_body_bottom <= prev_body_bottom) &
        (curr_body_top >= prev_body_top)
    )
    
    return is_bull_engulfing, is_bear_engulfing


def calculate_failed_breakouts(high, low, close, prev_high, prev_low, bar_color):
    """Calculate failed breakout patterns."""
    failed_breakout_high = (high > prev_high) & (close < prev_high)
    failed_breakout_low = (low < prev_low) & (close > prev_low)
    
    strict_failed_breakout_high = failed_breakout_high & (bar_color == -1)
    strict_failed_breakout_low = failed_breakout_low & (bar_color == 1)
    
    return failed_breakout_high, failed_breakout_low, strict_failed_breakout_high, strict_failed_breakout_low


def calculate_ema_features(close, high, low, ema):
    """Calculate EMA-related features."""
    safe_ema = np.where(ema == 0, np.nan, ema)
    dist_to_ema = (close - ema) / safe_ema
    
    bar_pos_ema = np.where(
        low > ema, 1,
        np.where(high < ema, -1, 0)
    )
    
    ema_touch = (high >= ema) & (low <= ema)
    gap_below_ema = high < ema
    gap_above_ema = low > ema
    
    return dist_to_ema, bar_pos_ema, ema_touch, gap_below_ema, gap_above_ema
