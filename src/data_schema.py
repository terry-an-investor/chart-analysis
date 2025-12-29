"""
data_schema.py
定义标准化的 OHLC 数据格式，作为所有适配器输出的统一接口。

标准列名:
    - datetime: 日期时间 (datetime64)
    - open: 开盘价 (float64)
    - high: 最高价 (float64)
    - low: 最低价 (float64)
    - close: 收盘价 (float64)
    - volume: 成交量 (float64, 可选)
"""

from dataclasses import dataclass
from typing import Optional
import pandas as pd


# 标准列名常量
COL_DATETIME = "datetime"
COL_OPEN = "open"
COL_HIGH = "high"
COL_LOW = "low"
COL_CLOSE = "close"
COL_VOLUME = "volume"

# 必需列
REQUIRED_COLUMNS = [COL_DATETIME, COL_OPEN, COL_HIGH, COL_LOW, COL_CLOSE]


@dataclass
class OHLCData:
    """
    标准化的 OHLC 数据容器。
    
    Attributes:
        df: 标准化的 DataFrame，包含 datetime, open, high, low, close 列
        symbol: 资产代码 (如 'TL.CFE')
        name: 资产名称 (如 'CFFEX30年期国债期货')
        source: 数据来源 (如 'Wind', 'Binance')
    """
    df: pd.DataFrame
    symbol: str = ""
    name: str = ""
    source: str = ""
    
    def __post_init__(self):
        """验证 DataFrame 是否包含所有必需列"""
        missing = [col for col in REQUIRED_COLUMNS if col not in self.df.columns]
        if missing:
            raise ValueError(f"DataFrame 缺少必需列: {missing}")
        
        # 确保 datetime 列是索引或可排序
        if not pd.api.types.is_datetime64_any_dtype(self.df[COL_DATETIME]):
            raise ValueError(f"'{COL_DATETIME}' 列必须是 datetime 类型")
    
    def __len__(self) -> int:
        return len(self.df)
    
    def __repr__(self) -> str:
        return (
            f"OHLCData(symbol='{self.symbol}', name='{self.name}', "
            f"source='{self.source}', rows={len(self)})"
        )
    
    @property
    def date_range(self) -> tuple:
        """返回数据的日期范围 (start, end)"""
        return (
            self.df[COL_DATETIME].min(),
            self.df[COL_DATETIME].max()
        )
    
    def to_csv(self, path: str, **kwargs) -> None:
        """导出为 CSV 文件"""
        self.df.to_csv(path, index=False, **kwargs)
    
    @classmethod
    def from_csv(cls, path: str, symbol: str = "", name: str = "", 
                 source: str = "") -> "OHLCData":
        """从标准格式的 CSV 文件加载"""
        df = pd.read_csv(path, parse_dates=[COL_DATETIME])
        return cls(df=df, symbol=symbol, name=name, source=source)
