"""
analysis/fractals.py
分型识别与笔过滤模块。

直接从合并后的K线数据中识别分型，并应用笔的过滤规则。
支持标准 OHLC 格式（推荐）和旧版中文列名格式（向后兼容）。
"""

import matplotlib.pyplot as plt
import pandas as pd

from ..io.schema import COL_CLOSE, COL_DATETIME, COL_HIGH, COL_LOW, COL_OPEN

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "Arial"]
plt.rcParams["axes.unicode_minus"] = False

# ============================================================
# 核心参数
# ============================================================
MIN_DIST = 4  # 顶底分型中间K线索引差至少为4（即中间隔3根，总共7根K线，不共用）


def _detect_columns(df: pd.DataFrame) -> tuple[str, str, str, str, str]:
    """
    检测 DataFrame 使用的列名格式，返回 (datetime, open, high, low, close) 列名。
    """
    # 标准格式
    if COL_HIGH in df.columns:
        return COL_DATETIME, COL_OPEN, COL_HIGH, COL_LOW, COL_CLOSE

    # 旧版中文格式
    if "最高价(元)" in df.columns:
        return "日期", "开盘价(元)", "最高价(元)", "最低价(元)", "收盘价(元)"

    if "最高价" in df.columns:
        return "日期", "开盘价", "最高价", "最低价", "收盘价"

    raise ValueError(f"无法识别列名格式，当前列: {df.columns.tolist()}")


def process_fractals(input_path, output_path, save_plot_path=None):
    """
    简化版分型识别（Al Brooks 风格）。

    只识别原始顶底分型，不应用笔的过滤规则。
    每个分型形成后（右肩出现），在右肩 K 线上标记候选信号。

    输出列:
    - raw_fractal: 原始分型类型 ('TOP', 'BOTTOM', '')
    - candidate_display: 候选信号标记 ('Tc', 'Bc', '')
    """
    print(f"读取合并后的K线数据: {input_path}")

    # 尝试多种编码
    try:
        df = pd.read_csv(input_path, encoding="utf-8")
    except UnicodeDecodeError:
        df = pd.read_csv(input_path, encoding="gbk")

    # 检测列名格式
    col_dt, col_open, col_high, col_low, col_close = _detect_columns(df)
    print(f"检测到列名格式: high={col_high}, low={col_low}")

    highs = df[col_high].values
    lows = df[col_low].values
    opens = df[col_open].values
    closes = df[col_close].values
    n = len(df)

    if n < 3:
        print("数据不足，无法识别分型")
        return

    # ============================================================
    # 识别原始分型（纯3根K线组合）
    # 顶分型：中间K线的High比左右都高
    # 底分型：中间K线的Low比左右都低
    # 注意：跳过包含 NaN 值的 K 线
    # ============================================================
    raw_fractals = [""] * n  # '', 'TOP', 'BOTTOM'

    import math

    for i in range(1, n - 1):
        h_prev, h_curr, h_next = highs[i - 1], highs[i], highs[i + 1]
        l_prev, l_curr, l_next = lows[i - 1], lows[i], lows[i + 1]

        # 跳过包含 NaN 的 K 线组合
        if any(
            math.isnan(x) if isinstance(x, float) else False
            for x in [h_prev, h_curr, h_next, l_prev, l_curr, l_next]
        ):
            continue

        # 顶分型：中间K线的High比左右都高 (合并处理后，这也意味着 Low 也较高)
        if h_curr > h_prev and h_curr > h_next:
            raw_fractals[i] = "TOP"
        # 底分型：中间K线的Low比左右都低 (合并处理后，这也意味着 High 也较低)
        elif l_curr < l_prev and l_curr < l_next:
            raw_fractals[i] = "BOTTOM"

    raw_count = sum(1 for x in raw_fractals if x)
    print(f"原始分型数量: {raw_count}")

    # ============================================================
    # 生成候选信号显示列
    # 分型在 i 处形成，右肩在 i+1，信号标记在右肩 K 线上
    # ============================================================
    candidate_display = [""] * n

    for i in range(n):
        if raw_fractals[i]:
            right_shoulder = i + 1
            if right_shoulder < n:
                marker = "Tc" if raw_fractals[i] == "TOP" else "Bc"
                # 允许同一根K线上有多个标记（用逗号分隔）
                if candidate_display[right_shoulder]:
                    candidate_display[right_shoulder] += "," + marker
                else:
                    candidate_display[right_shoulder] = marker

    # 添加列到 DataFrame
    df["raw_fractal"] = raw_fractals
    df["candidate_display"] = candidate_display
    # 为兼容性保留 valid_fractal 列（与候选相同）
    df["valid_fractal"] = [""] * n

    # 保存
    df.to_csv(output_path, index=False, encoding="utf-8")

    # 统计
    print(f"分型识别完成。原始分型: {raw_count}")
    print(f"结果已保存至: {output_path}")


