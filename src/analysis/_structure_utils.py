"""Utility functions and constants for structure analysis."""

import numpy as np
import pandas as pd

DEFAULT_SWING_WINDOW = 5
PRICE_TOLERANCE_PCT = 0.001


def safe_divide(numerator, denominator, fill_value=np.nan):
    """Safely divide two arrays/series, handling zeros."""
    safe_denom = np.where(denominator == 0, np.nan, denominator)
    return numerator / safe_denom


def detect_duplicates(arr):
    """Remove consecutive duplicates, keeping only the first occurrence."""
    prev_arr = np.roll(arr, 1)
    prev_arr[0] = False
    return arr & ~prev_arr


def compare_prices(current_price, last_price, tolerance_pct):
    """Compare two prices and return classification: 'DT'/'DB', 'HH'/'HL', or 'LH'/'LL'."""
    if last_price <= 0 or not np.isfinite(last_price):
        return None
    
    price_diff_pct = abs(current_price - last_price) / last_price
    
    if price_diff_pct <= tolerance_pct:
        return 'DOUBLE'
    elif current_price > last_price:
        return 'HIGHER'
    else:
        return 'LOWER'


def classify_swing_high(price, last_h_price, tolerance_pct):
    """Classify a swing high as HH, LH, or DT."""
    comparison = compare_prices(price, last_h_price, tolerance_pct)
    
    if comparison is None:
        return 'HH'
    elif comparison == 'DOUBLE':
        return 'DT'
    elif comparison == 'HIGHER':
        return 'HH'
    else:
        return 'LH'


def classify_swing_low(price, last_l_price, tolerance_pct):
    """Classify a swing low as HL, LL, or DB."""
    comparison = compare_prices(price, last_l_price, tolerance_pct)
    
    if comparison is None:
        return 'LL'
    elif comparison == 'DOUBLE':
        return 'DB'
    elif comparison == 'LOWER':
        return 'LL'
    else:
        return 'HL'


def merge_sorted_events(high_indices, low_indices):
    """Merge and sort high/low swing events by time."""
    events = (
        [(i, 'high') for i in high_indices] + 
        [(i, 'low') for i in low_indices]
    )
    return sorted(events, key=lambda x: x[0])
