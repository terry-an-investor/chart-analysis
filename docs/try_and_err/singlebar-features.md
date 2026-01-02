这就对了，量化就是要把简单的东西拆解到极致。目前的列表只覆盖了“大概轮廓”，如果要达到 Al Brooks 对 K 线“显微镜级”的观察，我们还可以继续“压榨”出更多维度的**单 K 线特征**。

Al Brooks 经常说：**"Every tick matters"**（每一个跳动都重要）。虽然我们在处理 OHLC，无法看到 tick，但我们可以通过特定的比率推测出 K 线内部的博弈。

以下是深挖后的 **进阶单 K 线特征 (Advanced Single-Bar Features)**，我们将它们分为三个新的维度：**极端性、阻力结构、形态分类**。

### 1. 极端性特征 (Extremity & Urgency) —— 寻找“光头光脚”

Al Brooks 非常看重 **Shaved Bars (光头/光脚 K 线)**。如果一根 K 线收盘价等于最高价（或极度接近），这意味着多头一直买到了最后一秒，没有任何获利回吐，这是极强的**紧迫感 (Urgency)**。

| 特征名称 | 逻辑/公式 | Al Brooks 含义 | 代码实现建议 |
| --- | --- | --- | --- |
| **Shaved_Top** |  | **强力买入** | 布尔值 (Bool)。允许极其微小的误差 (如 0.1 tick)。 |
| **Shaved_Bottom** |  | **强力卖出** | 布尔值。意味着在该 K 线周期内，底部没有买盘反抗。 |
| **Full_Control** | `Shaved_Top` AND `Shaved_Bottom` | **Marubozu (全秃)** | 这种 K 线出现时，往往标志着趋势的高潮或突破的开始。 |
| **Close_in_Body** |  时看是否接近 ;  时看是否接近  | **收盘坚决度** | 将 `Close_Pos` 细化。如果是阳线，`Close` 是否在实体的前 10%？ |

### 2. 阻力结构特征 (Resistance & Failure) —— 影线的深层含义

影线 (Tails/Wicks) 本质上是**失败的突破**。上影线 = 多头试图推高但失败了；下影线 = 空头试图砸盘但被拉回了。我们需要量化这种“失败”的程度。

| 特征名称 | 逻辑/公式 | Al Brooks 含义 | 备注 |
| --- | --- | --- | --- |
| **Top_Tail_Pct** |  | **上方抛压** | 若 ，说明这根 K 线虽然可能是阳线，但空头反击极其强烈（Shooting Star）。 |
| **Bottom_Tail_Pct** |  | **下方支撑** | 若 ，说明下方有强买盘（Hammer）。 |
| **Tail_Dominance** | `Top_Tail` vs `Bottom_Tail` | **多空分歧** | 比如 `abs(Top - Bottom)`。如果两头影线都很长且相等，这是极度的犹豫（Spinning Top）。 |
| **Body_Mid_Loc** |  在  的位置 | **重心位置** | 即使是十字星，重心偏上还是偏下？偏上利多。 |

### 3. 形态分类特征 (Morphology Classifiers) —— 给 K 线起名

这是为了方便后续策略逻辑调用。与其每次都写公式，不如直接生成分类标签。

| 特征名称 | 逻辑 | Al Brooks 术语 | 用途 |
| --- | --- | --- | --- |
| **is_Doji** | `Body_Size` < `Total_Range` * 0.1 | **Doji (犹豫)** | 只要是 Doji，就不是好的 Signal Bar，通常不能在 Doji 上方挂单买入。 |
| **is_Pinbar** | 实体很小 + 单侧影线极长 (>66%) | **Reversal Bar** | 这是最经典的单 K 反转信号。 |
| **is_Trend_Bar** | `Body_Size` > `Total_Range` * 0.6 | **Trend Bar** | 趋势交易的基础单位。 |
| **Bull_Reversal_Shape** | 下影线长 + 收盘在最高点附近 + 实体小 | **Buy Signal Bar** | 专门用于识别潜在的 L1/L2 买入信号棒。 |
| **Bear_Reversal_Shape** | 上影线长 + 收盘在最低点附近 + 实体小 | **Sell Signal Bar** | 专门用于识别潜在的 H1/H2 卖出信号棒。 |

### 4. 隐藏的微观特征 (Implicit Micro-Structure)

这是通过 OHLC 倒推内部 tick 走势。

* **Open_Sentiment (开盘情绪):**
* 公式：`(Open - Low) / (High - Low)`
* 含义：如果一根阳线开盘在**最低点** (`Open == Low`)，这比开盘在中间更强。说明从开盘第一秒开始就是多头控盘。


* **Color_Change (颜色反转 - 伪代码):**
* 如果你能获取更细的数据（比如 1分钟 K 线合成 5分钟），你可以判断这根 5分钟 K 线是否经历了“由红变绿”的过程。在单 K 线层面，如果 `Close > Open` 但 `Low << Open`，说明它曾经是一根阴线，后来被拉起来了。这是一个隐藏的 Bull Power。



---

### 汇总：完备的单 K 线 Feature Vector (特征向量)

如果把这些“压榨”干尽，对于任意一根 K 线 ，你的程序将拥有以下数据包：

1. **基础物理量:** `Open`, `High`, `Low`, `Close`, `Volume`
2. **尺寸特征:** `Total_Range`, `Body_Size`
3. **方向特征:** `Direction` (+1/-1)
4. **比例特征:** `Body_Pct`, `Top_Tail_Pct`, `Bottom_Tail_Pct`
5. **位置特征:** `Close_Pos` (收盘位置), `Open_Pos` (开盘位置), `Midpoint_Loc`
6. **布尔标记 (Flags):**
* `is_shaved_top` / `is_shaved_bottom`
* `is_doji`
* `is_bull_trend_bar` / `is_bear_trend_bar`
* `has_long_top_tail` / `has_long_bottom_tail`



### 现在的“完备度”评估

目前这个清单在 **“静态单 K 线”** 层面已经达到了 **95% 的完备度**。
剩下的 5% 是什么？是 **Tick Data**（逐笔成交数据）。

* Al Brooks 有时会说：“这根 K 线先向上突破失败，然后向下……”。单纯的 OHLC 无法区分“先上后下”还是“先下后上”。
* **解决方案：** 如果你没有 Tick 数据，目前的特征已经是天花板了。如果有 Tick 数据，可以加一个 `Path_Type` 特征。

**下一步建议：**
你要不要用这些特征，先做一个简单的**“信号棒评分器 (Signal Bar Scorer)”**？
例如：输入一根 K 线，程序输出 `Score: 85/100`（这是一根完美的 Al Brooks 买入信号棒）。这能立刻检验这些特征好不好用。