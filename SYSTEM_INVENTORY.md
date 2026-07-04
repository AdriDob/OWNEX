# SYSTEM_INVENTORY.md

> Inventario técnico completo del sistema CATEYE.
> Mantener actualizado ante cualquier cambio significativo.

---

# 1. Resumen del sistema

| Campo | Valor |
|---|---|
| **Nombre del proyecto** | CATEYE (formerly ORION / Rastro) |
| **Objetivo principal** | Sistema de inteligencia artificial para automatizar el ciclo completo de bug bounty: descubrimiento, análisis de alcance, reconocimiento, generación de hipótesis, validación, generación de reportes y envío a plataformas (HackerOne, Bugcrowd, Intigriti, Synack, YesWeHack) |
| **Estado actual** | Producción (Stable) |
| **Versión** | 1.8.0 |
| **Fecha de última actualización** | 2026-07-04 |
| **Licencia** | MIT |
| **Arquitectura** | Monolito modular con frontend SPA |
| **Lenguaje principal** | Python 3.10+ |
| **Backend** | FastAPI + SQLAlchemy + SQLite/PostgreSQL |
| **Frontend** | Vue 3 + TypeScript + Tailwind CSS v4 + Vite |
| **Desktop** | PyInstaller + pywebview + pystray |

---

# 2. Arquitectura General

## Frontend

- **Tecnología:** Vue 3.5+ SPA con TypeScript
- **Build tool:** Vite 6.3+
- **Estilos:** Tailwind CSS 4.1+
- **Estado:** Pinia 3.0+
- **Enrutamiento:** Vue Router 4.5+ con guardia global de autenticación
- **Componentes UI:** Radix Vue / Reka UI (headless accesibles), Lucide Vue (iconos), VueUse (composables)
- **Gráficos:** Chart.js + vue-chartjs
- **API Client:** Cliente HTTP propio en `frontend/src/lib/api.ts` con 50+ funciones tipadas, autenticación automática, SSE streaming, manejo de errores
- **Rutas:** ~50 páginas registradas en el router
- **Ubicación:** `frontend/`

## Backend

- **Tecnología:** Python 3.10+ con FastAPI
- **Estructura:** Monolito modular organizado por dominios en `cores/`
- **Módulos principales:** 50+ subdirectorios en `cores/` que cubren AI, recon, inteligencia, agentes, orquestación, plataformas, reporting, etc.
- **Punto de entrada único:** `run.py` (máquina de estados: browser, tray, service, safe-mode, build, install)
- **Launcher secundario:** `launcher/start.py` (modo desarrollo multi-proceso)
- **Logging unificado:** `cores/log_config.py` con formato prefijado por módulo
- **Observabilidad:** `cores/observability.py` con métricas
- **Ubicación:** `cores/`, `api/`

## API

- **Framework:** FastAPI
- **Puerto:** 8000 (por defecto)
- **Prefijo:** `/api/*`
- **Routers:** 52 routers en `api/routers/`
- **Middleware:** CORS, autenticación, rate limiting, manejo de errores
- **Schemas:** Pydantic en `api/schemas/`
- **Documentación:** Swagger UI en `/docs` (FastAPI auto)
- **Grupos de endpoints:** economic, orion, targets, findings, reports, pipeline, attack, verdicts, evidence, zap, hunt, assistant, validation, auth, license, system, sync, webhooks, connections, overview, etc.

## Base de datos

- **ORMs:** SQLAlchemy 2.0+
- **Soporte:** SQLite (desarrollo/default) y PostgreSQL (producción)
- **Modelos principales:** `database/models.py` (~30 modelos) + `database/models_economic.py` (~8 modelos)
- **Migraciones:** No hay sistema de migraciones formal (esquema gestionado por código)
- **Ubicación por defecto:** `~/.cateye/database/cateye.db`
- **Configuración:** `DATABASE_URL` en variable de entorno

## Event Bus

- **Implementación:** `cores/events/event_bus.py` — pub/sub asíncrono con priorización
- **Prioridades:** critical, high, medium, low, ignore
- **Eventos predefinidos:** system:error, system:degraded, opportunity:found, quick_win:detected, etc.
- **Límite FIFO:** 500 eventos máximo

## Watchdog

- **Implementación:** `desktop/watchdog.py` — supervisor interno
- **Monitorea:** API health, agentes, scheduler, eventbus, memoria, CPU
- **Recuperación:** Multi-nivel con backoff exponencial (RecoveryEngine → HTTP restart → EventBus reinit)
- **Detección:** Congelamiento, memory leaks, service failures
- **Estados:** HEALTHY, DEGRADED, FAILED, UNKNOWN

## Agentes IA

- **Sistema:** `cores/agents/` — 8 agentes especializados que se comunican vía bus de eventos
- **Agentes:** Coordinator, Research, Validator, Exploit, Documentation, Strategy, Memory, Financial
- **Comunicación:** Event bus (`cores/agents/bus.py`) con eventos inmutables tipados
- **Pipeline de 11 estados:** pending → discovery → validation → evidence → ai_review → ready → submitted → triaged → paid → closed → failed/cancelled
- **Agente principal chat:** `cores/ai/orion_agent.py` — CATEYE Agent con tool calling (Gemini → OpenRouter → Ollama)

## Workers

- **Scheduler de pipelines:** `api/scheduler.py` — `ScanScheduler` asíncrono
- **Etapas programadas:** discover (1h), recon (30min), hypothesis (15min), scope_check (1h), validate (2h), report (1h)
- **Motor autónomo 24/7:** `cores/autonomous/engine.py` — escanea targets priorizados por ORION Score

## Scheduler

- **Implementación:** `api/scheduler.py` — `ScanScheduler` (basado en asyncio)
- **Intervalo base:** 30 minutos (configurable)
- **Etapas:** discover, recon, hypothesis, scope_check, validate, report
- **Control vía API:** POST /api/hunt/start, /pause, /resume, /stop

## Servicios

| Servicio | Archivo | Propósito |
|---|---|---|
| Windows Service | `desktop/service.py` | Servicio Windows con pywin32 |
| Desktop Settings | `desktop/settings.py` | Configuración persistente JSON |
| Desktop Notifications | `desktop/notifications.py` | Notificaciones OS (plyer) |
| Desktop Tray | `desktop/tray.py` | Icono de bandeja del sistema (pystray) |
| Desktop Updater | `desktop/updater.py` | Auto-actualización desde GitHub Releases |
| Desktop Autostart | `desktop/autostart.py` | Inicio automático del sistema |
| Desktop Browser Opener | `desktop/browser_opener.py` | Apertura de dashboard en navegador |
| Boot Guard | `desktop/boot_guard.py` | Guardián de arranque seguro |
| First Run | `desktop/first_run.py` | Configuración inicial en primer inicio |
| Serve Frontend | `desktop/serve_frontend.py` | Servidor de archivos estáticos del frontend |
| Service Util | `desktop/service_util.py` | Detección ligera del servicio Windows |
| Identity Vault | `cores/identity_vault.py` | Bóveda encriptada de credenciales (AES-256-GCM) |
| Event Bus | `cores/events/event_bus.py` | Bus de eventos interno |
| Timeline | `cores/timeline.py` | Motor de línea de tiempo histórica |
| System State | `cores/system_state.py` | Estado global del sistema |
| System Health | `cores/system_health.py` | Salud del sistema |
| Observability | `cores/observability.py` | Métricas y observabilidad |
| Log Config | `cores/log_config.py` | Configuración unificada de logging |
| WebSocket Bridge | `cores/ws/bridge.py` | Puente WebSocket |

## Módulos

Lista completa de submódulos en `cores/`:

