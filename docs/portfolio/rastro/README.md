# Rastro — Portfolio Evidence Package

> Paquete de evidencia reutilizable para GitHub · LinkedIn · Fiverr · CV · website.
> Solo contenido real y verificable. Última revisión: 2026-08-10.

> **Estado**: el pipeline de seguridad vive dentro del repo OWNEX (módulo CATEYE legacy
> `cores/` + `core/cycles/security`). Este paquete documenta esa pieza para su extracción
> como repo independiente en PHASE 2 del Professional Presence Plan.

## One-liner

**Rastro** — pipeline de bug bounty automatizado: descubrimiento, reconocimiento, hipótesis,
validación, evidencia y reporte en un flujo E2E con priorización por valor esperado real.

## Problem

El bug bounty manual repite el mismo ciclo: descubrir targets, escanear, formular hipótesis,
validar, armar evidencia, reportar. Sin pipeline, las oportunidades de alto EV se pierden en
ruido y la evidencia queda desorganizada.

## Solution

Un pipeline de 13 stages que orquesta el ciclo completo con priorización económica:
- **Discovery** de targets/programas con scoring por EV y cooldown anti-rescaneo
- **Recon** (subdominios, endpoints, ataque de superficie) con prefetch y normalización
- **Hipótesis** por target con razonadores (IDOR, SSRF, XSS, SQLi, Auth Bypass) + Hypothesis
  Challenger (explicaciones alternativas, contrapruebas, incertidumbre explícita)
- **Validación** con confidence scoring penalizado por incertidumbre
- **Evidencia** estructurada (PoC, CVSS, CWE, CAPEC) con integridad verificable
- **Reporte** generado en plantillas de plataforma reales
- **Aprendizaje**: cada outcome pliega feedback al scoring (nunca inventa tasas)

## Stack

Python 3.11 · FastAPI · SQLAlchemy · httpx · pytest · Ruff

## Features (verificables)

| Área | Detalle |
|------|---------|
| Pipeline | discover→recon→hypothesis→auto_validate→promote→validate→report→ai_bounty (13 stages) |
| Priorización | TargetPrioritizer por EV: reward × detección × velocidad (USD/h real de payout history) |
| Recon | subdomain/endpoint discovery, análisis de superficie con cooldown 1h |
| Razonadores | 5 tipos de vuln (IDOR, SSRF, XSS, SQLi, Auth Bypass) con evidence bundles |
| Challenger | explicaciones alternativas + tests de contradicción + uncertainty penalty |
| Revenue intelligence | plataformas rankeadas por payout real, velocidad de pago, USD/hora |
| Evidencia | composer estandarizado, PoC + metadata, verificable |

## Screenshots

- Intelligence: `docs/assets/screenshots/desktop/intelligence.png`
- Targets / Discovery: `docs/assets/screenshots/desktop/targets.png`
- Reports: `docs/assets/screenshots/desktop/reports.png`
- Executive Dashboard (verdict semanal "$ ganado esta semana"): `docs/assets/screenshots/desktop/executive-dashboard.png`

## Architecture (resumen)

```
Rastro pipeline
├── ScanScheduler (api/scheduler.py) — 13 stages, cooldown + priorización
├── cores/recon/ — discover, subdomains, endpoints, osint
├── cores/validation/ — challenger, gate, confidence
├── cores/evidence/ — composer, bundles
├── core/cycles/security.py — SecurityCycle + 7 stage executors + run_pipeline()
└── revenue intelligence — USD/h, platform speed, EV ranking
```

## Results (honestos)

- Pipeline E2E corre solo: scheduler ejecuta run_pipeline con guards anti-duplicado
- 7 stage executors + tests E2E pasan (8/8)
- Priorización por USD/hora real desde payout history, fallback a estimación curada

## Limitations (honestas)

- Probes HTTP con razonadores deterministas; validación final requiere humano
- Depende de fuentes externas (plataformas) que degradan graceful
- Sin auto-submisión: enviar reportes requiere aprobación (Human Control)

## Installation

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python run.py --add-target <name> --domain <domain>   # agregar target
python run.py                                        # backend + scheduler
```

## Fork de uso

LinkedIn: One-liner + Problem + Solution + Stack + "mi pipeline de seguridad automatizada"
con screenshots. Fiverr: gigs de security testing/automation con evidencia real,
etiquetado como proyecto personal.