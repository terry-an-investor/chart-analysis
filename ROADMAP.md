# Al Brooks Price Action System - Development Roadmap

This document outlines the strategic progression from basic feature extraction to a fully actionable trading analysis system.

## Phase 1: Micro-Analysis (Bar Features) [Current]
**Goal**: Quantify the immediate properties of specific bars. "The Atoms of Price Action"
*   **Module**: `src/analysis/bar_features.py`
*   **Status**: 100% Complete (Legacy logic unified).

### 1.1 Single-Bar Features (The Physics)
*   **Scope**: N=1 (Internal properties).
*   **Status**: [Done]
*   **Deliverables**:
    *   [x] **L1 Scale**: Body Size, Range, Climax Detection.
    *   [x] **L2 Shape**: Doji, Pinbar, Bar Color.
    *   [x] **L3 Signal**: Strong Reversal Bars (Brooks Definition).

### 1.2 Dual-Bar Features (The Interaction)
*   **Scope**: N=2 (Relationship with immediate predecessor).
*   **Status**: [Done]
*   **Deliverables**:
    *   [x] **Gaps**: Body Gap, True Gap.
    *   [x] **Patterns**: Engulfing, Outside Bars, Inside Bars.
    *   [x] **Blended**: Virtual single bar analysis of 2 bars.
    *   [x] **Traps**: Failed Breakouts.

### 1.3 Multi-Bar Features (The Context)
*   **Scope**: N > 2 (Rolling window / Indicator relations).
*   **Status**: [In Progress]
*   **Deliverables**:
    *   [x] **P0: EMA Gravity**: Distance to EMA, Gap Bars, Magnetic Pull.
    *   [x] **Trend Streak**: Consecutive trend bars.
    *   [x] **P1: Volatility**: ATR-based normalization (Implemented in prompt guidelines).

## Phase 2: The Map (Market Structure) [Current]
**Goal**: Identify the "Terrain" where the battle is fighting. "Where are we?"
*   **Module**: `src/analysis/structure.py` (New)
*   **Key Concepts**:
    1.  **Swing Points**: Robust Fractal Highs/Lows identification (The anchor points).
    2.  **Market Cycle Classification**:
        *   **Trend**: Broad Channel vs. Tight Channel (Spike).
        *   **Trading Range**: Balanced areas, Barbwire.
    3.  **"Always In" State**: A discrete state machine determining the probabilistic direction (Long/Short/Neutral).

## Phase 3: The Setup (Pattern Recognition)
**Goal**: Identify specific tactical opportunities within the structure. "Is there an entry?"
*   **Module**: `src/analysis/patterns.py` (New)
*   **Key Concepts**:
    1.  **Pullback Counting**: The Holy Grail of Brooks trend trading.
        *   H1/H2 (Bull Trend Pullbacks).
        *   L1/L2 (Bear Trend Pullbacks).
    2.  **Geometry**:
        *   Wedges (3-push patterns).
        *   Trendline Breaks & Retests.
    3.  **Spike & Channel**: Identifying the transition from impulse to oscillation.

## Phase 4: The Strategy (Decision Engine)
**Goal**: Synthesize Context + Signal for execution. "Should I take this trade?"
*   **Module**: `src/strategy/signal_engine.py` (New)
*   **Key Concepts**:
    1.  **Context Scoring**: Weighting `Trend_Strength` + `Support_Location` + `Setup_Quality`.
    2.  **Trap Filters**: "Good Signal Bar at Bad Location" detection (e.g., buying a Bull Reversal at the top of a Trading Range).
    3.  **Trade Management**:
        *   Stop Loss placement (Swing point vs. Signal bar extreme).
        *   Profit Targets (Scalp vs. Swing).

---

## Technical Dependency Graph

```mermaid
graph TD
    A[Phase 1: Bar Features (L1-L4)] --> B[Phase 1: EMA Features];
    B --> C[Phase 2: Swing Points];
    C --> D[Phase 2: Market Cycle / Always In];
    D --> E[Phase 3: H1/H2 Counting];
    D --> F[Phase 3: Wedge/Channel Lines];
    E --> G[Phase 4: Signal Generation];
    F --> G;
```
