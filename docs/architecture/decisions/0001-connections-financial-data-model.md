# ADR-0001: Connections data lives in JSON stores + canonical ledger; capital engines stay manual-input until FX policy decided

- **Status**: ACCEPTED
- **Date**: 2026-11-09
- **Context**: v12 required consolidating IOL/PPI/Binance/imported data into OWNEX finance. Existing engines (`cores/capital`, `core/investment`) take manual inputs; `cores/ledger` is the canonical income record.
- **Decision**:
  1. Provider snapshots/normalized data persist as JSON under OWNEX data dir (`connections/{snapshots,normalized,exports}`), NOT new DB tables — reuses existing pattern, zero migrations.
  2. Normalization targets existing canonical types (`core/normalizer/base.py`).
  3. Cash/positions grouped per currency; **no FX conversion ever invented** — consolidation is per-currency only.
  4. Income reaches the ledger only via explicit user action (`POST .../income-candidates/import`, idempotent `inc_<hash>` source_id, `ADJUSTMENT_MANUAL`).
  5. Capital engines (`runway`/`risk`) are NOT fed consolidated balances yet — pending user FX policy.
- **Alternatives considered**: new SQLAlchemy models for positions (rejected — JSON stores match existing convention and avoid migration risk); auto-convert to USD (rejected — fabricates financial data); wire capital engines immediately (rejected — requires FX decision).
- **Consequences**: honest per-currency views now; capital runway ignores external balances until FX decided; ledger stays clean of transfers/trades.
- **Modules affected**: `cores/connections/*`, `api/routers/connection_manager.py`, `cores/ledger`, `cores/capital` (future).
