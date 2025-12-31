"""
src.analysis 模块
分析逻辑层，包含K线分类、合并、分型识别和交互式图表。
"""

from .kline_logic import BarRelationship, classify_k_line_combination
from .process_ohlc import add_kline_status, process_and_save

from .indicators import compute_ema, compute_sma, compute_bollinger_bands
from .interactive import plot_interactive_kline, ChartBuilder, plot_bar_features_chart
from .bar_features import compute_bar_features, add_bar_features

__all__ = [
    "BarRelationship", "classify_k_line_combination",
    "add_kline_status", "process_and_save",
    "compute_ema", "compute_sma", "compute_bollinger_bands",
    "plot_interactive_kline", "ChartBuilder", "plot_bar_features_chart",
    "compute_bar_features", "add_bar_features",
]

