我是 **Al Brooks Quant Architect**。

你觉得“怪怪的”是非常正常的。我刚刚审查了你的 `structure.py` 和 `interactive.py` 的代码逻辑，发现目前的实现虽然数学上是严谨的（无未来函数），但在**视觉呈现**和**交易逻辑**上存在两个核心违和感。

这就是“工程师思维”和“交易员思维”的冲突点。

### 核心诊断：为什么看起来“怪怪的”？

#### 1. 视觉上的“上帝视角” (The Visual Cheat)

在 `interactive.py` 中，你为了让图表好看，做了一个 `shift(-swing_window)` 的操作：

```python
# interactive.py
adjusted_major_high = major_high.shift(-swing_window)

```

* **现象**：阶梯线（Major High）会在最高点的那根 K 线**当场**发生变化。
* **违和感**：在实盘中，直到 5 根 K 线之后，你才知道那是高点。但图表上，红线在顶峰那一刻就变了。这让你看着像是一个“重绘”指标（类似 ZigZag），虽然你的底层数据没重绘，但**视觉欺骗了你**，让你觉得“这太完美了，不可能做到”。

#### 2. 逻辑上的“过度敏感” (Minor vs Major)

在 `structure.py` 中，你把**每一个** Swing Point 都当成了 Structure Level：

```python
# structure.py
df.at[idx, 'major_high'] = curr_price  # 只要是分型，就更新阻力位

```

* **现象**：在牛市回调中，如果出现一个微小的 Lower High (LH)，你的红线（阻力位）会立刻**向下跳水**压住价格。
* **违和感**：Al Brooks 会告诉你，在牛市里，**阻力位是前高 (HH)**。回调中的 LH 只是一个次级波段（Minor Move），不应该把作为结构性防线的 Major High 拉下来。
* **结果**：你的图表看起来像是一个**紧缩的牢笼**，价格稍微一抖动，天花板就塌下来了，这不符合“趋势”的定义。

---

### 解决方案：引入“趋势状态过滤”

我们需要修改 `structure.py` 中的 `classify_swings`，让它变聪明。

**Al Brooks 逻辑修正：**

* **Bull Trend (牛市中)**：
* **Major Low (支撑)**：跟随 Higher Low (HL) 上移。（移动止损）
* **Major High (阻力)**：**死死钉在最高点 (HH)**。如果出现 LH，**不要**降低阻力线，除非趋势反转。


* **Bear Trend (熊市中)**：
* **Major High (阻力)**：跟随 Lower High (LH) 下移。
* **Major Low (支撑)**：**死死钉在最低点 (LL)**。



### 代码迭代 (Phase 2.1)

请用以下代码替换 `src/analysis/structure.py` 中的 `classify_swings` 函数。这实现了**“Major Level Trailing Logic” (结构位追踪逻辑)**。

