"""
run_pipeline.py
驱动整个 K 线分析流水线的入口脚本。

流程:
1. 加载数据    - 使用 data_loader 自动适配数据源
2. 处理原始K线 - 添加 K 线状态标签
3. K线合并     - 合并包含关系的 K 线
4. 分型识别    - 识别分型并过滤生成有效笔

用法:
    uv run run_pipeline.py              # 交互式选择数据文件
    uv run run_pipeline.py TL.CFE.xlsx  # 直接指定文件
    
输出文件:
    - *_processed.csv   (带状态标签的原始K线)
    - *_merged.csv      (合并后的K线)
    - *_strokes.csv     (带笔端点标记的最终结果)
    - output_merged_kline.png  (合并后K线图)
    - output_strokes.png       (笔端点标记图)
"""

import sys
from pathlib import Path

# 支持的数据文件扩展名
SUPPORTED_EXTENSIONS = {'.xlsx', '.xls', '.csv'}


def find_data_files(directory: Path = Path('.')) -> list[Path]:
    """扫描目录下所有支持的数据文件（排除处理后的输出文件）"""
    files = []
    for ext in SUPPORTED_EXTENSIONS:
        for f in directory.glob(f'*{ext}'):
            # 排除输出文件
            if not any(suffix in f.stem for suffix in ['_processed', '_merged', '_strokes']):
                files.append(f)
    return sorted(files, key=lambda x: x.name.lower())


def select_file_interactive() -> str:
    """交互式选择数据文件"""
    files = find_data_files()
    
    if not files:
        print("❌ 当前目录下没有找到可处理的数据文件")
        print(f"   支持的格式: {', '.join(SUPPORTED_EXTENSIONS)}")
        sys.exit(1)
    
    if len(files) == 1:
        print(f"找到数据文件: {files[0].name}")
        return str(files[0])
    
    print("\n📂 请选择要处理的数据文件:\n")
    for i, f in enumerate(files, 1):
        # 显示文件大小
        size_kb = f.stat().st_size / 1024
        print(f"  [{i}] {f.name}  ({size_kb:.1f} KB)")
    
    print(f"\n  [0] 退出\n")
    
    while True:
        try:
            choice = input("请输入序号: ").strip()
            if choice == '0':
                print("已退出")
                sys.exit(0)
            
            idx = int(choice) - 1
            if 0 <= idx < len(files):
                selected = files[idx]
                print(f"\n✅ 已选择: {selected.name}\n")
                return str(selected)
            else:
                print(f"请输入 0-{len(files)} 之间的数字")
        except ValueError:
            print("请输入有效的数字")
        except KeyboardInterrupt:
            print("\n已取消")
            sys.exit(0)


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
    # 支持命令行参数或交互式选择
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        input_file = select_file_interactive()
    
    main(input_file)
