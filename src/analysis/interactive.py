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
        
        # 【关键】只筛选有效的 T 和 B (忽略 Tx, Bx 等被替换的分型)
        valid_strokes = [
            (idx, f_type) for idx, f_type in strokes 
            if f_type in ('T', 'B')
        ]
        
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
            fractals: 分型标记列表 [(index, 'T'|'B'|'Tx'|'Bx'), ...]
        
        Returns:
            self: 支持链式调用
        """
        for idx, f_type in fractals:
            if idx < 0 or idx >= len(self.df):
                continue
            
            row = self.df.iloc[idx]
            is_cancelled = 'x' in f_type
            base_type = f_type.replace('x', '')
            
            if base_type == 'T':
                price = float(row['high'])
                self.markers.append({
                    'time': self._timestamp(row['datetime']),
                    'position': 'aboveBar',
                    'color': '#9e9e9e' if is_cancelled else '#ef5350',  # 灰色 vs 红色
                    'shape': 'arrowDown',
                    'text': f'Tx' if is_cancelled else f'T {price:.{self.precision}f}'
                })
            elif base_type == 'B':
                price = float(row['low'])
                self.markers.append({
                    'time': self._timestamp(row['datetime']),
                    'position': 'belowBar',
                    'color': '#9e9e9e' if is_cancelled else '#26a69a',  # 灰色 vs 绿色
                    'shape': 'arrowUp',
                    'text': f'Bx' if is_cancelled else f'B {price:.{self.precision}f}'
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
                timeVisible: true,
                secondsVisible: false,
                rightOffset: 5,
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
