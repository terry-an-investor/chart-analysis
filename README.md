# TL-Fractal Analysis System

## 📊 项目简介
本项目是一个基于**缠论 (Chan Theory)** 和 **威廉分型 (Bill Williams Fractal)** 理论的金融时间序列分析工具。专注于 K 线的标准化处理、分型识别、笔段自动生成以及高交互性的可视化图表展示。

## 🚀 核心功能

1.  **多源数据适配**
    - 支持加载 Wind 导出的 Excel 数据格式 (`.xlsx`)。
    - **[NEW] Wind API 自动获取**: 通过 `fetch_data.py` 直接调用 Wind Python API (WindPy) 获取最新数据。
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

5.  **Market Structure 市场结构 (Phase 2)**
    - **Swing Detection**: 基于 N-bar 确认法则识别 Swing High/Low (HH, HL, LH, LL)。
    - **Major Levels**: 自动计算并维护结构性支撑/阻力位 (Major High/Low 阶梯线)。
    - **可视化恢复滞后**: 图表上将标记回溯到实际极值时间点，消除视觉滞后。

6.  **📊 Bar Features K 线特征 (New)**
    - **多维特征提取**: 提取单根 K 线特征，辅助 Price Action (Al Brooks) 分析:
        - **相对指标 (Relative)**: 
            - `bar_dir`: 方向 (Bull/Bear/Doji)。
            - `body_pct`: 实体占比 (>0.5 为 Trend Bar，否则为 Trading Range Bar)。
            - `close_pos`: 收盘位置 (**Urgency**, >0.8 为强力买入信号)。
            - `rel_size`: 相对振幅 (当前振幅 / 平均振幅)。
            - `upper_tail_pct/lower_tail_pct`: 上下影线占比。
        - **绝对指标 (Absolute)**: 
            - `total_range`: 高低价差 (波动幅度)。
            - `body_size`: 实体大小 |C-O|。
            - `upper_tail`: **卖压 (Selling Pressure)**。
            - `lower_tail`: **买压 (Buying Pressure)**。
    - **独立可视化**: 生成 `_bar_features.html`，不仅显示 OHLC 蜡烛图，还以副图形式展示特征曲线。

## 🛠️ 安装与运行

本项目使用 `uv` 进行依赖管理。

### 1. 环境准备
确保已安装 `uv` (现代化的 Python 包管理器)。

```bash
# 初始化环境并安装依赖
uv sync
```

### 2. 获取数据 (可选)
如果已安装 Wind 终端且有 Python API 权限，可自动获取配置的数据：

```bash
# 获取所有配置数据的最新行情 (默认近5年)
uv run fetch_data.py

# 获取指定品种 (支持不在配置列表中的任意代码，通过 Wind API 自动识别名称)
uv run fetch_data.py TL.CFE 600519.SH
```

### 3. 运行分析
将原始数据文件放入 `data/raw/` 目录 (或使用 `fetch_data.py` 自动获取)，然后运行主程序：

```bash
# 交互式选择数据文件 (支持多选，输入 "1 2 3")
uv run run_pipeline.py

# 直接指定文件
uv run run_pipeline.py data/raw/TL.CFE.xlsx

# 非交互模式（自动使用默认文件 TB10Y.WI.xlsx）
echo "" | uv run run_pipeline.py
```

### 4. 选择输入与输出
- **智能识别**: 程序启动后会扫描 `data/raw` 目录下的文件。支持识别标准 Wind 命名格式（如 `600519_SH.xlsx`），即使该代码不在配置列表中，也会自动归类并尝试解析中文名。
- **批量处理**: 支持输入多个序号（用空格或逗号分隔）进行顺序处理。
- **描述性目录**: 运行结果将保存在以 `代码_名称` 命名的子目录中，例如 `output/600519_sh_贵州茅台/`，极大地方便了多品种管理。
- **元数据缓存**: 首次解析的资产名称会缓存至 `data/security_names.json`，后续运行将优先读取缓存，避免重复调用 Wind API。

## 📂 项目结构

