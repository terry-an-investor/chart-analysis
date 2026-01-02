# Al Brooks Price Action 完整术语表 (中英对照 & 代码映射)

本文档基于 `docs/brooks-pa-terms.md` 原文，对所有术语进行了**全量翻译**与**分类整理**。同时，针对已在 `src/analysis/bar_features.py` 中实现量化特征的概念，特别标注了对应的**代码变量**与逻辑说明，方便将主观的 PA 理论与客观的代码实现对照学习。

---

## 1. K线形态与单柱特征 (Candle Patterns & Features)
*关注单根或相邻几根 K 线的具体形状与相互关系，是识别市场情绪的最小单元。*

| 英文术语 (English) | 中文术语 | 定义与解释 (Definition) | 代码映射 (Code Mapping) |
| :--- | :--- | :--- | :--- |
| **Candle** | K线 / 蜡烛图 | 价格行为的图表表示，包含实体（开盘与收盘之间）和影线（高低点）。白/阳线(Close>Open)，黑/阴线(Close<Open)。 | `bar_color`, `body_pct`, `upper/lower_tail_pct` |
| **Trend Bar** | 趋势K线 | 具有明显实体的K线，表明存在明确的价格运动。收盘价远离于开盘价。 | `is_trend_bar` (body_pct $\ge$ 0.6) |
| **Doji** | 十字星 | 实体非常小或没有实体的K线。表明多空力量均衡，既无多头也无空头控制。 | `is_doji` (body_pct < 0.25) |
| **Shaved Body** | 光头/光脚 | 没有影线（或影线极短）的K线。光头无上影，光脚无下影，代表极强动能。 | `shaved_top/bottom` (tail_pct $\le$ 2%) |
| **Reversal Bar** | 反转K线 | 与当前趋势方向相反的趋势K线，通常带有反向的长影线。 | `is_strong_bull/bear_reversal` |
| **Inside Bar (ii)** | 内包线 | 高点低于前高，低点高于前低。代表波动率收缩。连续两根称为 **ii**，连续三根称为 **iii**。 | `is_inside` |
| **Outside Bar (oo)** | 外包线 | 高点高于前高，低点低于前低。代表波动率扩张或困境。连续两根称为 **oo**。 | `is_outside` |
| **Outside Down/Up Bar** | 外包阴/阳线 | 收盘低于开盘(Down)或高于开盘(Up)的外包线。 | `is_outside_down/up` |
| **ioi / oio** | ioi / oio | 内包-外包-内包 (Inside-Outside-Inside) 或 外包-内包-外包 的组合形态，通常作为突破模式。 | *(需多K线识别)* |
| **Breakout Bar** | 突破K线 | 创造突破的K线，通常是一根强趋势K线。 | *(逻辑概念)* |
| **Surprise Bar** | 意外/惊喜K线 | 异常巨大的趋势K线，通常会引发至少一两个小波段的跟随。 | `is_climax_bar` |
| **Dominant Feature** | 主导特征 | 也是一种巨大的 Surprise Bar，其影响可能持续一整天。 | `is_climax_bar` |
| **Disappointment Bar** | 失望K线 | 在上涨趋势中出现的阴线，或下跌趋势中出现的阳线，导致部分交易者获利了结。 | *(逻辑概念)* |
| **Pause Bar** | 停顿K线 | 未能延伸趋势的K线（如内包线，或未创新高的小阳线），视为一种极其微小的回撤。 | *(类似 small body_pct)* |
| **Signal Bar** | 信号K线 | 设置入场单之前的最后一根K线。如果入场单被触发，它就成为信号K线。 | *(逻辑概念)* |
| **Entry Bar** | 入场K线 | 交易被触发/执行的那根K线。 | *(逻辑概念)* |
| **Follow-through Bar** | 后续K线 | 紧随入场K线或突破K线之后的一根或几根K线，以确认趋势是否延续。 | *(逻辑概念)* |
| **Barbwire** | 铁丝网 | 三根或更多根重叠较大且包含一个或多个十字星的K线组。一种需避免交易的窄幅震荡形态。 | *(需组合识别)* |
| **Gap Reversal** | 缺口反转 | 开盘跳空后，第二根K线立即回补缺口（例如向上跳空后，立即跌破第一根K线低点）。 | *(需组合识别)* |
| **Micro Double Bottom/Top** | 微型双底/顶 | 连续或接近连续的K线由于具有相同的低点(双底)或高点(双顶)。 | *(需组合识别)* |

