---
description: Review bar_features.py and its tests for Al Brooks Price Action logic
---

# Bar Features Code Review Workflow

This workflow helps review the core price action feature engineering module.

## 1. Review Feature Definitions

Check the docstring hierarchy in `src/analysis/bar_features.py`:
```bash
head -60 src/analysis/bar_features.py
```

Verify that the docstring correctly describes:
- L1: Scale features (total_range, body_size, amplitude, rel_range_to_avg)
- L2: Shape features (body_pct, clv, signed_body)
- L3: Classifications (is_trend_bar, is_doji, is_pinbar, is_strong_reversal)
- L4: Cross-day features (gap, body_gap, overlap_pct, trend_streak)

## 2. Verify Constants

Ensure thresholds align with Al Brooks definitions:
```bash
grep -n "THRESHOLD\|TOLERANCE" src/analysis/bar_features.py
```

Expected values:
- `DOJI_BODY_THRESHOLD = 0.25` (25% body = Doji)
- `TREND_BAR_THRESHOLD = 0.6` (60% body = Trend Bar)
- `PINBAR_TAIL_THRESHOLD = 0.66` (66% tail = Pin Bar)
- `CLOSE_ON_EXTREME_THRESHOLD = 0.9` (90% CLV = Extreme)

## 3. Check Edge Case Handling

// turbo
Run tests with strict warning mode to catch divide-by-zero or NaN issues:
```bash
uv run python -m pytest -W error tests/test_bar_features.py
```

## 4. Validate Test Coverage

// turbo
Check that all major features have corresponding test cases:
```bash
uv run python -m pytest --collect-only tests/test_bar_features.py | grep "test_"
```

Expected test cases:
- `test_standard_bull_bar` / `test_standard_bear_bar`
- `test_doji_bar`
- `test_preclose_features`
- `test_rel_range_and_climax`
- `test_strong_reversals`
- `test_body_gap`
- `test_trend_streak`

## 5. Review Robustness

Check for safe division and log handling:
```bash
grep -n "np.where\|safe_" src/analysis/bar_features.py
```

Ensure:
- `safe_range` handles `high == low` case
- `safe_prev_close` handles zero prev_close
- Log returns check for positive inputs before `np.log()`

## 6. Run Full Test Suite

// turbo
```bash
uv run python -m pytest tests/test_bar_features.py -v
```

All tests should pass with no warnings.
