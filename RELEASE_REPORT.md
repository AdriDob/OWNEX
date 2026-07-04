# CATEYE Release Report

## Summary

| Field | Value |
|-------|-------|
| **System** | CATEYE |
| **Version** | v1.7.0 |
| **Release** | v1.7.0 (2026-07-03) |
| **Frontend** | Vue 3 + TypeScript + Vite + Pinia + Tailwind CSS v4 |
| **Backend** | Python 3.10+ · FastAPI · SQLAlchemy · SQLite/PostgreSQL |
| **Desktop** | PyInstaller + PyWebView + Pystray |
| **Build Host** | Linux (development) / Windows (production installer) |

## Release Highlights

### Sistema de Notificaciones Unificado (Mission Inbox)
- **MissionInbox** — centro operativo con línea de tiempo inteligente (Hoy/Ayer/Esta Semana/Este Mes), filtros por prioridad/plataforma/hunter, búsqueda global, acciones masivas, evidencia y conversaciones anidadas
- **AiGuidanceGenerator** — copiloto IA que analiza conversaciones, detecta solicitudes de evidencia, genera borradores de respuesta (requiere aprobación humana), calcula scores de completitud/calidad
- **10 tipos de evidencia** — Screenshot, Video, Log, Request, Response, Timeline, Playwright, etc. con detección IA y revisión humana
- **Conversaciones por evento** — threading con participantes, tags, adjuntos, respuestas desde plataformas
- **Búsqueda y exportación** — búsqueda avanzada en timeline/conversaciones/evidencia, exportación a JSON/CSV/YAML
- **Health checks** — monitoreo de salud con async context manager

### Canales de Notificación
- **WhatsApp** — `WhatsAppAdapter` vía Twilio API (env vars `CATEYE_TWILIO_*`)
- **Gmail** — `GmailAdapter` vía Gmail API OAuth2 (env vars `CATEYE_GMAIL_*`)
- **Email SMTP** — canal existente mejorado
- **FCM** — Firebase Cloud Messaging para push móvil
- **Desktop / Web** — notificaciones nativas del SO y centro de notificaciones in-app

### UniversalPlatformAPI
- **Detección de plataformas** — motor que descubre +8 plataformas (HackerOne, Bugcrowd, Intigriti, Synack, YesWeHack, Huntr, Immunefi, GitHub) desde URLs, HTML/JS, meta tags, redes sociales, directorios bug bounty
- **Configuración JSON** — plataformas definidas por configuración con tipos de auth (BearerToken, BasicAuth, APIKey, OAuth2), rate limits, endpoints, detección de capacidades
- **Estrategias de envío** — auto/semi-auto/manual según plataforma

### UX y Branding
- Rebranding completo de ORION/Rastro a **CATEYE**
- Nueva estética cyber/security: scanlines, glass-terminal, matrix effects
- Logo SVG animado (ojo de gato con iris verde)
- Paleta de colores: `#00ff41` (verde) sobre `#050505` (negro)
- Tooltips contextuales y menús contextuales (right-click)
- Command Palette (`Cmd+K`) con búsqueda de navegación, acciones y targets
- Breadcrumbs limpias, nombres reales en Mission Control, shortcuts visibles
- 22 fricciones UX resueltas en auditoría

### OSINT (16 APIs)
| API | Propósito |
|-----|-----------|
| Shodan | Dispositivos expuestos |
| Censys | Superficie de ataque |
| VirusTotal | Malware/URLs |
| SecurityTrails | DNS history |
| AlienVault OTX | Threat intel |
| URLScan.io | Website analysis |
| Hunter.io | Email discovery |
| BuiltWith | Tech profiling |
| Have I Been Pwned | Breach data |
| GreyNoise | Internet noise |
| IntelX | OSINT search |
| Pulsedive | Threat intel |
| ThreatFox | IOC sharing |
| IPInfo | IP geolocation |
| SpoofCheck | Email spoofing |
| *Cliente bulk con rate limiting y caché por API* | |

