"""
Configuration settings using Pydantic v2.

Supports loading from YAML files and environment variable overrides.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import BaseModel, Field


class AnalysisConfig(BaseModel):
    """Analysis parameters configuration."""

    swing_window: int = Field(
        default=5, description="Swing detection window (bars before/after)", ge=1, le=20
    )
    price_tolerance_pct: float = Field(
        default=0.001,
        description="Price tolerance percentage for double tops/bottoms",
        ge=0.0,
        le=0.1,
    )
    min_dist: int = Field(
        default=4, description="Minimum distance between fractal points", ge=1, le=50
    )
    atr_multiplier: float = Field(
        default=2.0, description="ATR multiplier for climax reversal detection", ge=0.5, le=10.0
    )
    consecutive_count: int = Field(
        default=3, description="Number of consecutive bars for reversal detection", ge=2, le=10
    )
    ema_period: int = Field(default=20, description="EMA period for trend indicator", ge=5, le=200)

    model_config = {
        "validate_assignment": True,
        "extra": "forbid",
    }


class UIConfig(BaseModel):
    """UI and visualization configuration."""

    chart_width: int = Field(default=1200, description="Chart width in pixels")
    chart_height: int = Field(default=600, description="Chart height in pixels")

    # Color scheme
    bull_color: str = Field(default="#26a69a", description="Bullish candle color")
    bear_color: str = Field(default="#ef5350", description="Bearish candle color")
    ema_color: str = Field(default="#FFA500", description="EMA line color")

    # Line widths
    ema_line_width: int = Field(default=1, ge=1, le=5)
    level_line_width: int = Field(default=1, ge=1, le=5)

    # Export settings
    export_bar_features: bool = Field(
        default=False, description="Export separate bar features chart"
    )

    model_config = {
        "validate_assignment": True,
        "extra": "forbid",
    }


class AppConfig(BaseModel):
    """Application-wide configuration."""

    analysis: AnalysisConfig = Field(default_factory=AnalysisConfig)
    ui: UIConfig = Field(default_factory=UIConfig)

    # Path settings
    data_raw_dir: str = Field(default="data/raw", description="Raw data directory")
    output_dir: str = Field(default="output", description="Output directory")
    log_dir: str = Field(default="logs", description="Log directory")

    # Logging settings
    log_level: str = Field(
        default="INFO", description="Logging level (DEBUG, INFO, WARNING, ERROR)"
    )
    log_to_file: bool = Field(default=False, description="Enable file logging")

    model_config = {
        "validate_assignment": True,
        "extra": "forbid",
    }

    @classmethod
    def from_yaml(cls, path: str | Path) -> AppConfig:
        """
        Load configuration from YAML file.

        Args:
            path: Path to YAML configuration file

        Returns:
            AppConfig instance

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If YAML is invalid
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")

        with open(path, "r") as f:
            data = yaml.safe_load(f)

        if data is None:
            data = {}

        # Apply environment variable overrides
        data = cls._apply_env_overrides(data)

        return cls(**data)

    @classmethod
    def from_yaml_or_default(cls, path: str | Path | None = None) -> AppConfig:
        """
        Load configuration from YAML file or use defaults.

        Args:
            path: Optional path to YAML configuration file

        Returns:
            AppConfig instance
        """
        if path is None:
            # Try default locations
            default_paths = [
                Path("config.yaml"),
                Path("config/config.yaml"),
                Path("src/config/analysis.yaml"),
            ]

            for default_path in default_paths:
                if default_path.exists():
                    path = default_path
                    break

        if path and Path(path).exists():
            return cls.from_yaml(path)

        # Use defaults with environment overrides
        data = cls._apply_env_overrides({})
        return cls(**data)

    @classmethod
    def _apply_env_overrides(cls, data: dict[str, Any]) -> dict[str, Any]:
        """
        Apply environment variable overrides to configuration.

        Environment variables should be prefixed with APP_CONFIG_
        Example: APP_CONFIG_ANALYSIS_SWING_WINDOW=7
        """
        # Analysis overrides
        if "analysis" not in data:
            data["analysis"] = {}

        env_mappings = {
            "APP_CONFIG_ANALYSIS_SWING_WINDOW": ("analysis", "swing_window", int),
            "APP_CONFIG_ANALYSIS_PRICE_TOLERANCE_PCT": ("analysis", "price_tolerance_pct", float),
            "APP_CONFIG_ANALYSIS_MIN_DIST": ("analysis", "min_dist", int),
            "APP_CONFIG_LOG_LEVEL": ("log_level", None, str),
            "APP_CONFIG_LOG_TO_FILE": (
                "log_to_file",
                None,
                lambda x: x.lower() in ("true", "1", "yes"),
            ),
        }

        for env_var, mapping in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                if len(mapping) == 3 and mapping[1] is not None:
                    # Nested config (e.g., analysis.swing_window)
                    section, key, converter = mapping
                    data[section][key] = converter(env_value)
                else:
                    # Top-level config
                    key, _, converter = mapping
                    data[key] = converter(env_value)

        return data

    def to_yaml(self, path: str | Path) -> None:
        """
        Save configuration to YAML file.

        Args:
            path: Path where to save the configuration
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w") as f:
            yaml.dump(self.model_dump(), f, default_flow_style=False, sort_keys=False)