```python
def classify_swings(
    df: pd.DataFrame,
    tolerance_pct: float = PRICE_TOLERANCE_PCT
) -> pd.DataFrame:
    """
    [Updated] 结构状态机: 区分 Major vs Minor
    
    改进逻辑:
    1. 引入 'trend_bias' (趋势倾向)。
    2. Bull Mode: 只上移 Major Low，Major High 保持在最高点 (HH)。
    3. Bear Mode: 只下移 Major High，Major Low 保持在最低点 (LL)。
    4. 只有当反向突破发生时，才切换模式并重置 Level。
    """
    if 'swing_high_confirmed' not in df.columns:
        df = detect_swings(df)
    
    df = df.copy()
    
    # 初始化
    df['swing_type'] = pd.Series([np.nan] * len(df), dtype=object)
    df['major_high'] = np.nan
    df['major_low'] = np.nan
    df['trend_bias'] = 0  # 1=Bull, -1=Bear
    
    # 状态变量
    last_h_price = -np.inf
    last_l_price = np.inf
    
    # 结构位 (Trailing Levels)
    # 初始状态设宽一点，避免一开始就被穿透
    curr_structure_high = np.inf 
    curr_structure_low = -np.inf
    curr_bias = 0 
    
    # 提取事件
    high_indices = df.index[df['swing_high_confirmed']].tolist()
    low_indices = df.index[df['swing_low_confirmed']].tolist()
    events = sorted(
        [(i, 'high') for i in high_indices] + 
        [(i, 'low') for i in low_indices], 
        key=lambda x: x[0]
    )
    
    for idx, event_type in events:
        if event_type == 'high':
            price = df.at[idx, 'swing_high_price']
            
            # 1. 标记 Swing Type (几何属性)
            if last_h_price > 0:
                if abs(price - last_h_price) / last_h_price <= tolerance_pct: label = 'DT'
                elif price > last_h_price: label = 'HH'
                else: label = 'LH'
            else: label = 'HH' # 初始
            
            last_h_price = price
            df.at[idx, 'swing_type'] = label
            
            # 2. 结构位逻辑 (Al Brooks Logic)
            # 如果价格突破了当前的 Major High -> 确认 Bull Trend
            if price > curr_structure_high and curr_bias <= 0:
                curr_bias = 1 # 转多
                curr_structure_low = last_l_price # 支撑位设为最近的低点
            
            # 更新 Major High:
            # - 如果是 Bull: 只有创新高 (HH) 才上移 Major High。出现 LH 时保持原高点不变！
            # - 如果是 Bear: 只要出现 High 就更新 (作为移动止损)
            if curr_bias == 1:
                if price > curr_structure_high:
                    curr_structure_high = price
            else: # Bear or Neutral
                curr_structure_high = price

        elif event_type == 'low':
            price = df.at[idx, 'swing_low_price']
            
            # 1. 标记 Swing Type
            if last_l_price < np.inf:
                if abs(price - last_l_price) / last_l_price <= tolerance_pct: label = 'DB'
                elif price < last_l_price: label = 'LL'
                else: label = 'HL'
            else: label = 'LL'
            
            last_l_price = price
            df.at[idx, 'swing_type'] = label
            
            # 2. 结构位逻辑
            # 如果价格跌破了当前的 Major Low -> 确认 Bear Trend
            if price < curr_structure_low and curr_bias >= 0:
                curr_bias = -1 # 转空
                curr_structure_high = last_h_price # 阻力位设为最近的高点
            
            # 更新 Major Low:
            # - 如果是 Bear: 只有创新低 (LL) 才下移 Major Low。
            # - 如果是 Bull: 只要出现 Low 就更新 (作为移动止损)
            if curr_bias == -1:
                if price < curr_structure_low:
                    curr_structure_low = price
            else: # Bull or Neutral
                curr_structure_low = price
                
        # 记录每一步的状态
        df.at[idx, 'major_high'] = curr_structure_high
        df.at[idx, 'major_low'] = curr_structure_low
        df.at[idx, 'trend_bias'] = curr_bias

    # 填充
    df['major_high'] = df['major_high'].ffill()
    df['major_low'] = df['major_low'].ffill()
    df['trend_bias'] = df['trend_bias'].ffill().fillna(0).astype(int)
    
    return df

```

### 为什么这样改就不怪了？

1. **容错性**：在牛市（`trend_bias=1`）中，即使出现了 LH（Lower High），`major_high` 依然维持在之前的 HH 高度。这在图表上会形成一个**平顶的天花板**，而不是每次回调都压下来的盖子。这符合“蓄势待发”的视觉感受。
2. **止损性**：在牛市中，`major_low` 会随着每一个 HL 不断上移。图表底部的绿线会呈现阶梯状上升，这正是**Trailing Stop**的样子。

**建议操作**：

1. 更新 `src/analysis/structure.py`。
2. 重新运行 `python run_pipeline.py data/raw/PDD_O.xlsx`。
3. 你会发现图表上的绿线（Major Low）像阶梯一样稳步向上，而红线（Major High）在突破前会保持水平，这看起来就像真正的“价格行为”了。

---
我是 **Al Brooks Quant Architect**。

你的直觉非常敏锐，简直是交易员的本能反应。

