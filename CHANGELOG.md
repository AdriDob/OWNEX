# Changelog

## v2.0.0 — 2026-07-05

### 🚀 WalletConnect Protocol
- `cores/crypto/wallet_connect.py`: Conexión con wallets mobile vía WalletConnect v2
- Pairing URI generado como QR, sesión almacenada en Identity Vault
- Delegación de operaciones on-chain a EVMConnector
- `POST /api/crypto/wallets/walletconnect/pair` y `/connect`

### ⛓️ Crypto Expansión
- **BTC connector** (`cores/crypto/btc.py`): Blockstream.info API, satoshi→BTC, vin/vout parsing
- **Solana connector** (`cores/crypto/solana.py`): JSON-RPC mainnet, lamports→SOL, fee parsing
- **Tron connector** (`cores/crypto/tron.py`): TronGrid API, SUN→TRX, TRC20 tokens
- ERC20 tokens expandidos a 19-20 por chain (UNI, AAVE, CRV, SNX, MKR, COMP, LINK, GMX, etc.)
- 44 tests unitarios crypto con HTTP mockeado

### 🛡️ WithdrawalTracker Reorg-Safe
- `cores/financial/withdrawal.py`: +340 líneas — reescritura crypto-first
- `WithdrawalEntry` dataclass con tx_hash, chain, confirmations, block_number, block_hash
- `DEFAULT_CONFIRMATIONS_REQUIRED` por chain (ETH=12, BTC=6, SOL=30, TRX=19)
- `detect_reorg()`, `is_reorg_safe()`, `auto_finalize()` vía CryptoSyncManager
- `ConfirmationMethod.REORG_SAFE` — nuevo método de confirmación

### 🏦 Bank Payout Connector
- `cores/financial/bank_payout.py`: Plaid API + CSV import + webhooks
- `PlaidProvider`: link token, exchange, sync transactions, balances
- `CSVImporter`: parseo de CSV bancarios, auto-detección de plataformas via regex
- `WebhookHandler`: procesamiento de webhooks Plaid y custom
- Detección de pagos de HackerOne, Bugcrowd, Intigriti, Stripe, etc.
- 7 endpoints `/api/bank-payout/*`

### ⚡ Micro‑Functions (10)
- **`cores/financial/micro.py`**: 10 funciones compactas para el dashboard
  - `quick_sync_all()` — sync total con medición de tiempo
  - `sync_source_now()` — sync individual con delta before/after
  - `get_sync_health()` — salud de integraciones (success/error rate, latency)
  - `trace_balance_origin()` — árbol de origen del balance desde ledger
  - `detect_sync_anomalies()` — anomalías con severidad (negativos, stale, mismatches)
  - `get_pending_actions()` — acciones pendientes priorizadas
  - `compute_real_exposure()` — exposición financiera real (crypto + platforms + pending)
  - `export_account_snapshot()` — snapshot completo de cuenta
  - `retry_failed_syncs()` — reintento inteligente con backoff
  - `get_minimal_dashboard_state()` — payload ligero para UI

### 🖥️ Micro‑API Router
- `api/routers/micro.py`: 10 endpoints `/api/micro/*`
- 4 batch endpoints: `/api/micro/batch/export|sync|delete|tag`
- Entity fetch: `/api/micro/entity/{type}/{id}`

### 🎨 Micro‑Interactions Frontend (20)
- **Nuevos componentes**: InspectorPanel, Timeline, MiniPreview, MultiSelectHandler, CompareView, CopyHelper, EmptyState, ErrorRecoveryUI, MoreInfoPanel
- **Nuevos composables**: useMicroInteractions, useCopyHelper, useMultiSelect
- **Nueva store**: `ui.ts` — estado global de inspector, preview, timeline, compare, multi-select
- **Shortcuts mejorados**: Ctrl+Shift+S (sync all), Ctrl+/ (shortcuts help), Alt+←/→ (navegación)
- Keyboard Shortcuts integrados con accessibility store
- Todos los componentes usan Lucide icons, CSS variables CATEYE, glass/cyber theme
- TypeScript compila limpio, 165 tests pasando

### 📚 Documentación
- `finalroadmap.md`: Roadmap unificado (PLAN.md + ROADMAP.md)
- README.md actualizado a v2.0.0 con nuevas features
- SVG logos actualizados (v2.0.0, HUNTER MODE)

### Fixes
- Ruff lint: imports organizados, variables no usadas limpiadas
- API main.py: router micro incluido correctamente
- TypeScript: 0 errores en todos los nuevos componentes

---

## v1.8.0 — 2026-07-04

[Previous entries unchanged from v1.8.0 down to v1.0.0]
