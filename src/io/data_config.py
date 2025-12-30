"""
src/io/data_config.py
数据源配置管理，集中定义所有需要获取的数据代码和参数。

用法:
    from src.io.data_config import DATA_SOURCES, get_config
    
    # 获取所有数据源配置
    for config in DATA_SOURCES:
        print(config.symbol, config.name)
    
    # 获取指定数据源配置
    config = get_config("TL.CFE")
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class DataConfig:
    """
    单个数据源的配置。
    
    Attributes:
        symbol: Wind代码 (如 'TL.CFE', '000510.SH')
        name: 资产名称
        trading_calendar: 交易日历代码 (CFFE/SSE/Nasdaq等)
        fields: 获取的字段列表，默认 OHLCV
        description: 数据描述
    """
    symbol: str
    name: str
    trading_calendar: str = "SSE"
    fields: str = "open,high,low,close,volume"
    description: str = ""
    
    @property
    def filename(self) -> str:
        """生成保存文件名 (将 . 替换为 _ 避免路径问题)"""
        return self.symbol.replace(".", "_") + ".xlsx"


# ============================================================
# 预定义数据源配置
# ============================================================

DATA_SOURCES: list[DataConfig] = [
    # 原有数据
    DataConfig(
        symbol="TL.CFE",
        name="30年期国债期货",
        trading_calendar="",  # 使用 Wind 默认 (通常是 CFFE 或跟随品种)
        description="CFFEX 30年期国债期货主力合约",
    ),
    DataConfig(
        symbol="TB10Y.WI",
        name="10年期国债收益率",
        trading_calendar="SSE",
        description="Wind 10年期国债收益率指数",
    ),
    
    # 新增数据
    DataConfig(
        symbol="881001.WI",
        name="万得全A",
        trading_calendar="SSE",
        description="Wind 万得全A指数",
    ),
    DataConfig(
        symbol="000510.SH",
        name="中证A500",
        trading_calendar="SSE",
        description="中证A500指数",
    ),
    DataConfig(
        symbol="NDX.GI",
        name="纳斯达克100",
        trading_calendar="Nasdaq",
        fields="open,high,low,close",  # 全球指数可能无成交量
        description="NASDAQ-100 Index",
    ),
    DataConfig(
        symbol="600415.SH",
        name="小商品城",
        trading_calendar="SSE",
        description="浙江小商品城",
    ),
]


# ============================================================
# 便捷函数
# ============================================================

def get_all_symbols() -> list[str]:
    """获取所有配置的代码列表"""
    return [cfg.symbol for cfg in DATA_SOURCES]


def get_config(symbol: str) -> Optional[DataConfig]:
    """
    根据代码获取配置。
    
    Args:
        symbol: Wind 代码
        
    Returns:
        DataConfig 或 None (如果未找到)
    """
    for cfg in DATA_SOURCES:
        if cfg.symbol == symbol:
            return cfg
    return None


def list_configs() -> None:
    """打印所有配置的数据源"""
    print("=" * 60)
    print("可用数据源配置")
    print("=" * 60)
    for cfg in DATA_SOURCES:
        print(f"  {cfg.symbol:<15} | {cfg.name:<15} | {cfg.trading_calendar}")
    print("=" * 60)
