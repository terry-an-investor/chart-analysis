"""
analysis/merging.py
K 线合并模块，处理包含关系的 K 线合并。

支持标准 OHLC 格式（推荐）和旧版中文列名格式（向后兼容）。
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from ..io.schema import COL_DATETIME, COL_OPEN, COL_HIGH, COL_LOW, COL_CLOSE

# 设置中文显示
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial'] 
plt.rcParams['axes.unicode_minus'] = False


def _detect_columns(df: pd.DataFrame) -> tuple[str, str, str, str, str]:
    """
    检测 DataFrame 使用的列名格式，返回 (datetime, open, high, low, close) 列名。
    支持标准格式和旧版中文格式。
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


def get_initial_trend(bars, col_high: str, col_low: str):
    """
    向后扫描直到找到明确的趋势方向
    """
    for i in range(1, len(bars)):
        prev = bars[i-1]
        curr = bars[i]
        
        h_prev, l_prev = prev[col_high], prev[col_low]
        h_curr, l_curr = curr[col_high], curr[col_low]
        
        # 排除包含关系
        is_inside = (h_curr <= h_prev) and (l_curr >= l_prev)
        is_outside = (h_curr >= h_prev) and (l_curr <= h_prev)
        
        if not is_inside and not is_outside:
            if h_curr > h_prev and l_curr > l_prev:
                return 1  # UP
            elif h_curr < h_prev and l_curr < l_prev:
                return -1  # DOWN
    return 1  # 默认向上，如果全都是包含关系（极不可能）


