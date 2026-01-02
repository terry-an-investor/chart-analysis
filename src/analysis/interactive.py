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
        添加 K 线蜡烛图层
        
        Returns:
            self: 支持链式调用
        """
        for _, row in self.df.iterrows():
            self.candlestick_data.append({
                'time': self._timestamp(row['datetime']),
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close']),
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
    
    def add_structure_levels(
        self, 
        major_high: pd.Series, 
        major_low: pd.Series,
        swing_types: Optional[pd.Series] = None,
        swing_high_prices: Optional[pd.Series] = None,
        swing_low_prices: Optional[pd.Series] = None,
        swing_window: int = 5,
    ) -> 'ChartBuilder':
        """
        添加市场结构层级 (Major High/Low 阶梯线 + Swing 标记)
        
        关键设计：可视化时"恢复滞后"
        - structure.py 中确认时刻在 Index=T+window
        - 但可视化标记应该放回到实际极值点 Index=T
        - 阶梯线也从 Index=T 开始显示新的 level
        
        Args:
            major_high: Major High 价格序列 (前向填充的阶梯数据)
            major_low: Major Low 价格序列
            swing_types: Swing Point 类型 (HH, HL, LH, LL, DT, DB)
            swing_high_prices: 确认时刻记录的 Swing High 价格
            swing_low_prices: 确认时刻记录的 Swing Low 价格
            swing_window: 摆动点确认窗口 (用于恢复滞后)
        
        Returns:
            self: 支持链式调用
        """
        n = len(self.df)
        
        # -------------------------------------------------------------------------
        # 1. Major High/Low 阶梯线 (诚实滞后版)
        # 不做 shift，线条在确认时刻 (T+window) 才变化，模拟真实交易体验
        # -------------------------------------------------------------------------
        
        # 直接使用原始数据，不做提前处理
        adjusted_major_high = major_high
        adjusted_major_low = major_low
        
        # 绘制 Major High 阶梯线 (红色)
        major_high_data = []
        for i, (orig_idx, row) in enumerate(self.df.iterrows()):
            try:
                value = adjusted_major_high.loc[orig_idx] if orig_idx in adjusted_major_high.index else None
            except:
                value = adjusted_major_high.iloc[i] if i < len(adjusted_major_high) else None
            
            if pd.notna(value):
                major_high_data.append({
                    'time': self._timestamp(row['datetime']),
                    'value': float(value)
                })
        
        if major_high_data:
            self.indicators.append({
                'name': 'Major High',
                'data': major_high_data,
                'color': '#FF5252',
                'lineWidth': 1,
                'lineStyle': 2
            })
        
        # 绘制 Major Low 阶梯线 (绿色)
        major_low_data = []
        for i, (orig_idx, row) in enumerate(self.df.iterrows()):
            try:
                value = adjusted_major_low.loc[orig_idx] if orig_idx in adjusted_major_low.index else None
            except:
                value = adjusted_major_low.iloc[i] if i < len(adjusted_major_low) else None
            
            if pd.notna(value):
                major_low_data.append({
                    'time': self._timestamp(row['datetime']),
                    'value': float(value)
                })
        
        if major_low_data:
            self.indicators.append({
                'name': 'Major Low',
                'data': major_low_data,
                'color': '#69F0AE',
                'lineWidth': 1,
                'lineStyle': 2
            })
        
        # -------------------------------------------------------------------------
        # 2. Swing Point 标记 (诚实滞后版)
        # 标记显示在确认时刻，不做回溯，与实盘体验一致
        # -------------------------------------------------------------------------
        if swing_types is not None:
            for i, (orig_idx, row) in enumerate(self.df.iterrows()):
                try:
                    swing_type = swing_types.loc[orig_idx] if orig_idx in swing_types.index else None
                except (KeyError, TypeError):
                    swing_type = swing_types.iloc[i] if i < len(swing_types) else None
                
                if pd.isna(swing_type) or swing_type is None:
                    continue
                
                # 诚实滞后版：标记直接显示在确认时刻的 K 线上
                # 根据类型确定位置和颜色
                if swing_type in ('HH', 'LH', 'DT'):
                    position = 'aboveBar'
                    color_map = {'HH': '#00E676', 'LH': '#FF8A80', 'DT': '#FFD54F'}
                else:
                    position = 'belowBar'
                    color_map = {'HL': '#00E676', 'LL': '#FF8A80', 'DB': '#FFD54F'}
                
                color = color_map.get(swing_type, '#FFFFFF')
                
                self.markers.append({
                    'time': self._timestamp(row['datetime']),
                    'position': position,
                    'color': color,
                    'shape': 'circle',
                    'text': swing_type,
                    'size': 1
                })
        
        return self
    
    def add_reversal_markers(
        self,
        consecutive_bear_start: pd.Series,
        consecutive_bull_start: pd.Series,
        consecutive_top_price: pd.Series,
        consecutive_bottom_price: pd.Series,
    ) -> 'ChartBuilder':
        """
        添加渐进式反转标记 (Consecutive Reversal Markers)
        
        在确认连续 N 根同向 K 线时，标记回溯的顶/底部价格
        """
        for i, (orig_idx, row) in enumerate(self.df.iterrows()):
            # Bear Top (连续阴线确认的顶部)
            try:
                is_bear_top = consecutive_bear_start.loc[orig_idx] if orig_idx in consecutive_bear_start.index else False
            except:
                is_bear_top = consecutive_bear_start.iloc[i] if i < len(consecutive_bear_start) else False
            
            if is_bear_top:
                self.markers.append({
                    'time': self._timestamp(row['datetime']),
                    'position': 'aboveBar',
                    'color': '#FF1744',  # 亮红色
                    'shape': 'arrowDown',
                    'text': '▼',
                    'size': 2
                })
            
            # Bull Bottom (连续阳线确认的底部)
            try:
                is_bull_bot = consecutive_bull_start.loc[orig_idx] if orig_idx in consecutive_bull_start.index else False
            except:
                is_bull_bot = consecutive_bull_start.iloc[i] if i < len(consecutive_bull_start) else False
            
            if is_bull_bot:
                self.markers.append({
                    'time': self._timestamp(row['datetime']),
                    'position': 'belowBar',
                    'color': '#00E676',  # 亮绿色
                    'shape': 'arrowUp',
                    'text': '▲',
                    'size': 2
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
        
        # 使用 Jinja2 渲染模板
        from jinja2 import Template
        with open(template_path, 'r', encoding='utf-8') as f:
            template = Template(f.read())
        
        html_content = template.render(
            title=title,
            candlestick_json=candlestick_json,
            indicators_json=indicators_json,
            strokes_json=strokes_json,
            markers_json=markers_json,
            precision=precision
        )
        
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


def plot_bar_features_chart(
    df: pd.DataFrame,
    save_path: str,
    title: Optional[str] = None,
) -> None:
    """
    绘制带有 Bar Features 的交互式图表
    
    主图显示 OHLC 蜡烛图，副图显示 bar_features 指标:
    - body_pct: 实体占比
    - clv: 收盘位置
    - signed_body: 带符号实体比
    - upper_tail_pct: 上影线占比
    - lower_tail_pct: 下影线占比
    
    Args:
        df: 包含 datetime, open, high, low, close 的 DataFrame
        save_path: HTML 保存路径
        title: 图表标题
    
    Example:
        >>> from src.io import load_ohlc
        >>> from src.analysis import plot_bar_features_chart
        >>> ohlc = load_ohlc('data/raw/000510_SH.xlsx')
        >>> plot_bar_features_chart(ohlc.df, 'output/bar_features.html')
    """
    from .bar_features import compute_bar_features
    
    # 确保 datetime 列存在且是 datetime 类型
    df = df.copy()
    if 'datetime' in df.columns:
        df['datetime'] = pd.to_datetime(df['datetime'])
    
    # 计算 bar features
    features = compute_bar_features(df)
    
    # 动态检测价格精度
    series = df['close']
    precision = 2
    for decimals in range(2, 5):
        rounded = series.round(decimals)
        if (series - rounded).abs().max() < 1e-9:
            precision = decimals
            break
    
    # 构建 OHLC 数据
    candlestick_data = []
    for _, row in df.iterrows():
        ts = int(pd.Timestamp(row['datetime']).timestamp())
        candlestick_data.append({
            'time': ts,
            'open': float(row['open']),
            'high': float(row['high']),
            'low': float(row['low']),
            'close': float(row['close']),
        })
    
    # 构建 features 数据 (使用当前 bar_features.py 中的特征)
    features_data = {}
    feature_cols = ['body_pct', 'clv', 'signed_body', 'upper_tail_pct', 'lower_tail_pct']
    for col in feature_cols:
        if col in features.columns:
            features_data[col] = [
                None if pd.isna(v) else float(v) 
                for v in features[col].tolist()
            ]
    
    # 生成标题
    if title is None:
        symbol = df['symbol'].iloc[0] if 'symbol' in df.columns else ''
        title = f'Bar Features - {symbol}'
    
    # 序列化为 JSON
    candlestick_json = json.dumps(candlestick_data)
    features_json = json.dumps(features_data)
    
    # 加载模板
    template_path = Path(__file__).parent / 'templates' / 'bar_features_template.html'
    
    # 使用 Jinja2 渲染模板
    from jinja2 import Template
    with open(template_path, 'r', encoding='utf-8') as f:
        template = Template(f.read())
    
    html_content = template.render(
        title=title,
        candlestick_json=candlestick_json,
        features_json=features_json,
        precision=precision
    )
    
    # 保存文件
    Path(save_path).parent.mkdir(parents=True, exist_ok=True)
    with open(save_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"Bar Features 图表已保存至: {save_path}")


def plot_structure_chart(
    df: pd.DataFrame,
    save_path: Optional[str] = None,
    swing_window: int = 5,
    title: Optional[str] = None,
    symbol: Optional[str] = None,
) -> None:
    """
    绘制带有市场结构 (Market Structure) 的交互式图表
    
    主图显示:
    - OHLC 蜡烛图
    - Major High/Low 阶梯线 (结构性阻力/支撑位)
    - Swing Point 标记 (HH/HL/LH/LL/DT/DB)
    - EMA20 指标线
    
    Args:
        df: 包含 datetime, open, high, low, close 的 DataFrame
        save_path: HTML 保存路径，默认为 output/structure/{symbol}_structure.html
        swing_window: 摆动点确认周期 (默认 5)
        title: 图表标题
    
    Example:
        >>> from src.io import load_ohlc
        >>> from src.analysis import plot_structure_chart
        >>> ohlc = load_ohlc('data/raw/600519_SH.xlsx')
        >>> plot_structure_chart(ohlc.df)  # 自动保存到 output/structure/
    """
    from .structure import compute_market_structure
    from .indicators import compute_ema
    
    # 确保 datetime 列存在且是 datetime 类型
    df = df.copy()
    if 'datetime' in df.columns:
        df['datetime'] = pd.to_datetime(df['datetime'])
    
    # 计算市场结构
    structure = compute_market_structure(df, swing_window=swing_window)
    
    # 计算 EMA20 (compute_ema 接受 DataFrame)
    ema20 = compute_ema(df, period=20)
    
    # 获取 symbol 用于生成默认路径和标题
    if symbol is None:
        symbol = df['symbol'].iloc[0] if 'symbol' in df.columns else 'unknown'
    
    # 生成默认保存路径 (保存到股票自己的子目录下，与其他输出保持一致)
    if save_path is None:
        # 格式: output/{symbol_lowercase}/{SYMBOL}_structure.html
        symbol_lower = symbol.lower().replace('.', '_')
        symbol_upper = symbol.upper().replace('.', '_')
        save_path = f'output/{symbol_lower}/{symbol_upper}_structure.html'
    
    # 生成标题
    if title is None:
        title = f'Market Structure - {symbol}'
    
    # 构建图表
    chart = ChartBuilder(df)
    chart.add_candlestick()
    chart.add_indicator('EMA20', ema20, '#FFA500', line_width=1)
    chart.add_structure_levels(
        major_high=structure['major_high'],
        major_low=structure['major_low'],
        swing_types=structure['swing_type'],
        swing_high_prices=structure['swing_high_price'],
        swing_low_prices=structure['swing_low_price'],
        swing_window=swing_window,  # 传入用于恢复滞后
    )
    chart.build(save_path, title=title)

