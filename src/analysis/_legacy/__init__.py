"""
_legacy 模块

遗留代码，保留供参考但不再积极维护。
这些模块主要基于缠论体系，与当前 Al Brooks Price Action 方向不同。

包含：
- kline_logic.py: K 线关系分类 (INSIDE/OUTSIDE/TREND_UP/TREND_DOWN)
- merging.py: 缠论式 K 线合并（处理包含关系）
- fractals.py: 缠论分型识别、笔、中枢

注意：kline_logic.py 仍被 process_ohlc.py 引用（用于 kline_status 计算）。
     如需完全移除，请先重构 process_ohlc.py。
"""

from .kline_logic import BarRelationship, classify_k_line_combination
from .process_ohlc import add_kline_status, process_and_save

__all__ = [
    "BarRelationship",
    "classify_k_line_combination",
    "add_kline_status",
    "process_and_save",
]
