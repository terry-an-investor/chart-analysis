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

4.  **阻力/支撑分析 (Support & Resistance)**
    - 基于"重要高低点" (Major Swing High/Low) 逻辑。
    - 识别潜在的市场关键位。

5.  **📈 交互式可视化 (Interactive Charts)**
    - **Plotly 引擎**：生成高性能 HTML 交互图表。
    - **功能完备**：
        - 支持鼠标滚轮缩放、右侧价格轴手动拖拽。
        - 底部包含迷你缩略图滑块 (RangeSlider)，支持快速区间定位。
        - 悬停显示详细 OHLC 数据。
        - 顶底分型价格标注 (T/B Annotations)。

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
uv run run_pipeline.py
```

### 3. 选择输入
程序启动后会扫描 `data/raw` 目录下的 `.xlsx` / `.csv` 文件，请根据提示输入序号选择要分析的数据文件。

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
│   │   ├── interactive.py   # Plotly 交互式绘图模块
│   │   ├── kline_logic.py   # K线状态分类
│   │   └── process_ohlc.py  # 原始数据处理
│   └── io/                  # 数据输入输出适配器
│       ├── loader.py        # 统一数据加载入口
│       ├── schema.py        # 数据模式定义
│       └── adapters/        # 数据适配器
│           ├── wind_cfe_adapter.py  # Wind CFE 格式适配器
│           └── base.py      # 适配器基类
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
- TB10Y.WI: 有效笔从 164 降至 114（减少 30.5%）

## 📝 交互式图表操作指南

- **缩放 (Zoom)**: 使用鼠标滚轮在图表区域滚动，或拖动底部的 RangeSlider 滑块边缘。
- **平移 (Pan)**: 按住鼠标左键拖动图表。
- **纵向伸缩**: 在右侧价格轴上按住鼠标左键上下拖动，可手动调整 K 线高度比例。
- **重置视图**: 在图表空白处**双击鼠标左键**，自动恢复最佳视野。

## 📋 最近更新

- **MIN_DIST 参数优化**: 将最小间隔从 3 调整为 4，过滤短期噪音，使笔的划分更加稳定。
- **多品种支持**: 扩展支持 TB10Y.WI（10年期国债）等国债期货品种。
- **数据分类存储**: 处理后的数据和输出图表按 ticker 分类存储到独立子目录。
- **测试脚本**: 新增 `tests/test_min_dist.py` 和 `tests/plot_min_dist_compare.py` 用于参数对比测试。
