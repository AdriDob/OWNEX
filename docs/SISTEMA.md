# CATEYE — Documentación del Sistema

**Versión:** Alpha 1.0 | **Stack:** Python 3.10+ · FastAPI · Vue 3 · SQLAlchemy · SQLite/PostgreSQL

---

## Arquitectura General

CATEYE es un sistema de inteligencia económica para bug bounty compuesto por tres capas:

```
DESKTOP (main_desktop.py)
  PyWebView | SystemTray | Uvicorn (thread) | Watchdog
       |
FASTAPI (api/main.py)
  55+ Routers | Auth+Rate Middleware | Scheduler 6-stage | WebSocket
       |
CORE ENGINES (cores/)
  AI | Agents (8) | Recon | Intelligence | Economic | Opportunity
  Hypothesis | Validation | Reporting | Scope Reader | Identity Vault
  Memory | Events | Orchestrator | Autonomous | Platforms (5)
       |
DATABASE (SQLAlchemy)
  models.py (30+ ORM) · models_economic.py (8) · SQLite/PostgreSQL
       |
FRONTEND (Vue 3 + TypeScript + Vite + Tailwind v4 + Pinia)
  EconomicDashboard | MoneyRadar | Findings | Reports | Settings
```

## Stack Tecnológico

| Componente | Tecnología |
|---|---|
| Frontend | Vue 3, TypeScript, Vite, Tailwind v4, Pinia, Radix Vue, Lucide |
| Backend | Python 3.10+, FastAPI 0.95+, Uvicorn |
| Base de datos | SQLAlchemy 2.0+ / SQLite (dev) / PostgreSQL (prod) |
| IA | Gemini (principal), Ollama (local), OpenAI, OpenRouter |
| Escritorio | PyWebView + PyInstaller + Pystray + Plyer |
| Cifrado | AES-256-GCM, Fernet (PBKDF2-HMAC-SHA256) |
| Gráficos | Chart.js + vue-chartjs |
| Testing | pytest + pytest-cov + Playwright |

## Puertos

```
Frontend: http://localhost:5173  (dev) / built-in desde backend
API:      http://localhost:8000
Docs API: http://localhost:8000/docs
```

## Variables de Entorno

| Variable | Default | Descripción |
|---|---|---|
| `OLLAMA_HOST` | `http://localhost:11434` | Host del servicio Ollama |
| `OLLAMA_MODEL` | `qwen3:14b` | Modelo local por defecto |
| `GEMINI_API_KEY` | — | API Key de Google Gemini |
| `DATABASE_URL` | `sqlite:///.orion/database/orion.db` | Conexión a base de datos |
| `CATEYE_AUTH_TOKEN` | — | Token de sesión (generado automáticamente) |

## Filosofía de Diseño

- **100% local** — ningún dato sale de tu máquina
- **Privacidad total** — credenciales cifradas con AES-256-GCM
- **Sin suscripciones** — código abierto, autónomo
- **Pasivo por diseño** — ZAP solo en modo spider + passive scan. Nunca lanza exploits sin autorización.
- **Enfoque económico** — toda decisión se mide en USD/hora, probabilidad de éxito, retorno esperado

## Componentes Principales

### Backend (`cores/` + `api/`)

| Módulo | Responsabilidad |
|---|---|
| `cores/ai/` | Proveedores IA, OrionAgent con tool calling, contexto unificado |
| `cores/agents/` | Sistema multi-agente (8 agentes vía event bus) |
| `cores/recon/` | Wrappers para 15+ herramientas externas + 16 clientes OSINT |
| `cores/engine/` | Hipótesis, scoring unificado (ORION Score), ROI |
| `cores/intelligence/` | Bucle de inteligencia, aprendizaje, memoria adaptativa |
| `cores/platforms/` | Integraciones: HackerOne, Bugcrowd, Intigriti, Synack, YesWeHack |
| `cores/orchestrator/` | Pipeline de cacería, scan service |
| `cores/autonomous/` | Motor de cacería autónoma 24/7 |
| `cores/reporting/` | Generación de reportes profesionales |
| `cores/validation/` | Motor de validación y veredictos |
| `cores/events/` | Bus de eventos interno (pub/sub) |
| `cores/memory/` | Memoria a largo plazo y patrones aprendidos |
| `api/routers/` | 55+ routers FastAPI organizados por dominio |

### Frontend (`frontend/`)

| Ruta | Página | Propósito |
|---|---|---|
| `/` | EconomicDashboard | KPIs, pipeline funnel, top oportunidades |
| `/money-radar` | MoneyRadar | Programas rankeados por ORION Score |
| `/radar` | OpportunityRadar | Oportunidades descubiertas |
| `/hot-paths` | HotPaths | Rutas de ataque priorizadas |
| `/findings` | Findings | Pipeline de hallazgos |
| `/reports` | ReportCenter | Reportes con IA, export, envío |
| `/programs/:id` | ProgramIntel | Dossier por programa |
| `/settings` | Settings | Configuración del sistema |
| `/connections` | Connections | Conexiones a plataformas y cuentas de cobro |
| 40+ páginas más | — | Detalle, operaciones, inteligencia |

## Screenshots

Ver [docs/screenshots/README.md](screenshots/README.md) para la galería completa de capturas del sistema.

## Documentación Relacionada

| Documento | Descripción |
|---|---|
| [`SYSTEM.md`](../SYSTEM.md) | Documentación completa del sistema |
| [`SYSTEM_INVENTORY.md`](../SYSTEM_INVENTORY.md) | Inventario técnico exhaustivo |
| [`README.md`](../README.md) | Landing page del proyecto |
