"""
bar_features.py
单根 K 线特征提取模块

基于 Al Brooks Price Action 理论，为每根 K 线计算基础特征"积木块"，
用于后续 H1/H2、Spike、Trading Range 等高级模式识别。

特征说明:
    - bar_dir: 方向 (+1=Bull, -1=Bear, 0=Doji)
    - body_pct: 实体占比 (0.0-1.0)
    - close_pos: 收盘位置 (0.0-1.0)
    - rel_size: 相对振幅 (当前振幅 / 过去N根平均振幅)
    - upper_tail_pct: 上影线占比 (0.0-1.0)
    - lower_tail_pct: 下影线占比 (0.0-1.0)
"""

import numpy as np
import pandas as pd


# 常量：用于判断 Doji 的实体占比阈值
DOJI_BODY_THRESHOLD = 0.1


def compute_bar_features(
    df: pd.DataFrame,
    rel_size_lookback: int = 20,
    doji_threshold: float = DOJI_BODY_THRESHOLD,
) -> pd.DataFrame:
    """
    计算单根 K 线特征。

    Args:
        df: 包含 OHLC 数据的 DataFrame，必须包含 'open', 'high', 'low', 'close' 列
        rel_size_lookback: 计算相对振幅时的回看周期，默认 20
        doji_threshold: 判断 Doji 的实体占比阈值，默认 0.1

    Returns:
        pd.DataFrame: 包含以下列的 DataFrame（保留原始索引）:
            - bar_dir: int, 方向 (+1=Bull, -1=Bear, 0=Doji)
            - body_pct: float, 实体占比 (0.0-1.0)
            - close_pos: float, 收盘位置 (0.0-1.0)
            - rel_size: float, 相对振幅
            - upper_tail_pct: float, 上影线占比 (0.0-1.0)
            - lower_tail_pct: float, 下影线占比 (0.0-1.0)

    Example:
        >>> from src.io import load_ohlc
        >>> from src.analysis import compute_bar_features
        >>> df = load_ohlc('data/000510.SH.csv')
        >>> features = compute_bar_features(df)
        >>> print(features.head())
    """
    # 提取 OHLC 列
    open_price = df["open"]
    high = df["high"]
    low = df["low"]
    close = df["close"]

    # 计算基础值
    total_range = high - low
    body_size = (close - open_price).abs()

    # 处理零振幅边界情况 (high == low)
    # 使用 np.where 避免除零警告
    safe_range = np.where(total_range == 0, np.nan, total_range)

    # 1. body_pct: 实体占比
    body_pct = body_size / safe_range

    # 2. close_pos: 收盘位置
    close_pos = (close - low) / safe_range

    # 3. bar_dir: 方向
    # 先计算原始方向
    raw_dir = np.sign(close - open_price).astype(int)
    # 如果 body_pct < doji_threshold，标记为 Doji (0)
    bar_dir = np.where(body_pct < doji_threshold, 0, raw_dir)

    # 4. rel_size: 相对振幅
    avg_range = total_range.rolling(window=rel_size_lookback, min_periods=1).mean()
    rel_size = total_range / avg_range

    # 5. upper_tail_pct: 上影线占比
    upper_tail = high - np.maximum(open_price, close)
    upper_tail_pct = upper_tail / safe_range

    # 6. lower_tail_pct: 下影线占比
    lower_tail = np.minimum(open_price, close) - low
    lower_tail_pct = lower_tail / safe_range

    # 构建结果 DataFrame
    result = pd.DataFrame(
        {
            "bar_dir": bar_dir,
            "body_pct": body_pct,
            "close_pos": close_pos,
            "rel_size": rel_size,
            "upper_tail_pct": upper_tail_pct,
            "lower_tail_pct": lower_tail_pct,
        },
        index=df.index,
    )

    return result


def add_bar_features(
    df: pd.DataFrame,
    rel_size_lookback: int = 20,
    doji_threshold: float = DOJI_BODY_THRESHOLD,
    prefix: str = "",
) -> pd.DataFrame:
    """
    在原始 DataFrame 上添加 K 线特征列（原地修改）。

    这是 compute_bar_features 的便捷包装，直接将特征列添加到输入 DataFrame。

    Args:
        df: 包含 OHLC 数据的 DataFrame
        rel_size_lookback: 计算相对振幅时的回看周期
        doji_threshold: 判断 Doji 的实体占比阈值
        prefix: 特征列名前缀，例如 "feat_" 会生成 "feat_bar_dir" 等

    Returns:
        pd.DataFrame: 添加了特征列的原始 DataFrame

    Example:
        >>> df = add_bar_features(df, prefix="feat_")
        >>> print(df[["close", "feat_bar_dir", "feat_body_pct"]].head())
    """
    features = compute_bar_features(df, rel_size_lookback, doji_threshold)
    for col in features.columns:
        df[f"{prefix}{col}"] = features[col]
    return df