**你说得完全正确。** 如果 Major Low 像阶梯一样每出现一个 Higher Low 就上移，那你其实是在追踪 **Minor Swings (次级波段)**，而不是 **Major Structure (主要结构)**。

在 Al Brooks 的《Trends》中，关于 **Major Trend Reversal (MTR)** 有一个核心定义：

> "A Major Higher Low is the start of a move that leads to a **NEW HIGH**."
> (一个主要更高低点，必须是引发了**新高**的那一波行情的起点。)

如果一个 Higher Low 后面没有创新高，它就只是一个 **Leg in a Trading Range** (震荡区间里的一条腿)，或者是 **Minor Pullback**。如果你把止损（Major Low）移到这里，你会在复杂的震荡中被频繁扫地出局（Whipsaw）。

---

### 核心修正：引入“突破确认机制” (Breakout Confirmation)

我们要把逻辑从 **"出现 HL 就上移"** 修改为 **"创新高后，才把 Major Low 移到最近的 HL"**。

#### 逻辑对比 (Visual Logic)

* **V1 (过于敏感 - 你觉得怪的版本)**:
* 低点 A -> 低点 B (B>A) -> **上移 Major Low 到 B** -> 价格没创新高就跌破 B -> **判定趋势反转 (错误！)**


* **V2 (Al Brooks 标准版)**:
* 低点 A -> 低点 B (B>A) -> **Major Low 保持在 A 不动** (视 B 为潜在震荡) -> 价格突破前高 -> **确认趋势延续，瞬间将 Major Low 上移到 B**。



这就像攀岩：**只有当你的一只手抓住了更高的新岩石（创新高），你才把脚下的安全扣（Major Low）往上移一格。** 如果你没抓住新的岩石，你的安全扣应该留在原地不动。

---

### 代码迭代 (Phase 2.2)

请用以下代码更新 `src/analysis/structure.py` 中的 `classify_swings`。

这个版本实现了 **"Breakout Confirmation" (突破确认)** 逻辑，Major Levels 的变化会显著减少，变得更加像“楼层”而不是“楼梯”。

