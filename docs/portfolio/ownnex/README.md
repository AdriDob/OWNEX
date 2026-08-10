# OWNEX — Portfolio Evidence Package

> Paquete de evidencia reutilizable para GitHub · LinkedIn · Fiverr · CV · website.
> Solo contenido real y verificable. Última revisión: 2026-08-10.

## One-liner

**OWNEX** — Autonomous Work Operating System. Descubre oportunidades, automatiza el flujo
de seguridad, orquesta agentes y rutea IA local/cloud en un solo sistema privado.

## Problem

Operar bug bounty, desarrollo y generación de ingresos implica decenas de herramientas
desconectadas: scanners por un lado, trackers de ingresos por otro, agentes en una
tercera. La información no fluye, las oportunidades se pierden y la evidencia se dispersa.

## Solution

Un sistema único que cierra loops completos: discovery de oportunidades puntuadas por
barrera real y valor esperado → pipeline de seguridad E2E (recon → hipótesis → validación
→ evidencia → reporte) → 6 Work Cycles con 28 jobs de scheduler → runtime de IA (OAR) con
fallbacks y presupuesto → autonomía con approval gates → inteligencia de ingresos.

## Stack

Python 3.11 · FastAPI · SQLAlchemy · Vue 3 · TypeScript · Tailwind CSS 4 · Tauri 2 ·
SQLite/PostgreSQL · pytest · Ruff · mypy strict

## Features (verificables)

| Área | Detalle |
|------|---------|
| Opportunity Discovery | 135+ fuentes curadas, score 0-100 por barrera/EV, Work Bank autónomo |
| Security Pipeline | 7 stages E2E conectados: recon→attack_surface→hypothesis→validation→evidence→report→learning |
| Work Cycles | security, forge, pulse, vault, atlas, direct_work — 28 jobs scheduler |
| OAR AI Runtime | registry de providers, routing por TaskType, cost tracker, circuit breaker, cache semántica |
| Autonomía | workflow engine, handoffs departamentales, CoderAgent, approval gates |
| Evidence | evidence composer, hashing, integridad, reportes exportables |
| Frontend | Mission Control, 61 rutas, dark+light, design system propio, desktop Tauri (deb/rpm/AppImage) |
| Calidad | 3179+ tests, ruff 0 errores, vue-tsc 0 errores |

## Screenshots

- Mission Control: `docs/assets/screenshots/desktop/mission-control.png`
- Good Morning (panel diario): `docs/assets/screenshots/desktop/good-morning.png`
- Executive Dashboard (CEO view): `docs/assets/screenshots/desktop/executive-dashboard.png`
- Intelligence: `docs/assets/screenshots/desktop/intelligence.png`
- Capital / Revenue: `docs/assets/screenshots/desktop/capital-dashboard.png`
- Reports: `docs/assets/screenshots/desktop/reports.png`
- Mobile Companion: `docs/assets/screenshots/mobile/mission-control.png`

## Architecture (resumen)

```
OWNEX (monolito modular)
├── API: FastAPI (api/main.py, 60+ routers)
├── Core: EventBus, Scheduler, UnifiedMemory, Registry
├── Cores: security pipeline, opportunity, direct_work_engine, ai/runtime (OAR), revenue
├── Cycles: security, forge, pulse, vault, atlas, direct_work + QA
├── Frontend: Vue 3 + Tauri desktop + Capacitor Android
└── DB: SQLite (dev) / PostgreSQL (prod)
```

## Technical decisions destacadas

- Monolito modular + EventBus (no microservicios): 1 usuario, 0 infraestructura externa
- Barrera de entrada como espectro 0-100, nunca una promesa
- Feedback loop real: scoring aprende de outcomes verificados (no inventa tasas)
- Local-first AI: Ollama + proxys propios, fallback chain, presupuesto diario USD
- Evidencia > adjetivos: sin mocks en producción, todo visible por API/UI

## Results (honestos)

- Pipeline E2E funciona sin intervención (scheduler + cycles)
- 3179 tests pasan, lint 0 errores en todo el repo
- Desktop release: OWNEX OMEGA 7.0.0 (deb/rpm/AppImage)
- Android APK debug compila (ai.rastro.app)

## Limitations (honestas)

- Sistema privado de 1 usuario, no multiusuario
- Scrapers de plataformas dependen de disponibilidad externa (degradan graceful)
- Validación GUI desktop requiere sesión gráfica (headless no renderiza)

## Installation

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python scripts/dev test-fast    # smoke tests
python run.py                   # arranca backend :8000
cd frontend && npm install && npm run dev   # frontend :5173
```

## Fork de uso

LinkedIn: usar One-liner + Problem + Solution + Stack + 3 screenshots + link al repo.
Fiverr: usar features de automation/security + screenshots como portfolio visual + nota
"personal project" donde corresponda.