---

## 2. 市场结构与价格行为 (Market Structure & Price Action)
*描述价格运动的宏观结构、支撑阻力及特殊的价格真空现象。*

| 英文术语 (English) | 中文术语 | 定义与解释 (Definition) | 代码映射 (Code Mapping) |
| :--- | :--- | :--- | :--- |
| **Trend** | 趋势 | 价格主要向上（牛市）或向下（熊市）的一系列变动。 | `trend_streak` |
| **Trading Range** | 交易区间 | 横向波动的市场，多空力量暂时平衡，常表现为前一根K线被大量重叠。 | `is_trading_range_bar`, `overlap_pct` |
| **Tight Trading Range** | 窄幅交易区间 | 两根或更多根重叠严重且波幅很小的K线，通常难以通过止损单盈利。 | `is_trading_range_bar` |
| **Tight Channel** | 窄幅通道 | 趋势线和通道线靠得很近，回撤很小且短暂（1-3根K线）的通道。 | *(需波段识别)* |
| **Broad Channel** | 宽幅通道 | *(暗含概念)* 包含较大回撤的趋势通道。 | *(需波段识别)* |
| **Micro Channel** | 微型通道 | 极窄的通道，大部分K线的高低点都触及趋势线，几乎没有回撤。 | *(需波段识别)* |
| **Breakout** | 突破 | 价格超出先前的关键价位（如波段高点、趋势线）。 | `failed_breakout_high/low` (反向即为突破) |
| **Breakout Mode** | 突破模式 | 无论向上还是向下突破都可能产生跟随行情的形态（如收敛三角形）。 | `is_inside` |
| **Gap** | 跳空/缺口 | 相邻两根K线之间的价格真空。通常指今日开盘价在昨日区间之外。 | `gap`, `gap_type` |
| **Body Gap** | 实体缺口 | 即使影线重叠，但两根K线的实体部分不重叠。这是趋势强度的体现。 | `body_gap` |
| **Measuring Gap** | 测量缺口 | 导致测量行情（Measured Move）的突破缺口或强趋势K线。 | *N/A* |
| **Micro Measuring Gap** | 微型测量缺口 | 强趋势K线前后的K线互不重叠，预示着微型测量行情。 | *N/A* |
| **Exhaustion Gap** | 衰竭缺口 | 趋势末端出现的巨大趋势K线或跳空，通常引发获利了结和反转。 | `is_climax_bar` |
| **Spike and Channel** | 尖峰与通道 | 强力突破（Spike）后动能减弱，转为通道式（Channel）上涨或下跌。 | *N/A* |
| **Stair / Shrinking Stairs** | 阶梯 / 阶梯收缩 | 连续的突破幅度越来越小（阶梯收缩），显示动能衰竭。 | *N/A* |
| **Vacuum** | 真空效应 | 价格被快速“吸”向某个磁力点（Magnet），表现为顺势加速。 | *N/A* |
| **Magnet** | 磁力点 | *(隐含概念)* 吸引价格的目标位，如支撑阻力、均线、极值点。 | *N/A* |
| **Climax** | 高潮/极值 | 走势过快过远，随之而来通常是反转或区间震荡。 | `is_climax_bar` |
| **Meltdown / Melt-up** | 崩盘 / 暴涨 | 极强的单边趋势，几乎没有回撤。 | *N/A* |
| **Swing** | 波段 | 突破趋势线的小型趋势，至少由两个波段组成。 | *N/A* |
| **Swing High/Low** | 波段高/低点 | 看起来像尖峰一样凸出或凹陷的K线（高点高于前后，低点低于前后）。 | *N/A* |
| **Higher/Lower High/Low** | 更高/低的高/低点 | 也是 Swing High/Low 的相对关系，用于定义趋势。 | *N/A* |
| **Trending Highs/Lows/Closes** | 趋势性高/低/收盘 | 连续三根或更多根K线的高点、低点或收盘价呈趋势排列。 | *(需 trend_streak 逻辑)* |
| **Trending Swings** | 趋势性波段 | 连续的波段高低点不断抬高（牛市）或降低（熊市）。 | *N/A* |
| **Leg** | 腿/段 | 任何较小的趋势，是较大趋势的一部分。 | *N/A* |
| **Test** | 测试 | 价格接近之前的关键价位，可能过冲 (Overshoot) 或未达 (Undershoot)。 | *N/A* |
| **Overshoot / Undershoot** | 过冲 / 未达 | 价格穿越目标位 (Overshoot) 或接近但在到达前反转 (Undershoot)。 | *N/A* |
| **Trend From The Open** | 开盘即趋势 | 趋势从当天的第一根或前几根K线开始，且全天大部分时间维持在该方向。 | *N/A* |
| **Small Pullback Trend** | 小回撤趋势 | 极强的趋势，回撤非常小且短暂。 | *N/A* |
| **Buy/Sell The Close Trend** | 买/卖收盘趋势 | 趋势极强，以至于交易者敢于在收盘价直接追涨杀跌。 | *N/A* |
| **Ledge** | 平台 | 极小的交易区间，由两根或更多根底部（牛市平台）或顶部（熊市平台）平齐的K线组成。 | *N/A* |

