# TL-Fractal Analysis System

## 📊 项目简介
本项目是一个基于**缠论 (Chan Theory)** 和 **威廉分型 (Bill Williams Fractal)** 理论的金融时间序列分析工具。专注于 K 线的标准化处理、分型识别、笔段自动生成以及高交互性的可视化图表展示。

## 🚀 核心功能

1.  **多源数据适配**
    - 支持加载 Wind 导出的 Excel 数据格式 (`.xlsx`)。
    - 自动识别并适配国债期货 (TF/TL)、10年期国债 (TB10Y) 等品种数据。
    - 支持 CSV 格式输入。

2.  **K 线包含关系处理 (Merge)**
    - 严格遵循缠论定义的包含关系处理逻辑。
    - 自动识别趋势方向（上涨/下跌）并进行 K 线合并，消除市场噪音。
    - 支持递归合并和向左回溯检查。

3.  **分型与笔识别 (Fractals & Strokes)**
    - **顶底分型**：基于合并 K 线识别顶分型 (Top/T) 和底分型 (Bottom/B)。
    - **笔生成**：根据分型间的包含关系和力度，自动连接生成"笔" (Strokes)。
    - **有效性过滤**：内置过滤逻辑，确保分型间满足最小 K 线间隔要求 (MIN_DIST=4)。
    - **笔有效性验证**：验证每笔的终点是否为区间内真正的极值点，无效笔会回溯处理。
    - **被替换分型标记**：显示 Tx/Bx 标记（灰色），帮助理解笔的筛选过程。

4.  **阻力/支撑分析 (Support & Resistance)**
    - 基于"重要高低点" (Major Swing High/Low) 逻辑。
    - 识别潜在的市场关键位。

5.  **📈 交互式可视化 (Interactive Charts)**
    - **Lightweight Charts 引擎**：使用 TradingView 开源图表库生成高性能 HTML 交互图表。
    - **功能完备**：
        - 鼠标滚轮缩放（以鼠标位置为中心）。
        - 左上角固定 OHLC 数据面板（日期、开高低收、涨跌幅）。
        - 顶底分型标注 (T/B) 及被替换分型 (Tx/Bx) 可视化。
        - 笔连线和技术指标叠加 (EMA20)。
        - 自动 Y 轴缩放、Crosshair 十字线。

## 🛠️ 安装与运行

本项目使用 `uv` 进行依赖管理。

### 1. 环境准备
确保已安装 `uv` (现代化的 Python 包管理器)。

```bash
# 初始化环境并安装依赖
uv sync
```

### 2. 运行分析
将原始数据文件放入 `data/raw/` 目录，然后运行主程序：

```bash
# 交互式选择数据文件
uv run run_pipeline.py

# 直接指定文件
uv run run_pipeline.py data/raw/TL.CFE.xlsx

# 非交互模式（自动使用默认文件 TB10Y.WI.xlsx）
echo "" | uv run run_pipeline.py
```

### 3. 选择输入
程序启动后会扫描 `data/raw` 目录下的 `.xlsx` / `.csv` 文件，请根据提示输入序号选择要分析的数据文件。非交互模式下自动使用默认文件。

## 📂 项目结构

```
tl-fractal/
├── data/
│   ├── raw/                 # 存放原始 Excel/CSV 数据文件
│   └── processed/           # 存放处理过程中的 CSV（按 ticker 分类）
│       ├── tl/              # TL.CFE 相关数据
│       └── tb10y/           # TB10Y.WI 相关数据
├── output/                  # 生成的图表结果（按 ticker 分类）
│   ├── tl/
│   └── tb10y/
├── src/
│   ├── analysis/            # 核心分析逻辑
│   │   ├── fractals.py      # 分型与笔识别算法 (MIN_DIST=4)
│   │   ├── merging.py       # K线包含关系合并
│   │   ├── interactive.py   # Lightweight Charts 交互式绘图模块
│   │   ├── indicators.py    # 技术指标计算 (EMA, SMA, Bollinger)
│   │   ├── kline_logic.py   # K线状态分类
│   │   └── process_ohlc.py  # 原始数据处理
│   └── io/                  # 数据输入输出适配器
│       ├── loader.py        # 统一数据加载入口
│       ├── schema.py        # 数据模式定义
│       └── adapters/        # 数据适配器
│           ├── wind_cfe_adapter.py  # Wind CFE 格式适配器
│           └── base.py      # 适配器基类
├── docs/                    # 文档
│   └── workflow.md          # 工作流程图
├── tests/                   # 测试脚本
│   ├── test_min_dist.py     # MIN_DIST 参数对比测试
│   └── plot_min_dist_compare.py  # 可视化对比脚本
├── run_pipeline.py          # 主程序入口
├── pyproject.toml           # 项目依赖配置
└── README.md                # 项目文档
```

## 📝 参数配置

### MIN_DIST (最小间隔)
在 `src/analysis/fractals.py` 中定义：

```python
MIN_DIST = 4  # 顶底分型中间K线索引差至少为4（即中间隔3根，总共7根K线，不共用）
```

**MIN_DIST=4 的效果**：
- 减少短期噪音过滤更多笔
- TL.CFE: 有效笔从 65 降至 53（减少 18.5%）
- TB10Y.WI: 有效笔从 164 降至 73（减少 55%，含笔有效性验证）

## 📝 交互式图表操作指南

- **缩放 (Zoom)**: 使用鼠标滚轮缩放，**以鼠标位置为中心**。
- **平移 (Pan)**: 按住鼠标左键拖动图表。
- **OHLC 信息**: 鼠标悬停时，左上角显示日期、开高低收、涨跌幅和指标值。
- **分型标记**:
  - **T** (红色) / **B** (绿色): 有效顶底分型
  - **Tx** (灰色) / **Bx** (灰色): 被替换的分型

## 📋 最近更新 (2024-12-30)

- **笔有效性验证**: 验证每笔终点是否为区间内真正极值，无效笔回溯处理。
- **交互式图表增强**:
  - 左上角固定 OHLC 信息面板（日期、OHLC、涨跌幅、指标值）
  - 以鼠标位置为中心的滚轮缩放
  - Tx/Bx 被替换分型标记（灰色箭头）
- **默认运行模式**: 非交互模式下自动使用 TB10Y.WI.xlsx 作为默认数据文件。
- **技术指标模块**: 新增 `indicators.py`，支持 EMA、SMA、Bollinger Bands 计算。