def process_strokes(input_path, output_path, save_plot_path=None):
    """
    从合并后的K线数据中：
    1. 识别原始分型（顶/底）
    2. 应用笔的规则过滤（顶底交替 + 极值更新 + 间隔约束）
    """
    print(f"读取合并后的K线数据: {input_path}")

    # 尝试多种编码
    try:
        df = pd.read_csv(input_path, encoding="utf-8")
    except UnicodeDecodeError:
        df = pd.read_csv(input_path, encoding="gbk")

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
    # 第一步：识别原始分型（纯3根K线组合）
    # 注：分型识别只看相邻3根K线，距离约束在笔过滤阶段处理
    # ============================================================
    raw_fractals = [""] * n  # '', 'TOP', 'BOTTOM'

    for i in range(1, n - 1):
        h_prev, h_curr, h_next = highs[i - 1], highs[i], highs[i + 1]
        l_prev, l_curr, l_next = lows[i - 1], lows[i], lows[i + 1]

        # 顶分型：中间K线的High比左右都高
        if h_curr > h_prev and h_curr > h_next:
            raw_fractals[i] = "TOP"
        # 底分型：中间K线的Low比左右都低
        elif l_curr < l_prev and l_curr < l_next:
            raw_fractals[i] = "BOTTOM"

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
    # 每个笔端点的确认信息: {fractal_idx: confirm_idx}
    # confirm_idx 是该分型被确认时的K线索引（即出现反向分型的那根K线）
    stroke_confirm_info = {}

    # 状态变量
    pending = None
    last_stroke_end = None
    # 被替换的候选列表
    replaced_candidates = []
    # 候选分型记录: [(fractal_idx, fractal_type, candidate_bar_idx), ...]
    # candidate_bar_idx 是该分型成为候选时的K线索引（= fractal_idx + 1，右肩K线）
    candidate_history = []
    # 当前候选分型 (pending 从未被确认，且不在 replaced_candidates 中)
    current_candidate = None

    for idx, f_type in fractal_points:

        if pending is None:
            if last_stroke_end is None:
                pending = (idx, f_type)
                # 记录候选历史：分型成为 pending 时就是候选状态
                candidate_bar = idx + 1
                if candidate_bar < n:
                    candidate_history.append((idx, f_type, candidate_bar))
                continue

            dist = idx - last_stroke_end[0]

            # 同向分型：极值比较（需检查新分型与上上笔终点的距离）
            if f_type == last_stroke_end[1]:
                # 计算与上上笔终点的距离（如果存在的话）
                prev_stroke_idx = strokes[-2][0] if len(strokes) >= 2 else -MIN_DIST
                dist_to_prev = idx - prev_stroke_idx

                if f_type == "TOP" and highs[idx] > highs[last_stroke_end[0]]:
                    # 只有当新分型与上上笔终点距离足够时才替换
                    if dist_to_prev >= MIN_DIST:
                        old = strokes.pop()
                        replaced_candidates.append(old)
                        strokes.append((idx, f_type))
                        last_stroke_end = (idx, f_type)
                        # 补录候选历史：这个新分型也是一个有效的候选点
                        candidate_bar = idx + 1
                        if candidate_bar < n:
                            candidate_history.append((idx, f_type, candidate_bar))
                elif f_type == "BOTTOM" and lows[idx] < lows[last_stroke_end[0]]:
                    if dist_to_prev >= MIN_DIST:
                        old = strokes.pop()
                        replaced_candidates.append(old)
                        strokes.append((idx, f_type))
                        last_stroke_end = (idx, f_type)
                        # 补录候选历史
                        candidate_bar = idx + 1
                        if candidate_bar < n:
                            candidate_history.append((idx, f_type, candidate_bar))
                continue

            # 反向分型：检查距离
            if dist < MIN_DIST:
                continue

            pending = (idx, f_type)
            # 记录候选历史
            candidate_bar = idx + 1
            if candidate_bar < n:
                candidate_history.append((idx, f_type, candidate_bar))
            continue

        # 已有待确认分型
        pending_idx, pending_type = pending

        if f_type == pending_type:
            # 同向分型：比较极值
            if f_type == "TOP":
                if highs[idx] > highs[pending_idx]:
                    replaced_candidates.append(pending)
                    pending = (idx, f_type)
                    # 记录候选历史：新的 pending 替代了旧的
                    candidate_bar = idx + 1
                    if candidate_bar < n:
                        candidate_history.append((idx, f_type, candidate_bar))
            elif f_type == "BOTTOM":
                if lows[idx] < lows[pending_idx]:
                    replaced_candidates.append(pending)
                    pending = (idx, f_type)
                    # 记录候选历史
                    candidate_bar = idx + 1
                    if candidate_bar < n:
                        candidate_history.append((idx, f_type, candidate_bar))
        else:
            # 反向分型：尝试确认pending
            if last_stroke_end is not None:
                dist = pending_idx - last_stroke_end[0]
                if dist < MIN_DIST:
                    # pending太近，直接忽略 (不算作 Tx/Bx，因为从未生效过)
                    # replaced_candidates.append(pending)  <-- 删除此行

                    if f_type == last_stroke_end[1]:
                        if f_type == "TOP" and highs[idx] > highs[last_stroke_end[0]]:
                            old = strokes.pop()
                            replaced_candidates.append(old)
                            strokes.append((idx, f_type))
                            last_stroke_end = (idx, f_type)
                        elif f_type == "BOTTOM" and lows[idx] < lows[last_stroke_end[0]]:
                            old = strokes.pop()
                            replaced_candidates.append(old)
                            strokes.append((idx, f_type))
                            last_stroke_end = (idx, f_type)
                        pending = None
                    else:
                        pending = (idx, f_type)
                    continue

            # 距离足够，准备确认 pending
            # 【关键验证】检查从 last_stroke_end 到 pending 的区间内是否存在更极端的价格
            # 如果存在，说明 pending 不是真正的极值点，这一笔无效
            is_valid_stroke = True
            if last_stroke_end is not None:
                start_idx = last_stroke_end[0]
                end_idx = pending_idx

                if pending_type == "TOP":
                    # 检查区间内是否有更高的 high
                    max_high_in_range = max(highs[start_idx : end_idx + 1])
                    if max_high_in_range > highs[pending_idx]:
                        is_valid_stroke = False
                elif pending_type == "BOTTOM":
                    # 检查区间内是否有更低的 low
                    min_low_in_range = min(lows[start_idx : end_idx + 1])
                    if min_low_in_range < lows[pending_idx]:
                        is_valid_stroke = False

            if is_valid_stroke:
                # 记录确认信息
                stroke_confirm_info[pending_idx] = idx

                strokes.append(pending)
                last_stroke_end = pending
                pending = (idx, f_type)
                # 记录候选历史：新的 pending 成为候选
                candidate_bar = idx + 1
                if candidate_bar < n:
                    candidate_history.append((idx, f_type, candidate_bar))
            else:
                # 笔无效：pending 不是真正的极值点
                # 【方案3】只回溯一层：取消 last_stroke_end，然后直接确认当前分型
                replaced_candidates.append(pending)
                if strokes:
                    old_stroke = strokes.pop()
                    replaced_candidates.append(old_stroke)

                # 回溯后，直接将当前反向分型确认为新的笔端点，不再验证
                # 这样可以避免级联取消
                strokes.append((idx, f_type))
                last_stroke_end = (idx, f_type)
                pending = None

    # 处理最后一个pending
    # pending 状态的分型是"候选分型"，尚未被反向分型确认
    if pending is not None:
        if last_stroke_end is not None:
            dist = pending[0] - last_stroke_end[0]
            if dist >= MIN_DIST:
                # 距离足够但尚未被反向分型确认
                # 这是一个有效的候选分型
                current_candidate = pending
            else:
                # 距离不够，不是有效候选
                pass
        else:
            # 没有 last_stroke_end，pending 作为第一个候选
            current_candidate = pending

    # ============================================================
    # 第三步：生成输出
    # ============================================================

    # 创建分型列：合并确认的和被替换的
    valid_fractals = [""] * n

    # 确认的笔端点用 T/B
    for idx, f_type in strokes:
        valid_fractals[idx] = f_type[0]  # 'TOP' -> 'T', 'BOTTOM' -> 'B'

    # 被替换的用 Tx/Bx
    for idx, f_type in replaced_candidates:
        valid_fractals[idx] = f_type[0] + "x"  # 'TOP' -> 'Tx', 'BOTTOM' -> 'Bx'

    # 当前候选分型用 Tc/Bc
    if current_candidate is not None:
        idx, f_type = current_candidate
        valid_fractals[idx] = f_type[0] + "c"  # 'TOP' -> 'Tc', 'BOTTOM' -> 'Bc'

    # 候选分型显示列：记录在右肩K线上的候选分型
    # 格式：Tc 或 Bc，表示该K线上应显示候选分型标记
    candidate_display = [""] * n
    for fractal_idx, fractal_type, display_bar_idx in candidate_history:
        marker_type = fractal_type[0] + "c"  # 'TOP' -> 'Tc', 'BOTTOM' -> 'Bc'
        # 可能多个候选在同一K线上，用逗号分隔
        if candidate_display[display_bar_idx]:
            candidate_display[display_bar_idx] += "," + marker_type
        else:
            candidate_display[display_bar_idx] = marker_type
    # 当前候选分型也加入显示列
    if current_candidate is not None:
        idx, f_type = current_candidate
        display_bar = idx + 1 if idx + 1 < n else idx
        marker_type = f_type[0] + "c"
        if candidate_display[display_bar]:
            candidate_display[display_bar] += "," + marker_type
        else:
            candidate_display[display_bar] = marker_type

    df["raw_fractal"] = raw_fractals
    df["valid_fractal"] = valid_fractals
    df["candidate_display"] = candidate_display

    # 保存
    df.to_csv(output_path, index=False, encoding="utf-8")

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
    all_markers += [(idx, f_type[0] + "x") for idx, f_type in replaced_candidates]  # 'Tx' or 'Bx'

    # 添加历史候选分型 (显示在右肩K线上)
    # candidate_history: [(fractal_idx, fractal_type, candidate_bar_idx), ...]
    for fractal_idx, fractal_type, candidate_bar_idx in candidate_history:
        marker_type = fractal_type[0] + "c"  # 'TOP' -> 'Tc', 'BOTTOM' -> 'Bc'
        all_markers.append(
            (candidate_bar_idx, marker_type, fractal_idx)
        )  # 第三个元素是原始分型位置

    # 当前候选分型 (最后一个 pending)
    if current_candidate is not None:
        idx, f_type = current_candidate
        candidate_bar = idx + 1 if idx + 1 < n else idx
        all_markers.append((candidate_bar, f_type[0] + "c", idx))  # 'Tc' or 'Bc'

    all_markers.sort(key=lambda x: x[0])  # 按索引排序

    plot_strokes(
        df, strokes, all_markers, col_dt, col_open, col_high, col_low, col_close, save_plot_path
    )


