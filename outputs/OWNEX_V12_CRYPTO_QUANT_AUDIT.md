# OWNEX v12 — Crypto & Quant Audit (verified 2026-11-09)

## Trading engine — IMPLEMENTED, safe defaults
- `core/trading/`: config.py (TradingMode REAL/DRY_RUN/PAPER_TRADING, **default DRY_RUN**), executor, copy_trading (RiskControls, FollowedTrader), virtual_wallet, dex/jupiter (Solana), store, metrics, reasoning, trader_intelligence.
- Safety: `is_live` flag, max_position_size, slippage/fee caps, paper wallet simulates fees+slippage+latency. Live trading requires explicit TRADING_MODE=real + keys — never default.
- TWIN TREE WARNING: `core/trading/` AND `cores/trading/` both exist; `cores/crypto/` vs scattered crypto modules — consolidation pending (P14).

## Crypto data — IMPLEMENTED (partial)
- `cores/crypto/`: coingecko (market data), btc, evm, solana, tron, wallet_connect, exchange, sync_manager, exchanges/ (mostly empty).
- `core/revenue_multiplier/crypto_trader.py` + `cores/` twin.

## Quant — MOSTLY EMPTY
- `core/quant/strategies`, `core/quant/research`, `core/quant/performance` — directories exist but contain NO implementation files (only __init__/pycache). `core/investment/adapters/quant_research_adapter.py` exists.
- `core/polymarket/backtest` exists (prediction-market backtesting).

## Investment engines — IMPLEMENTED
- `core/investment/`: manager, allocation, smart_allocator, risk_guardian, metrics, attribution, strategist, adapters.
- `cores/capital/`: runway, risk, allocation, diversification, forecasting, maximizer(+advanced), state_machine, timeline, alerts.
- NOT wired: consolidated external portfolio (connections) → capital engines (needs FX policy decision by user).

## Gap vs megaprompt §14
- DATA→SIGNAL→STRATEGY→BACKTEST→OOS→PAPER→RISK→APPROVAL→LIVE pipeline: trading modes exist; quant strategies/backtest framework MISSING (dirs empty). Hummingbot/OpenBB/CCXT evaluation not done (ccxt already used read-only for Binance).
- Recommendation: do NOT build quant strategies until real capital data flows in; priority stays income generation.
