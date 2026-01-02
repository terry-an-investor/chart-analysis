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
    rolling_max = highs.rolling(window=scan_window, center=True).max()
    rolling_min = lows.rolling(window=scan_window, center=True).min()
    
    # 标记几何高低点
    # 注意: 如果相邻多根 K 线价格相同，rolling 会让它们都等于 max/min
    # 我们需要只取第一个作为有效摆动点
    is_high_raw = (highs == rolling_max)
    is_low_raw = (lows == rolling_min)
    
    # 去重: 只保留连续相同高点中的第一个
    # 通过检查前一根是否也是高点来实现: 如果前一根也是高点，则当前不算
    is_high_raw = is_high_raw & (~is_high_raw.shift(1).fillna(False))
    is_low_raw = is_low_raw & (~is_low_raw.shift(1).fillna(False))
    
    # -------------------------------------------------------------------------
    # 2. 信号层确认 (Signal Confirmation) - 消除未来函数
    # -------------------------------------------------------------------------
    # 关键步骤: 将 Index=T 的信号平移到 Index=T+window
    # 这意味着我们在 T+window 时刻才"确认"之前那个是高点
    df['swing_high_confirmed'] = is_high_raw.shift(window).fillna(False)
    df['swing_low_confirmed'] = is_low_raw.shift(window).fillna(False)
    
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
    
    # 初始化输出列
    df['swing_type'] = np.nan     # HH, LH, HL, LL, DT, DB
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
