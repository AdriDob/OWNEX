# OWNEX Investment System

> **Generated from actual codebase** — This document reflects the real implementation.

## Overview

The Investment System supports the full investment decision lifecycle: tracking, analysis, recommendation, preparation, approval, execution, confirmation, and reconciliation.

## Philosophy

**Two Legitimate Modes Only:**

| Mode | When | Flow |
|------|------|------|
| **DIRECT EXECUTION** | Real, safe, verified provider integration exists | RECOMMEND → PREVIEW → APPROVE → EXECUTE → CONFIRM → RECONCILE |
| **EXTERNAL EXECUTION** | No direct integration | RECOMMEND → EXPLAIN → OPEN PROVIDER → USER EXECUTES → IMPORT/SYNC → RECONCILE |

**Never** fake direct execution. No "Invest Now" buttons that don't actually move money.

## Architecture

```
Investment System
├── Atlas Portfolio (apps/atlas/) — Multi-exchange portfolio tracking
├── Trading Engine (cores/trading/) — Copy trading + Strategy DNA
├── Investment Manager (cores/investment/) — Traditional investments
├── Payment Compat (cores/payment_compat/) — Provider viability
└── Capital Snapshot — Unified view
```

## 1. Atlas Portfolio (`apps/atlas/engines/portfolio.py`)

### Connectors
| Exchange | Type | Status |
|----------|------|--------|
| Binance | Spot + Futures | ✅ Connected |
| Kraken | Spot + Staking | ✅ Connected |
| Coinbase | Spot | ✅ Connected |
| Yahoo Finance | Stocks/ETFs | ✅ Connected |
| CSV Import | Manual | ✅ Connected |
| Freqtrade | Dry-run | ✅ Connected |
| Hummingbot | Optional | ⚠️ Config |

### Portfolio Engine
```python
class PortfolioEngine:
    def get_total_value_usd(self) -> Decimal:
        # Aggregates all connectors with graceful degradation
        pass
    
    def get_allocation(self) -> dict[str, Decimal]:
        # Returns {asset: value_usd}
        pass
    
    def get_unrealized_pnl(self) -> Decimal:
        # Current value - cost basis
        pass
```

### Factory Pattern
```python
def get_configured_engine() -> PortfolioEngine:
    """
    Registers all available connectors with graceful degradation.
    Missing API keys → connector skipped, not crashed.
    """
```

## 2. Trading Engine (`cores/trading/`)

### Copy Trading (`copy_trading.py`)

```python
class CopyTradingEngine:
    def follow_master(self, master_id: str, config: CopyConfig):
        # Cap per equity % or absolute
        # Drawdown limits (daily/total) → auto-stop
        # DryRunExecutor by default
    
    def replicate_order(self, master_order: Order) -> Order:
        # Normalizes pairs: BASE-QUOTE → BASE/QUOTE
        # Applies sizing rules
        pass
    
    def emergency_stop(self):
        # Stops all copying, closes positions per config
        pass
```

### Strategy DNA (`reasoning.py`)

```python
class StrategyDNA:
    """
    Identifies winning strategies from historical trades.
    - Clusters by entry/exit patterns, indicators, timeframes
    - Scores: win rate, risk/reward, max drawdown, consistency
    - Generates StrategyDNA objects with parameters
    """


class AutoParamOptimizer:
    """
    Proposes parameter optimizations for strategies.
    - Grid search / Bayesian optimization
    - Backtest validation required
    - Human approval before deployment
    """
```

### Trader Intelligence (`trader_intelligence.py`)

```python
class TraderScorer:
    """
    Scores copy trading candidates:
    - BacktestValidator: historical performance
    - LiveTraderMonitor: real-time metrics
    - TraderDiscovery: finds new candidates (Jupiter DEX)
    
    Bands: AVOID (<30) | WEAK (30-50) | NEUTRAL (50-70) | STRONG (70-85) | ELITE (>85)
    """
```

## 3. Investment Manager (`cores/investment/`)

### Traditional Investments
```python
class InvestmentManager:
    def track_position(self, position: InvestmentPosition):
        # Stocks, ETFs, bonds, crypto, real estate
    
    def analyze_performance(self) -> PerformanceAnalysis:
        # TWR, IRR, Sharpe, max drawdown
    
    def recommend_rebalance(self) -> list[RebalanceAction]:
        # Based on target allocation vs current
```

## 4. Investment Recommendation Flow

### Data Model
```python
class InvestmentRecommendation:
    asset: str  # "BTC", "AAPL", "SPY"
    action: BUY | SELL | HOLD
    amount_usd: Decimal
    reasoning: str  # Human-readable explanation
    risk_level: LOW | MEDIUM | HIGH
    time_horizon: SHORT | MEDIUM | LONG
    expected_return: Decimal  # Annualized %
    confidence: HIGH | MEDIUM | LOW
    execution_mode: DIRECT | EXTERNAL
    provider: str | None  # If DIRECT: "binance", "kraken"
    fees_estimate: Decimal
    liquidity_risk: str
    concentration_impact: str
```

### Recommendation Engine
```python
def generate_investment_recommendations(
    capital_available: Decimal, risk_profile: RiskProfile, current_portfolio: Portfolio
) -> list[InvestmentRecommendation]:
    """
    1. Analyze current allocation vs target
    2. Identify gaps (underweight assets)
    3. Score candidates by: expected return, risk, correlation, liquidity
    4. Filter by risk_profile max_drawdown
    5. Size positions (Kelly criterion variant)
    6. Return ranked recommendations
    """
```

