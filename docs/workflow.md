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
        PROCESS["process_ohlc.py<br/>add_kline_status()"]
        MERGE["merging.py<br/>apply_kline_merging()"]
        FRACTAL["fractals.py<br/>process_strokes()<br/>MIN_DIST=4"]
        BAR_FEAT["bar_features.py<br/>compute_bar_features()"]
        KLINE["kline_logic.py<br/>classify_k_line_combination()"]
        INTERACTIVE["interactive.py<br/>交互式可视化"]
        
        LOADER --> PROCESS
        KLINE -.-> PROCESS
        PROCESS --> MERGE
        MERGE --> FRACTAL
        LOADER --> BAR_FEAT
        FRACTAL --> INTERACTIVE
        BAR_FEAT --> INTERACTIVE
    end
    
    subgraph "📂 data/processed/"
        CSV1[("*_processed.csv")]
        CSV2[("*_merged.csv")]
        CSV3[("*_strokes.csv")]
        
        PROCESS --> CSV1
        MERGE --> CSV2
        FRACTAL --> CSV3
    end
    
    subgraph "📂 output/"
        PNG1[("*_merged_kline.png")]
        PNG2[("*_strokes.png")]
        HTML1[("*_interactive.html")]
        HTML2[("*_bar_features.html")]
        
        MERGE --> PNG1
        FRACTAL --> PNG2
        INTERACTIVE --> HTML1
        INTERACTIVE --> HTML2
    end
    
    subgraph "🧪 tests/"
        TEST["test_min_dist.py<br/>MIN_DIST参数测试"]
        PLOT["plot_min_dist_compare.py<br/>MIN_DIST对比可视化"]
        TEST_BAR["test_bar_features.py"]
        
        FRACTAL --> TEST
        FRACTAL --> PLOT
        BAR_FEAT --> TEST_BAR
    end
    
    PIPELINE --> LOADER
    
    style WIND fill:#bbdefb
    style RAW_API fill:#e1f5fe
    style RAW_USER fill:#e1f5fe
    style FETCH fill:#fff3e0
    style PIPELINE fill:#fff3e0
    style CSV1 fill:#e8f5e9
    style CSV2 fill:#e8f5e9
    style CSV3 fill:#e8f5e9
    style PNG1 fill:#fce4ec
    style PNG2 fill:#fce4ec
    style HTML1 fill:#f3e5f5
    style HTML2 fill:#f3e5f5
    style TEST fill:#fff9c4
    style PLOT fill:#fff9c4
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
        alt is standard/api file
            IO->>IO: StandardAdapter.load()
            IO->>IO: data_config.get_config() [Name Lookup]
            IO->>IO: security_names.json [Cache Lookup]
            IO->>IO: WindAPIAdapter.get_security_name() [Optional Fallback]
        else is legacy file
            IO->>IO: WindCFEAdapter.load()
        end
        IO-->>Pipeline: OHLCData 对象 (Symbol & Name)
        
        Note over Pipeline: Step 2: K线状态分类
        Pipeline->>Analysis: process_and_save()
        Analysis-->>Output: (Saved to data/processed/code_name/)
        
        Note over Pipeline: Step 3: K线合并
        Pipeline->>Analysis: apply_kline_merging()
        Analysis-->>Output: (Saved to output/code_name/)
        
        Note over Pipeline: Step 4: 分型与笔识别
        Pipeline->>Analysis: process_strokes()
        Analysis->>Analysis: 记录候选分型 (Candidate History)
        Analysis->>Analysis: 过滤无效笔 + 验证极值
        
        Note over Pipeline: Step 5: 可视化
        Pipeline->>Analysis: ChartBuilder.build()
        Analysis->>Analysis: 计算 H/L 计数 (Signal Filter)
        Analysis-->>Output: *_interactive.html
        
        Note over Pipeline: Step 6: Bar Features
        Pipeline->>Analysis: plot_bar_features_chart()
        Analysis->>Analysis: compute_bar_features()
        Analysis-->>Output: *_bar_features.html
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
        KLINE[kline_logic.py]
        PROCESS[process_ohlc.py]
        MERGE[merging.py]
        FRACTAL[fractals.py]
        INTERACTIVE[interactive.py]
        INDICATORS[indicators.py]
        BAR_FEAT[bar_features.py]
        
        PROCESS --> KLINE
        PROCESS --> SCHEMA
        INTERACTIVE --> INDICATORS
        INTERACTIVE --> BAR_FEAT
        INTERACTIVE --> SCHEMA
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
| **加载(旧)**| xlsx/csv | `WindCFEAdapter` | `OHLCData` | 兼容旧版 Wind 导出格式 |
| **状态标记** | `OHLCData` | `process_ohlc` | `*_processed.csv` | 保存至 `processed/code_name/` 目录下 |
| **合并** | processed.csv | `merging` | `*_merged.csv` | 绘制图表保存至 `output/code_name/` 目录下 |
| **分型** | merged.csv | `fractals` | `*_strokes.csv` | 识别顶底分型，应用 MIN_DIST=4 过滤 |
| **Bar特征** | `OHLCData` | `bar_features` | `*_bar_features.html` | 生成 PA 特征图表 (含 Urgency, Buying/Selling Pressure) |

## 已知限制

| 品种 | 问题 | 解决方案 |
|------|------|----------|
| `TB10Y.WI` | Wind API 不返回 `open` 字段 | 请从 Wind 终端手动下载数据 |

