"""
test_bar_features.py
单根 K 线特征提取模块的单元测试
"""

import numpy as np
import pandas as pd
import pytest

from src.analysis.bar_features import add_bar_features, compute_bar_features


class TestComputeBarFeatures:
    """compute_bar_features 函数测试"""

    def test_standard_bull_bar(self):
        """标准多头 K 线测试"""
        df = pd.DataFrame(
            {
                "open": [10.0],
                "high": [15.0],
                "low": [9.0],
                "close": [14.0],
            }
        )
        result = compute_bar_features(df)

        # bar_color: 收盘 > 开盘 → +1 (阳线)
        assert result["bar_color"].iloc[0] == 1

        # body_pct: (14-10) / (15-9) = 4/6 ≈ 0.667
        assert abs(result["body_pct"].iloc[0] - 4 / 6) < 0.001

        # upper_tail_pct: (15-14) / (15-9) = 1/6 ≈ 0.167
        assert abs(result["upper_tail_pct"].iloc[0] - 1 / 6) < 0.001

        # lower_tail_pct: (10-9) / (15-9) = 1/6 ≈ 0.167
        assert abs(result["lower_tail_pct"].iloc[0] - 1 / 6) < 0.001

        # L2 恒等式: body_pct + upper_tail_pct + lower_tail_pct = 1
        total = (
            result["body_pct"].iloc[0]
            + result["upper_tail_pct"].iloc[0]
            + result["lower_tail_pct"].iloc[0]
        )
        assert abs(total - 1.0) < 0.001

        # --- L1 尺度特征测试 ---
        # total_range: 15 - 9 = 6.0
        assert result["total_range"].iloc[0] == 6.0

        # body_size: |14 - 10| = 4.0
        assert result["body_size"].iloc[0] == 4.0

        # amplitude: (15 - 9) / 10 = 0.6
        assert abs(result["amplitude"].iloc[0] - 0.6) < 0.001

        # --- L2.5 极简特征对测试 ---
        # clv: (2*14 - 15 - 9) / 6 = (28 - 24) / 6 = 4/6 ≈ 0.667
        assert abs(result["clv"].iloc[0] - 4 / 6) < 0.001

        # signed_body: (14 - 10) / 6 = 4/6 ≈ 0.667
        assert abs(result["signed_body"].iloc[0] - 4 / 6) < 0.001

        # --- L4 布尔分类器测试 ---
        # shaved_top: upper_tail_pct ≈ 0.167 > 0.02 → False
        assert result["shaved_top"].iloc[0] == False

        # shaved_bottom: lower_tail_pct ≈ 0.167 > 0.02 → False
        assert result["shaved_bottom"].iloc[0] == False

        # is_doji: body_pct ≈ 0.667 > 0.25 → False
        assert result["is_doji"].iloc[0] == False

        # is_trading_range_bar: Trend Bar 的反面。因为 is_trend_bar 为 True，所以这里为 False
        assert result["is_trading_range_bar"].iloc[0] == False

        # is_trend_bar: body_pct ≈ 0.667 >= 0.6 → True
        assert result["is_trend_bar"].iloc[0] == True

        # is_pinbar: 单侧影线 ≈ 0.167 < 0.66 → False
        assert result["is_pinbar"].iloc[0] == False

    def test_standard_bear_bar(self):
        """标准空头 K 线测试"""
        df = pd.DataFrame(
            {
                "open": [14.0],
                "high": [15.0],
                "low": [9.0],
                "close": [10.0],
            }
        )
        result = compute_bar_features(df)

        # bar_color: 收盘 < 开盘 → -1 (阴线)
        assert result["bar_color"].iloc[0] == -1

        # L2 恒等式: body_pct + upper_tail_pct + lower_tail_pct = 1
        total = (
            result["body_pct"].iloc[0]
            + result["upper_tail_pct"].iloc[0]
            + result["lower_tail_pct"].iloc[0]
        )
        assert abs(total - 1.0) < 0.001

    def test_doji_bar(self):
        """Doji K 线测试 (实体极小)"""
        df = pd.DataFrame(
            {
                "open": [10.0],
                "high": [15.0],
                "low": [5.0],
                "close": [10.5],  # 实体占比 = 0.5/10 = 0.05 < 0.1
            }
        )
        result = compute_bar_features(df)

        # bar_color: close > open → +1 (即使实体很小，颜色仍是阳线)
        assert result["bar_color"].iloc[0] == 1

        # is_doji: 实体占比 < 0.25 → True
        assert result["is_doji"].iloc[0] == True

        # body_pct: 0.5/10 = 0.05
        assert abs(result["body_pct"].iloc[0] - 0.05) < 0.001

        # is_trading_range_bar: 任何不是 Trend Bar 的都是 TR Bar (包括 Doji)
        # body_pct = 0.05 < 0.6 → is_trend_bar=False → is_trading_range_bar=True
        assert result["is_trading_range_bar"].iloc[0] == True

    def test_preclose_features(self):
        """Preclose 相关特征测试 (gap, day_return, true_range) - Dependent on shift(1)"""
        df = pd.DataFrame(
            {
                "open": [10.0, 11.0],  # Gap up from preclose (10)
                "high": [12.0, 15.0],
                "low": [8.0, 10.0],
                "close": [10.0, 14.0],
                # preclose column is ignored now
            }
        )
        result = compute_bar_features(df)

        # Use 2nd bar (index 1) for checks
        # gap: (11 - 10) / 10 = 0.1 (10% gap up)
        assert "gap" in result.columns
        assert abs(result["gap"].iloc[1] - (np.log(11.0 / 10.0))) < 0.001

        # day_return: (14 - 10) / 10 = 0.4 (40% up) -> ln(14/10)
        assert abs(result["day_return"].iloc[1] - np.log(14.0 / 10.0)) < 0.001

        # true_range: max(H-L=5, |H-PC|=|15-10|=5, |L-PC|=|10-10|=0) = 5
        assert result["true_range"].iloc[1] == 5.0

        # rel_true_range: 5 / 10 = 0.5
        assert abs(result["rel_true_range"].iloc[1] - 0.5) < 0.001

        # movement_efficiency: |14 - 10| / 5 = 4/5 = 0.8
        assert abs(result["movement_efficiency"].iloc[1] - 0.8) < 0.001

        # open_in_body: gap = 0.1 (10%), |gap| > 0.01 → False
        assert result["open_in_body"].iloc[1] == False

    def test_close_on_extreme(self):
        """close_on_extreme 特征测试 (|clv| > 0.9)"""
        # Case 1: 收盘在最高点 (CLV = 1.0)
        df_high = pd.DataFrame(
            {
                "open": [10.0],
                "high": [15.0],
                "low": [10.0],
                "close": [15.0],  # 收盘 = 最高
            }
        )
        result_high = compute_bar_features(df_high)
        assert result_high["close_on_extreme"].iloc[0] == True
        assert result_high["clv"].iloc[0] == 1.0

        # Case 2: 收盘在中间 (CLV = 0)
        df_mid = pd.DataFrame(
            {
                "open": [10.0],
                "high": [15.0],
                "low": [10.0],
                "close": [12.5],  # 收盘 = 中点
            }
        )
        result_mid = compute_bar_features(df_mid)
        assert result_mid["close_on_extreme"].iloc[0] == False
        assert abs(result_mid["clv"].iloc[0]) < 0.1

    def test_open_in_body(self):
        """open_in_body 特征测试 (|gap| < 1%)"""
        # Case 1: 开盘在前日收盘附近 (gap < 1%)
        df_in = pd.DataFrame(
            {
                "open": [10.0, 10.05],  # gap = 0.5% (10.05 mixed against prev close 10.0)
                "high": [11.0, 11.0],
                "low": [10.0, 10.0],
                "close": [10.0, 10.8],
            }
        )
        result_in = compute_bar_features(df_in)
        assert result_in["open_in_body"].iloc[1] == True

        # Case 2: 开盘跳空 (gap > 1%)
        df_out = pd.DataFrame(
            {
                "open": [10.0, 10.5],  # gap = 5%
                "high": [11.0, 11.0],
                "low": [10.0, 10.0],
                "close": [10.0, 10.8],
            }
        )
        result_out = compute_bar_features(df_out)
        assert result_out["open_in_body"].iloc[1] == False

    def test_single_bar_features(self):
        """测试单根K线的情况 (无历史数据)"""
        df = pd.DataFrame(
            {
                "open": [10.0],
                "high": [15.0],
                "low": [9.0],
                "close": [14.0],
            }
        )
        result = compute_bar_features(df)

        # 不应有 preclose 相关列 - 实际上列存在，但值为 NaN
        assert "gap" in result.columns
        assert np.isnan(result["gap"].iloc[0])
        assert np.isnan(result["true_range"].iloc[0])

    def test_zero_range_bar(self):
        """零振幅 K 线测试 (high == low)"""
        df = pd.DataFrame(
            {
                "open": [10.0],
                "high": [10.0],
                "low": [10.0],
                "close": [10.0],
            }
        )
        result = compute_bar_features(df)

        # 所有比例相关的特征应为 NaN
        assert np.isnan(result["body_pct"].iloc[0])
        assert np.isnan(result["upper_tail_pct"].iloc[0])
        assert np.isnan(result["lower_tail_pct"].iloc[0])

    def test_index_preservation(self):
        """测试索引保留"""
        df = pd.DataFrame(
            {
                "open": [10.0, 11.0],
                "high": [12.0, 13.0],
                "low": [9.0, 10.0],
                "close": [11.0, 12.0],
            },
            index=["2024-01-01", "2024-01-02"],
        )
        result = compute_bar_features(df)

        assert list(result.index) == ["2024-01-01", "2024-01-02"]


