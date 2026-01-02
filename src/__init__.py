"""
src 模块
K 线分析核心逻辑包。

结构:
    - io/: 数据输入输出层
    - analysis/: 分析逻辑层
"""

from .io import OHLCData, load_ohlc

__all__ = [
    "OHLCData",
    "load_ohlc",
]
