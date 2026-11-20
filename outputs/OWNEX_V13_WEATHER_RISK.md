# OWNEX V13 — Risk Management

## Non-Negotiable Safety Constraints

These controls are **absolutely protected** and cannot be bypassed, modified, or disabled:

1. ❌ **No real trading execution** — paper trading only, V13 first version
2. ❌ **No automatic strategy modification** without statistical validation and safety limits
3. ❌ **No hidden real-execution code paths** — must always verify disabled
4. ❌ **No AGPL code reuse** in OWNEX without legal analysis (PolyWeather AGPL-3.0)
5. ❌ **No credentials.txt secrets** — ML Weather Model, never open/use
6. ❌ **No position sizing without calibrated probabilities**
7. ❌ **No Kelly without validated calibration** — Brier score and calibration curve mandatory first
8. ❌ **No bypass of geoblocking** nor account restrictions (Argentina access)
9. ❌ **No trading without human gate approval**
10. ❌ **No simulated PnL counted as real OWNEX income**

## Risk Controls Table

| Control Type | Implementation | Enforcement |
|-------------|---------------|-------------|
| **Maximum exposure** | Total open positions across all markets | System-enforced limit; strategy reports but system decides |
| **Maximum position size** | Size per individual position | Configurable; fractional Kelly or fixed fraction; strategy proposes, system disposes |
| **Daily loss limit** | Maximum loss per 24h period | Stop trading if exceeded; circuit breaker triggers |
| **Maximum open positions** | Concurrent positions limit | System counter; blocks new positions if limit reached |
| **Liquidity requirements** | Minimum volume per market | Skip markets below threshold; verified before trade entry |
| **Spread limits** | Maximum acceptable spread | Skip markets if spread > threshold; real-time check |
| **Slippage estimates** | Expected slippage per trade | Included in adjusted_edge; estimated per market condition |
| **Uncertainty limits** | Maximum model uncertainty | Skip forecasts with risk_score > threshold |
| **Correlation limits** | Max correlation between positions | System monitors; blocks if correlation exceeded |
| **Circuit breaker** | Automatic stop after N losses | System-wide, overrides individual strategy; resets after review |

## Probability Calibration Requirements

**Before any strategy can generate signals, these must be validated:**

| Requirement | Description | Validation Method |
|-------------|-------------|-------------------|
| **Brier score** | Probability accuracy metric | Calculated per city/model/horizon/variable/season; must be below threshold |
| **Calibration curves** | Probability distribution vs observed frequency | Near 45° line; tested via out-of-sample data |
| **MAE** | Mean absolute error | Tracked continuously; per group statistics |
| **RMSE** | Root mean square error | Tracked continuously; per group statistics |
| **Standard deviation σ** | Estimated and validated | Per: city, station, model, horizon, variable, season; fallback chain if insufficient data |
| **Bias correction** | Systematic error correction | Validated via walk-forward; not applied until out-of-sample testing passes |

**❌ No strategy generates signals if any of the above are unvalidated.**

## Position Sizing — Fractional Kelly (Experimental)

### Formula

```
f = fractional_kelly × (bp - q) / b
```

Where:
- `f` = fraction of capital to risk
- `fractional_kelly` = conservative multiplier (typically 0.25-0.5)
- `b` = odds received (payout ratio)
- `p` = probability of win (calibrated model probability)
- `q` = probability of lose (1 - p)

### Kelly — EXPERIMENTAL Only

⚠️ **Kelly is an option, never used without calibrated probability estimates.**

| Condition | Action |
|-----------|--------|
| No calibrated probabilities | ❌ Kelly NOT enabled |
| Brier score unvalidated | ❌ Kelly NOT enabled |
| No calibration curve | ❌ Kelly NOT enabled |
| Out-of-sample validation failed | ❌ Kelly NOT enabled |
| First activation | ⚠️ Start with `fractional_kelly = 0.25` |
| Successful validation | ⚠️ Can increase to 0.5, but never full Kelly |

### Fractional Kelly — Recommended Default

