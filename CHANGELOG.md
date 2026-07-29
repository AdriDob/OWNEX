# Changelog

## v5.1.0 — 2026-07-29

### 🔧 Integration Registry
- **init_integration_registry** wired into FastAPI lifespan — integrates extension registry with integration status tracking
- **Import cleanup** across all extension modules (aider, git, mcp, playwright, qdrant)

### 🔧 Infrastructure
- Import ordering and formatting consistency improvements across extension connectors and manifests

### 🎯 HTTP Probe Module + Widget Dashboard + Retro UI + MERLIN
- **HTTP Probe Engine**: protocol-agnostic probe core with HTTP/HTTPS adapter, economic scoring before requests, strategic minimal probes
- **Widget Dashboard**: modular widget system with 12 widget types (system health, financial, targets, findings, pipeline status)
- **Retro UI Theme**: retro CRT aesthetic with scanlines, phosphor glow, terminal fonts
- **F1 MERLIN rebrand**: MERLIN agent unified under ORION identity, logo overhaul, README refresh
- **PROMOTE Stage Bridge**: pipeline promotion stage for findings → evidence → report handoff
- **Vision Gateway MCP**: MCP server for vision model integration in the probe/evidence pipeline
- **ORION Identity Docs**: centralized identity and branding documentation

### 🧪 Testing
- **2330 tests**, 100% pass rate, Ruff clean
- `test_revenue_pipeline.py`: 52 passed
- `test_financial_hub.py`: KYC, verification tracker, documents checklist
- `test_target_intelligence.py`: EV-based prioritizer tests
- `test_ai_router.py`: provider failover tests

### 🔧 System
- Command System Fase 1: runtime registry + dispatcher
- Session continuity audit + Command System docs
- Hermes Agent v2: EventBus integration, permission system, security layer

---

## v4.5.0 — 2026-07-20

### 🎯 Offensive Intelligence + Revenue Pipeline
- **Attack Pipeline**: 6 reasoners (IDOR, SSRF, XSS, SQLi, Auth, Web3) con ProbeEngine y Evidence Composer
- **Revenue Pipeline**: pipeline completo Finding → Evidence → Report → Platform → Payout
- **Knowledge Graph**: grafo persistente con nodos/edges, query API, integración COPILOT
- **Execution Runtime**: simulation sandbox + task scheduler con rate limiting por plataforma
- **Platform Hardening**: audit log, rate limiting, CSRF, OAuth2 multi-provider

### 🧠 COPILOT v2
- Senior Copilot Agent: reasoning layer con planner/executor/analyzer/recommender
- Evidence Graph: for/against evidence scoring por hypothesis con persistencia
- Unified Memory: namespaces, tags, expiration, cross-session recall
- Decision Journal: decisiones con contexto + resultado + learning feedback loop
- ConfidenceScorer singleton: aprendizaje propaga al scoring en vivo

### 💰 Financial Expansion
- Capital Dashboard: payout summary, ROI por programa/tipo, acceptance rate, time metrics, program ranking, hot targets
- Economic Memory: ROI scoring histórico por programa y tipo de vulnerabilidad
- ATLAS Financial Intelligence: multi-agent scoring (ATLAS, MIDAS, Risk, Portfolio, F1)
- Investment Hub: gestión de inversiones con portfolio tracking

### 🛠️ Infrastructure
- Pre-commit hooks: Ruff (lint+format) + pytest on every commit
- Integration Center: unified view of all external integrations
- Maintenance Engine: auto-repair de servicios caídos
- Update Manager: actualización automática de pipelines
- Plugin SDK: extensión vía `extensions/` auto-descubrimiento
- Hermes Doctor: diagnóstico completo del sistema

---

## v4.1.0 — 2026-07-12

### 🎯 ORION Financial Layer
- **Financial Hub**: KYC Manager, Route Optimizer, Documents Checklist, Tax Notes, Payouts
- **Takenos integration**: USDC balance + CSV import
- **Coinbase/Kraken**: portfolio via HMAC auth
- **Financial Intelligence**: F1 multi-agent pipeline (scoring, riesgo, PnL)
- Economic dashboard con 30+ cryptos vía CoinGecko

