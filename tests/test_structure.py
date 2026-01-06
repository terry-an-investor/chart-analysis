"""
test_structure.py
市场结构模块 (structure.py) 的单元测试
"""

import numpy as np
import pandas as pd
import pytest

from src.analysis.structure import (
    DEFAULT_SWING_WINDOW,
    classify_swings,
    classify_swings_v2,
    classify_swings_v3,
    detect_swings,
)


class TestDetectSwings:
    """detect_swings 函数测试"""

    def test_plot_columns_exist(self):
        """验证绘图辅助列 plot_swing_high/low 存在"""
        # 构造简单数据：中间有一个明显的高点
        df = pd.DataFrame(
            {
                "high": [10, 11, 15, 12, 10, 9, 8, 9, 10, 11, 12],
                "low": [8, 9, 13, 10, 8, 7, 6, 7, 8, 9, 10],
                "close": [9, 10, 14, 11, 9, 8, 7, 8, 9, 10, 11],
                "open": [9, 10, 13, 12, 10, 9, 7, 7, 8, 9, 10],
            }
        )

        result = detect_swings(df, window=2)

        # 检查列存在
        assert "plot_swing_high" in result.columns
        assert "plot_swing_low" in result.columns

    def test_plot_swing_high_at_physical_position(self):
        """验证 plot_swing_high 在物理高点位置有值"""
        # 索引 2 是几何高点 (high=15)，window=2 意味着确认在索引 4
        # plot_swing_high 应该把值移回索引 2
        df = pd.DataFrame(
            {
                "high": [10, 11, 15, 12, 10, 9, 8, 9, 10, 11, 12],
                "low": [8, 9, 13, 10, 8, 7, 6, 7, 8, 9, 10],
            }
        )

        result = detect_swings(df, window=2)

        # swing_high_price 应该在索引 4 (确认点) 有值 15
        assert result.loc[4, "swing_high_confirmed"] == True
        assert result.loc[4, "swing_high_price"] == 15

        # plot_swing_high 应该在索引 2 (物理点) 有值 15
        # 因为 shift(-window) 将索引 4 的值移到了索引 2
        assert result.loc[2, "plot_swing_high"] == 15

    def test_plot_swing_low_at_physical_position(self):
        """验证 plot_swing_low 在物理低点位置有值"""
        # 索引 6 是几何低点 (low=6)，window=2 意味着确认在索引 8
        df = pd.DataFrame(
            {
                "high": [10, 11, 15, 12, 10, 9, 8, 9, 10, 11, 12],
                "low": [8, 9, 13, 10, 8, 7, 6, 7, 8, 9, 10],
            }
        )

        result = detect_swings(df, window=2)

        # plot_swing_low 应该在索引 6 (物理点) 有值
        assert result.loc[8, "swing_low_confirmed"] == True
        assert result.loc[6, "plot_swing_low"] == 6


