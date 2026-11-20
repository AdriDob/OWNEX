# OWNEX V13 — Probability Engine

## Core Probabilistic Forecast Estimation

**Never assume a normal distribution describes all meteorological errors correctly.** Standard deviation must be estimated and validated per: city, station, model, horizon, variable, and season.

## Gaussian Bucket Model (from Hermes Repo 2)

**Safety constraint**: "adaptation automática no puede modificar estrategias sin validación estadística y límites de seguridad"

The Gaussian Bucket Model discretizes continuous probability distributions into buckets for market analysis.

### Bucket Structure

| Bucket | Range | Interpretation |
|--------|-------|----------------|
| Bucket 0 | (-∞, μ - 2σ] | Extreme low |
| Bucket 1 | (μ - 2σ, μ - σ] | Low |
| Bucket 2 | (μ - σ, μ] | Below average |
| Bucket 3 | (μ, μ + σ] | Above average |
| Bucket 4 | (μ + σ, μ + 2σ] | High |
| Bucket 5 | (μ + 2σ, ∞) | Extreme high |

Where:
- μ = predicted mean
- σ = estimated standard deviation (validated per city/model/horizon/variable/season)

### Probability Calculation

For a Gaussian distribution:
- P(Bucket i) = Φ((upper - μ)/σ) - Φ((lower - μ)/σ)
- Where Φ is the standard normal CDF
- Bucket bounds: μ - 2σ, μ - σ, μ, μ + σ, μ + 2σ

### Key Properties

1. **50% of probability** in Bucket 2 + Bucket 3 (within ±σ of mean)
2. **~34% in Bucket 1 + Bucket 3** (within ±σ but one-side)
3. **~13.5% in Bucket 0 + Bucket 4** (within ±2σ but one-side)
4. **~2.5% in Bucket 0 + Bucket 5** (beyond ±2σ)

### Calibration Requirements

**Mandatory** before any use:

1. **Brier score** calculated per bucket configuration
2. **Calibration curves** per city/model/horizon/variable/season
3. **MAE and RMSE** tracked continuously
4. **Out-of-sample validation** — new models must demonstrate improvement
5. **Walk-forward validation** for strategy evaluation

### Standard Deviation Estimation

σ must be estimated from **historical errors** per group:

```
σ_city_model_horizon_variable_season
```

If insufficient data for a specific combination, fall back to:
1. Same variable, same horizon, different season
2. Same model, different city
3. Different model, same variable
4. Global default (last resort, clearly marked)

### Bias Correction

After estimating σ, apply bias correction:

```
corrected_value = predicted_value + bias_adjustment
```

Where bias_adjustment is calculated from historical under/over-prediction patterns per group.

### Probability Buckets vs. Thresholds

| Approach | Use Case |
|----------|----------|
| **Buckets** | Market discovery — categorize probability ranges for edge detection |
| **Thresholds** | Risk management — trigger actions at specific probability levels |

**Never present probabilities with artificial precision.** Always include uncertainty intervals.

## Market Implied Probability

When Polymarket/Kalshi market prices are available:

```
market_implied_probability = f(price, commission, liquidity, resolution_rules)
```

**Important**: A prediction meteorological more precise does NOT guarantee a profitable operation. Also important:
- Exact market rules
- Location and measurement time horizon
- Event resolution
- Commissions
- Liquidity
- Slippage

## Edge Detection Logic

Compare these values:

| Component | Description |
|-----------|-------------|
| `model_probability` | Probability from Gaussian Bucket Model |
| `market_implied_probability` | Probability from market price |
| `raw_edge` | model_probability - market_implied_probability |
| `adjusted_edge` | raw_edge - costs (commissions + slippage estimates) |
| `expected_value` | adjusted_edge × position_size × payout |
| `confidence` | Brier score / calibration quality score |
| `risk_score` | Uncertainty + liquidity + spread factors |

### Edge Classification

| Edge Range | Classification | Action |
|------------|----------------|--------|
| edge > threshold_high | Strong opportunity | Paper trade only |
| 0 < edge ≤ threshold_high | Moderate opportunity | Paper trade only |
| -threshold_low ≤ edge ≤ 0 | Fair/neutral | No action |
| -threshold_low > edge | Poor opportunity | No action |

**Never automatically consider the difference between estimated probability and price as a profitable opportunity.** Incorporate real costs and execution limitations.

## Historical Learning Loop

### Comparison Data Structure

Every comparison must record:

| Field | Description |
|-------|-------------|
| `original_forecast` | The forecast made at time T |
| `updated_forecast` | Forecast updated later (if applicable) |
| `observation_final` | Actual observed value |
| `market_resolution` | How the market resolved |
| `calculated_probability` | Probability assigned at resolution |
| `result` | Outcome (win/loss for paper trade) |
| `error` | Difference between predicted and actual |
| `brier_score` | Accuracy metric at resolution |
| `confidence` | Model confidence at time of forecast |

### Evaluation Metrics

| Metric | Formula | Target |
|--------|---------|--------|
| **Brier Score** | (forecast_prob - outcome)² | Lower is better (max 0.25 for binary) |
| **Log Loss** | -[y·log(p) + (1-y)·log(1-p)] | Lower is better |
| **MAE** | mean(|forecast - observation|) | Lower is better |
| **RMSE** | sqrt(mean((forecast - observation)²)) | Lower is better |
| **Calibration Curves** | bin → observed frequency | Near 45° line |
| **Accuracy per Bucket** | % correct per bucket | Calibrated per bucket |
| **Error per City** | MAE by city | Minimize variation |
| **Error per Horizon** | MAE by horizon | Minimize variation |
| **Error per Model** | MAE by model | Select best |
| **Error per Season** | MAE by season | Minimize variation |

### Validation Pipeline

```
1. Train    → historical data (first 70%)
2. Validation → remaining 30%, tune hyperparameters
3. Out-of-sample → never-before-seen data
4. Walk-forward → rolling retrain + reevaluate
5. Only if out-of-sample improvement → substitute model
```

**❌ No data leakage** — never use future data to adjust past forecasts.
**❌ No overfitting** — new models must demonstrate out-of-sample improvement.

## Strategy Engine — Modular Strategies

Each strategy is an independent, comparable module:

| Strategy | Basis | Parameters | State | Hypothesis |
|----------|-------|------------|-------|------------|
| `gfs_ensemble` | GFS ensemble probabilities | μ, σ, bucket config | versioned | GFS ensemble mispriced vs market |
| `ecmwf_bucket` | ECMWF Gaussian buckets | μ, σ, bucket config | versioned | ECMWF better calibrated than GFS |
| `multi_model_ensemble` | Weighted combination | weights_per_model | versioned | Combination outperforms individual |
| `gaussian_bucket` | Gaussian Bucket Model | bucket_count, σ_est | versioned | Bucket model accurate |
| `bias_correction` | Historical bias | correction_per_group | versioned | Bias is predictable |
| `historical_calibration` | Historical error correction | correction_scheme | versioned | Historical errors predictable |

### Strategy Requirements

1. **Identifier** — unique name + version
2. **Version** — semantic versioning
3. **Parameters** — all settings, clearly documented
4. **Sources** — which data sources this uses
5. **Hypothesis** — what this strategy bets on
6. **Conditions** — when active/inactive
7. **Results** — historical performance (paper trading only)
8. **Risks** — known failure modes
9. **State** — active/paused/retired
10. **Change history** — what changed and why

### Critical: No Self-Modifying Strategies

❌ **No strategy may modify itself and enter production automatically.**
✅ **Machine learning may propose changes, but must create a NEW experimental version.**

### Strategy Lifecycle

```
created → testing → approved → active → retired
  ↑                                           ↓
  └─────────────── constant evaluation ──────────┘
```

New versions are created via:
- ML model proposal
- Historical learning loop detection
- Manual review and approval

**Never** allow a strategy to modify its own parameters in production.

## Risk Management

| Risk Type | Control | Limit |
|-----------|---------|-------|
| **Maximum exposure** | Total open positions across all markets | Configurable per session |
| **Maximum position size** | Size per individual position | Configurable (fractional Kelly or fixed) |
| **Daily loss limit** | Maximum loss per 24h period | Stop trading if exceeded |
| **Maximum open positions** | Concurrent positions limit | Prevents over-concentration |
| **Liquidity requirements** | Minimum volume per market | Skip illiquid markets |
| **Spread limits** | Maximum acceptable spread | Skip wide-spread markets |
| **Slippage estimates** | Expected slippage per trade | Factor into EV calculation |
| **Uncertainty limits** | Maximum model uncertainty | Skip high-uncertainty forecasts |
| **Correlation limits** | Max correlation between positions | Diversification requirement |
| **Circuit breaker** | Automatic stop after N losses | Prevents catastrophic loss |

### Kelly Criterion — EXPERIMENTAL

⚠️ **Kelly is an option, never used without calibrated probability estimates.**

| Formula | Use Case |
|---------|----------|
| `f = (bp - q) / b` | Full Kelly (b=odds, p=win prob, q=lose prob) |
| `f = fractional_kelly × (bp - q) / b` | Fractional Kelly (conservative) |

