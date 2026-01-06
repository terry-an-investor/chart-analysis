"""
Tests for structure utility functions.

Tests helper functions for structure analysis.
"""

from __future__ import annotations

import numpy as np
import pytest

from src.analysis._structure_utils import (
    classify_swing_high,
    classify_swing_low,
    compare_prices,
    detect_duplicates,
    merge_sorted_events,
    safe_divide,
)


def test_safe_divide_normal() -> None:
    """Test safe division with normal values."""
    result = safe_divide(np.array([10, 20, 30]), np.array([2, 4, 5]))
    expected = np.array([5.0, 5.0, 6.0])
    np.testing.assert_array_equal(result, expected)


def test_safe_divide_with_zeros() -> None:
    """Test safe division with zero denominators."""
    result = safe_divide(np.array([10, 20, 30]), np.array([2, 0, 5]))
    assert result[0] == 5.0
    assert np.isnan(result[1])
    assert result[2] == 6.0


def test_detect_duplicates_no_duplicates() -> None:
    """Test duplicate detection with no consecutive duplicates."""
    arr = np.array([True, False, True, False, True])
    result = detect_duplicates(arr)

    expected = np.array([True, False, True, False, True])
    np.testing.assert_array_equal(result, expected)


def test_detect_duplicates_with_duplicates() -> None:
    """Test duplicate detection removes consecutive duplicates."""
    arr = np.array([True, True, False, True, True, True, False])
    result = detect_duplicates(arr)

    # Should keep only first True in each sequence
    expected = np.array([True, False, False, True, False, False, False])
    np.testing.assert_array_equal(result, expected)


def test_detect_duplicates_all_same() -> None:
    """Test duplicate detection with all same values."""
    arr = np.array([True, True, True, True])
    result = detect_duplicates(arr)

    # Only first element should remain True
    expected = np.array([True, False, False, False])
    np.testing.assert_array_equal(result, expected)


def test_compare_prices_higher() -> None:
    """Test price comparison when current is higher."""
    result = compare_prices(105.0, 100.0, 0.001)
    assert result == "HIGHER"


def test_compare_prices_lower() -> None:
    """Test price comparison when current is lower."""
    result = compare_prices(95.0, 100.0, 0.001)
    assert result == "LOWER"


def test_compare_prices_double_within_tolerance() -> None:
    """Test price comparison detects double top/bottom."""
    result = compare_prices(100.05, 100.0, 0.001)
    assert result == "DOUBLE"


def test_compare_prices_invalid_last_price() -> None:
    """Test price comparison with invalid last price."""
    result = compare_prices(100.0, 0.0, 0.001)
    assert result is None

    result = compare_prices(100.0, -10.0, 0.001)
    assert result is None

    result = compare_prices(100.0, np.inf, 0.001)
    assert result is None


def test_classify_swing_high_hh() -> None:
    """Test swing high classification: Higher High."""
    result = classify_swing_high(105.0, 100.0, 0.001)
    assert result == "HH"


def test_classify_swing_high_lh() -> None:
    """Test swing high classification: Lower High."""
    result = classify_swing_high(95.0, 100.0, 0.001)
    assert result == "LH"


def test_classify_swing_high_dt() -> None:
    """Test swing high classification: Double Top."""
    result = classify_swing_high(100.05, 100.0, 0.001)
    assert result == "DT"


def test_classify_swing_high_first() -> None:
    """Test swing high classification for first swing."""
    result = classify_swing_high(100.0, -np.inf, 0.001)
    assert result == "HH"


def test_classify_swing_low_ll() -> None:
    """Test swing low classification: Lower Low."""
    result = classify_swing_low(95.0, 100.0, 0.001)
    assert result == "LL"


def test_classify_swing_low_hl() -> None:
    """Test swing low classification: Higher Low."""
    result = classify_swing_low(105.0, 100.0, 0.001)
    assert result == "HL"


def test_classify_swing_low_db() -> None:
    """Test swing low classification: Double Bottom."""
    result = classify_swing_low(100.05, 100.0, 0.001)
    assert result == "DB"


def test_classify_swing_low_first() -> None:
    """Test swing low classification for first swing."""
    result = classify_swing_low(100.0, np.inf, 0.001)
    assert result == "LL"


def test_merge_sorted_events_empty() -> None:
    """Test merging with no events."""
    result = merge_sorted_events([], [])
    assert result == []


def test_merge_sorted_events_only_highs() -> None:
    """Test merging with only high events."""
    result = merge_sorted_events([1, 3, 5], [])

    assert len(result) == 3
    assert result[0] == (1, "high")
    assert result[1] == (3, "high")
    assert result[2] == (5, "high")


def test_merge_sorted_events_only_lows() -> None:
    """Test merging with only low events."""
    result = merge_sorted_events([], [2, 4, 6])

    assert len(result) == 3
    assert result[0] == (2, "low")
    assert result[1] == (4, "low")
    assert result[2] == (6, "low")


def test_merge_sorted_events_mixed() -> None:
    """Test merging with mixed high/low events."""
    result = merge_sorted_events([1, 5, 7], [2, 4, 8])

    assert len(result) == 6
    assert result == [
        (1, "high"),
        (2, "low"),
        (4, "low"),
        (5, "high"),
        (7, "high"),
        (8, "low"),
    ]


def test_merge_sorted_events_alternating() -> None:
    """Test merging alternating high/low events."""
    result = merge_sorted_events([0, 2, 4], [1, 3, 5])

    assert len(result) == 6
    assert result[0] == (0, "high")
    assert result[1] == (1, "low")
    assert result[2] == (2, "high")
    assert result[3] == (3, "low")
    assert result[4] == (4, "high")
    assert result[5] == (5, "low")
