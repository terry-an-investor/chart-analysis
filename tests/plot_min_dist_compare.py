"""
可视化脚本：对比 MIN_DIST=3 和 MIN_DIST=4 的笔识别结果
"""
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib
matplotlib.use('Agg')
import os

os.chdir(os.path.dirname(__file__) or '.')

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial']
plt.rcParams['axes.unicode_minus'] = False

def detect_columns(df):
    if 'high' in df.columns:
        return 'datetime', 'open', 'high', 'low', 'close'
    raise ValueError(f"无法识别列名格式，当前列: {df.columns.tolist()}")


def process_strokes_with_min_dist(df, min_dist):
    col_high = 'high'
    col_low = 'low'
    
    highs = df[col_high].tolist()
    lows = df[col_low].tolist()
    n = len(df)
    
    raw_fractals = [''] * n
    
    for i in range(1, n - 1):
        if highs[i] > highs[i-1] and highs[i] > highs[i+1]:
            raw_fractals[i] = 'TOP'
        elif lows[i] < lows[i-1] and lows[i] < lows[i+1]:
            raw_fractals[i] = 'BOTTOM'
    
    fractal_points = [(i, raw_fractals[i]) for i in range(n) if raw_fractals[i]]
    
    strokes = []
    pending = None
    last_stroke_end = None
    replaced_candidates = []
    
    for idx, f_type in fractal_points:
        if pending is None:
            if last_stroke_end is None:
                pending = (idx, f_type)
                continue
            dist = idx - last_stroke_end[0]
            if f_type == last_stroke_end[1]:
                if f_type == 'TOP' and highs[idx] > highs[last_stroke_end[0]]:
                    old = strokes.pop()
                    replaced_candidates.append(old)
                    strokes.append((idx, f_type))
                    last_stroke_end = (idx, f_type)
                elif f_type == 'BOTTOM' and lows[idx] < lows[last_stroke_end[0]]:
                    old = strokes.pop()
                    replaced_candidates.append(old)
                    strokes.append((idx, f_type))
                    last_stroke_end = (idx, f_type)
                continue
            if dist < min_dist:
                continue
            pending = (idx, f_type)
            continue
        
        pending_idx, pending_type = pending
        
        if f_type == pending_type:
            if f_type == 'TOP' and highs[idx] > highs[pending_idx]:
                replaced_candidates.append(pending)
                pending = (idx, f_type)
            elif f_type == 'BOTTOM' and lows[idx] < lows[pending_idx]:
                replaced_candidates.append(pending)
                pending = (idx, f_type)
        else:
            if last_stroke_end is not None:
                dist = pending_idx - last_stroke_end[0]
                if dist < min_dist:
                    replaced_candidates.append(pending)
                    if f_type == last_stroke_end[1]:
                        if f_type == 'TOP' and highs[idx] > highs[last_stroke_end[0]]:
                            old = strokes.pop()
                            replaced_candidates.append(old)
                            strokes.append((idx, f_type))
                            last_stroke_end = (idx, f_type)
                        elif f_type == 'BOTTOM' and lows[idx] < lows[last_stroke_end[0]]:
                            old = strokes.pop()
                            replaced_candidates.append(old)
                            strokes.append((idx, f_type))
                            last_stroke_end = (idx, f_type)
                        pending = None
                    else:
                        pending = (idx, f_type)
                    continue
            strokes.append(pending)
            last_stroke_end = pending
            pending = (idx, f_type)
    
    if pending is not None:
        if last_stroke_end is not None:
            dist = pending[0] - last_stroke_end[0]
            if dist >= min_dist:
                strokes.append(pending)
            else:
                replaced_candidates.append(pending)
        else:
            strokes.append(pending)
    
    return {'strokes': strokes, 'replaced': replaced_candidates, 'highs': highs, 'lows': lows}


