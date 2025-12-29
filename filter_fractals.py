"""
filter_fractals.py
分型识别与笔过滤模块。

直接从合并后的K线数据中识别分型，并应用笔的过滤规则。
支持标准 OHLC 格式（推荐）和旧版中文列名格式（向后兼容）。
"""
import pandas as pd
import matplotlib.pyplot as plt

from data_schema import COL_DATETIME, COL_OPEN, COL_HIGH, COL_LOW, COL_CLOSE

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial'] 
plt.rcParams['axes.unicode_minus'] = False

# ============================================================
# 核心参数
# ============================================================
MIN_DIST = 3  # 顶底分型中间K线索引差至少为3（即中间隔2根，总共6根K线，不共用）


def _detect_columns(df: pd.DataFrame) -> tuple[str, str, str, str, str]:
    """
    检测 DataFrame 使用的列名格式，返回 (datetime, open, high, low, close) 列名。
    """
    # 标准格式
    if COL_HIGH in df.columns:
        return COL_DATETIME, COL_OPEN, COL_HIGH, COL_LOW, COL_CLOSE
    
    # 旧版中文格式
    if '最高价(元)' in df.columns:
        return '日期', '开盘价(元)', '最高价(元)', '最低价(元)', '收盘价(元)'
    
    if '最高价' in df.columns:
        return '日期', '开盘价', '最高价', '最低价', '收盘价'
    
    raise ValueError(f"无法识别列名格式，当前列: {df.columns.tolist()}")


def process_strokes(input_path, output_path, save_plot_path=None):
    """
    从合并后的K线数据中：
    1. 识别原始分型（顶/底）
    2. 应用笔的规则过滤（顶底交替 + 极值更新 + 间隔约束）
    """
    print(f"读取合并后的K线数据: {input_path}")
    
    # 尝试多种编码
    try:
        df = pd.read_csv(input_path, encoding='utf-8')
    except UnicodeDecodeError:
        df = pd.read_csv(input_path, encoding='gbk')
    
    # 检测列名格式
    col_dt, col_open, col_high, col_low, col_close = _detect_columns(df)
    print(f"检测到列名格式: high={col_high}, low={col_low}")
    
    highs = df[col_high].tolist()
    lows = df[col_low].tolist()
    n = len(df)
    
    if n < 3:
        print("数据不足，无法识别分型")
        return
    
    # ============================================================
    # 第一步：识别原始分型（3根K线组合）
    # ============================================================
    raw_fractals = [''] * n  # '', 'TOP', 'BOTTOM'
    
    for i in range(1, n - 1):
        h_prev, h_curr, h_next = highs[i-1], highs[i], highs[i+1]
        l_prev, l_curr, l_next = lows[i-1], lows[i], lows[i+1]
        
        # 顶分型：中间High最高
        if h_curr > h_prev and h_curr > h_next:
            raw_fractals[i] = 'TOP'
        # 底分型：中间Low最低
        elif l_curr < l_prev and l_curr < l_next:
            raw_fractals[i] = 'BOTTOM'
    
    raw_count = sum(1 for x in raw_fractals if x)
    print(f"原始分型数量: {raw_count}")
    
    # ============================================================
    # 第二步：过滤分型，生成有效笔
    # 规则：顶底交替 + 极值更新 + 最小间隔约束
    # ============================================================
    
    # 收集所有原始分型的 (索引, 类型)
    fractal_points = [(i, raw_fractals[i]) for i in range(n) if raw_fractals[i]]
    
    if not fractal_points:
        print("未找到任何分型")
        return
    
    # 有效笔的端点列表: [(index, type), ...]
    strokes = []
    
    # 状态变量
    pending = None
    last_stroke_end = None
    # 被替换的候选列表
    replaced_candidates = []
    
    for idx, f_type in fractal_points:
        
        if pending is None:
            if last_stroke_end is None:
                pending = (idx, f_type)
                continue
            
            dist = idx - last_stroke_end[0]
            
            # 同向分型：极值比较
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
            
            # 反向分型：检查距离
            if dist < MIN_DIST:
                continue
            
            pending = (idx, f_type)
            continue

        
        # 已有待确认分型
        pending_idx, pending_type = pending
        
        if f_type == pending_type:
            # 同向分型：比较极值
            if f_type == 'TOP':
                if highs[idx] > highs[pending_idx]:
                    replaced_candidates.append(pending)
                    pending = (idx, f_type)
            elif f_type == 'BOTTOM':
                if lows[idx] < lows[pending_idx]:
                    replaced_candidates.append(pending)
                    pending = (idx, f_type)
        else:
            # 反向分型：尝试确认pending
            if last_stroke_end is not None:
                dist = pending_idx - last_stroke_end[0]
                if dist < MIN_DIST:
                    # pending太近，作为被替换记录
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
            
            # 距离足够，确认pending
            strokes.append(pending)
            last_stroke_end = pending
            pending = (idx, f_type)
    
    # 处理最后一个pending
    if pending is not None:
        if last_stroke_end is not None:
            dist = pending[0] - last_stroke_end[0]
            if dist >= MIN_DIST:
                strokes.append(pending)
            else:
                replaced_candidates.append(pending)
        else:
            strokes.append(pending)
    
    # ============================================================
    # 第三步：生成输出
    # ============================================================
    
    # 创建分型列：合并确认的和被替换的
    valid_fractals = [''] * n
    
    # 确认的笔端点用 T/B
    for idx, f_type in strokes:
        valid_fractals[idx] = f_type[0]  # 'TOP' -> 'T', 'BOTTOM' -> 'B'
    
    # 被替换的用 Tx/Bx
    for idx, f_type in replaced_candidates:
        valid_fractals[idx] = f_type[0] + 'x'  # 'TOP' -> 'Tx', 'BOTTOM' -> 'Bx'
    
    df['raw_fractal'] = raw_fractals
    df['valid_fractal'] = valid_fractals
    
    # 保存
    df.to_csv(output_path, index=False, encoding='utf-8')
    
    # 统计
    print(f"过滤完成。规则: 最小间隔 {MIN_DIST}")
    print(f"有效笔端点: {len(strokes)}, 被替换: {len(replaced_candidates)}, 原始分型: {raw_count}")
    print(f"结果已保存至: {output_path}")
    
    # 验证：检查是否交替
    if len(strokes) >= 2:
        prev_type = strokes[0][1]
        alternation_ok = True
        for s_idx, s_type in strokes[1:]:
            if s_type == prev_type:
                print(f"警告: 连续两个 {s_type} 分型未交替！位置 {s_idx}")
                alternation_ok = False
            prev_type = s_type
        if alternation_ok:
            print("✅ 顶底分型交替验证通过")
    
    # 合并所有标记点用于可视化
    all_markers = [(idx, f_type[0]) for idx, f_type in strokes]  # 'T' or 'B'
    all_markers += [(idx, f_type[0] + 'x') for idx, f_type in replaced_candidates]  # 'Tx' or 'Bx'
    all_markers.sort(key=lambda x: x[0])  # 按索引排序
    
    plot_strokes(df, strokes, all_markers, col_dt, col_open, col_high, col_low, col_close, save_plot_path)


