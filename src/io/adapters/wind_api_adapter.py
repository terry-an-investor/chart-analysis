"""
adapters/wind_api_adapter.py
Wind Python API 数据适配器，通过 Wind 终端 API 在线获取数据。

要求:
    - 已安装 Wind 金融终端
    - 已修复 WindPy Python 接口
    - Wind 终端已启动并登录

用法:
    from src.io.adapters import WindAPIAdapter

    adapter = WindAPIAdapter()
    data = adapter.fetch("TL.CFE", start_date="2023-01-01", end_date="2024-12-30")
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Union

import pandas as pd

from ..schema import COL_CLOSE, COL_DATETIME, COL_HIGH, COL_LOW, COL_OPEN, COL_VOLUME, OHLCData
from .base import DataAdapter


class WindAPIAdapter(DataAdapter):
    """
    Wind Python API 数据适配器。

    通过 WindPy 的 w.wsd() 函数获取日K线数据，并转换为标准 OHLCData 格式。
    """

    name = "Wind API"
    supported_extensions = []  # 此适配器不处理文件

    # Wind API 返回字段到标准列名的映射
    FIELD_MAPPING = {
        "OPEN": COL_OPEN,
        "HIGH": COL_HIGH,
        "LOW": COL_LOW,
        "CLOSE": COL_CLOSE,
        "VOLUME": COL_VOLUME,
    }

    def __init__(self):
        self._wind = None
        self._connected = False

    def _ensure_connected(self) -> None:
        """确保 Wind 已连接"""
        if self._connected:
            return

        try:
            from WindPy import w

            self._wind = w
        except ImportError:
            raise ImportError(
                "未找到 WindPy 模块。请确保:\n"
                "1. 已安装 Wind 金融终端\n"
                "2. 已通过终端的'插件修复'功能修复 Python 接口\n"
                "3. 当前 Python 环境已被 Wind 识别"
            )

        # 启动 Wind（waitTime 设置超时时间）
        result = self._wind.start(waitTime=60)
        if result.ErrorCode != 0:
            raise ConnectionError(
                f"Wind 连接失败 (ErrorCode={result.ErrorCode})。\n"
                "请确保 Wind 金融终端已启动并登录。"
            )

        self._connected = True
        print("Wind API 已连接")

    def disconnect(self) -> None:
        """断开 Wind 连接"""
        if self._wind and self._connected:
            self._wind.stop()
            self._connected = False
            print("Wind API 已断开")

    def load(self, path: Union[str, Path]) -> OHLCData:
        """
        DataAdapter 接口实现（不支持，此适配器用于API获取）。

        请使用 fetch() 方法获取数据。
        """
        raise NotImplementedError("WindAPIAdapter 不支持从文件加载，请使用 fetch() 方法")

    def fetch(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fields: str = "open,high,low,close,volume",
        trading_calendar: str = "SSE",
        name: str = "",
    ) -> OHLCData:
        """
        从 Wind API 获取日K线数据。

        Args:
            symbol: Wind 代码 (如 'TL.CFE', '000510.SH')
            start_date: 起始日期 (格式 'YYYY-MM-DD')，默认2年前
            end_date: 截止日期 (格式 'YYYY-MM-DD')，默认今天
            fields: 获取的字段，逗号分隔
            trading_calendar: 交易日历 (SSE/CFFE/Nasdaq等)
            name: 资产名称 (可选，用于 OHLCData 元信息)

        Returns:
            OHLCData: 标准化的 OHLC 数据

        Raises:
            ImportError: WindPy 未安装
            ConnectionError: Wind 连接失败
            ValueError: 数据获取失败
        """
        self._ensure_connected()

        # 设置默认日期范围
        if end_date is None:
            # 默认为昨天 (因为今天可能并未结束)
            end_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        if start_date is None:
            # 默认为 end_date 往前推 2 年
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            start_date = (end_dt - timedelta(days=730)).strftime("%Y-%m-%d")

        print(f"正在获取 {symbol} 数据: {start_date} ~ {end_date}")

        # 构建 options 字符串
        options = ""
        if trading_calendar:
            options += f"TradingCalendar={trading_calendar};"

        # 移除末尾分号
        options = options.rstrip(";")

        # 调用 Wind API
        error_code, df = self._wind.wsd(symbol, fields, start_date, end_date, options, usedf=True)

        # 错误处理
        if error_code != 0:
            raise ValueError(
                f"Wind API 错误 (ErrorCode={error_code}): "
                f"无法获取 {symbol} 数据。\n"
                f"请检查代码是否正确，以及您是否有权限访问该数据。"
            )

        if df is None or df.empty:
            raise ValueError(f"未获取到 {symbol} 的数据")

        # 转换 DataFrame
        df = self._transform_dataframe(df)

        print(f"  获取成功: {len(df)} 条记录")

        return OHLCData(df=df, symbol=symbol, name=name, source="Wind API")

    def _transform_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        将 Wind API 返回的 DataFrame 转换为标准格式。

        Wind wsd 返回的 DataFrame:
        - index 是日期 (datetime)
        - columns 是大写字段名 (OPEN, HIGH, LOW, CLOSE, VOLUME)
        """
        # 将 index 转为 datetime 列
        df = df.reset_index()
        df = df.rename(columns={"index": COL_DATETIME})

        # 确保 datetime 列是 datetime 类型
        df[COL_DATETIME] = pd.to_datetime(df[COL_DATETIME])

        # 重命名列（大写转小写）
        rename_map = {}
        for col in df.columns:
            col_upper = col.upper()
            if col_upper in self.FIELD_MAPPING:
                rename_map[col] = self.FIELD_MAPPING[col_upper]

        df = df.rename(columns=rename_map)

        # 选择标准列
        standard_cols = [COL_DATETIME, COL_OPEN, COL_HIGH, COL_LOW, COL_CLOSE]
        if COL_VOLUME in df.columns:
            standard_cols.append(COL_VOLUME)

        # 过滤掉全为 NaN 的行
        df = df.dropna(subset=[COL_OPEN, COL_HIGH, COL_LOW, COL_CLOSE], how="all")

        # 按日期排序
        df = df.sort_values(COL_DATETIME).reset_index(drop=True)

        return df[standard_cols]

    def get_security_name(self, symbol: str) -> str:
        """
        通过 Wind API 获取资产的中文名称。

        Returns:
            str: 资产名称，如果获取失败则返回 symbol 本身
        """
        self._ensure_connected()
        try:
            # 使用 w.wss 获取静态名称
            data = self._wind.wss(symbol, "sec_name")
            if data.ErrorCode == 0 and data.Data:
                return str(data.Data[0][0])
        except Exception:
            pass
        return symbol

    def fetch_and_save(
        self, symbol: str, output_dir: Union[str, Path] = "data/raw", **kwargs
    ) -> Path:
        """
        获取数据并保存为 Excel 文件。

        Args:
            symbol: Wind 代码
            output_dir: 输出目录
            **kwargs: 传递给 fetch() 的其他参数

        Returns:
            Path: 保存的文件路径
        """
        # 获取数据
        data = self.fetch(symbol, **kwargs)

        # 构建输出路径
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # 文件名: 将 . 替换为 _ (例如 TL.CFE -> TL_CFE.xlsx)
        filename = symbol.replace(".", "_") + ".xlsx"
        output_path = output_dir / filename

        # 保存为 Excel
        data.df.to_excel(output_path, index=False)
        print(f"  已保存: {output_path}")

        return output_path

    def __del__(self):
        """析构时断开连接"""
        self.disconnect()