def identify_hubs(strokes, highs, lows):
    """
    识别中枢：找出连续3笔以上有价格重叠的区间

    中枢定义：至少3笔（4个端点），且存在价格重叠区间
    重叠区间 = max(所有笔的低点) ~ min(所有笔的高点)
    如果 max_low < min_high，则存在有效重叠

    返回: [(start_idx, end_idx, top, bottom), ...]
    """
    if len(strokes) < 4:  # 至少需要4个端点才能构成3笔
        return []

    hubs = []
    i = 0

    while i < len(strokes) - 3:  # 需要至少4个点（3笔）
        # 尝试从当前位置开始构建中枢
        # 取前3笔（4个端点）的价格范围
        stroke_ranges = []
        for j in range(3):  # 前3笔
            idx1, type1 = strokes[i + j]
            idx2, type2 = strokes[i + j + 1]

            # 根据笔的方向确定高低点
            if type1 == "BOTTOM":  # 向上笔
                stroke_low = lows[idx1]
                stroke_high = highs[idx2]
            else:  # 向下笔
                stroke_high = highs[idx1]
                stroke_low = lows[idx2]

            stroke_ranges.append((stroke_low, stroke_high))

        # 计算重叠区间: max(低点), min(高点)
        hub_bottom = max(r[0] for r in stroke_ranges)
        hub_top = min(r[1] for r in stroke_ranges)

        if hub_bottom < hub_top:  # 存在有效重叠
            hub_start = strokes[i][0]
            hub_end = strokes[i + 3][0]

            # 尝试扩展中枢：检查后续笔是否也在重叠区间内
            extend_idx = i + 4
            while extend_idx < len(strokes):
                idx_prev = strokes[extend_idx - 1][0]
                type_prev = strokes[extend_idx - 1][1]
                idx_curr = strokes[extend_idx][0]
                type_curr = strokes[extend_idx][1]

                # 计算新笔的范围
                if type_prev == "BOTTOM":  # 向上笔
                    new_low = lows[idx_prev]
                    new_high = highs[idx_curr]
                else:  # 向下笔
                    new_high = highs[idx_prev]
                    new_low = lows[idx_curr]

                # 检查是否与中枢有重叠
                if new_low < hub_top and new_high > hub_bottom:
                    hub_end = idx_curr
                    extend_idx += 1
                else:
                    break

            hubs.append(
                {"start_idx": hub_start, "end_idx": hub_end, "top": hub_top, "bottom": hub_bottom}
            )

            # 从中枢结束位置继续寻找下一个中枢
            i = extend_idx - 1
        else:
            i += 1

    return hubs


