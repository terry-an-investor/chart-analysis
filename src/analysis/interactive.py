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
        添加顶底分型标记
        
        Args:
            fractals: 分型标记列表 [(index, 'T'|'B'|'Tx'|'Bx'|'Tc'|'Bc'), ...]
                      - T/B: 已确认分型
                      - Tx/Bx: 被替换的分型
                      - Tc/Bc: 候选分型 (尚未确认，低滞后)
        
        Returns:
            self: 支持链式调用
        """
        # 1. 预处理所有标记，转换为统一格式 (index, type) 并排序
        # 注意: 这里 index 是 `display_idx` (显示位置)
        processed_markers = []
        for marker in fractals:
            if len(marker) == 3:
                display_idx, f_type, _ = marker
            else:
                display_idx, f_type = marker
            
            if 0 <= display_idx < len(self.df):
                processed_markers.append((display_idx, f_type))
        
            if 0 <= display_idx < len(self.df):
                processed_markers.append((display_idx, f_type))
        
        # 去重: 确保每个位置每种类型的标记只出现一次
        processed_markers = list(set(processed_markers))
        
        # 按索引排序，确保计数逻辑正确 (从左到右)
        processed_markers.sort(key=lambda x: x[0])
        
        # 2. H/L 计数逻辑
        h_count = 0  # H1, H2, H3... (Buy setups in Leg Down)
        l_count = 0  # L1, L2, L3... (Sell setups in Leg Up)
        
        last_h_idx = -999
        last_l_idx = -999
        
        processed_markers.sort(key=lambda x: x[0])
        
        for display_idx, f_type in processed_markers:
            row = self.df.iloc[display_idx]
            base_type = f_type.replace('x', '').replace('c', '')
            is_candidate = 'c' in f_type
            is_cancelled = 'x' in f_type
            is_confirmed = not is_candidate and not is_cancelled # T/B
            
            # --- 计数重置逻辑 (互斥重置) ---
            # 我们不再依赖 T/B 分型，而是依赖信号的触发来重置对手方的计数
            # 只有当信号真正触发时，才重置对手方
            
            # --- 候选标记逻辑 ---
            # 只处理候选分型 (用户请求：只显示 Hx/Lx)
            if is_candidate:
                # 信号确认逻辑：
                # Hx (Bc): (Next High > Sig High AND Next Close > Sig Close) OR (Signal Bar is Strong)
                # Lx (Tc): (Next Low < Sig Low AND Next Close < Sig Close) OR (Signal Bar is Strong)
                
                # display_idx 是信号K线 (Signal Bar) 的索引
                next_bar_idx = display_idx + 1
                has_next_bar = next_bar_idx < len(self.df)
                
                # 判断信号线本身是否强势 (Strong Signal Bar)
                # 强势定义: 收盘价在极值附近 (顶分型收在低位，底分型收在高位)
                # 并且实体有一定长度 (避免十字星)
                s_high = float(row['high'])
                s_low = float(row['low'])
                s_close = float(row['close'])
                s_open = float(row['open'])
                s_range = s_high - s_low
                
                is_strong = False
                if s_range > 0:
                    if base_type == 'T':
                        # 顶分型: 收盘在底部 1/3，且是阴线(或实体很小的假阳)
                        pos = (s_close - s_low) / s_range
                        if pos < 0.33:
                            is_strong = True
                    elif base_type == 'B':
                        # 底分型: 收盘在顶部 1/3
                        pos = (s_close - s_low) / s_range
                        if pos > 0.66:
                            is_strong = True

                triggered = False
                
                if base_type == 'T':
                    # --- L Setup (Sell) ---
                    # 1. Strong Signal Exception
                    if is_strong:
                        triggered = True
                    # 2. Next Bar Confirmation
                    elif has_next_bar:
                        next_bar = self.df.iloc[next_bar_idx]
                        next_low = float(next_bar['low'])
                        next_close = float(next_bar['close'])
                        # 严格条件：Next Low < Signal Low (突破) AND Next Close < Signal Close (收盘确认)
                        if next_low < s_low and next_close < s_close:
                            triggered = True
                            
                    if triggered:
                        # 间距过滤: 防止相邻的K线同时标记 L2, L3
                        if display_idx - last_l_idx < 2:
                            continue
                            
                        l_count += 1
                        last_l_idx = display_idx
                        
                        # 互斥重置: 触发卖出信号，意味着下跌波段开始，重置买入计数
                        h_count = 0
                        
                        label = f'L{l_count}'
                        color = '#e040fb' # 亮紫色
                        pos = 'aboveBar'
                        self.markers.append({
                            'time': self._timestamp(row['datetime']),
                            'position': pos,
                            'color': color,
                            'shape': 'circle',
                            'text': label
                        })
                    
                elif base_type == 'B':
                    # --- H Setup (Buy) ---
                    # 1. Strong Signal Exception
                    if is_strong:
                        triggered = True
                    # 2. Next Bar Confirmation
                    elif has_next_bar:
                        next_bar = self.df.iloc[next_bar_idx]
                        next_high = float(next_bar['high'])
                        next_close = float(next_bar['close'])
                        # 严格条件：Next High > Signal High (突破) AND Next Close > Signal Close (收盘确认)
                        if next_high > s_high and next_close > s_close:
                            triggered = True

                    if triggered:
                        # 间距过滤
                        if display_idx - last_h_idx < 2:
                            continue

                        h_count += 1
                        last_h_idx = display_idx
                        
                        # 互斥重置: 触发买入信号，意味着上涨波段开始，重置卖出计数
                        l_count = 0
                        
                        label = f'H{h_count}'
                        color = '#ff4081' # 粉红色
                        pos = 'belowBar'
                        self.markers.append({
                            'time': self._timestamp(row['datetime']),
                            'position': pos,
                            'color': color,
                            'shape': 'circle',
                            'text': label
                        })
                continue
            
                continue
            
            # 用户请求：隐藏所有其他分型 (T/B/Tx/Bx)
            if not is_candidate:
                continue

            # 分析右肩 (Signal Bar) 强度
            # 分型由 左(idx-1) 中(idx) 右(idx+1) 构成
            # 这里的 display_idx 是分型顶底所在的中间K线
            # 我们考察右边那根K线(display_idx+1)的收盘力度
            right_bar_idx = display_idx + 1
            is_strong_signal = False
            
            if 0 <= right_bar_idx < len(self.df):
                rb = self.df.iloc[right_bar_idx]
                rb_range = rb['high'] - rb['low']
                if rb_range > 0:
                    if base_type == 'T':
                        # 强顶分型: 右肩收在低位 (Bottom 1/3)
                        close_pos = (rb['close'] - rb['low']) / rb_range
                        if close_pos < 0.33:
                            is_strong_signal = True
                    elif base_type == 'B':
                        # 强底分型: 右肩收在高位 (Top 1/3)
                        close_pos = (rb['close'] - rb['low']) / rb_range
                        if close_pos > 0.66:
                            is_strong_signal = True

            if base_type == 'T':
                price = float(row['high'])
                
                # 颜色逻辑: 
                # - 被破坏(Tx): 灰色 #9e9e9e
                # - 强信号(Strong T): 亮红 #ff0000 (纯红)
                # - 普通(T): 暗红 #b71c1c (深红)
                if is_cancelled:
                    color = '#9e9e9e'
                    text_prefix = 'Tx'
                elif is_strong_signal:
                    color = '#ff0000' # 强信号高亮
                    text_prefix = 'T+'
                else:
                    color = '#b71c1c' # 普通信号变暗
                    text_prefix = 'T'
                    
                # 简化显示: 只显示 T/B/Tx 标识，不显示价格文本
                # 原因: Lightweight Charts 不支持多行文本，显示价格会导致标记过宽挤在一起
                # 价格信息已由箭头位置和左上角 OHLC 面板提供
                self.markers.append({
                    'time': self._timestamp(row['datetime']),
                    'position': 'aboveBar',
                    'color': color,
                    'shape': 'arrowDown',
                    'text': f'{text_prefix}'
                })
            elif base_type == 'B':
                price = float(row['low'])
                
                # 颜色逻辑:
                # - 被破坏(Bx): 灰色 #9e9e9e
                # - 强信号(Strong B): 亮绿 #00e676 (荧光绿)
                # - 普通(B): 暗绿 #1b5e20 (深绿)
                if is_cancelled:
                    color = '#9e9e9e'
                    text_prefix = 'Bx'
                elif is_strong_signal:
                    color = '#00e676' # 强信号高亮
                    text_prefix = 'B+'
                else:
                    color = '#1b5e20' # 普通信号变暗
                    text_prefix = 'B'
                    
                self.markers.append({
                    'time': self._timestamp(row['datetime']),
                    'position': 'belowBar',
                    'color': color,
                    'shape': 'arrowUp',
                    'text': f'{text_prefix}'
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
        
        # 动态检测价格精度 (根据数据的实际小数位数)
        # 检测 close 列的小数位数来决定精度
        def detect_precision(series, max_decimals=4, min_decimals=2):
            """检测数据需要的最小精度"""
            for decimals in range(min_decimals, max_decimals + 1):
                rounded = series.round(decimals)
                if (series - rounded).abs().max() < 1e-9:
                    return decimals
            return max_decimals
        
        precision = detect_precision(self.df['close'])
        
        # 序列化数据为 JSON
        candlestick_json = json.dumps(self.candlestick_data)
        indicators_json = json.dumps(self.indicators)
        strokes_json = json.dumps(self.stroke_lines)
        markers_json = json.dumps(self.markers)
        
        html_content = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <script src="https://unpkg.com/lightweight-charts@4.1.0/dist/lightweight-charts.standalone.production.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #131722;
            color: #d1d4dc;
        }}
        .container {{
            width: 100%;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }}
        .header {{
            padding: 12px 20px;
            background: #1e222d;
            border-bottom: 1px solid #2a2e39;
            display: flex;
            align-items: center;
            gap: 20px;
        }}
        .header h1 {{
            font-size: 16px;
            font-weight: 500;
            color: #d1d4dc;
        }}
        .legend {{
            display: flex;
            gap: 15px;
            font-size: 12px;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 5px;
        }}
        .legend-color {{
            width: 12px;
            height: 3px;
            border-radius: 1px;
        }}
        #chart-container {{
            flex: 1;
            width: 100%;
        }}
        .ohlc-panel {{
            position: absolute;
            top: 50px;
            left: 10px;
            padding: 8px 12px;
            background: rgba(30, 34, 45, 0.85);
            border-radius: 4px;
            font-size: 12px;
            z-index: 1000;
            pointer-events: none;
            display: flex;
            gap: 15px;
            align-items: center;
        }}
        .ohlc-item {{
            display: flex;
            gap: 4px;
        }}
        .ohlc-label {{
            color: #787b86;
        }}
        .ohlc-value {{
            font-weight: 500;
        }}
        .ohlc-value.up {{
            color: #26a69a;
        }}
        .ohlc-value.down {{
            color: #ef5350;
        }}
        .ohlc-date {{
            color: #d1d4dc;
            margin-right: 10px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{title}</h1>
            <div class="legend" id="legend"></div>
        </div>
        <div id="chart-container">
            <div class="ohlc-panel" id="ohlc-panel"></div>
        </div></div>

    <script>
        // 数据
        const candlestickData = {candlestick_json};
        const indicators = {indicators_json};
        const strokesData = {strokes_json};
        const markersData = {markers_json};
        const pricePrecision = {precision}; // 动态精度

        // 创建图表
        const container = document.getElementById('chart-container');
        const chart = LightweightCharts.createChart(container, {{
            layout: {{
                background: {{ type: 'solid', color: '#131722' }},
                textColor: '#d1d4dc',
            }},
            grid: {{
                vertLines: {{ color: '#1e222d' }},
                horzLines: {{ color: '#1e222d' }},
            }},
            crosshair: {{
                mode: LightweightCharts.CrosshairMode.Normal,
                vertLine: {{
                    color: '#758696',
                    width: 1,
                    style: LightweightCharts.LineStyle.Dashed,
                    labelBackgroundColor: '#2a2e39',
                }},
                horzLine: {{
                    color: '#758696',
                    width: 1,
                    style: LightweightCharts.LineStyle.Dashed,
                    labelBackgroundColor: '#2a2e39',
                }},
            }},
            rightPriceScale: {{
                borderColor: '#2a2e39',
                mode: LightweightCharts.PriceScaleMode.Logarithmic,
                scaleMargins: {{
                    top: 0.1,
                    bottom: 0.1,
                }},
            }},
            timeScale: {{
                borderColor: '#2a2e39',
                timeVisible: false,
                secondsVisible: false,
                rightOffset: 5,
                tickMarkFormatter: (time) => {{
                    const date = new Date(time * 1000);
                    const yy = String(date.getFullYear()).slice(-2);
                    const mm = String(date.getMonth() + 1).padStart(2, '0');
                    const dd = String(date.getDate()).padStart(2, '0');
                    return `${{yy}}-${{mm}}-${{dd}}`;
                }},
            }},
            localization: {{
                timeFormatter: (time) => {{
                    const date = new Date(time * 1000);
                    const yy = String(date.getFullYear()).slice(-2);
                    const mm = String(date.getMonth() + 1).padStart(2, '0');
                    const dd = String(date.getDate()).padStart(2, '0');
                    return `${{yy}}-${{mm}}-${{dd}}`;
                }},
            }},
            handleScroll: {{
                vertTouchDrag: false,
            }},
            handleScale: {{
                mouseWheel: false,  // 禁用默认滚轮缩放，使用自定义实现
            }},
        }});

        // 自定义滚轮缩放：以鼠标位置为中心
        container.addEventListener('wheel', (e) => {{
            e.preventDefault();
            
            const timeScale = chart.timeScale();
            const visibleRange = timeScale.getVisibleLogicalRange();
            if (!visibleRange) return;

            const containerRect = container.getBoundingClientRect();
            const mouseX = e.clientX - containerRect.left;
            const chartWidth = containerRect.width;
            
            // 鼠标在图表中的相对位置 (0-1)
            const mouseRatio = mouseX / chartWidth;
            
            // 当前可见范围
            const rangeLength = visibleRange.to - visibleRange.from;
            
            // 缩放因子：向上滚动放大，向下滚动缩小
            const zoomFactor = e.deltaY > 0 ? 1.1 : 0.9;
            const newRangeLength = rangeLength * zoomFactor;
            
            // 限制最小/最大缩放范围
            if (newRangeLength < 10 || newRangeLength > candlestickData.length) return;
            
            // 以鼠标位置为中心计算新范围
            const mouseLogicalPos = visibleRange.from + rangeLength * mouseRatio;
            const newFrom = mouseLogicalPos - newRangeLength * mouseRatio;
            const newTo = mouseLogicalPos + newRangeLength * (1 - mouseRatio);
            
            timeScale.setVisibleLogicalRange({{
                from: newFrom,
                to: newTo,
            }});
        }}, {{ passive: false }});

        // --------------------------------------------------------
        // Shift + 拖动: 垂直平移 (调整价格轴边距)
        // --------------------------------------------------------
        let isDragging = false;
        let lastY = 0;
        let currentTopMargin = 0.1;
        let currentBottomMargin = 0.1;
        
        container.addEventListener('mousedown', (e) => {{
            if (e.shiftKey) {{
                isDragging = true;
                lastY = e.clientY;
                e.preventDefault();
            }}
        }});
        
        document.addEventListener('mousemove', (e) => {{
            if (!isDragging) return;
            
            const deltaY = e.clientY - lastY;
            lastY = e.clientY;
            
            // 调整边距来实现垂直平移效果
            const marginDelta = deltaY / container.clientHeight * 0.5;
            currentTopMargin = Math.max(0, Math.min(0.9, currentTopMargin + marginDelta));
            currentBottomMargin = Math.max(0, Math.min(0.9, currentBottomMargin - marginDelta));
            
            chart.priceScale('right').applyOptions({{
                scaleMargins: {{
                    top: currentTopMargin,
                    bottom: currentBottomMargin,
                }},
            }});
        }});
        
        document.addEventListener('mouseup', () => {{
            isDragging = false;
        }});
        
        // 双击重置视图
        container.addEventListener('dblclick', () => {{
            currentTopMargin = 0.1;
            currentBottomMargin = 0.1;
            chart.priceScale('right').applyOptions({{
                scaleMargins: {{
                    top: 0.1,
                    bottom: 0.1,
                }},
            }});
            chart.timeScale().fitContent();
        }});
        // --------------------------------------------------------

        // K 线系列
        const candlestickSeries = chart.addCandlestickSeries({{
            upColor: '#26a69a',
            downColor: '#ef5350',
            borderUpColor: '#26a69a',
            borderDownColor: '#ef5350',
            wickUpColor: '#26a69a',
            wickDownColor: '#ef5350',
        }});
        candlestickSeries.setData(candlestickData);

        // 设置标记 (分型点)
        if (markersData.length > 0) {{
            candlestickSeries.setMarkers(markersData);
        }}

        // 笔连线 (已禁用，如需启用请取消注释)
        // if (strokesData.length > 0) {{
        //     const strokeSeries = chart.addLineSeries({{
        //         color: '#9c27b0',
        //         lineWidth: 2,
        //         crosshairMarkerVisible: false,
        //         lastValueVisible: false,
        //         priceLineVisible: false,
        //     }});
        //     strokeSeries.setData(strokesData);
        // }}

        // 技术指标线
        const legendContainer = document.getElementById('legend');
        indicators.forEach((indicator, index) => {{
            const lineSeries = chart.addLineSeries({{
                color: indicator.color,
                lineWidth: indicator.lineWidth,
                crosshairMarkerVisible: true,
                lastValueVisible: false,
                priceLineVisible: false,
            }});
            lineSeries.setData(indicator.data);

            // 添加图例
            const legendItem = document.createElement('div');
            legendItem.className = 'legend-item';
            legendItem.innerHTML = `
                <div class="legend-color" style="background: ${{indicator.color}}"></div>
                <span>${{indicator.name}}</span>
            `;
            legendContainer.appendChild(legendItem);
        }});

        // 添加笔图例
        if (strokesData.length > 0) {{
            const strokeLegend = document.createElement('div');
            strokeLegend.className = 'legend-item';
            strokeLegend.innerHTML = `
                <div class="legend-color" style="background: #9c27b0"></div>
                <span>笔</span>
            `;
            legendContainer.appendChild(strokeLegend);
        }}

        // OHLC 面板 (左上角固定显示)
        const ohlcPanel = document.getElementById('ohlc-panel');
        
        chart.subscribeCrosshairMove((param) => {{
            if (!param.time || !param.point) {{
                ohlcPanel.innerHTML = '';
                return;
            }}

            const data = param.seriesData.get(candlestickSeries);
            if (!data) {{
                ohlcPanel.innerHTML = '';
                return;
            }}

            const date = new Date(param.time * 1000);
            const dateStr = date.toISOString().split('T')[0];
            
            const change = data.close - data.open;
            const changeClass = change >= 0 ? 'up' : 'down';
            const changePercent = ((change / data.open) * 100).toFixed(2);
            const changeSign = change >= 0 ? '+' : '';
            
            // 获取指标值
            let indicatorHtml = '';
            indicators.forEach((indicator) => {{
                const found = indicator.data.find(d => d.time === param.time);
                if (found) {{
                    indicatorHtml += `
                        <div class="ohlc-item">
                            <span class="ohlc-label">${{indicator.name}}:</span>
                            <span class="ohlc-value" style="color:${{indicator.color}}">${{found.value.toFixed(pricePrecision)}}</span>
                        </div>
                    `;
                }}
            }});

            ohlcPanel.innerHTML = `
                <span class="ohlc-date">${{dateStr}}</span>
                <div class="ohlc-item"><span class="ohlc-label">O:</span><span class="ohlc-value ${{changeClass}}">${{data.open.toFixed(pricePrecision)}}</span></div>
                <div class="ohlc-item"><span class="ohlc-label">H:</span><span class="ohlc-value ${{changeClass}}">${{data.high.toFixed(pricePrecision)}}</span></div>
                <div class="ohlc-item"><span class="ohlc-label">L:</span><span class="ohlc-value ${{changeClass}}">${{data.low.toFixed(pricePrecision)}}</span></div>
                <div class="ohlc-item"><span class="ohlc-label">C:</span><span class="ohlc-value ${{changeClass}}">${{data.close.toFixed(pricePrecision)}}</span></div>
                <div class="ohlc-item"><span class="ohlc-value ${{changeClass}}">${{changeSign}}${{changePercent}}%</span></div>
                ${{indicatorHtml}}
            `;
        }});

        // 自适应大小
        const resizeObserver = new ResizeObserver(entries => {{
            for (const entry of entries) {{
                chart.applyOptions({{
                    width: entry.contentRect.width,
                    height: entry.contentRect.height,
                }});
            }}
        }});
        resizeObserver.observe(container);

        // 初始显示最后 120 根 K 线
        if (candlestickData.length > 120) {{
            const from = candlestickData[candlestickData.length - 120].time;
            const to = candlestickData[candlestickData.length - 1].time;
            chart.timeScale().setVisibleRange({{ from, to }});
        }}
    </script>
</body>
</html>
'''
        
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
