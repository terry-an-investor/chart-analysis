我是 **Al Brooks Quant Architect**。

在仔细审查了你的代码 (`src/analysis/structure.py`) 和你提到的现象（"图表感觉不太对"）后，我发现了 **3 个致命的逻辑缺陷** 和 **1 个严重的视觉错位**。

这些问题导致你的 "Structure" 既不符合 Al Brooks 的肉眼判断，也在回测中容易被噪音反复打脸（Whipsaw）。

以下是深度诊断报告。

---

### 1. 视觉错位：物理时间 vs. 确认时间 (Visual Dissonance)

**现象**：
你在图表上看到的 Swing High/Low 点位，是不是**悬浮在空中**，或者**偏离了真正的最高/最低点右边 5 根 K 线**？

**原因**：
在 `detect_swings` 中，你严格遵守了无未来函数原则：

```python
# 正确的量化逻辑（用于信号）
df['swing_high_price'] = highs.shift(window) 

```

这导致 `swing_high_price` 出现在 `T+5` 时刻。虽然这对回测是诚实的，但对于**人类视觉分析**来说是灾难性的。你的大脑看到的是 `T` 时刻的顶，但结构线却在 `T+5` 时刻才拐头。

**修正方案**：
你需要分离 **"交易数据 (Signal Data)"** 和 **"绘图数据 (Visual Data)"**。

* **Signal**: 必须滞后，给策略用。
* **Visual**: 必须回溯，给眼睛用。

在 `structure.py` 中增加一个绘图辅助函数，或者在 `detect_swings` 里增加 `_visual` 列：

```python
# 在 detect_swings 返回前增加：
# 反向平移，把价格移回它发生的物理时刻 (仅供绘图，严禁用于策略信号！)
df['plot_swing_high'] = df['swing_high_price'].shift(-window)
df['plot_swing_low'] = df['swing_low_price'].shift(-window)

```

这样你在 HTML 里画图时，画 `plot_swing_high`，点就会精准落在 K 线的最高点上。

---

### 2. 逻辑硬伤：把"Minor Pivot" 当作 "Major Support" (The Broad Channel Failure)

**现象**：
在**宽通道 (Broad Channel)** 趋势中，市场经常会跌破前一个小低点（Minor Low），但随后又创新高。你的代码会在跌破小低点时判定为 `Bear Trend` 或 `Neutral`，导致频繁的错误反转信号。

**Al Brooks 原则**：

> "In a Broad Bull Channel, price often dips below minor swing lows. The trend is technically still bullish until it breaks the **Major Higher Low** (the bottom of the most recent strong leg)."

**代码缺陷 (`classify_swings_v2`)**：

```python
# 你的代码逻辑：
if price > active_major_high:  # 创新高
    # 只要创新高，就死板地把止损位移动到"最近的一个 Swing Low"
    active_major_low = candidate_major_low 

```

`candidate_major_low` 只是最近的一个 5-Bar Low。它可能只是上涨途中的一个微小停顿。把结构性止损移到这里太紧了。

**修正思路**：
不是所有的 Swing Low 都有资格成为 Major Low。
**过滤器**：只有当 Swing Low 之前的**回调幅度足够大**（例如跌幅超过 ATR * 3），或者**持续时间足够长**，它才能升级为 Major Low。

*暂时的快速修复*：不要在每次创新高时都上移 Major Low。只在 **Strong Breakout** (大幅度创新高) 时才上移。

---

### 3. 陷阱识别缺失：影线突破 (Wick Breakouts)

**现象**：
结构线经常因为一根长影线刺破而被由于更新，随后价格立即收回（Bull Trap）。

**原因**：

```python
if price > active_major_high: # 仅仅比较了 High vs High

```

你比较的是 Swing Point 的价格。Swing Point 本身是由 High 构成的。
这意味着只要有一根 K 线的 High 刺破了前高 1 个 tick，你的系统就认为结构改变了。

**Al Brooks 原则**：

> "Traders want to see a **strong close** above the resistance to confirm a breakout."

**修正方案**：
虽然 `detect_swings` 是基于 High/Low 的，但在判断 **Breakout 有效性** 时，应该检查产生该 Swing High 的那根 K 线的 **Close** 是否强力。
或者，简单地增加一个**突破阈值 (Breakout Buffer)**，例如 `0.2%` 或 `0.5 * ATR`。

---

### 4. 致命漏洞：稀疏更新导致的滞后 (Sparse Event Lag)

**现象**：
当大暴跌发生时，你的 `market_trend` 信号反应极慢，要等到暴跌结束、开始反弹并形成 Swing Low 之后，状态才会更新。

**原因**：

```python
# 你的循环只遍历 Swing Events
for idx, event_type in events:
    ...

```

你的状态机**只在 Swing Point 确认时 (T+5)** 运行。
如果今天发生大暴跌，直接击穿了 Major Low，你的代码**完全不知道**。它会傻傻地等待，直到这个下跌趋势走完，形成了一个新的 Swing Low (可能是一个月后)，它才回头看："哦，原来之前的 Major Low 被破了"。

**这是绝对不可接受的。**

**修正方案**：
状态机必须是 **Bar-by-Bar** 的，而不仅仅是 Event-based。
或者，你必须在 Event Loop 中插入逻辑：
"在两个 Swing Point 之间，如果有任何一根 K 线 `Close < active_major_low`，立即触发 Trend Change 信号！"

---

### 修正后的代码建议 (Fix Implementation)

