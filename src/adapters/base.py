"""
adapters/base.py
数据适配器基类，定义所有适配器必须实现的接口。
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Union

from ..data_schema import OHLCData


class DataAdapter(ABC):
    """
    数据适配器基类。
    
    所有具体适配器必须实现 load() 方法，将特定格式的原始数据
    转换为标准的 OHLCData 对象。
    """
    
    # 适配器名称，子类应覆盖
    name: str = "BaseAdapter"
    
    # 支持的文件扩展名列表
    supported_extensions: list[str] = []
    
    @abstractmethod
    def load(self, path: Union[str, Path]) -> OHLCData:
        """
        加载原始数据并转换为标准 OHLC 格式。
        
        Args:
            path: 数据文件路径
            
        Returns:
            OHLCData: 标准化的 OHLC 数据对象
            
        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 数据格式不正确
        """
        pass
    
    def can_handle(self, path: Union[str, Path]) -> bool:
        """
        检查此适配器是否能处理给定文件。
        
        默认实现基于文件扩展名检查，子类可覆盖以添加更复杂的检测逻辑。
        """
        path = Path(path)
        return path.suffix.lower() in self.supported_extensions
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}')"
