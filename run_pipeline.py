"""
run_pipeline.py
驱动整个 K 线分析流水线的入口脚本。

流程:
1. 加载数据    - 使用 data_loader 自动适配数据源
2. 处理原始K线 - 添加 K 线状态标签
3. K线合并     - 合并包含关系的 K 线
4. 分型识别    - 识别分型并过滤生成有效笔

用法:
    uv run run_pipeline.py [数据文件路径]
    
示例:
    uv run run_pipeline.py TL.CFE.xlsx
    uv run run_pipeline.py path/to/other_data.csv
    
输出文件:
    - *_processed.csv   (带状态标签的原始K线)
    - *_merged.csv      (合并后的K线)
    - *_strokes.csv     (带笔端点标记的最终结果)
    - output_merged_kline.png  (合并后K线图)
    - output_strokes.png       (笔端点标记图)
"""

import sys
from pathlib import Path


def main(input_file: str = "TL.CFE.xlsx"):
    print("=" * 60)
    print("K 线分析流水线 (Bill Williams / Chan Theory)")
    print("=" * 60)
    
    # 从输入文件名生成输出文件名
    input_path = Path(input_file)
    base_name = input_path.stem  # 不含扩展名的文件名
    
    processed_csv = f"{base_name}_processed.csv"
    merged_csv = f"{base_name}_merged.csv"
    strokes_csv = f"{base_name}_strokes.csv"
    
    # Step 1: 加载数据
    print(f"\n[Step 1/4] 加载数据: {input_file}")
    from data_loader import load_ohlc
    data = load_ohlc(input_file)
    print(f"  加载完成: {data}")
    print(f"  日期范围: {data.date_range[0].date()} ~ {data.date_range[1].date()}")
    
    # Step 2: 处理原始数据，添加K线状态
    print(f"\n[Step 2/4] 添加 K 线状态标签...")
    from process_ohlc import process_and_save
    process_and_save(data, processed_csv)
    
    # Step 3: K 线合并
    print(f"\n[Step 3/4] 合并包含关系的 K 线...")
    from kline_merging import apply_kline_merging
    apply_kline_merging(processed_csv, merged_csv, 
                        save_plot_path='output_merged_kline.png')
    
    # Step 4: 分型识别与笔过滤
    print(f"\n[Step 4/4] 识别分型并生成有效笔...")
    from filter_fractals import process_strokes
    process_strokes(merged_csv, strokes_csv,
                    save_plot_path='output_strokes.png')
    
    print("\n" + "=" * 60)
    print("流水线完成！")
    print("=" * 60)
    print("生成文件:")
    print("  CSV:")
    print(f"    - {processed_csv}  (带状态标签的原始K线)")
    print(f"    - {merged_csv}     (合并后的K线)")
    print(f"    - {strokes_csv}    (带笔端点标记的最终结果)")
    print("  图表:")
    print("    - output_merged_kline.png  (合并后K线图)")
    print("    - output_strokes.png       (笔端点标记图)")


if __name__ == "__main__":
    # 支持命令行参数
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        input_file = "TL.CFE.xlsx"  # 默认使用 xlsx 文件
    
    main(input_file)
