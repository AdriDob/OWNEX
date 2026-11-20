# OWNEX V13 — Strategy Engine

## Overview

Modular, comparable strategies for weather-based market edges. **NOT** cloning audited repos — own implementation. Each strategy independent, versioned, and non-self-modifying.

## Strategy Architecture

### Core Principle

> **No strategy may modify itself and enter production automatically.**
> Machine learning may propose changes, but must create a NEW experimental version.

### Strategy Identity

Every strategy has:

| Attribute | Description |
|-----------|-------------|
| `identifier` | Unique name (e.g., "gfs_ensemble", "ecmwf_bucket") |
| `version` | Semantic version (MAJOR.MINOR.PATCH) |
| `parameters` | All settings, fully documented |
| `sources` | Which data sources this uses |
| `hypothesis` | What this strategy bets on |
| `conditions` | When active/inactive |
| `results` | Historical performance (paper trading only) |
| `risks` | Known failure modes |
| `state` | active/paused/retired |
| `change_history` | What changed and why (immutable record) |

## Strategy Modules

### 1. `gfs_ensemble` — GFS Ensemble Strategy

| Field | Value/Description |
|-------|-------------------|
| `identifier` | gfs_ensemble |
| `version` | 1.0.0 (increment as changes) |
| `parameters` | - `μ`: mean from GFS ensemble<br>- `σ`: std dev (validated per city/horizon)<br>- `bucket_count`: 6 (default)<br>- `bias_correction`: true/false<br>- `min_liquidity`: USD threshold<br>- `max_spread`: max acceptable spread |
| `sources` | gfs data engine output |
| `hypothesis` | GFS ensemble mean probability mispriced vs Polymarket/Kalshi |
| `conditions` | - Active: when model_probability outside [-threshold, threshold] of market<br>- Inactive: during extreme market volatility, low liquidity<br>- Required: min_liquidity met, spread within limits |
| `results` | Paper trading only: win rate, EV, Brier score per backtest period |
| `risks` | - GFS systematic bias<br>- Model drift over season<br>- Market regime change<br>- Liquidation risk if edge too small |
| `state` | paused (initialized, awaiting calibration) |
| `change_history` | "Created v1.0.0 — initial implementation based on Repo 1 GFS Weather Bot ensemble analysis. No code copied." |

### 2. `ecmwf_bucket` — ECMWF Gaussian Bucket Strategy

| Field | Value/Description |
|-------|-------------------|
| `identifier` | ecmwf_bucket |
| `version` | 1.0.0 |
| `parameters` | - `μ`: mean from ECMWF ensemble<br>- `σ`: std dev (validated per city/horizon)<br>- `bucket_count`: 6 (default)<br>- `bias_correction`: true/false<br>- `min_liquidity`: USD threshold<br>- `max_spread`: max acceptable spread<br>- `horizon_priority`: preferred time horizon |
| `sources` | ec_met data engine output |
| `hypothesis` | ECMWF bucket probabilities mispriced vs market, especially vs GFS |
| `conditions` | - Active: when ECMWF bucket prob differs from GFS by > delta<br>- Inactive: ECMWF data unavailable, high uncertainty<br>- Required: both ECMWF and GFS data available |
| `results` | Paper trading only: comparative win rate vs GFS, EV per period |
| `risks` | - ECMWF less frequent than GFS<br>- Higher computational cost<br>- Similar systematic biases to GFS<br>- Data latency issues |
| `state` | paused |
| `change_history` | "Created v1.0.0 — based on Repo 2 Hermes WeatherBot Gaussian Bucket Model. No code copied. Adaptation automática requires statistical validation per safety constraint." |

### 3. `multi_model_ensemble` — Multi-Model Ensemble Strategy