**Comparisons**:
- Fractional Kelly vs. fixed position sizes vs. conservative strategies
- Kelly should **never** increase risk after winning streaks
- Position sizing based on **edge / uncertainty**, not historical performance

### Risk Controls (Non-Negotiable)

1. ❌ **No automatic risk increase** after winning streaks
2. ❌ **No position sizing without calibrated probabilities**
3. ❌ **No Kelly without validation** — must have Brier score and calibration curve first
4. ✅ **Fractional Kelly** as experimental option with strict validation
5. ✅ **Maximum daily loss limit** — stop if exceeded
6. ✅ **Circuit breaker** — automatic halt after N consecutive losses
7. ✅ **Liquidity checks** — skip markets below minimum volume
8. ✅ **Spread monitoring** — skip if spread > threshold

## Paper Trading — MANDATORY FIRST

### First Version: Research and Simulation Only

**❌ Real trading NOT enabled in this phase.**

### What Must Be Recorded

| Field | Description |
|-------|-------------|
| `signal` | The trading signal generated |
| `observed_price` | Market price at signal time |
| `simulated_entry_price` | Entry price in simulation |
| `timestamp` | When signal was generated |
| `simulated_size` | Position size in simulation |
| `costs` | Commissions + fees incurred |
| `slippage` | Estimated slippage |
| `resolution` | How the event resolved |
| `result` | Paper PnL outcome |
| `pnl_simulated` | Simulated profit/loss |
| `strategy` | Strategy identifier + version |
| `model_version` | Weather model version used |

### Paper Trading — What NOT to Do

| Prohibition | Reason |
|-------------|--------|
| ❌ **No historical future prices** | Look-ahead bias |
| ❌ **No instant execution assumptions** | Realistic simulation |
| ❌ **No simulated PnL as real OWNEX income** | Revenue rule violation |
| ❌ **No real keys/credentials** | Security |
| ❌ **No trade execution** | Paper only |

### Paper Trading — Realistic Simulation Conditions

1. **Realistic costs** — include commissions, fees, slippage estimates
2. **Time-delimited** — simulate the time between signal and resolution
3. **Market impact consideration** — position size doesn't move market
4. **Same resolution rules** — Polymarket/Kalshi rules apply
5. **Same liquidity conditions** — assume similar market depth
6. **Document everything** — full audit trail for every simulation

## Real Trading — DISABLED

### First Implementation: Research and Simulation Only

**Absolutely not enabled**:

1. ❌ **No real execution** — paper trading only, first version
2. ❌ **No private key storage** — never request or store
3. ❌ **No transaction signing** — no blockchain/crypto signing
4. ❌ **No buy/sell orders** — no token trading
5. ❌ **No deposits/withdrawals** — no fund movement
6. ❌ **No leverage** — 1x only in simulation

### Future Real Trading — Requirements

Any future real trading implementation must be:

1. ✅ **Separate module** — not integrated into core Weather Intelligence
2. ✅ **Permission-protected** — explicit access controls
3. ✅ **Human confirmation** — explicit approval for each trade or batch
4. ✅ **Risk controls** — independent risk management system
5. ✅ **Audit trail** — complete logging of all operations
6. ✅ **Separate from P0 baseline** — doesn't affect revenue metrics
7. ✅ **Graduated rollout** — paper → small real → full with oversight

**⚠️ Real trading requires separate authorization and is OUT OF SCOPE for V13.**

## Frontend Integration — OWNEX Investment Dashboard

### Section: "Weather Intelligence"

Integrated into the **canonical** OWNEX frontend, NOT a separate React app.

### Must Include

| Section | Content |
|---------|---------|
| **Mercados meteorológicos** | Active Polymarket/Kalshi weather markets |
| **Pronósticos** | Current forecasts from GFS, ECMWF, Open-Meteo |
| **Comparación de modelos** | Side-by-side model comparison |
| **Distribuciones probabilísticas** | Gaussian bucket displays |
| **Señales** | Edge detection signals |
| **Edge** | Estimated vs market probability comparison |
| **Liquidez** | Market liquidity status |
| **Riesgos** | Risk scores per signal |
| **Estrategias** | Active/paused strategy list |
| **Backtesting** | Historical performance (paper trading data) |
| **Paper trading** | Simulation controls |
| **Historial** | All previous signals and outcomes |
| **Rendimiento** | Strategy performance metrics |
| **Calibración** | Brier score, calibration curves |
| **Estado de conexiones** | Data source health |