def draw_klines(ax, df, col_high, col_low, col_open, col_close):
    highs = df[col_high].tolist()
    lows = df[col_low].tolist()
    opens = df[col_open].tolist()
    closes = df[col_close].tolist()
    n = len(df)
    
    for i in range(n):
        color = '#FF6B6B' if closes[i] >= opens[i] else '#4ECDC4'
        ax.plot([i, i], [lows[i], highs[i]], color=color, linewidth=1, alpha=0.7)
        body_bottom = min(opens[i], closes[i])
        body_height = abs(closes[i] - opens[i])
        ax.bar(i, body_height, 0.4, bottom=body_bottom, color=color, alpha=0.9)


def plot_comparison(df, result_dist3, result_dist4, save_path=None):
    col_dt, col_open, col_high, col_low, col_close = detect_columns(df)
    
    df[col_dt] = pd.to_datetime(df[col_dt])
    
    num_bars = 120
    if len(df) > num_bars:
        plot_df = df.iloc[-num_bars:].copy().reset_index(drop=True)
        offset = len(df) - num_bars
    else:
        plot_df = df.copy().reset_index(drop=True)
        offset = 0
    
    fig, axes = plt.subplots(2, 1, figsize=(18, 12), sharex=True)
    fig.suptitle('MIN_DIST=3 vs MIN_DIST=4 笔识别对比', fontsize=16, fontweight='bold')
    
    def draw_axis(ax, result, min_dist_label, color_theme):
        ax.set_title(f'MIN_DIST = {min_dist_label} (有效笔: {len(result["strokes"])})', 
                    fontsize=14, fontweight='bold', color=color_theme)
        
        draw_klines(ax, plot_df, col_high, col_low, col_open, col_close)
        
        strokes = result['strokes']
        highs_all = result['highs']
        lows_all = result['lows']
        
        stroke_indices = [(idx - offset, t) for idx, t in strokes if offset <= idx < offset + num_bars]
        
        for idx, f_type in stroke_indices:
            if idx < 0 or idx >= len(plot_df):
                continue
            
            if f_type == 'TOP':
                price = plot_df[col_high].iloc[idx]
                ax.scatter(idx, price, marker='v', s=150, c='red', zorder=5, edgecolors='black', linewidths=1)
                ax.annotate(f'T', xy=(idx, price), xytext=(idx, price*1.008),
                           ha='center', fontsize=9, fontweight='bold', color='red')
            else:
                price = plot_df[col_low].iloc[idx]
                ax.scatter(idx, price, marker='^', s=150, c='green', zorder=5, edgecolors='black', linewidths=1)
                ax.annotate(f'B', xy=(idx, price), xytext=(idx, price*0.992),
                           ha='center', fontsize=9, fontweight='bold', color='green')
        
        stroke_sorted = sorted(stroke_indices, key=lambda x: x[0])
        
        for i in range(len(stroke_sorted) - 1):
            curr_idx, curr_type = stroke_sorted[i]
            next_idx, next_type = stroke_sorted[i+1]
            
            if curr_type == 'B' and next_type == 'T':
                y1 = plot_df[col_low].iloc[curr_idx]
                y2 = plot_df[col_high].iloc[next_idx]
                ax.plot([curr_idx, next_idx], [y1, y2], color='purple', linewidth=2, alpha=0.8)
            elif curr_type == 'T' and next_type == 'B':
                y1 = plot_df[col_high].iloc[curr_idx]
                y2 = plot_df[col_low].iloc[next_idx]
                ax.plot([curr_idx, next_idx], [y1, y2], color='blue', linewidth=2, alpha=0.8)
        
        replaced = result['replaced']
        replaced_indices = [(idx - offset, t) for idx, t in replaced if offset <= idx < offset + num_bars]
        
        for idx, f_type in replaced_indices:
            if idx < 0 or idx >= len(plot_df):
                continue
            
            if f_type == 'TOP':
                price = plot_df[col_high].iloc[idx]
                ax.scatter(idx, price, marker='v', s=80, c='lightgray', zorder=4, edgecolors='gray', linewidths=1, alpha=0.7)
            else:
                price = plot_df[col_low].iloc[idx]
                ax.scatter(idx, price, marker='^', s=80, c='lightgray', zorder=4, edgecolors='gray', linewidths=1, alpha=0.7)
        
        y_min, y_max = plot_df[col_low].min(), plot_df[col_high].max()
        y_margin = (y_max - y_min) * 0.1
        ax.set_ylim(y_min - y_margin, y_max + y_margin)
        
        ax.set_ylabel('Price', fontsize=12)
        ax.grid(True, alpha=0.3)
        
        return len(strokes), len(replaced)
    
    strokes3, replaced3 = draw_axis(axes[0], result_dist3, '3', '#2196F3')
    strokes4, replaced4 = draw_axis(axes[1], result_dist4, '4', '#FF9800')
    
    step = 10
    axes[1].set_xticks(range(0, len(plot_df), step))
    axes[1].set_xticklabels([plot_df[col_dt].iloc[i].strftime('%m-%d') for i in range(0, len(plot_df), step)], 
                           rotation=45, fontsize=9)
    axes[1].set_xlabel('Date', fontsize=12)
    
    legend_elements = [
        mpatches.Patch(color='#FF6B6B', alpha=0.8, label='K线上涨'),
        mpatches.Patch(color='#4ECDC4', alpha=0.8, label='K线下跌'),
        plt.Line2D([0], [0], marker='v', color='w', markerfacecolor='red', markersize=10, label='顶分型(T)'),
        plt.Line2D([0], [0], marker='^', color='w', markerfacecolor='green', markersize=10, label='底分型(B)'),
        plt.Line2D([0], [0], marker='v', color='w', markerfacecolor='lightgray', markersize=10, label='被替换分型'),
        plt.Line2D([0], [0], color='purple', linewidth=2, label='上涨笔(B→T)'),
        plt.Line2D([0], [0], color='blue', linewidth=2, label='下跌笔(T→B)'),
    ]
    
    fig.legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(0.98, 0.98), fontsize=10)
    
    stats_text = f"MIN_DIST=3: {strokes3}笔, {replaced3}替换 | MIN_DIST=4: {strokes4}笔, {replaced4}替换"
    fig.text(0.5, 0.02, stats_text, ha='center', fontsize=11, 
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.tight_layout(rect=[0, 0.04, 0.96, 0.96])
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"图表已保存至: {save_path}")
        plt.close()
    else:
        plt.show()


