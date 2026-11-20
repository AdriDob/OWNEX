# OWNEX V13 — Backtesting Framework

## Overview

Historical testing framework for weather-based trading strategies. **Paper trading only**. No real execution. No look-ahead bias. Out-of-sample validation mandatory.

## Backtesting Philosophy

> **Never use future data to adjust past forecasts (no look-ahead bias).**
> **New strategies must demonstrate out-of-sample improvement before substitution.**
> **Walk-forward validation required** before any strategy activation.

## Validation Pipeline — Mandatory

```
1. Data Split → train/validation/out-of-sample
2. Model Training → on training data only
3. Hyperparameter Tuning → on validation data only
4. Out-of-Sample Testing → on never-before-seen data
5. Only if OOS improvement → substitute model/strategy
```

### Split Ratios (Configurable, Recommended)

| Split | Fraction | Purpose |
|-------|----------|---------|
| **Train** | 70% | Model parameter estimation |
| **Validation** | 15% | Hyperparameter tuning, model selection |
| **Out-of-Sample** | 15% | Final evaluation, never-before-seen |

**❌ No data leakage** — strict separation of splits.

### Walk-Forward Validation

More rigorous than simple train/test split:

```
┌─────────────────────────────────────────────────────┐
│  INITIAL PERIOD:                               │
│  - Train on [T0, T1]                             │
│  - Validate on [T1, T2]                          │
│  - Test on [T2, T3]                              │
│  - Record performance                           │
│  ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄ │
│  SLIDE FORWARD:                                │
│  - Train on [T1, T2] (drop T0, add T3)           │
│  - Validate on [T2, T3]                          │
│  - Test on [T3, T4]                              │
│  - Record performance                           │
│  ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄ │
│  CONTINUE SLIDING →                              │
│  until end of dataset                            │
└─────────────────────────────────────────────────────┘
```

**Key properties**:
- Each test period uses fresh data (no overlap with training)
- Model re-trained at each step
- Performance aggregated across all walk-forward periods
- More conservative than single train/test

## Backtesting Data Structure

Every backtest record must include:

| Field | Type | Description |
|-------|------|-------------|
| `strategy_id` | string | Strategy identifier |
| `strategy_version` | string | Strategy version |
| `model_version` | string | Weather model version |
| `forecast_timestamp` | datetime | When forecast was made |
| `city` | string | Forecast city |
| `variable` | string | Temperature, precipitation, etc. |
| `horizon` | string | 6h, 24h, 72h, 7d, etc. |
| `model_probability` | float | Model's estimated probability |
| `market_implied` | float | Market price implied probability |
| `raw_edge` | float | model - market_implied |
| `adjusted_edge` | float | raw_edge - costs |
| `expected_value` | float | EV calculation |
| `position_size` | float | Fraction of capital risked |
| `costs` | float | Commissions + slippage |
| `pnl_simulated` | float | Simulated profit/loss |
| `resolution_timestamp` | datetime | When event resolved |
| `observation_final` | float | Actual observed value |
| `result` | enum | win, loss, break_even |
| `brier_score` | float | (prob - outcome)² |
| `calibration_error` | float | Deviation from perfect calibration |
| `confidence` | float | Based on calibration quality |
| `risk_score` | float | System risk assessment |
| `liquidity_usd` | float | Market liquidity at trade time |
| `spread` | float | bid-ask spread |
| `slippage` | float | Estimated slippage |
| `walk_forward_period` | integer | Which walk-forward cycle |
| `validation_status` | enum | passed, failed, incomplete |

## Metrics Calculated

| Metric | Formula | Target/Interpretation |
|--------|---------|----------------------|
| **Total Trades** | count of backtested trades | > 30 for statistical significance |
| **Win Rate** | trades with pnl_simulated > 0 / total | > 55% desirable |
| **Loss Rate** | trades with pnl_simulated < 0 / total | < 45% acceptable |
| **Break-Even Rate** | trades with pnl_simulated ≈ 0 / total | ~0% desired |
| **Total PnL** | sum of all pnl_simulated | Positive desirable |
| **Average Trade** | total_pnl / total_trades | Positive desirable |
| **Maximum Drawdown** | peak-to-trough decline in equity | Minimize |
| **Sharpe Ratio** | (avg_trade - risk_free) / std_trade | > 1 desirable |
| **Sortino Ratio** | similar Sharpe but downside only | > 1.5 desirable |
| **Brier Score (overall)** | mean of all brier_scores | Lower is better (max 0.25) |
| **Calibration Error** | | Near 0 desired (perfect calibration) |
| **Edge Capture Rate** | % of trades with adjusted_edge > 0 | Higher desirable |
| **Cost Capture** | total_costs / |total_pnl| | Lower desirable |
| **Slippage Impact** | total_slippage / |total_pnl| | Lower desirable |

