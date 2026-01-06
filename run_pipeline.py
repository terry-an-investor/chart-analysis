"""
Pipeline entry point for market structure analysis.

Usage:
    uv run run_pipeline.py                    # Interactive file selection
    uv run run_pipeline.py data/raw/file.xlsx # Direct file specification
    uv run run_pipeline.py --log-level DEBUG  # With debug logging
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from pathlib import Path

import pandas as pd

from src.analysis.indicators import compute_ema
from src.analysis.interactive import ChartBuilder
from src.analysis.structure import (
    classify_swings_v2,
    detect_climax_reversal,
    detect_consecutive_reversal,
    detect_swings,
    merge_structure_with_events,
)
from src.config import AppConfig
from src.io import load_ohlc
from src.io.file_discovery import select_files_interactive
from src.logging import configure_logging

logger = logging.getLogger(__name__)


def process_file(input_file: str, config: AppConfig) -> None:
    """Process a single data file through the analysis pipeline."""
    output_dir = Path(config.output_dir)

    logger.info("=" * 60)
    logger.info("K 线分析流水线 (Market Structure)")
    logger.info("=" * 60)

    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"[Step 1/2] 加载数据: {input_file}")
    data = load_ohlc(input_file)
    logger.info(f"  加载完成: {data}")
    logger.info(f"  日期范围: {data.date_range[0].date()} ~ {data.date_range[1].date()}")

    input_path = Path(input_file)
    base_name = input_path.stem

    safe_name = re.sub(r'[\\/*?:"<>|]', "_", data.name)
    safe_symbol = data.symbol.replace(".", "_")

    if safe_name == safe_symbol or safe_name == data.symbol:
        dir_name = safe_symbol.lower()
    else:
        dir_name = f"{safe_symbol}_{safe_name}".lower()

    ticker_output_dir = output_dir / dir_name
    ticker_output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"\n[Step 2/2] 生成市场结构交互式图表...")

    df = data.df.copy()
    df["datetime"] = pd.to_datetime(df["datetime"])

    df_with_swings = detect_swings(df, window=config.analysis.swing_window)
    result = classify_swings_v2(df_with_swings, tolerance_pct=config.analysis.price_tolerance_pct)

    result = detect_climax_reversal(result, atr_multiplier=config.analysis.atr_multiplier)
    result = detect_consecutive_reversal(
        result, consecutive_count=config.analysis.consecutive_count
    )

    result = merge_structure_with_events(
        df_structure=result, df_events_climax=result, df_events_consecutive=result
    )

    ema_period = config.analysis.ema_period
    ema_data = compute_ema(df, period=ema_period)

    structure_plot = ticker_output_dir / f"{base_name}_structure.html"
    chart = ChartBuilder(result)
    chart.add_candlestick()
    chart.add_indicator(
        f"EMA{ema_period}", ema_data, config.ui.ema_color, line_width=config.ui.ema_line_width
    )

    chart.add_structure_levels(
        major_high=result["adjusted_major_high"],
        major_low=result["adjusted_major_low"],
        swing_types=result["swing_type"],
        swing_window=config.analysis.swing_window,
        secondary_item_high=result["major_high"],
        secondary_item_low=result["major_low"],
    )

    chart.build(str(structure_plot), title=f"{data.name} - Market Structure")

    logger.info("\n" + "=" * 60)
    logger.info("流水线完成！")
    logger.info("=" * 60)
    logger.info("生成文件:")
    logger.info(f"  - {structure_plot}  (市场结构图表)")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Market structure analysis pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("files", nargs="*", help="Input data files to process")
    parser.add_argument("--config", type=str, help="Path to configuration YAML file")
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)",
    )
    parser.add_argument("--log-to-file", action="store_true", help="Enable file logging")

    args = parser.parse_args()

    # Load configuration
    if args.config:
        config = AppConfig.from_yaml(args.config)
    else:
        config = AppConfig.from_yaml_or_default()

    # Override log level from command line
    if args.log_level:
        config.log_level = args.log_level
    if args.log_to_file:
        config.log_to_file = True

    # Configure logging
    configure_logging(
        level=config.log_level, log_to_file=config.log_to_file, log_dir=config.log_dir
    )

    logger.info(
        f"Configuration: swing_window={config.analysis.swing_window}, "
        f"price_tolerance={config.analysis.price_tolerance_pct}"
    )

    # Determine input files
    input_files: list[str] = []
    data_raw_dir = Path(config.data_raw_dir)
    default_file = data_raw_dir / "TB10Y.WI.xlsx"

    if args.files:
        input_files = args.files
    elif sys.stdin.isatty():
        input_files = select_files_interactive(data_raw_dir)
    else:
        logger.info(f"非交互模式，使用默认文件: {default_file}")
        input_files = [str(default_file)]

    total = len(input_files)
    for i, f in enumerate(input_files, 1):
        if total > 1:
            logger.info("\n" + "#" * 60)
            logger.info(f"正在处理第 {i}/{total} 个文件: {Path(f).name}")
            logger.info("#" * 60)

        try:
            process_file(f, config)
        except Exception as e:
            logger.error(f"\n❌ 处理失败 {f}: {e}", exc_info=True)
            if total == 1:
                raise


if __name__ == "__main__":
    main()