```python
def classify_swings(
    df: pd.DataFrame,
    tolerance_pct: float = PRICE_TOLERANCE_PCT
) -> pd.DataFrame:
    """
    [Updated V2] 结构状态机: 突破确认逻辑 (Breakout Confirmation)
    
    Al Brooks 核心原则:
    - Major Low 的上移，必须由"价格创出新高 (New High)"来确认。
    - Major High 的下移，必须由"价格创出新低 (New Low)"来确认。
    
    这意味着: 在没有创新高之前，中间所有的 Higher Lows 都只是 Minor Swings (次级折返)，
    不应改变结构性的支撑位。
    """
    if 'swing_high_confirmed' not in df.columns:
        df = detect_swings(df)
    
    df = df.copy()
    
    # 初始化
    df['swing_type'] = pd.Series([np.nan] * len(df), dtype=object)
    df['major_high'] = np.nan
    df['major_low'] = np.nan
    df['trend_bias'] = 0  # 1=Bull, -1=Bear
    
    # 状态变量
    last_h_price = -np.inf
    last_l_price = np.inf
    
    # "候选" Swing Points (Candidates)
    # 这些是最近出现的 HL 或 LH，但还没"转正"成为 Major Level
    candidate_major_low = -np.inf
    candidate_major_high = np.inf
    
    # 当前生效的结构位 (Active Structure Levels)
    # 初始给个很宽的范围
    active_major_high = df['high'].max() * 1.5 
    active_major_low = df['low'].min() * 0.5
    
    curr_bias = 0 
    
    # 提取事件流
    high_indices = df.index[df['swing_high_confirmed']].tolist()
    low_indices = df.index[df['swing_low_confirmed']].tolist()
    events = sorted(
        [(i, 'high') for i in high_indices] + 
        [(i, 'low') for i in low_indices], 
        key=lambda x: x[0]
    )
    
    for idx, event_type in events:
        if event_type == 'high':
            price = df.at[idx, 'swing_high_price']
            
            # 1. 标记 Swing Type
            if last_h_price > 0:
                if abs(price - last_h_price) / last_h_price <= tolerance_pct: label = 'DT'
                elif price > last_h_price: label = 'HH'
                else: label = 'LH'
            else: label = 'HH'
            
            last_h_price = price
            df.at[idx, 'swing_type'] = label
            
            # 更新候选 Major High (最新的 High 总是阻力候选)
            candidate_major_high = price

            # --- 核心逻辑: Bull Breakout Check ---
            # 如果这是一个 HH，且突破了当前的 active_major_high
            # 说明之前的那个 candidate_major_low 确实起到了支撑作用，转正！
            if curr_bias == 1:
                if price > active_major_high:
                    # 只有创新高了，才把支撑位上移到最近的那个 Low
                    if candidate_major_low > active_major_low:
                        active_major_low = candidate_major_low
                    # 同时更新阻力位为当前价格 (作为新的天花板)
                    active_major_high = price
            
            # --- 核心逻辑: Bear Trend Reversal Check ---
            # 如果在熊市中反弹突破了 active_major_high -> 趋势反转为多
            elif curr_bias == -1:
                if price > active_major_high:
                    curr_bias = 1 # Flip to Bull
                    active_major_low = candidate_major_low # 最近的低点成为新支撑
                    active_major_high = price
            
            # 初始化阶段
            elif curr_bias == 0:
                 active_major_high = price

        elif event_type == 'low':
            price = df.at[idx, 'swing_low_price']
            
            # 1. 标记 Swing Type
            if last_l_price < np.inf:
                if abs(price - last_l_price) / last_l_price <= tolerance_pct: label = 'DB'
                elif price < last_l_price: label = 'LL'
                else: label = 'HL'
            else: label = 'LL'
            
            last_l_price = price
            df.at[idx, 'swing_type'] = label
            
            # 更新候选 Major Low (最新的 Low 总是支撑候选)
            candidate_major_low = price
            
            # --- 核心逻辑: Bear Breakout Check ---
            # 如果这是一个 LL，且跌破了 active_major_low
            # 说明之前的 candidate_major_high 有效，转正！
            if curr_bias == -1:
                if price < active_major_low:
                    # 只有创新低了，才把阻力位下移到最近的那个 High
                    if candidate_major_high < active_major_high:
                        active_major_high = candidate_major_high
                    active_major_low = price
            
            # --- 核心逻辑: Bull Trend Reversal Check ---
            # 如果在牛市中跌破了 active_major_low -> 趋势反转为空
            elif curr_bias == 1:
                if price < active_major_low:
                    curr_bias = -1 # Flip to Bear
                    active_major_high = candidate_major_high # 最近的高点成为新阻力
                    active_major_low = price
            
            # 初始化阶段
            elif curr_bias == 0:
                active_major_low = price
                
        # 记录状态
        df.at[idx, 'major_high'] = active_major_high
        df.at[idx, 'major_low'] = active_major_low
        df.at[idx, 'trend_bias'] = curr_bias

    # 填充
    df['major_high'] = df['major_high'].ffill()
    df['major_low'] = df['major_low'].ffill()
    df['trend_bias'] = df['trend_bias'].ffill().fillna(0).astype(int)
    
    return df

```

### 这个版本会有什么变化？

1. **更稳定的 Major Low**: 在拼多多 (PDD) 这种波动剧烈的图表上，你可能会看到连续出现 3 个 Higher Low (HL)，但 Major Low (绿线) **纹丝不动**。
2. **阶梯更宽**: 直到某一根阳线终于**突破前高 (HH)**，绿线才会突然“跳”上来，对齐到最近的那个低点。
3. **符合 Al Brooks 心理学**: 这模拟了机构投资者的止损逻辑——“我有浮盈了，但我不会轻易收紧止损，直到市场证明这波上涨已经稳了（Breakout），我再把止损移上来锁定利润。”

请更新代码并重新生成图表。这次的 `structure` 线条应该会让你觉得“稳重”多了。