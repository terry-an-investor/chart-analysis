"""
indicators.py
技术指标计算模块

提供常用的技术分析指标计算函数，用于叠加在 K 线图上。
"""

import pandas as pd


def compute_ema(df: pd.DataFrame, period: int, column: str = "close") -> pd.Series:
    """
    计算指数移动平均 (Exponential Moving Average)

    Args:
        df: 包含价格数据的 DataFrame
        period: EMA 周期 (如 20, 50, 200)
        column: 用于计算的列名，默认 'close'

    Returns:
        pd.Series: EMA 值序列

    Example:
        >>> df['ema20'] = compute_ema(df, 20)
    """
    return df[column].ewm(span=period, adjust=False).mean()


def compute_sma(df: pd.DataFrame, period: int, column: str = "close") -> pd.Series:
    """
    计算简单移动平均 (Simple Moving Average)

    Args:
        df: 包含价格数据的 DataFrame
        period: SMA 周期 (如 5, 10, 20)
        column: 用于计算的列名，默认 'close'

    Returns:
        pd.Series: SMA 值序列

    Example:
        >>> df['sma5'] = compute_sma(df, 5)
    """
    return df[column].rolling(window=period).mean()


def compute_bollinger_bands(
    df: pd.DataFrame, period: int = 20, std_dev: float = 2.0, column: str = "close"
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    计算布林带 (Bollinger Bands)

    Args:
        df: 包含价格数据的 DataFrame
        period: 中轨 SMA 周期，默认 20
        std_dev: 标准差倍数，默认 2.0
        column: 用于计算的列名，默认 'close'

    Returns:
        tuple: (upper_band, middle_band, lower_band)

    Example:
        >>> upper, middle, lower = compute_bollinger_bands(df)
    """
    middle = df[column].rolling(window=period).mean()
    std = df[column].rolling(window=period).std()
    upper = middle + (std * std_dev)
    lower = middle - (std * std_dev)
    return upper, middle, lower
