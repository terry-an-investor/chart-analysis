"""
Tests for configuration management.

Tests Pydantic configuration models and YAML loading.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import yaml

from src.config import AnalysisConfig, AppConfig, UIConfig


def test_analysis_config_defaults() -> None:
    """Test AnalysisConfig default values."""
    config = AnalysisConfig()

    assert config.swing_window == 5
    assert config.price_tolerance_pct == 0.001
    assert config.min_dist == 4
    assert config.atr_multiplier == 2.0
    assert config.consecutive_count == 3
    assert config.ema_period == 20


def test_analysis_config_custom_values() -> None:
    """Test AnalysisConfig with custom values."""
    config = AnalysisConfig(swing_window=7, price_tolerance_pct=0.002, min_dist=6)

    assert config.swing_window == 7
    assert config.price_tolerance_pct == 0.002
    assert config.min_dist == 6


def test_analysis_config_validation() -> None:
    """Test AnalysisConfig field validation."""
    # Valid values
    config = AnalysisConfig(swing_window=5, min_dist=4)
    assert config.swing_window == 5

    # Invalid values should raise validation error
    with pytest.raises(Exception):  # Pydantic validation error
        AnalysisConfig(swing_window=0)  # Must be >= 1


def test_ui_config_defaults() -> None:
    """Test UIConfig default values."""
    config = UIConfig()

    assert config.chart_width == 1200
    assert config.chart_height == 600
    assert config.bull_color == "#26a69a"
    assert config.bear_color == "#ef5350"
    assert config.ema_color == "#FFA500"
    assert config.export_bar_features is False


def test_ui_config_custom_values() -> None:
    """Test UIConfig with custom values."""
    config = UIConfig(chart_width=1400, chart_height=700, export_bar_features=True)

    assert config.chart_width == 1400
    assert config.chart_height == 700
    assert config.export_bar_features is True


def test_app_config_defaults() -> None:
    """Test AppConfig default values."""
    config = AppConfig()

    assert isinstance(config.analysis, AnalysisConfig)
    assert isinstance(config.ui, UIConfig)
    assert config.data_raw_dir == "data/raw"
    assert config.output_dir == "output"
    assert config.log_level == "INFO"
    assert config.log_to_file is False


def test_app_config_nested() -> None:
    """Test AppConfig with nested configurations."""
    config = AppConfig(analysis=AnalysisConfig(swing_window=7), ui=UIConfig(chart_width=1400))

    assert config.analysis.swing_window == 7
    assert config.ui.chart_width == 1400


def test_app_config_from_yaml() -> None:
    """Test loading AppConfig from YAML file."""
    yaml_content = """
analysis:
  swing_window: 7
  price_tolerance_pct: 0.002
  min_dist: 5

ui:
  chart_width: 1400
  chart_height: 700

log_level: "DEBUG"
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        temp_path = Path(f.name)

    try:
        config = AppConfig.from_yaml(temp_path)

        assert config.analysis.swing_window == 7
        assert config.analysis.price_tolerance_pct == 0.002
        assert config.ui.chart_width == 1400
        assert config.log_level == "DEBUG"
    finally:
        temp_path.unlink()


def test_app_config_from_yaml_missing_file() -> None:
    """Test loading from non-existent YAML file."""
    with pytest.raises(FileNotFoundError):
        AppConfig.from_yaml("nonexistent_config.yaml")


def test_app_config_from_yaml_or_default_with_file() -> None:
    """Test from_yaml_or_default with existing file."""
    yaml_content = """
analysis:
  swing_window: 9

log_level: "WARNING"
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        temp_path = Path(f.name)

    try:
        config = AppConfig.from_yaml_or_default(temp_path)

        assert config.analysis.swing_window == 9
        assert config.log_level == "WARNING"
    finally:
        temp_path.unlink()


def test_app_config_from_yaml_or_default_no_file() -> None:
    """Test from_yaml_or_default falls back to defaults."""
    config = AppConfig.from_yaml_or_default("definitely_nonexistent.yaml")

    # Should use defaults
    assert config.analysis.swing_window == 5
    assert config.log_level == "INFO"


def test_app_config_to_yaml() -> None:
    """Test saving AppConfig to YAML file."""
    config = AppConfig(
        analysis=AnalysisConfig(swing_window=7), ui=UIConfig(chart_width=1400), log_level="DEBUG"
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "test_config.yaml"
        config.to_yaml(output_path)

        assert output_path.exists()

        # Read back and verify
        with open(output_path) as f:
            data = yaml.safe_load(f)

        assert data["analysis"]["swing_window"] == 7
        assert data["ui"]["chart_width"] == 1400
        assert data["log_level"] == "DEBUG"


def test_app_config_env_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test environment variable overrides."""
    # Set environment variables
    monkeypatch.setenv("APP_CONFIG_ANALYSIS_SWING_WINDOW", "8")
    monkeypatch.setenv("APP_CONFIG_LOG_LEVEL", "ERROR")
    monkeypatch.setenv("APP_CONFIG_LOG_TO_FILE", "true")

    config = AppConfig.from_yaml_or_default()

    assert config.analysis.swing_window == 8
    assert config.log_level == "ERROR"
    assert config.log_to_file is True


def test_config_validation() -> None:
    """Test that config validation works."""
    # Valid config
    config = AppConfig(log_level="INFO")
    assert config.log_level == "INFO"

    # Can set valid value
    config.log_level = "DEBUG"
    assert config.log_level == "DEBUG"


def test_analysis_config_bounds() -> None:
    """Test AnalysisConfig field bounds."""
    # Valid bounds
    config = AnalysisConfig(swing_window=1, min_dist=1)
    assert config.swing_window == 1

    config = AnalysisConfig(swing_window=20, min_dist=50)
    assert config.swing_window == 20
    assert config.min_dist == 50

    # Invalid bounds
    with pytest.raises(Exception):
        AnalysisConfig(swing_window=21)  # exceeds max

    with pytest.raises(Exception):
        AnalysisConfig(min_dist=51)  # exceeds max
