"""
test_bar_features.py
单根 K 线特征提取模块的单元测试
"""

import numpy as np
import pandas as pd
import pytest

from src.analysis.bar_features import compute_bar_features, add_bar_features


class TestComputeBarFeatures:
    """compute_bar_features 函数测试"""

    def test_standard_bull_bar(self):
        """标准多头 K 线测试"""
        df = pd.DataFrame({
            "open": [10.0],
            "high": [15.0],
            "low": [9.0],
            "close": [14.0],
        })
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
        total = (result["body_pct"].iloc[0] + 
                 result["upper_tail_pct"].iloc[0] + 
                 result["lower_tail_pct"].iloc[0])
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
        df = pd.DataFrame({
            "open": [14.0],
            "high": [15.0],
            "low": [9.0],
            "close": [10.0],
        })
        result = compute_bar_features(df)

        # bar_color: 收盘 < 开盘 → -1 (阴线)
        assert result["bar_color"].iloc[0] == -1

        # L2 恒等式: body_pct + upper_tail_pct + lower_tail_pct = 1
        total = (result["body_pct"].iloc[0] + 
                 result["upper_tail_pct"].iloc[0] + 
                 result["lower_tail_pct"].iloc[0])
        assert abs(total - 1.0) < 0.001

    def test_doji_bar(self):
        """Doji K 线测试 (实体极小)"""
        df = pd.DataFrame({
            "open": [10.0],
            "high": [15.0],
            "low": [5.0],
            "close": [10.5],  # 实体占比 = 0.5/10 = 0.05 < 0.1
        })
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
        """Preclose 相关特征测试 (gap, day_return, true_range)"""
        df = pd.DataFrame({
            "open": [11.0],     # Gap up from preclose
            "high": [15.0],
            "low": [10.0],
            "close": [14.0],
            "preclose": [10.0],  # 昨收
        })
        result = compute_bar_features(df)

        # gap: (11 - 10) / 10 = 0.1 (10% gap up)
        assert "gap" in result.columns
        assert abs(result["gap"].iloc[0] - 0.1) < 0.001
        
        # day_return: (14 - 10) / 10 = 0.4 (40% up)
        assert abs(result["day_return"].iloc[0] - 0.4) < 0.001
        
        # true_range: max(H-L=5, |H-PC|=5, |L-PC|=0) = 5
        assert result["true_range"].iloc[0] == 5.0
        
        # rel_true_range: 5 / 10 = 0.5
        assert abs(result["rel_true_range"].iloc[0] - 0.5) < 0.001
        
        # movement_efficiency: |14 - 10| / 5 = 4/5 = 0.8
        assert abs(result["movement_efficiency"].iloc[0] - 0.8) < 0.001
        
        # open_in_body: gap = 0.1 (10%), |gap| > 0.01 → False
        assert result["open_in_body"].iloc[0] == False

    def test_close_on_extreme(self):
        """close_on_extreme 特征测试 (|clv| > 0.9)"""
        # Case 1: 收盘在最高点 (CLV = 1.0)
        df_high = pd.DataFrame({
            "open": [10.0],
            "high": [15.0],
            "low": [10.0],
            "close": [15.0],  # 收盘 = 最高
        })
        result_high = compute_bar_features(df_high)
        assert result_high["close_on_extreme"].iloc[0] == True
        assert result_high["clv"].iloc[0] == 1.0
        
        # Case 2: 收盘在中间 (CLV = 0)
        df_mid = pd.DataFrame({
            "open": [10.0],
            "high": [15.0],
            "low": [10.0],
            "close": [12.5],  # 收盘 = 中点
        })
        result_mid = compute_bar_features(df_mid)
        assert result_mid["close_on_extreme"].iloc[0] == False
        assert abs(result_mid["clv"].iloc[0]) < 0.1

    def test_open_in_body(self):
        """open_in_body 特征测试 (|gap| < 1%)"""
        # Case 1: 开盘在前日收盘附近 (gap < 1%)
        df_in = pd.DataFrame({
            "open": [10.05],   # gap = 0.5%
            "high": [11.0],
            "low": [10.0],
            "close": [10.8],
            "preclose": [10.0],
        })
        result_in = compute_bar_features(df_in)
        assert result_in["open_in_body"].iloc[0] == True
        
        # Case 2: 开盘跳空 (gap > 1%)
        df_out = pd.DataFrame({
            "open": [10.5],   # gap = 5%
            "high": [11.0],
            "low": [10.0],
            "close": [10.8],
            "preclose": [10.0],
        })
        result_out = compute_bar_features(df_out)
        assert result_out["open_in_body"].iloc[0] == False

    def test_no_preclose(self):
        """没有 preclose 列时，不应有 gap/day_return/true_range"""
        df = pd.DataFrame({
            "open": [10.0],
            "high": [15.0],
            "low": [9.0],
            "close": [14.0],
        })
        result = compute_bar_features(df)

        # 不应有 preclose 相关列
        assert "gap" not in result.columns
        assert "day_return" not in result.columns
        assert "true_range" not in result.columns

    def test_zero_range_bar(self):
        """零振幅 K 线测试 (high == low)"""
        df = pd.DataFrame({
            "open": [10.0],
            "high": [10.0],
            "low": [10.0],
            "close": [10.0],
        })
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
        df = pd.DataFrame({
            "open": [10.0],
            "high": [15.0],
            "low": [9.0],
            "close": [14.0],
        })
        result = add_bar_features(df)

        # 原始列仍在
        assert "open" in result.columns
        assert "close" in result.columns

        # 新列已添加
        assert "bar_color" in result.columns
        assert "body_pct" in result.columns

    def test_prefix(self):
        """测试列名前缀"""
        df = pd.DataFrame({
            "open": [10.0],
            "high": [15.0],
            "low": [9.0],
            "close": [14.0],
        })
        result = add_bar_features(df, prefix="feat_")

        assert "feat_bar_color" in result.columns
        assert "feat_body_pct" in result.columns
        assert "bar_color" not in result.columns
