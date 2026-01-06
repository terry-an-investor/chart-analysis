"""
Reversal detection: climax and consecutive bar patterns.

Detects V-shaped reversals and gradual reversals to supplement swing-based structure.
"""

import numpy as np
import pandas as pd
from typing import Optional


def detect_climax_reversal(
    df: pd.DataFrame,
    atr_multiplier: float = 2.0,
    lookback: int = 5
) -> pd.DataFrame:
    """
    Detect V-shaped climax reversals.
    
    Identifies sharp turns via large trend bar followed by strong reversal bar.
    Supplements standard swing detection for acute turns.
    
    Args:
        df: DataFrame with OHLC data
        atr_multiplier: ATR multiple for climax bar threshold
        lookback: Period for ATR calculation
    
    Returns:
        DataFrame with added columns:
            - is_climax_top: bool
            - is_climax_bottom: bool
            - climax_top_price: float
            - climax_bottom_price: float
    """
    df = df.copy()
    
    high = df['high']
    low = df['low']
    close = df['close']
    prev_close = close.shift(1)
    
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)
    atr = tr.rolling(window=lookback, min_periods=1).mean()
    
    body_size = (close - df['open']).abs()
    is_bull = close > df['open']
    is_bear = close < df['open']
    
    is_climax_bar = body_size > (atr * atr_multiplier)
    is_bull_climax = is_climax_bar & is_bull
    is_bear_climax = is_climax_bar & is_bear
    
    prev_is_bull = is_bull.astype(float).shift(1).fillna(0.0).astype(bool)
    prev_is_bear = is_bear.astype(float).shift(1).fillna(0.0).astype(bool)
    prev_body = body_size.shift(1).fillna(0)
    
    is_bear_reversal = (
        prev_is_bull & 
        is_bear & 
        (body_size > prev_body * 0.5) &
        (close < df['open'].shift(1))
    )
    
    is_bull_reversal = (
        prev_is_bear & 
        is_bull & 
        (body_size > prev_body * 0.5) &
        (close > df['open'].shift(1))
    )
    
    prev_bull_climax = is_bull_climax.astype(float).shift(1).fillna(0.0).astype(bool)
    is_v_top = prev_bull_climax & is_bear_reversal
    
    prev_bear_climax = is_bear_climax.astype(float).shift(1).fillna(0.0).astype(bool)
    is_v_bottom = prev_bear_climax & is_bull_reversal
    
    df['is_climax_top'] = is_v_top
    df['is_climax_bottom'] = is_v_bottom
    
    df['climax_top_price'] = np.where(is_v_top, high.shift(1), np.nan)
    df['climax_bottom_price'] = np.where(is_v_bottom, low.shift(1), np.nan)
    
    return df


def detect_consecutive_reversal(
    df: pd.DataFrame,
    consecutive_count: int = 3
) -> pd.DataFrame:
    """
    Detect gradual reversals via consecutive bars.
    
    When N consecutive bars move in one direction, marks start of sequence
    as reversal point. Complements climax detection for gradual turns.
    
    Args:
        df: DataFrame with OHLC data
        consecutive_count: Threshold for consecutive same-direction bars
    
    Returns:
        DataFrame with added columns:
            - consecutive_bear_start: bool
            - consecutive_bull_start: bool
            - consecutive_top_price: float
            - consecutive_bottom_price: float
    """
    df = df.copy()
    
    close = df['close']
    open_price = df['open']
    high = df['high']
    low = df['low']
    
    is_bull = close > open_price
    is_bear = close < open_price
    
    bear_groups = (~is_bear).cumsum()
    bull_groups = (~is_bull).cumsum()
    
    df['bear_streak'] = is_bear.groupby(bear_groups).cumsum()
    df['bull_streak'] = is_bull.groupby(bull_groups).cumsum()
    
    is_bear_confirmed = df['bear_streak'] == consecutive_count
    is_bull_confirmed = df['bull_streak'] == consecutive_count
    
    df['consecutive_bear_start'] = False
    df['consecutive_bull_start'] = False
    df['consecutive_top_price'] = np.nan
    df['consecutive_bottom_price'] = np.nan
    
    for i in df.index[is_bear_confirmed]:
        pos = df.index.get_loc(i)
        start_pos = pos - consecutive_count
        if start_pos >= 0:
            df.at[i, 'consecutive_bear_start'] = True
            df.at[i, 'consecutive_top_price'] = high.iloc[start_pos]
    
    for i in df.index[is_bull_confirmed]:
        pos = df.index.get_loc(i)
        start_pos = pos - consecutive_count
        if start_pos >= 0:
            df.at[i, 'consecutive_bull_start'] = True
            df.at[i, 'consecutive_bottom_price'] = low.iloc[start_pos]
    
    df.drop(['bear_streak', 'bull_streak'], axis=1, inplace=True)
    
    return df