---

## 3. 交易架构与信号 (Setups & Signals)
*具体的入场模式，用于捕捉反转或顺势机会。*

| 英文术语 (English) | 中文术语 | 定义与解释 (Definition) | 代码映射 (Code Mapping) |
| :--- | :--- | :--- | :--- |
| **Setup** | 架构 | 由上下文（Context）和信号K线组成的一个或多个K线的组合形态。 | *(逻辑概念)* |
| **Pullback** | 回撤 | 趋势中的暂时停顿或反向运动。 | *N/A* |
| **Bar Pullback** | 单K回撤 | 极其微小的回撤，表现为单根K线的逆向极值。 | *N/A* |
| **Breakout Pullback** | 突破回撤 | 突破后的小幅回撤，是对突破有效性的确认（Failed Failure）。 | *N/A* |
| **Breakout Test** | 突破回踩 | 回撤至原来的突破点附近进行测试。 | *N/A* |
| **Bull/Bear Flag** | 看涨/看跌旗形 | 趋势中的中继形态，预期趋势将延续。可以是任何暂停形态。 | *N/A* |
| **Double Bottom/Top** | 双底 / 双顶 | 经典的测试形态。常出现在旗形中（双底看涨旗形）。 | *N/A* |
| **Double Bottom/Top Pullback** | 双底/顶回撤 | 双底/顶形成后的深幅回撤，是一个更加可靠的入场架构。 | *N/A* |
| **Wedge** | 楔形 | 三推浪结构，趋势线收敛。既可以是反转形态，也可以是中继形态（楔形旗形）。 | *N/A* |
| **Three Pushes** | 三推浪 | 类似于楔形，三个连续的高点或低点。 | *N/A* |
| **Opening Reversal** | 开盘反转 | 开盘后第一小时内出现的反转。 | *(时间相关)* |
| **Trap** | 陷阱 | 诱导交易者入场后立即反转的形态。 | `failed_breakout_high/low` |
| **Failed Breakout** | 突破失败 | 价格突破某关键位后收盘未能站稳。 | `failed_breakout_high/low` |
| **Failure (Failed Move)** | 失败 | 止损被触发而未能达到目标的交易。 | *N/A* |
| **Failed Failure** | 失败的失败 | 一个失败的形态（如突破失败）自身也失败了，意味着原方向恢复，通常是极佳的入场点（即 Breakout Pullback）。 | *N/A* |
| **Five-tick Failure** | 五跳失败 | (Emini特指) 突破信号K线后走了5个tick即反转，导致剥头皮交易者止损退出。 | *N/A* |
| **H1/H2 (High 1, 2)** | 高1/高2 | 牛市回撤中，第一次突破前根K线高点为H1，第二次为H2。H2通常胜率更高。 | *N/A* |
| **L1/L2 (Low 1, 2)** | 低1/低2 | 熊市反弹中，第一次跌破前根K线低点为L1，第二次为L2。 | *N/A* |
| **High/Low 3, 4** | 高/低 3, 4 | 如果出现H3/L3，通常意味着楔形或者更复杂的调整。 | *N/A* |
| **Second Entry / Signal** | 二次入场/信号 | 第一次信号失败后的第二次同向信号，通常概率更高(如L2, H2)。 | *N/A* |
| **Major Trend Reversal** | 主要趋势反转 | 趋势彻底改变，通常包含突破趋势线、测试极值等步骤。 | *N/A* |
| **Minor Trend Reversal** | 次要趋势反转 | 趋势中的小反转，通常演变为回撤或交易区间。 | *N/A* |

