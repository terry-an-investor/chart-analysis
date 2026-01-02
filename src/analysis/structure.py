"""
src/analysis/structure.py
市场结构核心模块 (Phase 2) - Swing Points & Trend Structure

职责:
1. 识别摆动点 (Fractals/Swings): 基于 Al Brooks 定义 (N bar high/low)。
2. 消除未来函数: 使用 Shift 机制将"几何高点"平移到"确认时间"。
3. 维护结构状态: 识别 HH (Higher High), LH (Lower High) 等结构性特征。
4. 提供趋势方向: Always In Long / Short / Neutral 状态。

特征层级 (Feature Hierarchy):

    L5 - 结构层 (Structure Layer):
    - swing_high_confirmed: bool (确认时刻为 True)
    - swing_low_confirmed: bool
    - swing_high_price: float (确认时记录的历史高点价格)
    - swing_low_price: float (确认时记录的历史低点价格)
    - swing_type: str (HH, LH, HL, LL, DT, DB)
    - major_high: float (当前生效的结构性阻力位)
    - major_low: float (当前生效的结构性支撑位)
    - market_trend: int (+1=Bull, -1=Bear, 0=Neutral)

Author: Al Brooks Quant Architect
"""

import pandas as pd
import numpy as np
from typing import Tuple, Optional

# ============================================================
# 常量定义
# ============================================================

# Al Brooks 标准: 左右各 N 根 K 线确认摆动点
DEFAULT_SWING_WINDOW = 5

# 价格容差: 判断 Double Top/Bottom 时使用 (0.1% 以内视为相同价位)
PRICE_TOLERANCE_PCT = 0.001


def detect_swings(
    df: pd.DataFrame, 
    window: int = DEFAULT_SWING_WINDOW,
    high_col: str = 'high',
    low_col: str = 'low'
) -> pd.DataFrame:
    """
    识别 Swing Highs 和 Swing Lows (Al Brooks Fractals)。
    
    核心逻辑:
    1. 物理层 (God Mode): 使用 rolling(center=True) 寻找几何上的最高/最低点。
    2. 信号层 (Real Mode): 将信号向后平移 'window' 个周期，模拟实盘中的滞后确认。
    
    Al Brooks 定义:
    - Swing High: 某根 K 线的 High 是前后各 N 根 K 线中的最高点
    - Swing Low: 某根 K 线的 Low 是前后各 N 根 K 线中的最低点
    
    无未来函数保证:
    - 在 Index=T 时刻的摆动点，需要等到 Index=T+N 时刻才能确认
    - 因为我们需要看到右侧的 N 根 K 线才能确定 T 是不是真正的极值点
    
    Args:
        df: 包含 OHLC 数据的 DataFrame
        window: 确认周期 (默认 5，即需要左右各 5 根 K 线来确认)
        high_col: High 列名
        low_col: Low 列名
        
    Returns:
        pd.DataFrame: 追加了以下列:
        - swing_high_confirmed: bool (在确认时刻 index=t+N 为 True)
        - swing_low_confirmed: bool
        - swing_high_price: float (历史高点价格，仅在 confirmed=True 时有效)
        - swing_low_price: float (历史低点价格，仅在 confirmed=True 时有效)
        
    Example:
        >>> df = pd.DataFrame({'high': [1,2,5,3,1,2,1], 'low': [0,1,4,2,0,1,0]})
        >>> result = detect_swings(df, window=2)
        >>> # Index=2 是几何高点 (high=5)，但要到 Index=4 才确认
        >>> result.loc[4, 'swing_high_confirmed']  # True
        >>> result.loc[4, 'swing_high_price']      # 5.0
    """
    # 避免修改原始数据
    df = df.copy()
    
    highs = df[high_col]
    lows = df[low_col]
    
    # -------------------------------------------------------------------------
    # 1. 物理层检测 (Physical Detection) - 包含未来数据
    # -------------------------------------------------------------------------
    # 扫描窗口 = 左 N + 中 1 + 右 N = 2N + 1
    scan_window = 2 * window + 1
    
    # 使用 center=True 偷看未来，找出几何结构
    # rolling_max[t] 实际上用到了 [t-N, t+N] 范围内的数据
    # 使用 min_periods=1 来处理数据中的 NaN 值 (如休市日缺失数据)
    rolling_max = highs.rolling(window=scan_window, center=True, min_periods=1).max()
    rolling_min = lows.rolling(window=scan_window, center=True, min_periods=1).min()
    
    # 标记几何高低点
    # 注意: 如果相邻多根 K 线价格相同，rolling 会让它们都等于 max/min
    # 我们需要只取第一个作为有效摆动点
    # 同时需要过滤掉本身是 NaN 的数据点
    is_high_raw = (highs == rolling_max) & highs.notna()
    is_low_raw = (lows == rolling_min) & lows.notna()
    
    # 去重: 只保留连续相同高点中的第一个
    # 通过检查前一根是否也是高点来实现: 如果前一根也是高点，则当前不算
    # 使用 numpy 操作避免 pandas FutureWarning
    is_high_arr = is_high_raw.to_numpy()
    is_low_arr = is_low_raw.to_numpy()
    
    prev_high_arr = np.roll(is_high_arr, 1)
    prev_high_arr[0] = False  # 第一个元素没有前一个
    prev_low_arr = np.roll(is_low_arr, 1)
    prev_low_arr[0] = False
    
    is_high_dedup = is_high_arr & ~prev_high_arr
    is_low_dedup = is_low_arr & ~prev_low_arr
    
    # -------------------------------------------------------------------------
    # 2. 信号层确认 (Signal Confirmation) - 消除未来函数
    # -------------------------------------------------------------------------
    # 关键步骤: 将 Index=T 的信号平移到 Index=T+window
    # 这意味着我们在 T+window 时刻才"确认"之前那个是高点
    shifted_high_arr = np.roll(is_high_dedup, window)
    shifted_high_arr[:window] = False  # 前 window 个元素没有确认
    shifted_low_arr = np.roll(is_low_dedup, window)
    shifted_low_arr[:window] = False
    
    df['swing_high_confirmed'] = shifted_high_arr
    df['swing_low_confirmed'] = shifted_low_arr
    
    # -------------------------------------------------------------------------
    # 3. 价值保留 (Value Retention)
    # -------------------------------------------------------------------------
    # 在 Index=T+window 时，我们需要知道 Index=T 的价格是多少
    # 使用 shift 将价格带到未来确认时刻
    df['swing_high_price'] = highs.shift(window)
    df['swing_low_price'] = lows.shift(window)
    
    # 数据清洗: 只有在 confirmed=True 的行，price 才有效
    # 其他行设为 NaN，方便后续使用 dropna() 快速提取关键点
    df.loc[~df['swing_high_confirmed'], 'swing_high_price'] = np.nan
    df.loc[~df['swing_low_confirmed'], 'swing_low_price'] = np.nan
    
    return df


