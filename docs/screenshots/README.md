# ORION Platform — Screenshots

Imágenes del sistema ORION Platform v4.7.0. Todos los screenshots son SVGs generados con la estética cyber/terminal del sistema (púrpura `#A855F7` / oro `#F5A623` sobre negro `#050508`).

## Pantallas Principales

| Screenshot | Descripción |
|---|---|
| [![Cover](screenshots/orion-cover.svg)](screenshots/orion-cover.svg) | **ORION Cover / Hero** — Portada del sistema con logo ORION (marca CE), versión, pilares funcionales (AEGIS, CATEYE, ATLAS, ODYSSEY, MERLIN, COPILOT, REVENUE) y estado del sistema. |
| [![Dashboard](screenshots/orion-dashboard.svg)](screenshots/orion-dashboard.svg) | **Dashboard Principal ORION** — Centro de mando con KPIs en tiempo real (targets, endpoints, hallazgos, pagos), gráficos de severidad y veredictos, oportunidades prioritarias con EV scoring. |
| [![Revenue Intelligence](screenshots/orion-revenue-intelligence.svg)](screenshots/orion-revenue-intelligence.svg) | **Revenue Intelligence** — Pipeline completo Finding→Evidence→Report→Platform→Payout. Desglose por plataforma (HackerOne, Bugcrowd, Intigriti, Immunefi), Target Prioritizer con EV scoring, Economic Memory (aprendizaje de pagos), Report Acceptance Optimizer. |
| [![Offensive Intelligence](screenshots/orion-offensive-intelligence.svg)](screenshots/orion-offensive-intelligence.svg) | **Inteligencia Ofensiva (CATEYE)** — 5 Reasoners (IDOR, SSRF, XSS, SQLi, Auth Bypass) con stats, técnicas y hallazgos recientes. Contradiction Engine (7 tipos), Evidence Composer (PoC, curl, Python, CVSS, CWE, CAPEC, MITRE), HTTP Probes Pipeline en vivo. |
| [![Knowledge Intelligence](screenshots/orion-knowledge-intelligence.svg)](screenshots/orion-knowledge-intelligence.svg) | **Inteligencia de Conocimiento** — Evidence Graph (nodo central + evidencias a favor/en contra/neutral con balance scoring), Knowledge Graph (explorador SQL de nodos/aristas), Decision Journal (append-only), integración COPILOT (consultas en lenguaje natural). |
| [![Automation & Operations](screenshots/orion-automation-operations.svg)](screenshots/orion-automation-operations.svg) | **Automatización y Operaciones (MERLIN)** — Core Scheduler (13 etapas pipeline E2E), Hermes Automation Agent (6 comandos), Workflow Engine (definiciones declarativas), Extension SDK (hot reload, manifest, hooks), Senior Copilot Agent (5 niveles autoridad, 4 auditors, Policy Engine, Recommender). |
| [![Architecture Overview](screenshots/orion-architecture-overview.svg)](screenshots/orion-architecture-overview.svg) | **Visión Arquitectónica** — Diagrama completo monolito modular + event-driven: ORION Core (Registry, EventBus, Scheduler, DB Manager, AI Runtime, Memory, Decision Journal, Simulation), Shared Security Layer, Apps (CATEYE/ATLAS/ODYSSEY), Frontend (Vue 3). Incluye 4 problemas críticos documentados (0.1-0.4) con fixes propuestos. |
| [![Mobile Companion](screenshots/orion-mobile-companion.svg)](screenshots/orion-mobile-companion.svg) | **ORION Companion (Android/Wear OS)** — Centro de control móvil: health score, tabs (Home/Dashboard/Alertas/Config), quick actions (Scan, Reportar, Cobros, COPILOT), estado del sistema en un vistazo. |
| [![Event Flow / Pipeline](screenshots/orion-event-flow.svg)](screenshots/orion-event-flow.svg) | **Flujo de Eventos y Pipeline** — 6 etapas pipeline horizontal (DISCOVER→RECON→HYPOTHESIS→VALIDATE→REPORT→AUTO-REPORT), productores/consumidores de eventos, CoreEventBus central con bridge a legacy, Correlation ID trace E2E, catálogo 40+ tipos de eventos. |

---

## Logos y Branding

| Asset | Descripción |
|---|---|
| [![Logo Mark](screenshots/orion-logo-mark.svg)](screenshots/orion-logo-mark.svg) | **Logo Mark** — Icono principal ORION (anillos orbitales, core púrpura/oro, punto cian). |
| [![Logo Horizontal](screenshots/orion-logo-horizontal.svg)](screenshots/orion-logo-horizontal.svg) | **Logo Horizontal** — Para sidebar/header. |
| [![Logo Vertical](screenshots/orion-logo-vertical.svg)](screenshots/orion-logo-vertical.svg) | **Logo Vertical** — Para splash/loading. |
| [![Favicon](screenshots/orion-favicon.svg)](screenshots/orion-favicon.svg) | **Favicon** — 48×48 optimizado. |

---

## Convenciones Visuales

- **Fondo**: `#050508` con grid sutil y scanline overlay
- **Púrpura primario**: `#A855F7` / `#7C3AED` / `#6D28D9` — marca, headers, acentos
- **Oro acento**: `#F5A623` / `#FFCC66` — métricas económicas, warnings, highlights
- **Verde éxito**: `#00FF41` / `#00E676` — confirmados, activo, online
- **Cian info**: `#00FFFF` / `#00B8FF` — EventBus, COPILOT, arquitectura
- **Naranja warning**: `#FF6600` / `#FFAB00` — medio-alto, cola
- **Rojo crítico**: `#FF1744` / `#FF4466` — rechazados, errores, bugs críticos
- **Tipografía**: Orbitron (display/títulos), Inter (sans), JetBrains Mono (mono/código)
- **Tarjetas**: Glass effect `rgba(12,12,18,0.92)` + borde `rgba(109,40,217,0.15)` + glow superior
- **Grid**: Pattern sutil 40×40px con `#6D28D9` opacity 0.12

---

## Regeneración

```bash
# Desde la raíz del proyecto
python scripts/generate_screenshots.py
```

Última actualización: **Julio 2026** — ORION v4.7.0 STABLE