---

## 4. 订单流与参与者 (Order Flow & Participants)
*描述市场背后的力量与参与者行为。*

| 英文术语 (English) | 中文术语 | 定义与解释 (Definition) | 代码映射 (Code Mapping) |
| :--- | :--- | :--- | :--- |
| **Institution** | 机构 | 能够通过大资金量影响市场的“聪明钱” (Smart Money)。 | *N/A* |
| **Smart Traders** | 聪明交易者 | 持续盈利，通常交易大仓位且站在正确一方的交易者。 | *N/A* |
| **Strong Bulls/Bears** | 强势多头/空头 | 决定市场方向的机构交易者及其累积的买卖力量。 | *N/A* |
| **Buying Pressure** | 买压 | 强势多头掌控局面的迹象（如阳线、下影线、连续阳线）。 | `is_strong_bull_reversal`, `close_on_extreme` |
| **Selling Pressure** | 卖压 | 强势空头掌控局面的迹象（如阴线、上影线、连续阴线）。 | `is_strong_bear_reversal`, `close_on_extreme` |
| **HFT** | 高频交易 | 利用算法进行的高速交易，基于统计而非基本面。 | *N/A* |
| **News** | 新闻 | 对交易者通常无用甚至有害的信息，应该忽略，只关注价格行为。 | *N/A* |

---

## 5. 指标与时间周期 (Indicators & Time Frames)
*辅助分析工具。*

| 英文术语 (English) | 中文术语 | 定义与解释 (Definition) | 代码映射 (Code Mapping) |
| :--- | :--- | :--- | :--- |
| **EMA** | 指数移动平均 | 通常指 20 周期 EMA。 | `ema` |
| **Moving Average Gap Bar** | 均线缺口K线 | 完全不触碰均线的K线，强趋势标志。 | `gap_below/above_ema`, `dist_to_ema` |
| **20 Moving Average Gap Bars** | 20根均线缺口 | 连续20根以上K线未触碰均线，通常会导致极值测试。 | *(需 trend_streak 衍生)* |
| **Second MA Gap Bar Setup** | 二次均线缺口架构 | 第一次回测均线失败后，第二次回测均线形成的入场架构。 | *N/A* |
| **Trend Line** | 趋势线 | 连接波段高点或低点的直线。 | *N/A* |
| **Major Trend Line** | 主要趋势线 | 控制整个屏幕价格走势的长期趋势线。 | *N/A* |
| **Trend Channel Line** | 趋势通道线 | 平行于趋势线，画在K线的另一侧。 | *N/A* |
| **Micro Trend Line** | 微型趋势线 | 连接2-10根K线的短期趋势线。 | *N/A* |
| **Time Frame** | 时间周期 | 图表一根K线代表的时间（如5分钟）。 | *N/A* |
| **HTF (Higher Time Frame)** | 更高时间周期 | 相比当前图表更高级别的周期（如5分钟图的HTF是60分钟）。 | *N/A* |
| **STF (Smaller Time Frame)** | 更小时间周期 | 相比当前图表更低级别的周期。 | *N/A* |
| **Tick** | Tick / 跳动点 | 全球市场最小的价格变动单位。Emini是0.25点。 | *N/A* |
| **Pip** | 点 (外汇) | 外汇市场的最小变动单位。 | *N/A* |
| **Chart Type** | 图表类型 | K线图、线图、成交量图等。 | *N/A* |