### Display Requirements

- 📋 **Clearly distinguish**: real data, simulations, estimates
- 📋 **Never hide** the source of each signal
- 📋 **Every signal must explain**: why it exists, what data supports it
- 📋 **Separate always**: Observation, Forecast, Calculated probability, Market price, Signal, Simulation, **NO real operation**

### Frontend Components (own implementation, not copied)

- WeatherOverview component
- CityForecast component
- ModelComparison component
- BucketDistribution component
- EdgeSignal component
- StrategyPanel component
- PaperTradingPanel component
- BacktestingPanel component

### NOT allowed

- ❌ Another dashboard React application independent from OWNEX
- ❌ Duplicate financial engine
- ❌ Parallel trading backend

## Multi-Agent Integration

### Coordinated Agents

| Agent | Responsibility |
|-------|----------------|
| **Investment Engine** | Coordinate weather module with overall investment strategy |
| **Financial Hub** | Ensure weather signal PnL doesn't conflict with other positions |
| **Connection Framework** | Manage data source connections and health |
| **Frontend** | Render Weather Intelligence section consistently |
| **QA/Security** | Validate no safety constraints violated |

### Governance Rules

- 📋 **Single writer owner** per module at any time
- 📋 **No shared contract modifications** without coordination
- 📋 **Document architectural decisions** via ADR (Architecture Decision Records)
- 📋 **One agent owns writing** per module
- 📋 **No modifying shared modules without coordination**
- 📋 **Detect duplicaciones** — prefer reuse over recreation
- 📋 **Conservar alternativa técnica superior** — if existing implementation is better, keep it
- 📋 **Registrar decisiones arquitectónicas** — all trade-offs documented

### Agent Coordination Flow

```
Investment Engine → Weather Module → Signal → Paper Trade Simulation → Financial Hub → Risk Check → OK → Record in Dashboard
```

## Test Specifications

### Data Ingestion Tests

- ✅ Unit tests for each data source connector
- ✅ Normalization to unified Weather Record format
- ✅ UTC and timezone conversion
- ✅ Weather station validation
- ✅ Distribution tests (histogram of retrieved values)

### Probability Engine Tests

- ✅ Gaussian Bucket model calculations
- ✅ Standard deviation estimation per group
- ✅ Bias correction application
- ✅ Calibration curve generation
- ✅ Brier score computation
- ✅ MAE/RMSE tracking
- ✅ Out-of-sample validation
- ✅ Walk-forward validation

### Market Discovery Tests

- ✅ Polymarket market data fetching
- ✅ Kalshi market data fetching
- ✅ Market resolution rules parsing
- ✅ Liquidity and volume thresholds
- ✅ Edge detection logic
- ✅ EV calculation with costs
- ✅ Confidence scoring

### Strategy Engine Tests

- ✅ Strategy identifier and versioning
- ✅ Parameter validation
- ✅ Historical results (paper trading only)
- ✅ State management (active/paused/retired)
- ✅ Change history tracking
- ✅ No self-modification in production
- ✅ Comparison between strategies

### Paper Trading Tests

- ✅ Signal recording completeness
- ✅ No look-ahead bias
- ✅ Cost and slippage inclusion
- ✅ Realistic execution timing
- ✅ No simulated PnL as real income
- ✅ Full audit trail

### Risk Management Tests

- ✅ Maximum exposure enforcement
- ✅ Daily loss limit detection
- ✅ Circuit breaker activation
- ✅ Position size validation
- ✅ Liquidity requirement checks
- ✅ Spread limit validation

### License and Security Tests

- ✅ No AGPL code copied from PolyWeather
- ✅ No credentials.txt secrets used
- ✅ No real trading execution
- ✅ Paper trading only mode
- ✅ Argentina access restrictions documented
- ✅ Safety constraint verification

## Deliverables Already Generated

- outputs/OWNEX_V13_WEATHER_DATA_SOURCES.md (created)
- outputs/OWNEX_V13_WEATHER_MODELS.md — to create
- outputs/OWNEX_V13_POLYMARKET_MARKET_ANALYSIS.md — to create
- outputs/OWNEX_V13_WEATHER_STRATEGIES.md — to create
- outputs/OWNEX_V13_WEATHER_RISK.md — to create
- outputs/OWNEX_V13_WEATHER_BACKTEST.md — to create
- outputs/OWNEX_V13_WEATHER_SECURITY.md — to create
- outputs/OWNEX_V13_WEATHER_TESTS.md — to create
- outputs/OWNEX_V13_WEATHER_BLOCKERS.md — to create