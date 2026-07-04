# Changelog

## v1.8.0 — 2026-07-04

### Financial Truth Layer
- **TruthLayer**: derive FinancialState desde el ledger append-only; ValueCategory enum (VERIFIED_REAL/PENDING/ESTIMATED/MANUAL/UNKNOWN); classify_value() + confidence_from_source()
- **SyncPipeline**: RateLimiter token-bucket por plataforma, SyncCache con TTL, retry con backoff exponencial (hasta 5), delta detection (NEW/UPDATED/REMOVED), SyncConfig con FULL/INCREMENTAL
- **WithdrawalTracker**: create_withdrawal() → mark_pending() → complete_withdrawal() / fail_withdrawal(); ConfirmationMethod (API_VERIFIED/MANUAL_PROOF/RECONCILIATION/UNCONFIRMED); ProofAttachment; get_summary() para KPIs
- **ReconciliationEngine**: check_platform() compara entries externos vs ledger; clasifica DiscrepancyType; auto-resuelve con confianza ≥0.9; flaggea entradas en disputa en TruthLayer
- **Financial Events**: 10 eventos (payout_received, report_accepted, withdrawal_completed/failed, target_detected, sync_completed/failed, reconciliation_conflict, dispute_resolved, high_value_opportunity) enrutados a NotificationHub
- **MoneyRadar rewrite**: EV = P(acceptance) × real_payout_history × exploit_ease; sin hardcoded floors; ingest_real_data() desde sync; data_confidence y data_category en cada EVScore