---

## 6. 交易管理与概率 (Trade Management & Probability)
*资金管理、数学期望与交易心理。*

| 英文术语 (English) | 中文术语 | 定义与解释 (Definition) |
| :--- | :--- | :--- |
| **Always In** | 总是/一直在场 | 假设必须时刻持有头寸，当前应该持有的方向（Always In Long/Short）。 |
| **Trader's Equation** | 交易者方程 | 概率 × 潜在回报 > (1 - 概率) × 风险。正期望值的数学表达。 |
| **Probability** | 概率 | 交易成功的机会。 |
| **Likely / Probably / Usually** | 可能/通常 | 至少 60% 的确定性。 |
| **Unlikely** | 不太可能 | 最多 40% 的确定性。 |
| **Risk** | 风险 | 入场价到止损价的距离（Tick数）。 |
| **Reward** | 回报 | 入场价到止盈目标的距离（Tick数）。 |
| **Risk / Reward** | 风险/回报比 | 潜在盈利与亏损的比例。 |
| **Risk On / Off** | 风险偏好/厌恶 | 市场情绪倾向于追逐高风险资产(On)还是避险资产(Off)。 |
| **Risky** | 风险高 | 交易者方程不清晰，或胜率 $\le$ 50%。 |
| **Scalp** | 剥头皮/短线 | 目标利润较小，旨在快速获利的交易。 |
| **Scalper** | 短线交易者 | 主要进行剥头皮交易的人。 |
| **Scalper's Profit** | 短线利润 | 短线交易的典型目标利润（如Emini的4个点）。 |
| **Swing Trade** | 波段交易 | 持有时间较长，目标捕捉较大波段的交易。 |
| **Day Trade** | 日内交易 | 当天平仓不过夜的交易。 |
| **Position** | 头寸 | 持有的多单或空单。 |
| **Long** | 多头 | 买入持有者。 |
| **Short** | 空头 | 卖出持有者。 |
| **Flat** | 空仓 | 未持有任何头寸。 |
| **Stop (Money Stop)** | 止损 (金额止损) | 基于固定金额或点数的止损。 |
| **Trailing a Stop** | 移动止损 | 随着盈利增加，移动止损以保护利润。 |
| **Countertrend** | 逆势 | 与当前趋势方向相反的交易，通常胜率较低。 |
| **Countertrend Scalp** | 逆势剥头皮 | 认为趋势延续但有回调需求，试图抓取小回调的交易（通常是错误的）。 |
| **Fade** | 逆向操作 | 在趋势中反向交易（如卖出牛市突破），期望其失败。 |
| **With Trend** | 顺势 | 与当前主趋势方向一致的交易。 |
| **Perfect Trade** | 完美交易 | 高胜率且高盈亏比的交易。这种交易**不存在**（如果存在，没人会做对手盘）。 |
| **Tradable** | 可交易的 | 胜率和盈亏比合理，值得进场的架构。 |
| **Scratch** | 平手/微亏 | 在盈亏平衡点附近平仓的交易。 |
| **Blown Account** | 爆仓 | 亏损导致账户资金低于最低保证金要求。 |
| **Lot** | 手/张 | 最小交易单位。 |
| **Price Action** | 价格行为 | 任何图表上的任何价格变动。 |
| **Context** | 上下文/背景 | 左侧的所有K线结构。孤立的K线没有意义，必须结合 Context。 |
| **False** | 假的 | 即 Failed / Failure。 |

---

*注：代码映射中的变量名均出自 `src/analysis/bar_features.py`。部分术语（如 Market Structure 和 Setups）需要结合多根K线的逻辑（H1/H2, Double Bottom）才能在策略层实现，因此在单 K 线特征提取模块中显示为 `N/A` 或提示需后续组合。*
