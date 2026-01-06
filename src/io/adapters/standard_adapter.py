"""
adapters/standard_adapter.py
标准 OHLC 数据适配器。

处理已经是标准格式的数据文件（列名: datetime, open, high, low, close）。
这通常用于加载由 fetch_data.py 获取并保存的数据。
"""

from pathlib import Path
from typing import Union

import pandas as pd

from ..schema import (
    COL_CLOSE,
    COL_DATETIME,
    COL_HIGH,
    COL_LOW,
    COL_OPEN,
    COL_VOLUME,
    REQUIRED_COLUMNS,
    OHLCData,
)
from .base import DataAdapter


class StandardAdapter(DataAdapter):
    """
    标准格式数据适配器。

    检测规则:
    文件包含所有必需的标准列名 (datetime, open, high, low, close)。
    """

    name = "Standard OHLC"
    supported_extensions = [".xlsx", ".xls", ".csv"]

    def can_handle(self, path: Union[str, Path]) -> bool:
        """
        检查文件是否符合标准格式。

        除了检查扩展名，还会读取文件头来验证列名。
        """
        if not super().can_handle(path):
            return False

        try:
            # 读取文件头 (只读第一行)
            path = Path(path)
            if path.suffix.lower() in [".xlsx", ".xls"]:
                # Excel 需要读取一点数据来获取 columns
                df = pd.read_excel(path, nrows=0)
            else:
                df = pd.read_csv(path, nrows=0)

            # 检查是否包含所有必需列
            columns = set(df.columns)
            missing = [col for col in REQUIRED_COLUMNS if col not in columns]

            # 如果没有缺失列，说明是标准格式
            return len(missing) == 0

        except Exception:
            # 读取出错则认为不匹配
            return False

    def load(self, path: Union[str, Path]) -> OHLCData:
        """
        加载标准格式数据。
        """
        path = Path(path)

        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {path}")

        # 读取数据
        if path.suffix.lower() in [".xlsx", ".xls"]:
            df = pd.read_excel(path)
        else:
            df = pd.read_csv(path)

        # 确保 datetime 列是 datetime 类型
        if COL_DATETIME in df.columns:
            df[COL_DATETIME] = pd.to_datetime(df[COL_DATETIME])

        # 按日期排序
        df = df.sort_values(COL_DATETIME).reset_index(drop=True)

        # --------------------------------------------------------
        # 处理缺失的 open 列 (常见于利率/指数数据)
        # 策略: 用前一日的 close 填充当日 open，首日用当日 close
        # --------------------------------------------------------
        if COL_OPEN in df.columns and df[COL_OPEN].isna().any():
            df[COL_OPEN] = df[COL_OPEN].fillna(df[COL_CLOSE].shift(1))
            # 首日无前一日数据，用当日 close 填充
            df[COL_OPEN] = df[COL_OPEN].fillna(df[COL_CLOSE])

        # 尝试从文件名推断 symbol
        symbol = path.stem.replace("_", ".")

        # 尝试从配置中获取对应的中文名称
        from ..data_config import get_config

        config = get_config(symbol)

        name = symbol
        if config:
            name = config.name
        else:
            # 1. 尝试从本地缓存读取名称 (避免 API 调用)
            import json

            cache_file = Path("data") / "security_names.json"
            if cache_file.exists():
                try:
                    with open(cache_file, "r", encoding="utf-8") as f:
                        cache = json.load(f)
                        if symbol in cache:
                            name = cache[symbol]
                except Exception:
                    pass
            # 不再调用 Wind API 获取名称，只使用缓存

        return OHLCData(df=df, symbol=symbol, name=name, source="Standard File")