| Risk Tolerance | fractional_kelly | Rationale |
|---------------|------------------|-----------|
| Conservative | 0.10 - 0.25 | Low risk, slow growth |
| Moderate | 0.25 - 0.50 | Balanced growth/risk |
| Aggressive | 0.50 - 0.75 | High risk, faster growth (not recommended) |
| Not recommended | > 0.75 | Excessive risk |

### Fixed Position Sizing (Alternative)

When calibrated probabilities unavailable or Kelly too aggressive:

```
position_size_fixed = capital × fixed_fraction
```

Where `fixed_fraction` typically 0.01 - 0.05 (1-5% of capital per trade).

### Position Sizing — What's PROHIBITED

| Prohibition | Reason |
|-------------|--------|
| ❌ Automatic risk increase after winning streaks | Gambler's fallacy, not statistical |
| ❌ Position sizing without calibrated probabilities | Undefined risk |
| ❌ Full Kelly without validation | Excessive risk |
| ❌ Position sizing based solely on historical performance | Overfitting |
| ❌ Dynamic risk increase based on PnL | No statistical basis |
| ❌ Fixed position ignoring edge size | Wastes edge or exceeds risk |

## Daily Loss Limit — Circuit Breaker

### Implementation

```
daily_pnl_cumulative = sum of all pnl_simulated today

if daily_pnl_cumulative ≤ -daily_loss_limit:
    circuit_breaker_triggered = True
    block_all_new_trades = True
    alert_human_gate = True
    log_event("circuit_breaker_triggered", daily_pnl_cumulative)
```

### Parameters

| Parameter | Default | Rationale |
|-----------|---------|-----------|
| `daily_loss_limit` | 10% of allocated capital | Stops significant daily drawdown |
| `circuit_breaker_reset` | After review + human approval | Prevents automatic restart without oversight |
| `consecutive_losses_trigger` | 5 consecutive losses | Early warning before daily limit |
| `reset_period` | 24h from trigger | Aligns with daily PnL window |

### Circuit Breaker Behavior

1. **Triggered** when daily PnL ≤ -limit
2. **All new trades blocked** — no strategy can override
3. **Human gate alert** — notification to approver
4. **Reset requires** — human approval, not automatic
5. **Post-mortem** — analyze why before restart
6. **Restart** — only after root cause addressed

## Uncertainty Limits — When to Skip

Skip forecast/model when:

| Condition | Threshold | Action |
|-----------|-----------|--------|
| `risk_score` > maximum | > 0.7 (on 0-1 scale) | Skip forecast, no trade |
| `σ` estimation insufficient | < min_data_points per group | Use fallback or skip |
| Calibration error > tolerance | > acceptable_error | Skip, improve calibration first |
| Model not validated for group | No data for city/model/horizon/variable/season | Skip or use most similar group |
| Seasonal variation high | Known high-variance season | Use season-specific model if available |

### Risk Score Calculation

```
risk_score = weighted_combination(
    uncertainty_from_σ,
    liquidity_penalty,
    spread_penalty,
    calibration_error,
    sample_size_penalty
)
```

Each component in [0, 1] range, weights configurable but default:
- uncertainty_from_σ: 0.4
- liquidity_penalty: 0.2
- spread_penalty: 0.2
- calibration_error: 0.15
- sample_size_penalty: 0.05

**If risk_score > 0.7 → skip forecast.**

## Liquidity Requirements — When to Skip Markets

Skip market entry when:

| Metric | Threshold | Action |
|--------|-----------|--------|
| `liquidity_usd` | < 1000 | Skip market, seek more liquid |
| `volume_24h_usd` | < 500 | Skip market, seek more activity |
| `bid-ask spread` | > 0.05 | Skip market, wider spread costly |
| `market_age` | < 24h | Skip, insufficient price discovery |
| `open_interest` | Not available/low | Use liquidity_usd + volume_24h as proxy |

**Never execute trade in market below liquidity thresholds.**

## Spread Limits — When to Skip

Skip when:

| Condition | Threshold | Action |
|-----------|-----------|--------|
| `ask - bid` > 0.05 | > 5% spread | Skip, spread too high |
| `ask - bid` > 0.10 | > 10% spread | Definitely skip |
| `ask - bid` > 0.25 | > 25% spread | Avoid, extremely costly |

