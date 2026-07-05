# CATEYE — Final Roadmap

> **Versión actual:** v2.0.0 | **Última actualización:** 2026-07-05

---

## ✅ v1.0 — Foundation (Complete)
- [x] Backend FastAPI con todos los routers
- [x] Base de datos SQLAlchemy con modelos completos
- [x] Orion Context Engine (core/ai/context/engine.py)

## ✅ v1.1 — AI & Intelligence (Complete)
- [x] AI Copilot con OpenRouter + Ollama
- [x] OrionAgent con tool-calling
- [x] Sistema de memoria e inteligencia
- [x] Pipeline de ejecución autónoma

## ✅ v1.2 — Vue 3 Frontend (Complete)
- [x] Proyecto Vue 3 + Vite + TypeScript + Pinia + ShadCN Vue
- [x] 45+ páginas con lazy loading, dark mode glassmorphism
- [x] Sidebar colapsable (13 items), Command Palette (Ctrl+K), Copilot (⌘B)
- [x] API Client con auth interceptor, auto-login, loading tracker
- [x] Mission Control, Opportunity Radar, Hot Paths, Findings, Report Center
- [x] Onboarding 5 pasos, Settings con auto-save y tool verification

## ✅ v1.3 — Polish & Performance (Complete)
- [x] Audit UX (24 fricciones resueltas)
- [x] Sidebar 36→13, scanline overlay, WS indicator
- [x] Auto-save, breadcrumbs, shortcuts visibles, tooltips
- [x] Banner R A S T R O → C A T E Y E, env vars `RASTRO_*` → `CATEYE_*`

## ✅ v1.4 — Infrastructure & Refinamiento (Complete)
- [x] Alembic configurado, 165 tests frontend + 330 backend
- [x] OpenAPI con security scheme Bearer JWT
- [x] `RastroConfig` → `CATEYEConfig` (alias retrocompatible)
- [x] `cores/config.py` eliminado, todos los env vars en `CATEYE_*`
- [ ] Normalizar formato de respuesta API
- [ ] Completar CRUD faltantes (DELETE targets, endpoints, findings, evidence, verdicts)

## ⏳ v1.5 — Mobile & Desktop (En progreso)
- [ ] Responsive design (mobile sidebar → bottom nav)
- [ ] PWA support (service worker)
- [ ] Capacitor integration (Android)
- [ ] Desktop Tauri build
- [ ] Servicio Linux systemd + macOS launchd

## ⏳ v1.6 — Enterprise & Plataformas (En progreso)
- [ ] Unificar `cores/platforms/` con `identity_vault.py` + retry + rate-limit
- [ ] Migrar notifications/auth/license a env vars `CATEYE_*`
- [ ] Audit logging, SSO integration

## ✅ v1.7 — Financial Truth Layer (Complete)
- [x] TruthLayer — derivación de estado financiero desde ledger append-only
- [x] SyncPipeline — rate limiter token-bucket, cache TTL, retry backoff
- [x] WithdrawalTracker — ciclo completo (initiated→pending→completed/failed)
- [x] ReconciliationEngine — auto-resuelve discrepancias con confianza ≥0.9
- [x] Financial Events (10) enrutados a NotificationHub
- [x] MoneyRadar rewrite — EV sin hardcoded floors, data_confidence por score

## ✅ v1.8 — Crypto Financial Sync System (Complete)
- [x] EVMConnector — 5 chains (ETH/Polygon/BSC/Arbitrum/Optimism)
- [x] ExchangeConnector — Binance/Coinbase/Kraken/Bybit
- [x] CryptoSyncManager — auto-discovery desde IdentityVault
- [x] 9 nuevos LedgerEvent crypto
- [x] API routers crypto (7) + accounts-hub (2)
- [x] Frontend: AccountsHub, SyncCenter, TruthInspector
- [x] 382 API routes, 165 tests frontend, 330 backend

## ✅ v1.9 — Platform Sync & AuthHub (Complete)
- [x] `sync_earnings()` en Intigriti, Synack, YesWeHack
- [x] AuthHub: Gmail OAuth2, WhatsApp Twilio, Telegram bot
- [x] Auto-sync scheduler financiero (crypto + plataformas)
- [x] Account Health Dashboard con degradación visual
- [x] 44 tests crypto, 375 backend total

## ✅ v2.0 — Wallet Hub, Withdrawals & Micro‑Functions (Complete)
### Crypto & Payouts
- [x] WalletConnect protocol (pairing vía QR, delegación a EVMConnector)
- [x] BTC connector via Blockstream.info API
- [x] Solana connector via JSON-RPC
- [x] Tron connector via TronGrid API
- [x] WithdrawalTracker upgrade crypto-first (reorg-safe, confirmations por chain)
- [x] BankPayoutConnector (Plaid API + CSV import + webhooks)

