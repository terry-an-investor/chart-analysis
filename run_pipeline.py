"""
Pipeline entry point for market structure analysis.

Usage:
    uv run run_pipeline.py                    # Interactive file selection
    uv run run_pipeline.py data/raw/file.xlsx # Direct file specification
"""

import sys
import re
from pathlib import Path

import pandas as pd

from src.io import load_ohlc
from src.io.file_discovery import select_files_interactive
from src.analysis.structure import (
    detect_swings, 
    classify_swings_v2,
    detect_climax_reversal,
    detect_consecutive_reversal,
    merge_structure_with_events,
)
from src.analysis.indicators import compute_ema
from src.analysis.interactive import ChartBuilder

DATA_RAW_DIR = Path("data/raw")
OUTPUT_DIR = Path("output")
DEFAULT_FILE = "data/raw/TB10Y.WI.xlsx"


def process_file(input_file: str):
    """Process a single data file through the analysis pipeline."""
    print("=" * 60)
    print("K 线分析流水线 (Market Structure)")
    print("=" * 60)
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    print(f"\n[Step 1/2] 加载数据: {input_file}")
    data = load_ohlc(input_file)
    print(f"  加载完成: {data}")
    print(f"  日期范围: {data.date_range[0].date()} ~ {data.date_range[1].date()}")

    input_path = Path(input_file)
    base_name = input_path.stem
    
    safe_name = re.sub(r'[\\/*?:"<>|]', '_', data.name)
    safe_symbol = data.symbol.replace('.', '_')
    
    if safe_name == safe_symbol or safe_name == data.symbol:
        dir_name = safe_symbol.lower()
    else:
        dir_name = f"{safe_symbol}_{safe_name}".lower()
    
    ticker_output_dir = OUTPUT_DIR / dir_name
    ticker_output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n[Step 2/2] 生成市场结构交互式图表...")
    
    df = data.df.copy()
    df['datetime'] = pd.to_datetime(df['datetime'])
    
    df_with_swings = detect_swings(df, window=5)
    result = classify_swings_v2(df_with_swings)
    
    result = detect_climax_reversal(result, atr_multiplier=2.0)
    result = detect_consecutive_reversal(result, consecutive_count=3)
    
    result = merge_structure_with_events(
        df_structure=result,
        df_events_climax=result,
        df_events_consecutive=result
    )
    
    ema20 = compute_ema(df, period=20)
    
    structure_plot = ticker_output_dir / f"{base_name}_structure.html"
    chart = ChartBuilder(result)
    chart.add_candlestick()
    chart.add_indicator('EMA20', ema20, '#FFA500', line_width=1)
    
    chart.add_structure_levels(
        major_high=result['adjusted_major_high'],
        major_low=result['adjusted_major_low'],
        swing_types=result['swing_type'],
        swing_window=5,
        secondary_item_high=result['major_high'],
        secondary_item_low=result['major_low']
    )
    
    chart.build(str(structure_plot), title=f"{data.name} - Market Structure")
    
    print("\n" + "=" * 60)
    print("流水线完成！")
    print("=" * 60)
    print("生成文件:")
    print(f"  - {structure_plot}  (市场结构图表)")


def main():
    """Main entry point."""
    input_files = []
    
    if len(sys.argv) > 1:
        input_files = sys.argv[1:]
    elif sys.stdin.isatty():
        input_files = select_files_interactive(DATA_RAW_DIR)
    else:
        print(f"非交互模式，使用默认文件: {DEFAULT_FILE}")
        input_files = [DEFAULT_FILE]
    
    total = len(input_files)
    for i, f in enumerate(input_files, 1):
        if total > 1:
            print("\n" + "#" * 60)
            print(f"正在处理第 {i}/{total} 个文件: {Path(f).name}")
            print("#" * 60)
        
        try:
            process_file(f)
        except Exception as e:
            print(f"\n❌ 处理失败 {f}: {e}")
            if total == 1:
                raise


if __name__ == "__main__":
    main()