def classify_swings(
    df: pd.DataFrame,
    tolerance_pct: float = PRICE_TOLERANCE_PCT
) -> pd.DataFrame:
    """
    结构状态机: 标记 HH, LH, HL, LL 并维护 Major Swing Points。
    
    逻辑:
    1. 提取所有已确认的 Swing Points。
    2. 按时间顺序遍历，比较当前 Swing 与上一个同向 Swing 的价格关系。
    3. 更新当前生效的 Major High / Major Low (作为结构性阻力/支撑)。
    
    Swing Type 定义:
    - HH (Higher High): 当前高点 > 前一个高点 => 趋势延续 (牛市)
    - LH (Lower High): 当前高点 < 前一个高点 => 趋势减弱 (牛转熊信号)
    - HL (Higher Low): 当前低点 > 前一个低点 => 趋势延续 (牛市)
    - LL (Lower Low): 当前低点 < 前一个低点 => 趋势减弱 (熊市)
    - DT (Double Top): 当前高点 ≈ 前一个高点 (容差范围内)
    - DB (Double Bottom): 当前低点 ≈ 前一个低点 (容差范围内)
    
    Args:
        df: 经过 detect_swings 处理的 DataFrame
        tolerance_pct: 判断 Double Top/Bottom 的价格容差 (默认 0.1%)
        
    Returns:
        pd.DataFrame: 追加了以下列:
        - swing_type: str (HH, LH, HL, LL, DT, DB)
        - major_high: float (当前生效的结构性阻力位，前向填充)
        - major_low: float (当前生效的结构性支撑位，前向填充)
    """
    # 确保前置依赖
    if 'swing_high_confirmed' not in df.columns:
        df = detect_swings(df)
    
    df = df.copy()
    
    # 初始化输出列 (使用 object 类型避免类型警告)
    df['swing_type'] = pd.Series([np.nan] * len(df), dtype=object)
    df['major_high'] = np.nan
    df['major_low'] = np.nan
    
    # 状态变量 (State Variables)
    # 使用极端初始值确保第一个摆动点能正确分类
    last_h_price = -np.inf
    last_l_price = np.inf
    
    # 当前生效的 Major Levels (用于填充)
    current_major_high = np.nan
    current_major_low = np.nan
    
    # -------------------------------------------------------------------------
    # 稀疏遍历 (Sparse Traversal) - 只处理关键事件
    # -------------------------------------------------------------------------
    # 提取所有事件发生的索引
    high_indices = df.index[df['swing_high_confirmed']].tolist()
    low_indices = df.index[df['swing_low_confirmed']].tolist()
    
    # 合并事件流并按时间排序: [(index, 'high'), (index, 'low'), ...]
    # 这样我们就能像回放磁带一样重演历史
    events = sorted(
        [(i, 'high') for i in high_indices] + 
        [(i, 'low') for i in low_indices], 
        key=lambda x: x[0]
    )
    
    # 运行状态机
    for idx, event_type in events:
        if event_type == 'high':
            curr_price = df.at[idx, 'swing_high_price']
            
            # 容差计算: 判断是否为 Double Top
            if last_h_price > 0:  # 排除初始值
                price_diff_pct = abs(curr_price - last_h_price) / last_h_price
                is_double = price_diff_pct <= tolerance_pct
            else:
                is_double = False
            
            # 状态判定
            if is_double:
                label = 'DT'
            elif curr_price > last_h_price:
                label = 'HH'
            else:
                label = 'LH'
            
            # 更新状态
            last_h_price = curr_price
            df.at[idx, 'swing_type'] = label
            
            # 更新当前生效的 Major High
            current_major_high = curr_price
            df.at[idx, 'major_high'] = current_major_high
            df.at[idx, 'major_low'] = current_major_low
            
        elif event_type == 'low':
            curr_price = df.at[idx, 'swing_low_price']
            
            # 容差计算: 判断是否为 Double Bottom
            if last_l_price < np.inf:  # 排除初始值
                price_diff_pct = abs(curr_price - last_l_price) / last_l_price
                is_double = price_diff_pct <= tolerance_pct
            else:
                is_double = False
            
            # 状态判定
            if is_double:
                label = 'DB'
            elif curr_price < last_l_price:
                label = 'LL'
            else:
                label = 'HL'
            
            # 更新状态
            last_l_price = curr_price
            df.at[idx, 'swing_type'] = label
            
            # 更新当前生效的 Major Low
            current_major_low = curr_price
            df.at[idx, 'major_low'] = current_major_low
            df.at[idx, 'major_high'] = current_major_high

    # -------------------------------------------------------------------------
    # 状态填充 (State Propagation)
    # -------------------------------------------------------------------------
    # 将稀疏的 major_high/low 前向填充到每一根 K 线
    # 这样每一根 K 线都知道自己头顶的压力位和脚下的支撑位在哪里
    df['major_high'] = df['major_high'].ffill()
    df['major_low'] = df['major_low'].ffill()
    
    return df