**Spread includes both explicit commission and implicit slippage.**

## Correlation Limits — Diversification Requirement

System monitors position correlation:

| Metric | Threshold | Action |
|--------|-----------|--------|
| `pairwise_correlation` | > 0.7 between any 2 positions | Reduce concentration, diversify |
| `portfolio_correlation` | > 0.8 overall | Rebalance across uncorrelated markets |
| `concentration_ratio` | Top N positions > 70% equity | Reduce largest positions |

**❌ No strategy may increase correlation to bypass diversification.**

## Circuit Breaker — System-Wide Override

The circuit breaker **overrides all strategies**:

```
if circuit_breaker_active:
    block all new trade entries
    close existing positions (if configured)
    alert human gate
    log detailed event
    require approval before resume
```

**Strategy has NO ability to override or bypass the circuit breaker.**

## Integration with Paper Trading

Risk controls integrate with paper trading simulation:

```
Paper Trade Flow:
1. Strategy generates signal
2. System checks all risk controls
3. If any control fails → block signal, return "rejected"
4. If all pass → simulate trade
5. Record pnl_simulated
6. Update cumulative daily PnL
7. Check circuit breaker
8. If circuit triggered → block further trades
9. Update strategy state and results
```

**❌ Strategy never sees "real" PnL — only simulated.**
**❌ Simulated PnL never counted as real OWNEX revenue.**
**❌ Human gate must approve any circuit breaker reset.**

## Argentina Access Risk Controls

Additional controls for Argentina-based operation:

| Control | Status | Documentation |
|---------|--------|---------------|
| Geoblocking bypass | ❌ Never | Documented in data sources |
| Residency requirement | ⚠️ Investigate | Document result |
| KYC requirement | ⚠️ Investigate | Document result |
| Payment methods from AR | ⚠️ Investigate | Document result |
| Platform acceptance | ⚠️ Investigate per platform | Polymarket/Kalshi separately |
| Commission rates AR | ⚠️ Investigate | May differ from standard |
| Tax obligations AR | ⚠️ Investigate | Document or consult tax advisor |

**❌ Never assume API-accessible = legally financable from Argentina.**
**❌ Never bypass geoblocking nor account restrictions.**

## Risk Management Integration Summary

```
┌─────────────────────────────────────────────────────────┐
│  STRATEGY ENGINE generates signal                         │
│  │                                                        │
│  ▼                                                        │
│  RISK MANAGER checks:                                     │
│  │                                                        │
│  ✅ Maximum exposure not exceeded                        │
│  ✅ Position size within limits                          │
│  ✅ Daily loss limit not breached                        │
│  ✅ Max open positions not reached                       │
│  ✅ Liquidity requirements met                           │
│  ✅ Spread within limits                                 │
│  ✅ Slippage estimated and included                      │
│  ✅ Uncertainty risk_score ≤ threshold                   │
│  ✅ Correlation limits not violated                      │
│  ✅ Circuit breaker not active                           │
│  ✅ Argentina access restrictions respected              │
│  │                                                        │
│  ► ALL PASS → Paper trade simulation                      │
│  ▼                                                        │
│  SIMULATION → pnl_simulated → historical learning →      │
│  strategy state update                                    │
│  │                                                        │
│  ◄ ANY FAIL → "signal rejected" → strategy logs           │
│  │                                                        │
│  ⚠️ Circuit breaker → human gate approval required        │
└─────────────────────────────────────────────────────────┘
```

## Deliverables Already Generated

- outputs/OWNEX_V13_WEATHER_DATA_SOURCES.md (created)
- outputs/OWNEX_V13_WEATHER_MODELS.md (created)
- outputs/OWNEX_V13_POLYMARKET_MARKET_ANALYSIS.md (created)
- outputs/OWNEX_V13_WEATHER_STRATEGIES.md (created)
- outputs/OWNEX_V13_WEATHER_RISK.md — created above
- outputs/OWNEX_V13_WEATHER_BACKTEST.md — next
- outputs/OWNEX_V13_WEATHER_SECURITY.md — next
- outputs/OWNEX_V13_WEATHER_TESTS.md — next
- outputs/OWNEX_V13_WEATHER_BLOCKERS.md — next