| Módulo | Responsabilidad |
|---|---|
| `ai/` | Proveedores IA (Ollama, OpenAI, Gemini, OpenRouter), agente CATEYE, tools, advisor, assistant, analyzer, insights, memory, recommendations, summary, context engine |
| `recon/` | Wrappers para herramientas externas: subfinder, amass, httpx, katana, nuclei, ffuf, gau, waybackurls, crt.sh, burp_import, zap_runner, whois, parser |
| `engine/` | Motores de inteligencia: hypothesis (generación de hipótesis vía LLM+ZAP), unified_scoring, roi_model, correlation, extraction, guardrails, risk_model, priority_rebalancer, snapshot, unified_classifier |
| `intelligence/` | Bucle de inteligencia: learning_loop, adaptive_memory, reward_learning, bounty_intel, noise_filter, trend_detector, priority_engine, recommendation_engine, unified_orchestrator, pattern_registry, historical_analyzer, dependency_graph, event_system, caching, export, observability, anti_drift |
| `scope_reader/` | Descarga y parseo de documentos de alcance de programas |
| `orchestrator/` | Orquestación de pipelines: pipeline, assistant_orchestrator, scan_service |
| `autonomous/` | Motor de cacería autónoma 24/7 |
| `crypto/` | Crypto Wallet Sync: base (CryptoConnector ABC + tipos), evm (EVMConnector 5 chains), exchange (ExchangeConnector 4 exchanges), sync_manager (CryptoSyncManager) |
| `opportunity/` | Scoring de oportunidades, EVH, ORION Score, recomendaciones |
| `platforms/` | Integraciones: hackerone, bugcrowd, intigriti, synack, yeswehack + base abstracta |
| `agents/` | Sistema multi-agente: base, bus, coordinator, research, validator, exploit, documentation, strategy, memory, financial, types, bus |
| `reporting/` | Generación de reportes: report_engine, export_formats, severity + templates HTML |
| `validation/` | Motor de validación: confidence, evidence_builder, gate, hardening, llm_analyzer, loop_engine, replayer, rules, verdict_handler |
| `evidence/` | Gestión de evidencia: graph, store |
| `execution/` | Ejecución de exploits/PoC: differential_engine, gap_analyzer, poc_generator, request_mutator |
| `memory/` | Memoria a largo plazo: decision_memory, identity_graph, insight_archive, learning_scorer, memory, memory_store, pattern_extractor |
| `tracking/` | Tracking de envíos y pagos |
| `learning/` | Enrutamiento de aprendizaje: explainer, export, memory, prioritizer, profile, router, tracker |
| `events/` | Bus de eventos interno |
| `analysis/` | Análisis: analyzer, investigation_graph, noise_reduction |
| `artifacts/` | Artefactos de pipeline: hypothesis, differential, quick_wins, attack_surface, evidence, execution, pipeline, roi, screenshot, ai_insights |
| `pipeline/` | Pipeline state machine: stages, state_machine, evidence_service, report_service |
| `notifications/` | Notificaciones: hub, push, email, fcm, bridges, db_bridge |
| `targets/` | Gestión de targets: filters, hunter, models, parser, technology |
| `target_auth/` | Autenticación a targets: identity_manager, idor_tester, login_service, session_manager, vault |
| `bounty_scraper/` | Scraping de programas desde plataformas |
| `health/` | Health checks: engine, scoring |
| `auth/` | Autenticación: auth, auth_manager, session, session_validator, token_service |
| `identity/` | Gestión de identidad: device_registry, identity_manager, session_store |
| `license/` | Licencias: hardware, store, validator |
| `sync/` | Sincronización multi-dispositivo: manager, mobile_sync |
| `settings/` | Configuración: service |
| `ws/` | WebSocket: bridge, manager |
| `tools/` | Tools abstraction: base, extra, httpx, nuclei, pipeline, subfinder |
| `env/` | Configuración de entorno tipada |
| `platform/` | Detección de SO y rutas |
| `knowledge/` | Gestión de conocimiento: graph, store, manager, models, parsers, pipeline, enrichers, etc. |
| `screenshot/` | Capturas de pantalla |
| `quick_wins/` | Quick wins engine |
| `financial/` | Financial Truth Layer: truth_layer (estado financiero + ValueCategory), sync_pipeline (rate limiter + retry + delta), withdrawal (tracking de retiros), reconciliation (discrepancia + auto-resolución), events (10 eventos financieros) |
| `orion/` | Context engine, next_action, opportunity_analyzer |
| `contracts/` | Contratos: base, normalizers, validator, wrapper |
| `attack/` | Motor de ataque |
| `predictor/` | Predicciones |
| `clustering/` | Clustering |
| `optimization/` | Optimización |
| `export/` | Exportación |
| `explainability/` | Explainabilidad: decision_trace, explanation_engine |
| `recovery/` | Recuperación: circuit_breaker, engine, healing_rules, health_monitor, persistence |
| `gateway/` | API Gateway: rate_limit, router, schemas, version |
| `web3/` | Integración Web3 |
| `diagnostics/` | Diagnósticos |
| `ux/` | UX info filter |
| `accountability/` | Accountability: outcome_tracker, system_scorecard |

## Comunicación entre componentes

```
Frontend (Vue 3 SPA)
    │
    │ HTTP/SSE (fetch + EventSource)
    ▼
API REST (FastAPI en puerto 8000)
    │
    ├──► Database (SQLAlchemy → SQLite/PostgreSQL)
    ├──► Scheduler (asyncio tasks)
    ├──► Event Bus (pub/sub interno)
    │       │
    │       ├──► Agent System (8 agentes vía IEventBus)
    │       ├──► Watchdog (monitoreo y recuperación)
    │       └──► CATEYE Agent (chat IA con tool calling)
    ├──► Recon Tools (subprocess a binarios Go/CLI)
    ├──► Identity Vault (AES-256-GCM encryptado)
    ├──► WebSocket Bridge (eventos en tiempo real)
    └──► Platform Integrations (API HTTP a HackerOne, Bugcrowd, etc.)

Desktop Layer (PyInstaller bundle)
    ├──► System Tray (pystray)
    ├──► Desktop Window (pywebview)
    ├──► Notifications OS (plyer)
    ├──► Watchdog (supervisor interno)
    └──► Auto-updater (GitHub Releases)
```

---

# 3. Herramientas Integradas

## Herramientas de Reconocimiento y Seguridad

| Nombre | Tipo | Propósito | Interna/Externa | Licencia | Gratuita/Paga | Estado |
|---|---|---|---|---|---|---|
| OWASP ZAP | Escáner | Escaneo de seguridad web (spider, passive, active) | Externa | Apache 2.0 | Gratuita | ✅ Integrada |
| Subfinder | Recon | Descubrimiento de subdominios | Externa | MIT | Gratuita | ✅ Integrada |
| Amass | Recon | Descubrimiento de subdominios (OSINT) | Externa | CC0 | Gratuita | ✅ Integrada |
| httpx | Recon | Sondeo HTTP (status, tecnologías) | Externa | MIT | Gratuita | ✅ Integrada |
| nuclei | Escáner | Escaneo de vulnerabilidades basado en templates | Externa | MIT | Gratuita | ✅ Integrada |
| ffuf | Fuzzing | Fuzzing de directorios/parámetros | Externa | MIT | Gratuita | ✅ Integrada |
| katana | Crawler | Crawling web y extracción de endpoints | Externa | MIT | Gratuita | ✅ Integrada |
| gau | Recon | Extracción de URLs (AlienVault/OTX/Wayback) | Externa | MIT | Gratuita | ✅ Integrada |
| waybackurls | Recon | URLs históricas de Wayback Machine | Externa | BSD-3 | Gratuita | ✅ Integrada |
| dnsx | Recon | Resolución DNS | Externa | MIT | Gratuita | ✅ Integrada |
| naabu | Recon | Escaneo de puertos | Externa | MIT | Gratuita | ✅ Integrada |
| assetfinder | Recon | Descubrimiento de assets | Externa | MIT | Gratuita | ✅ Integrada |
| whois | Recon | Consultas WHOIS | Externa | GPL | Gratuita | ✅ Integrada |
| crt.sh | Recon | Certificados SSL | Externa | — | Gratuita | ✅ Integrada |
| playwright | Automatización | Capturas de pantalla automatizadas | Externa | Apache 2.0 | Gratuita | ✅ Integrada |

## Stack de Desarrollo

