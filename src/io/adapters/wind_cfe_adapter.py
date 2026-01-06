"""
adapters/wind_cfe_adapter.py
Wind 金融终端导出的中金所期货数据适配器。

支持格式:
    - xlsx 文件
    - 列名: 代码, 名称, 日期, 开盘价(元), 最高价(元), 最低价(元), 收盘价(元), ...
    - 自动过滤末尾的空行和 "数据来源：Wind" 行
"""

from pathlib import Path
from typing import Union

import pandas as pd

from ..schema import COL_CLOSE, COL_DATETIME, COL_HIGH, COL_LOW, COL_OPEN, COL_VOLUME, OHLCData
from .base import DataAdapter


class WindCFEAdapter(DataAdapter):
    """
    Wind 中金所期货数据适配器。

    处理 Wind 金融终端导出的 xlsx 格式期货数据，支持:
    - GBK/UTF-8 编码自动检测
    - 自动过滤无效行（空行、数据来源标注等）
    - 列名标准化映射
    """

    name = "Wind CFE"
    supported_extensions = [".xlsx", ".xls", ".csv"]

    # Wind 列名到标准列名的映射
    COLUMN_MAPPING = {
        "日期": COL_DATETIME,
        "开盘价(元)": COL_OPEN,
        "最高价(元)": COL_HIGH,
        "最低价(元)": COL_LOW,
        "收盘价(元)": COL_CLOSE,
        "成交量(股)": COL_VOLUME,
        # 兼容其他可能的列名格式
        "开盘价": COL_OPEN,
        "最高价": COL_HIGH,
        "最低价": COL_LOW,
        "收盘价": COL_CLOSE,
        "成交量": COL_VOLUME,
    }

    def load(self, path: Union[str, Path]) -> OHLCData:
        """
        加载 Wind 导出的期货数据。

        Args:
            path: xlsx/xls/csv 文件路径

        Returns:
            OHLCData: 标准化的 OHLC 数据
        """
        path = Path(path)

        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {path}")

        # 根据扩展名选择读取方式
        if path.suffix.lower() in [".xlsx", ".xls"]:
            df = pd.read_excel(path)
        else:
            # CSV 尝试多种编码
            try:
                df = pd.read_csv(path, encoding="gbk")
            except UnicodeDecodeError:
                df = pd.read_csv(path, encoding="utf-8")

        # 提取元数据（在过滤前）
        symbol = self._extract_symbol(df)
        name = self._extract_name(df)

        # 过滤无效行
        df = self._filter_invalid_rows(df)

        # 重命名列
        df = self._rename_columns(df)

        # 确保日期列是 datetime 类型
        df[COL_DATETIME] = pd.to_datetime(df[COL_DATETIME])

        # 按日期排序
        df = df.sort_values(COL_DATETIME).reset_index(drop=True)

        return OHLCData(df=df, symbol=symbol, name=name, source="Wind")

    def _extract_symbol(self, df: pd.DataFrame) -> str:
        """提取资产代码"""
        if "代码" in df.columns and len(df) > 0:
            # 取第一个有效值
            for val in df["代码"]:
                if pd.notna(val) and isinstance(val, str) and not val.startswith("数据来源"):
                    return val
        return ""

    def _extract_name(self, df: pd.DataFrame) -> str:
        """提取资产名称"""
        if "名称" in df.columns and len(df) > 0:
            for val in df["名称"]:
                if pd.notna(val) and isinstance(val, str):
                    return val
        return ""

    def _filter_invalid_rows(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        过滤无效行:
        1. 日期列为空的行
        2. 代码列包含 "数据来源" 的行
        """
        # 找到日期列（可能叫 '日期' 或其他名称）
        date_col = None
        for col in df.columns:
            if "日期" in col:
                date_col = col
                break

        if date_col is None:
            raise ValueError("未找到日期列")

        # 过滤条件
        valid_mask = df[date_col].notna()

        # 如果有代码列，过滤掉 "数据来源" 行
        if "代码" in df.columns:
            code_mask = df["代码"].apply(lambda x: not (isinstance(x, str) and "数据来源" in x))
            valid_mask = valid_mask & code_mask

        filtered_df = df[valid_mask].copy()

        print(f"  过滤无效行: {len(df)} -> {len(filtered_df)} 行")

        return filtered_df

    def _rename_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """将原始列名映射为标准列名"""
        rename_map = {}

        for orig_col in df.columns:
            if orig_col in self.COLUMN_MAPPING:
                rename_map[orig_col] = self.COLUMN_MAPPING[orig_col]

        df = df.rename(columns=rename_map)

        # 只保留标准列
        standard_cols = [COL_DATETIME, COL_OPEN, COL_HIGH, COL_LOW, COL_CLOSE]
        if COL_VOLUME in df.columns:
            standard_cols.append(COL_VOLUME)

        # 检查必需列是否存在
        missing = [
            col
            for col in [COL_DATETIME, COL_OPEN, COL_HIGH, COL_LOW, COL_CLOSE]
            if col not in df.columns
        ]
        if missing:
            raise ValueError(f"无法映射必需列: {missing}，原始列名: {df.columns.tolist()}")

        return df[standard_cols]
