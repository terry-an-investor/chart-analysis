"""
io/loader.py
统一数据加载入口，自动选择合适的适配器加载数据。

用法:
    from src.io import load_ohlc

    # 自动检测适配器
    data = load_ohlc("data/raw/TL.CFE.xlsx")

    # 指定适配器
    data = load_ohlc("data/raw/TL.CFE.xlsx", adapter="wind_cfe")
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from .adapters import StandardAdapter, WindCFEAdapter
from .adapters.base import DataAdapter
from .schema import OHLCData

logger = logging.getLogger(__name__)


# 注册所有可用的适配器 (顺序很重要，Standard 优先检测)
ADAPTERS: dict[str, DataAdapter] = {
    "standard": StandardAdapter(),
    "wind_cfe": WindCFEAdapter(),
}


def load_ohlc(path: str | Path, adapter: Optional[str] = None) -> OHLCData:
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
        logger.error(f"文件不存在: {path}")
        raise FileNotFoundError(f"文件不存在: {path}")

    logger.info(f"加载数据文件: {path.name}")

    # 如果指定了适配器
    if adapter is not None:
        if adapter not in ADAPTERS:
            logger.error(f"未知适配器: '{adapter}'，可用: {list(ADAPTERS.keys())}")
            raise ValueError(f"未知适配器: '{adapter}'，可用: {list(ADAPTERS.keys())}")
        selected_adapter = ADAPTERS[adapter]
        logger.info(f"使用指定适配器: {selected_adapter.name}")
        return selected_adapter.load(path)

    # 自动检测适配器
    for name, adp in ADAPTERS.items():
        if adp.can_handle(path):
            logger.info(f"自动选择适配器: {adp.name}")
            data = adp.load(path)
            logger.info(f"成功加载数据: {len(data.df)} rows")
            return data

    logger.error(f"无法找到处理 '{path}' 的适配器，文件扩展名: {path.suffix}")
    raise ValueError(f"无法找到处理 '{path}' 的适配器，文件扩展名: {path.suffix}")


def list_adapters() -> list[str]:
    """列出所有可用的适配器名称"""
    return list(ADAPTERS.keys())


def register_adapter(name: str, adapter: DataAdapter) -> None:
    """注册新的适配器"""
    ADAPTERS[name] = adapter
    print(f"已注册适配器: {name} -> {adapter}")
