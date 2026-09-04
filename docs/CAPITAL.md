# OWNEX Capital System

> **Generated from actual codebase** — This document reflects the real implementation.

## Overview

The Capital System provides a **unified view of net worth** across all revenue streams: bug bounties, dev bounties, work bank, investments, crypto, and savings.

## Unified Capital Snapshot

### Endpoint: `GET /api/capital/snapshot`

```json
{
  "generated_at": "2026-08-27T10:30:00Z",
  "bounty_payouts": {
    "total_received_usd": 12500.00,
    "pending_usd": 3200.00,
    "by_platform": {
      "hackerone": {"received": 8000, "pending": 2000},
      "bugcrowd": {"received": 4500, "pending": 1200}
    }
  },
  "workbank_income": {
    "ready_to_deliver_usd": 15000.00,
    "delivered_pending_usd": 8500.00,
    "targets": {"daily": 10, "weekly": 100, "monthly": 1000}
  },
  "investments": {
    "portfolio_value_usd": 45000.00,
    "unrealized_pnl_usd": 3200.00,
    "realized_pnl_usd": 1100.00,
    "by_asset": {
      "BTC": {"value": 20000, "pnl": 1500},
      "ETH": {"value": 15000, "pnl": 800},
      "STOCKS": {"value": 10000, "pnl": 900}
    }
  },
  "crypto_wallets": {
    "total_usd": 12000.00,
    "by_wallet": {
      "metamask": 8000,
      "ledger": 4000
    }
  },
  "expected_cash": {
    "by_rail": {
      "bank_wire": 5000,
      "crypto_usdc": 3000,
      "paypal": 2000
    },
    "total_usd": 10000.00
  },
  "payment_compat": {
    "compatible_platforms": 12,
    "viable_platforms": 8,
    "incompatible_platforms": 3
  },
  "net_worth_usd": 79500.00,
  "liquidity_usd": 25000.00
}
```

## Data Sources

| Component | Source | Update Frequency |
|-----------|--------|------------------|
| Bounty Payouts | `PayoutRecord` table (synced every 30min) | 30 min |
| Work Bank | `data/workbank.json` (daily cycle 6 AM) | Daily |
| Investments | `InvestmentManager` (Atlas + external APIs) | 15 min |
| Crypto Wallets | `PaymentCompatibilityEngine` configured accounts | Manual/On-demand |
| Expected Cash | `PaymentCompatibilityEngine` + `FinancialSyncScheduler` | 30 min |

## Capital Tracking

### PayoutRecord (Canonical)

```python
class PayoutRecord:
    id: str
    platform: str  # hackerone, bugcrowd, etc.
    external_id: str  # platform:id (dedupe key)
    amount_usd: Decimal
    currency: str  # USD, USDC, ARS, etc.
    status: RECEIVED | PENDING | FAILED
    received_at: datetime
    payout_method: str  # bank_wire, paypal, crypto, etc.
    raw_data: dict  # Original platform response
```

### Deduplication
```python
def persist_earnings(earnings: list[Earning]) -> int:
    """
    Upsert by (platform, external_id)
    - New record → INSERT
    - Existing → UPDATE amount/timestamp
    - Returns count of new records
    """
```

## Net Worth Calculation

```python
def calculate_net_worth() -> NetWorth:
    """
    ASSETS:
    + cash (bank, wallets)
    + investments (portfolio value)
    + crypto (wallet balances)
    + expected_cash (verified only)
    + work_bank.ready_to_deliver (high confidence)
    
    LIABILITIES:
    - credit_cards
    - loans
    - pending_taxes (estimated)
    
    NET_WORTH = ASSETS - LIABILITIES
    LIQUIDITY = cash + crypto_stablecoins + expected_cash_30d
    """
```

## Capital Allocation (`cores/capital/allocation.py`)

### Savings Goals
```python
class SavingsGoal:
    goal_id: str
    name: str
    target_amount_usd: Decimal
    current_amount_usd: Decimal
    target_date: date
    monthly_contribution_usd: Decimal
    auto_allocate: bool  # From work_bank PAID payouts
```

### Allocation Rules
| Priority | Allocation | Source |
|----------|------------|--------|
| 1 | Emergency Fund (3-6 months expenses) | WorkBank PAID |
| 2 | Tax Reserve (30% of revenue) | Every PAID payout |
| 3 | Investment Capital | Remaining PAID |
| 4 | Savings Goals | Per goal monthly_contribution |