| Field | Value/Description |
|-------|-------------------|
| `identifier` | multi_model_ensemble |
| `version` | 1.0.0 |
| `parameters` | - `weights`: dict model→weight (sums to 1.0)<br>- `min_liquidity`: USD threshold<br>- `max_spread`: max acceptable spread<br>- `diversification_penalty`: weight penalty for correlated models<br>- `min_weight`: minimum weight per model |
| `sources` | gfs, ec_met, open_meteo, metar, noaa |
| `hypothesis` | Combined ensemble of multiple models outperforms individual models |
| `conditions` | - Active: when ensemble edge > individual model edges<br>- Inactive: insufficient model diversity, weights unstable<br>- Required: ≥2 models with valid data |
| `results` | Paper trading only: win rate comparison, EV vs single-model strategies |
| `risks` | - Model correlation reduces diversification benefit<br>- Weight optimization overfitting<br>- Increased complexity, more failure modes<br>- Calibration per model required |
| `state` | paused |
| `change_history` | "Created v1.0.0 — combines GFS + ECMWF + Open-Meteo. Weights optimized via walk-forward validation. No code copied from repos." |

### 4. `gaussian_bucket` — Gaussian Bucket Strategy

| Field | Value/Description |
|-------|-------------------|
| `identifier` | gaussian_bucket |
| `version` | 1.0.0 |
| `parameters` | - `μ`: predicted mean<br>- `σ`: estimated std dev (validated per group)<br>- `bucket_count`: 6 (default: -∞, μ-2σ, μ-σ, μ, μ+σ, μ+2σ, ∞)<br>- `bias_correction`: true/false<br>- `calibration_curve`: applied/none<br>- `min_liquidity`: USD threshold<br>- `max_spread`: max acceptable spread |
| `sources` | Any data engine output (GFS, ECMWF, etc.) |
| `hypothesis` | Gaussian distribution of errors provides accurate probability buckets |
| `conditions` | - Active: when σ validated, calibration within acceptable error<br>- Inadequate: insufficient historical data for σ estimation<br>- Required: σ estimated per city/model/horizon/variable/season |
| `results` | Paper trading only: calibration accuracy, Brier score per bucket, win rate |
| `risks` | - σ estimation error with limited data<br>- Non-Gaussian error distributions<br>- Seasonal variation not accounted<br>- Overfitting to specific city/horizon |
| `state` | paused |
| `change_history` | "Created v1.0.0 — core probability engine bucket model. σ must be estimated and validated per city/model/horizon/variable/season. No arbitrary probabilities." |

### 5. `bias_correction` — Bias Correction Strategy

| Field | Value/Description |
|-------|-------------------|
| `identifier` | bias_correction |
| `version` | 1.0.0 |
| `parameters` | - `correction_scheme`: "historical_mean", "seasonal", "ml_model"<br>- `correction_per`: "city", "model", "horizon", "variable", "season"<br>- `min_data_points`: minimum observations for calibration<br>- `max_age_days`: max age of historical data |
| `sources` | Historical forecast vs observation data |
| `hypothesis` | Systematic bias exists and is correctable |
| `conditions` | - Active: when enough historical data (min_data_points)<br>- Inactive: insufficient data, correction unstable<br>- Required: min_data_points observations per group |
| `results` | Paper trading only: before/after bias correction Brier score, EV impact |
| `risks` | - Overfitting calibration to specific history<br>- Correction changes with new data<br>- May introduce new biases<br>- Data dredging risk |
| `state` | paused |
| `change_history` | "Created v1.0.0 — learns systematic forecast biases from historical errors. Validated via out-of-sample testing." |

### 6. `historical_calibration` — Historical Calibration Strategy

| Field | Value/Description |
|-------|-------------------|
| `identifier` | historical_calibration |
| `version` | 1.0.0 |
| `parameters` | - `train_ fraction`: fraction of data for training (e.g., 0.7)<br>- `validation_fraction`: fraction for validation (e.g., 0.15)<br>- `out_of_sample_fraction`: fraction for testing (e.g., 0.15)<br>- `calibration_method`: " Platt scaling", "Isotonic", "Quantile"<br>- `min_observations`: minimum for reliable calibration |
| `sources` | Historical forecast archives + actual observations |
| `hypothesis` | Historical error patterns can calibrate future forecasts |
| `conditions` | - Active: when sufficient data (min_observations per group)<br>- Inactive: data sparse, calibration unreliable<br>- Required: train/validation/oos splits valid |
| `results` | Paper trading only: calibration improvement, Brier score before/after |
| `risks` | - Data leakage if splits not proper<br>- Overfitting calibration function<br>- Calibration may not generalize<br>- Requires significant historical data |
| `state` | paused |
| `change_history` | "Created v1.0.0 — calibrates forecast probabilities using historical error patterns. Train/validation/oos split mandatory." |