def plot_strokes(df, strokes, all_markers, col_dt, col_open, col_high, col_low, col_close, save_path=None):
    """绘制带笔端点标注的K线图"""
    print("\n开始绘制...")
    
    df[col_dt] = pd.to_datetime(df[col_dt])
    
    num_bars = 100
    plot_df = df.tail(num_bars).copy().reset_index(drop=True)
    
    # 调整索引到 plot_df 的范围
    offset = len(df) - num_bars
    plot_strokes_only = [(idx - offset, t[0]) for idx, t in strokes if idx >= offset]  # 仅用于连线
    plot_all_markers = [(idx - offset, t) for idx, t in all_markers if idx >= offset]  # 用于所有标记
    
    dates = plot_df[col_dt]
    opens = plot_df[col_open]
    closes = plot_df[col_close]
    highs = plot_df[col_high]
    lows = plot_df[col_low]
    
    fig, ax = plt.subplots(figsize=(14, 8))
    
    width = 0.6
    width2 = 0.05
    
    up = closes >= opens
    down = closes < opens
    col_up, col_down = 'red', 'green'
    
    # 绘制K线
    ax.bar(plot_df.index[up], highs[up]-lows[up], width2, bottom=lows[up], color=col_up)
    ax.bar(plot_df.index[down], highs[down]-lows[down], width2, bottom=lows[down], color=col_down)
    ax.bar(plot_df.index[up], (closes[up]-opens[up]).abs(), width, bottom=opens[up], color=col_up)
    ax.bar(plot_df.index[down], (closes[down]-opens[down]).abs(), width, bottom=closes[down], color=col_down)
    
    # 绘制所有分型标记
    for plot_idx, f_type in plot_all_markers:
        if plot_idx < 0 or plot_idx >= len(plot_df):
            continue
        
        is_cancelled = 'x' in f_type
        base_type = f_type.replace('x', '')
        
        if base_type == 'T':
            color = 'gray' if is_cancelled else 'black'
            label = 'Tx' if is_cancelled else 'T'
            ax.annotate(label, xy=(plot_idx, highs.iloc[plot_idx]), 
                        xytext=(plot_idx, highs.iloc[plot_idx]*1.003),
                        ha='center', fontsize=10, fontweight='bold', color=color)
        elif base_type == 'B':
            color = 'gray' if is_cancelled else 'blue'
            label = 'Bx' if is_cancelled else 'B'
            ax.annotate(label, xy=(plot_idx, lows.iloc[plot_idx]),
                        xytext=(plot_idx, lows.iloc[plot_idx]*0.997),
                        ha='center', fontsize=10, fontweight='bold', color=color)
    
    # 笔的连线：只连接确认的端点
    stroke_x = []
    stroke_y = []
    for plot_idx, f_type in plot_strokes_only:
        if plot_idx < 0 or plot_idx >= len(plot_df):
            continue
        if f_type == 'T':
            stroke_x.append(plot_idx)
            stroke_y.append(highs.iloc[plot_idx])
        elif f_type == 'B':
            stroke_x.append(plot_idx)
            stroke_y.append(lows.iloc[plot_idx])
    
    ax.plot(stroke_x, stroke_y, color='purple', linewidth=1.5, linestyle='-', label='笔')
    
    step = 5
    ax.set_xticks(range(0, len(plot_df), step))
    ax.set_xticklabels([d.strftime('%Y-%m-%d') for d in dates[::step]], rotation=45, fontsize=8)
    
    ax.set_title('Stroke Identification (Bill Williams / Chan Theory)', fontsize=14)
    ax.set_ylabel('Price')
    ax.legend()
    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"图表已保存至: {save_path}")
        plt.close()
    else:
        plt.show()


if __name__ == "__main__":
    # 直接从合并后的数据开始处理
    process_strokes('TL.CFE_merged.csv', 'TL.CFE_strokes.csv')
