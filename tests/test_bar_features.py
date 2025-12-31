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

        # bar_dir: 收盘 > 开盘 → +1
        assert result["bar_dir"].iloc[0] == 1

        # body_pct: (14-10) / (15-9) = 4/6 ≈ 0.667
        assert abs(result["body_pct"].iloc[0] - 4 / 6) < 0.001

        # close_pos: (14-9) / (15-9) = 5/6 ≈ 0.833
        assert abs(result["close_pos"].iloc[0] - 5 / 6) < 0.001

        # upper_tail_pct: (15-14) / (15-9) = 1/6 ≈ 0.167
        assert abs(result["upper_tail_pct"].iloc[0] - 1 / 6) < 0.001

        # lower_tail_pct: (10-9) / (15-9) = 1/6 ≈ 0.167
        assert abs(result["lower_tail_pct"].iloc[0] - 1 / 6) < 0.001

    def test_standard_bear_bar(self):
        """标准空头 K 线测试"""
        df = pd.DataFrame({
            "open": [14.0],
            "high": [15.0],
            "low": [9.0],
            "close": [10.0],
        })
        result = compute_bar_features(df)

        # bar_dir: 收盘 < 开盘 → -1
        assert result["bar_dir"].iloc[0] == -1

        # close_pos: (10-9) / (15-9) = 1/6 ≈ 0.167
        assert abs(result["close_pos"].iloc[0] - 1 / 6) < 0.001

    def test_doji_bar(self):
        """Doji K 线测试 (实体极小)"""
        df = pd.DataFrame({
            "open": [10.0],
            "high": [15.0],
            "low": [5.0],
            "close": [10.5],  # 实体占比 = 0.5/10 = 0.05 < 0.1
        })
        result = compute_bar_features(df)

        # bar_dir: 实体占比 < 0.1 → 0 (Doji)
        assert result["bar_dir"].iloc[0] == 0

        # body_pct: 0.5/10 = 0.05
        assert abs(result["body_pct"].iloc[0] - 0.05) < 0.001

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
        assert np.isnan(result["close_pos"].iloc[0])
        assert np.isnan(result["upper_tail_pct"].iloc[0])
        assert np.isnan(result["lower_tail_pct"].iloc[0])

    def test_rel_size_calculation(self):
        """相对振幅计算测试"""
        # 创建 5 根振幅相同的 K 线，然后一根振幅翻倍的 K 线
        df = pd.DataFrame({
            "open": [10.0] * 5 + [10.0],
            "high": [12.0] * 5 + [14.0],  # 振幅 2 * 5 + 振幅 4
            "low": [10.0] * 5 + [10.0],
            "close": [11.0] * 5 + [13.0],
        })
        result = compute_bar_features(df, rel_size_lookback=5)

        # rolling(5) 包含当前行，所以第 6 根 K 线 (index=5) 时
        # 窗口为 [2, 2, 2, 2, 4]，平均 = 2.4
        # rel_size = 4 / 2.4 ≈ 1.667
        assert abs(result["rel_size"].iloc[5] - 4 / 2.4) < 0.001

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
        assert "bar_dir" in result.columns
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

        assert "feat_bar_dir" in result.columns
        assert "feat_body_pct" in result.columns
        assert "bar_dir" not in result.columns
