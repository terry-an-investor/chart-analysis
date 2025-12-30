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


def select_file_interactive() -> list[str]:
    """交互式选择数据文件 (支持多选)"""
    from src.io.data_config import DATA_SOURCES
    
    files = find_data_files()
    
    if not files:
        print(f"❌ 目录 '{DATA_RAW_DIR}' 下没有找到可处理的数据文件")
        print(f"   支持的格式: {', '.join(SUPPORTED_EXTENSIONS)}")
        print(f"   请将数据文件放到 {DATA_RAW_DIR}/ 目录下")
        sys.exit(1)
    
    if len(files) == 1:
        print(f"找到数据文件: {files[0].name}")
        return [str(files[0])]
    
    # 区分 API 获取的文件和用户提供的文件
    api_filenames = {cfg.filename for cfg in DATA_SOURCES}
    api_files = []
    user_files = []
    
    import re
    # 匹配 Wind API 输出的文件名格式: 代码_后缀.xlsx (如 000510_SH.xlsx)
    wind_file_pattern = re.compile(r'^[a-zA-Z0-9.]+_[a-zA-Z]+\.xlsx$', re.IGNORECASE)
    
    for f in files:
        if f.name in api_filenames or wind_file_pattern.match(f.name):
            api_files.append(f)
        else:
            user_files.append(f)
            
    # 合并列表用于索引选择 (API 在前)
    all_files = api_files + user_files
    
    print("\n📂 请选择要处理的数据文件:\n")
    
    current_idx = 1
    
    if api_files:
        print("  --- 🌏 来自 Wind API ---")
        
        # 尝试为一个 Wind 连接实例化适配器 (用于解析名称)
        wind_adapter = None
        
        # 读取名称缓存
        import json
        cache_data = {}
        cache_file = Path("data") / "security_names.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
            except Exception:
                pass
        
        for f in api_files:
            size_kb = f.stat().st_size / 1024
            # 找到对应的配置名称
            comment = ""
            found_config = False
            for cfg in DATA_SOURCES:
                if cfg.filename == f.name:
                    comment = f"[{cfg.name}]"
                    found_config = True
                    break
            
            # 如果不在配置中，尝试动态解析
            if not found_config and wind_file_pattern.match(f.name):
                # 从文件名还原 symbol
                symbol = f.stem.replace('_', '.')
                
                # 只从缓存读取，不再调用 Wind API
                if symbol in cache_data:
                     comment = f"[{cache_data[symbol]}]"
            
            print(f"  [{current_idx}] {f.name:<20} {comment} ({size_kb:.1f} KB)")
            current_idx += 1
        print()
            
    if user_files:
        print("  --- 👤 用户手工提供 ---")
        for f in user_files:
            size_kb = f.stat().st_size / 1024
            print(f"  [{current_idx}] {f.name:<20} ({size_kb:.1f} KB)")
            current_idx += 1
    
    print(f"\n  [0] 退出\n")
    print(f"  提示: 输入多个序号可用空格或逗号分隔 (如: 1 2 3)\n")
    
    while True:
        try:
            raw_input = input("请输入序号: ").strip()
            if raw_input == '0':
                print("已退出")
                sys.exit(0)
            
            # 支持空格或逗号分隔
            parts = raw_input.replace(',', ' ').split()
            selected_files = []
            invalid_inputs = []
            
            for part in parts:
                try:
                    idx = int(part) - 1
                    if 0 <= idx < len(all_files):
                        selected_files.append(all_files[idx])
                    else:
                        invalid_inputs.append(part)
                except ValueError:
                    invalid_inputs.append(part)
            
            if invalid_inputs:
                print(f"❌ 无效的序号: {', '.join(invalid_inputs)}")
                continue
                
            if not selected_files:
                print("未选择任何文件")
                continue
                
            print(f"\n✅ 已选择 {len(selected_files)} 个文件:")
            for f in selected_files:
                print(f"  - {f.name}")
            print()
            return [str(f) for f in selected_files]
            
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
    
    # Step 1: 加载数据 (提前到这里以便使用数据中的名称来创建目录)
    print(f"\n[Step 1/4] 加载数据: {input_file}")
    from src.io import load_ohlc
    data = load_ohlc(input_file)
    print(f"  加载完成: {data}")
    print(f"  日期范围: {data.date_range[0].date()} ~ {data.date_range[1].date()}")

    # 从输入文件名生成基本文件名 (用于文件命名)
    input_path = Path(input_file)
    base_name = input_path.stem  # 不含扩展名的文件名，如 "TL.CFE"
    
    # 构建输出目录名称: Code_Name (e.g., 000510_SH_中证A500)
    # 替换名称中的非法字符
    import re
    safe_name = re.sub(r'[\\/*?:"<>|]', '_', data.name)
    safe_symbol = data.symbol.replace('.', '_')
    
    # 如果 symbol 和 name 相同，只用 symbol，否则 symbol_name
    if safe_name == safe_symbol or safe_name == data.symbol:
        dir_name = safe_symbol.lower()
    else:
        dir_name = f"{safe_symbol}_{safe_name}".lower() # 保持小写风格，虽然中文不会变小写
    
    # 创建ticker子目录
    ticker_processed_dir = DATA_PROCESSED_DIR / dir_name
    ticker_output_dir = OUTPUT_DIR / dir_name
    ticker_processed_dir.mkdir(parents=True, exist_ok=True)
    ticker_output_dir.mkdir(parents=True, exist_ok=True)
    
    # 输出路径
    processed_csv = ticker_processed_dir / f"{base_name}_processed.csv"
    merged_csv = ticker_processed_dir / f"{base_name}_merged.csv"
    strokes_csv = ticker_processed_dir / f"{base_name}_strokes.csv"
    merged_plot = ticker_output_dir / f"{base_name}_merged_kline.png"
    strokes_plot = ticker_output_dir / f"{base_name}_strokes.png"
    
    # Step 2: 处理原始数据，添加K线状态
    print(f"\n[Step 2/4] 添加 K 线状态标签...")
    from src.analysis import process_and_save
    process_and_save(data, str(processed_csv))
    
    # Step 3: K 线合并
    print(f"\n[Step 3/4] 合并包含关系的 K 线...")
    from src.analysis.merging import apply_kline_merging
    apply_kline_merging(str(processed_csv), str(merged_csv), 
                        save_plot_path=str(merged_plot))
    
    # Step 4: 分型识别（Al Brooks 风格，不做笔过滤）
    print(f"\n[Step 4/4] 识别顶底分型...")
    from src.analysis.fractals import process_fractals
    process_fractals(str(merged_csv), str(strokes_csv),
                    save_plot_path=str(strokes_plot))

    # Step 5: 生成交互式图表
    print(f"\n[Step 5/5] 生成交互式 HTML 图表...")
    from src.analysis import ChartBuilder, compute_ema
    interactive_plot = ticker_output_dir / f"{base_name}_interactive.html"
    
    # 重新加载数据以获取绘图所需的DataFrame
    import pandas as pd
    
    # 注意：这里我们使用合并后的数据来画图，因为它更干净
    # 但strokes是基于合并后数据的索引，所以是对齐的
    merged_df = pd.read_csv(merged_csv)
    # 转换 datetime
    merged_df['datetime'] = pd.to_datetime(merged_df['datetime'])
    
    # 读取 strokes
    strokes_df = pd.read_csv(strokes_csv)
    # 转换 strokes 为 [(idx, type)] 格式
    stroke_list = [
        (idx, row['valid_fractal']) 
        for idx, row in strokes_df.iterrows()
        if pd.notna(row['valid_fractal']) and row['valid_fractal'] != ''
    ]
    
    # 读取候选分型显示列 (candidate_display)
    # 格式为 3元组: (display_idx, type, display_idx) - 第三个元素用于兼容
    if 'candidate_display' in strokes_df.columns:
        for idx, row in strokes_df.iterrows():
            if pd.notna(row['candidate_display']) and row['candidate_display'] != '':
                # 可能有多个候选分型，用逗号分隔
                for marker_type in row['candidate_display'].split(','):
                    stroke_list.append((idx, marker_type.strip(), idx))
    
    # 计算技术指标
    merged_df['ema20'] = compute_ema(merged_df, 20)
    
    # 使用 ChartBuilder 构建图表
    chart = ChartBuilder(merged_df)
    chart.add_candlestick()
    chart.add_indicator('EMA20', merged_df['ema20'], '#FFA500')  # 橙色
    chart.add_strokes(stroke_list)
    chart.add_fractal_markers(stroke_list)
    
    # 设置标题: Name [Symbol]
    chart_title = f"{data.name} [{data.symbol}]"
    chart.build(str(interactive_plot), title=chart_title)
    
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
    # 默认数据文件
    DEFAULT_FILE = "data/raw/TB10Y.WI.xlsx"
    input_files = []
    
    # 支持命令行参数或交互式选择
    if len(sys.argv) > 1:
        # 命令行参数传入多个文件
        input_files = sys.argv[1:]
    elif sys.stdin.isatty():
        # 交互式终端，让用户选择
        input_files = select_file_interactive()
    else:
        # 非交互模式（如 agent 调用），使用默认文件
        print(f"非交互模式，使用默认文件: {DEFAULT_FILE}")
        input_files = [DEFAULT_FILE]
    
    # 批量处理
    total = len(input_files)
    for i, f in enumerate(input_files, 1):
        if total > 1:
            print("\n" + "#" * 60)
            print(f"正在处理第 {i}/{total} 个文件: {Path(f).name}")
            print("#" * 60)
        
        try:
            main(f)
        except Exception as e:
            print(f"\n❌ 处理失败 {f}: {e}")
            # 如果是批量处理，不要因为一个失败就退出全部（除非是严重错误）
            if total == 1:
                raise
