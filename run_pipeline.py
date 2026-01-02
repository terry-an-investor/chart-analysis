"""
run_pipeline.py
驱动 K 线分析流水线的入口脚本。

流程:
1. 加载数据    - 使用 data_loader 自动适配数据源
2. 生成交互式图表 - 原始 OHLC 蜡烛图 + EMA20
3. 生成 Bar Features 图表 - 单 K 线特征可视化

用法:
    uv run run_pipeline.py              # 交互式选择数据文件
    uv run run_pipeline.py data/raw/TL.CFE.xlsx  # 直接指定文件
    
输出文件:
    - output/{ticker}/*_interactive.html  (交互式 OHLC 图表)
    - output/{ticker}/*_bar_features.html (K线特征图表)
"""

import sys
import re
import json
from pathlib import Path

import pandas as pd

# 确保 src 模块可导入
sys.path.insert(0, str(Path(__file__).parent))

# 目录配置
DATA_RAW_DIR = Path("data/raw")
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


def _get_api_filenames() -> dict[str, str]:
    """
    轻量级读取 API 配置文件名（避免导入 pandas）。
    
    Returns:
        dict: {filename: name} 映射，如 {"TL_CFE.xlsx": "30年期国债期货"}
    """
    import ast
    config_path = Path(__file__).parent / "src" / "io" / "data_config.py"
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            source = f.read()
        tree = ast.parse(source)
        
        result = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == 'DATA_SOURCES':
                        if isinstance(node.value, ast.List):
                            for elt in node.value.elts:
                                if isinstance(elt, ast.Call):
                                    symbol = name = None
                                    for kw in elt.keywords:
                                        if kw.arg == 'symbol' and isinstance(kw.value, ast.Constant):
                                            symbol = kw.value.value
                                        if kw.arg == 'name' and isinstance(kw.value, ast.Constant):
                                            name = kw.value.value
                                    if symbol:
                                        filename = symbol.replace('.', '_') + '.xlsx'
                                        result[filename] = name or symbol
        return result
    except Exception:
        return {}


def select_file_interactive() -> list[str]:
    """交互式选择数据文件 (支持多选)"""
    api_config = _get_api_filenames()
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
    api_filenames = set(api_config.keys())
    api_files = []
    user_files = []
    
    wind_file_pattern = re.compile(r'^[a-zA-Z0-9.]+_[a-zA-Z]+\.xlsx$', re.IGNORECASE)
    
    for f in files:
        if f.name in api_filenames or wind_file_pattern.match(f.name):
            api_files.append(f)
        else:
            user_files.append(f)
            
    all_files = api_files + user_files
    
    print("\n📂 请选择要处理的数据文件:\n")
    
    current_idx = 1
    
    if api_files:
        print("  --- 🌏 来自 Wind API ---")
        
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
            comment = ""
            found_config = False
            if f.name in api_config:
                comment = f"[{api_config[f.name]}]"
                found_config = True
            
            if not found_config and wind_file_pattern.match(f.name):
                symbol = f.stem.replace('_', '.')
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
    print("K 线分析流水线 (Bar Features)")
    print("=" * 60)
    
    # 确保输出目录存在
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Step 1: 加载数据
    print(f"\n[Step 1/2] 加载数据: {input_file}")
    from src.io import load_ohlc
    data = load_ohlc(input_file)
    print(f"  加载完成: {data}")
    print(f"  日期范围: {data.date_range[0].date()} ~ {data.date_range[1].date()}")

    # 从输入文件名生成基本文件名
    input_path = Path(input_file)
    base_name = input_path.stem
    
    # 构建输出目录名称
    safe_name = re.sub(r'[\\/*?:"<>|]', '_', data.name)
    safe_symbol = data.symbol.replace('.', '_')
    
    if safe_name == safe_symbol or safe_name == data.symbol:
        dir_name = safe_symbol.lower()
    else:
        dir_name = f"{safe_symbol}_{safe_name}".lower()
    
    # 创建 ticker 子目录
    ticker_output_dir = OUTPUT_DIR / dir_name
    ticker_output_dir.mkdir(parents=True, exist_ok=True)
    
    # Step 2: 生成市场结构图表 (Structure Chart)
    print(f"\n[Step 2/2] 生成市场结构交互式图表...")
    from src.analysis import plot_structure_chart
    
    structure_plot = ticker_output_dir / f"{base_name}_structure.html"
    plot_structure_chart(
        data.df, 
        save_path=str(structure_plot),
        swing_window=5,
        title=f"{data.name} - Market Structure"
    )
    
    # # [已注释] 生成原始交互式图表 (OHLC + EMA20)
    # from src.analysis import ChartBuilder, compute_ema
    # interactive_plot = ticker_output_dir / f"{base_name}_interactive.html"
    # raw_df = data.df.copy()
    # raw_df['datetime'] = pd.to_datetime(raw_df['datetime'])
    # raw_df['ema20'] = compute_ema(raw_df, 20)
    # chart = ChartBuilder(raw_df)
    # chart.add_candlestick()
    # chart.add_indicator('EMA20', raw_df['ema20'], '#FFA500')
    # chart_title = f"{data.name} [{data.symbol}]"
    # chart.build(str(interactive_plot), title=chart_title)
    
    # # [已注释] 生成 Bar Features 图表
    # from src.analysis import plot_bar_features_chart
    # bar_features_plot = ticker_output_dir / f"{base_name}_bar_features.html"
    # plot_bar_features_chart(data.df, str(bar_features_plot), title=f"{data.name} - Bar Features")
    
    print("\n" + "=" * 60)
    print("流水线完成！")
    print("=" * 60)
    print("生成文件:")
    print(f"  - {structure_plot}  (市场结构图表)")


if __name__ == "__main__":
    DEFAULT_FILE = "data/raw/TB10Y.WI.xlsx"
    input_files = []
    
    if len(sys.argv) > 1:
        input_files = sys.argv[1:]
    elif sys.stdin.isatty():
        input_files = select_file_interactive()
    else:
        print(f"非交互模式，使用默认文件: {DEFAULT_FILE}")
        input_files = [DEFAULT_FILE]
    
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
            if total == 1:
                raise