def merge_structure_with_events(
    df_structure: pd.DataFrame,
    df_events_climax: Optional[pd.DataFrame] = None,
    df_events_consecutive: Optional[pd.DataFrame] = None
) -> pd.DataFrame:
    """
    Merge reversal events into structure levels.
    
    Override major high/low when strong reversal signals detected,
    providing immediate structure response to price action.
    
    Args:
        df_structure: DataFrame with major_high/low from swing analysis
        df_events_climax: DataFrame with climax reversal columns (optional)
        df_events_consecutive: DataFrame with consecutive reversal columns (optional)
        
    Returns:
        DataFrame with adjusted_major_high and adjusted_major_low columns
    """
    df = df_structure.copy()
    
    df['adjusted_major_high'] = df['major_high']
    df['adjusted_major_low'] = df['major_low']
    
    df['override_high_price'] = np.nan
    df['override_low_price'] = np.nan
    
    if df_events_climax is not None:
        if 'is_climax_top' in df_events_climax.columns:
            mask = df_events_climax['is_climax_top'].fillna(False)
            df.loc[mask, 'override_high_price'] = df_events_climax.loc[mask, 'climax_top_price']
            
        if 'is_climax_bottom' in df_events_climax.columns:
            mask = df_events_climax['is_climax_bottom'].fillna(False)
            df.loc[mask, 'override_low_price'] = df_events_climax.loc[mask, 'climax_bottom_price']

    if df_events_consecutive is not None:
        if 'consecutive_bear_start' in df_events_consecutive.columns:
            mask = df_events_consecutive['consecutive_bear_start'].fillna(False)
            current_vals = df.loc[mask, 'override_high_price']
            new_vals = df_events_consecutive.loc[mask, 'consecutive_top_price']
            df.loc[mask, 'override_high_price'] = np.where(
                current_vals.isna(), 
                new_vals, 
                np.minimum(current_vals, new_vals)
            )
            
        if 'consecutive_bull_start' in df_events_consecutive.columns:
            mask = df_events_consecutive['consecutive_bull_start'].fillna(False)
            current_vals = df.loc[mask, 'override_low_price']
            new_vals = df_events_consecutive.loc[mask, 'consecutive_bottom_price']
            df.loc[mask, 'override_low_price'] = np.where(
                current_vals.isna(),
                new_vals,
                np.maximum(current_vals, new_vals)
            )
    
    override_high_indices = df.index[df['override_high_price'].notna()]
    override_low_indices = df.index[df['override_low_price'].notna()]
    
    if len(override_high_indices) == 0 and len(override_low_indices) == 0:
        return df
    
    curr_high = np.inf
    last_v2_high = np.nan
    
    curr_low = -np.inf
    last_v2_low = np.nan
    
    major_high_vals = df['major_high'].values
    major_low_vals = df['major_low'].values
    high_prices = df['high'].values
    low_prices = df['low'].values
    override_high_vals = df['override_high_price'].values
    override_low_vals = df['override_low_price'].values
    
    adj_high_vals = np.full(len(df), np.nan)
    adj_low_vals = np.full(len(df), np.nan)
    
    for i in range(len(df)):
        v2_h = major_high_vals[i]
        ov_h = override_high_vals[i]
        
        if high_prices[i] > curr_high:
            curr_high = np.inf
            
        v2_changed = False
        if np.isnan(v2_h) and np.isnan(last_v2_high):
            v2_changed = False
        elif np.isnan(v2_h) or np.isnan(last_v2_high):
            v2_changed = True
        else:
            v2_changed = (v2_h != last_v2_high)
            
        if v2_changed:
            if not np.isnan(v2_h):
                curr_high = v2_h
            last_v2_high = v2_h
            
        if not np.isnan(ov_h):
            if curr_high == np.inf or ov_h < curr_high:
                curr_high = ov_h
                
        if not np.isinf(curr_high):
            adj_high_vals[i] = curr_high
            
        v2_l = major_low_vals[i]
        ov_l = override_low_vals[i]
        
        if low_prices[i] < curr_low:
            curr_low = -np.inf
            
        v2_l_changed = False
        if np.isnan(v2_l) and np.isnan(last_v2_low):
            v2_l_changed = False
        elif np.isnan(v2_l) or np.isnan(last_v2_low):
            v2_l_changed = True
        else:
            v2_l_changed = (v2_l != last_v2_low)
            
        if v2_l_changed:
            if not np.isnan(v2_l):
                curr_low = v2_l
            last_v2_low = v2_l
            
        if not np.isnan(ov_l):
            if curr_low == -np.inf or ov_l > curr_low:
                curr_low = ov_l
                
        if not np.isinf(curr_low):
            adj_low_vals[i] = curr_low
            
    df['adjusted_major_high'] = adj_high_vals
    df['adjusted_major_low'] = adj_low_vals
    
    return df