### Statistical Significance

**Requirements for valid backtesting**:

1. ✅ Minimum 30 trades (rule of thumb for normality)
2. ✅ Positive expected value (EV > 0)
3. ✅ Statistical test passed (t-test or non-parametric equivalent)
4. ✅ Out-of-sample validation passed
5. ✅ No look-ahead bias confirmed
6. ✅ Calibration within acceptable error

**❌ Fewer than 30 trades → insufficient statistical significance, report as "inconclusive".**

## Walk-Forward Validation Results

Report these per walk-forward period:

| Period | Start | End | Trades | Win Rate | Total PnL | Sharpe | Notes |
|--------|-------|-----|--------|----------|-----------|--------|-------|
| Period 1 | T0 | T1 | n | w% | $ | S | |
| Period 2 | T1 | T2 | n | w% | $ | S | |
| ... | ... | ... | ... | ... | ... | ... | |
| Period N | T_{N-1} | T_N | n | w% | $ | S | |

**Aggregate metrics** across all periods:
- Total trades: sum
- Aggregate win rate: weighted average
- Aggregate total PnL: sum
- Average Sharpe: mean
- Statistical significance test

## Backtesting — What's PROHIBITED

| Prohibition | Reason |
|-------------|--------|
| ❌ Look-ahead bias — using future data for past forecasts | Invalidates entire results |
| ❌ Training and testing on same data | Overfitting, inflated results |
| ❌ Reporting only favorable periods | Cherry-picking, scientific fraud |
| ❌ Using same data for model selection and evaluation | Optimistic bias |
| ❌ Reporting only winning strategies | Survival bias |
| ❌ Simulated PnL as real OWNEX income | Revenue rule violation |
| ❌ No transaction costs included | Unrealistic, misleading |
| ❌ No slippage included | Unrealistic, misleading |
| ❌ Changing strategy after seeing results | Post-hoc optimization |
| ❌ Infinite backtesting until positive result | Data dredging, p-hacking |

## Backtesting — What's MANDATORY

| Requirement | Implementation |
|-----------|----------------|
| Train/validation/oos split | Strict 70/15/15 or walk-forward |
| Transaction costs included | All commissions + fees |
| Slippage included | Estimated per market condition |
| Look-ahead bias check | Documented and verified |
| Statistical significance | ≥30 trades or appropriate test |
| Calibration reported | Brier score + calibration curve |
| Edge capture rate | % of trades with positive adjusted_edge |
| Cost breakdown | Commissions, slippage, spread separately |
| Walk-forward if possible | More rigorous than simple split |

## Strategy Comparison in Backtesting

When comparing multiple strategies:

1. **Same data splits** — all strategies tested on identical train/validation/oos splits
2. **Same cost assumptions** — same commissions, slippage rates
3. **Same position sizing** — unless strategy specifies otherwise
4. **Same significance thresholds** — all must meet ≥30 trades
5. **Report all results** — even strategies that underperform
6. **No automatic selection** — human review required

**Comparison report includes**:

| Strategy | Total Trades | Win Rate | Total PnL | Sharpe | Brier Score | Decision |
|----------|-------------|----------|-----------|--------|-------------|----------|
| gfs_ensemble | 42 | 58% | $245 | 1.23 | 0.18 | ✅ Proceed to paper trading |
| ecmwf_bucket | 38 | 52% | $112 | 0.87 | 0.22 | ✅ Proceed to paper trading |
| multi_model_ensemble | 45 | 61% | $310 | 1.45 | 0.15 | ✅ Proceed to paper trading |
| historical_calibration | 35 | 50% | $45 | 0.65 | 0.25 | ⚠️ Recalibrate before PT |

**❌ Never select solely based on total PnL** — consider risk, Sharpe, brier score, edge capture.

## Backtesting Workflow

