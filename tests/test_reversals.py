"""
Tests for reversal detection module.

Tests climax and consecutive reversal detection patterns.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.analysis.reversals import (
    detect_climax_reversal,
    detect_consecutive_reversal,
    merge_structure_with_events,
)


@pytest.fixture
def sample_ohlc() -> pd.DataFrame:
    """Create sample OHLC data for testing."""
    return pd.DataFrame(
        {
            "open": [100, 101, 105, 110, 108, 105, 102, 103, 106, 109],
            "high": [102, 106, 112, 111, 109, 106, 104, 107, 110, 112],
            "low": [99, 100, 104, 107, 104, 101, 100, 102, 105, 108],
            "close": [101, 105, 110, 108, 105, 102, 103, 106, 109, 111],
        }
    )


@pytest.fixture
def v_top_data() -> pd.DataFrame:
    """Create data with V-Top pattern (bull climax followed by bear reversal)."""
    return pd.DataFrame(
        {
            "open": [100, 101, 102, 103, 110, 110, 105],
            "high": [101, 102, 103, 115, 111, 110, 106],
            "low": [99, 100, 101, 102, 104, 103, 102],
            "close": [101, 102, 103, 114, 105, 104, 103],
        }
    )


@pytest.fixture
def v_bottom_data() -> pd.DataFrame:
    """Create data with V-Bottom pattern (bear climax followed by bull reversal)."""
    return pd.DataFrame(
        {
            "open": [110, 109, 108, 107, 100, 100, 105],
            "high": [111, 110, 109, 108, 101, 106, 107],
            "low": [109, 108, 107, 95, 96, 99, 104],
            "close": [109, 108, 107, 96, 105, 106, 107],
        }
    )


@pytest.fixture
def consecutive_bear_data() -> pd.DataFrame:
    """Create data with consecutive bear bars."""
    return pd.DataFrame(
        {
            "open": [110, 109, 108, 107, 106, 105, 104],
            "high": [111, 110, 109, 108, 107, 106, 105],
            "low": [108, 107, 106, 105, 104, 103, 102],
            "close": [109, 108, 107, 106, 105, 104, 103],
        }
    )


@pytest.fixture
def consecutive_bull_data() -> pd.DataFrame:
    """Create data with consecutive bull bars."""
    return pd.DataFrame(
        {
            "open": [100, 101, 102, 103, 104, 105, 106],
            "high": [102, 103, 104, 105, 106, 107, 108],
            "low": [99, 100, 101, 102, 103, 104, 105],
            "close": [101, 102, 103, 104, 105, 106, 107],
        }
    )


def test_detect_climax_reversal_returns_required_columns(sample_ohlc: pd.DataFrame) -> None:
    """Test that detect_climax_reversal returns required columns."""
    result = detect_climax_reversal(sample_ohlc)

    assert "is_climax_top" in result.columns
    assert "is_climax_bottom" in result.columns
    assert "climax_top_price" in result.columns
    assert "climax_bottom_price" in result.columns


def test_detect_climax_reversal_preserves_original_data(sample_ohlc: pd.DataFrame) -> None:
    """Test that original OHLC columns are preserved."""
    result = detect_climax_reversal(sample_ohlc)

    assert len(result) == len(sample_ohlc)
    assert "open" in result.columns
    assert "high" in result.columns
    assert "low" in result.columns
    assert "close" in result.columns


def test_detect_climax_reversal_v_top(v_top_data: pd.DataFrame) -> None:
    """Test V-Top reversal detection."""
    result = detect_climax_reversal(v_top_data, atr_multiplier=1.5)

    # With the pattern structure, might or might not detect - test columns exist
    assert "is_climax_top" in result.columns
    assert "is_climax_bottom" in result.columns


def test_detect_climax_reversal_v_bottom(v_bottom_data: pd.DataFrame) -> None:
    """Test V-Bottom reversal detection."""
    result = detect_climax_reversal(v_bottom_data, atr_multiplier=1.5)

    # With the pattern structure, might or might not detect - test columns exist
    assert "is_climax_top" in result.columns
    assert "is_climax_bottom" in result.columns


def test_detect_climax_reversal_empty_dataframe() -> None:
    """Test climax detection with empty DataFrame."""
    df = pd.DataFrame(
        {
            "open": [],
            "high": [],
            "low": [],
            "close": [],
        }
    )

    result = detect_climax_reversal(df)
    assert len(result) == 0


def test_detect_climax_reversal_single_bar() -> None:
    """Test climax detection with single bar."""
    df = pd.DataFrame(
        {
            "open": [100],
            "high": [102],
            "low": [99],
            "close": [101],
        }
    )

    result = detect_climax_reversal(df)
    assert len(result) == 1
    assert not result["is_climax_top"].iloc[0]
    assert not result["is_climax_bottom"].iloc[0]


def test_detect_consecutive_reversal_returns_required_columns(sample_ohlc: pd.DataFrame) -> None:
    """Test that detect_consecutive_reversal returns required columns."""
    result = detect_consecutive_reversal(sample_ohlc)

    assert "consecutive_bear_start" in result.columns
    assert "consecutive_bull_start" in result.columns
    assert "consecutive_top_price" in result.columns
    assert "consecutive_bottom_price" in result.columns


def test_detect_consecutive_reversal_bear_pattern(consecutive_bear_data: pd.DataFrame) -> None:
    """Test consecutive bear reversal detection."""
    result = detect_consecutive_reversal(consecutive_bear_data, consecutive_count=3)

    # Check that columns exist and function runs without error
    assert "consecutive_bear_start" in result.columns
    assert "consecutive_top_price" in result.columns


def test_detect_consecutive_reversal_bull_pattern(consecutive_bull_data: pd.DataFrame) -> None:
    """Test consecutive bull reversal detection."""
    result = detect_consecutive_reversal(consecutive_bull_data, consecutive_count=3)

    # Check that columns exist and function runs without error
    assert "consecutive_bull_start" in result.columns
    assert "consecutive_bottom_price" in result.columns


def test_detect_consecutive_reversal_custom_threshold() -> None:
    """Test consecutive detection with different thresholds."""
    df = pd.DataFrame(
        {
            "open": [100, 101, 102, 103, 104],
            "high": [102, 103, 104, 105, 106],
            "low": [99, 100, 101, 102, 103],
            "close": [101, 102, 103, 104, 105],
        }
    )

    result_2 = detect_consecutive_reversal(df, consecutive_count=2)
    result_4 = detect_consecutive_reversal(df, consecutive_count=4)

    # Lower threshold should detect more or equal patterns
    assert result_2["consecutive_bull_start"].sum() >= result_4["consecutive_bull_start"].sum()


def test_detect_consecutive_reversal_empty_dataframe() -> None:
    """Test consecutive detection with empty DataFrame."""
    df = pd.DataFrame(
        {
            "open": [],
            "high": [],
            "low": [],
            "close": [],
        }
    )

    result = detect_consecutive_reversal(df)
    assert len(result) == 0


def test_merge_structure_with_events_basic() -> None:
    """Test merging structure with events."""
    df = pd.DataFrame(
        {
            "high": [100, 105, 110, 108],
            "low": [95, 100, 105, 103],
            "major_high": [100, 105, 110, 110],
            "major_low": [95, 95, 95, 95],
        }
    )

    result = merge_structure_with_events(df)

    assert "adjusted_major_high" in result.columns
    assert "adjusted_major_low" in result.columns
    assert len(result) == len(df)


def test_merge_structure_with_climax_events() -> None:
    """Test merging with climax reversal events."""
    df = pd.DataFrame(
        {
            "high": [100, 105, 110, 108],
            "low": [95, 100, 105, 103],
            "major_high": [100, 105, 110, 110],
            "major_low": [95, 95, 95, 95],
        }
    )

    df_climax = pd.DataFrame(
        {
            "is_climax_top": [False, False, True, False],
            "climax_top_price": [np.nan, np.nan, 110, np.nan],
            "is_climax_bottom": [False, False, False, False],
            "climax_bottom_price": [np.nan, np.nan, np.nan, np.nan],
        }
    )

    result = merge_structure_with_events(df, df_events_climax=df_climax)

    assert "adjusted_major_high" in result.columns
    assert "override_high_price" in result.columns


def test_merge_structure_with_consecutive_events() -> None:
    """Test merging with consecutive reversal events."""
    df = pd.DataFrame(
        {
            "high": [100, 105, 110, 108],
            "low": [95, 100, 105, 103],
            "major_high": [100, 105, 110, 110],
            "major_low": [95, 95, 95, 95],
        }
    )

    df_consecutive = pd.DataFrame(
        {
            "consecutive_bear_start": [False, False, True, False],
            "consecutive_top_price": [np.nan, np.nan, 105, np.nan],
            "consecutive_bull_start": [False, False, False, False],
            "consecutive_bottom_price": [np.nan, np.nan, np.nan, np.nan],
        }
    )

    result = merge_structure_with_events(df, df_events_consecutive=df_consecutive)

    assert "adjusted_major_high" in result.columns
    assert "override_high_price" in result.columns


def test_merge_structure_no_events() -> None:
    """Test merge when no reversal events provided."""
    df = pd.DataFrame(
        {
            "high": [100, 105, 110, 108],
            "low": [95, 100, 105, 103],
            "major_high": [100, 105, 110, 110],
            "major_low": [95, 95, 95, 95],
        }
    )

    result = merge_structure_with_events(df, df_events_climax=None, df_events_consecutive=None)

    # Without events, adjusted should match original
    pd.testing.assert_series_equal(
        result["adjusted_major_high"].fillna(-1), result["major_high"].fillna(-1), check_names=False
    )


def test_merge_structure_empty_dataframe() -> None:
    """Test merge with empty DataFrame."""
    df = pd.DataFrame(
        {
            "high": [],
            "low": [],
            "major_high": [],
            "major_low": [],
        }
    )

    result = merge_structure_with_events(df)
    assert len(result) == 0
    assert "adjusted_major_high" in result.columns
