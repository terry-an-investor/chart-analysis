"""
src.analysis 模块
分析逻辑层，包含 K 线特征提取、指标计算、市场结构和交互式图表。
"""

from .bar_features import add_bar_features, compute_bar_features
from .indicators import compute_bollinger_bands, compute_ema, compute_sma
from .interactive import (
    ChartBuilder,
    plot_bar_features_chart,
    plot_interactive_kline,
    plot_structure_chart,
)
from .structure import (
    add_structure_features,
    classify_swings,
    classify_swings_v2,
    compute_market_structure,
    compute_trend_state,
    detect_climax_reversal,
    detect_consecutive_reversal,
    detect_swings,
    merge_structure_with_events,
)

__all__ = [
    # 指标
    "compute_ema",
    "compute_sma",
    "compute_bollinger_bands",
    # 可视化
    "plot_interactive_kline",
    "ChartBuilder",
    "plot_bar_features_chart",
    "plot_structure_chart",
    # Phase 1: Bar Features
    "compute_bar_features",
    "add_bar_features",
    # Phase 2: Market Structure
    "detect_swings",
    "classify_swings",
    "classify_swings_v2",
    "compute_trend_state",
    "compute_market_structure",
    "add_structure_features",
    "detect_climax_reversal",
    "detect_consecutive_reversal",
    "merge_structure_with_events",
]