```
1. Define strategy and parameters
2. Retrieve historical weather data (engine)
3. Retrieve historical market data (Polymarket/Kalshi)
4. Split data: train/validation/oos (70/15/15 or walk-forward)
5. Train model on train data (estimate σ, bias, calibration)
6. Tune hyperparameters on validation data
7. Test on out-of-sample data
8. Calculate all metrics (pnl, win rate, brier, sharpe, etc.)
9. Walk-forward: repeat steps 5-8 across sliding periods
10. Aggregate results across all periods
11. Compare against baseline (no-edge strategy, fixed position)
12. Report: all metrics, limitations, statistical tests
13. If OOS improvement → enable in paper trading
14. If not → revise or retire strategy
```

## Baseline Strategy — Comparison Reference

**Always compare new strategies against this baseline:**

| Metric | Baseline Value | Description |
|--------|---------------|-------------|
| `strategy_id` | "baseline_fixed" | Fixed-position baseline |
| `position_size` | 0.01 × capital | 1% of capital per trade |
| `entry_condition` | `adjusted_edge > 0` | Only trade when edge positive |
| `exit_condition` | always | Hold until resolution |
| `total_trades` | Variable | Depends on market opportunities |
| `win_rate` | ~50% | Random-like, edge near 0 |
| `total_pnl` | ≈ 0 | Near zero expected (costs eat edge) |
| `sharpe` | ≈ 0 | No risk-adjusted return |
| `brier_score` | ~0.25 | Random probability (binary) |

**New strategy must improve upon baseline on multiple metrics**, not just total PnL.

## Backtesting Report Template

```
BACKTEST REPORT — Strategy: {strategy_id} v{strategy_version}

1. EXECUTIVE SUMMARY
   - Total trades: {n}
   - Win rate: {w%} (baseline: ~50%)
   - Total PnL: ${total_pnl:.2f} (baseline: ~$0)
   - Sharpe ratio: {sharpe:.2f} (baseline: ~0)
   - Brier score: {brier:.4f} (baseline: ~0.25)
   - Edge capture rate: {edge_capture:.1%}

2. DETAILED METRICS
   - Win/loss/break-even counts
   - Average trade: ${avg:.2f}
   - Maximum drawdown: ${dd:.2f}
   - Total costs: ${costs:.2f} (commissions: ${com:.2f}, slippage: ${slip:.2f})
   - Edge capture rate: {ec:.1%} (trades with adjusted_edge > 0)
   - Calibration error: {ce:.4f}

3. WALK-FORWARD AGGREGATE
   - Periods evaluated: {n_periods}
   - Aggregate win rate: {awr:.1%}
   - Aggregate total PnL: ${atot:.2f}
   - Average Sharpe: {asharpe:.2f}

4. OUT-OF-SAMPLE VALIDATION
   - OOS improvement over baseline: {yes/no}
   - OOS win rate: {oos_wr:.1%}
   - OOS total PnL: ${oos_pnl:.2f}

5. CALIBRATION
   - Overall Brier score: {brier:.4f}
   - Calibration curve: {description}
   - Calibration within tolerance: {yes/no}

6. LIMITATIONS
   - Data period: {start} to {end}
   - Markets covered: {list}
   - Known issues: {list}

7. STATISTICAL SIGNIFICANCE
   - t-test p-value: {p_value:.4f}
   - Significant (p < 0.05): {yes/no}
   - Minimum trade count met: {yes/no} (≥30)

8. RECOMMENDATION
   - Enable in paper trading: {yes/no}
   - Retry after: {suggestions}
   - Retire: {yes/no}
```

## Integration with Paper Trading

Backtesting → Paper Trading Pipeline:

```
Backtest Results → Passed criteria → Enable in paper trading system → 
Signal generation → Paper trading simulation → Results recording → 
Historical learning loop → Calibration update → New validation cycle
```

**❌ Backtesting results never count as real income.**
**❌ Paper trading uses simulated capital only.**
**❌ Any strategy activation requires human gate approval.**

## Deliverables Already Generated

- outputs/OWNEX_V13_WEATHER_DATA_SOURCES.md (created)
- outputs/OWNEX_V13_WEATHER_MODELS.md (created)
- outputs/OWNEX_V13_POLYMARKET_MARKET_ANALYSIS.md (created)
- outputs/OWNEX_V13_WEATHER_STRATEGIES.md (created)
- outputs/OWNEX_V13_WEATHER_RISK.md (created)
- outputs/OWNEX_V13_WEATHER_BACKTEST.md — created above
- outputs/OWNEX_V13_WEATHER_SECURITY.md — next
- outputs/OWNEX_V13_WEATHER_TESTS.md — next
- outputs/OWNEX_V13_WEATHER_BLOCKERS.md — next