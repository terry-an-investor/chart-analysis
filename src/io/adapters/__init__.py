"""
adapters 模块
提供各种数据源的适配器，将原始数据转换为标准 OHLC 格式。
"""

from .base import DataAdapter
from .standard_adapter import StandardAdapter
from .wind_api_adapter import WindAPIAdapter
from .wind_cfe_adapter import WindCFEAdapter

__all__ = ["DataAdapter", "WindCFEAdapter", "WindAPIAdapter", "StandardAdapter"]