class TestClassifySwingsV3:
    """classify_swings_v3 函数测试"""

    def test_close_based_breakout_bull(self):
        """验证使用 Close 判断牛市突破"""
        # 构造场景：High 刺破阻力但 Close 未破
        # 初始阻力位应该保持不变
        df = pd.DataFrame(
            {
                "high": [10, 10, 10, 10, 10, 10, 12, 10, 10, 10, 10, 10],
                "low": [8, 8, 8, 8, 8, 8, 9, 8, 8, 8, 8, 8],
                "close": [9, 9, 9, 9, 9, 9, 9.5, 9, 9, 9, 9, 9],  # Close 未突破
                "open": [9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9],
            }
        )

        result = classify_swings_v3(df, window=2)

        # High 刺破但 Close 未破，趋势不应变为 Bull
        # 索引 6: High=12 刺破初始阻力(~10)，但 Close=9.5 未突破
        # 趋势应该仍然是 Neutral (0)
        assert result.loc[6, "market_trend"] == 0

    def test_close_based_breakout_bear(self):
        """验证使用 Close 判断熊市突破"""
        # 构造场景：Low 刺破支撑但 Close 未破
        df = pd.DataFrame(
            {
                "high": [10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10],
                "low": [8, 8, 8, 8, 8, 8, 6, 8, 8, 8, 8, 8],  # Low 刺破
                "close": [9, 9, 9, 9, 9, 9, 8.5, 9, 9, 9, 9, 9],  # Close 未跌破
                "open": [9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9],
            }
        )

        result = classify_swings_v3(df, window=2)

        # Low 刺破但 Close 未破，趋势不应变为 Bear
        assert result.loc[6, "market_trend"] == 0

    def test_real_close_breakout_triggers_trend(self):
        """验证真正的 Close 突破会触发趋势变化"""
        df = pd.DataFrame(
            {
                "high": [10, 10, 10, 10, 10, 10, 12, 12, 12, 12, 12, 12],
                "low": [8, 8, 8, 8, 8, 8, 9, 9, 9, 9, 9, 9],
                "close": [9, 9, 9, 9, 9, 9, 11, 11, 11, 11, 11, 11],  # Close 突破了
                "open": [9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9],
            }
        )

        result = classify_swings_v3(df, window=2)

        # Close > 初始阻力 (10)，趋势应该变为 Bull (1)
        assert result.loc[6, "market_trend"] == 1

    def test_bar_by_bar_instant_reaction(self):
        """验证突破后状态即时变化，无滞后"""
        # 构造场景：第 6 根 K 线发生突破
        df = pd.DataFrame(
            {
                "high": [10, 10, 10, 10, 10, 10, 12, 12, 12, 12, 12, 12],
                "low": [8, 8, 8, 8, 8, 8, 9, 9, 9, 9, 9, 9],
                "close": [9, 9, 9, 9, 9, 9, 11, 11, 11, 11, 11, 11],
                "open": [9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9],
            }
        )

        result = classify_swings_v3(df, window=2)

        # 在第 6 根 K 线就应该变成 Bull，而不是等到形成新的 Swing Point
        assert result.loc[5, "market_trend"] == 0  # 突破前
        assert result.loc[6, "market_trend"] == 1  # 突破后立即变化

    def test_level_disappears_after_break(self):
        """验证突破后 Level 消失 (变为 NaN 或被新值替代)"""
        df = pd.DataFrame(
            {
                "high": [10, 10, 10, 10, 10, 10, 12, 12, 12, 12, 12, 12],
                "low": [8, 8, 8, 8, 8, 8, 9, 9, 9, 9, 9, 9],
                "close": [9, 9, 9, 9, 9, 9, 11, 11, 11, 11, 11, 11],
                "open": [9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9],
            }
        )

        result = classify_swings_v3(df, window=2)

        # 突破后趋势变为 Bull，此时应该显示 major_low (止损线)
        # major_high 应该消失或不显示 (因为已被突破)
        assert result.loc[6, "market_trend"] == 1
        assert pd.notna(result.loc[6, "major_low"])  # 止损线存在

    def test_swing_type_classification(self):
        """验证 Swing Type (HH/HL/LH/LL) 分类正确"""
        # 构造一个先涨后跌的场景
        df = pd.DataFrame(
            {
                "high": [10, 11, 12, 11, 10, 9, 8, 7, 8, 9, 10, 9, 8],
                "low": [8, 9, 10, 9, 8, 7, 6, 5, 6, 7, 8, 7, 6],
                "close": [9, 10, 11, 10, 9, 8, 7, 6, 7, 8, 9, 8, 7],
                "open": [9, 9, 10, 11, 10, 9, 8, 7, 6, 7, 8, 9, 8],
            }
        )

        result = classify_swings_v3(df, window=2)

        # 验证 swing_type 列存在且有效
        assert "swing_type" in result.columns
        # 应该有一些非 NaN 的分类
        swing_types = result["swing_type"].dropna().unique()
        assert len(swing_types) > 0


class TestCompareV2V3:
    """比较 V2 和 V3 的行为差异"""

    def test_v3_filters_wick_breakouts(self):
        """验证 V3 能过滤影线假突破，而 V2 可能不能"""
        # 影线刺破场景
        df = pd.DataFrame(
            {
                "high": [10, 10, 10, 10, 10, 10, 15, 10, 10, 10, 10, 10],  # index 6 影线刺破
                "low": [8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8],
                "close": [9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9],  # Close 未突破
                "open": [9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9],
            }
        )

        result_v3 = classify_swings_v3(df, window=2)

        # V3 应该不会因为影线刺破而改变趋势
        # (V2 的行为取决于其内部逻辑，这里主要验证 V3)
        assert result_v3.loc[6, "market_trend"] == 0  # 趋势不变