### Crypto Financial Sync System
- **cores/crypto/**: módulo completo con EVMConnector (Ethereum/Polygon/BSC/Arbitrum/Optimism), ExchangeConnector (Binance/Coinbase/Kraken/Bybit), CryptoSyncManager con auto-discovery desde IdentityVault
- **Ledger upgrade**: 9 nuevos LedgerEvent (CRYPTO_DEPOSIT, CRYPTO_WITHDRAWAL, CRYPTO_STAKING_REWARD, CRYPTO_DEFI_YIELD, CRYPTO_SWAP, CRYPTO_GAS_FEE, CRYPTO_AIRDROP, EXCHANGE_TRADE, EXCHANGE_FEE) + compute_wallet() extendido
- **Financial Events crypto**: 7 eventos financieros crypto con prioridades y push notifications
- **API routers**: /api/crypto/* (7 endpoints) + /api/accounts-hub/* (2 endpoints)
- **Frontend**: AccountsHub.vue (dashboard unificado), SyncCenter.vue (timeline de sincronización), TruthInspector.vue (ledger explorer con búsqueda y detalle)
- **382 API routes**, 165 tests pasando, 0 errores Vue type-check

### Platform Sync
- HackerOne + Bugcrowd: sync_earnings() implementados con API real
- SyncResult dataclass extendido con payouts/programs/totals
- Platform earnings sincronizados automáticamente

### Frontend
- FinancialTruth.vue: 6 KPI cards, barra proporcional, 4 tabs (Resumen/Plataformas/Retiros/Reconciliación), salud de sync por plataforma
- ContextMenu.vue: menú flotante right-click con ARIA accesible y Teleport
- MicroSection.vue: sección colapsable con badge/loading/preview
- QuickActions.vue: toolbar por entidad con acciones contextuales
- useGlobalShortcuts.ts: 13 shortcuts (Ctrl+K, números, flechas, escape)
- useContextMenu.ts: estado universal de context menu + acciones
- accessibility.ts store: 6 settings de accesibilidad (persistidos + CSS bindings)
- Sidebar: balance "Verificado"/"Pendiente" desde /financial/state/summary; navegación Accounts Hub / Sync Center / Truth Inspector

### Fixes
- api/main.py: imports duplicados limpiados (bloque huérfano lines 77–118)
- financial API: rutas registradas correctamente sin conflictos

---

## v1.7.0 (RC4) — 2026-07-04

### 🎯 Release Candidate 4 — Finalización
- **Config system unified**: `CATEYEConfig` reemplaza `EnvConfig` como fuente canónica única con ~45+ env vars y fallback retrocompatible `RASTRO_*`
- **Acceptance Predictor**: nuevo módulo `cores/predictor/` con `AcceptancePredictor`, `PredictionResult`, `ScoreWeights`, `compute_acceptance_score` (9 factores de evaluación)
- **Code audit completo**: autoflake eliminó 93 F401, 3 syntax errors críticos corregidos en `universal_api.py`
- **165 tests frontend + 330 backend = 495 tests pasando** — 92.53% cobertura de funciones en stores

### 🔄 Migración RASTRO_* → CATEYE_*
- 8 archivos migrados de `os.environ.get()` a `get_config()`: `api/main.py`, `api/scheduler.py`, `cores/notifications/email.py`, `fcm.py`, `whatsapp.py`, `gmail.py`, `cores/intelligence/priority_engine.py`, `desktop/main_desktop.py`
- `RASTRO_AUTH_SECRET` → `CATEYE_AUTH_SECRET`, `RASTRO_LICENSE_SECRET` → `CATEYE_LICENSE_SECRET`
- Variables directas `os.environ.get("RASTRO_*")` en auth/license migradas a `CATEYE_*`

### 🧪 Testing
- Mock hoisting con `vi.hoisted()` en 8 test files
- Toast singleton state leak corregido (module-level `toasts` + `setTimeout` cleanup)
- PipelineMonitor error text test corregido
- MissionControl hunt toggle rewrite (verifica store en vez de DOM)
- ~40 Lucide icon stubs registrados globalmente en test-setup.ts

### 📚 Documentación
- **PLAN.md**: branding actualizado, tests marcados como completados, % coverage
- **ROADMAP.md**: v1.4 marcado completo, conteo de tests actualizado
- **CLINE_SETUP.md**, **orion-rules.md**: referencias Orion → CATEYE
- **SYSTEM.md**: directorio raíz `Rastro/` → `CATEYE/`
- **SYSTEM_INVENTORY.md**: referencias a `Orion.spec`/`Rastro.spec` eliminadas (specs ya removidos)
- **docs/SISTEMA.md**: DB path `.orion/` → `.cateye/`

### 🏷️ Branding
- Logos SVG: versión actualizada a v1.7.0, tag "RELEASE CANDIDATE"
- Loggers `catseye.orion.*` → `catseye.cateye.*` en cores/orion/, api/, desktop/
- Mensajes de log `[Orion]` → `[CATEYE]` en context engine, next action, opportunity analyzer
- `scripts/install_tools.sh`: banner "ORION" → "CATEYE"
- `scripts/build_windows.ps1`: "ORION RELEASE ISOLATION" → "CATEYE RELEASE ISOLATION"
- `scripts/generate_screenshots.py`: texto "RASTRO" → "CATEYE" en screenshots generados
- `scripts/generate_icon.py`: default `orion.ico` → `cateye.ico`
- `cores/settings/service.py`: constante `RASTRO_NS` → `CATEYE_NS`

### 🖥️ Desktop & Deployment
- systemd service (`scripts/cateye.service`) con restart policy, hardening, journald logging
- launchd plist (`scripts/com.cateye.service.plist`) con KeepAlive, logging
- `scripts/install_service.sh`: install/uninstall helper unificado Linux + macOS
- Linux autostart restaurado en `desktop/autostart.py` (XDG .desktop)
- Thread name `"orion-server"` → `"cateye-server"`

### 🐛 Correcciones
- `cores/platforms/universal_api.py`: 3 syntax errors (unterminated docstring line 1421, `__init__self` line 707, `x[.protobuf]` line 2274)
- Re-exports `is_license_valid`/`FfufRunner` restaurados en `__init__.py` de license/recon
- Notifications test: expectativa corregida (B at index 0 después de `unshift`)

---

## vAlpha 1.0 (CATEYE) — 2026-07-02

### 🚀 Release
- **CATEYE Alpha Release 1.0** — Nombre oficial cambiado desde ORION/Rastro
- Tema CATEYE cyber security con scanlines, cyber-card, glass-terminal, matrix effects
- Logo animado SVG con estilo ojo de gato (green iris, black slit pupil)
- 16 integraciones OSINT (Shodan, Censys, VirusTotal, SecurityTrails, AlienVault OTX, URLScan.io, Hunter.io, BuiltWith, Have I Been Pwned, GreyNoise, IntelX, Pulsedive, ThreatFox, IPInfo, SpoofCheck)
- Nuevos routers: `/api/osint`, `/api/hunt`, `/api/settings_unified`
- Nuevos componentes UI: Tooltip.vue, ContextMenu.vue, OnboardingWizard.vue
- Settings store (Pinia) para preferencias de usuario
- Migración completa Vue 3 con glassmorphism y theme cyber security
- Screenshot assets actualizados de PNG a SVG con estética cyber

### 🧹 Limpieza
- Eliminados módulos legacy: `cores/export.py`, `cores/fallback.py`, `cores/web3/`, `cores/sync/mobile_sync.py`, `cores/unification.py`
- Eliminados archivos frontend legacy: `KPIGrid.vue`, `OpportunityTable.vue`, `AnimatedNumber.vue`, `EconomicDashboard.vue`
- Eliminados scripts legacy: `scripts/seed.py`, `scripts/seed_v2.py`
- Eliminados assets PWA legacy: `icon-192.png`, `icon-512.png`, `manifest.json`, etc.

### 🛡️ Estabilidad
- Watchdog interno con auto-recovery
- Sistema de auto-healing con backoff exponencial
- Rollback seguro en actualizaciones fallidas
- Arquitectura monoproceso (sin subprocess, sin multiprocessing)

### ⚡ Rendimiento
- EventSystem con límite FIFO (max 500 eventos)
- SQLite WAL mode + synchronous=NORMAL
- Cache de pipelines con límite

---

## v1.6.0 (RC3) — 2026-06-28

### 🚀 Nuevo
- Build pipeline profesional
- Instalador NSIS profesional
- Servicio Windows
- Watchdog interno
- Identity Center
- Auto-update con rollback seguro

### 🛡️ Seguridad y Estabilidad
- Cifrado AES-256-GCM para credenciales
- Flag "Nunca enviar sin aprobación"
- Sesión desktop con auto-autenticación

### 🐛 Correcciones
- Pipeline stuck en PAID → CLOSED
- Scheduler double-wrapping
- Agent subscriptions sin limpiar
- Retry delay faltante en Coordinator
- OOM en EventSystem
- SQLite "database is locked"

---

## v1.5.0 (RC2) — 2026-06-15

- Release Candidate 1
- Arquitectura multi-agente completa
- Pipeline de 11 estados
- Integración con HackerOne, Bugcrowd, Intigriti, YesWeHack, Synack
- Frontend Vue 3 con dark mode (migración desde React)
- 333+ tests pasando
- Exportación PDF / HTML / TXT

---

## v1.0.0 (Foundation) — 2026-06-01

- Backend FastAPI con todos los routers
- Base de datos SQLAlchemy con modelos completos
- Orion Context Engine
- Frontend React inicial (luego migrado a Vue 3)