### Motor de Herramientas
- **Dalfox** — escaneo XSS automatizado
- **Sqlmap** — detección de SQLi
- **TruffleHog** — detección de secrets en filesystem
- Pipeline unificado que encadena 10+ herramientas con correlación LLM
- Tools registradas en `TOOL_REGISTRY` con wrapper `BaseTool` consistente

### Otros
- Nuevos routers API: `/api/osint`, `/api/hunt`, `/api/settings_unified`
- Watchdog interno con auto-recuperación y backoff exponencial
- Safe rollback en actualizaciones fallidas
- Arquitectura monoproceso (sin subprocess, sin multiprocessing)
- SQLite WAL mode + synchronous=NORMAL
- EventSystem FIFO limit (500 eventos máx)
- Pipeline cache con límite de tamaño
- Migración React → Vue 3 completa
- Config cleanup: eliminados `RastroConfig`, `cores/config.py`

## Tech Stack

| Component | Technology |
|-----------|-----------|
| **Backend** | Python 3.10+ · FastAPI 0.95+ · Uvicorn |
| **ORM** | SQLAlchemy 2.0+ · Pydantic v2 |
| **Database** | SQLite (dev) / PostgreSQL (prod) |
| **Frontend** | Vue 3.5+ · TypeScript 5.8+ · Vite 6.3+ |
| **CSS** | Tailwind CSS 4.1+ |
| **State** | Pinia 3.0+ |
| **UI** | Radix Vue / Reka UI · Lucide Vue |
| **Charts** | Chart.js 4.5+ · vue-chartjs 5.3+ |
| **AI** | Gemini (primary) · Ollama · OpenAI · OpenRouter |
| **Desktop** | PyInstaller · PyWebView · Pystray · Plyer |
| **Mobile** | Capacitor 8 (Android) |
| **Security** | Cryptography (AES-256-GCM) · Fernet |

## Frontend Build

| Metric | Value |
|--------|-------|
| TypeScript errors (`vue-tsc -b`) | **0** |
| Build errors (`vite build`) | **0** |
| Chunks | ~100 (tree-shaken) |
| Pages | 50+ (46 rutas registradas) |
| Componentes UI | Card, Badge, Button, Input, Skeleton, Tooltip, ScrollArea, Separator, CommandPalette, ContextMenu |

## Backend Stats

| Metric | Value |
|--------|-------|
| Python lines (`cores/` + `api/`) | ~58 K |
| Frontend lines (`frontend/src/`) | ~7.5 K |
| Test lines | ~4.5 K |
| **Total source lines** | **~70 K** |
| Python files | 385+ |
| Frontend files (`.ts`/`.vue`/`.css`) | 50+ |
| API routers | ~55 |
| Core modules (`cores/`) | 55+ |

## Platform Integrations

| Platform | Type | Status |
|----------|------|--------|
| HackerOne | Bug Bounty | ✅ Integrada |
| Bugcrowd | Bug Bounty | ✅ Integrada |
| Intigriti | Bug Bounty | ✅ Integrada |
| Synack | Bug Bounty | ✅ Integrada |
| YesWeHack | Bug Bounty | ✅ Integrada |
| Huntr | Bug Bounty | ✅ UniversalPlatformAPI |
| Immunefi | Bug Bounty | ✅ UniversalPlatformAPI |
| GitHub | Security Advisories | ✅ UniversalPlatformAPI |
| Shodan | OSINT | ✅ Integrada |
| Censys | OSINT | ✅ Integrada |
| VirusTotal | OSINT | ✅ Integrada |
| 13 more OSINT APIs | OSINT | ✅ Integradas |

## Canales de Notificación

| Canal | Tecnología | Estado |
|-------|-----------|--------|
| Desktop | plyer (notificaciones nativas OS) | ✅ |
| Web | Centro de notificaciones in-app + WebSocket | ✅ |
| Email | SMTP | ✅ |
| FCM | Firebase Cloud Messaging | ✅ |
| WhatsApp | Twilio API | ✅ Nueva |
| Gmail | Gmail API OAuth2 | ✅ Nueva |