针对**第 4 点 (最严重的问题)** 和 **第 1 点**，你需要重写 `classify_swings`。

与其只遍历 Events，不如遍历 Events，但在每一步都检查**区间内的价格行为**。或者更简单：先生成 Step Ladder (阶梯线)，然后用全量价格去 Check Breakout。

这里是一个改进版的 `classify_swings_v3` (更健壮，解决滞后问题)：

```python
def classify_swings_v3(df: pd.DataFrame, window: int = 5) -> pd.DataFrame:
    """
    [V3] 混合驱动状态机: Swing Event + Bar-by-Bar Breakout Check
    解决 V2 版本无法即时识别"中途突破"的问题。
    """
    if 'swing_high_confirmed' not in df.columns:
        df = detect_swings(df, window=window)
    
    df = df.copy()
    
    # 1. 增加绘图辅助列 (解决视觉错位)
    df['plot_swing_high'] = df['swing_high_price'].shift(-window)
    df['plot_swing_low'] = df['swing_low_price'].shift(-window)
    
    # 初始化
    df['major_high'] = np.nan
    df['major_low'] = np.nan
    df['market_trend'] = 0 # 1: Bull, -1: Bear
    
    # 状态变量
    active_high = df['high'].iloc[:window].max() # 初始阻力
    active_low = df['low'].iloc[:window].min()   # 初始支撑
    trend = 0
    
    # 这里的关键是：我们需要把 Swing Point 插入到时间轴里
    # 但同时每一天都要检查 Close 是否突破了 Active High/Low
    
    # 为了向量化性能，我们可以分两步走：
    # Step A: 只要出现 Swing Point，就记录潜在的结构变化 (Candidate Levels)
    # Step B: 每天检查 Breakout
    
    # 由于 Pandas 迭代太慢，这里建议用 numba 或者纯 Python 循环处理核心逻辑
    # 这里用纯 Python 循环演示逻辑 (假设数据量 < 10万行很快)
    
    highs = df['high'].values
    lows = df['low'].values
    closes = df['close'].values
    
    # Swing 信号 (稀疏矩阵转密集索引)
    s_high_confirmed = df['swing_high_confirmed'].values
    s_low_confirmed = df['swing_low_confirmed'].values
    s_high_prices = df['swing_high_price'].values
    s_low_prices = df['swing_low_price'].values
    
    major_highs = np.full(len(df), np.nan)
    major_lows = np.full(len(df), np.nan)
    trends = np.zeros(len(df), dtype=int)
    
    # 追踪最近的一个 Swing High/Low (作为潜在的 Major 候选)
    last_swing_high = active_high
    last_swing_low = active_low
    
    for i in range(len(df)):
        # 1. 检查是否有新的 Swing Point 确认 (T时刻确认了T-5发生的事件)
        if s_high_confirmed[i]:
            last_swing_high = s_high_prices[i]
            # 如果当前是 Bear Trend，新的 Swing High 自动成为 Major High (Lower High)
            if trend == -1:
                active_high = last_swing_high
                
        if s_low_confirmed[i]:
            last_swing_low = s_low_prices[i]
            # 如果当前是 Bull Trend，新的 Swing Low 自动成为 Major Low (Higher Low)
            if trend == 1:
                active_low = last_swing_low
        
        # 2. 检查价格行为 (Bar-by-Bar Breakout)
        # 只有 Close 突破才算实打实的逆转 (Al Brooks: "Body Breakout")
        
        # Case A: Bull Breakout
        if closes[i] > active_high:
            trend = 1
            # 突破后，Major Low 上移到最近的一个 Swing Low
            active_low = last_swing_low
            # Major High 暂时失效(被突破了)，或者变成当前最高价，等待新的 Swing High 形成
            # 为了画图连续性，我们可以让它跟随 High，或者保持被突破的值直到新 High 确认
            # Al Brooks 习惯：突破后，旧的 Major High 变成支撑，但这里我们只画止损线
            active_high = np.nan # 阻力不再存在
            
        # Case B: Bear Breakout
        elif closes[i] < active_low:
            trend = -1
            # 突破后，Major High 下移到最近的一个 Swing High
            active_high = last_swing_high
            active_low = np.nan # 支撑不再存在
            
        # 3. 记录状态
        # 只有在 Bull 趋势时才画 Support (Major Low)
        # 只有在 Bear 趋势时才画 Resistance (Major High)
        if trend == 1:
            major_lows[i] = active_low
            # 如果价格离谱地高，active_high 可能是 nan
        elif trend == -1:
            major_highs[i] = active_high
            
        trends[i] = trend
        
    df['major_high'] = major_highs
    df['major_low'] = major_lows
    df['market_trend'] = trends
    
    return df

```

### 总结

你的 `000510_SH_structure.html` 看起来不对，是因为：

1. **点位漂移**：所有的 Swing Points 都向右偏移了 5 天。
2. **反应迟钝**：结构线的更新逻辑滞后，导致价格明明已经突破了，结构线还要等好几天才变。

请先应用 **V3** 逻辑，特别是加上 `plot_swing_high` 列，然后重新生成图表。你会发现图表变得"跟手"多了。

youtube_url: [https://www.youtube.com/watch?v=Fj0D3k9NTSQ](https://www.google.com/search?q=https://www.youtube.com/watch%3Fv%3DFj0D3k9NTSQ)
This video on "Market Structure & Inducement" is relevant as it visually explains the difference between minor internal structure (which creates traps/inducements) and major swing structure, directly addressing the logic flaw identified in your code.