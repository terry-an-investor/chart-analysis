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
    uv run run_pipeline.py data/raw/TL.CFE.xlsx  # 直接指定文件
    
输出文件:
    - data/processed/*_processed.csv   (带状态标签的原始K线)
    - data/processed/*_merged.csv      (合并后的K线)
    - data/processed/*_strokes.csv     (带笔端点标记的最终结果)
    - output/*_merged_kline.png        (合并后K线图)
    - output/*_strokes.png             (笔端点标记图)
"""

import sys
from pathlib import Path

# 确保 src 模块可导入
sys.path.insert(0, str(Path(__file__).parent))

# 目录配置
DATA_RAW_DIR = Path("data/raw")
DATA_PROCESSED_DIR = Path("data/processed")
OUTPUT_DIR = Path("output")

# 支持的数据文件扩展名
SUPPORTED_EXTENSIONS = {'.xlsx', '.xls', '.csv'}


def find_data_files(directory: Path = DATA_RAW_DIR) -> list[Path]:
    """扫描目录下所有支持的数据文件"""
    if not directory.exists():
        return []
    
    files = []
    for ext in SUPPORTED_EXTENSIONS:
        for f in directory.glob(f'*{ext}'):
            files.append(f)
    return sorted(files, key=lambda x: x.name.lower())


def select_file_interactive() -> str:
    """交互式选择数据文件"""
    files = find_data_files()
    
    if not files:
        print(f"❌ 目录 '{DATA_RAW_DIR}' 下没有找到可处理的数据文件")
        print(f"   支持的格式: {', '.join(SUPPORTED_EXTENSIONS)}")
        print(f"   请将数据文件放到 {DATA_RAW_DIR}/ 目录下")
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


def main(input_file: str):
    print("=" * 60)
    print("K 线分析流水线 (Bill Williams / Chan Theory)")
    print("=" * 60)
    
    # 确保输出目录存在
    DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # 从输入文件名生成输出文件名和子目录
    input_path = Path(input_file)
    base_name = input_path.stem  # 不含扩展名的文件名，如 "TL.CFE"
    
    # 提取ticker作为子目录名（取第一个点之前的部分，转小写）
    ticker = base_name.split('.')[0].lower()  # "TL.CFE" -> "tl"
    
    # 创建ticker子目录
    ticker_processed_dir = DATA_PROCESSED_DIR / ticker
    ticker_output_dir = OUTPUT_DIR / ticker
    ticker_processed_dir.mkdir(parents=True, exist_ok=True)
    ticker_output_dir.mkdir(parents=True, exist_ok=True)
    
    # 输出路径
    processed_csv = ticker_processed_dir / f"{base_name}_processed.csv"
    merged_csv = ticker_processed_dir / f"{base_name}_merged.csv"
    strokes_csv = ticker_processed_dir / f"{base_name}_strokes.csv"
    merged_plot = ticker_output_dir / f"{base_name}_merged_kline.png"
    strokes_plot = ticker_output_dir / f"{base_name}_strokes.png"
    
    # Step 1: 加载数据
    print(f"\n[Step 1/4] 加载数据: {input_file}")
    from src.io import load_ohlc
    data = load_ohlc(input_file)
    print(f"  加载完成: {data}")
    print(f"  日期范围: {data.date_range[0].date()} ~ {data.date_range[1].date()}")
    
    # Step 2: 处理原始数据，添加K线状态
    print(f"\n[Step 2/4] 添加 K 线状态标签...")
    from src.analysis import process_and_save
    process_and_save(data, str(processed_csv))
    
    # Step 3: K 线合并
    print(f"\n[Step 3/4] 合并包含关系的 K 线...")
    from src.analysis.merging import apply_kline_merging
    apply_kline_merging(str(processed_csv), str(merged_csv), 
                        save_plot_path=str(merged_plot))
    
    # Step 4: 分型识别与笔过滤
    print(f"\n[Step 4/4] 识别分型并生成有效笔...")
    from src.analysis.fractals import process_strokes
    process_strokes(str(merged_csv), str(strokes_csv),
                    save_plot_path=str(strokes_plot))

    # Step 5: 生成交互式图表
    print(f"\n[Step 5/5] 生成交互式 HTML 图表...")
    from src.analysis import plot_interactive_kline
    interactive_plot = ticker_output_dir / f"{base_name}_interactive.html"
    
    # 重新加载数据以获取绘图所需的DataFrame
    import pandas as pd
    from src.io import load_ohlc
    
    # 注意：这里我们使用合并后的数据来画图，因为它更干净
    # 但strokes是基于合并后数据的索引，所以是对齐的
    merged_df = pd.read_csv(merged_csv)
    # 转换 datetime
    merged_df['datetime'] = pd.to_datetime(merged_df['datetime'])
    merged_df.set_index('datetime', inplace=False) # 保持 DataFrame 结构
    
    # 读取 strokes
    strokes_df = pd.read_csv(strokes_csv)
    # 转换 strokes 为 [(idx, type)] 格式
    stroke_list = [
        (idx, row['valid_fractal']) 
        for idx, row in strokes_df.iterrows()
        if pd.notna(row['valid_fractal'])
    ]
    
    plot_interactive_kline(merged_df, stroke_list, str(interactive_plot))
    
    print("\n" + "=" * 60)
    print("流水线完成！")
    print("=" * 60)
    print("生成文件:")
    print(f"  CSV (data/processed/):")
    print(f"    - {processed_csv.name}  (带状态标签的原始K线)")
    print(f"    - {merged_csv.name}     (合并后的K线)")
    print(f"    - {strokes_csv.name}    (带笔端点标记的最终结果)")
    print(f"  图表 (output/):")
    print(f"    - {merged_plot.name}  (合并后K线图)")
    print(f"    - {strokes_plot.name}       (笔端点标记图)")
    print(f"    - {interactive_plot.name}   (交互式HTML图表) 🆕")


if __name__ == "__main__":
    # 支持命令行参数或交互式选择
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        input_file = select_file_interactive()
    
    main(input_file)
