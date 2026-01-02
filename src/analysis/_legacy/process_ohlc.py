"""
analysis/process_ohlc.py
通用 OHLC 数据处理模块，为 K 线添加状态标签。
"""

import pandas as pd
from .kline_logic import classify_k_line_combination
from ..io.schema import OHLCData, COL_DATETIME, COL_HIGH, COL_LOW


def add_kline_status(data: OHLCData) -> pd.DataFrame:
    """
    为 OHLC 数据添加 K 线状态标签。
    
    Args:
        data: 标准化的 OHLCData 对象
        
    Returns:
        pd.DataFrame: 添加了 'kline_status' 列的 DataFrame
    """
    df = data.df.copy()
    
    print(f"处理数据: {data.symbol} ({len(df)} 根K线)")
    
    # 状态列表
    status_list = ["INITIAL"]  # 第一根没有对比
    
    for i in range(1, len(df)):
        h1 = df.iloc[i-1][COL_HIGH]
        l1 = df.iloc[i-1][COL_LOW]
        h2 = df.iloc[i][COL_HIGH]
        l2 = df.iloc[i][COL_LOW]
        
        status = classify_k_line_combination(h1, l1, h2, l2)
        status_list.append(status.name)
    
    df['kline_status'] = status_list
    
    # 打印预览
    print("\n结果预览 (前5行):")
    print(df[[COL_DATETIME, COL_HIGH, COL_LOW, 'kline_status']].head())
    
    return df


def process_and_save(data: OHLCData, output_path: str) -> pd.DataFrame:
    """
    处理 OHLC 数据并保存为 CSV。
    
    Args:
        data: 标准化的 OHLCData 对象
        output_path: 输出 CSV 文件路径
        
    Returns:
        pd.DataFrame: 处理后的 DataFrame
    """
    df = add_kline_status(data)
    
    # 保存结果 (使用 UTF-8 编码，更通用)
    df.to_csv(output_path, index=False, encoding='utf-8')
    print(f"\n处理完成，保存至: {output_path}")
    
    return df
