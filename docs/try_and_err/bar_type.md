这非常关键。如果基础的 Building Blocks（积木块）定义不准，上层的逻辑（H1/H2、Spike、Channel）就会全部坍塌。

Al Brooks 看 K 线不仅仅是看“涨/跌”，他看的是**“压力 (Pressure)”**和**“紧迫感 (Urgency)”**。

为了量化这些抽象概念，除了你提到的 `Body_Size`, `Total_Range`, `Bar_Type`，我们需要扩充到以下 **4 个维度的基础积木**：

### 1. 内部力度 (Internal Strength) —— 它是谁？

这一层决定了这根 K 线是“趋势 K 线”还是“震荡 K 线”，以及多空谁在控制局面。

* **Direction (方向):**
* 简单：Close > Open (Bull), Close < Open (Bear).
* *量化值：* +1, -1, 0.


* **Body_Percentage (实体占比):**
* Al Brooks 经常说：“全是实体，没有影线，说明趋势极强。”
* *公式：* `Body_Size / Total_Range`
* *用途：* 如果 > 60%，定义为 Trend Bar；如果 < 30%，定义为 Doji (十字星/震荡线)。


* **Close_Position (收盘位置 - 核心指标):**
* 这是判断 **Signal Bar (信号棒)** 质量的关键。好的多头信号棒必须收在最高点附近。
* *公式：* `(Close - Low) / (High - Low)`
* *量化值：* 0.0 到 1.0。
* > 0.8: 收在顶部 (Strong Bull Close)。


* < 0.2: 收在底部 (Strong Bear Close)。
* 0.4 - 0.6: 收在中间 (Neutral/Indecision)。





### 2. 相对体量 (Relative Magnitude) —— 它有多大？

一根 10 个点的 K 线，在平静期是大阳线，在新闻发布时可能只是个小波动。必须做归一化处理。

* **Relative_Size (相对大小):**
* *公式：* `Total_Range / Average(Total_Range, Last 20 Bars)`
* *用途：*
* > 2.0: **Spike / Climax** (巨大，可能是突破起点，也可能是高潮耗尽)。


* < 0.5: **Quiet / Barbwire** (极小，甚至不要去交易它)。





### 3. 邻里关系 (Neighbor Interaction) —— 它和昨天怎么相处？

这是识别 **Trading Range (震荡区间)** 的杀手锏。Al Brooks 反复强调“重叠 (Overlap)”。

* **Overlap_Percentage (重叠度):**
* 这根 K 线有多少部分是在前一根 K 线的价格范围内的？
* *公式：* 计算当前 Low 到 High 与前一根 Low 到 High 的交集比例。
* *用途：* 连续 3 根 K 线的重叠度如果都很高（例如 > 70%），这就是 **Tight Trading Range (窄幅震荡)**，此时禁止做突破，只能做 Fade (反向)。


* **Gap (缺口):**
* Al Brooks 很看重 "Gap between Close and High"。
* *检测：* 当前 Close 是否高于前一根 High？(Body Gap)。这代表极强的趋势延续。



### 4. 特殊形态标记 (Special Classifiers)

这些是布尔值（True/False），用来触发特定逻辑。

* **Inside_Bar (孕线):** High < Prev_High 且 Low > Prev_Low。
* **Outside_Bar (吞没线):** High > Prev_High 且 Low < Prev_Low。
* **Reversal_Bar (反转K线):**
* 需要结合 `Body_Percentage` 和 `Tail_Size`。
* 例如：看涨反转 = 下影线长 (Bottom Tail > 1/3 Range) + 收盘在高位 + 实体较小。



---

### 汇总：你的“积木清单” (Data Dictionary)

为了写程序，我们需要把这些变成一个标准的**数据字典**。每一根 K 线经过处理后，应该包含以下数据：

| 积木名称 (Variable) | 类型 | 说明 | 对应 Al Brooks 概念 |
| --- | --- | --- | --- |
| `bar_dir` | int | 1 (Bull), -1 (Bear), 0 (Doji) | Bull/Bear Bar |
| `body_pct` | float | 0.0 - 1.0 | Trend Bar vs Doji |
| `close_pos` | float | 0.0 - 1.0 | Urgency / Strength |
| `rel_size` | float | 比如 1.5 (1.5倍平均振幅) | Spike / Climax |
| `overlap_pct` | float | 0.0 - 1.0 | Trading Range Mode |
| `is_inside` | bool | True/False | ii pattern |
| `is_outside` | bool | True/False | oo pattern |
| `gap_open` | bool | 是否跳空开盘 | Gap |

### 建议的下一步

既然确定了积木，我们能不能写一段 Python 代码（或者你常用的语言），**输入**一组 OHLC 数据，**输出**包含上面所有特征的 DataFrame？

这是所有量化策略的“地基”。如果这部分数据清洗做好了，后面写策略就是简单的拼图游戏了。需要我展示这个“特征提取”的代码模块吗？