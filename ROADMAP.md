# CATEYE Roadmap

## v1.0 — Foundation (Complete)
- [x] Backend FastAPI con todos los routers
- [x] Base de datos SQLAlchemy con modelos completos
- [x] Orion Context Engine (core/ai/context/engine.py)
- [x] Frontend React inicial

## v1.1 — AI & Intelligence (Complete)
- [x] AI Copilot con OpenRouter + Ollama
- [x] OrionAgent con tool-calling
- [x] Sistema de memoria e inteligencia
- [x] Pipeline de ejecución autónoma

## v1.2 — Vue 3 Frontend (Complete — 100%)
- [x] Proyecto Vue 3 + Vite + TypeScript
- [x] ShadCN Vue + Tailwind CSS v4 + Lucide Icons
- [x] Dark mode con glassmorphism
- [x] Layout con Sidebar navegación (13 items en 3 secciones, colapsable)
- [x] Command Palette (Ctrl+K) + Copilot (⌘B)
- [x] API Client con auth interceptor, auto-login, loading tracker
- [x] Mission Control Dashboard
- [x] Opportunity Radar, Hot Paths, Findings Pipeline, Report Center
- [x] AI Copilot panel — chat contextual con API real
- [x] Settings con auto-save, validación de import, tools verify, reset con doble confirmación
- [x] Páginas de detalle (target, endpoint, finding, report, pipeline, investigation)
- [x] Onboarding 5 pasos con skip con confirmación

## v1.3 — Polish & Performance (Complete)
- [x] Audit UX completa (24 fricciones resueltas)
- [x] Sidebar reducida 36→13, scanline overlay con CSS var, WS indicator
- [x] Auto-save, breadcrumbs, shortcuts visibles, tooltips en sidebar
- [x] Banner R A S T R O → C A T E Y E, env vars RASTRO_* → CATEYE_*
- [x] Unificación de paths (tray/updater → cores/utils/paths.py)

## v1.4 — Infrastructure & Refinamiento (Complete)
- [x] Alembic configurado con migration inicial (38 tablas)
- [x] Vitest + Vue Test Utils + jsdom instalados (165 tests)
- [x] OpenAPI con security scheme Bearer JWT + metadata completa
- [x] `RastroConfig` SQLAlchemy → `CATEYEConfig` (alias retrocompatible)
- [x] `cores/config.py` eliminado (cache_size → EnvConfig)
- [x] Todos los env vars de EnvConfig en `CATEYE_*`
- [x] Tests frontend (stores, pages, composables) — 165 tests, 92% store coverage
- [ ] Normalizar formato de respuesta API (unificar HTTPException/APIEnvelope/bare dicts)
- [ ] Completar CRUD faltantes (DELETE targets, endpoints, findings, evidence, verdicts)
- [ ] Rebuild Android compiled assets

## v1.5 — Mobile & Desktop
- [ ] Responsive design (mobile sidebar → bottom nav)
- [ ] PWA support (service worker)
- [ ] Capacitor integration (Android)
- [ ] Desktop Tauri build
- [ ] Servicio Linux systemd + macOS launchd

## v1.6 — Enterprise & Plataformas
- [ ] Unificar `cores/platforms/` con `identity_vault.py` + retry + rate-limit
- [ ] Migrar `cores/notifications/` (FCM, SMTP) a env vars `CATEYE_*`
- [ ] Migrar `cores/auth/` + `cores/license/` a env vars `CATEYE_*`
- [ ] Audit logging
- [ ] SSO integration

## v1.7 — Financial Truth Layer (Complete)
- [x] TruthLayer — derivación de estado financiero desde ledger append-only, ValueCategory, confidence scoring
- [x] SyncPipeline — rate limiter token-bucket, cache TTL, retry backoff, delta detection
- [x] WithdrawalTracker — ciclo completo (initiated → pending → completed/failed), confirmation methods
- [x] ReconciliationEngine — auto-resuelve discrepancias, flaggea entradas en disputa, tracking histórico
- [x] Financial Events — 10 eventos enrutados a NotificationHub con prioridades y push
- [x] MoneyRadar rewrite — EV sin hardcoded floors, ingest_real_data(), data_confidence por score

