"""
bar_features.py
单根 K 线特征提取模块

基于 Al Brooks Price Action 理论，为每根 K 线计算基础特征"积木块"，
用于后续 H1/H2、Spike、Trading Range 等高级模式识别。

特征层级 (Feature Hierarchy):

L1 - 尺度特征 (Scale / Magnitude):
    - total_range: H - L                    # 总能量 (绝对值)
    - body_size: |C - O|                    # 净动能 (绝对值)
    - amplitude: (H - L) / O                # 振幅 (百分比)
    
    可选 (需要 preclose 列):
    - rel_true_range: TR / Preclose         # 相对真实波幅 (总能量规模)
    - movement_efficiency: |C-PC| / TR      # 运动效率 (信噪比, 1=极强共识, 0=剧烈分歧)
    - gap: (O - Preclose) / Preclose        # 跳空幅度 (%)
    - day_return: (C - Preclose) / Preclose # 日涨跌幅 (%)
    - true_range: max(H-L, |H-PC|, |L-PC|)  # 真实波幅 (ATR 单日版)

L2 - 形状特征 (Shape / Ratio, 标度无关):
    - bar_color: sign(C - O) → +1=阳, -1=阴, 0=平
    - body_pct: body_size / total_range     # 实体比例 [0, 1]
    - upper_tail_pct: upper_tail / range    # 上影比例 [0, 1]
    - lower_tail_pct: 1 - body_pct - upper_tail_pct  # 下影比例 (派生)
    
    极简特征对 (Minimal Pair for ML):
    - clv: (2*C - H - L) / (H - L)          # 收盘位置 [-1, +1]
    - signed_body: (C - O) / (H - L)        # 带符号实体比 [-1, +1]
    
    洞察: 锤子线 = 高CLV + 正signed_body; 上吊线 = 高CLV + 负signed_body

L3 - 形态分类 (Classification):
    主分类 (Primary - Binary):
    - is_trend_bar: body_pct >= 0.6
    - is_trading_range_bar: body_pct < 0.6 (非趋势即区间，包含 Doji)

    特殊标签 (Tags - Subset):
    - is_doji: body_pct < 0.25
    - is_pinbar: tail_pct > 0.66
    - shaved_top/bottom: 无影线
    - close_on_extreme: |clv| > 0.9 (收盘在最高/最低 5% 区间)
    
    可选 (需要 preclose 列):
    - open_in_body: 开盘在前日实体内 (O 在 PC 和 PC+Body 之间)

Note: rel_size (Multi-Bar 特征) 将在 multi_bar_analysis.py 中实现
"""

import numpy as np
import pandas as pd


# 常量：用于判断 Doji 的实体占比阈值
DOJI_BODY_THRESHOLD = 0.25  # 25% 更符合 Al Brooks 的定义

# 常量：Trend Bar 判定阈值 (body_pct >= 0.6 视为 Trend Bar)
TREND_BAR_THRESHOLD = 0.6

# 常量：Pin Bar 影线占比阈值 (单侧影线 > 66%)
PINBAR_TAIL_THRESHOLD = 0.66

# 常量：Shaved Bar 检测容差 (允许 2% 的误差)
SHAVED_TOLERANCE = 0.02

# 常量：Close on Extreme 阈值 (|clv| > 0.9 代表收盘在极值附近)
CLOSE_ON_EXTREME_THRESHOLD = 0.9