def plot_strokes(
    df, strokes, all_markers, col_dt, col_open, col_high, col_low, col_close, save_path=None
):
    """绘制带笔端点标注和S/R线的K线图"""
    print("\n开始绘制...")

    df[col_dt] = pd.to_datetime(df[col_dt])

    # 显示最后100根K线
    num_bars = 100
    if len(df) > num_bars:
        plot_df = df.iloc[-num_bars:].copy().reset_index(drop=True)
        offset = len(df) - num_bars
    else:
        plot_df = df.copy().reset_index(drop=True)
        offset = 0

    # 调整索引到 plot_df 的范围
    plot_strokes_only = [(idx - offset, t[0]) for idx, t in strokes]  # 仅用于连线
    # 处理2元组和3元组格式的标记
    plot_all_markers = []
    for marker in all_markers:
        if len(marker) == 3:
            idx, t, _ = marker  # 3元组: (display_idx, type, fractal_idx)
        else:
            idx, t = marker  # 2元组: (idx, type)
        plot_all_markers.append((idx - offset, t))

    dates = plot_df[col_dt]
    opens = plot_df[col_open]
    closes = plot_df[col_close]
    highs = plot_df[col_high]
    lows = plot_df[col_low]

    # 根据数据量调整图表宽度
    fig_width = max(14, len(plot_df) * 0.12)
    fig, ax = plt.subplots(figsize=(fig_width, 8))

    width = 0.6
    width2 = 0.05

    up = closes >= opens
    down = closes < opens
    col_up, col_down = "red", "green"

    # 绘制K线
    ax.bar(plot_df.index[up], highs[up] - lows[up], width2, bottom=lows[up], color=col_up)
    ax.bar(plot_df.index[down], highs[down] - lows[down], width2, bottom=lows[down], color=col_down)
    ax.bar(plot_df.index[up], (closes[up] - opens[up]).abs(), width, bottom=opens[up], color=col_up)
    ax.bar(
        plot_df.index[down],
        (closes[down] - opens[down]).abs(),
        width,
        bottom=closes[down],
        color=col_down,
    )

    # 绘制所有分型标记
    for plot_idx, f_type in plot_all_markers:
        if plot_idx < 0 or plot_idx >= len(plot_df):
            continue

        is_cancelled = "x" in f_type
        base_type = f_type.replace("x", "")

        if base_type == "T":
            color = "gray" if is_cancelled else "black"
            price = highs.iloc[plot_idx]
            label = "Tx" if is_cancelled else f"T {price:.2f}"
            ax.annotate(
                label,
                xy=(plot_idx, price),
                xytext=(plot_idx + 0.3, price * 1.001),
                ha="left",
                fontsize=8,
                fontweight="bold",
                color=color,
            )
        elif base_type == "B":
            color = "gray" if is_cancelled else "blue"
            price = lows.iloc[plot_idx]
            label = "Bx" if is_cancelled else f"B {price:.2f}"
            ax.annotate(
                label,
                xy=(plot_idx, price),
                xytext=(plot_idx + 0.3, price * 0.998),
                ha="left",
                fontsize=8,
                fontweight="bold",
                color=color,
            )

    # 绘制 B->T 连线 (上涨笔)
    # stroke list example: [(idx, 'T'), (idx, 'B')]
    # plot_strokes_only 已经是相对索引 (idx-offset, type)

    sorted_strokes = sorted(plot_strokes_only, key=lambda x: x[0])

    for i in range(len(sorted_strokes) - 1):
        curr_idx, curr_type = sorted_strokes[i]
        next_idx, next_type = sorted_strokes[i + 1]

        # 过滤: 必须在绘图范围内 (虽然 plot_strokes_only 可能会有负索引，但在 loop 前应该已经处理?
        # 这里 plot_strokes_only 生成时只是减去了 offset, 没有过滤范围，所以必须检查)
        if curr_idx < 0 or curr_idx >= len(plot_df) or next_idx < 0 or next_idx >= len(plot_df):
            continue

        # 仅连接 B -> T
        if curr_type == "B" and next_type == "T":
            # B在low, T在high
            y1 = lows.iloc[curr_idx]
            y2 = highs.iloc[next_idx]

            ax.plot([curr_idx, next_idx], [y1, y2], color="purple", linewidth=1.5, alpha=0.8)

    # 绘制所有分型标记 (T/B Annotations)

    step = 5
    ax.set_xticks(range(0, len(plot_df), step))
    ax.set_xticklabels([d.strftime("%Y-%m-%d") for d in dates[::step]], rotation=45, fontsize=8)

    # 给Y轴留出边距，确保最高/最低点和标签不贴边
    y_min, y_max = lows.min(), highs.max()
    y_margin = (y_max - y_min) * 0.05  # 5% 边距
    ax.set_ylim(y_min - y_margin, y_max + y_margin)

    ax.set_title("Stroke Identification (Bill Williams / Chan Theory)", fontsize=14)
    ax.set_ylabel("Price")

    if save_path:
        # 保存 PNG（高DPI）
        plt.savefig(save_path, dpi=200, bbox_inches="tight")
        print(f"图表已保存至: {save_path}")

        # 同时保存 SVG 矢量图
        svg_path = save_path.replace(".png", ".svg")
        plt.savefig(svg_path, format="svg", bbox_inches="tight")
        print(f"矢量图已保存至: {svg_path}")
        plt.close()
    else:
        plt.show()