## Herramientas de Seguridad Integradas

| Herramienta | Propósito | Estado |
|------------|-----------|--------|
| OWASP ZAP | DAST scanning | ✅ |
| Subfinder | Subdominios pasivos | ✅ |
| Amass | Subdominios profundos | ✅ |
| Httpx | Sondeo HTTP + tech detect | ✅ |
| Nuclei | Escaneo basado en templates | ✅ |
| Katana | Crawling web | ✅ |
| Gau | URLs históricas | ✅ |
| Ffuf | Fuzzing web | ✅ |
| Waybackurls | Wayback Machine | ✅ |
| Dalfox | Escaneo XSS | ✅ Nueva |
| Sqlmap | Detección SQLi | ✅ Nueva |
| TruffleHog | Secrets en filesystem | ✅ Nueva |
| LinkFinder | Extracción de endpoints JS | ✅ |
| Dnsx | Resolución DNS | 🟡 Settings tracking |
| Naabu | Escaneo de puertos | 🟡 Settings tracking |
| Assetfinder | Descubrimiento de assets | 🟡 Settings tracking |
| Playwright | Capturas automatizadas | ✅ |
| Whois | Consultas WHOIS | ✅ |
| crt.sh | Certificados SSL | ✅ |

## All Tests Verdict

| Area | Result |
|------|--------|
| Backend tests (pytest) | ✅ PASS |
| Ruff linter | ✅ PASS |
| Mypy type check | ✅ PASS |
| Smoke test (HTTP) | ✅ PASS |
| TypeScript compile (`vue-tsc -b`) | ✅ PASS |
| Vite build | ✅ PASS |
| **FINAL** | **ALL GREEN** |

## Recent Commits

- `1c0d602` v1.7.0: 100% backend + test infra + OpenAPI + model rename
- `68c3b5d` cleanup: remove deprecated RastroConfig (cores/config.py)
- `6462436` v1.6.1: path unify + config cleanup + docs refresh
- `cf62911` docs: actualiza SYSTEM.md con auditoría UX, rutas corregidas, v1.6.0
- `7fa5df2` ux: más polish — breadcrumbs limpias, nombre real en Mission Control, shortcuts visibles
- `dafef32` fix: auditoría de fricciones UX — 22 issues resueltos
- `6e901d7` fix: move generated screenshots to docs/screenshots/
- `98e22fb` docs: fix README duplication, regenerate screenshots
- `17b4b64` feat: branding refresh — CATEYE Alpha 1.0, logo animado mejorado, documentación actualizada
- `3542f23` docs: overhaul README with professional layout, screenshots, badges, architecture
- `ec2aa28` various: refactor, cleanup, new routers (hunt, osint), onboarding components, svg assets
- `29f24dc` Migrate React→Vue, core_engines→cores, new API routers, fixes de paths obsoletos

## Changes from v1.6.0

- **v1.7.0**: 100% backend coverage, test infra, OpenAPI schema, model rename
- **v1.6.1**: Path unification, config cleanup (removed `RastroConfig`), docs refresh
- **Nuevo**: Sistema de notificaciones completo (MissionInbox, AiGuidanceGenerator, UniversalPlatformAPI)
- **Nuevo**: Canales WhatsApp y Gmail
- **Nuevo**: 16 integraciones OSINT
- **Nuevo**: Motor de herramientas extendido (Dalfox, Sqlmap, TruffleHog)
- **UX**: 22 fricciones resueltas, breadcrumbs, shortcuts, command palette
- **Branding**: CATEYE completo, logo animado, tema cyber

## Platform Requirements

- **Linux / Windows / macOS** (development)
- **Windows 11 64-bit** (recommended for production installer)
- 4 GB RAM (8 GB recommended)
- No Python or Node.js required for end users (PyInstaller bundle)
- Double-click installation via CATEYEInstaller.exe (Windows)

---

*Report generated on 2026-07-03 18:00:00 UTC*