def compute_bar_features(
    df: pd.DataFrame,
    doji_threshold: float = DOJI_BODY_THRESHOLD,
) -> pd.DataFrame:
    """
    计算单根 K 线特征。

    Args:
        df: 包含 OHLC 数据的 DataFrame，必须包含 'open', 'high', 'low', 'close' 列
        doji_threshold: 判断 Doji 的实体占比阈值，默认 0.25

    Returns:
        pd.DataFrame: 包含以下列的 DataFrame（保留原始索引）:
            - bar_color: int, K线颜色 (+1=阳, -1=阴, 0=平)
            - body_pct: float, 实体占比 (0.0-1.0)
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

    # 2. bar_color: K 线颜色 (纯开收关系，不做形态判断)
    # +1 = 阳线 (C > O)
    # -1 = 阴线 (C < O)
    #  0 = 平线 (C == O，注意：这不等于 Doji！)
    bar_color = np.sign(close - open_price).astype(int)

    # 3. 上影线 (upper_tail) 和 下影线 (lower_tail)
    upper_tail = high - np.maximum(open_price, close)
    upper_tail_pct = upper_tail / safe_range
    
    lower_tail = np.minimum(open_price, close) - low
    lower_tail_pct = lower_tail / safe_range

    # 4. amplitude: 振幅 (百分比波动率)
    # 以开盘价为基准的百分比波动
    amplitude = total_range / open_price

    # 5. CLV (Close Location Value): 收盘位置指标
    # 范围 [-1, +1]: +1=收盘在最高, -1=收盘在最低, 0=收盘在中点
    clv = (2 * close - high - low) / safe_range

    # 6. signed_body: 带符号实体比 (Signed Return)
    # 范围 [-1, +1]: 结合了方向和实体比例
    # 洞察: 锤子线 = 高CLV + 正signed_body; 上吊线 = 高CLV + 负signed_body
    signed_body = (close - open_price) / safe_range

    # --- 可选: Preclose 相关特征 ---
    has_preclose = "preclose" in df.columns
    if has_preclose:
        preclose = df["preclose"]
        safe_preclose = np.where(preclose == 0, np.nan, preclose)
        
        # gap: 跳空幅度 (O - PC) / PC
        gap = (open_price - preclose) / safe_preclose
        
        # day_return: 日涨跌幅 (C - PC) / PC
        day_return = (close - preclose) / safe_preclose
        
        # true_range: 真实波幅 = max(H-L, |H-PC|, |L-PC|)
        # ATR 的单日版本，包含 gap 信息
        true_range = np.maximum(
            total_range,
            np.maximum(
                (high - preclose).abs(),
                (low - preclose).abs()
            )
        )
        
        # 7. rel_true_range: 能量规模
        rel_true_range = true_range / safe_preclose
        
        # 8. movement_efficiency: 运动效率 (位移/路程)
        # 1.0 代表极度高效的单边行情；0.0 代表剧烈震荡但无实际位移
        safe_tr_val = np.where(true_range == 0, np.nan, true_range)
        movement_efficiency = (close - preclose).abs() / safe_tr_val
        
        # 9. open_in_body: 开盘是否在前日实体内
        # 需要前日的 open 和 close 来确定前日实体边界
        # 由于我们只有 preclose，所以这里用 preclose 作为前日实体的"中点"近似
        # open_in_body 定义为: O 在前日收盘价附近 (|O - PC| / PC < typical_body_pct)
        # 更简单的定义: |gap| < 0.01 (1% 以内的跳空算作"在实体内")
        # Al Brooks 定义: 开盘在前日 K 线的实体内部，表示“延续”而非“突破”
        open_in_body = gap.abs() < 0.01  # |gap| < 1%

    # --- L4: 布尔分类器 (基于 L2 阈值) ---
    
    # 极端性特征 (Shaved Bars): 直接使用 L2 比率
    shaved_top = upper_tail_pct <= SHAVED_TOLERANCE
    shaved_bottom = lower_tail_pct <= SHAVED_TOLERANCE

    # --- 形态分类特征 (Morphology Classifiers) ---
    
    # 1. 主分类 (Trend vs Trading Range) - 二元对立
    # Al Brooks 定义: 任何不是 Trend Bar 的 K 线都是 Trading Range Bar (包括 Doji)
    is_trend_bar = body_pct >= TREND_BAR_THRESHOLD
    is_trading_range_bar = ~is_trend_bar

    # 2. 特殊形态标签 (Tags / Subsets)
    # Doji: 实体极小的 Trading Range Bar
    is_doji = body_pct < doji_threshold
    
    # Pinbar (Reversal): 单侧影线极长
    # 通常是 Trading Range Bar，但具有反转意义
    is_pinbar = (
        ((upper_tail_pct > PINBAR_TAIL_THRESHOLD) | (lower_tail_pct > PINBAR_TAIL_THRESHOLD))
        & (body_pct < (1 - PINBAR_TAIL_THRESHOLD))
    )
    
    # 3. Close on Extreme: 收盘在极值附近
    # |clv| > 0.9 表示收盘在最高/最低 5% 区间，代表极强的多空控盘
    close_on_extreme = np.abs(clv) > CLOSE_ON_EXTREME_THRESHOLD

    # 构建结果 DataFrame (按层级排序)
    result_dict = {
        # --- L1: 尺度特征 (Scale) ---
        "total_range": total_range,  # 总能量 (H - L)
        "body_size": body_size,      # 净动能 |C - O|
        "amplitude": amplitude,      # 振幅 (H - L) / O
    }
    
    # 可选: Preclose 相关特征
    if has_preclose:
        result_dict.update({
            "gap": gap,
            "day_return": day_return,
            "true_range": true_range,
            "rel_true_range": rel_true_range,
            "movement_efficiency": movement_efficiency,
            "open_in_body": open_in_body,  # 开盘在前日实体内
        })
    
    # --- L2: 形状特征 (Shape) ---
    result_dict.update({
        "bar_color": bar_color,      # 方向 (+1=阳, -1=阴, 0=平)
        "body_pct": body_pct,        # 实体比例 [0, 1]
        "upper_tail_pct": upper_tail_pct,  # 上影比例 [0, 1]
        "lower_tail_pct": lower_tail_pct,  # 下影比例 [0, 1] (派生)
        
        # --- L2.5: 极简特征对 (Minimal Pair for ML) ---
        "clv": clv,                  # 收盘位置 [-1, +1]
        "signed_body": signed_body,  # 带符号实体比 [-1, +1]
        
        # --- L3: 布尔分类器 (Classifiers) ---
        # 极端性 (Shaved)
        "shaved_top": shaved_top,
        "shaved_bottom": shaved_bottom,
        # 形态 (Binary)
        "is_trend_bar": is_trend_bar,
        "is_trading_range_bar": is_trading_range_bar,
        # 特殊标签
        "is_doji": is_doji,
        "is_pinbar": is_pinbar,
        "close_on_extreme": close_on_extreme,  # 收盘在极值附近
    })
    
    result = pd.DataFrame(result_dict, index=df.index)

    return result


def add_bar_features(
    df: pd.DataFrame,
    doji_threshold: float = DOJI_BODY_THRESHOLD,
    prefix: str = "",
) -> pd.DataFrame:
    """
    在原始 DataFrame 上添加 K 线特征列（原地修改）。

    这是 compute_bar_features 的便捷包装，直接将特征列添加到输入 DataFrame。

    Args:
        df: 包含 OHLC 数据的 DataFrame
        doji_threshold: 判断 Doji 的实体占比阈值
        prefix: 特征列名前缀，例如 "feat_" 会生成 "feat_bar_color" 等

    Returns:
        pd.DataFrame: 添加了特征列的原始 DataFrame

    Example:
        >>> df = add_bar_features(df, prefix="feat_")
        >>> print(df[["close", "feat_bar_color", "feat_body_pct"]].head())
    """
    features = compute_bar_features(df, doji_threshold)
    for col in features.columns:
        df[f"{prefix}{col}"] = features[col]
    return df