## Strategy Lifecycle

```
created → testing → approved → active → retired
   ↑               ↑               ↑
   |               |               |
   └────constant evaluation─────┘
```

### Lifecycle Transitions

| From → To | Trigger | Requirements |
|-----------|---------|--------------|
| created → testing | Strategy definition complete | All fields populated, version set |
| testing → approved | Out-of-sample validation passed | Walk-forward validation, no data leakage |
| approved → active | Approved for paper trading | Strategy enabled in paper trading system |
| active → retired | Poor performance or better alternative | Justified by results analysis |
| retired → approved | New evidence suggests reactivation | Must pass testing again |

### Strategy Creation Process

1. **Define** — fill all strategy identity fields
2. **Test** — walk-forward validation on historical data
   - Train: 70% of data
   - Validation: 15% (tune hyperparameters)
   - Out-of-sample: 15% (never-before-seen)
3. **Approve** — if out-of-sample improvement over baseline
4. **Activate** — enable in paper trading system
5. **Monitor** — continuous performance tracking
6. **Retire** — if consistently underperforming or replaced

### Strategy Comparison

Strategies are **comparable** but not automatically combined:

1. Each strategy runs independently
2. Results compared via same metrics (Brier score, EV, win rate)
3. **No automatic** "best strategy selected"
4. **ML may propose** new version based on patterns
5. **Human review** required for any strategy activation

### Strategy Metrics Tracked

| Metric | Description | Target |
|--------|-------------|--------|
| `win_rate` | % of paper trades profitable | > 55% desirable |
| `expected_value` | EV per trade (adjusted edge × size) | > 0 desired |
| `brier_score` | Probability accuracy | Lower is better (max 0.25) |
| `calibration_error` | Deviation from perfect calibration | Near 0 desired |
| `max_drawdown` | Largest peak-to-trough decline | Minimize |
| `sharpe_ratio` | Risk-adjusted return | > 1 desirable |
| `total_trades` | Number of paper trades | > 30 for statistical significance |
| `cost_per_trade` | Commissions + slippage per trade | Minimize |
| `liquidity_coverage` | Trades within liquidity limits | 100% desired |

### Strategy Activation Requirements

**Before any strategy can be activated:**

1. ✅ Walk-forward validation passed (no data leakage)
2. ✅ Out-of-sample performance better than baseline
3. ✅ Calibration curves validated (Brier score, MAE, RMSE)
4. ✅ Minimum trade count for statistical significance (≥30)
5. ✅ All risk limits within thresholds
6. ✅ Strategy documented in change_history
7. ✅ **Human gate approval** — no automatic activation

### ❌ Prohibited Automatically

- ❌ Strategy modifying its own parameters in production
- ❌ Automatic activation without human gate
- ❌ Switching to a strategy based solely on historical performance
- ❌ Increasing risk after winning streaks
- ❌ Using unvalidated σ estimation

### ✅ Allowed with Validation

- ✅ ML model proposes new experimental version
- ✅ Human reviews and approves new version
- ✅ Strategy retired, new version activated
- ✅ Periodic re-validation (every N trades or N days)
- ✅ Bias correction strategies with out-of-sample validation

## Integration with Paper Trading

Each strategy interacts with the paper trading system:

```
Strategy → Generates signal → Paper trading records → Simulation → Results → Strategy state update
```

### Signal Format

```json
{
  "strategy_id": "gfs_ensemble",
  "strategy_version": "1.0.0",
  "signal_type": "long" or "short" (or "none"),
  "probability": 0.65,  // model probability
  "market_implied": 0.55,  // market price implied
  "raw_edge": 0.10,
  "adjusted_edge": 0.05,  // after costs
  "expected_value": 15.50,  // EV in USD
  "position_size": 0.10,  // 10% of capital or fractional Kelly
  "costs": 0.02,  // commissions + slippage
  "confidence": 0.85,  // based on calibration
  "risk_score": 0.15,  // uncertainty + liquidity
  "city": "Buenos Aires",
  "horizon": "24h",
  "model": "GFS 12z",
  "timestamp": "2026-11-09T14:30:00Z"
}
```