## 5. Execution Safety

### Pre-Execution Checks
```python
def validate_execution(recommendation: InvestmentRecommendation) -> ValidationResult:
    checks = [
        ("sufficient_capital", capital.available >= recommendation.amount_usd),
        ("within_risk_limits", portfolio.var_95 < risk_profile.max_var),
        ("not_concentrated", position_weight < max_concentration),
        ("provider_healthy", provider.health_check()),
        ("fees_acceptable", recommendation.fees_estimate < max_fee_pct),
        ("liquidity_sufficient", asset.liquidity_score > min_liquidity),
    ]
    return all(checks)
```

### Execution Flow (DIRECT)
```
1. RECOMMENDATION generated
2. PREVIEW shown: asset, amount, fees, risk, provider
3. HUMAN APPROVAL required (biometric on mobile)
4. EXECUTION via provider API (idempotent)
5. CONFIRMATION: wait for fill + blockchain confirmation
6. RECONCILE: update portfolio, track fees, log trade
```

### Execution Flow (EXTERNAL)
```
1. RECOMMENDATION generated
2. EXPLANATION shown: why this asset, why now, risks
3. PROVIDER OPTIONS: list of supported brokers/exchanges
4. DEEP LINK: "Open Binance" → deeplink to asset
5. USER EXECUTES externally
6. IMPORT: user uploads CSV / API sync / manual entry
7. RECONCILE: match imported trade to recommendation
```

## 6. Provider Integration

### Supported Providers (DIRECT)
| Provider | Assets | Status | Notes |
|----------|--------|--------|-------|
| Binance | Spot, Futures, Earn | ✅ | API key required |
| Kraken | Spot, Staking | ✅ | API key required |
| Coinbase | Spot | ✅ | OAuth |
| Interactive Brokers | Stocks, Options | ⚠️ | Planned |
| Alpaca | Stocks, Crypto | ⚠️ | Planned |

### External Providers (Catalog)
| Provider | Assets | Deeplink Support |
|----------|--------|------------------|
| Binance | All | `binance://asset/BTCUSDT` |
| Kraken | All | `kraken://trade/XBT/USD` |
| Coinbase | All | `coinbase://buy/BTC` |
| Interactive Brokers | Stocks | `ibkr://order/AAPL` |
| Robinhood | Stocks | `robinhood://trade/AAPL` |
| eToro | Stocks, Crypto | `etoro://asset/BTC` |

## 7. Reconciliation

### Automated
```python
def reconcile_daily():
    for provider in configured_providers:
        trades = provider.fetch_trades(since=last_sync)
        for trade in trades:
            match = find_matching_recommendation(trade)
            if match:
                mark_recommendation_executed(match, trade)
            else:
                create_unmatched_trade(trade)  # User manual entry
    update_portfolio_positions()
    update_pnl()
```

### Manual Reconciliation UI
- **Unmatched Trades** table → Link to recommendation or create new
- **Position Drift** alerts (|current - expected| > threshold)
- **Fee Verification** (compare charged vs estimated)

## 8. Risk Management

### Portfolio-Level
| Metric | Limit | Action |
|--------|-------|--------|
| Portfolio VaR (95%) | < 5% NAV | Block new BUY |
| Max Drawdown | < 15% | Reduce leverage |
| Single Asset | < 20% NAV | Warn on BUY |
| Single Sector | < 40% NAV | Warn on BUY |
| Correlation | < 0.7 avg | Diversify |

### Position-Level
| Check | Threshold |
|-------|-----------|
| Stop Loss | -10% from entry (configurable) |
| Take Profit | +20% / +50% (configurable) |
| Max Hold | 365 days (configurable) |
| Liquidity | > $10k daily volume |

## 9. API Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /api/trading/dashboard/summary` | Copy trading overview |
| `POST /api/trading/copy/ingest` | Ingest master order |
| `POST /api/trading/copy/toggle` | Enable/disable master |
| `POST /api/trading/emergency-stop` | Stop all copying |
| `GET /api/trading/reasoning/dna` | Strategy DNA analysis |
| `POST /api/trading/reasoning/proposals` | Param optimization proposals |
| `GET /api/trading/intelligence/discover` | Find new traders |
| `GET /api/trading/intelligence/score` | Score trader |
| `GET /api/investment/portfolio` | Traditional portfolio |
| `POST /api/investment/recommend` | Generate recommendations |
| `GET /api/capital/snapshot` | Includes investment value |

## 10. Frontend

### Pages
- `/trading/intelligence` — Copy trading, trader scoring, Strategy DNA
- `/capital` — Investments tab (portfolio, P&L, allocation)
- `/investment` — Recommendations, execution preview

### Components
- `TradingIntelligence.vue` — 3 tabs: Copy Trading / Trader Intelligence / Strategy DNA
- `InvestmentRecommendationCard` — Shows reasoning, risk, execution mode
- `ExecutionPreviewModal` — Amount, fees, risk, approve button
- `ProviderDeeplinkButton` — "Open in Binance" etc.

## 11. Testing

```bash
pytest tests/test_trading_intelligence.py    # 40 passed
pytest tests/test_investment_manager.py      # (if exists)
```

---

*Document generated from codebase. Last verified: 2026-08-27*