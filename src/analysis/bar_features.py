"""
bar_features.py
单根 K 线特征提取模块

基于 Al Brooks Price Action 理论，为每根 K 线计算基础特征"积木块"，
用于后续 H1/H2、Spike、Trading Range 等高级模式识别。

特征层级 (Feature Hierarchy):

L1 - 尺度特征 (Scale / Magnitude) - 单日:
    - total_range: H - L                    # 总能量 (绝对值)
    - body_size: |C - O|                    # 净动能 (绝对值)
    - amplitude: (H - L) / O                # 振幅 (百分比)
    - rel_range_to_avg: Range / SMA(20)     # 相对规模 (Context)
    - is_climax_bar: rel_range > 2.0        # 高潮棒

L2 - 形状特征 (Shape / Ratio, 标度无关) - 单日:
    - bar_color: sign(C - O) → +1=阳, -1=阴, 0=平
    - body_pct: body_size / total_range     # 实体比例 [0, 1]
    - upper_tail_pct: upper_tail / range    # 上影比例 [0, 1]
    - lower_tail_pct: 1 - body_pct - upper_tail_pct  # 下影比例 (派生)
    
    极简特征对 (Minimal Pair for ML):
    - clv: (2*C - H - L) / (H - L)          # 收盘位置 [-1, +1]
    - signed_body: (C - O) / (H - L)        # 带符号实体比 [-1, +1]
    
    洞察: 锤子线 = 高CLV + 正signed_body; 上吊线 = 高CLV + 负signed_body

L3 - 形态分类 (Classification) - 单日:
    主分类 (Primary - Binary):
    - is_trend_bar: body_pct >= 0.6
    - is_trading_range_bar: body_pct < 0.6 (非趋势即区间，包含 Doji)

    特殊标签 (Tags - Subset):
    - is_doji: body_pct < 0.25
    - is_pinbar: tail_pct > 0.66
    - shaved_top/bottom: 无影线
    - close_on_extreme: |clv| > 0.9 (收盘在最高/最低 5% 区间)
    - is_strong_bull/bear_reversal: 强反转信号 (Al Brooks 定义)

L4 - 跨日与上下文特征 (Cross-Day / Context, 基于 shift(1)):
    动力学与波动 (Dynamics & Volatility):
    - gap: ln(O / prev_close)               # 跳空幅度 (Log %)
    - body_gap: curr_body_low - prev_body_high # 实体缺口 (趋势力度)
    - day_return: ln(C / prev_close)        # 日涨跌幅 (Log %)
    - true_range: max(H-L, |H-PC|, |L-PC|)  # 真实波幅 (ATR 单日版)
    - rel_true_range: TR / prev_close       # 相对真实波幅 (总能量规模)
    - movement_efficiency: |C-PC| / TR      # 运动效率 (信噪比, 1=极强共识, 0=剧烈分歧)

    形态关系 (Structural Relationship):
    - is_inside: Range 在前一日 Range 内 (波动率收缩，准备突破)
    - is_outside: Range 覆盖前一日 Range (震荡加剧，陷阱或反转)
    - is_outside_up: Outside Bar 且收盘 > 前日最高 (强力反转向上)
    - is_outside_down: Outside Bar 且收盘 < 前日最低 (强力反转向下)
    - gap_type: +1=向上突破 / 0=范围内 / -1=向下突破 (定调开盘意图)
    - overlap_pct: 与昨日重叠比例 [0, 1] (比例越高，趋势越弱)
    - open_in_body: |gap| < 1% (开盘在前日收盘附近，延续而非突破)
    - trend_streak: 连续 Trend Bar 计数 (动能惯性)

    吞没形态 (Engulfing Patterns):
    - is_bull_engulfing: 阳线实体完全覆盖前日阴线实体 (反转买入信号)
    - is_bear_engulfing: 阴线实体完全覆盖前日阳线实体 (反转卖出信号)

    Blended Candle (合并K线分析):
    - blend_open/close/high/low: 当前 + 前一日合并后的虚拟 K 线
    - blend_clv: 合并 K 线的 CLV (隐藏信号棒检测)
    - blend_body_pct: 合并 K 线的实体比例

    突破失败 (Failed Breakout):
    - failed_breakout_high: 突破前日最高但收盘收回 (陷阱)
    - failed_breakout_low: 突破前日最低但收盘收回 (陷阱)

L4.5 - 多K线上下文特征 (Multi-Bar Context, 基于滑动窗口):
    EMA 关系 (EMA Gravity):
    - dist_to_ema: (C - EMA) / EMA            # 乖离率 (趋势强度/超买超卖)
    - bar_pos_ema: +1=Low>EMA, -1=High<EMA, 0=跨越 # 相对位置 (Always In 提示)
    - ema_touch: High >= EMA >= Low           # 均线测试 ("磁力"回归)
    - gap_below_ema: High < EMA               # K线完全在EMA下方 (多头衰竭)
    - gap_above_ema: Low > EMA                # K线完全在EMA上方 (空头衰竭)

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
    ema_period: int = 20,
) -> pd.DataFrame:
    """
    计算单根 K 线特征。

    Args:
        df: 包含 OHLC 数据的 DataFrame，必须包含 'open', 'high', 'low', 'close' 列
        doji_threshold: 判断 Doji 的实体占比阈值，默认 0.25
        ema_period: EMA 周期，默认 20 (Al Brooks 标准)。如果 df 已包含 'ema' 列则使用现有值

    Returns:
        pd.DataFrame: 包含以下列的 DataFrame（保留原始索引）:
            - bar_color: int, K线颜色 (+1=阳, -1=阴, 0=平)
            - body_pct: float, 实体占比 (0.0-1.0)
            - upper_tail_pct: float, 上影线占比 (0.0-1.0)
            - lower_tail_pct: float, 下影线占比 (0.0-1.0)
            - dist_to_ema: float, 与 EMA 的乖离率
            - bar_pos_ema: int, 相对 EMA 位置 (+1/-1/0)

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

    # 4.5 rel_range_to_avg: 相对规模 (L1 Context)
    # Al Brooks: "This is a large trend bar" 
    # 使用 20 周期 SMA 作为基准。注意：前 19 个值为 NaN
    avg_range_20 = total_range.rolling(window=20).mean()
    rel_range_to_avg = total_range / avg_range_20
    
    # is_climax_bar: 高潮棒 (rel_range > 2.0)
    # 通常表示不可持续的极值或强力突破
    is_climax_bar = rel_range_to_avg > 2.0

    # 5. CLV (Close Location Value): 收盘位置指标
    # 范围 [-1, +1]: +1=收盘在最高, -1=收盘在最低, 0=收盘在中点
    clv = (2 * close - high - low) / safe_range

    # 6. signed_body: 带符号实体比 (Signed Return)
    # 范围 [-1, +1]: 结合了方向和实体比例
    # 洞察: 锤子线 = 高CLV + 正signed_body; 上吊线 = 高CLV + 负signed_body
    signed_body = (close - open_price) / safe_range

    # --- Preclose 相关特征 (基于 shift(1) 自动获取前日数据) ---
    # 统一使用 shift(1) 获取前日 OHLC
    prev_open = df["open"].shift(1)
    prev_high = df["high"].shift(1)
    prev_low = df["low"].shift(1)
    prev_close = df["close"].shift(1)
    prev_range = prev_high - prev_low
    
    # 安全除法处理
    safe_prev_close = np.where(prev_close == 0, np.nan, prev_close)
    safe_prev_range = np.where(prev_range == 0, np.nan, prev_range)
    
    # gap: 跳空幅度 (Log Return)
    # ln(O / PC) -> return NaN if O<=0 or PC<=0
    # 使用 np.where 确保 log 输入为正数
    gap_ratio = open_price / prev_close
    safe_gap_ratio = np.where((open_price > 0) & (prev_close > 0), gap_ratio, np.nan)
    gap = np.log(safe_gap_ratio)
    
    # day_return: 日涨跌幅 (Log Return)
    # ln(C / PC) -> return NaN if C<=0 or PC<=0
    day_return_ratio = close / prev_close
    safe_return_ratio = np.where((close > 0) & (prev_close > 0), day_return_ratio, np.nan)
    day_return = np.log(safe_return_ratio)
    
    # true_range: 真实波幅 = max(H-L, |H-PC|, |L-PC|)
    # ATR 的单日版本，包含 gap 信息
    # true_range: 真实波幅 = max(H-L, |H-PC|, |L-PC|)
    # ATR 的单日版本，包含 gap 信息
    true_range = np.maximum(
        total_range,
        np.maximum(
            (high - prev_close).abs(),
            (low - prev_close).abs()
        )
    )
    
    # rel_true_range: 能量规模
    rel_true_range = true_range / safe_prev_close
    
    # movement_efficiency: 运动效率 (位移/路程)
    # 1.0 代表极度高效的单边行情；0.0 代表剧烈震荡但无实际位移
    safe_tr_val = np.where(true_range == 0, np.nan, true_range)
    movement_efficiency = (close - prev_close).abs() / safe_tr_val
    
    # open_in_body: 开盘是否在前日收盘价附近
    # |gap| < 0.01 (1% 以内的跳空算作"在实体内")
    # Al Brooks 定义: 开盘在前日 K 线的实体内部，表示"延续"而非"突破"
    open_in_body = np.abs(gap) < 0.01  # |gap| < 1%
    
    # --- L4: 跨日关系特征 (Cross-Day Relationship) ---
    
    # is_inside: 内包线 - 今日 Range 完全在前日 Range 内
    # 波动率收缩，准备突破
    is_inside = (high <= prev_high) & (low >= prev_low)
    
    # is_outside: 外包线 - 今日 Range 完全包含前日 Range
    # 震荡加剧，陷阱或反转
    # Brooks 定义: high >= prev_high AND low < prev_low, 或 high > prev_high AND low <= prev_low
    is_outside = ((high >= prev_high) & (low < prev_low)) | ((high > prev_high) & (low <= prev_low))
    
    # gap_type: 跳空类型
    # +1 = 向上突破 (开盘 > 前日最高)
    #  0 = 范围内开盘 (前日最低 <= 开盘 <= 前日最高)
    # -1 = 向下突破 (开盘 < 前日最低)
    gap_type = np.where(
        open_price > prev_high, 1,
        np.where(open_price < prev_low, -1, 0)
    )
    
    # overlap_pct: 与昨日重叠比例
    # 重叠区间 = [max(L, prev_L), min(H, prev_H)]
    overlap_high = np.minimum(high, prev_high)
    overlap_low = np.maximum(low, prev_low)
    overlap_length = np.maximum(0, overlap_high - overlap_low)  # 无重叠时为 0
    overlap_pct = overlap_length / safe_prev_range

    # body_gap: 实体缺口 (L4 Context)
    # Al Brooks: 强趋势的重要信号 (Gap Up/Down)
    # 计算公式: 当前实体底部 (min(O,C)) - 前日实体顶部 (max(PC, PO))
    # 正值 = 向上实体缺口 (Gap Up); 负值 = 重叠或向下缺口
    prev_body_top = np.maximum(prev_open, prev_close)
    curr_body_bottom = np.minimum(open_price, close)
    body_gap = curr_body_bottom - prev_body_top

    # --- L3b: 布尔分类器 (基于 L2 阈值) ---
    
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

    # 4. Strong Reversal Signals (Al Brooks) - L3
    # 强多头反转: 长下影线 (>1/3) + 高收盘 (>0.6) + 阳线实体
    is_strong_bull_reversal = (
        (lower_tail_pct > 0.33) & 
        (clv > 0.6) & 
        (bar_color == 1)
    )
    
    # 强空头反转: 长上影线 (>1/3) + 低收盘 (<-0.6) + 阴线实体
    is_strong_bear_reversal = (
        (upper_tail_pct > 0.33) & 
        (clv < -0.6) & 
        (bar_color == -1)
    )

    # 5. Trend Streak: 连续 Trend Bar 计数 (L4)
    # 逻辑: 只要 is_trend_bar 为 True 且方向一致，计数器 +1
    trend_dir = is_trend_bar.astype(int) * bar_color  # +1 (Bull Trend), -1 (Bear Trend), 0 (No Trend)
    
    # 使用 cumsum-groupby 技巧计算连续序列
    # 当 trend_dir 变化时，diff != 0，cumsum 增加，形成新的 group
    streak_group = (trend_dir != trend_dir.shift(1)).cumsum()
    # 在每个 group 内计数 (+1 因为从 1 开始)
    trend_streak_raw = df.groupby(streak_group)["close"].cumcount() + 1
    
    # 如果不是 Trend Bar，重置为 0 (Al Brooks: "Consecutive Trend Bars")
    trend_streak = np.where(is_trend_bar, trend_streak_raw, 0)

    # --- L4b: 2-Bar 关系特征 (2-Bar Relationship) ---
    
    # 6. Outside Bar 方向细分
    # is_outside_up: Outside Bar 且收盘 > 前日最高 (强力反转向上)
    is_outside_up = is_outside & (close > prev_high)
    # is_outside_down: Outside Bar 且收盘 < 前日最低 (强力反转向下)
    is_outside_down = is_outside & (close < prev_low)

    # 7. 吞没形态 (Engulfing Patterns)
    # is_bull_engulfing: 阳线实体完全覆盖前日阴线实体
    # 条件: 当前阳线 + 前日阴线 + 当前实体低 <= 前日实体低 + 当前实体高 >= 前日实体高
    prev_body_bottom = np.minimum(prev_open, prev_close)
    curr_body_top = np.maximum(open_price, close)
    is_bull_engulfing = (
        (bar_color == 1) &  # 当前是阳线
        (bar_color.shift(1) == -1) &  # 前日是阴线
        (curr_body_bottom <= prev_body_bottom) &  # 当前实体底 <= 前日实体底
        (curr_body_top >= prev_body_top)  # 当前实体顶 >= 前日实体顶
    )
    
    # is_bear_engulfing: 阴线实体完全覆盖前日阳线实体
    is_bear_engulfing = (
        (bar_color == -1) &  # 当前是阴线
        (bar_color.shift(1) == 1) &  # 前日是阳线
        (curr_body_bottom <= prev_body_bottom) &  # 当前实体底 <= 前日实体底
        (curr_body_top >= prev_body_top)  # 当前实体顶 >= 前日实体顶
    )

    # 8. Blended Candle (合并K线分析)
    # Al Brooks: "如果你把这两根K线合并起来看，它就是一个Pin Bar"
    blend_open = prev_open  # 合并K线的开盘 = 前日开盘
    blend_close = close  # 合并K线的收盘 = 当日收盘
    blend_high = np.maximum(high, prev_high)  # 合并K线的最高
    blend_low = np.minimum(low, prev_low)  # 合并K线的最低
    blend_range = blend_high - blend_low
    safe_blend_range = np.where(blend_range == 0, np.nan, blend_range)
    
    # blend_clv: 合并K线的 CLV (收盘位置)
    # 高 blend_clv + 反向趋势棒组合 = 隐藏的看涨信号
    blend_clv = (2 * blend_close - blend_high - blend_low) / safe_blend_range
    
    # blend_body_pct: 合并K线的实体比例
    blend_body_size = (blend_close - blend_open).abs()
    blend_body_pct = blend_body_size / safe_blend_range

    # 9. 突破失败 (Failed Breakout) - Brooks 体系核心陷阱识别
    # failed_breakout_high: 向上突破前日最高但收盘收回 (物理定义)
    # High > Prev High 且 Close < Prev High
    failed_breakout_high = (high > prev_high) & (close < prev_high)
    
    # failed_breakout_low: 向下突破前日最低但收盘收回 (物理定义)
    # Low < Prev Low 且 Close > Prev Low
    failed_breakout_low = (low < prev_low) & (close > prev_low)
    
    # 9b. 严格突破失败 (Strict Failed Breakout) - 强 Trap 信号
    # strict_failed_breakout_high: 突破前高但收阴 (Bull Trap)
    # 额外条件: bar_color == -1 (必须收阴)
    strict_failed_breakout_high = failed_breakout_high & (bar_color == -1)
    
    # strict_failed_breakout_low: 突破前低但收阳 (Bear Trap)
    # 额外条件: bar_color == 1 (必须收阳)
    strict_failed_breakout_low = failed_breakout_low & (bar_color == 1)

    # --- L4.5: EMA 关系特征 (EMA Gravity) ---
    
    # 10. 计算 EMA (如果未提供)
    if "ema" in df.columns:
        ema = df["ema"]
    else:
        ema = df["close"].ewm(span=ema_period, adjust=False).mean()
    
    # dist_to_ema: 乖离率 (Trend Strength)
    # 正值 = 在 EMA 上方 (看涨); 负值 = 在 EMA 下方 (看跌)
    safe_ema = np.where(ema == 0, np.nan, ema)
    dist_to_ema = (close - ema) / safe_ema
    
    # bar_pos_ema: K 线相对 EMA 位置
    # +1 = Low > EMA (完全在上方, 强趋势)
    # -1 = High < EMA (完全在下方, 强趋势)
    #  0 = 跨越 EMA (测试/震荡)
    bar_pos_ema = np.where(
        low > ema, 1,
        np.where(high < ema, -1, 0)
    )
    
    # ema_touch: 是否触及 EMA
    # High >= EMA >= Low (均线测试, "磁力"回归)
    ema_touch = (high >= ema) & (low <= ema)
    
    # Gap Bar (Al Brooks 核心概念) - 方向细分
    # gap_below_ema: K 线完全在 EMA 下方 (High < EMA)
    # 多头趋势中出现 = 衰竭信号 (Bulls losing control)
    gap_below_ema = high < ema
    
    # gap_above_ema: K 线完全在 EMA 上方 (Low > EMA)
    # 空头趋势中出现 = 衰竭信号 (Bears losing control)
    gap_above_ema = low > ema

    # 构建结果 DataFrame (按层级排序)
    result_dict = {
        # --- L1: 尺度特征 (Scale) ---
        "total_range": total_range,  # 总能量 (H - L)
        "body_size": body_size,      # 净动能 |C - O|
        "amplitude": amplitude,      # 振幅 (H - L) / O
        
        # --- L1.5: Preclose 相关特征 ---
        "gap": gap,
        "day_return": day_return,
        "true_range": true_range,
        "rel_true_range": rel_true_range,
        "movement_efficiency": movement_efficiency,
    }
    
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
        
        # --- L4: 跨日关系特征 (Cross-Day Relationship) ---
        "is_inside": is_inside,
        "is_outside": is_outside,
        "gap_type": gap_type,
        "overlap_pct": overlap_pct,
        "open_in_body": open_in_body,
        "body_gap": body_gap,
        "trend_streak": trend_streak,
        
        # --- L4.5: 高级上下文 (Advanced Context) ---
        "rel_range_to_avg": rel_range_to_avg,
        "is_climax_bar": is_climax_bar,
        "is_strong_bull_reversal": is_strong_bull_reversal,
        "is_strong_bear_reversal": is_strong_bear_reversal,
        
        # --- L4b: 2-Bar 关系特征 (2-Bar Relationship) ---
        "is_outside_up": is_outside_up,
        "is_outside_down": is_outside_down,
        "is_bull_engulfing": is_bull_engulfing,
        "is_bear_engulfing": is_bear_engulfing,
        "blend_open": blend_open,
        "blend_close": blend_close,
        "blend_high": blend_high,
        "blend_low": blend_low,
        "blend_clv": blend_clv,
        "blend_body_pct": blend_body_pct,
        "failed_breakout_high": failed_breakout_high,
        "failed_breakout_low": failed_breakout_low,
        "strict_failed_breakout_high": strict_failed_breakout_high,  # Bull Trap (收阴)
        "strict_failed_breakout_low": strict_failed_breakout_low,    # Bear Trap (收阳)
        
        # --- L4.5 EMA: EMA 关系特征 (EMA Gravity) ---
        "ema": ema,  # EMA 值本身，供下游使用
        "dist_to_ema": dist_to_ema,  # 乖离率
        "bar_pos_ema": bar_pos_ema,  # 相对位置 (+1/-1/0)
        "ema_touch": ema_touch,  # 是否触及 EMA
        "gap_below_ema": gap_below_ema,  # K 线完全在 EMA 下方
        "gap_above_ema": gap_above_ema,  # K 线完全在 EMA 上方
    })
    
    result = pd.DataFrame(result_dict, index=df.index)

    return result


def add_bar_features(
    df: pd.DataFrame,
    doji_threshold: float = DOJI_BODY_THRESHOLD,
    ema_period: int = 20,
    prefix: str = "",
) -> pd.DataFrame:
    """
    在原始 DataFrame 上添加 K 线特征列（原地修改）。

    这是 compute_bar_features 的便捷包装，直接将特征列添加到输入 DataFrame。

    Args:
        df: 包含 OHLC 数据的 DataFrame
        doji_threshold: 判断 Doji 的实体占比阈值
        ema_period: EMA 周期，默认 20
        prefix: 特征列名前缀，例如 "feat_" 会生成 "feat_bar_color" 等

    Returns:
        pd.DataFrame: 添加了特征列的原始 DataFrame

    Example:
        >>> df = add_bar_features(df, prefix="feat_")
        >>> print(df[["close", "feat_bar_color", "feat_body_pct"]].head())
    """
    features = compute_bar_features(df, doji_threshold, ema_period)
    for col in features.columns:
        df[f"{prefix}{col}"] = features[col]
    return df
