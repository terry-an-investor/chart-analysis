# K 线分析流水线 - 代码工作流

## 整体架构

```mermaid
graph TB
    subgraph "External"
        WIND[("Wind Terminal<br/>Python API")]
    end

    subgraph "Scripts"
        FETCH["🚀 fetch_data.py"]
        PIPELINE["🚀 run_pipeline.py"]
    end

    subgraph "📂 data/raw/"
        RAW_API[("Wind API Data<br/>(*.xlsx)")]
        RAW_USER[("User Data<br/>(*.xlsx/csv)")]
        CACHE[("security_names.json<br/>(Cache)")]
    end
    
    subgraph "📦 src/io/"
        CONFIG["data_config.py<br/>DataConfig"]
        WIND_ADAPTER["adapters/<br/>WindAPIAdapter"]
        STD_ADAPTER["adapters/<br/>StandardAdapter"]
        CFE_ADAPTER["adapters/<br/>WindCFEAdapter"]
        
        SCHEMA["schema.py<br/>OHLCData"]
        LOADER["loader.py<br/>load_ohlc()"]
        
        WIND --> FETCH
        FETCH --Uses--> WIND_ADAPTER
        CONFIG -.-> FETCH
        CONFIG -.-> STD_ADAPTER
        
        WIND_ADAPTER --Name Lookup--> CACHE
        WIND_ADAPTER --Saves--> RAW_API
        
        RAW_API --> STD_ADAPTER
        CACHE -.-> STD_ADAPTER
        RAW_USER --> CFE_ADAPTER
        
        STD_ADAPTER --> SCHEMA
        CFE_ADAPTER --> SCHEMA
        SCHEMA --> LOADER
    end
    
    subgraph "📊 src/analysis/"
        BAR_FEAT["bar_features.py<br/>compute_bar_features()"]
        BAR_UTILS["_bar_utils.py<br/>Feature Helpers"]
        SWINGS["swings.py<br/>Swing Detection"]
        REVERSALS["reversals.py<br/>Reversal Patterns"]
        STRUCTURE["structure.py<br/>Market Structure Integration"]
        INTERACTIVE["interactive.py<br/>交互式可视化"]
        INDICATORS["indicators.py<br/>技术指标"]
        
        LOADER --> BAR_FEAT
        BAR_FEAT --> BAR_UTILS
        BAR_UTILS --> SWINGS
        SWINGS --> REVERSALS
        REVERSALS --> STRUCTURE
        STRUCTURE --> INTERACTIVE
        INDICATORS --> INTERACTIVE
        BAR_FEAT --> INTERACTIVE
    end
    
    subgraph "📂 output/"
        HTML3[("*_structure.html")]
        HTML2[("*_bar_features.html")]
        
        STRUCTURE --> HTML3
        BAR_FEAT --> HTML2
    end
    
    subgraph "🧪 tests/"
        TEST_STRUC["test_structure.py"]
        TEST_BAR["test_bar_features.py"]
        
        STRUCTURE --> TEST_STRUC
        BAR_FEAT --> TEST_BAR
    end
    
    PIPELINE --> LOADER
    
    style WIND fill:#bbdefb
    style RAW_API fill:#e1f5fe
    style RAW_USER fill:#e1f5fe
    style FETCH fill:#fff3e0
    style PIPELINE fill:#fff3e0
    style HTML2 fill:#f3e5f5
    style HTML3 fill:#f3e5f5
    style TEST_STRUC fill:#fff9c4
    style TEST_BAR fill:#fff9c4
    style BAR_FEAT fill:#e1bee7
    style HTML2 fill:#e1bee7
```

## 数据获取与分析流程