def classify_swings_v2(
    df: pd.DataFrame,
    tolerance_pct: float = PRICE_TOLERANCE_PCT
) -> pd.DataFrame:
    """
    [V2] 突破确认逻辑 (Breakout Confirmation) 版本的结构分类状态机。
    
    与 V1 的核心差异:
    --------------------------------------
    V1: 每次出现 Swing Point 就更新对应的 Major Level。
    V2: Major Level 只有在价格突破后才确认更新。
    
    Al Brooks 核心原则:
    - Major Low 的上移，必须由"价格创出新高 (New High)"来确认。
    - Major High 的下移，必须由"价格创出新低 (New Low)"来确认。
    
    这意味着: 在没有创新高之前，中间所有的 Higher Lows 都只是 Minor Swings (次级折返)，
    不应改变结构性的支撑位。
    
    输出列 (同 V1):
    - swing_type: str (HH, LH, HL, LL, DT, DB)
    - major_high: float (当前生效的结构性阻力位)
    - major_low: float (当前生效的结构性支撑位)
    - trend_bias: int (当前趋势倾向: 1=Bull, -1=Bear, 0=Neutral)
    """
    if 'swing_high_confirmed' not in df.columns:
        df = detect_swings(df)
    
    df = df.copy()
    
    # 初始化输出列
    df['swing_type'] = pd.Series([np.nan] * len(df), dtype=object)
    df['major_high'] = np.nan
    df['major_low'] = np.nan
    df['trend_bias'] = 0
    
    # 状态变量 - 用于 HH/HL/LH/LL 分类
    last_h_price = -np.inf
    last_l_price = np.inf
    
    # "候选" Swing Points (Candidates) - 等待确认
    candidate_major_low = np.nan
    candidate_major_high = np.nan
    
    # 当前生效的结构位 (Active Structure Levels)
    first_valid_high = df['high'].dropna().iloc[0] if df['high'].notna().any() else np.nan
    first_valid_low = df['low'].dropna().iloc[0] if df['low'].notna().any() else np.nan
    active_major_high = first_valid_high
    active_major_low = first_valid_low
    
    curr_bias = 0  # 0=Neutral, 1=Bull, -1=Bear
    
    # 提取事件流
    high_indices = df.index[df['swing_high_confirmed']].tolist()
    low_indices = df.index[df['swing_low_confirmed']].tolist()
    events = sorted(
        [(i, 'high') for i in high_indices] + 
        [(i, 'low') for i in low_indices], 
        key=lambda x: x[0]
    )
    
    for idx, event_type in events:
        if event_type == 'high':
            price = df.at[idx, 'swing_high_price']
            
            # 1. 标记 Swing Type (几何属性)
            if last_h_price > 0:
                price_diff_pct = abs(price - last_h_price) / last_h_price
                if price_diff_pct <= tolerance_pct:
                    label = 'DT'
                elif price > last_h_price:
                    label = 'HH'
                else:
                    label = 'LH'
            else:
                label = 'HH'
            
            last_h_price = price
            df.at[idx, 'swing_type'] = label
            
            # 更新候选阻力位
            candidate_major_high = price
            
            # --- Bull Breakout Check ---
            if curr_bias == 1:
                if price > active_major_high:
                    if pd.notna(candidate_major_low) and candidate_major_low > active_major_low:
                        active_major_low = candidate_major_low
                    active_major_high = price
            elif curr_bias == -1:
                if price > active_major_high:
                    curr_bias = 1
                    if pd.notna(candidate_major_low):
                        active_major_low = candidate_major_low
                    active_major_high = price
            else:
                active_major_high = price
                if label == 'HH':
                    curr_bias = 1

        elif event_type == 'low':
            price = df.at[idx, 'swing_low_price']
            
            # 1. 标记 Swing Type
            if last_l_price < np.inf:
                price_diff_pct = abs(price - last_l_price) / last_l_price
                if price_diff_pct <= tolerance_pct:
                    label = 'DB'
                elif price < last_l_price:
                    label = 'LL'
                else:
                    label = 'HL'
            else:
                label = 'LL'
            
            last_l_price = price
            df.at[idx, 'swing_type'] = label
            
            # 更新候选支撑位
            candidate_major_low = price
            
            # --- Bear Breakout Check ---
            if curr_bias == -1:
                if price < active_major_low:
                    if pd.notna(candidate_major_high) and candidate_major_high < active_major_high:
                        active_major_high = candidate_major_high
                    active_major_low = price
            elif curr_bias == 1:
                if price < active_major_low:
                    curr_bias = -1
                    if pd.notna(candidate_major_high):
                        active_major_high = candidate_major_high
                    active_major_low = price
            else:
                active_major_low = price
                if label == 'LL':
                    curr_bias = -1
                
        # 记录状态
        df.at[idx, 'major_high'] = active_major_high
        df.at[idx, 'major_low'] = active_major_low
        df.at[idx, 'trend_bias'] = curr_bias

    # 状态填充
    df['major_high'] = df['major_high'].ffill()
    df['major_low'] = df['major_low'].ffill()
    df['trend_bias'] = df['trend_bias'].ffill().fillna(0).astype(int)
    
    return df


