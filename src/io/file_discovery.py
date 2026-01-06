"""File discovery and selection utilities."""

import re
import sys
from pathlib import Path
from typing import List, Tuple

from .config_loader import load_api_config, load_security_cache

SUPPORTED_EXTENSIONS = {'.xlsx', '.xls', '.csv'}
WIND_FILE_PATTERN = re.compile(r'^[a-zA-Z0-9.]+_[a-zA-Z]+\.xlsx$', re.IGNORECASE)


def find_data_files(directory: Path) -> List[Path]:
    """Scan directory for supported data files."""
    if not directory.exists():
        return []
    
    files = []
    for ext in SUPPORTED_EXTENSIONS:
        files.extend(directory.glob(f'*{ext}'))
    return sorted(files, key=lambda x: x.name.lower())


def categorize_files(files: List[Path]) -> Tuple[List[Path], List[Path]]:
    """
    Categorize files into API-sourced and user-provided.
    
    Returns:
        Tuple of (api_files, user_files)
    """
    api_config = load_api_config()
    api_filenames = set(api_config.keys())
    
    api_files = []
    user_files = []
    
    for f in files:
        if f.name in api_filenames or WIND_FILE_PATTERN.match(f.name):
            api_files.append(f)
        else:
            user_files.append(f)
    
    return api_files, user_files


def display_file_menu(api_files: List[Path], user_files: List[Path]) -> None:
    """Display interactive file selection menu."""
    api_config = load_api_config()
    cache_data = load_security_cache()
    
    print("\n📂 请选择要处理的数据文件:\n")
    
    current_idx = 1
    
    if api_files:
        print("  --- 🌏 来自 Wind API ---")
        
        for f in api_files:
            size_kb = f.stat().st_size / 1024
            comment = ""
            
            if f.name in api_config:
                comment = f"[{api_config[f.name]}]"
            elif WIND_FILE_PATTERN.match(f.name):
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


def parse_user_selection(raw_input: str, all_files: List[Path]) -> List[Path]:
    """
    Parse user input and return selected files.
    
    Returns:
        List of selected file paths
    """
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
    
    return selected_files, invalid_inputs


def select_files_interactive(data_dir: Path) -> List[str]:
    """
    Interactive file selection.
    
    Returns:
        List of selected file paths as strings
    """
    files = find_data_files(data_dir)
    
    if not files:
        print(f"❌ 目录 '{data_dir}' 下没有找到可处理的数据文件")
        print(f"   支持的格式: {', '.join(SUPPORTED_EXTENSIONS)}")
        print(f"   请将数据文件放到 {data_dir}/ 目录下")
        sys.exit(1)
    
    if len(files) == 1:
        print(f"找到数据文件: {files[0].name}")
        return [str(files[0])]
    
    api_files, user_files = categorize_files(files)
    all_files = api_files + user_files
    
    display_file_menu(api_files, user_files)
    
    while True:
        try:
            raw_input = input("请输入序号: ").strip()
            if raw_input == '0':
                print("已退出")
                sys.exit(0)
            
            selected_files, invalid_inputs = parse_user_selection(raw_input, all_files)
            
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