| Nombre | Tipo | Propósito | Interna/Externa | Licencia | Gratuita/Paga | Estado |
|---|---|---|---|---|---|---|
| Python 3.10+ | Lenguaje | Lenguaje principal del backend | Externa | PSF | Gratuita | ✅ Crítico |
| FastAPI | Framework | Framework web API REST | Externa | MIT | Gratuita | ✅ Crítico |
| SQLAlchemy 2.0+ | ORM | ORM de base de datos | Externa | MIT | Gratuita | ✅ Crítico |
| Uvicorn | Servidor | Servidor ASGI | Externa | BSD-3 | Gratuita | ✅ Crítico |
| Pydantic | Validación | Validación de datos/schemas | Externa | MIT | Gratuita | ✅ Crítico |
| Vue 3 | Framework | Framework frontend SPA | Externa | MIT | Gratuita | ✅ Crítico |
| TypeScript | Lenguaje | Tipado frontend | Externa | Apache 2.0 | Gratuita | ✅ Crítico |
| Tailwind CSS 4 | CSS | Framework de estilos | Externa | MIT | Gratuita | ✅ Crítico |
| Vite 6 | Build | Build tool frontend | Externa | MIT | Gratuita | ✅ Crítico |
| Pinia | Estado | Estado global frontend | Externa | MIT | Gratuita | ✅ Crítico |
| Vue Router | Routing | Enrutamiento frontend | Externa | MIT | Gratuita | ✅ Crítico |
| Radix Vue / Reka UI | UI | Componentes headless accesibles | Externa | MIT | Gratuita | ✅ Integrada |
| Lucide Vue | Iconos | Iconos vectoriales | Externa | ISC | Gratuita | ✅ Integrada |
| Chart.js | Gráficos | Visualización de datos | Externa | MIT | Gratuita | ✅ Integrada |
| SQLite | BD | Base de datos embebida | Externa | — | Gratuita | ✅ Crítico |

## Desktop

| Nombre | Tipo | Propósito | Interna/Externa | Licencia | Gratuita/Paga | Estado |
|---|---|---|---|---|---|---|
| PyInstaller | Build | Empaquetado en ejecutable | Externa | GPL | Gratuita | ✅ Integrada |
| pywebview | UI | Ventana de escritorio nativa | Externa | BSD-3 | Gratuita | ✅ Integrada |
| pystray | Tray | Icono de bandeja del sistema | Externa | MIT | Gratuita | ✅ Integrada |
| plyer | Notificaciones | Notificaciones del SO | Externa | MIT | Gratuita | ✅ Integrada |
| pywin32 | Win32 | API de Windows (servicio) | Externa | PSF | Gratuita | ✅ Integrada |
| psutil | Monitor | Monitoreo de recursos del sistema | Externa | BSD-3 | Gratuita | ✅ Integrada |
| cryptography | Cripto | Cifrado AES-256-GCM | Externa | Apache 2.0 | Gratuita | ✅ Crítico |
| Pillow | Imágenes | Procesamiento de imágenes | Externa | Historical | Gratuita | ✅ Integrada |
| httpx | HTTP | Cliente HTTP asíncrono | Externa | BSD-3 | Gratuita | ✅ Crítico |

## Mobile

| Nombre | Tipo | Propósito | Interna/Externa | Licencia | Gratuita/Paga | Estado |
|---|---|---|---|---|---|---|
| Capacitor 8 | Framework | Aplicación móvil nativa | Externa | MIT | Gratuita | 🟡 Parcial |
| Android SDK | SDK | Build de APK | Externa | Apache 2.0 | Gratuita | 🟡 Parcial |

## IA

| Nombre | Tipo | Propósito | Interna/Externa | Licencia | Gratuita/Paga | Estado |
|---|---|---|---|---|---|---|
| Gemini API | IA | Proveedor principal de IA (recomendado) | Externa | — | Freemium | ✅ Integrada |
| Ollama | IA | Proveedor local de IA (offline) | Externa | MIT | Gratuita | ✅ Integrada |
| OpenAI API | IA | Proveedor cloud de IA (fallback) | Externa | — | Paga | ✅ Integrada |
| OpenRouter | IA | Proveedor cloud multi-modelo (fallback) | Externa | — | Paga | ✅ Integrada |

---

# 4. APIs