def compute_trend_state(
    df: pd.DataFrame,
    lookback: int = 2
) -> pd.DataFrame:
    """
    计算趋势状态: Always In Long / Short / Neutral。
    
    趋势定义 (Al Brooks):
    - Bull Trend: 最近结构是 HH + HL (价格创新高且低点抬升)
    - Bear Trend: 最近结构是 LL + LH (价格创新低且高点降低)
    - Neutral: 结构混乱或处于转折期
    
    Args:
        df: 经过 classify_swings 处理的 DataFrame
        lookback: 考察最近多少个摆动点来判断趋势 (默认 2)
        
    Returns:
        pd.DataFrame: 追加了以下列:
        - market_trend: int (+1=Bull, -1=Bear, 0=Neutral)
        - last_swing_types: str (最近的摆动点类型序列，用于调试)
    """
    # 确保前置依赖
    if 'swing_type' not in df.columns:
        df = classify_swings(df)
    
    df = df.copy()
    
    # 初始化
    df['market_trend'] = 0
    df['last_swing_types'] = ''
    
    # 提取所有有效的摆动点
    swing_indices = df.index[df['swing_type'].notna()].tolist()
    
    if len(swing_indices) < lookback:
        return df  # 数据不足，返回中性
    
    # 状态变量
    current_trend = 0
    last_types = []
    
    # 遍历所有时间点，维护当前趋势状态
    swing_ptr = 0  # 指向下一个待处理的摆动点
    
    for i in df.index:
        # 更新已确认的摆动点
        while swing_ptr < len(swing_indices) and swing_indices[swing_ptr] <= i:
            swing_type = df.at[swing_indices[swing_ptr], 'swing_type']
            last_types.append(swing_type)
            # 只保留最近 lookback*2 个类型 (H 和 L 分开计数)
            if len(last_types) > lookback * 2:
                last_types.pop(0)
            swing_ptr += 1
        
        # 趋势判定逻辑
        if len(last_types) >= lookback:
            # 提取最近的 High 类型和 Low 类型
            recent_highs = [t for t in last_types if t in ('HH', 'LH', 'DT')]
            recent_lows = [t for t in last_types if t in ('HL', 'LL', 'DB')]
            
            # Bull Trend: 最近的 High 是 HH，且最近的 Low 是 HL
            if recent_highs and recent_lows:
                last_high = recent_highs[-1]
                last_low = recent_lows[-1]
                
                if last_high == 'HH' and last_low == 'HL':
                    current_trend = 1   # Bull
                elif last_high == 'LH' and last_low == 'LL':
                    current_trend = -1  # Bear
                else:
                    # 混合信号: HH+LL 或 LH+HL => 可能是转折期
                    current_trend = 0   # Neutral
        
        df.at[i, 'market_trend'] = current_trend
        df.at[i, 'last_swing_types'] = ','.join(last_types[-4:])  # 保留最近4个用于调试
    
    return df


