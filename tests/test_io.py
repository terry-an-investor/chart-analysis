"""
Tests for I/O modules (loader, adapters, file discovery).

Tests data loading, adapter selection, and file discovery functionality.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pandas as pd
import pytest

from src.io import list_adapters, load_ohlc
from src.io.adapters import StandardAdapter, WindCFEAdapter
from src.io.loader import ADAPTERS
from src.io.schema import OHLCData


@pytest.fixture
def sample_ohlc_df() -> pd.DataFrame:
    """Create sample OHLC DataFrame."""
    return pd.DataFrame(
        {
            "datetime": pd.date_range("2024-01-01", periods=5, freq="D"),
            "open": [100, 101, 102, 103, 104],
            "high": [102, 103, 104, 105, 106],
            "low": [99, 100, 101, 102, 103],
            "close": [101, 102, 103, 104, 105],
            "volume": [1000, 1100, 1200, 1300, 1400],
        }
    )


@pytest.fixture
def temp_csv_file(sample_ohlc_df: pd.DataFrame) -> Path:
    """Create temporary CSV file with standard format."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        sample_ohlc_df.to_csv(f.name, index=False)
        return Path(f.name)


@pytest.fixture
def temp_excel_file(sample_ohlc_df: pd.DataFrame) -> Path:
    """Create temporary Excel file with standard format."""
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        sample_ohlc_df.to_excel(f.name, index=False)
        return Path(f.name)


def test_list_adapters() -> None:
    """Test listing available adapters."""
    adapters = list_adapters()

    assert isinstance(adapters, list)
    assert len(adapters) > 0
    assert "standard" in adapters
    assert "wind_cfe" in adapters


def test_standard_adapter_can_handle_csv(temp_csv_file: Path) -> None:
    """Test StandardAdapter can handle CSV files."""
    adapter = StandardAdapter()

    try:
        # Should be able to handle valid CSV with required columns
        assert adapter.can_handle(temp_csv_file)
    finally:
        temp_csv_file.unlink()


def test_standard_adapter_can_handle_excel(temp_excel_file: Path) -> None:
    """Test StandardAdapter can handle Excel files."""
    adapter = StandardAdapter()

    try:
        # Should be able to handle valid Excel with required columns
        assert adapter.can_handle(temp_excel_file)
    finally:
        temp_excel_file.unlink()


def test_standard_adapter_cannot_handle_invalid_extension() -> None:
    """Test StandardAdapter rejects invalid file extensions."""
    adapter = StandardAdapter()

    with tempfile.NamedTemporaryFile(suffix=".txt") as f:
        assert not adapter.can_handle(Path(f.name))


def test_wind_cfe_adapter_can_handle_xlsx() -> None:
    """Test WindCFEAdapter can handle Excel files."""
    adapter = WindCFEAdapter()

    with tempfile.NamedTemporaryFile(suffix=".xlsx") as f:
        assert adapter.can_handle(Path(f.name))


def test_load_ohlc_csv(temp_csv_file: Path) -> None:
    """Test loading OHLC data from CSV file."""
    try:
        data = load_ohlc(temp_csv_file)

        assert isinstance(data, OHLCData)
        assert len(data.df) == 5
        assert "datetime" in data.df.columns
        assert "open" in data.df.columns
        assert "high" in data.df.columns
        assert "low" in data.df.columns
        assert "close" in data.df.columns
    finally:
        temp_csv_file.unlink()


def test_load_ohlc_excel(temp_excel_file: Path) -> None:
    """Test loading OHLC data from Excel file."""
    try:
        data = load_ohlc(temp_excel_file)

        assert isinstance(data, OHLCData)
        assert len(data.df) == 5
        assert "datetime" in data.df.columns
    finally:
        temp_excel_file.unlink()


def test_load_ohlc_with_explicit_adapter(temp_csv_file: Path) -> None:
    """Test loading with explicitly specified adapter."""
    try:
        data = load_ohlc(temp_csv_file, adapter="standard")

        assert isinstance(data, OHLCData)
        assert len(data.df) == 5
    finally:
        temp_csv_file.unlink()


def test_load_ohlc_invalid_adapter(temp_csv_file: Path) -> None:
    """Test loading with invalid adapter name."""
    try:
        with pytest.raises(ValueError, match="未知适配器"):
            load_ohlc(temp_csv_file, adapter="nonexistent")
    finally:
        temp_csv_file.unlink()


def test_load_ohlc_file_not_found() -> None:
    """Test loading non-existent file."""
    with pytest.raises(FileNotFoundError, match="文件不存在"):
        load_ohlc("nonexistent_file.csv")


def test_load_ohlc_unsupported_extension() -> None:
    """Test loading file with unsupported extension."""
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
        f.write(b"test content")
        temp_path = Path(f.name)

    try:
        with pytest.raises(ValueError, match="无法找到处理"):
            load_ohlc(temp_path)
    finally:
        temp_path.unlink()


def test_ohlc_data_schema() -> None:
    """Test OHLCData schema validation."""
    df = pd.DataFrame(
        {
            "datetime": pd.date_range("2024-01-01", periods=3, freq="D"),
            "open": [100, 101, 102],
            "high": [102, 103, 104],
            "low": [99, 100, 101],
            "close": [101, 102, 103],
            "volume": [1000, 1100, 1200],
        }
    )

    data = OHLCData(df=df, symbol="TEST", name="Test Data")

    assert data.symbol == "TEST"
    assert data.name == "Test Data"
    assert len(data.df) == 3
    assert data.date_range[0] == df["datetime"].iloc[0]
    assert data.date_range[1] == df["datetime"].iloc[-1]


def test_standard_adapter_load_validates_columns(temp_csv_file: Path) -> None:
    """Test that StandardAdapter validates required columns."""
    try:
        data = load_ohlc(temp_csv_file, adapter="standard")

        required_cols = ["datetime", "open", "high", "low", "close"]
        for col in required_cols:
            assert col in data.df.columns
    finally:
        temp_csv_file.unlink()


def test_load_ohlc_with_missing_columns() -> None:
    """Test loading data with missing required columns."""
    df = pd.DataFrame(
        {
            "datetime": pd.date_range("2024-01-01", periods=3),
            "open": [100, 101, 102],
            # Missing high, low, close
        }
    )

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        df.to_csv(f.name, index=False)
        temp_path = Path(f.name)

    try:
        with pytest.raises((ValueError, KeyError)):
            load_ohlc(temp_path)
    finally:
        temp_path.unlink()


def test_adapters_registry() -> None:
    """Test that adapters are properly registered."""
    assert "standard" in ADAPTERS
    assert "wind_cfe" in ADAPTERS
    assert isinstance(ADAPTERS["standard"], StandardAdapter)
    assert isinstance(ADAPTERS["wind_cfe"], WindCFEAdapter)


def test_standard_adapter_name() -> None:
    """Test StandardAdapter has correct name."""
    adapter = StandardAdapter()
    assert adapter.name == "Standard OHLC"


def test_wind_cfe_adapter_name() -> None:
    """Test WindCFEAdapter has correct name."""
    adapter = WindCFEAdapter()
    assert adapter.name == "Wind CFE"