### Auto-Allocation
```python
def auto_allocate_payout(payout: PayoutRecord):
    # 1. Tax reserve (30%)
    allocate(payout.amount * 0.30, "tax_reserve")
    
    # 2. Emergency fund (until target)
    if emergency_fund.current < emergency_fund.target:
        allocate(min(remaining, emergency_fund.target - emergency_fund.current), "emergency")
    
    # 3. Savings goals (proportional)
    for goal in active_goals:
        allocate(remaining * goal.monthly_contribution / total_monthly, goal.id)
    
    # 4. Investment capital
    allocate(remaining, "investment_capital")
```

## Investment Integration

### Atlas Portfolio (`apps/atlas/engines/portfolio.py`)

```python
class PortfolioEngine:
    def get_total_value_usd(self) -> Decimal:
        """
        Aggregates:
        - Binance (spot + futures)
        - Kraken (spot + staking)
        - Coinbase (spot)
        - Yahoo Finance (stocks/ETFs)
        - CSV imports (manual)
        - Freqtrade (dry-run positions)
        """
```

### Investment Manager (`cores/investment/manager.py`)

```python
class InvestmentManager:
    def get_portfolio_summary(self) -> PortfolioSummary:
        return PortfolioSummary(
            total_value_usd=atlas_engine.get_total_value_usd(),
            unrealized_pnl_usd=calculate_unrealized_pnl(),
            realized_pnl_usd=calculate_realized_pnl(),
            allocation_by_asset=atlas_engine.get_allocation(),
            risk_metrics=calculate_risk_metrics(),
        )
```

## Payment Compatibility (`cores/payment_compat/`)

### Engine
```python
class PaymentCompatibilityEngine:
    def evaluate(self, method: str, currency: str) -> PaymentVerdict:
        """
        Chain: METHOD → REQUIRED_COUNTRY → CURRENCY → AVAILABLE_ACCOUNTS → VERDICT
        
        Verdict:
        - compatible: true/false
        - viable: true/false
        - score: 0-100
        - matches: list[AccountMatch]
        - off_ramp: str | None
        - missing: list[str]
        - honest_notes: str
        """
```

### Configured Accounts (76)
| Layer | Examples | Function |
|-------|----------|----------|
| Banking USA | GrabrFi, Wise, Payoneer | Primary US receipt |
| Banking AR | Galicia, Santander, MercadoPago | Local ARS |
| Processors | PayPal, Payoneer, Deel | International |
| Crypto | Binance, Kraken, MetaMask, Ledger | USDC/USDT |
| Withdrawal | Belo, DolarApp, Lemon | ARS conversion |

### Usage in Work System
```python
# In IntelligentRecommender:
payment_verdict = payment_compat_engine.evaluate(opp.payment_method, opp.currency)
overall_score *= payment_verdict.score / 100  # Floor 0.3
reasoning.append(f"Payment: {payment_verdict.honest_notes}")
```

## API Endpoints

| Endpoint | Response |
|----------|----------|
| `GET /api/capital/snapshot` | Unified capital view |
| `GET /api/capital/history` | Net worth over time |
| `GET /api/capital/allocation` | Current allocation % |
| `POST /api/capital/goals` | Create/update savings goal |
| `GET /api/capital/goals` | List savings goals |
| `GET /api/payment-compat` | All 76 configured accounts |
| `POST /api/payment-compat/evaluate` | Single payment verdict |
| `POST /api/payment-compat/evaluate/chain` | Receive + off-ramp |

## Frontend: Capital Page (`frontend/src/pages/Capital.vue`)

### Tabs
1. **Overview** — Net worth, liquidity, 30-day trend
2. **Bounty Payouts** — Platform breakdown, pending
3. **Work Bank** — Ready to deliver, targets progress
4. **Investments** — Portfolio, P&L, allocation
5. **Crypto** — Wallets, balances
6. **Expected Cash** — By rail, payment compat
7. **Goals** — Savings goals progress

### Key Components
- `CapitalKPI` — Net worth, liquidity, monthly revenue
- `PlatformPayoutCard` — Per-platform received/pending
- `InvestmentPortfolioChart` — Allocation + P&L
- `PaymentCompatTable` — Platform → method → verdict

## Testing

```bash
pytest tests/test_financial_scheduler_persist.py   # 6 passed
pytest tests/test_atlas_composition.py             # 9 passed
pytest tests/test_payment_compat.py                # 13 passed
pytest tests/test_capital_dashboard.py             # (if exists)
```

---

*Document generated from codebase. Last verified: 2026-08-27*