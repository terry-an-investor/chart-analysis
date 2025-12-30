#!/usr/bin/env python
"""
fetch_data.py
从 Wind API 获取数据并保存到 data/raw 目录。

用法:
    # 获取所有配置的数据源
    uv run fetch_data.py
    
    # 获取指定代码
    uv run fetch_data.py TL.CFE
    
    # 获取多个代码
    uv run fetch_data.py TL.CFE 000510.SH
    
    # 自定义日期范围
    uv run fetch_data.py --start 2023-01-01 --end 2024-12-30

要求:
    - Wind 金融终端已启动并登录
    - WindPy Python 接口已修复
"""

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目根目录到 path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.io.data_config import DATA_SOURCES, get_config, list_configs
from src.io.adapters.wind_api_adapter import WindAPIAdapter


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="从 Wind API 获取数据",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    uv run fetch_data.py                      # 获取所有数据
    uv run fetch_data.py TL.CFE               # 获取单个代码
    uv run fetch_data.py --list               # 列出所有可用代码
    uv run fetch_data.py --start 2023-01-01   # 自定义起始日期
        """
    )
    
    parser.add_argument(
        "symbols",
        nargs="*",
        help="要获取的 Wind 代码 (不指定则获取全部)"
    )
    
    parser.add_argument(
        "--start",
        type=str,
        default=None,
        help="起始日期 (YYYY-MM-DD)，默认2年前"
    )
    
    parser.add_argument(
        "--end",
        type=str,
        default=None,
        help="截止日期 (YYYY-MM-DD)，默认今天"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        default="data/raw",
        help="输出目录，默认 data/raw"
    )
    
    parser.add_argument(
        "--list",
        action="store_true",
        help="列出所有可用的数据代码"
    )
    
    return parser.parse_args()


def main():
    """主函数"""
    args = parse_args()
    
    # 列出配置
    if args.list:
        list_configs()
        return 0
    
    from src.io.data_config import DataConfig
    
    # 确定要获取的代码
    if args.symbols:
        configs = []
        for symbol in args.symbols:
            cfg = get_config(symbol)
            if cfg is None:
                # 如果是未知代码，创建一个默认配置
                print(f"  🔍 代码 {symbol} 不在预置配置中，将尝试自动识别...")
                cfg = DataConfig(
                    symbol=symbol,
                    name=symbol,  # 初始名称设为代码，后面连接后尝试解析
                    trading_calendar="SSE",  # 默认 A 股日历
                    description="自动添加的代码"
                )
            configs.append(cfg)
    else:
        configs = DATA_SOURCES
    
    # 默认日期范围: end_date 为昨天 (当前交易日未结束), start_date 为两年前
    yesterday = datetime.now() - timedelta(days=1)
    end_date = args.end or yesterday.strftime("%Y-%m-%d")
    
    if args.start:
        start_date = args.start
    else:
        # 默认从 end_date 往前推 2 年 (730天)
        # 注意: 这里简单按天数推算，Wind 的 ED-2Y 是按日历年
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        start_date = (end_dt - timedelta(days=730)).strftime("%Y-%m-%d")
    
    print("=" * 60)
    print("Wind API 数据获取")
    print("=" * 60)
    print(f"日期范围: {start_date} ~ {end_date}")
    print(f"输出目录: {args.output}")
    print(f"数据源数量: {len(configs)}")
    print("=" * 60)
    
    # 创建适配器
    adapter = WindAPIAdapter()
    
    success_count = 0
    failed = []
    
    try:
        for cfg in configs:
            # 如果名称和代码一致（说明是自动添加的代码），尝试解析真实名称
            if cfg.name == cfg.symbol:
                cfg.name = adapter.get_security_name(cfg.symbol)
            
            print(f"\n📊 {cfg.symbol} ({cfg.name})")
            try:
                adapter.fetch_and_save(
                    symbol=cfg.symbol,
                    output_dir=args.output,
                    start_date=start_date,
                    end_date=end_date,
                    fields=cfg.fields,
                    trading_calendar=cfg.trading_calendar,
                    name=cfg.name,
                )
                success_count += 1
            except Exception as e:
                print(f"  ❌ 失败: {e}")
                failed.append((cfg.symbol, str(e)))
    
    finally:
        # 断开连接
        adapter.disconnect()
    
    # 汇总
    print("\n" + "=" * 60)
    print("获取完成")
    print("=" * 60)
    print(f"成功: {success_count}/{len(configs)}")
    
    if failed:
        print("\n失败列表:")
        for symbol, error in failed:
            print(f"  - {symbol}: {error}")
    
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