### 🤖 Hermes Agent v1
- Automation Agent para ORION Platform
- Comandos: backup, status, health, logs, portfolio, prices, doctor
- EventBus integration with 3 permission levels
- Safe Mode para operaciones de mantenimiento

### 📚 Documentation & Audit
- Informe final del multisistema v4.1.0
- Documentación en español del README
- Night Finalization Sprint: feedback pipeline, adaptive gate, auditoría
- 3 CRITICAL bugs corregidos de seguridad y consistencia

---

## v4.0.0 — 2026-07-10

### 🏗️ ORION Platform — Arquitectura Definitiva
- **Monolito modular**: EventBus para comunicación interna, arquitectura unificada
- **CATEYE/AEGIS**: bug bounty pipeline con Discovery → Recon → Hypothesis → Validate → Report
- **ATLAS**: financial hub + crypto sync + portfolio tracking
- **ODYSSEY**: research engine + predictive intelligence
- **COPILOT**: capa de inteligencia transversal con 5 niveles de autoridad
- **3 operation modes**: serve (full), hunt (one-shot pipeline), SPA (frontend-only)
- **AI Router**: failover chain Ollama → FCC Proxy → OpenCode Free
- **Target Intelligence**: EV-based prioritizer con TargetPrioritizer + RewardLearner

### 🖥️ Frontend Overhaul
- Vue 3.5+ con Composition API, TypeScript strict mode
- Tailwind CSS v4 + ShadCN Vue components
- Mission Control: dashboard central con estado en vivo
- Command Center: Ctrl+K / Cmd+K con scopes `>`, `/`, `@`, `#`, `$`
- Baby Mode: interfaz simplificada para no-técnicos
- 20+ páginas: Revenue, Capital Dashboard, Financial Hub, Trading, Wallets, Intel, Knowledge Graph, Logs

### 🛡️ Security Hardening
- HMAC machine-id validation
- AES-256-GCM Identity Vault (~/.orion/)
- CSRF middleware con tests HTTP reales
- Rate limiting con config por endpoint
- OAuth2 multi-provider login
- Audit log rotativo (10MB, 3 backups)

---

## v3.0.0 — 2026-07-08

### 🎯 Release Final Stable
- Marco el fin del desarrollo intensivo. CATEYE está lista para uso diario en bug bounty.

### 🧪 Testing
- **393 tests pasan** (359 + 34 tests de seguridad), 2 xfailed, 0 fallos
- `test_security.py` ahora incluido en suite (34 tests, todos verdes)
- CSRF middleware verificado con tests HTTP reales via TestClient
- Rate limit middleware con tests de integración HTTP

### 🛠️ Correcciones de estabilidad
- Scheduler pipeline: 5 stages funcionales (DISCOVER→RECON→HYPOTHESIS→VALIDATE→REPORT)
- `launch_scan()` corregido (argumentos posicionales + session)
- `boot_time` y `collect_health()` bugs corregidos en `api/main.py`
- 3 health systems existentes pero se unificará en v3.1
- Sistema multi-agente: 8 agentes con AgentBus → EventBus bridge

### 🔧 Hardening (prolonged-use audit)
- `FinancialSyncScheduler`: `sync_all()` movido a `asyncio.to_thread`
- `NotificationPoller`: stop flag + shutdown hook
- `Watchdog`: chequea EventBus correcto (no AgentBus)
- `research.py`: imports y clases runner corregidos
- 14 DB indexes agregados via `_migrate_indexes()`
- Orphaned tasks trackeados con `_background_tasks` set
- WAL checkpoint agregado post-ciclo scheduler
- `CorrelationEngine` dedup cache limitado (10K)
- Non-blocking dispatch para BaseAgent/AgentBus
- `with open()` en session.py y token_service.py
- Audit log con rotación (10MB, 3 backups)

### 📚 Documentación
- `FUNCTIONAL_SPEC.md`: 988 líneas de capacidades verificadas contra código
- `USER_GUIDE.md`: Manual práctico en español
- `DAILY_WORKFLOW.md`: Rutina diaria, semanal, mensual
- `RELEASE_NOTES_v3.0.0.md`: Archivo eliminado en limpieza de docs redundantes
- `.ai/` actualizado: AGENT_CHARTER.md, CURRENT_STATE.md, COMPLETED_FEATURES.json

### 📄 Licencia
- Propietaria (validación Ed25519). No MIT.

---

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
