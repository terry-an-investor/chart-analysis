"""
src.analysis 模块
分析逻辑层，包含 K 线特征提取、指标计算、市场结构和交互式图表。
"""

from .indicators import compute_ema, compute_sma, compute_bollinger_bands
from .interactive import plot_interactive_kline, ChartBuilder, plot_bar_features_chart, plot_structure_chart
from .bar_features import compute_bar_features, add_bar_features
from .structure import (
    detect_swings, classify_swings, classify_swings_v2, compute_trend_state,
    compute_market_structure, add_structure_features
)

__all__ = [
    # 指标
    "compute_ema", "compute_sma", "compute_bollinger_bands",
    # 可视化
    "plot_interactive_kline", "ChartBuilder", "plot_bar_features_chart", "plot_structure_chart",
    # Phase 1: Bar Features
    "compute_bar_features", "add_bar_features",
    # Phase 2: Market Structure
    "detect_swings", "classify_swings", "classify_swings_v2", "compute_trend_state",
    "compute_market_structure", "add_structure_features",
]