```mermaid
sequenceDiagram
    participant User
    participant Fetch as fetch_data.py
    participant Pipeline as run_pipeline.py
    participant IO as src/io/
    participant Analysis as src/analysis/
    participant Output as output/
    
    %% Phase 1: Data Fetching
    Note over User, Fetch: Phase 1: 获取数据 (可选)
    User->>Fetch: uv run fetch_data.py
    Fetch->>IO: WindAPIAdapter.connect()
    loop For each symbol
        Fetch->>IO: WindAPIAdapter.fetch_data()
        IO->>IO: w.wsd(symbol, fields...)
        Fetch->>IO: WindAPIAdapter.save_to_excel()
    end
    Fetch-->>User: ✅ 数据已保存至 data/raw/
    
    %% Phase 2: Analysis Pipeline
    Note over User, Pipeline: Phase 2: 运行流水线
    User->>Pipeline: uv run run_pipeline.py
    Pipeline->>User: 显示文件列表 (Wind API / User)
    User->>Pipeline: 选择文件 (支持多选 1 2 3)
    
    loop For each selected file
        Note over Pipeline: Step 1: 加载数据
        Pipeline->>IO: load_ohlc(file_path)
        IO-->>Pipeline: OHLCData 对象 (Symbol & Name)
        
        Note over Pipeline: Step 2: 市场结构分析
        Pipeline->>Analysis: detect_swings()
        Pipeline->>Analysis: classify_swings_v2()
        Pipeline->>Analysis: detect_climax_reversal()
        Pipeline->>Analysis: detect_consecutive_reversal()
        Pipeline->>Analysis: merge_structure_with_events()
        
        Note over Pipeline: Step 3: 可视化渲染
        Pipeline->>Analysis: ChartBuilder.build()
        Analysis-->>Output: *_structure.html
    end

    Pipeline-->>User: ✅ 所有文件处理完成
```

## 模块依赖关系

```mermaid
graph LR
    subgraph "src/io/"
        direction TB
        CONFIG[data_config.py]
        SCHEMA[schema.py]
        LOADER[loader.py]
        
        subgraph "Adapters"
            BASE[adapters/base.py]
            WIND_API[adapters/wind_api_adapter.py]
            WIND_CFE[adapters/wind_cfe_adapter.py]
            STD[adapters/standard_adapter.py]
        end
        
        BASE --> SCHEMA
        WIND_API --> BASE
        WIND_CFE --> BASE
        STD --> BASE
        
        WIND_API --> CONFIG
        WIND_API --> SCHEMA
        STD --> CONFIG
        
        LOADER --> STD
        LOADER --> WIND_CFE
    end
    
    subgraph "src/analysis/"
        INDICATORS[indicators.py]
        BAR_FEAT[bar_features.py]
        BAR_UTILS[_bar_utils.py]
        SWINGS[swings.py]
        REVERSALS[reversals.py]
        STRUCTURE[structure.py]
        STRUC_UTILS[_structure_utils.py]
        INTERACTIVE[interactive.py]
        
        BAR_FEAT --> BAR_UTILS
        BAR_FEAT --> INDICATORS
        SWINGS --> STRUC_UTILS
        REVERSALS --> STRUC_UTILS
        STRUCTURE --> SWINGS
        STRUCTURE --> REVERSALS
        INTERACTIVE --> INDICATORS
        INTERACTIVE --> STRUCTURE
    end
    
    subgraph "Scripts"
        FETCH[fetch_data.py]
        RUN[run_pipeline.py]
        
        FETCH --> WIND_API
        RUN --> LOADER
        RUN --> ANALYSIS_MODULES
    end
    
    RUN --> PROCESS
    RUN --> MERGE
    RUN --> FRACTAL
    RUN --> INTERACTIVE
```

## 数据转换流程

| 阶段 | 输入 | 下游/适配器 | 输出 | 说明 |
|------|------|-------------|------|------|
| **获取** | Wind Terminal | `WindAPIAdapter` | `*.xlsx` (Standard) | 自动解析名称并缓存至 `security_names.json` |
| **加载** | xlsx/csv | `StandardAdapter` | `OHLCData` | 优先读取缓存名称，**自动填充缺失的 open 列** |
| **特征提取** | `OHLCData` | `bar_features` | 特征 Series | 提取 PA 特征 (含 Urgency, Buying/Selling Pressure) |
| **Swing 检测** | `OHLCData` | `swings` | Swing Points | 识别 Major Swing High/Low (V2/V3) |
| **反转识别** | Swing Data | `reversals` | Reversal Events | 识别 Climax 和 Consecutive 反转模式 |
| **结构集成** | 多源数据 | `structure` | Market Structure | 集成 Swing、Reversal 和 Trend 状态 |
| **可视化** | Structure Data | `interactive` | `*_structure.html` | 生成交互式市场结构图表 |


## 已知限制

| 品种 | 问题 | 解决方案 |
|------|------|----------|