def apply_kline_merging(input_path, output_path, save_plot_path=None):
    """
    应用 K 线合并逻辑。
    
    Args:
        input_path: 输入 CSV 文件路径（已添加 kline_status 的数据）
        output_path: 输出 CSV 文件路径
        save_plot_path: 可选，保存图表的路径
    """
    print(f"开始读取数据: {input_path}")
    
    # 尝试多种编码
    try:
        df = pd.read_csv(input_path, encoding='utf-8')
    except UnicodeDecodeError:
        df = pd.read_csv(input_path, encoding='gbk')
    
    # 检测列名格式
    col_dt, col_open, col_high, col_low, col_close = _detect_columns(df)
    print(f"检测到列名格式: high={col_high}, low={col_low}")
    
    raw_bars = df.to_dict('records')
    if not raw_bars:
        return
    
    # 过滤掉 high/low 为 NaN 的无效行
    valid_bars = [b for b in raw_bars if pd.notna(b[col_high]) and pd.notna(b[col_low])]
    if len(valid_bars) < len(raw_bars):
        print(f"过滤无效行: {len(raw_bars)} -> {len(valid_bars)} 行")
    raw_bars = valid_bars

    merged_bars = []
    
    # 预先确定初始趋势，解决开头就是包含关系导致的无法合并问题
    current_trend = get_initial_trend(raw_bars, col_high, col_low)
    print(f"初始趋势判定为: {'上涨' if current_trend==1 else '下跌'}")
    
    merged_bars.append(raw_bars[0].copy())  # 使用副本以免修改原始数据
    
    merge_count = 0
    
    i = 1
    while i < len(raw_bars):
        curr = raw_bars[i].copy()
        prev = merged_bars[-1]  # 这里引用的是列表中的对象，修改它会直接生效
        
        h_curr, l_curr = curr[col_high], curr[col_low]
        h_prev, l_prev = prev[col_high], prev[col_low]
        
        is_inside = (h_curr <= h_prev) and (l_curr >= l_prev)
        is_outside = (h_curr >= h_prev) and (l_curr <= l_prev)
        
        # 只要存在包含关系，就根据当前趋势进行合并
        if is_inside or is_outside:
            if current_trend == 1:
                # Up Trend: 取高点中的高点，低点中的高点
                new_high = max(h_prev, h_curr)
                new_low = max(l_prev, l_curr)
            else:
                # Down Trend: 取高点中的低点，低点中的低点
                new_high = min(h_prev, h_curr)
                new_low = min(l_prev, l_curr)
            
            # 更新 close 为当前K线的收盘价
            new_close = curr[col_close]
            new_open = prev[col_open]  # 保留合并前第一根的开盘价
            
            # 【关键修复】确保 OHLC 一致性：
            # - low 必须 ≤ min(open, close)
            # - high 必须 ≥ max(open, close)
            new_low = min(new_low, new_open, new_close)
            new_high = max(new_high, new_open, new_close)
                
            # 原地更新 prev
            prev[col_high] = new_high
            prev[col_low] = new_low
            prev[col_close] = new_close
            prev[col_dt] = curr[col_dt] 
            prev['kline_status'] = "MERGED" 
            
            merge_count += 1
            
            # 【向左回溯】合并后OHLC可能变化，检查是否与更早的K线形成新的包含关系
            while len(merged_bars) >= 2:
                last = merged_bars[-1]
                second_last = merged_bars[-2]
                
                h_last, l_last = last[col_high], last[col_low]
                h_second, l_second = second_last[col_high], second_last[col_low]
                
                is_inside_back = (h_last <= h_second) and (l_last >= l_second)
                is_outside_back = (h_last >= h_second) and (l_last <= l_second)
                
                if not (is_inside_back or is_outside_back):
                    break  # 无包含关系，停止回溯
                
                # 确定回溯时的趋势
                if len(merged_bars) >= 3:
                    third_last = merged_bars[-3]
                    h_third, l_third = third_last[col_high], third_last[col_low]
                    if h_second > h_third and l_second > l_third:
                        backtrack_trend = 1
                    elif h_second < h_third and l_second < l_third:
                        backtrack_trend = -1
                    else:
                        backtrack_trend = current_trend
                else:
                    backtrack_trend = current_trend
                
                if backtrack_trend == 1:
                    new_high_back = max(h_second, h_last)
                    new_low_back = max(l_second, l_last)
                else:
                    new_high_back = min(h_second, h_last)
                    new_low_back = min(l_second, l_last)
                
                # OHLC一致性
                new_open_back = second_last[col_open]
                new_close_back = last[col_close]
                new_low_back = min(new_low_back, new_open_back, new_close_back)
                new_high_back = max(new_high_back, new_open_back, new_close_back)
                
                # 合并：更新second_last，移除last
                second_last[col_high] = new_high_back
                second_last[col_low] = new_low_back
                second_last[col_close] = new_close_back
                second_last[col_dt] = last[col_dt]
                second_last['kline_status'] = "MERGED"
                merged_bars.pop()
                merge_count += 1
            
            # i 增加，下一轮循环将用新的 prev (即刚刚合并后的结果) 与 raw_bars[i+1] 对比
            # 这就实现了向右的递归合并
            i += 1
        
        else:
            # 无包含关系，更新趋势
            if h_curr > h_prev and l_curr > l_prev:
                current_trend = 1
            elif h_curr < h_prev and l_curr < l_prev:
                current_trend = -1
            
            merged_bars.append(curr)
            
            # 【新增】向左回溯检查：新加入的K线可能与更早的K线形成包含关系
            # 这种情况发生在合并后OHLC调整改变了high/low
            while len(merged_bars) >= 2:
                last = merged_bars[-1]
                second_last = merged_bars[-2]
                
                h_last, l_last = last[col_high], last[col_low]
                h_second, l_second = second_last[col_high], second_last[col_low]
                
                is_inside_back = (h_last <= h_second) and (l_last >= l_second)
                is_outside_back = (h_last >= h_second) and (l_last <= l_second)
                
                if not (is_inside_back or is_outside_back):
                    break  # 无包含关系，停止回溯
                
                # 需要合并最后两根
                # 重新确定趋势（基于前一根的状态）
                if len(merged_bars) >= 3:
                    third_last = merged_bars[-3]
                    h_third, l_third = third_last[col_high], third_last[col_low]
                    if h_second > h_third and l_second > l_third:
                        backtrack_trend = 1
                    elif h_second < h_third and l_second < l_third:
                        backtrack_trend = -1
                    else:
                        backtrack_trend = current_trend
                else:
                    backtrack_trend = current_trend
                
                if backtrack_trend == 1:
                    new_high = max(h_second, h_last)
                    new_low = max(l_second, l_last)
                else:
                    new_high = min(h_second, h_last)
                    new_low = min(l_second, l_last)
                
                # OHLC一致性检查
                new_open = second_last[col_open]
                new_close = last[col_close]
                new_low = min(new_low, new_open, new_close)
                new_high = max(new_high, new_open, new_close)
                
                # 更新second_last，移除last
                second_last[col_high] = new_high
                second_last[col_low] = new_low
                second_last[col_close] = new_close
                second_last[col_dt] = last[col_dt]
                second_last['kline_status'] = "MERGED"
                merged_bars.pop()
                merge_count += 1
            
            i += 1

    # --- 新增步骤：重新计算合并后的 K 线状态 ---
    print("正在重新计算合并后的 K 线状态...")
    merged_bars[0]['kline_status'] = 'INITIAL'
    
    for i in range(1, len(merged_bars)):
        curr = merged_bars[i]
        prev = merged_bars[i-1]
        
        h_curr, l_curr = curr[col_high], curr[col_low]
        h_prev, l_prev = prev[col_high], prev[col_low]
        
        if h_curr > h_prev and l_curr > l_prev:
            status = 'TREND_UP'
        elif h_curr < h_prev and l_curr < l_prev:
            status = 'TREND_DOWN'
        else:
            # 理论上合并后不应存在 INSIDE/OUTSIDE，除非极其罕见的完全重合或者是逻辑漏洞
            # 这里统一标记为 MIXED 以示区别，或者通过上下影线判断
            status = 'MIXED'
        
        # 保留合并标记
        if "MERGED" in curr.get('kline_status', ''):
            curr['kline_status'] = status + "_(M)"
        else:
            curr['kline_status'] = status

    # 输出结果
    result_df = pd.DataFrame(merged_bars)
    result_df.to_csv(output_path, index=False, encoding='utf-8')
    print(f"合并完成。次数: {merge_count}")
    
    # 验证合并结果
    _validate_merged_data(result_df, col_high, col_low, col_open, col_close)
    
    plot_merged_kline(result_df, col_dt, col_open, col_high, col_low, col_close, save_plot_path)