def compute_market_structure(
    df: pd.DataFrame,
    swing_window: int = DEFAULT_SWING_WINDOW,
    trend_lookback: int = 2
) -> pd.DataFrame:
    """
    一站式结构计算: 完整的 Phase 2 流水线。
    
    依次执行:
    1. detect_swings() - 识别摆动点
    2. classify_swings() - 分类并标记 Major Levels
    3. compute_trend_state() - 计算趋势方向
    
    Args:
        df: 包含 OHLC 数据的 DataFrame
        swing_window: 摆动点确认周期
        trend_lookback: 趋势判定回看周期
        
    Returns:
        pd.DataFrame: 包含所有结构特征的完整 DataFrame
    """
    result = detect_swings(df, window=swing_window)
    result = classify_swings(result)
    result = compute_trend_state(result, lookback=trend_lookback)
    
    return result


def add_structure_features(
    df: pd.DataFrame,
    swing_window: int = DEFAULT_SWING_WINDOW,
    trend_lookback: int = 2,
    prefix: str = 'struct_'
) -> pd.DataFrame:
    """
    在原始 DataFrame 上添加结构特征列（原地修改）。
    
    这是 compute_market_structure 的便捷包装，直接将特征列添加到输入 DataFrame。
    
    Args:
        df: 包含 OHLC 数据的 DataFrame
        swing_window: 摆动点确认周期
        trend_lookback: 趋势判定回看周期
        prefix: 特征列前缀
        
    Returns:
        pd.DataFrame: 添加了结构特征列的原始 DataFrame
    """
    features = compute_market_structure(
        df, 
        swing_window=swing_window, 
        trend_lookback=trend_lookback
    )
    
    # 需要添加的特征列
    feature_cols = [
        'swing_high_confirmed', 'swing_low_confirmed',
        'swing_high_price', 'swing_low_price',
        'swing_type', 'major_high', 'major_low',
        'market_trend', 'last_swing_types'
    ]
    
    for col in feature_cols:
        if col in features.columns:
            df[f'{prefix}{col}'] = features[col].values
    
    return df


# ============================================================
# Climax Detector (Phase 2.3)
# ============================================================