| Nombre | Uso | Método de autenticación | Endpoint principal | Documentación | Estado | Costo |
|---|---|---|---|---|---|---|
| **API REST propia** | Backend completo del sistema | Token-based (device_id + server session) | `http://127.0.0.1:8000/api/*` | Swagger `/docs` | ✅ Activa | N/A |
| **HackerOne API** | Sincronización y envío de reportes | API Key + Username | — | Externa | 🟡 Pendiente de verificar | Gratuita |
| **Bugcrowd API** | Sincronización y envío de reportes | API Key | — | Externa | 🟡 Pendiente de verificar | Gratuita |
| **Intigriti API** | Sincronización y envío de reportes | API Key | — | Externa | 🟡 Pendiente de verificar | Gratuita |
| **Synack API** | Sincronización y envío de reportes | API Key | — | Externa | 🟡 Pendiente de verificar | Gratuita |
| **YesWeHack API** | Sincronización y envío de reportes | API Key | — | Externa | 🟡 Pendiente de verificar | Gratuita |
| **Gemini API** | Proveedor de IA principal | API Key (`GEMINI_API_KEY`) | `https://generativelanguage.googleapis.com/v1beta/models/...` | [aistudio.google.com](https://aistudio.google.com/) | ✅ Activa | Freemium |
| **OpenAI API** | Proveedor de IA (fallback) | API Key (`OPENAI_API_KEY`) | `https://api.openai.com/v1` | [platform.openai.com](https://platform.openai.com/) | ✅ Activa | Paga |
| **OpenRouter API** | Proveedor de IA (fallback) | API Key (`OPENROUTER_API_KEY`) | `https://openrouter.ai/api/v1` | [openrouter.ai](https://openrouter.ai/) | ✅ Activa | Paga |
| **Ollama API** | Proveedor de IA local | Ninguna (localhost) | `http://localhost:11434` | [ollama.ai](https://ollama.ai/) | ✅ Activa | Gratuita |
| **GitHub Releases API** | Auto-update | Ninguna (público) | `https://api.github.com/repos/.../releases` | [docs.github.com](https://docs.github.com/) | ✅ Activa | Gratuita |

---

# 5. Agentes IA

## 5.1 Agente Principal: CATEYE Agent (`cores/ai/orion_agent.py`)

| Campo | Descripción |
|---|---|
| **Nombre** | CATEYE Agent |
| **Objetivo** | Copiloto de inteligencia para bug bounty. Responde con datos reales del sistema, nunca inventa cifras. |
| **Entradas** | Mensaje del usuario, historial de conversación opcional |
| **Salidas** | `{"response": str, "engine": "gemini"|"cloud"|"local"|"none"}` |
| **Prompt principal** | "Sos el copiloto de CATEYE, una plataforma de inteligencia para bug bounty. Respondés con datos reales del sistema, nunca inventás cifras de dinero ni de bounties. Si no sabés algo, usá las herramientas disponibles para consultarlo. Sé directo y breve, como un analista senior, no como un chatbot genérico. Respondé en el mismo idioma en que te pregunten." |
| **Herramientas** | `get_top_bounties`, `get_earnings_summary`, `get_report_status`, `get_target_details`, `web_search` |
| **Dependencias** | httpx, cores.ai.tools |
| **Proveedores (orden)** | 1. Gemini API → 2. OpenRouter → 3. Ollama local |
| **Nivel de autonomía** | Medio: responde consultas, ejecuta tools, pero no toma decisiones autónomas |

## 5.2 Sistema Multi-Agente (`cores/agents/`)

| Agente | ID | Objetivo | Entradas | Salidas | Dependencias |
|---|---|---|---|---|---|
| **Coordinator** | `coordinator` | Orquestar pipelines de principio a fin | Eventos del bus | Transiciones de pipeline | cores.pipeline.state_machine, database |
| **Research** | `research` | Descubrimiento de endpoints y subdominios | RESEARCH_START | RESEARCH_COMPLETED | cores.recon.* |
| **Validator** | `validator` | Validación de hallazgos | VALIDATION_REQUESTED | VALIDATION_COMPLETED | cores.validation.* |
| **Exploit** | `exploit` | Generación y ejecución de PoCs | EXPLOIT_REQUESTED | EXPLOIT_COMPLETED | cores.execution.* |
| **Documentation** | `documentation` | Generación de reportes | DOCUMENTATION_REQUESTED | DOCUMENTATION_COMPLETED | cores.reporting.* |
| **Strategy** | `strategy` | Recomendaciones estratégicas | Eventos del sistema | STRATEGY_RECOMMENDATION | cores.opportunity.* |
| **Memory** | `memory` | Almacenamiento y recuperación de patrones | MEMORY_STORE | MEMORY_LEARNED | cores.memory.* |
| **Financial** | `financial` | Tracking financiero y pagos | FINANCIAL_UPDATED | FINANCIAL_PAYOUT_RECORDED | cores.financial.* |

### Comunicación entre agentes

Todos los agentes se comunican exclusivamente a través del `IEventBus` (`cores/agents/bus.py`).
Nunca se llaman directamente. Los eventos son inmutables, serializables y trazables.

**Pipeline de 11 estados:** `PENDING → DISCOVERY → VALIDATION → EVIDENCE → AI_REVIEW → READY → SUBMITTED → TRIAGED → PAID → CLOSED | FAILED | CANCELLED`

---

# 6. Scripts

## Scripts de automatización (`scripts/`)

| Archivo | Ubicación | Propósito | Cuándo se ejecuta | Dependencias |
|---|---|---|---|---|
| `assemble_output.py` | `scripts/` | Ensambla la salida del build | Durante build/release | PyInstaller, shutil |
| `audit_imports.py` | `scripts/` | Auditoría de imports en el código | Manual (desarrollo) | ast |
| `autorelease.py` | `scripts/` | Automatización de releases | CI (release) | gh CLI, git |
| `bootstrap.py` | `scripts/` | Bootstrap inicial del proyecto | Instalación inicial | pip, npm |
| `build_android.py` | `scripts/` | Build de APK Android | `make build-android` | Capacitor, Gradle, Android SDK |
| `build_release.py` | `scripts/` | Orquestador de build de release | CI (release) | build_desktop.py |
| `gen_build_info.py` | `scripts/` | Genera metadata del build | Durante build | — |
| `generate_icon.py` | `scripts/` | Genera iconos del proyecto | Manual | Pillow |
| `generate_release_report.py` | `scripts/` | Genera reporte de release | Post-release | jinja2 |
| `generate_screenshots.py` | `scripts/` | Genera capturas para docs | Manual | playwright |
| `install.py` | `scripts/` | Instalación production (cross-platform) | `python run.py --install` | PyInstaller, npm |
| `install_windows.py` | `scripts/` | Instalación Windows + NSIS | `make install-windows` | PyInstaller, NSIS |
| `migrate_to_postgres.py` | `scripts/` | Migración de SQLite a PostgreSQL | Manual | sqlalchemy, psycopg2 |
| `package_portable.py` | `scripts/` | Empaquetado portable | Durante release | zipfile |
| `prebuild.py` | `scripts/` | Validación pre-build (8 fases) | `make prebuild` | ruff, mypy, pytest, npm |
| `real_world_validation.py` | `scripts/` | Validación con datos reales | Manual (QA) | — |
| `release.py` | `scripts/` | Script de release | Manual (release) | git, gh |
| `release_isolation.py` | `scripts/` | Aislamiento de release | CI | — |
| `seed.py` | `scripts/` | Seed de datos de prueba | `launcher/start.py --demo` | database |
| `seed_real.py` | `scripts/` | Seed con datos reales | Manual | database |
| `seed_v2.py` | `scripts/` | Seed v2 de datos | Manual | database |
| `smoke_test.py` | `scripts/` | Smoke test post-build | CI / post-build | httpx |
| `smoke_test_playwright.py` | `scripts/` | Smoke test con navegador | CI / post-build | playwright |
| `test_desktop_boot.py` | `scripts/` | Test de arranque desktop | CI | desktop.boot_guard |
| `test_installer.py` | `scripts/` | Test del instalador | CI | — |
| `test_portable.py` | `scripts/` | Test de versión portable | CI | — |
| `validate_assets.py` | `scripts/` | Validación de assets del build | CI / post-build | — |

## Scripts del launcher (`launcher/`)

| Archivo | Ubicación | Propósito | Cuándo se ejecuta | Dependencias |
|---|---|---|---|---|
| `start.py` | `launcher/` | Launcher multímodo (dev) | `python launcher/start.py` | uvicorn, psutil |

## Scripts de build (`desktop/build/`)

| Archivo | Ubicación | Propósito | Cuándo se ejecuta | Dependencias |
|---|---|---|---|---|
| `build_desktop.py` | `desktop/build/` | Build PyInstaller | `make build-desktop` | PyInstaller |
| `build_all.py` | `desktop/build/` | Build multiplataforma | Manual | build_desktop.py |
| `install_linux.sh` | `desktop/build/` | Instalación Linux | Manual | bash |
| `install_macos.sh` | `desktop/build/` | Instalación macOS | Manual | bash |
| `install_windows.ps1` | `desktop/build/` | Instalación Windows | Manual | PowerShell |

## Scripts de CI/CD (`.github/workflows/`)

| Archivo | Ubicación | Propósito | Cuándo se ejecuta | Dependencias |
|---|---|---|---|---|
| `test.yml` | `.github/workflows/` | Tests automáticos | Push a main/dev, PR a main | pytest, npm |
| `release.yml` | `.github/workflows/` | Build y release automático | Push de tag v* | PyInstaller, npm, gh |

---

# 7. Automatizaciones

| Proceso | Descripción | Frecuencia | Componente |
|---|---|---|---|
| **Descubrimiento** | Scrapeo de nuevas plataformas (HackerOne, Bugcrowd, etc.) | Cada 1 hora | `api/scheduler.py` → `cores/bounty_scraper/` |
| **Reconocimiento** | Subfinder, amass, httpx, katana, nuclei, gau, waybackurls | Cada 30 min | `api/scheduler.py` → `cores/recon/` |
| **Generación de hipótesis** | Hipótesis vía LLM + ZAP + análisis estático | Cada 15 min | `api/scheduler.py` → `cores/engine/hypothesis/` |
| **Verificación de alcance** | Validación de autorización antes de pruebas activas | Cada 1 hora | `api/scheduler.py` → `cores/scope_reader/` |
| **Validación** | Pruebas activas controladas en targets autorizados | Cada 2 horas | `api/scheduler.py` → `cores/validation/` |
| **Reportes** | Generación de drafts de reporte para hallazgos confirmados | Cada 1 hora | `api/scheduler.py` → `cores/reporting/` |
| **Cacería autónoma** | Pipeline completo 24/7 sin supervisión | Continua | `cores/autonomous/engine.py` |
| **Auto-update** | Verificación de nuevas versiones en GitHub | Al arrancar + periódico | `desktop/updater.py` |
| **Watchdog** | Monitoreo y recuperación de salud del sistema | Cada ~10s | `desktop/watchdog.py` |
| **Pre-build validation** | 8 fases de validación antes de build | Manual (`make prebuild`) | `scripts/prebuild.py` |
| **CI tests** | Tests automáticos en push/PR | Por evento git | `.github/workflows/test.yml` |
| **Release build** | Build + ZIP + GitHub Release | Por tag v* | `.github/workflows/release.yml` |
| **Sync multi-dispositivo** | Sincronización de sesión entre dispositivos | Manual (API) | `cores/sync/` |
| **Learning Loop** | Retroalimentación y mejora continua | Por evento | `cores/intelligence/learning_loop.py` |
| **Bounty Intel** | Inteligencia de programas bug bounty | Por evento | `cores/intelligence/bounty_intel.py` |

---

# 8. Dependencias

## Dependencias Python (de `requirements.txt` y `pyproject.toml`)

| Dependencia | Versión | Propósito | Crítica | Comentario |
|---|---|---|---|---|
| fastapi | >=0.95.0 | Framework API REST | ✅ Sí | |
| uvicorn[standard] | >=0.22.0 | Servidor ASGI | ✅ Sí | |
| sqlalchemy | >=2.0.0 | ORM | ✅ Sí | |
| pydantic | >=2.2.0 | Validación de datos | ✅ Sí | |
| httpx | >=0.24.0 | Cliente HTTP | ✅ Sí | |
| requests | >=2.31.0 | Cliente HTTP legacy | 🟡 Media | |
| python-dotenv | >=1.0.0 | Variables de entorno | ✅ Sí | |
| rich | >=13.0.0 | Output de terminal | ❌ No | |
| ollama | >=0.1.7 | Cliente Ollama | 🟡 Media | Solo si se usa Ollama |
| plotly | >=6.0.0 | Gráficos | 🟡 Media | |
| pandas | >=2.0.0 | Data processing | 🟡 Media | |
| jinja2 | >=3.0.0 | Templates HTML (reportes) | ✅ Sí | |
| cvss | >=3.0.0 | Cálculo de CVSS | 🟡 Media | |
| psutil | >=6.0.0 | Monitoreo de recursos | 🟡 Media | Watchdog |
| pywin32 | >=306 | API Windows (servicio) | 🟡 Media | Solo Windows |
| pywebview | >=6.0.0 | Ventana desktop nativa | 🟡 Media | Desktop mode |
| pystray | >=0.19.0 | Icono de bandeja | 🟡 Media | Desktop mode |
| plyer | >=2.1.0 | Notificaciones OS | 🟡 Media | Desktop mode |
| Pillow | >=10.0.0 | Procesamiento de imágenes | 🟡 Media | |
| psycopg2-binary | >=2.9.0 | Conexión PostgreSQL | 🟡 Media | Solo PostgreSQL |
| cryptography | >=41.0.0 | Cifrado (Identity Vault) | ✅ Sí | AES-256-GCM |
| playwright | >=1.40.0 | Automatización navegador | 🟡 Media | Screenshots |
| ruff | >=0.6.0 | Linter | ❌ No | Desarrollo |
| mypy | >=1.11.0 | Type checker | ❌ No | Desarrollo |
| pytest-cov | >=5.0.0 | Cobertura de tests | ❌ No | Desarrollo |
| PyInstaller | — | Empaquetado | 🟡 Media | Build |

## Dependencias Node/Frontend (de `frontend/package.json`)

| Dependencia | Versión | Propósito | Crítica |
|---|---|---|---|
| vue | ^3.5.13 | Framework SPA | ✅ Sí |
| vue-router | ^4.5.1 | Enrutamiento | ✅ Sí |
| pinia | ^3.0.4 | Estado global | ✅ Sí |
| @lucide/vue | ^1.22.0 | Iconos | 🟡 Media |
| @vueuse/core | ^14.3.0 | Composables utilitarios | 🟡 Media |
| chart.js | ^4.5.1 | Gráficos | 🟡 Media |
| vue-chartjs | ^5.3.3 | Integración Chart.js + Vue | 🟡 Media |
| radix-vue | ^1.9.17 | Componentes headless | 🟡 Media |
| reka-ui | ^2.2.0 | Componentes headless | 🟡 Media |
| class-variance-authority | ^0.7.1 | Variantes de clases | 🟡 Media |
| clsx | ^2.1.1 | Clases condicionales | 🟡 Media |
| tailwind-merge | ^3.2.0 | Merge de clases Tailwind | 🟡 Media |
| tailwindcss | ^4.1.6 | Framework CSS | ✅ Sí |
| vite | ^6.3.5 | Build tool | ✅ Sí |
| @vitejs/plugin-vue | ^5.2.4 | Plugin Vue para Vite | ✅ Sí |
| vue-tsc | ^2.2.4 | Type checker Vue | ❌ No |
| typescript | ~5.8.3 | Tipado | ❌ No |
| @tailwindcss/vite | ^4.1.6 | Plugin Tailwind para Vite | ✅ Sí |

## Dependencias Node/Global (de `package.json` raíz)

| Dependencia | Versión | Propósito | Crítica |
|---|---|---|---|
| @capacitor/core | ^8.4.0 | Framework mobile | 🟡 Media |
| @capacitor/android | ^8.4.0 | Plataforma Android | 🟡 Media |
| @capacitor/cli | ^8.4.0 | CLI Capacitor | 🟡 Media |
| typescript | ^6.0.3 | Tipado Capacitor | ❌ No |

## Dependencias del Sistema

| Dependencia | Propósito | SO | Crítica |
|---|---|---|---|
| libgtk-3-dev | pywebview (Linux) | Linux | 🟡 Media |
| libwebkit2gtk-4.1-dev | pywebview (Linux) | Linux | 🟡 Media |
| ANDROID_HOME | Build Android | Todos | 🟡 Media |
| Java 17+ | Build Android | Todos | 🟡 Media |
| Node.js 20 | Build frontend | Todos | ✅ Sí |
| npm | Build frontend | Todos | ✅ Sí |
| Python 3.10+ | Runtime | Todos | ✅ Sí |
| Go (opcional) | Instalación de tools de recon | Todos | 🟡 Media |

## Dependencias Opcionales

| Dependencia | Propósito | Alternativa |
|---|---|---|
| subfinder (Go) | Descubrimiento de subdominios | — |
| amass (Go) | Descubrimiento de subdominios | — |
| httpx (Go) | Sondeo HTTP | — |
| katana (Go) | Crawling web | — |
| nuclei (Go) | Escaneo de vulnerabilidades | — |
| ffuf (Go) | Fuzzing | — |
| gau (Go) | Extracción de URLs | — |
| waybackurls (Go) | URLs históricas | — |
| NSIS (Windows) | Instalador Windows | script/PS1 |
| Ollama | IA local | Gemini/OpenAI/OpenRouter |

---

# 9. Assets

## Frontend Assets

| Asset | Ubicación | Propósito |
|---|---|---|
| `index.html` | `frontend/` | Entry point HTML |
| `favicon.svg` | `frontend/public/` | Favicon |
| `icons.svg` | `frontend/public/` | Iconos SVG |
| `icon.png` | `frontend/public/` | Icono principal |
| `icon-192.png` | `frontend/public/` | PWA icon (192px) |
| `icon-512.png` | `frontend/public/` | PWA icon (512px) |
| `manifest.json` | `frontend/public/` | PWA manifest |
| `service-worker.js` | `frontend/public/` | Service worker |
| `dist/` | `frontend/dist/` | Build de producción (generado) |

## Desktop Assets

| Asset | Ubicación | Propósito |
|---|---|---|
| `orion.ico` | `installer/icons/` | Icono de aplicación Windows |
| `CATEYE.ico` | `desktop/build/icons/` | Icono alternativo |
| `CATEYE.png` | `desktop/build/icons/` | Icono PNG |

## Template Assets

| Asset | Ubicación | Propósito |
|---|---|---|
| `report.html` | `cores/reporting/templates/` | Template HTML para reportes |

## Documentación

| Asset | Ubicación | Propósito |
|---|---|---|
| `screenshots/*.png` | `docs/screenshots/` | Capturas para documentación |

## Configuraciones

| Archivo | Propósito |
|---|---|
| `pyproject.toml` | Configuración Python (ruff, mypy, pytest) |
| `.env.example` | Template de variables de entorno |
| `frontend/tsconfig.json` | Configuración TypeScript frontend |
| `frontend/vite.config.ts` | Configuración Vite |
| `frontend/components.json` | Configuración de componentes UI |
| `capacitor.config.json` | Configuración Capacitor mobile |
| `build/` | Build output directory |
| `scripts/cateye.service` | systemd service unit (Linux) |
| `scripts/com.cateye.service.plist` | launchd service plist (macOS) |
| `scripts/install_service.sh` | Unified service install/uninstall helper |
| `pyproject.toml` | Tool config (ruff, mypy, pytest) |
| `.github/workflows/*.yml` | Configuración CI/CD |
| `.githooks/pre-commit` | Hook pre-commit local |

---

# 10. Build

## PyInstaller (deprecated — see `scripts/build_release.py`)

- **Entry point:** `run.py`
- **Build script:** `scripts/build_release.py`
- **Output:** `build/` directory

## Build Pipeline

Build completo (producción):

```
1. python scripts/build_release.py
   (orquestra npm ci → npm run build → pyinstaller → assemble → ZIP)
```

Comandos Makefile:

| Comando | Propósito |
|---|---|
| `make build-desktop` | Build PyInstaller onedir |
| `make build-desktop-onefile` | Build PyInstaller onefile |
| `make install-windows` | Build + portable + ZIP |
| `make install-windows-full` | Build + NSIS installer |
| `make build-android` | Build APK debug |
| `make build-android-release` | Build APK release |
| `make prebuild` | Validación pre-build |
| `make lint` | Ruff linter |
| `make typecheck` | Mypy type checker |
| `make test` | Pytest con cobertura |
| `make clean` | Limpiar artifacts |

## CI Pipeline (GitHub Actions)

| Trigger | Workflow | Acciones |
|---|---|---|
| Push a main/dev, PR a main | `test.yml` | pip install → npm ci → npm build → pytest → verify imports |
| Push tag v* | `release.yml` | Build Windows + Linux → ZIP → GitHub Release |

## Validaciones Pre-build (`scripts/prebuild.py`)

| Fase | Check |
|---|---|
| 1 | Python dependencies (fastapi, uvicorn, sqlalchemy, etc.) |
| 2 | Recon tools (subfinder, katana, httpx) |
| 3 | Database connectivity |
| 4 | App import (API loads with routes) |
| 5 | Frontend build (npm run build) |
| 6 | Static analysis (ruff) |
| 7 | Type checking (mypy) |
| 8 | Test suite (pytest) |

## Smoke Tests

| Script | Propósito |
|---|---|
| `scripts/smoke_test.py` | Smoke test HTTP post-build |
| `scripts/smoke_test_playwright.py` | Smoke test con navegador |

## Validación de Assets (`scripts/validate_assets.py`)

- Verifica que el build contenga todos los archivos requeridos
- Checks: binary, frontend dist, docs, VERSION, CHANGELOG, LICENSE, plantillas
- Soporta modo CI con output JSON

---

# 11. Seguridad

## Variables de Entorno

| Variable | Propósito | Sensible |
|---|---|---|
| `CATEYE_AUTH_TOKEN` | Token de autenticación local | ✅ Sí |
| `CATEYE_AUTH_SECRET` | Secreto de autenticación (antes `RASTRO_AUTH_SECRET`) | ✅ Sí |
| `CATEYE_LICENSE_SECRET` | Secreto de licencia (antes `RASTRO_LICENSE_SECRET`) | ✅ Sí |
| `CATEYE_SMTP_HOST` | Host SMTP para notificaciones (antes `RASTRO_SMTP_HOST`) | ❌ No |
| `CATEYE_NOTIFICATION_EMAIL` | Email de notificaciones (antes `RASTRO_NOTIFICATION_EMAIL`) | ❌ No |
| `CATEYE_FCM_SERVER_KEY` | FCM server key (antes `RASTRO_FCM_SERVER_KEY`) | ✅ Sí |
| `CATEYE_FCM_PROJECT_ID` | FCM project ID (antes `RASTRO_FCM_PROJECT_ID`) | ❌ No |
| `CATEYE_OUTPUT_DIR` | Directorio de salida (antes `RASTRO_OUTPUT_DIR`) | ❌ No |
| `CATEYE_MEMORY_CONSUME` | Consumo de memoria (antes `RASTRO_MEMORY_CONSUME`) | ❌ No |
| `CATEYE_DATA_DIR` | Directorio de datos | ❌ No |
| `CATEYE_CONFIG_DIR` | Directorio de configuración | ❌ No |
| `GEMINI_API_KEY` | API Key de Google Gemini | ✅ Sí |
| `GEMINI_MODEL` | Modelo de Gemini | ❌ No |
| `OLLAMA_HOST` | Host de Ollama | ❌ No |
| `OLLAMA_MODEL` | Modelo de Ollama | ❌ No |
| `OPENAI_API_KEY` | API Key de OpenAI | ✅ Sí |
| `OPENAI_BASE_URL` | URL base de OpenAI | ❌ No |
| `OPENROUTER_API_KEY` | API Key de OpenRouter | ✅ Sí |
| `DATABASE_URL` | URL de conexión a BD | 🟡 Puede contener credenciales |
| `SCAN_INTERVAL` | Intervalo de escaneo | ❌ No |
| `HOST` | Host del servidor | ❌ No |
| `PORT` | Puerto del servidor | ❌ No |
| `DEBUG` | Modo debug | ❌ No |
| `LOG_LEVEL` | Nivel de log | ❌ No |
| `FRONTEND_DIR` | Directorio del frontend | ❌ No |
| `DISABLE_FRONTEND` | Deshabilitar frontend | ❌ No |
| `NO_BROWSER` | No abrir navegador | ❌ No |
| `BUILD_ENV` | Entorno de build | ❌ No |

> **Nota:** Las variables `RASTRO_*` legacy siguen siendo aceptadas con un `DeprecationWarning`. Se recomienda migrar a `CATEYE_*`.

## Manejo de Credenciales

- **Identity Vault:** `cores/identity_vault.py` — Bóveda encriptada con AES-256-GCM
- **Machine-derived key:** La clave de cifrado se deriva de `/etc/machine-id` + HOSTNAME
- **API Keys:** Se almacenan en variables de entorno (`.env`), NUNCA en el código
- **Credentials:** No se almacenan en texto plano, siempre en vault cifrado
- **Secrets nunca logueados:** Política explícita en el código de no loguear secrets

## Archivos Sensibles

| Archivo | Riesgo | Protección |
|---|---|---|
| `.env` | Contiene API keys | Incluido en `.gitignore` |
| `identity_vault.json` | Credenciales cifradas | Cifrado AES-256-GCM, en `~/.cateye/` |
| `*.db` (SQLite) | Datos completos | Protección por ACL del SO |
| `orion.ico` | Ninguno | Público |

## Permisos

- La aplicación corre en modo usuario, no requiere permisos de administrador
- El instalador NSIS instala en `Program Files` (requiere admin solo para instalación)
- El servicio Windows corre como `LocalSystem`
- No se exponen puertos a la red por defecto (bind a 127.0.0.1)

## Autenticación

- **Mecanismo:** Token-based (device_id + server session)
- **Sesión desktop:** Auto-autenticación con token generado localmente
- **Login manual:** Email + contraseña (vía `/api/auth/users/login`)
- **Registro:** Email + contraseña (vía `/api/auth/users/register`)
- **Auto-login:** Device ID para sesión persistente

---

# 12. Cobertura funcional

## Backend

| Funcionalidad | Estado | Módulo |
|---|---|---|
| API REST completa (50+ routers) | ✅ Completado | `api/` |
| Base de datos SQLite/PostgreSQL | ✅ Completado | `database/` |
| Proveedores de IA (Gemini, Ollama, OpenAI, OpenRouter) | ✅ Completado | `cores/ai/` |
| Agente Orion con tool calling | ✅ Completado | `cores/ai/orion_agent.py` |
| Chat asistente con streaming SSE | ✅ Completado | `api/routers/assistant.py` |
| Pipeline de hallazgos (11 estados) | ✅ Completado | `cores/pipeline/` |
| Sistema multi-agente (8 agentes) | ✅ Completado | `cores/agents/` |
| Bus de eventos interno | ✅ Completado | `cores/events/` |
| Escaneo con OWASP ZAP | ✅ Completado | `cores/recon/zap_runner.py` |
| Recon tools (subfinder, httpx, katana, etc.) | ✅ Completado | `cores/recon/` |
| Generación de hipótesis vía LLM | ✅ Completado | `cores/engine/hypothesis/` |
| Motor de validación (veredictos, confianza) | ✅ Completado | `cores/validation/` |
| Generación de reportes profesionales | ✅ Completado | `cores/reporting/` |
| Centro de reportes con submit | ✅ Completado | `api/routers/reports.py` |
| Cacería autónoma 24/7 | ✅ Completado | `cores/autonomous/` |
| Lector de alcance (scope_reader) | ✅ Completado | `cores/scope_reader/` |
| Bóveda de identidades encriptada | ✅ Completado | `cores/identity_vault.py` |
| Patrones aprendidos (memory) | ✅ Completado | `cores/memory/` |
| Timeline de eventos | ✅ Completado | `cores/timeline.py` |
| Sincronización multi-dispositivo | ✅ Completado | `cores/sync/` |
| Sistema de licencias | ✅ Completado | `cores/license/` |
| Scoring unificado (ORION Score, EVH) | ✅ Completado | `cores/engine/unified_scoring.py` |
| ROI Model | ✅ Completado | `cores/engine/roi_model.py` |
| Learning loop y reward learning | ✅ Completado | `cores/intelligence/` |
| Análisis diferencial | ✅ Completado | `cores/differential_intelligence/` |
| Quick wins engine | ✅ Completado | `cores/quick_wins/` |
| WebSocket bridge | ✅ Completado | `cores/ws/` |
| Identity center | ✅ Completado | `api/routers/identity_center.py` |
| Screenshot engine | ✅ Completado | `cores/screenshot/` |

## Frontend

| Funcionalidad | Estado | Ruta |
|---|---|---|
| Panel económico con KPIs | ✅ Completado | `/` |
| Money Radar (ranking de programas) | ✅ Completado | `/money-radar` |
| Radar de oportunidades | ✅ Completado | `/radar` |
| Pipeline de hallazgos | ✅ Completado | `/findings` |
| Centro de reportes | ✅ Completado | `/reports` |
| Cola priorizada de reportes | ✅ Completado | `/report-queue` |
| Configuración del sistema | ✅ Completado | `/settings` |
| Conexiones (plataformas + bancos) | ✅ Completado | `/connections` |
| Centro de agentes | ✅ Completado | `/agents` |
| Monitor de pipelines | ✅ Completado | `/pipelines` |
| Centro de evidencia | ✅ Completado | `/evidence` |
| Vista de historial | ✅ Completado | `/history` |
| Modo diario | ✅ Completado | `/daily` |
| Dashboard de inteligencia adaptativa | ✅ Completado | `/intelligence` |
| Superficie de ataque | ✅ Completado | `/attack-surface` |
| Patrones aprendidos | ✅ Completado | `/memory-patterns` |
| Hot paths / rutas críticas | ✅ Completado | `/hot-paths` |
| Centro de investigaciones | ✅ Completado | `/investigations` |
| Cola de hipótesis | ✅ Completado | `/hypotheses` |
| Motor diferencial | ✅ Completado | `/differential` |
| Insights del sistema | ✅ Completado | `/insights` |
| Billeteras | ✅ Completado | `/wallets` |
| Catálogo de programas | ✅ Completado | `/program-catalog` |
| Centro de reproducción | ✅ Completado | `/replay` |
| Centro de capturas | ✅ Completado | `/screenshots` |
| Dashboard de proyecto | ✅ Completado | `/project-dashboard` |
| Historial de reportes | ✅ Completado | `/report-history` |
| Inteligencia de programa | ✅ Completado | `/programs/:id` |
| Plan de cacería | ✅ Completado | `/programs/:id/plan` |
| Verificación manual | ✅ Completado | `/verify` |
| Detalle de target | ✅ Completado | `/targets/:id` |
| Detalle de endpoint | ✅ Completado | `/endpoints/:id` |
| Detalle de hallazgo | ✅ Completado | `/findings/:id` |
| Detalle de reporte | ✅ Completado | `/reports/:id` |
| Detalle de pipeline | ✅ Completado | `/pipelines/:id` |
| Panel de operaciones | ✅ Completado | `/operations` |
| Cola de tareas | ✅ Completado | `/tasks` |
| Perfil de aprendizaje | ✅ Completado | `/personal-intelligence` |
| Notificaciones | ✅ Completado | `/notifications` |
| Página de login | ✅ Completado | `/login` |
| Activación de licencia | ✅ Completado | `/activation` |

## Desktop

| Funcionalidad | Estado | Módulo |
|---|---|---|
| Launcher state machine | ✅ Completado | `run.py` |
| Modo browser (full stack) | ✅ Completado | `desktop/main_desktop.py` |
| Modo tray (system tray) | ✅ Completado | `desktop/tray.py` |
| Modo service (Windows service) | ✅ Completado | `desktop/service.py` |
| Modo safe mode (degradado) | ✅ Completado | `desktop/boot_guard.py` |
| Modo install (setup inicial) | ✅ Completado | `run.py` |
| Auto-update con rollback | ✅ Completado | `desktop/updater.py` |
| Watchdog interno | ✅ Completado | `desktop/watchdog.py` |
| Notificaciones del SO | ✅ Completado | `desktop/notifications.py` |
| Autostart | ✅ Completado | `desktop/autostart.py` |
| PyInstaller build | ✅ Completado | `Orion.spec` |
| NSIS installer | ✅ Completado | `installer/orion.nsi` |
| Ventana desktop nativa (pywebview) | ✅ Completado | `desktop/main_desktop.py` |

## Plataformas Bug Bounty

| Funcionalidad | Estado | Módulo |
|---|---|---|
| Integración HackerOne | ✅ Completado | `cores/platforms/hackerone.py` |
| Integración Bugcrowd | ✅ Completado | `cores/platforms/bugcrowd.py` |
| Integración Intigriti | ✅ Completado | `cores/platforms/intigriti.py` |
| Integración Synack | ✅ Completado | `cores/platforms/synack.py` |
| Integración YesWeHack | ✅ Completado | `cores/platforms/yeswehack.py` |
| Webhooks de plataformas | ✅ Completado | `api/routers/webhooks.py` |
| Bóveda de credenciales encriptada | ✅ Completado | `cores/identity_vault.py` |

## Mobile

| Funcionalidad | Estado | Módulo |
|---|---|---|
| Configuración Capacitor | 🟡 Parcial | `capacitor.config.json` |
| Android build script | 🟡 Parcial | `scripts/build_android.py` |
| Android project structure | 🟡 Parcial | `android/` |
| Mobile sync API | 🟡 Parcial | `api/routers/mobile.py`, `cores/sync/mobile_sync.py` |
| Push notifications (FCM) | 🟡 Parcial | `cores/notifications/fcm.py` |
| Aplicación móvil funcional | ❌ Pendiente | — |

## Testing

| Funcionalidad | Estado | Archivos |
|---|---|---|
| Tests de agentes | ✅ Completado | `tests/test_agents.py` |
| Tests de API endpoints | ✅ Completado | `tests/test_api_endpoints.py` |
| Tests de scoring | ✅ Completado | `tests/test_scoring.py` |
| Tests de seguridad | ✅ Completado | `tests/test_security.py` |
| Tests de tools | ✅ Completado | `tests/test_tools.py` |
| Tests de contratos | ✅ Completado | `tests/test_contracts.py` |
| Tests de learning loop | ✅ Completado | `tests/test_learning.py` |
| Tests de inteligencia | 🟡 Parcial | `tests/test_intelligence_loop.py` |
| Tests E2E flow | 🟡 Parcial | `tests/test_e2e_flow.py` |
| Tests de pipeline E2E | 🟡 Parcial | `tests/test_pipeline_e2e.py` |
| Tests de scheduler | 🟡 Parcial | `tests/test_scheduler.py` |
| Tests de desktop release | 🟡 Parcial | `tests/test_desktop_release.py` |
| Tests de auth_users | 🟡 Parcial | `tests/test_auth_users.py` |
| Tests de nuevas integraciones | 🟡 Parcial | `tests/test_new_integrations.py` |
| Tests unitarios frontend | ❌ Pendiente | — |
| Smoke tests (HTTP) | ✅ Completado | `scripts/smoke_test.py` |
| Smoke tests (Playwright) | ✅ Completado | `scripts/smoke_test_playwright.py` |

---

# 13. Roadmap técnico

## Próximas mejoras (corto plazo)

| Prioridad | Item | Esfuerzo estimado |
|---|---|---|
| 1 | Páginas de detalle (target/:id, finding/:id, report/:id) — conectar todas las vistas | 2-3 días |
| 2 | Skeleton loading states globales y error handling en frontend | 1 día |
| 3 | Tests unitarios frontend (Vitest + Vue Test Utils) | 3-4 días |
| 4 | Responsive design + PWA completa | 2-3 días |
| 5 | Workflow humano completo: scope → hipótesis → validación → reporte | — |

## Deuda técnica

| Item | Área | Impacto |
|---|---|---|
| Módulos con imports no auditados | Varios | Medio |
| Falta de migraciones de BD formales (Alembic) | Database | Medio |
| Cobertura de tests insuficiente (~40%) | Tests | Alto |
| Archivo `AGENT_CONTEXT.md` en `cores/` sin uso claro | Docs | Bajo |
| Algunos módulos en `cores/` sin `__init__.py` | Core | Bajo |
| Error "`_log` is not callable" en `cores/fallback.py` en ciertos imports | Core | Medio |
| ~~`desktop/build/Rastro.spec` desactualizado vs `Orion.spec`~~ | Build | Resuelto — specs eliminados |
| Directorio `targets/Airbyte/` con archivos de ejecución (subdominios) que no deberían estar en VCS | Repo | Bajo |
| `logs/` con datos de ejecución en VCS | Repo | Bajo |
| `archive_cleanup/` con DB antigua en VCS | Repo | Bajo |

## Refactors planificados

| Item | Motivo |
|---|---|
| Unificar `EnvConfig` (`cores/env/config.py`) y `RastroConfig` (`cores/config.py`) | Dos sistemas de configuración paralelos |
| Migrar a sistema de migraciones formal (Alembic) | Control de esquema de BD |
| Separar frontend en micro-frontends o lazy loading | Performance |
| Estandarizar manejo de errores en API | Consistencia |

## Ideas futuras

| Idea | Área |
|---|---|
| Soporte para más plataformas bug bounty | Plataformas |
| Dashboard PWA instalable offline | Frontend |
| Reportes exportables a PDF más ricos | Reporting |
| Plugin system para herramientas externas | Arquitectura |
| Integración con Slack / Discord para notificaciones | Notificaciones |
| Auto-triage de hallazgos duplicados | Inteligencia |
| Modelo de predicción de severidad | IA |
| Integración con shodan.io, censys.io | Recon |
| Motor de búsqueda semántico sobre hallazgos | Knowledge |

---

# 14. Integraciones futuras

| Herramienta/Motor | Tipo | Propósito | Estado |
|---|---|---|---|
| **Tauri** | Desktop | Alternativa a PyInstaller + pywebview (Rust-based) | 🔜 Futuro |
| **Alembic** | DB | Migraciones de base de datos formales | 🔜 Planificado |
| **Slack / Discord webhooks** | Notificaciones | Alertas en tiempo real | 🔜 Idea |
| **Shodan.io API** | Recon | Descubrimiento de activos expuestos | 🔜 Idea |
| **Censys.io API** | Recon | Superficie de ataque externa | 🔜 Idea |
| **Copilot (autocompletado)** | IA | Asistencia contextual en hallazgos | 🔜 Idea |
| **Modelos locales adicionales** | IA | Más opciones de LLM local | 🔜 Idea |
| **Nuevos escáneres (Dalfox, sqlmap)** | Security | Escaneo de XSS, SQLi | 🟡 Parcial |
| **GitHub Advisory Database** | Security | Correlación de CVEs | 🔜 Idea |
| **Mobile app (Capacitor/Tauri)** | Mobile | Aplicación móvil nativa | 🔜 Futuro |
| **Docker deployment** | DevOps | Contenedor Docker | 🔜 Idea |
| **Kubernetes helm chart** | DevOps | Orquestación cloud | 🔜 Idea |

---

# 15. Auditoría

## Módulos sin usar

| Módulo | Archivo | Evidencia |
|---|---|---|
| `cores/targets/hunter.py` | `cores/targets/` | 🟡 Pendiente de verificar si tiene uso activo |
| `cores/tools/` | `cores/tools/` | Puede ser duplicado de `cores/recon/tools.py` |
| `scripts/seed_v2.py` | `scripts/` | Puede ser redundante con `seed.py` y `seed_real.py` |
| `scripts/autorelease.py` | `scripts/` | Pendiente de verificar si se usa (vs release.yml CI) |
| `scripts/release.py` | `scripts/` | Pendiente de verificar si se usa manualmente |
| `scripts/release_isolation.py` | `scripts/` | Pendiente de verificar |
| `launcher/start.py` | `launcher/` | Puede estar obsoleto vs `run.py` (modo dev) |

## Dependencias huérfanas

| Dependencia | Archivo | Problema potencial |
|---|---|---|
| `streamlit` (comentada) | `requirements.txt` | Eliminada pero referenciada en docstring de `launcher/start.py` |
| `taipy` (comentada) | `requirements.txt` | Eliminada, referencias no verificadas |
| `plotly` | `requirements.txt` | Puede que no se use directamente (usado por `pandas/chart.js`) — 🟡 Verificar |
| `matplotlib` | Excluida en `Orion.spec` | Excluida del build, verificar que no se importa en runtime |

## Scripts duplicados

| Grupo | Archivos | Nota |
|---|---|---|
| Spec PyInstaller | ~~`Orion.spec` vs `desktop/build/Rastro.spec`~~ | Resuelto — ambos specs eliminados, build vía `scripts/build_release.py` |
| Seed data | `scripts/seed.py`, `scripts/seed_real.py`, `scripts/seed_v2.py` | Posible consolidación |
| Smoke test | `scripts/smoke_test.py`, `scripts/smoke_test_playwright.py` | Complementarios (HTTP + browser) |

## Configuraciones inconsistentes

| Inconsistencia | Detalle |
|---|---|
| `EnvConfig` vs `RastroConfig` | Dos sistemas de configuración (`cores/env/config.py` y `cores/config.py`) con diferente estructura |
| Paths de core | `SYSTEM.md` refiere `cores/` pero algunos imports usan `core_engines.*` y `core.*` |
| Nombre del proyecto | CATEYE (formerly ORION/Rastro) — `RastroConfig` eliminado, código migrado a `CATEYEConfig` |

## Assets faltantes

| Asset | Verificación |
|---|---|
| `installer/icons/orion.ico` | ✅ Existe |
| `frontend/public/favicon.svg` | ✅ Existe |
| `frontend/public/manifest.json` | ✅ Existe |
| `frontend/public/service-worker.js` | ✅ Existe |
| `frontend/public/icon.png` | ✅ Existe |
| `frontend/public/icon-192.png` | ✅ Existe |
| `frontend/public/icon-512.png` | ✅ Existe |
| `desktop/build/icons/CATEYE.ico` | ✅ Existe |
| `desktop/build/icons/CATEYE.png` | ✅ Existe |
| `frontend/dist/` | ❌ No existe (generado por build) |
| `installer/uninstall_windows.ps1` | ✅ Existe |
| `VERSION` | ✅ Existe |

## Rutas rotas

| Ruta | Archivo | Problema |
|---|---|---|
| ~~`core.env.config`~~ | ~~`desktop/build/Rastro.spec`~~ | Resuelto — spec eliminado |
| ~~`core.platform`~~ | ~~`desktop/build/Rastro.spec`~~ | Resuelto — spec eliminado |
| ~~`desktop/service_util`~~ | ~~`Orion.spec`~~ | Resuelto — spec eliminado |

## Código muerto detectado

| Archivo | Problema |
|---|---|
| `cores/tools/base.py` | Posible duplicado de `cores/recon/tools.py` |
| ~~`desktop/build/Rastro.spec`~~ | Resuelto — specs eliminados, build vía `scripts/build_release.py` |
| `targets/Airbyte/` | Directorio con datos de ejecución, no debería estar en VCS |
| `logs/cateye.log` | Archivos de log en VCS |
| `logs/CATEYE.log` | Archivos de log en VCS |
| `logs/lifecycle.log` | Archivos de log en VCS |
| `archive_cleanup/cateye_20260630.db` | Base de datos antigua en VCS |

## APIs no utilizadas

| API/Endpoint | Archivo | Situación |
|---|---|---|
| Webhook endpoints por plataforma | `api/routers/webhooks.py` | 🟡 Implementado pero depende de configuración externa |
| Mobile sync | `api/routers/mobile.py` | 🟡 Parcial hasta que la app móvil esté completa |
| FCM push notifications | `cores/notifications/fcm.py` | 🟡 Depende de configuración de Firebase |

---

> **Última actualización:** 2026-07-02
> **Próxima revisión programada:** Al próximo cambio significativo en el códigobase.
> **Mantenido por:** SYSTEM_INVENTORY.md es generado automáticamente; actualizar secciones afectadas al modificar componentes.