### Micro‑Functions (10)
- [x] `quick_sync_all()` — sync total con medición de tiempo
- [x] `sync_source_now()` — sync individual con delta
- [x] `get_sync_health()` — salud de todas las integraciones
- [x] `trace_balance_origin()` — árbol de origen del balance
- [x] `detect_sync_anomalies()` — anomalías e inconsistencias
- [x] `get_pending_actions()` — acciones pendientes priorizadas
- [x] `compute_real_exposure()` — exposición financiera real
- [x] `export_account_snapshot()` — snapshot completo de cuenta
- [x] `retry_failed_syncs()` — reintento inteligente con backoff
- [x] `get_minimal_dashboard_state()` — estado mínimo para UI rápida

### Micro‑Interactions Frontend (20)
- [x] Right Click Context Menu (global, adaptable por entidad)
- [x] Quick Actions (hover toolbar contextual)
- [x] Inspector Lateral (panel slide-in sin cambiar de página)
- [x] Breadcrumb Inteligente (navegación completa con historial)
- [x] Tooltips Inteligentes (con descripción, fuente, confianza)
- [x] Cards Expandibles (resumen → avanzado → JSON)
- [x] Panel "Más información" (información técnica expandible)
- [x] Timeline (eventos cronológicos con dots de estado)
- [x] Search Everywhere (Ctrl+K)
- [x] Command Palette (acciones globales estilo VSCode)
- [x] Mini Preview (hover popup con resumen + acciones)
- [x] Multi Select (selección múltiple + batch actions)
- [x] Compare View (comparación lado a lado con diff)
- [x] Status Chips (chips visuales para todos los estados)
- [x] Copy Helpers (un clic para copiar ID/hash/JSON)
- [x] Micro Animations (animaciones funcionales CSS nativas)
- [x] Keyboard Shortcuts (Ctrl+K, Ctrl+/, Ctrl+Shift+S, Alt+←/→)
- [x] Empty States (guiados con descripción + acción)
- [x] Error Recovery (reintentar, detalles, copiar error)
- [x] Diseño (minimalista, profesional, ARIA, responsive)

### API Micro Router
- [x] 10 endpoints `/api/micro/*` para cada micro-función
- [x] 4 batch endpoints (`/api/micro/batch/export|sync|delete|tag`)
- [x] Entity fetch endpoint (`/api/micro/entity/{type}/{id}`)

---

## 🚀 v3.0 — Próximo (Planificado)

### Wallet & Pagos
- [ ] Integración PayPal/Stripe como payout methods
- [ ] Swap in-app entre wallets (ETH ↔ USDC)
- [ ] Notificaciones push de pagos en tiempo real

### Frontend Avanzado
- [ ] Dashboard personalizable con widgets arrastrables
- [ ] Modo responsivo completo (mobile bottom nav)
- [ ] PWA con service worker + offline fallback
- [ ] Temas adicionales (AMOLED, terminal, high-contrast)

### Infraestructura
- [ ] PostgreSQL como DB principal (SQLite → dev-only)
- [ ] Pruebas de base de datos aislada
- [ ] GitHub Actions CI/CD completo
- [ ] Build Tauri para desktop nativo

### Plataformas
- [ ] Huntr e Immunefi connectors
- [ ] Scraper con JS rendering (Playwright) para Bugcrowd
- [ ] Webhook signature verification (HMAC-SHA256)

### Seguridad
- [ ] Circuit breaker en llamadas API externas
- [ ] Rate limiting + retry en integraciones bug bounty
- [ ] Tests de seguridad automatizados

---

## 📊 Estado Actual

| Componente | Estado | Métrica |
|-----------|--------|---------|
| Backend tests | ✅ | 375 passing, 2 xfailed |
| Frontend tests | ✅ | 165 passing (17 suites) |
| TypeScript | ✅ | 0 errors |
| Ruff lint | ✅ | 0 errors |
| API routes | ✅ | 390+ endpoints |
| Frontend pages | ✅ | 45+ páginas |
| Crypto chains | ✅ | 9 (EVM×5, BTC, SOL, TRX, Exchange×4) |
| Platforms | ✅ | 5 (H1, BC, INT, SYN, YWH) |
| Micro-functions | ✅ | 10 funciones + batch + entity |
| Micro-interactions | ✅ | 20 componentes + composables |
| AuthHub | ✅ | Gmail, WhatsApp, Telegram |
| WalletConnect | ✅ | Pairing QR, sesión vault |
