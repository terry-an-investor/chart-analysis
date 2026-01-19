"""
src.io 模块
数据输入/输出层，包含数据模型、加载器和适配器。
"""

from .loader import list_adapters, load_ohlc, register_adapter
from .schema import (
    COL_CLOSE,
    COL_DATETIME,
    COL_HIGH,
    COL_LOW,
    COL_OPEN,
    COL_VOLUME,
    REQUIRED_COLUMNS,
    OHLCData,
)

__all__ = [
    "OHLCData",
    "COL_DATETIME",
    "COL_OPEN",
    "COL_HIGH",
    "COL_LOW",
    "COL_CLOSE",
    "COL_VOLUME",
    "REQUIRED_COLUMNS",
    "load_ohlc",
    "list_adapters",
    "register_adapter",
]
