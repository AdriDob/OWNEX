<!-- markdownlint-disable MD041 -->

# CATEYE — Sistema de Inteligencia para Bug Bounty Automático

> **Versión:** 1.7.0
> **Arquitectura:** Monolito modular con frontend SPA
> **Backend:** Python + FastAPI + SQLAlchemy + SQLite/PostgreSQL
> **Frontend:** Vue 3 + TypeScript + Tailwind CSS v4 + Vite

---

## Índice

1. [Visión General](#1-visión-general)
2. [Estructura del Proyecto](#2-estructura-del-proyecto)
3. [Backend — `cores/`](#3-backend---cores)
4. [Frontend — `frontend/`](#4-frontend---frontend)
5. [API REST](#5-api-rest)
6. [Modelos de Datos](#6-modelos-de-datos)
7. [Ciclo de Bug Bounty Automático](#7-ciclo-de-bug-bounty-automático)
8. [IA y Modelos de Lenguaje](#8-ia-y-modelos-de-lenguaje)
9. [Sincronización y Plataformas](#9-sincronización-y-plataformas)
10. [Seguridad](#10-seguridad)
11. [Despliegue](#11-despliegue)
12. [Evolución y Roadmap](#12-evolución-y-roadmap)

---

## 1. Visión General

CATEYE es un sistema de inteligencia artificial diseñado para automatizar el ciclo completo de bug bounty: desde el descubrimiento de programas y análisis de alcance, hasta la generación de reportes profesionales y su envío a plataformas como HackerOne, Bugcrowd, Intigriti y Synack.

### Principios de diseño

- **Automatización progresiva**: el sistema opera en segundo plano pero siempre permite intervención humana.
- **Inteligencia económica**: cada decisión está respaldada por un modelo de ROI (EVH, ORION Score).
- **Privacidad primero**: los datos y credenciales se almacenan encriptados localmente.
- **Degradación elegante**: si un componente falla, el resto del sistema sigue funcionando.
- **Observabilidad total**: todo evento es registrado y visible en la línea de tiempo.

---

## 2. Estructura del Proyecto

```
Rastro/
├── SYSTEM.md                  ← Este documento
├── run.py                     ← Launcher state machine (modos: browser, tray, service, safe-mode)
├── .env                       ← Variables de entorno (OLLAMA_HOST, API keys, etc.)
│
├── cores/                     ← Núcleo del sistema (ex core/ + core_engines/)
│   ├── __init__.py             ← Re-exporta componentes principales
│   ├── config.py               ← Configuración centralizada
│   ├── env/config.py           ← EnvConfig: variables de entorno tipadas
│   ├── platform/system.py      ← Detección de SO, rutas de datos, directorios
│   ├── identity_vault.py       ← Bóveda encriptada de credenciales
│   ├── timeline.py             ← Motor de línea de tiempo histórica
│   ├── system_state.py         ← Estado global del sistema
│   │
│   ├── ai/                     ← Proveedores de IA
│   │   ├── provider.py         ← Catálogo de proveedores: Ollama, OpenAI, OpenRouter
│   │   ├── orion_agent.py      ← Agente principal con tool calling
│   │   ├── tools.py            ← Herramientas del agente
│   │   ├── context/engine.py   ← Contexto unificado de CATEYE
│   │   ├── advisor.py          ← Asesor de decisiones
│   │   ├── assistant.py        ← Chat asistente
│   │   └── ...
│   │
│   ├── recon/                  ← Reconocimiento y herramientas externas
│   │   ├── zap_runner.py       ← Wrapper de OWASP ZAP
│   │   └── parser.py           ← Parseo de resultados
│   │
│   ├── engine/                 ← Motores de inteligencia
│   │   ├── hypothesis/         ← Generación de hipótesis (LLM + ZAP)
│   │   ├── unified_scoring.py  ← Sistema de puntuación unificado
│   │   └── roi_model.py        ← Modelo de retorno de inversión
│   │
│   ├── intelligence/           ← Inteligencia central
│   │   ├── engine.py           ← Orquestador de inteligencia
│   │   ├── learning_loop.py    ← Bucle de aprendizaje continuo
│   │   ├── reward_learning.py  ← Aprendizaje de recompensas
│   │   ├── adaptive_memory.py  ← Memoria adaptativa
│   │   └── bounty_intel.py     ← Inteligencia de programas bug bounty
│   │
│   ├── scope_reader/           ← Lector de alcance de programas
│   │   └── __init__.py         ← Download, extract, hash, detectar cambios
│   │
│   ├── orchestrator/           ← Orquestación de pipelines de cacería
│   │   ├── pipeline.py         ← Pipeline de ejecución
│   │   ├── assistant_orchestrator.py
│   │   └── scan_service.py     ← Servicio de escaneos y persistencia de endpoints
│   │
│   ├── autonomous/             ← Cacería autónoma
│   │   └── engine.py           ← Motor autónomo 24/7
│   │
│   ├── bounty_scraper/         ← Scraping de plataformas
│   ├── platforms/              ← Integración con plataformas
│   │   ├── hackerone.py
│   │   ├── bugcrowd.py
│   │   ├── intigriti.py
│   │   ├── synack.py
│   │   └── yeswehack.py
│   │
│   ├── opportunity/            ← Detección de oportunidades
│   ├── reporting/              ← Generación de reportes
│   ├── validation/             ← Motor de validación
│   ├── execution/              ← Ejecución de exploits/PoC
│   ├── evidence/               ← Gestión de evidencia
│   ├── artifacts/              ← Artefactos de pipeline
│   ├── memory/                 ← Memoria a largo plazo
│   ├── tracking/               ← Tracking de envíos y pagos
│   ├── learning/               ← Enrutamiento de aprendizaje
│   ├── agents/                 ← Sistema de agentes
│   ├── events/event_bus.py     ← Bus de eventos interno
│   ├── ws/bridge.py            ← WebSocket bridge
│   └── ...
│
├── api/                        ← API REST (FastAPI)
│   ├── main.py                 ← Punto de entrada de FastAPI
│   ├── scheduler.py            ← Tareas programadas
│   └── routers/                ← Routers por dominio
│       ├── economic.py         ← Inteligencia económica
│       ├── orion.py            ← Contexto y estado
│       ├── reports.py          ← CRUD de reportes + submit
│       ├── targets.py          ← Programas/objetivos
│       ├── findings.py         ← Hallazgos
│       ├── zap.py              ← Integración ZAP
│       ├── auth.py             ← Autenticación
│       ├── license.py          ← Licencias
│       ├── sync.py             ← Sincronización multi-dispositivo
│       ├── webhooks.py         ← Webhooks de plataformas
│       ├── opportunity_intelligence.py ← Identidades y cuentas
│       └── ... (40+ routers total)
│
├── database/                   ← Modelos y migraciones
│   ├── models.py               ← Modelos SQLAlchemy principales
│   └── models_economic.py      ← Modelos financieros y de programas
│
├── desktop/                    ← Aplicación de escritorio (PyInstaller)
│   ├── main_desktop.py         ← Punto de entrada desktop
│   ├── boot_guard.py           ← Guardián de arranque seguro
│   ├── service.py              ← Windows service
│   └── ...
│
├── frontend/                   ← SPA (Vue 3 + TypeScript)
│   └── src/
│       ├── router/index.ts     ← Enrutamiento con guardia global de auth
│       ├── lib/api.ts          ← Cliente HTTP + gestión de token y sesión
│       ├── types/index.ts      ← Interfaces TypeScript
│       ├── stores/             ← Pinia stores
│       ├── composables/        ← Composables (WebSocket, scan helpers)
│       ├── pages/              ← Páginas del dashboard
│       └── components/         ← UI components
│
├── launcher/start.py           ← Launcher unificado
├── scripts/                    ← Scripts de utilidad
└── tests/                      ← Tests
```

---

## 3. Backend — `cores/`

### 3.1 Arquitectura

`cores/` es el corazón del sistema. Es un paquete Python monolítico organizado por dominios. No hay separación física entre "core" y "core_engines" — todo vive aquí para simplificar imports y evitar dependencias circulares.

### 3.2 Módulos Principales

| Módulo | Responsabilidad |
|---|---|
| `ai/` | Proveedores de IA (Gemini, Ollama, OpenAI, OpenRouter), agente CATEYE con tool calling, contexto unificado |
| `recon/` | OWASP ZAP wrapper, parsing de resultados |
| `engine/hypothesis/` | Generación de hipótesis de vulnerabilidades vía LLM + ZAP + análisis estático |
| `intelligence/` | Bucle de inteligencia, aprendizaje por refuerzo, memoria adaptativa |
| `scope_reader/` | Descarga y parseo de documentos de alcance de programas |
| `orchestrator/` | Orquestación de pipelines de cacería, incluido el servicio de escaneo |
| `autonomous/` | Cacería autónoma 24/7 sin supervisión |
| `opportunity/` | Scoring de oportunidades, EVH, priorización |
| `platforms/` | Integración con HackerOne, Bugcrowd, Intigriti, Synack, YesWeHack |
| `bounty_scraper/` | Scraping de programas desde plataformas |
| `reporting/` | Generación de reportes profesionales |
| `validation/` | Motor de validación y veredictos |
| `evidence/` | Gestión de evidencia técnica |
| `artifacts/` | Artefactos del pipeline (hypothesis, differential, quick_wins, etc.) |
| `tracking/` | Tracking de envíos, estados de reportes y pagos |
| `memory/` | Memoria a largo plazo y archivo de insights |
| `events/` | Bus de eventos interno (pub/sub) |
| `timeline.py` | Motor de línea de tiempo histórica |
| `identity_vault.py` | Bóveda encriptada de credenciales de plataformas |
| `env/config.py` | Configuración de entorno tipada |

### 3.3 Configuración (`.env`)

```env
# Proveedor de IA (ollama | openai | openrouter)
AI_PROVIDER=ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen2.5-coder:7b-instruct-q4_K_M

# OpenAI (fallback)
OPENAI_API_KEY=sk-...
LLM_MODEL=gpt-4o-mini

# OpenRouter (fallback remoto)
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_MODEL=openai/gpt-4o-mini

# Base de datos
DATABASE_URL=sqlite:///.orion/database/orion.db

# Escáner
SCAN_TIMEOUT=600
```

---

## 4. Frontend — `frontend/`

### 4.1 Stack

| Tecnología | Versión | Uso |
|---|---|---|
| Vue 3 | 3.5+ | Framework SPA |
| TypeScript | 5.8+ | Tipado |
| Tailwind CSS | 4.1+ | Estilos utilitarios |
| Vite | 6.3+ | Build tool |
| Vue Router | 4.5+ | Enrutamiento |
| Pinia | 3.0+ | Estado global |
| Lucide Vue | 1.22+ | Iconos |
| Radix Vue / Reka UI | 2.x | Componentes headless accesibles |
| VueUse | 14.x | Composables utilitarios |

### 4.2 Rutas

| Ruta | Página | Descripción |
|---|---|---|
| `/mission-control` | MissionControl | Control de Misión (home principal) |
| `/money-radar` | MoneyRadar | Programas rankeados por ORION Score |
| `/radar` | OpportunityRadar | Radar de oportunidades |
| `/hot-paths` | HotPaths | Rutas críticas de ataque |
| `/findings` | Findings | Pipeline de hallazgos |
| `/reports` | ReportCenter | Centro de reportes |
| `/report-queue` | ReportQueue | Cola priorizada de reportes |
| `/memory-patterns` | MemoryPatterns | Patrones aprendidos |
| `/programs/:id` | ProgramIntel | Inteligencia de programa individual |
| `/programs/:id/plan` | OpportunityPlanner | Plan de cacería |
| `/bounties` | Bounties | Bounties activos |
| `/investigations` | InvestigationCenter | Centro de investigaciones |
| `/verify` | VerificationGuide | Guía de validación manual |
| `/settings` | Settings | Configuración del sistema |
| `/connections` | Connections | Conexiones con plataformas y bancos |

### 4.3 Sidebar

La barra lateral muestra:
- Logo CATEYE + estado de la cacería (idle/running/paused)
- Balance total (cobrado + pendiente)
- Estado de conexión de plataformas (HackerOne, Bugcrowd, Intigriti, Synack)
- Cuenta bancaria vinculada
- Navegación por secciones (Inteligencia, Operaciones, Sistema) — **13 items** (podado de 36 originales tras auditoría UX)
- Botón Copiloto (panel de chat IA, atajo `⌘B`)
- Atajo `⌘K` para Command Palette

### 4.4 API Layer

El frontend se comunica con el backend a través de `frontend/src/lib/api.ts`, que expone:
- Cliente HTTP con autenticación automática (token en sessionStorage)
- 50+ funciones tipadas para todos los endpoints
- Soporte de SSE streaming para chat
- Manejo de errores con degradación (ApiError)
- Tracker de loading global

---

## 5. API REST

La API se sirve en `http://127.0.0.1:8000/api/*` con los siguientes grupos:

| Prefix | Tags | Descripción |
|---|---|---|
| `/api/economic` | economic | Programas, money-radar, ROI, financial-summary, patterns, report-queue |
| `/api/orion` | orion | Contexto del sistema, next-action |
| `/api/targets` | targets | CRUD de programas/objetivos |
| `/api/findings` | findings | Hallazgos y pipeline |
| `/api/reports` | reports | Reportes, submit, export, versions, reward-learning |
| `/api/pipeline` | pipeline | Etapas del pipeline |
| `/api/attack` | attack | Decisiones de ataque (hot paths) |
| `/api/verdicts` | verdicts | Veredictos de validación |
| `/api/evidence` | evidence | Subida de evidencia |
| `/api/zap` | zap | Integración OWASP ZAP |
| `/api/hunt` | hunt | Control de cacería autónoma |
| `/api/assistant` | assistant | Chat con IA (stream + no-stream) |
| `/api/validation` | validation | Registro de validaciones |
| `/api/auth` | auth | Autenticación |
| `/api/license` | license | Licencias |
| `/api/system` | system | Timeline, replay, confidence, review, health |
| `/api/sync` | sync | Sincronización multi-dispositivo |
| `/api/webhooks` | webhooks | Webhooks de plataformas externas |
| `/api/opportunity_intelligence` | opportunity | Identidades, categorías, histórico |
| `/api/connections` | connections | Gestión de cuentas de plataformas y bancos |
| `/api/overview` | overview | Resumen del sistema |
| 30+ routers más | — | Funcionalidades específicas |

---

## 6. Modelos de Datos

### 6.1 Base de datos principal (`database/models.py`)

- **Target** — Programas/objetivos de bug bounty
- **Endpoint** — Endpoints/URLs descubiertos
- **Finding** — Hallazgos de vulnerabilidades
- **Verdict** — Veredictos de validación
- **Report** — Reportes generados
- **SubmissionRecord** — Historial de envíos a plataformas
- **Evidence** — Evidencia técnica (requests, responses, screenshots)
- **ScanRun** — Ejecuciones de escaneo
- **PipelineState** — Estado del pipeline
- **AIProviderConfig** — Configuración persistente del proveedor IA
- 30+ modelos más

### 6.2 Modelos económicos (`database/models_economic.py`)

- **Program** — Programas con score, EVH, tecnologías, prioridad
- **BountyTier** — Escalones de recompensa por programa
- **ScopeDocument** — Documentos de alcance parseados
- **ProgramIntel** — Inteligencia generada por IA por programa
- **MemoryPattern** — Patrones aprendidos
- **ReportPriority** — Priorización de reportes

---

## 7. Ciclo de Bug Bounty Automático

```
                    ┌─────────────────┐
                    │  DISCOVERY       │
                    │  (scraper + API) │
                    └────────┬────────┘
                             ▼
                    ┌─────────────────┐
                    │  SCOPE ANALYSIS  │
                    │  (scope_reader)  │
                    └────────┬────────┘
                             ▼
                    ┌─────────────────┐
              ┌────►│  RECONNAISSANCE  │◄────┐
              │     │  (ZAP + parser)  │     │
              │     └────────┬────────┘     │
              │              ▼              │
              │     ┌─────────────────┐     │
              │     │  HYPOTHESIS      │     │
              │     │  (LLM + engine)  │     │
              │     └────────┬────────┘     │
              │              ▼              │
              │     ┌─────────────────┐     │
              │     │  VALIDATION      │     │ (loop: más
              │     │  (manual + auto) │     │  hipótesis,
              │     └────────┬────────┘     │  más reco)
              │              ▼              │
              │     ┌─────────────────┐     │
              │     │  FINDING CONFIRM │     │
              │     │  (pipeline)      │     │
              │     └────────┬────────┘     │
              │              ▼              │
              │     ┌─────────────────┐     │
              │     │  REPORT DRAFT    │     │
              │     │  (automático)    │     │
              │     └────────┬────────┘     │
              │              ▼              │
              │     ┌─────────────────┐     │
              │     │  HUMAN REVIEW    │     │
              │     │  (aprobación)    │     │
              │     └────────┬────────┘     │
              │              ▼              │
              │     ┌─────────────────┐     │
              │     │  SUBMISSION      │     │
              │     │  (vía API key)   │     │
              │     └────────┬────────┘     │
              │              ▼              │
              │     ┌─────────────────┐     │
              │     │  PAYMENT TRACK   │     │
              │     │  (webhooks +     │     │
              │     │   manual)        │     │
              │     └────────┬────────┘     │
              │              ▼              │
              │     ┌─────────────────┐     │
              │     │  LEARNING LOOP   │────┘
              │     │  (patterns)      │
              │     └─────────────────┘
              │
              └────── Feedback loop ──────┘
```

### 7.1 Discovery

El sistema descubre programas automáticamente mediante:
- **Scraping**: `cores/bounty_scraper/` extrae programas de HackerOne, Bugcrowd, etc.
- **API**: `POST /api/targets` permite agregar targets manualmente
- **Plataformas**: integración directa vía API keys

### 7.2 Scope Analysis

`POST /api/economic/programs/{id}/read-scope` ejecuta el pipeline:
1. **Download**: fetch del URL del programa
2. **Extract**: HTML → texto, PDF → texto
3. **Hash**: fingerprint para detección de cambios
4. **Diff**: comparación contra versión anterior
5. **LLM Summary**: resumen del alcance generado por IA
6. **Asset Extraction**: tecnologías, endpoints, dominios

### 7.3 Autonomous Hunting

El motor autónomo (`cores/autonomous/engine.py`) puede operar 24/7:
- Escanea targets en orden de prioridad (ORION Score)
- Genera hipótesis automáticamente
- Valida hallazgos con ZAP + heurísticas
- Mueve hallazgos por el pipeline
- Genera drafts de reporte

Control vía API:
- `POST /api/hunt/start`, `/pause`, `/resume`, `/stop`
- `GET /api/hunt/status`

---

## 8. IA y Modelos de Lenguaje

### 8.1 Proveedores Soportados

| Proveedor | Tipo | Modelo por defecto | Variable de entorno |
|---|---|---|---|
| **Ollama** | Local | `qwen3:14b` | `OLLAMA_MODEL` |
| **OpenAI** | Nube | `gpt-4o-mini` | `LLM_MODEL` |
| **OpenRouter** | Nube | `openai/gpt-4o-mini` | `OPENROUTER_MODEL` |

### 8.2 Agente CATEYE

El agente principal (`cores/ai/orion_agent.py`) usa tool calling para:
- Consultar el contexto del sistema
- Ejecutar herramientas de análisis
- Generar hipótesis de vulnerabilidades
- Responder preguntas del operador

### 8.3 Modelo Económico

Cada programa tiene un **ORION Score** (0.0–1.0) calculado como:

```
ORION_SCORE = w1 × freshness + w2 × tech_fit + w3 × competition_inverse + w4 × historical_success
```

**EVH** (Expected Value per Hour):

```
EVH = (max_reward × 0.6 × ORION_SCORE × 0.7) / max(effort_hours, 0.5)
```

---

## 9. Sincronización y Plataformas

### 9.1 Conexión con Plataformas

El sistema permite vincular cuentas de:
- **HackerOne**
- **Bugcrowd**
- **Intigriti**
- **Synack**
- **YesWeHack**

Las credenciales se almacenan en una **bóveda encriptada** (`cores/identity_vault.py`) usando Fernet (symmetric encryption). Cada cuenta permite:
- Subir reportes automáticamente
- Sincronizar estado de envíos
- Recibir webhooks con actualizaciones
- Historial completo de submissions

### 9.2 Webhooks

`POST /api/webhooks/{platform}` recibe callbacks de las plataformas para actualizar:
- Estado del reporte (triaged, resolved, paid, rejected)
- Recompensa otorgada
- Comentarios del equipo de seguridad

### 9.3 Sync Multi-dispositivo

`POST /api/sync/push` y `GET /api/sync/pull` permiten sincronizar el estado entre dispositivos (sesión, filtros, último target visitado).

---

## 10. Seguridad

- **Autenticación**: token-based (device_id + server session)
- **Licencias**: validación con clave de activación
- **Bóveda de credenciales**: encriptación Fernet (AES-128)
- **CORS**: configurado para frontend local
- **Rate limiting**: middleware de rate limit
- **Guardianes de arranque**: `boot_guard.py` previene modos inseguros
- **No se almacenan API keys en texto plano**: siempre en vault o variables de entorno
- **Headless por defecto**: no expone puertos a la red

---

## 11. Despliegue

### 11.1 Modos de ejecución

| Modo | Comando | Descripción |
|---|---|---|
| Full stack | `python launcher/start.py` | Backend + frontend + browser |
| Backend only | `python launcher/start.py --backend` | API sola |
| Demo mode | `python launcher/start.py --demo` | Fake dataset para pruebas |
| Dashboard (react) | `python launcher/start.py --dashboard react` | Frontend Vue dev server |
| Desktop | `python run.py --tray` | System tray icon (PyInstaller) |
| Service | `python run.py --service` | Windows service |
| Safe mode | `python run.py --safe-mode` | Degradado, browser only |
| Build | `python run.py --build` | PyInstaller bundle |

### 11.2 Stack técnico

```
OS: Linux, macOS, Windows
Runtime: Python ≥3.10
Database: SQLite (dev) / PostgreSQL (prod)
Frontend server: Vite dev server o built dist/
Queue: SQLite-based (no Redis requerido)
```

---

## 12. Evolución y Roadmap

### Estado actual (v1.7.0)

| Feature | Estado |
|---|---|
| Panel económico con KPIs | ✅ Completo |
| Money Radar (ranking de programas) | ✅ Completo |
| Pipeline de hallazgos | ✅ Completo |
| Centro de reportes con submit | ✅ Completo |
| Hipótesis vía IA con campos didácticos | ✅ Completo |
| Guía de validación manual | ✅ Completo |
| Cacería autónoma 24/7 | ✅ Completo |
| Lector de alcance (scope_reader) | ✅ Completo |
| Bóveda de identidades encriptada | ✅ Completo |
| Patrones aprendidos (memory) | ✅ Completo |
| Timeline de eventos | ✅ Completo |
| Integración ZAP (spider + passive + hypotheses) | ✅ Completo |
| Sync multi-dispositivo | ✅ Completo |
| Panel de Conexiones (plataformas + bancos) | 🆕 Nueva |
| Vista Calendario/Timeline | 🆕 Nueva |
| Retiros bancarios (withdrawals) | 🔜 Próximo |
| Workflow humano: scope → hipótesis → validación → reporte | 🔜 Próximo |
| Mobile app | 🔜 Futuro |

---

## 13. Auditoría UX (Julio 2026)

Se realizó una auditoría de fricciones con perspectiva de **bug bounty hunter profesional**. Resultados:

| Categoría | Issues | Resueltos |
|---|---|---|
| 🔴 Críticos | 5 | 5 |
| 🟠 Altos | 6 | 6 |
| 🟡 Medios | 8 | 8 |
| 🟢 Bajos | 5 | 5 |
| **Total** | **24** | **24 (100%)** |

### Mejoras clave aplicadas

- **Sidebar**: 36 → 13 items (secciones compactas Inteligencia/Operaciones/Sistema)
- **Onboarding**: 9 → 5 pasos, skip con confirmación, tool check eliminado
- **Rutas**: eliminado `/dashboard` duplicado, `/legacy` → `/mission-control`
- **Branding**: banner `R A S T R O` → `C A T E Y E`, env vars `RASTRO_*` → `CATEYE_*`
- **Feedback**: auto-save con indicador visual, Tools con loading spinner, WS status en topbar
- **Seguridad**: import config validado, reset con doble confirmación
- **Shortcuts**: `⌘B` Copilot y `⌘K` Command Palette visibles en topbar
- **Paths**: `tray.py` y `updater.py` ahora usan `cores/utils/paths.py:get_data_path()` como único resolver
- **Config**: `cache_size` migrado de `cores/config.py:RastroConfig` a `cores/env/config.py:EnvConfig`, `RastroConfig` eliminado
- **Env vars**: todos los `RASTRO_*` en `EnvConfig` renombrados a `CATEYE_*`
- **TypeScript**: 0 errores

---

## 14. Progreso de Producción

### Código Total

| Métrica | Valor |
|---|---|
| Líneas de Python (`cores/` + `api/`) | ~59.3K |
| Líneas de frontend (`frontend/src/`) | ~19.2K |
| Líneas de tests | ~4.5K |
| **Total líneas fuente** | **~83K** |
| Archivos Python (`cores/` + `api/`) | 374 |
| Archivos frontend (`.ts`/`.vue`/`.css`) | 89 |
| Archivos de tests | 15 |
| **Total archivos fuente** | **~478** |

### Completitud por Área

| Área | % | Detalle |
|---|---|---|
| **Backend `cores/`** | **100%** | 57 módulos, ~45K líneas. Alembic configurado con migration inicial, `cache_size` migrado a EnvConfig, `RastroConfig` → `CATEYEConfig`, todos los env vars en `CATEYE_*`. |
| **API REST** | **96%** | 56 routers registrados y funcionales. OpenAPI con security scheme Bearer JWT, description, contact, license info. Pendientes: normalización de formato de respuesta. |
| **Frontend Vue 3** | **93%** | 50 páginas, 21 componentes, 6 stores, navegación podada (36→13 items), onboarding reducido (9→5 pasos), auto-save global, shortcuts visibles, todas las páginas de detalle implementadas. Vitest + Vue Test Utils configurados, 30 tests unitarios (Button, Badge, Card, utils). |
| **Desktop / Launcher** | **87%** | Multi-modo (browser, tray, service, safe-mode), build PyInstaller, system tray, boot guard. Launcher unificado con branding corregido, paths de datos unificados. |
| **Plataformas Bug Bounty** | **68%** | 5 integraciones (HackerOne, Bugcrowd, Intigriti, Synack, YesWeHack), bóveda encriptada Fernet, scraping infraestructura presente. Pendientes: battle-testing, manejo de errores de API. |
| **Tests** | **30%** | 15 suites backend, 4.5K líneas. Tests de API, agents, scoring, E2E. **Frontend**: Vitest + Vue Test Utils configurados, 30 tests (Button, Badge, Card, utils). |
| **Mobile** | **0%** | Planificado para v1.4 (Capacitor Android + Tauri desktop). |

### Total General: **~93%**

### 7% Restante (Priorizado)

| Prioridad | Item | Esfuerzo |
|---|---|---|
| 1 | Más tests frontend (stores, pages, composables) | 3-5 días |
| 2 | Normalizar formato de respuesta API (unificar HTTPException/APIEnvelope/bare dicts) | 2-3 días |
| 3 | Completar CRUD faltantes (DELETE targets, endpoints, findings, evidence, verdicts) | 1-2 días |
| 4 | Rebuild Android compiled assets | 1 día |
| 5 | Responsive design + PWA | 2-3 días |
| 6 | Mobile (Capacitor/Tauri) | 1-2 semanas |
| 7 | Migrar `cores/platforms/` a unificar con `identity_vault.py` + retry + rate-limit | 3-4 días |
| 8 | Migrar `cores/notifications/` (FCM, SMTP) a env vars `CATEYE_*` consistentes | 0.5 días |
| 9 | Migrar `cores/auth/auth.py` + `cores/license/validator.py` a env vars `CATEYE_*` | 0.5 días |
| 10 | Implementar servicio Linux systemd + macOS launchd | 2 días |