```
tl-fractal/
├── data/
│   ├── raw/                 # 存放原始 Excel/CSV 数据文件
│   ├── security_names.json  # [NEW] 资产名称本地缓存 (避免重复调用 API)
│   └── processed/           # 存放处理过程中的 CSV（按 ticker_name 分类）
│       ├── tl_30年期国债期货/
│       └── 600519_sh_贵州茅台/
├── output/                  # 生成的图表结果（按 ticker_name 分类）
│   ├── tl_30年期国债期货/
│   │   输出文件:
│   │     - output/{ticker}/*_structure.html  (市场结构交互式图表)
│   │     - output/{ticker}/*_interactive.html  (交互式 OHLC 图表) [可选]
│   │     - output/{ticker}/*_bar_features.html (K线特征图表) [可选]
│   └── 600519_sh_贵州茅台/
├── src/
│   ├── analysis/            # 核心分析逻辑
│   │   ├── bar_features.py  # [NEW] K 线特征提取 (Al Brooks PA)
│   │   ├── fractals.py      # 分型与笔识别算法 (MIN_DIST=4)
│   │   ├── merging.py       # K线包含关系合并
│   │   ├── interactive.py   # Lightweight Charts 交互式绘图模块
│   │   ├── structure.py     # [NEW] 市场结构分析 (Phase 2)
│   │   ├── indicators.py    # 技术指标计算 (EMA, SMA, Bollinger)
│   │   ├── kline_logic.py   # K线状态分类
│   │   └── process_ohlc.py  # 原始数据处理
│   │   └── templates/       # [NEW] HTML 图表模板
│   │       ├── chart_template.html
│   │       └── bar_features_template.html
│   ├── io/                  # 数据输入输出适配器
│       ├── loader.py        # 统一数据加载入口
│       ├── schema.py        # 数据模式定义
│       ├── data_config.py   # [NEW] 数据源配置
│       └── adapters/        # 数据适配器
│           ├── wind_api_adapter.py  # [NEW] Wind API 在线获取适配器
│           ├── wind_cfe_adapter.py  # Wind CFE 格式适配器
│           ├── standard_adapter.py  # [NEW] 标准格式加载适配器
│           └── base.py      # 适配器基类
├── docs/                    # 文档
│   ├── wind-python-api-manual.md # Wind API 参考手册
│   └── workflow.md          # 工作流程图
├── tests/                   # 测试脚本
│   ├── test_bar_features.py # [NEW] 特征提取单元测试
│   ├── test_min_dist.py     # MIN_DIST 参数对比测试
│   └── plot_min_dist_compare.py  # 可视化对比脚本
├── fetch_data.py            # [NEW] 数据获取脚本
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
- **Al Brooks 风格信号**:
  - **Tc** (紫色圆圈): 顶分型候选 (Top Candidate)
    - 触发: 中间 K 线 High 最高，由右肩确认
  - **Bc** (粉红圆圈): 底分型候选 (Bottom Candidate)
    - 触发: 中间 K 线 Low 最低，由右肩确认

## 📋 最近更新 (2025-12-31)

- **[NEW] Bar Features 模块**:
  - 新增 `src.analysis.bar_features`，基于 Al Brooks PA 理论提取单根 K 线特征。
  - **特征增强**: 加入 `total_range`, `body_size`, `upper_tail` (卖压), `lower_tail` (买压) 等绝对物理量。
  - 新增 `plot_bar_features_chart`，生成 OHLC 蜡烛图 + 副图特征曲线的交互式图表。
  - 流水线集成：`run_pipeline.py` 默认生成 `_bar_features.html`。
- **可视化升级**:
  - `interactive.py` 迁移至 **Jinja2** 模板引擎，渲染更稳定。
  - 修复 HTML 模板中 JavaScript 占位符替换的潜在问题。
- **分型系统调整**: 
  - 恢复原始分型定义（纯 High/Low 比较），移除收盘价突破实体的限制。
  - 移除 Hn/Ln 计数逻辑，直接显示 **Tc/Bc** 分型标记。
- **数据质量优化**: 自动过滤 high/low 为 NaN 的无效数据行（如节假日占位符）。
- **动态代码获取**: `fetch_data.py` 支持获取**任意**代码 (股票/基金/指数等)。
- **目录结构优化**: 输出目录由纯代码变为 `代码_名称` 格式。
- **技术指标模块**: 新增 `indicators.py`，支持 EMA、SMA、Bollinger Bands。
- **Phase 2 Market Structure**: 新增 `structure.py`，实现市场结构识别与可视化。