def _validate_merged_data(df, col_high, col_low, col_open, col_close):
    """
    验证合并后的K线数据：
    1. OHLC一致性：low ≤ min(open, close) 且 high ≥ max(open, close)
    2. 无包含关系：相邻K线都是趋势关系
    """
    # 检查OHLC一致性
    ohlc_violations = []
    for i, row in df.iterrows():
        o, h, l, c = row[col_open], row[col_high], row[col_low], row[col_close]
        if l > min(o, c) or h < max(o, c):
            ohlc_violations.append(i)
    
    if ohlc_violations:
        print(f"⚠️ OHLC一致性违规: {len(ohlc_violations)} 个")
    else:
        print("✅ OHLC一致性验证通过")
    
    # 检查相邻K线的包含关系
    inclusion_count = 0
    for i in range(1, len(df)):
        prev = df.iloc[i-1]
        curr = df.iloc[i]
        
        h1, l1 = prev[col_high], prev[col_low]
        h2, l2 = curr[col_high], curr[col_low]
        
        is_inside = (h2 <= h1) and (l2 >= l1)
        is_outside = (h2 >= h1) and (l2 <= l1)
        
        if is_inside or is_outside:
            inclusion_count += 1
    
    if inclusion_count > 0:
        print(f"⚠️ 发现 {inclusion_count} 对包含关系未处理")
    else:
        print("✅ 无包含关系，所有相邻K线都是趋势关系")


def plot_merged_kline(df, col_dt, col_open, col_high, col_low, col_close, save_path=None):
    """绘制合并后的 K 线图"""
    print("\n开始绘制合并后的 K 线图...")
    df[col_dt] = pd.to_datetime(df[col_dt])
    
    num_bars = 60
    plot_df = df.tail(num_bars).copy().reset_index(drop=True)
    
    dates = plot_df[col_dt]
    opens = plot_df[col_open]
    closes = plot_df[col_close]
    highs = plot_df[col_high]
    lows = plot_df[col_low]
    status_list = plot_df['kline_status']
    
    fig, ax = plt.subplots(figsize=(14, 8))
    
    width = 0.6
    width2 = 0.05
    
    up = closes >= opens
    down = closes < opens
    
    col_up = 'red'
    col_down = 'green'
    
    ax.bar(plot_df.index[up], highs[up]-lows[up], width2, bottom=lows[up], color=col_up)
    ax.bar(plot_df.index[down], highs[down]-lows[down], width2, bottom=lows[down], color=col_down)
    
    heights = (closes - opens).abs()
    bottoms = plot_df[[col_open, col_close]].min(axis=1)
    
    ax.bar(plot_df.index[up], heights[up], width, bottom=bottoms[up], color=col_up)
    ax.bar(plot_df.index[down], heights[down], width, bottom=bottoms[down], color=col_down)
    
    step = 5
    ax.set_xticks(range(0, len(plot_df), step))
    ax.set_xticklabels([d.strftime('%Y-%m-%d') for d in dates[::step]], rotation=45, fontsize=8)
    
    for i in range(len(plot_df)):
        status = str(status_list.iloc[i])
        if "(M)" in status:
             ax.text(i, highs.iloc[i] * 1.0005, "M", 
                ha='center', va='bottom',
                rotation=0, fontsize=8, color='purple', fontweight='bold')
    
    ax.set_title('Merged K-line Visualization (Recursive)', fontsize=14)
    ax.set_ylabel('Price')
    ax.text(0.02, 0.98, "标注说明:\nM = 合并K线", transform=ax.transAxes,
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.8),
            verticalalignment='top')


    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"图表已保存至: {save_path}")
        plt.close()
    else:
        plt.show()