def detect_climax_reversal(
    df: pd.DataFrame,
    atr_multiplier: float = 2.0,
    lookback: int = 5
) -> pd.DataFrame:
    """
    识别 V 型反转 (Climax Reversal): 高潮顶/底 + 强力反转棒。
    
    这是对 Window=5 Fractals 的补充，用于捕捉那些因为形态太尖锐
    而未被常规 Swing 检测到的反转点。
    
    Al Brooks 定义:
    - Climax = 巨型趋势棒 (Body > 2*ATR) 或 连续 N 根同向趋势棒
    - Reversal = 紧接着的强力反向棒 (吞没/大实体反向)
    - V-Top: Bull Climax + Bear Reversal → 标记即时阻力位
    - V-Bottom: Bear Climax + Bull Reversal → 标记即时支撑位
    
    Args:
        df: 包含 OHLC 数据的 DataFrame
        atr_multiplier: 判断 Climax Bar 的 ATR 倍数阈值
        lookback: 计算 ATR 的回看周期
    
    Returns:
        pd.DataFrame: 追加以下列:
        - is_climax_top: bool (V型顶确认)
        - is_climax_bottom: bool (V型底确认)
        - climax_top_price: float (顶部价格)
        - climax_bottom_price: float (底部价格)
    """
    df = df.copy()
    
    # 计算 ATR (Average True Range)
    high = df['high']
    low = df['low']
    close = df['close']
    prev_close = close.shift(1)
    
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)
    atr = tr.rolling(window=lookback, min_periods=1).mean()
    
    # 计算 K 线属性
    body_size = (close - df['open']).abs()
    is_bull = close > df['open']
    is_bear = close < df['open']
    
    # 识别 Climax Bar (巨型趋势棒)
    is_climax_bar = body_size > (atr * atr_multiplier)
    is_bull_climax = is_climax_bar & is_bull
    is_bear_climax = is_climax_bar & is_bear
    
    # 识别 Reversal Bar (强力反向棒)
    # 简化版: 大阴线跟着大阳线 / 大阳线跟着大阴线
    prev_is_bull = is_bull.astype(float).shift(1).fillna(0.0).astype(bool)
    prev_is_bear = is_bear.astype(float).shift(1).fillna(0.0).astype(bool)
    prev_body = body_size.shift(1).fillna(0)
    
    # Bear Reversal: 前一根是大阳线，当前是大阴线且吞没
    is_bear_reversal = (
        prev_is_bull & 
        is_bear & 
        (body_size > prev_body * 0.5) &  # 至少覆盖前一根一半
        (close < df['open'].shift(1))    # 收盘低于前一根开盘
    )
    
    # Bull Reversal: 前一根是大阴线，当前是大阳线且吞没
    is_bull_reversal = (
        prev_is_bear & 
        is_bull & 
        (body_size > prev_body * 0.5) &
        (close > df['open'].shift(1))
    )
    
    # V-Top: 前一根是 Bull Climax，当前是 Bear Reversal
    # 或者：前两根中有 Bull Climax，当前是 Bear Reversal
    prev_bull_climax = is_bull_climax.astype(float).shift(1).fillna(0.0).astype(bool)
    is_v_top = prev_bull_climax & is_bear_reversal
    
    # V-Bottom: 前一根是 Bear Climax，当前是 Bull Reversal
    prev_bear_climax = is_bear_climax.astype(float).shift(1).fillna(0.0).astype(bool)
    is_v_bottom = prev_bear_climax & is_bull_reversal
    
    # 记录价格
    df['is_climax_top'] = is_v_top
    df['is_climax_bottom'] = is_v_bottom
    
    # 顶部价格 = 前一根 (Climax Bar) 的 High
    df['climax_top_price'] = np.where(
        is_v_top,
        high.shift(1),
        np.nan
    )
    
    # 底部价格 = 前一根 (Climax Bar) 的 Low
    df['climax_bottom_price'] = np.where(
        is_v_bottom,
        low.shift(1),
        np.nan
    )
    
    return df


def detect_consecutive_reversal(
    df: pd.DataFrame,
    consecutive_count: int = 3
) -> pd.DataFrame:
    """
    识别渐进式反转 (Consecutive Bars Reversal)。
    
    当出现连续 N 根同向 K 线后，回溯标记该段行情的起点作为反转点。
    这是对 Climax Reversal 的补充，用于捕捉"温水煮青蛙"式的渐进反转。
    
    Al Brooks 逻辑:
    - 连续 3+ 根阴线 = Bear Breakout 确认 → 回溯标记最后的 Swing High
    - 连续 3+ 根阳线 = Bull Breakout 确认 → 回溯标记最后的 Swing Low
    
    Args:
        df: 包含 OHLC 数据的 DataFrame
        consecutive_count: 连续同向 K 线的阈值 (默认 3)
    
    Returns:
        pd.DataFrame: 追加以下列:
        - consecutive_bear_start: bool (连续阴线起点)
        - consecutive_bull_start: bool (连续阳线起点)
        - consecutive_top_price: float (渐进顶部价格)
        - consecutive_bottom_price: float (渐进底部价格)
    """
    df = df.copy()
    
    close = df['close']
    open_price = df['open']
    high = df['high']
    low = df['low']
    
    is_bull = close > open_price
    is_bear = close < open_price
    
    # 计算连续阴线/阳线计数
    # 使用 groupby 技巧：当方向变化时创建新组
    bear_groups = (~is_bear).cumsum()
    bull_groups = (~is_bull).cumsum()
    
    # 计算每组内的累计计数
    df['bear_streak'] = is_bear.groupby(bear_groups).cumsum()
    df['bull_streak'] = is_bull.groupby(bull_groups).cumsum()
    
    # 识别连续阴线达到阈值的时刻 (确认点)
    is_bear_confirmed = df['bear_streak'] == consecutive_count
    is_bull_confirmed = df['bull_streak'] == consecutive_count
    
    # 回溯找到连续阴线开始前的最后一根阳线高点
    # 逻辑：从确认点往前数 consecutive_count 根
    df['consecutive_bear_start'] = False
    df['consecutive_bull_start'] = False
    df['consecutive_top_price'] = np.nan
    df['consecutive_bottom_price'] = np.nan
    
    n = len(df)
    
    # 处理连续阴线确认 → 标记渐进顶部
    for i in df.index[is_bear_confirmed]:
        pos = df.index.get_loc(i)
        # 往前找 consecutive_count 根
        start_pos = pos - consecutive_count
        if start_pos >= 0:
            # 在开始位置之前找最近的高点
            # 简化：直接用连续阴线开始前那根的 High
            prev_idx = df.index[start_pos]
            df.at[i, 'consecutive_bear_start'] = True
            df.at[i, 'consecutive_top_price'] = high.iloc[start_pos]
    
    # 处理连续阳线确认 → 标记渐进底部
    for i in df.index[is_bull_confirmed]:
        pos = df.index.get_loc(i)
        start_pos = pos - consecutive_count
        if start_pos >= 0:
            df.at[i, 'consecutive_bull_start'] = True
            df.at[i, 'consecutive_bottom_price'] = low.iloc[start_pos]
    
    # 清理临时列
    df.drop(['bear_streak', 'bull_streak'], axis=1, inplace=True)
    
    return df


