# Changelog

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
