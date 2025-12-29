import plotly.graph_objects as go
import pandas as pd
from typing import List, Tuple

def plot_interactive_kline(df: pd.DataFrame, 
                         strokes: List[Tuple[int, str]], 
                         save_path: str = None):
    """
    绘制交互式 K 线图 (Plotly)
    
    Args:
        df: 包含 datetime, open, high, low, close 的 DataFrame
        strokes: 分型标记 list of (index, type)，如 [(10, 'T'), (15, 'B')]
        save_path: HTML 保存路径
    """
    
    #构造 Hover Text
    hover_text = [
        f"时间: {d.strftime('%Y-%m-%d')}<br>O: {o:.2f}<br>H: {h:.2f}<br>L: {l:.2f}<br>C: {c:.2f}"
        for d, o, h, l, c in zip(df['datetime'], df['open'], df['high'], df['low'], df['close'])
    ]
    
    # 1. 创建 K 线图 Traces
    candlestick = go.Candlestick(
        x=df.index,  # 使用索引作为X轴，避免非交易日空隙
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name='K线',
        text=hover_text,
        hoverinfo='text'
    )
    
    # 3. 收集分型和笔的数据
    annotations = []
    
    # 仅收集确认的分型用于连线
    stroke_x = []
    stroke_y = []
    
    # 按索引排序
    sorted_strokes = sorted(strokes, key=lambda x: x[0])
    
    for idx, f_type in sorted_strokes:
        if idx < 0 or idx >= len(df):
            continue
            
        if f_type == 'T':
            price = df['high'].iloc[idx]
            stroke_x.append(idx)
            stroke_y.append(price)
            # 添加顶分型标注
            annotations.append(dict(
                x=idx, y=price,
                text=f"T {price:.2f}",
                showarrow=False,
                yshift=10,
                font=dict(color='black', size=10, family='Arial Black')
            ))
            
        elif f_type == 'B':
            price = df['low'].iloc[idx]
            stroke_x.append(idx)
            stroke_y.append(price)
            # 添加底分型标注
            annotations.append(dict(
                x=idx, y=price,
                text=f"B {price:.2f}",
                showarrow=False,
                yshift=-10,
                font=dict(color='blue', size=10, family='Arial Black')
            ))
    
    # 5. 创建笔连线 Trace
    stroke_trace = go.Scatter(
        x=stroke_x,
        y=stroke_y,
        mode='lines',
        line=dict(color='purple', width=1.5),
        name='笔',
        hoverinfo='skip'
    )
    
    # 6. 组装 Figure
    # 注意：不包含文字 Trace，因为它们会弄乱 RangeSlider
    fig = go.Figure(data=[candlestick, stroke_trace])
    
    # 7. 配置 Layout
    dates = df['datetime'].dt.strftime('%Y-%m-%d').tolist()
    
    fig.update_layout(
        title=f'Fractal Analysis - {df.iloc[0]["symbol"] if "symbol" in df.columns else ""}',
        yaxis_title='Price',
        xaxis_title='Date',
        dragmode='zoom', # 默认缩放模式
        hovermode='x unified',
        template='plotly_white',
        height=700,
        margin=dict(l=50, r=50, t=80, b=50),
        
        # 将文字标注作为布局的一部分添加到图中
        annotations=annotations,

        # Y 轴自适应与交互设置
        yaxis=dict(
            autorange=True,      # 自动缩放
            fixedrange=False,    # 允许手动缩放（在价格轴上拖拽）
            side='right',        # 价格显示在右侧
            gridcolor='#F0F0F0',
            zeroline=False,
            exponentformat='none',
            # 增加一个微小的 rangemode，防止 K 线贴着上下边缘
            rangemode='normal'
        ),
        
        # X 轴设置
        xaxis=dict(
            type='linear',
            tickmode='array',
            tickvals=list(range(0, len(dates), max(1, len(dates)//20))), 
            ticktext=[dates[i] for i in range(0, len(dates), max(1, len(dates)//20))],
            gridcolor='#F0F0F0',
            
            # 滑块设置：精细化样式
            rangeslider=dict(
                visible=True,
                thickness=0.1,      # 稍微加高一点，让波形更清楚
                bgcolor='#FFFFFF',  # 显式白背景，解决“未选中区域变灰”的问题
                bordercolor='#DEDEDE',
                borderwidth=1,
                yaxis=dict(rangemode='match') # 恢复 match，但在白背景下应该表现更好，或者去掉
            ),
            range=[max(0, len(df)-120), len(df)] # 默认显示最后120根
        )
    )
    
    # 启用鼠标滚轮缩放，并清理工具栏
    config = dict({
        'scrollZoom': True,           # 允许滚轮缩放
        'displayModeBar': True,
        'modeBarButtonsToRemove': ['lasso2d', 'select2d', 'autoScale2d'],
        'displaylogo': False,
        'doubleClick': 'reset+autosize', # 双击重置
        'responsive': True
    })


    if save_path:
        # 强制更新所有 trace 不在 slider 中重复（虽然 plotly 对 scatter 较难完全控制）
        # 但我们之前改用 annotations 已经解决了最大的文字乱入问题
        fig.write_html(save_path, config=config)
        print(f"交互式图表已保存至: {save_path}")