class TestAddBarFeatures:
    """add_bar_features 函数测试"""

    def test_adds_columns_to_df(self):
        """测试在原始 DataFrame 上添加列"""
        df = pd.DataFrame(
            {
                "open": [10.0],
                "high": [15.0],
                "low": [9.0],
                "close": [14.0],
            }
        )
        result = add_bar_features(df)

        # 原始列仍在
        assert "open" in result.columns
        assert "close" in result.columns

        # 新列已添加
        assert "bar_color" in result.columns
        assert "body_pct" in result.columns

    def test_prefix(self):
        """测试列名前缀"""
        df = pd.DataFrame(
            {
                "open": [10.0],
                "high": [15.0],
                "low": [9.0],
                "close": [14.0],
            }
        )
        result = add_bar_features(df, prefix="feat_")

        assert "feat_bar_color" in result.columns
        assert "feat_body_pct" in result.columns
        assert "bar_color" not in result.columns


class TestAlBrooksFeatures:
    """Tests for Al Brooks Price Action enhancements"""

    def test_rel_range_and_climax(self):
        """Test rel_range_to_avg and is_climax_bar"""
        # Need at least 20 bars. Create 20 bars with range 1, then 1 bar with range 5.
        data = {
            "open": np.arange(21),
            "close": np.arange(21) + 1,  # body size 1
            "high": np.arange(21) + 1,
            "low": np.arange(21),  # total range 1
        }
        df = pd.DataFrame(data)
        # Modify the last one to be a climax bar
        df.iloc[20, df.columns.get_loc("high")] = 20 + 5  # range 5
        df.iloc[20, df.columns.get_loc("low")] = 20
        df.iloc[20, df.columns.get_loc("close")] = 20 + 2  # keep it sane

        result = compute_bar_features(df)

        # First 19 should be NaN for rel_range (rolling 20 needs 20 items)
        # Index 0 to 18 = 19 items. Index 19 = 20th item.
        # result[0..18] -> NaN

        assert np.isnan(result["rel_range_to_avg"].iloc[0])
        assert np.isnan(result["rel_range_to_avg"].iloc[18])

        # 20th bar (index 19): avg of previous 20 (indexes 0-19).
        # ranges are all 1. avg 1. rel 1.
        assert abs(result["rel_range_to_avg"].iloc[19] - 1.0) < 0.001

        # 21st bar (index 20): range 5.
        # Window: 19 ones + 1 five = 24. Avg = 24/20 = 1.2
        # Rel range = 5 / 1.2 = 4.1666...
        expected_rel = 5 / 1.2
        assert abs(result["rel_range_to_avg"].iloc[20] - expected_rel) < 0.001
        assert result["is_climax_bar"].iloc[20] == True

    def test_strong_reversals(self):
        """Test strong bull/bear reversal features"""
        # Case 1: Strong Bull Reversal
        # open=10, close=14, high=15, low=5.
        # Body=4. Range=10. Body%=0.4.
        # LowerTail = 5 (0.5 > 0.33).
        # CLV = (.8 > 0.6).
        # Color = 1.

        # Case 2: Strong Bear Reversal
        # open=6, close=5.5, high=15, low=5.
        # Body=0.5. Range=10.
        # UpperTail = 15-6=9. Pct=0.9 (>0.33).
        # CLV = (11-20)/10 = -0.9 (<-0.6).
        # Color = -1.

        df = pd.DataFrame(
            {
                "open": [10.0, 6.0],
                "high": [15.0, 15.0],
                "low": [5.0, 5.0],
                "close": [14.0, 5.5],
            }
        )

        result = compute_bar_features(df)

        # Bull Reversal
        assert result["is_strong_bull_reversal"].iloc[0] == True
        assert result["is_strong_bear_reversal"].iloc[0] == False

        # Bear Reversal
        assert result["is_strong_bull_reversal"].iloc[1] == False
        assert result["is_strong_bear_reversal"].iloc[1] == True

    def test_body_gap(self):
        """Test body_gap logic"""
        # Bar 0: Range 10-20.
        # Bar 1: Range 25-30. Gap Up.
        # Gap = min(O,C)_1 - max(O,C)_0 = 25 - 20 = 5.

        # Bar 2: Range 22-28. Overlap/Down from 25-30.
        # Gap = min(22,28) - max(25,30) = 22 - 30 = -8.

        df = pd.DataFrame(
            {
                "open": [10, 25, 22],
                "close": [20, 30, 28],
                "high": [20, 30, 28],  # Simplify
                "low": [10, 25, 22],
            }
        )

        result = compute_bar_features(df)

        # index 1: Gap Up
        assert result["body_gap"].iloc[1] == 5.0

        # index 2: Overlap/Down
        assert result["body_gap"].iloc[2] == -8.0

    def test_trend_streak(self):
        """Test trend streak logic"""
        # Trend Bar Threshold: body_pct >= 0.6 (default)
        # Range 10. Trend >= 6.

        # Seq:
        # 0: Bull Trend (7/10)
        # 1: Bull Trend (8/10)
        # 2: Doji/TR (2/10)
        # 3: Bear Trend (7/10) -> Color -1
        # 4: Bear Trend (8/10) -> Color -1
        # 5: Bull Trend (9/10)

        o = [0, 0, 0, 10, 10, 0]
        c = [7, 8, 2, 3, 2, 9]
        # For bear bars (3,4): Open 10, Close 3 -> Body 7.
        # For bull bars (0,1,5): Open 0, Close 7.

        h = [12] * 6
        l = [-2] * 6  # Range 14.
        # Adjust range to be exactly 10 for simplicity?
        # Let's set high/low to match O/C + small epsilon to avoid exact heavy math.
        # Range 10.

        # Re-spec:
        # 0: O=0, C=7, H=10, L=0. Body 7/10=0.7. Trend. Color 1.
        # 1: O=0, C=8, H=10, L=0. Body 8/10=0.8. Trend. Color 1.
        # 2: O=0, C=2, H=10, L=0. Body 0.2. TR. Color 1.
        # 3: O=10, C=3, H=10, L=0. Body 7/10=0.7. Trend. Color -1.
        # 4: O=10, C=2, H=10, L=0. Body 8/10=0.8. Trend. Color -1.
        # 5: O=0, C=9, H=10, L=0. Body 9/10=0.9. Trend. Color 1.

        df = pd.DataFrame(
            {
                "open": [0, 0, 0, 10, 10, 0],
                "close": [7, 8, 2, 3, 2, 9],
                "high": [10] * 6,
                "low": [0] * 6,
            }
        )

        result = compute_bar_features(df)

        # Check Trend Status
        assert result["is_trend_bar"].tolist() == [True, True, False, True, True, True]
        assert result["bar_color"].tolist() == [1, 1, 1, -1, -1, 1]

        # Expected Streak:
        # 0: 1
        # 1: 2
        # 2: 0 (Not Trend)
        # 3: 1 (New direction)
        # 4: 2
        # 5: 1 (New direction)

        expected = [1, 2, 0, 1, 2, 1]
        np.testing.assert_array_equal(result["trend_streak"].values, expected)

    def test_engulfing_patterns(self):
        """Test engulfing pattern detection"""
        # Bar 0: 阴线 (Open=110, Close=100)
        # Bar 1: 阳线吞没 (Open=95, Close=115) -> 实体覆盖前日
        # Bar 2: 阳线 (Open=100, Close=110)
        # Bar 3: 阴线吞没 (Open=115, Close=95) -> 实体覆盖前日

        df = pd.DataFrame(
            {
                "open": [110, 95, 100, 115],
                "close": [100, 115, 110, 95],
                "high": [115, 120, 115, 120],
                "low": [95, 90, 95, 90],
            }
        )

        result = compute_bar_features(df)

        # Bar 1: Bull Engulfing
        assert result["is_bull_engulfing"].iloc[1] == True
        assert result["is_bear_engulfing"].iloc[1] == False

        # Bar 3: Bear Engulfing
        assert result["is_bull_engulfing"].iloc[3] == False
        assert result["is_bear_engulfing"].iloc[3] == True

    def test_outside_bar_directions(self):
        """Test is_outside_up and is_outside_down"""
        # Bar 0: 基准 (H=110, L=100)
        # Bar 1: Outside Up (H=115, L=95, C=112 > prev_H=110)
        # Bar 2: 基准 (H=110, L=100)
        # Bar 3: Outside Down (H=115, L=95, C=98 < prev_L=100)

        df = pd.DataFrame(
            {
                "open": [105, 100, 105, 100],
                "close": [105, 112, 105, 98],
                "high": [110, 115, 110, 115],
                "low": [100, 95, 100, 95],
            }
        )

        result = compute_bar_features(df)

        # Bar 1: Outside Up
        assert result["is_outside"].iloc[1] == True
        assert result["is_outside_up"].iloc[1] == True
        assert result["is_outside_down"].iloc[1] == False

        # Bar 3: Outside Down
        assert result["is_outside"].iloc[3] == True
        assert result["is_outside_up"].iloc[3] == False
        assert result["is_outside_down"].iloc[3] == True

    def test_blended_candle(self):
        """Test blended candle features"""
        # Bar 0: 大阴线 (O=110, C=100, H=115, L=95)
        # Bar 1: 大阳线 (O=100, C=110, H=115, L=95)
        # 合并后: blend_open=110, blend_close=110, blend_high=115, blend_low=95
        # blend_clv = (2*110 - 115 - 95) / 20 = (220-210)/20 = 0.5

        df = pd.DataFrame(
            {
                "open": [110, 100],
                "close": [100, 110],
                "high": [115, 115],
                "low": [95, 95],
            }
        )

        result = compute_bar_features(df)

        # 合并后的 CLV
        assert abs(result["blend_clv"].iloc[1] - 0.5) < 0.01
        # 合并后的 Body Pct = |110-110| / 20 = 0 (Doji)
        assert abs(result["blend_body_pct"].iloc[1]) < 0.01

    def test_failed_breakout(self):
        """Test failed breakout detection"""
        # Bar 0: 基准 (H=110, L=100)
        # Bar 1: Failed Breakout High (H=115 > prev_H=110, C=108 < prev_H=110)
        # Bar 2: 基准 (H=110, L=100)
        # Bar 3: Failed Breakout Low (L=95 < prev_L=100, C=102 > prev_L=100)

        df = pd.DataFrame(
            {
                "open": [105, 112, 105, 98],
                "close": [105, 108, 105, 102],
                "high": [110, 115, 110, 108],
                "low": [100, 105, 100, 95],
            }
        )

        result = compute_bar_features(df)

        # Bar 1: Failed Breakout High
        assert result["failed_breakout_high"].iloc[1] == True
        assert result["failed_breakout_low"].iloc[1] == False

        # Bar 3: Failed Breakout Low
        assert result["failed_breakout_high"].iloc[3] == False
        assert result["failed_breakout_low"].iloc[3] == True

    def test_ema_features(self):
        """Test EMA gravity features"""
        # 构造一个简单的上涨序列，使得 EMA 可预测
        # Close: 100, 102, 104, 106, 108 (持续上涨)
        # EMA(20) 在早期会接近 Close 值

        df = pd.DataFrame(
            {
                "open": [100, 101, 103, 105, 107],
                "close": [100, 102, 104, 106, 108],
                "high": [101, 103, 105, 107, 109],
                "low": [99, 101, 103, 105, 107],
            }
        )

        result = compute_bar_features(df)

        # EMA 应该存在
        assert "ema" in result.columns
        assert "dist_to_ema" in result.columns
        assert "bar_pos_ema" in result.columns
        assert "ema_touch" in result.columns
        assert "gap_below_ema" in result.columns
        assert "gap_above_ema" in result.columns

        # 在上涨趋势中，后期 K 线应该完全在 EMA 上方
        # bar_pos_ema = +1 (Low > EMA)
        # 由于 EMA 滞后，最后几根 K 线的 Low 可能 > EMA
        # 验证最后一根 K 线 (idx=4): Low=107
        ema_last = result["ema"].iloc[4]
        if result["low"].iloc[4] if "low" in result.columns else df["low"].iloc[4] > ema_last:
            assert result["bar_pos_ema"].iloc[4] == 1

        # dist_to_ema 在上涨趋势中应该为正
        assert result["dist_to_ema"].iloc[4] > 0

        # gap_above_ema: 如果 bar_pos_ema = +1 (Low > EMA)，则 gap_above_ema = True
        if result["bar_pos_ema"].iloc[4] == 1:
            assert result["gap_above_ema"].iloc[4] == True

    def test_ema_touch(self):
        """Test ema_touch detection"""
        # Bar 跨越 EMA (High >= EMA >= Low)
        # 构造一个 EMA 在 K 线中间穿过的场景

        df = pd.DataFrame(
            {
                "open": [100, 100, 100],
                "close": [100, 100, 100],
                "high": [105, 105, 105],
                "low": [95, 95, 95],
            }
        )

        result = compute_bar_features(df)

        # EMA(20) 初始值接近 Close=100
        # High=105, Low=95, 所以 ema_touch 应该为 True
        assert result["ema_touch"].iloc[0] == True

        # bar_pos_ema 应该为 0 (跨越 EMA)
        assert result["bar_pos_ema"].iloc[0] == 0