## v1.8 — Crypto Financial Sync System (Complete)
- [x] EVMConnector — 5 chains (ETH/Polygon/BSC/Arbitrum/Optimism) via RPC + explorer API
- [x] ExchangeConnector — Binance/Coinbase/Kraken/Bybit con API firmada HMAC
- [x] CryptoSyncManager — auto-discovery desde IdentityVault, sync_all, historial por wallet
- [x] Ledger upgrade — 9 nuevos LedgerEvent crypto (deposit/withdrawal/staking/yield/swap/gas/airdrop/trade/fee)
- [x] API routers — /api/crypto/* (7 endpoints) + /api/accounts-hub/* (2 endpoints)
- [x] Frontend — AccountsHub.vue, SyncCenter.vue, TruthInspector.vue
- [x] 382 API routes, 165 tests, 0 Vue type-errors

## v1.9 — Platform Sync & AuthHub (Next)
- [ ] sync_earnings() en Intigriti, Synack, YesWeHack (actualmente stubs)
- [ ] AuthHub: Gmail OAuth2, WhatsApp Twilio, Telegram bot
- [ ] Auto-sync scheduler financiero (crypto + plataformas)
- [ ] Account health dashboard con degradación visual

## v2.0 — Wallet Hub & Withdrawals
- [ ] Wallet Connect (WalletConnect protocol)
- [ ] BTC connector via block explorer API
- [ ] Withdrawal tracker upgrade crypto-first (reorg-safe, confirmations)
- [ ] Bank Payout connector (Plaid API)

## Ideas Futuras (Post-v2.0)

### Calidad y Robustez
- **Rate limiting + retry + circuit breaker** en todas las integraciones con plataformas bug bounty
- **Webhook signature verification** para HackerOne, Bugcrowd (HMAC-SHA256)
- **Soporte batch** para plataformas que lo permitan
- **Paginación nativa** en todos los endpoints list
- **Test de base de datos aislada** (SQLite separada para tests)
- **`server_default` con `func.now()`** en vez de strings para portabilidad PostgreSQL

### Plataformas Faltantes
- Módulos `cores/platforms/huntr.py` e `cores/platforms/immunefi.py`
- Implementar Synack (actualmente stub de 32 líneas)
- Agregar Huntr e Immunefi al `identity_vault`
- Scraper con JS rendering (Playwright) para Bugcrowd

### UX / Frontend
- **Cobertura de tests completa** (stores, composables, pages, router)
- **Modo responsivo**: sidebar → bottom nav en mobile
- **PWA**: service worker con cache de assets + offline fallback
- **Vista calendario/timeline** completa (actualmente placeholder)
- **Workflow humano completo**: scope → hipótesis → validación → reporte

### Infraestructura
- **Consolidar build system**: unificar 6 scripts de build dispares en pipeline único (`release_isolation.py` como gold standard)
- **pyproject.toml**: mover dependencias de `requirements.txt` a `[project.dependencies]`
- **GitHub Actions**: CI/CD con lint + test + build automáticos

### Backend
- **Migración a PostgreSQL**: probar migraciones Alembic con Postgres, eliminar dependencias SQLite
- **Manejo de sesiones SQLAlchemy**: estandarizar `Depends(get_db)` en todos los routers
- **response_model Pydantic**: tipar todos los endpoints (actualmente ~30% usan response_model)
- **Migrar `server_default="CURRENT_TIMESTAMP"`** a `server_default=func.now()` (compatibilidad Postgres)

### Seguridad
- **Remover hardcoded API keys** de `.env` (GEMINI_API_KEY visible)
- **Validación de webhooks** con HMAC-SHA256 por plataforma
- **Circuit breaker** para llamadas API externas
- **Test de seguridad automatizados** (inyección, auth bypass, rate-limit bypass)

### Desktop
- **Servicio systemd en Linux** (actualmente solo Windows Service con pywin32)
- **Servicio launchd en macOS**
- **Linux autostart** con `.desktop` file en `~/.config/autostart/`
- **Consolidar íconos**: 4 sets de iconos → 1 set canónico
- **Deprecar formalmente `launcher/start.py`** en favor de `run.py`
- **Crear entry points en pyproject.toml** (`cateye`, `cateye-service`)
