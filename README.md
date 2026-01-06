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
    - **Swing Detection (V2)**: 
        - 采用 **Breakout Confirmation** 逻辑：只有当价格跌破前低时，才确认上方的高点为 Major Swing High。
        - 相比传统分型，能有效过滤噪音，提供更稳健的结构性阻力/支撑位。
    - **Climax Reversal**: 
        - 识别 **V-Top/V-Bottom** (急转模式)：捕捉 "Bull Climax + Bear Reversal" 的反转形态。
    - **Consecutive Reversal**:
        - 识别 **渐进式反转**：当出现连续 3+ 根同向 K 线后，回溯标记该段行情的起点。
    - **可视化 (Dual-Line Visualization)**: 
        - **实线 (Active Level)**: 代表融合后的**紧缩止损**。
            - 极其敏感，对 Climax/Reversal 事件立即响应。
            - **击穿即失效 (Gap)**: 当价格突破实线时，实线会断开(留白)，直到新结构形成。
        - **虚线 (Major Level)**: 代表原始 V2 **宽止损** (Breakout Confirmed)。
            - 提供宏观市场结构背景，作为长期多空分界线。
            - 即使实线被击穿，只要虚线未破，大趋势可能仍未改变。
        - **诚实滞后**: 线条不进行回溯显示，完全模拟盘中决策体验。

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
src/
├── analysis/
│   ├── bar_features.py      # K线特征提取 (267行)
│   ├── _bar_utils.py        # [NEW] 特征计算辅助函数
│   ├── structure.py         # [REFACTORED] 薄包装层 (175行)
│   ├── swings.py            # [NEW] Swing detection (374行)
│   ├── reversals.py         # [NEW] 反转检测 (289行)
│   ├── _structure_utils.py  # [NEW] 辅助函数和常量 (72行)
│   ├── indicators.py        # 技术指标计算
│   ├── interactive.py       # Lightweight Charts 绘图
│   └── templates/           # HTML 图表模板
├── io/
│   ├── loader.py            # 统一数据加载入口
│   ├── schema.py            # 数据模式定义
│   ├── data_config.py       # 数据源配置
│   ├── config_loader.py     # [NEW] 配置读取模块 (60行)
│   ├── file_discovery.py    # [NEW] 文件发现模块 (158行)
│   └── adapters/
│       ├── wind_api_adapter.py
│       ├── wind_cfe_adapter.py
│       ├── standard_adapter.py
│       └── base.py
├── run_pipeline.py          # [REFACTORED] 简洁入口 (129行)
├── fetch_data.py            # 数据获取脚本
└── ...
```

## 📝 参数配置

### MIN_DIST (最小间隔)
在 `src/analysis/_legacy/fractals.py` 中定义：

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

## 📋 最近更新 (2026-01-06)

### 代码重构 (Clean Code Initiative)
- **模块拆分**: structure.py (1166行) 拆分为 swings.py、reversals.py、structure.py、_structure_utils.py
  - swings.py: Swing detection 逻辑 (374行)
  - reversals.py: Climax 和 Consecutive 反转检测 (289行)
  - structure.py: 薄包装层集成各子模块 (175行)
  - _structure_utils.py: 共用常量和辅助函数 (72行)
- **特征提取优化**: bar_features.py (536行 → 267行)
  - 提取重复逻辑到 _bar_utils.py
  - 移除过度注释，保留关键说明
- **配置隔离**: run_pipeline.py 精简 (318行 → 129行)
  - config_loader.py: 配置读取 (60行)
  - file_discovery.py: 文件扫描 (158行)
- **代码风格**: 统一导入顺序、类型提示、函数签名
- **验证**: 所有测试通过 ✅

### 🚀 项目现代化改进 (2025-01-06)
- **配置管理**: Pydantic v2 + YAML 配置系统，支持环境变量覆盖
- **CI/CD**: GitHub Actions 自动化测试、类型检查、代码格式检查
- **日志系统**: 专业的 logging 模块，支持控制台和文件输出
- **类型提示**: 完整的类型提示，支持 mypy --strict 检查
- **测试覆盖**: 从 31 个测试提升到 **120 个测试**，覆盖率 **54%** (排除 legacy)
- **代码质量**: black + isort 自动格式化
- **详细文档**: 参见 [MODERNIZATION.md](MODERNIZATION.md)