def plot_diff_highlight(df, result_dist3, result_dist4, save_path=None):
    col_dt, col_open, col_high, col_low, col_close = detect_columns(df)
    
    df[col_dt] = pd.to_datetime(df[col_dt])
    
    num_bars = 120
    if len(df) > num_bars:
        plot_df = df.iloc[-num_bars:].copy().reset_index(drop=True)
        offset = len(df) - num_bars
    else:
        plot_df = df.copy().reset_index(drop=True)
        offset = 0
    
    fig, ax = plt.subplots(figsize=(20, 8))
    ax.set_title(f'笔识别差异对比 (红色圆圈 = MIN_DIST=4 跳过的分型)', fontsize=14, fontweight='bold')
    
    draw_klines(ax, plot_df, col_high, col_low, col_open, col_close)
    
    strokes3_set = set(result_dist3['strokes'])
    strokes4_set = set(result_dist4['strokes'])
    
    strokes3_only = strokes3_set - strokes4_set
    strokes4_only = strokes4_set - strokes3_set
    
    stroke_indices3 = [(idx - offset, t) for idx, t in strokes3_only if offset <= idx < offset + num_bars]
    stroke_indices4 = [(idx - offset, t) for idx, t in strokes4_only if offset <= idx < offset + num_bars]
    
    for idx, f_type in stroke_indices3:
        if idx < 0 or idx >= len(plot_df):
            continue
        
        if f_type == 'TOP':
            price = plot_df[col_high].iloc[idx]
            ax.scatter(idx, price, marker='o', s=250, c='red', zorder=5, edgecolors='darkred', linewidths=2)
        else:
            price = plot_df[col_low].iloc[idx]
            ax.scatter(idx, price, marker='o', s=250, c='red', zorder=5, edgecolors='darkred', linewidths=2)
    
    for idx, f_type in stroke_indices4:
        if idx < 0 or idx >= len(plot_df):
            continue
        
        if f_type == 'TOP':
            price = plot_df[col_high].iloc[idx]
            ax.scatter(idx, price, marker='s', s=150, c='green', zorder=5, edgecolors='darkgreen', linewidths=2)
        else:
            price = plot_df[col_low].iloc[idx]
            ax.scatter(idx, price, marker='s', s=150, c='green', zorder=5, edgecolors='darkgreen', linewidths=2)
    
    all_strokes = result_dist4['strokes']
    stroke_indices = [(idx - offset, t) for idx, t in all_strokes if offset <= idx < offset + num_bars]
    stroke_sorted = sorted(stroke_indices, key=lambda x: x[0])
    
    for i in range(len(stroke_sorted) - 1):
        curr_idx, curr_type = stroke_sorted[i]
        next_idx, next_type = stroke_sorted[i+1]
        
        if curr_type == 'B' and next_type == 'T':
            y1 = plot_df[col_low].iloc[curr_idx]
            y2 = plot_df[col_high].iloc[next_idx]
            ax.plot([curr_idx, next_idx], [y1, y2], color='purple', linewidth=1.5, alpha=0.6)
        elif curr_type == 'T' and next_type == 'B':
            y1 = plot_df[col_high].iloc[curr_idx]
            y2 = plot_df[col_low].iloc[next_idx]
            ax.plot([curr_idx, next_idx], [y1, y2], color='blue', linewidth=1.5, alpha=0.6)
    
    y_min, y_max = plot_df[col_low].min(), plot_df[col_high].max()
    y_margin = (y_max - y_min) * 0.1
    ax.set_ylim(y_min - y_margin, y_max + y_margin)
    
    step = 10
    ax.set_xticks(range(0, len(plot_df), step))
    ax.set_xticklabels([plot_df[col_dt].iloc[i].strftime('%m-%d') for i in range(0, len(plot_df), step)], 
                      rotation=45, fontsize=9)
    ax.set_xlabel('Date', fontsize=12)
    ax.set_ylabel('Price', fontsize=12)
    ax.grid(True, alpha=0.3)
    
    legend_elements = [
        mpatches.Patch(color='#FF6B6B', alpha=0.8, label='K线上涨'),
        mpatches.Patch(color='#4ECDC4', alpha=0.8, label='K线下跌'),
        plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='red', markersize=12, 
                  markeredgecolor='darkred', label=f'MIN_DIST=3独有分型 (跳过{len(strokes3_only)}个)'),
        plt.Line2D([0], [0], marker='s', color='w', markerfacecolor='green', markersize=10, 
                  markeredgecolor='darkgreen', label=f'MIN_DIST=4独有分型'),
        plt.Line2D([0], [0], color='purple', linewidth=2, label='上涨笔'),
        plt.Line2D([0], [0], color='blue', linewidth=2, label='下跌笔'),
    ]
    
    ax.legend(handles=legend_elements, loc='upper left', fontsize=10)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"差异图已保存至: {save_path}")
        plt.close()
    else:
        plt.show()


if __name__ == "__main__":
    input_path = "data/processed/TB10Y.WI_merged.csv"
    output_path1 = "data/processed/tb10y_min_dist_comparison.png"
    output_path2 = "data/processed/tb10y_min_dist_diff.png"
    
    print("读取数据...")
    df = pd.read_csv(input_path, encoding='utf-8')
    print(f"K线数量: {len(df)}")
    
    print("\n处理 MIN_DIST=3...")
    result_dist3 = process_strokes_with_min_dist(df, min_dist=3)
    print(f"  有效笔: {len(result_dist3['strokes'])}")
    
    print("\n处理 MIN_DIST=4...")
    result_dist4 = process_strokes_with_min_dist(df, min_dist=4)
    print(f"  有效笔: {len(result_dist4['strokes'])}")
    
    print("\n生成对比图...")
    plot_comparison(df, result_dist3, result_dist4, output_path1)
    
    print("\n生成差异图...")
    plot_diff_highlight(df, result_dist3, result_dist4, output_path2)
    
    print("\n完成！")
