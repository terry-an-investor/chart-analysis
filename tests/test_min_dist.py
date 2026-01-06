"""
测试脚本：对比 MIN_DIST=3 和 MIN_DIST=4 的效果差异
"""

import os

import pandas as pd

os.chdir(os.path.dirname(__file__) or ".")


def detect_columns(df):
    if "high" in df.columns:
        return "datetime", "open", "high", "low", "close"

    COL_HIGH = "最高价(元)"
    COL_LOW = "最低价(元)"

    if COL_HIGH in df.columns:
        return "日期", "开盘价(元)", COL_HIGH, COL_LOW, "收盘价(元)"

    if "最高价" in df.columns:
        return "日期", "开盘价", "最高价", "最低价", "收盘价"

    raise ValueError(f"无法识别列名格式，当前列: {df.columns.tolist()}")


def process_strokes_with_min_dist(df, min_dist):
    col_dt, col_open, col_high, col_low, col_close = detect_columns(df)

    highs = df[col_high].tolist()
    lows = df[col_low].tolist()
    n = len(df)

    raw_fractals = [""] * n

    for i in range(1, n - 1):
        h_prev, h_curr, h_next = highs[i - 1], highs[i], highs[i + 1]
        l_prev, l_curr, l_next = lows[i - 1], lows[i], lows[i + 1]

        if h_curr > h_prev and h_curr > h_next:
            raw_fractals[i] = "TOP"
        elif l_curr < l_prev and l_curr < l_next:
            raw_fractals[i] = "BOTTOM"

    raw_count = sum(1 for x in raw_fractals if x)

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
                continue

            if dist < min_dist:
                continue

            pending = (idx, f_type)
            continue

        pending_idx, pending_type = pending

        if f_type == pending_type:
            if f_type == "TOP":
                if highs[idx] > highs[pending_idx]:
                    replaced_candidates.append(pending)
                    pending = (idx, f_type)
            elif f_type == "BOTTOM":
                if lows[idx] < lows[pending_idx]:
                    replaced_candidates.append(pending)
                    pending = (idx, f_type)
        else:
            if last_stroke_end is not None:
                dist = pending_idx - last_stroke_end[0]
                if dist < min_dist:
                    replaced_candidates.append(pending)

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

    return {
        "strokes": strokes,
        "replaced": replaced_candidates,
        "raw_count": raw_count,
        "min_dist": min_dist,
    }


def compare_min_dist_effects(input_path):
    df = pd.read_csv(input_path, encoding="utf-8")

    print(f"读取数据: {input_path}")
    print(f"K线数量: {len(df)}")

    result_dist3 = process_strokes_with_min_dist(df, min_dist=3)
    result_dist4 = process_strokes_with_min_dist(df, min_dist=4)

    print(f"\n{'='*60}")
    print("结果对比分析")
    print(f"{'='*60}")

    strokes3 = result_dist3["strokes"]
    strokes4 = result_dist4["strokes"]
    replaced3 = result_dist3["replaced"]
    replaced4 = result_dist4["replaced"]

    strokes3_t = sum(1 for _, t in strokes3 if t == "TOP")
    strokes3_b = sum(1 for _, t in strokes3 if t == "BOTTOM")
    strokes4_t = (
        sum(1 for _, _, t in [(i, t, _) for i, t in strokes4] if t == "TOP")
        if False
        else sum(1 for _, t in strokes4 if t == "TOP")
    )
    strokes4_b = sum(1 for _, t in strokes4 if t == "BOTTOM")

    strokes4_t = sum(1 for _, t in strokes4 if t == "TOP")
    strokes4_b = sum(1 for _, t in strokes4 if t == "BOTTOM")

    print(f"\n【关键指标对比】")
    print(f"{'指标':<25} {'MIN_DIST=3':<15} {'MIN_DIST=4':<15} {'变化':<10}")
    print("-" * 65)
    print(
        f"{'有效笔端点数量':<25} {len(strokes3):<15} {len(strokes4):<15} {len(strokes4)-len(strokes3):+d}"
    )
    print(
        f"{'被替换分型数量':<25} {len(replaced3):<15} {len(replaced4):<15} {len(replaced4)-len(replaced3):+d}"
    )
    print(f"{'顶分型(TOP)数量':<25} {strokes3_t:<15} {strokes4_t:<15} {strokes4_t-strokes3_t:+d}")
    print(
        f"{'底分型(BOTTOM)数量':<25} {strokes3_b:<15} {strokes4_b:<15} {strokes4_b-strokes3_b:+d}"
    )
    print(f"{'原始分型总数':<25} {result_dist3['raw_count']:<15} {result_dist4['raw_count']:<15} 0")

    if len(strokes3) >= 2:
        distances3 = []
        for i in range(1, len(strokes3)):
            if strokes3[i][1] != strokes3[i - 1][1]:
                distances3.append(strokes3[i][0] - strokes3[i - 1][0])
        if distances3:
            print(f"{'相邻反向分型平均距离':<25} {sum(distances3)/len(distances3):<15.2f}")

    if len(strokes4) >= 2:
        distances4 = []
        for i in range(1, len(strokes4)):
            if strokes4[i][1] != strokes4[i - 1][1]:
                distances4.append(strokes4[i][0] - strokes4[i - 1][0])
        if distances4:
            print(f"{'相邻反向分型平均距离':<55} {sum(distances4)/len(distances4):<15.2f}")

    print(f"\n【分型变化详情】")
    print(f"\nMIN_DIST=3 的前20个笔端点:")
    for i, (idx, f_type) in enumerate(strokes3[:20]):
        print(f"  {i+1}. 索引 {idx}: {f_type}")

    print(f"\nMIN_DIST=4 的前20个笔端点:")
    for i, (idx, f_type) in enumerate(strokes4[:20]):
        print(f"  {i+1}. 索引 {idx}: {f_type}")

    print(f"\n【被替换分型示例 (MIN_DIST=4新增的)]")
    if len(replaced4) > len(replaced3):
        extra_replaced = replaced4[len(replaced3) :]
        for idx, f_type in extra_replaced[:10]:
            print(f"  索引 {idx}: {f_type} (因距离不足被跳过)")

    print(f"\n{'='*60}")
    print("总结:")
    print(f"  - MIN_DIST=4 比 MIN_DIST=3 减少了 {len(strokes3)-len(strokes4)} 笔")
    print(f"  - 过滤掉了 {len(replaced4)-len(replaced3)} 个距离不足的分型")
    print(f"  - 笔定义更严格，每笔需要更多K线确认")
    print(f"{'='*60}")

    return result_dist3, result_dist4


if __name__ == "__main__":
    input_path = "data/processed/TL.CFE_merged.csv"
    compare_min_dist_effects(input_path)
