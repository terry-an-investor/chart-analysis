"""
interactive.py
交互式 K 线图表模块 (TradingView Lightweight Charts)

使用 TradingView 的开源 Lightweight Charts 库生成专业级交互式图表，支持：
- K 线蜡烛图 (专业 TradingView 风格)
- 技术指标叠加 (EMA, SMA, etc.)
- 笔连线和分型标注
- 内置 Crosshair、时间轴导航
- 自动 Y 轴缩放
"""

import json
import pandas as pd
from typing import List, Tuple, Optional
from pathlib import Path


# 预定义的指标颜色映射
INDICATOR_COLORS = {
    'ema5': '#FF6B6B',
    'ema10': '#4ECDC4',
    'ema20': '#FFA500',
    'ema50': '#45B7D1',
    'ema200': '#96CEB4',
    'sma5': '#FFEAA7',
    'sma10': '#DFE6E9',
    'sma20': '#74B9FF',
}


class ChartBuilder:
    """
    交互式图表构建器 (TradingView Lightweight Charts)
    
    使用链式调用模式构建图表：
    
    Example:
        chart = ChartBuilder(df)
        chart.add_candlestick()
        chart.add_indicator('EMA20', df['ema20'], '#FFA500')
        chart.add_strokes(stroke_list)
        chart.add_fractal_markers(stroke_list)
        chart.build('output/chart.html')
    """
    
    def __init__(self, df: pd.DataFrame):
        """
        初始化图表构建器
        
        Args:
            df: 包含 datetime, open, high, low, close 的 DataFrame
        """
        self.df = df.copy()
        self.candlestick_data = []
        self.indicators = []  # [(name, data, color), ...]
        self.stroke_lines = []  # 笔的线段数据
        self.markers = []  # 标记点数据
        
        # 确保 datetime 列存在且是 datetime 类型
        if 'datetime' in self.df.columns:
            self.df['datetime'] = pd.to_datetime(self.df['datetime'])
        
        # 动态检测价格精度 (根据数据的实际小数位数)
        self.precision = self._detect_precision()
    
    def _detect_precision(self, max_decimals=4, min_decimals=2) -> int:
        """检测数据需要的最小精度"""
        series = self.df['close']
        for decimals in range(min_decimals, max_decimals + 1):
            rounded = series.round(decimals)
            if (series - rounded).abs().max() < 1e-9:
                return decimals
        return max_decimals
    
    def _timestamp(self, dt) -> int:
        """将 datetime 转换为 Unix 时间戳 (秒)"""
        return int(pd.Timestamp(dt).timestamp())
    
    def add_candlestick(self) -> 'ChartBuilder':
        """
        添加收盘价线图层 (原为K线蜡烛图)
        
        Returns:
            self: 支持链式调用
        """
        for _, row in self.df.iterrows():
            self.candlestick_data.append({
                'time': self._timestamp(row['datetime']),
                'value': float(row['close']),
            })
        return self
    
    def add_indicator(
        self, 
        name: str, 
        series: pd.Series, 
        color: Optional[str] = None,
        line_width: int = 2
    ) -> 'ChartBuilder':
        """
        添加技术指标线
        
        Args:
            name: 指标名称 (如 'EMA20')
            series: 指标数据序列
            color: 线条颜色，None 则自动选择
            line_width: 线条宽度
        
        Returns:
            self: 支持链式调用
        """
        if color is None:
            color = INDICATOR_COLORS.get(name.lower(), '#FFFFFF')
        
        data = []
        for i, (_, row) in enumerate(self.df.iterrows()):
            value = series.iloc[i]
            if pd.notna(value):
                data.append({
                    'time': self._timestamp(row['datetime']),
                    'value': float(value)
                })
        
        self.indicators.append({
            'name': name,
            'data': data,
            'color': color,
            'lineWidth': line_width
        })
        return self
    
    def add_strokes(self, strokes: List[Tuple[int, str]]) -> 'ChartBuilder':
        """
        添加笔连线
        
        Args:
            strokes: 分型标记列表 [(index, 'T'|'B'), ...]
                     注意：只接受纯 'T' 或 'B'，忽略 'Tx', 'Bx' 等
        
        Returns:
            self: 支持链式调用
        """
        if not strokes:
            return self
        
        # 【关键】只筛选有效的 T 和 B (忽略 Tx, Bx, Tc, Bc 等)
        valid_strokes = []
        for marker in strokes:
            if len(marker) == 3:
                idx, f_type, _ = marker
            else:
                idx, f_type = marker
            if f_type in ('T', 'B'):
                valid_strokes.append((idx, f_type))
        
        if not valid_strokes:
            return self
        
        # 按索引排序
        sorted_strokes = sorted(valid_strokes, key=lambda x: x[0])
        
        # 构建笔的线段数据
        stroke_data = []
        for idx, f_type in sorted_strokes:
            if idx < 0 or idx >= len(self.df):
                continue
            row = self.df.iloc[idx]
            price = float(row['high']) if f_type == 'T' else float(row['low'])
            stroke_data.append({
                'time': self._timestamp(row['datetime']),
                'value': price
            })
        
        self.stroke_lines = stroke_data
        return self
    
    def add_fractal_markers(self, fractals: List[Tuple[int, str]]) -> 'ChartBuilder':
        """
        添加分型标记 (Tc/Bc)
        
        Args:
            fractals: 分型标记列表 [(index, 'Tc'|'Bc'), ...]
                      - Tc: 顶分型候选 (Top Candidate)
                      - Bc: 底分型候选 (Bottom Candidate)
        
        显示规则:
            - 直接显示 Tc 和 Bc 标记
            - 不进行 Hn/Ln 计数
        
        Returns:
            self: 支持链式调用
        """
        # 1. 预处理: 提取候选分型并去重
        processed_markers = []
        for marker in fractals:
            if len(marker) == 3:
                display_idx, f_type, _ = marker
            else:
                display_idx, f_type = marker
            
            # 只处理候选分型 (Tc/Bc) - 当前已禁用
            if False and 'c' in f_type and 0 <= display_idx < len(self.df):
                processed_markers.append((display_idx, f_type))
        
        # 去重并按索引排序
        processed_markers = sorted(set(processed_markers), key=lambda x: x[0])
        
        # 2. 标记逻辑 (Tc/Bc)
        # 不再使用 Hn/Ln 计数，直接显示原始分型标记
        
        for display_idx, f_type in processed_markers:
            # display_idx 是右肩 K 线的索引（信号确认的位置）
            # 分型中间 K 线的索引 = display_idx - 1
            fractal_center_idx = display_idx - 1
            if fractal_center_idx < 0:
                continue  # 安全检查
            
            # 获取中间 K 线的数据用于定位
            center_row = self.df.iloc[fractal_center_idx]
            base_type = f_type.replace('c', '')  # 'Tc' -> 'T', 'Bc' -> 'B'
            
            if base_type == 'T':
                # Top 分型 -> Tc (标在中间K线)
                label = 'Tc'
                color = '#e040fb'  # 亮紫色
                self.markers.append({
                    'time': self._timestamp(center_row['datetime']),
                    'position': 'aboveBar',
                    'color': color,
                    'shape': 'circle',
                    'text': label
                })
                
            elif base_type == 'B':
                # Bottom 分型 -> Bc (标在中间K线)
                label = 'Bc'
                color = '#ff4081'  # 粉红色
                self.markers.append({
                    'time': self._timestamp(center_row['datetime']),
                    'position': 'belowBar',
                    'color': color,
                    'shape': 'circle',
                    'text': label
                })
        
        return self
    
    def build(self, save_path: str, title: Optional[str] = None) -> None:
        """
        组装并保存为 HTML
        
        Args:
            save_path: HTML 文件保存路径
            title: 图表标题
        """
        if title is None:
            symbol = self.df['symbol'].iloc[0] if 'symbol' in self.df.columns else ''
            title = f'Fractal Analysis - {symbol}'
        
        # 动态检测价格精度
        precision = self._detect_precision()
        
        # 序列化数据为 JSON
        candlestick_json = json.dumps(self.candlestick_data)
        indicators_json = json.dumps(self.indicators)
        strokes_json = json.dumps(self.stroke_lines)
        markers_json = json.dumps(self.markers)
        
        # 加载模板文件
        template_path = Path(__file__).parent / 'templates' / 'chart_template.html'
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
        
        # 使用 str.replace() 替换占位符 (避免与 JS 模板字符串冲突)
        html_content = template_content
        html_content = html_content.replace('{{title}}', title)
        html_content = html_content.replace('{{candlestick_json}}', candlestick_json)
        html_content = html_content.replace('{{indicators_json}}', indicators_json)
        html_content = html_content.replace('{{strokes_json}}', strokes_json)
        html_content = html_content.replace('{{markers_json}}', markers_json)
        html_content = html_content.replace('{{precision}}', str(precision))
        
        # 保存文件
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"交互式图表已保存至: {save_path}")


# ============================================================
# 向后兼容的函数接口
# ============================================================

def plot_interactive_kline(
    df: pd.DataFrame, 
    strokes: List[Tuple[int, str]], 
    save_path: str = None
) -> None:
    """
    绘制交互式 K 线图 - 向后兼容函数
    
    Args:
        df: 包含 datetime, open, high, low, close 的 DataFrame
        strokes: 分型标记 list of (index, type)，如 [(10, 'T'), (15, 'B')]
        save_path: HTML 保存路径
    
    Note:
        此函数保留以兼容旧代码，新代码建议使用 ChartBuilder 类。
    """
    chart = ChartBuilder(df)
    chart.add_candlestick()
    chart.add_strokes(strokes)
    chart.add_fractal_markers(strokes)
    
    if save_path:
        chart.build(save_path)
