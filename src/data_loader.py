"""
data_loader.py
统一数据加载入口，自动选择合适的适配器加载数据。

用法:
    from src.data_loader import load_ohlc
    
    # 自动检测适配器
    data = load_ohlc("data/raw/TL.CFE.xlsx")
    
    # 指定适配器
    data = load_ohlc("data/raw/TL.CFE.xlsx", adapter="wind_cfe")
"""

from pathlib import Path
from typing import Union, Optional

from .data_schema import OHLCData
from .adapters import WindCFEAdapter
from .adapters.base import DataAdapter


# 注册所有可用的适配器
ADAPTERS: dict[str, DataAdapter] = {
    "wind_cfe": WindCFEAdapter(),
}


def load_ohlc(
    path: Union[str, Path],
    adapter: Optional[str] = None
) -> OHLCData:
    """
    加载 OHLC 数据的统一入口。
    
    Args:
        path: 数据文件路径
        adapter: 适配器名称。如果为 None，则自动检测合适的适配器。
                可选值: 'wind_cfe'
    
    Returns:
        OHLCData: 标准化的 OHLC 数据
        
    Raises:
        ValueError: 无法找到合适的适配器
        FileNotFoundError: 文件不存在
    """
    path = Path(path)
    
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {path}")
    
    # 如果指定了适配器
    if adapter is not None:
        if adapter not in ADAPTERS:
            raise ValueError(
                f"未知适配器: '{adapter}'，可用: {list(ADAPTERS.keys())}"
            )
        selected_adapter = ADAPTERS[adapter]
        print(f"使用指定适配器: {selected_adapter.name}")
        return selected_adapter.load(path)
    
    # 自动检测适配器
    for name, adp in ADAPTERS.items():
        if adp.can_handle(path):
            print(f"自动选择适配器: {adp.name}")
            return adp.load(path)
    
    raise ValueError(
        f"无法找到处理 '{path}' 的适配器，文件扩展名: {path.suffix}"
    )


def list_adapters() -> list[str]:
    """列出所有可用的适配器名称"""
    return list(ADAPTERS.keys())


def register_adapter(name: str, adapter: DataAdapter) -> None:
    """注册新的适配器"""
    ADAPTERS[name] = adapter
    print(f"已注册适配器: {name} -> {adapter}")