def merge_structure_with_events(
    df_structure: pd.DataFrame,
    df_events_climax: Optional[pd.DataFrame] = None,
    df_events_consecutive: Optional[pd.DataFrame] = None
) -> pd.DataFrame:
    """
    [Phase 2.4] 融合层 (Fusion Layer): 将 Climax/Reversal 事件融入市场结构
    
    职责:
    当检测到 V-Top 或 连续反转 等强力信号时，
    强制更新 Major High/Low，覆盖常规 V2 逻辑。
    
    解决问题:
    "信号已出但结构线滞后" - 让结构线对 Price Action 做出即时反应。
    
    逻辑:
    1. 基础: 使用 classify_swings_v2 计算的 major_high/low。
    2. 覆盖: 
        - V-Top / Consecutive Bear Top -> 强制将 major_high 压低。
        - V-Bottom / Consecutive Bull Bottom -> 强制将 major_low 拉高。
    3. 广播: 将新的结构位 forward fill 到未来，直到被新的结构点更新。
    
    Args:
        df_structure: 包含 major_high/low 的 V2 结构数据
        df_events_climax:包含 is_climax_top 等列的数据 (可选)
        df_events_consecutive: 包含 consecutive_bear_start 等列的数据 (可选)
        
    Returns:
        pd.DataFrame: 包含 adjusted_major_high, adjusted_major_low 的数据
    """
    df = df_structure.copy()
    
    # 1. 初始 adjusted 列为原始结构
    df['adjusted_major_high'] = df['major_high']
    df['adjusted_major_low'] = df['major_low']
    
    # 2. 合并事件数据
    # 为了处理方便，我们将关键事件映射到统一的 "override_high" 和 "override_low" 列
    df['override_high_price'] = np.nan
    df['override_low_price'] = np.nan
    
    # Climax Reversal 事件
    if df_events_climax is not None:
        if 'is_climax_top' in df_events_climax.columns:
            mask = df_events_climax['is_climax_top'].fillna(False)
            df.loc[mask, 'override_high_price'] = df_events_climax.loc[mask, 'climax_top_price']
            
        if 'is_climax_bottom' in df_events_climax.columns:
            mask = df_events_climax['is_climax_bottom'].fillna(False)
            df.loc[mask, 'override_low_price'] = df_events_climax.loc[mask, 'climax_bottom_price']

    # Consecutive Reversal 事件 (优先级更高，或者取更紧的那个)
    if df_events_consecutive is not None:
        if 'consecutive_bear_start' in df_events_consecutive.columns:
            mask = df_events_consecutive['consecutive_bear_start'].fillna(False)
            # 如果已有 override，取更低(更紧)的；如果没有，直接填入
            current_vals = df.loc[mask, 'override_high_price']
            new_vals = df_events_consecutive.loc[mask, 'consecutive_top_price']
            df.loc[mask, 'override_high_price'] = np.where(
                current_vals.isna(), 
                new_vals, 
                np.minimum(current_vals, new_vals)
            )
            
        if 'consecutive_bull_start' in df_events_consecutive.columns:
            mask = df_events_consecutive['consecutive_bull_start'].fillna(False)
            current_vals = df.loc[mask, 'override_low_price']
            new_vals = df_events_consecutive.loc[mask, 'consecutive_bottom_price']
            df.loc[mask, 'override_low_price'] = np.where(
                current_vals.isna(),
                new_vals,
                np.maximum(current_vals, new_vals)
            )
    
    # 3. 核心覆盖逻辑 (Sequential Processing Reqd for correct propagation)
    # 因为主要的变化是稀疏的，且 V2 结构也是分段的，我们可以迭代更新。
    # 为了保持向量化的高效，我们采用 "Event Mask + GroupBy FFill" 的策略。
    
    # 策略:
    # 新的 adjusted_major_high 应该是: min(original_major_high, latest_override_high)
    # 但 "latest_override_high" 只有在它比 original 更低时才生效，且要持续生效直到 original 自己降下来。
    
    # 简化实现 (V1.0): 
    # 只要出现了 override event，我们就在那个点打上新值。
    # 然后我们需要把这个新值向后传播，但是不能覆盖掉 "本来就已经更低" 的 major_high。
    
    # 让我们用迭代法处理，虽然慢一点点，但最准确。
    # 提取所有事件点和结构变化点
    
    # 优化: 仅在有 override 的行进行处理
    override_high_indices = df.index[df['override_high_price'].notna()]
    override_low_indices = df.index[df['override_low_price'].notna()]
    
    # 如果没有事件，直接返回
    if len(override_high_indices) == 0 and len(override_low_indices) == 0:
        return df
        
    # --- 处理 High ---
    # 我们不仅要修改当前点，还要影响后续
    # 这实际上是一个状态机：
    # State = min(V2_Level, Last_Override_Level)
    # 但是 V2_Level 也是动态变化的。
    
    # 简单做法: 
    # adjusted = min(major_high, ffill(override_high)) 
    # 但这有个问题：如果 major_high 后来主要下降了，ffill 的 override 可能会阻碍它？
    # 不会，因为是 min()。
    # 问题是：如果 major_high 后来上升了（Bull Trend 恢复），ffill 的 override 是否应该失效？
    # 是的！当 prices 创新高时，旧的 override high 就失效了。
    
    # 鉴于复杂性，V1.0 采用局部修补：
    # 仅修改 override 点及其后 N 天，或者直到 major_high 发生变化。
    # 这里的可视化目的是 "让用户看到线掉下来了"。
    
    # 最稳健的做法：重新生成一条序列
    # adjusted[t] = min(major_high[t], last_valid_override)
    # last_valid_override 在 price > it 时失效
    
    curr_override_high = np.inf
    curr_override_low = -np.inf
    
    # 转换为 numpy 数组加速
    major_high_vals = df['major_high'].values
    major_low_vals = df['major_low'].values
    high_prices = df['high'].values
    low_prices = df['low'].values
    override_high_vals = df['override_high_price'].values
    override_low_vals = df['override_low_price'].values
    
    adj_high_vals = np.full(len(df), np.nan)
    adj_low_vals = np.full(len(df), np.nan)
    
    # --- State Machine: Broken-Wait-Update ---
    # 原则: 
    # 1. 如果 Active Level 被突破，它失效并消失 (NaN)，而不是跳回旧的 V2。
    # 2. 只有当新的 V2 结构形成(数值变化) 或 新的 Override 信号出现时，Active Level 才会重新建立。
    
    curr_high = np.inf
    last_v2_high = np.nan
    
    curr_low = -np.inf
    last_v2_low = np.nan
    
    for i in range(len(df)):
        # --- Handle High (Resistance) ---
        v2_h = major_high_vals[i]
        ov_h = override_high_vals[i]
        
        # 1. Check Break (Stop Run)
        if high_prices[i] > curr_high:
            curr_high = np.inf # Broken -> Disappear
            
        # 2. Check V2 Update (New Structure)
        # 如果 V2 数值发生了变化 (且不是变回 NaN)，说明形成了新结构，重置 Active
        # 注意的处理 NaN 的相等性比较
        v2_changed = False
        if np.isnan(v2_h) and np.isnan(last_v2_high):
            v2_changed = False
        elif np.isnan(v2_h) or np.isnan(last_v2_high):
            v2_changed = True
        else:
            v2_changed = (v2_h != last_v2_high)
            
        if v2_changed:
            if not np.isnan(v2_h):
                # 新结构出现，重置/更新 Active (取较紧者)
                curr_high = v2_h
            last_v2_high = v2_h
            
        # 3. Check Override (Tighten)
        if not np.isnan(ov_h):
            # Override 总是让止损更紧 (更低)
            # 如果当前是 inf (已消失)，Override 可以重新激活它
            if curr_high == np.inf or ov_h < curr_high:
                curr_high = ov_h
                
        # 4. Assign
        if not np.isinf(curr_high):
            adj_high_vals[i] = curr_high
            
            
        # --- Handle Low (Support) ---
        v2_l = major_low_vals[i]
        ov_l = override_low_vals[i]
        
        # 1. Check Break
        if low_prices[i] < curr_low:
            curr_low = -np.inf # Broken -> Disappear
            
        # 2. Check V2 Update
        v2_l_changed = False
        if np.isnan(v2_l) and np.isnan(last_v2_low):
            v2_l_changed = False
        elif np.isnan(v2_l) or np.isnan(last_v2_low):
            v2_l_changed = True
        else:
            v2_l_changed = (v2_l != last_v2_low)
            
        if v2_l_changed:
            if not np.isnan(v2_l):
                curr_low = v2_l
            last_v2_low = v2_l
            
        # 3. Check Override (Tighten)
        if not np.isnan(ov_l):
            if curr_low == -np.inf or ov_l > curr_low:
                curr_low = ov_l
                
        # 4. Assign
        if not np.isinf(curr_low):
            adj_low_vals[i] = curr_low
            
    df['adjusted_major_high'] = adj_high_vals
    df['adjusted_major_low'] = adj_low_vals
    
    return df