### Paper Trading Response

```
Paper trading simulates:
1. Entry at simulated_entry_price (observed_price + slippage)
2. Position size = position_size × available_capital
3. Costs deducted (commissions + slippage already in adjusted_edge)
4. Wait for resolution (real-time or accelerated simulation)
5. Calculate pnl_simulated based on actual resolution
6. Update strategy state and results
7. Record in historical learning loop
```

## Integration with Historical Learning

Every strategy result feeds the historical learning loop:

```
Paper Trade Result → Comparison Data → Historical Learning → Model Calibration → New Strategy Version
```

### Comparison Data Recording (per trade)

| Field | Description |
|-------|-------------|
| `original_forecast` | Forecast made at signal time |
| `updated_forecast` | If later updated (null if not) |
| `observation_final` | Actual observed value at resolution |
| `market_resolution` | How market resolved |
| `calculated_probability` | Probability assigned at forecast time |
| `result` | win/loss (paper PnL sign) |
| `error` | forecast_error = calculated_prob - observation_final |
| `brier_score` | (calculated_prob - outcome)² |
| `strategy` | strategy identifier + version |
| `model_version` | weather model version |
| `edge` | adjusted_edge at trade time |
| `costs` | commissions + slippage |
| `pnl_simulated` | simulated profit/loss |
| `confidence` | based on calibration quality |

### Learning Loop Outcomes

1. **Calibration update** — adjust σ estimation per group
2. **Bias correction update** — refine historical bias patterns
3. **New strategy version** — if ML detects pattern worth formalizing
4. **Strategy retirement** — if consistent underperformance
5. **Parameter adjustment** — if validation shows drift

**❌ No data leakage** — out-of-sample only.
**❌ No overfitting** — any new version must pass validation.

## Risk Management Integration

Each strategy must respect the overall risk management controls:

| Control | Strategy Compliance |
|---------|---------------------|
| Maximum exposure | Strategy reports position size; system enforces limit |
| Maximum position size | Strategy's position_size must be ≤ system maximum |
| Daily loss limit | System tracks cumulative PnL; stops if exceeded |
| Maximum open positions | System tracks open positions; blocks if limit reached |
| Liquidity requirements | System verifies market liquidity before allowing trade |
| Spread limits | System checks spread; blocks if above threshold |
| Slippage estimates | Included in adjusted_edge calculation |
| Uncertainty limits | Strategy's risk_score must be ≤ system maximum |
| Correlation limits | System monitors position correlation; blocks if exceeded |
| Circuit breaker | System-wide, overrides individual strategy |

**Strategy never bypasses system-wide risk controls.**

## Frontend Integration

### Strategy Panel (within Weather Intelligence section)

Displays:

| Element | Description |
|---------|-------------|
| Active strategies | List of currently active strategies |
| Strategy version | v1.0.0, v1.1.0, etc. |
| Key parameters | μ, σ, min_liquidity, max_spread (simplified) |
| State | active/paused/retired |
| Performance | win rate, EV, total trades (paper trading) |
| Controls | Pause/retire buttons (human gate) |
| Change history | Link to full change log |

### Strategy Creation (frontend)

Human-in-the-loop flow:

1. Define strategy parameters
2. Run walk-forward validation (automated)
3. Review results (human)
4. Approve for activation (human gate)
5. Enable in paper trading system
6. Monitor performance
7. Periodic re-validation

**No automated creation without human review.**

## Deliverables Already Generated

- outputs/OWNEX_V13_WEATHER_DATA_SOURCES.md (created)
- outputs/OWNEX_V13_WEATHER_MODELS.md (created)
- outputs/OWNEX_V13_POLYMARKET_MARKET_ANALYSIS.md (created)
- outputs/OWNEX_V13_WEATHER_STRATEGIES.md — created above
- outputs/OWNEX_V13_WEATHER_RISK.md — next
- outputs/OWNEX_V13_WEATHER_BACKTEST.md — next
- outputs/OWNEX_V13_WEATHER_SECURITY.md — next
- outputs/OWNEX_V13_WEATHER_TESTS.md — next
- outputs/OWNEX_V13_WEATHER_BLOCKERS.md — next