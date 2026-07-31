# FUNCTIONAL SPEC — CATEYE v4.6.0 STABLE

> **REGLA DE ORO**
>
> Este documento NO describe la arquitectura.
> Describe únicamente capacidades verificadas mediante código.
>
> Si una capacidad no puede demostrarse mediante código ejecutable,
> NO debe aparecer aquí.
>
> Si una capacidad está parcialmente implementada,
> debe marcarse como ⚠️ PARCIAL.
>
> Si una capacidad depende de configuración externa,
> debe indicarse explícitamente.
>
> Este documento es la única fuente de verdad sobre
> lo que CATEYE realmente puede hacer.

---

## Índice

| Sec | Título |
|-----|--------|
| 1 | Introducción |
| 2 | Filosofía |
| 3 | Capacidades del Sistema (por tarea real) |
| 4 | ORION |
| 5 | Capacidades del Usuario |
| 6 | Automatizaciones |
| 7 | Flujo Completo E2E |
| 8 | Integraciones |
| 9 | Herramientas de Recon |
| 10 | Plataformas Soportadas |
| 11 | Wallets y Crypto |
| 12 | Reportes |
| 13 | Dashboard y Métricas |
| 14 | Scheduler |
| 15 | EventBus |
| 16 | Base de Datos |
| 17 | Desktop |
| 18 | API REST |
| 19 | Frontend |
| 20 | Seguridad |
| 21 | Límites del Sistema |
| 22 | Extensibilidad |
| 23 | Preguntas Frecuentes |
| 24 | Checklist Completo de Capacidades |
| 25 | Casos de Uso Completos |

---

## 1. Introducción

CATEYE es un sistema de inteligencia operativa privada para bug bounty. Automatiza el ciclo completo: descubrimiento de programas, reconocimiento, generación de hipótesis, validación, reporte y seguimiento de pagos.

- **Versión:** 4.6.0
- **Arquitectura:** v3.0 STABLE
- **Stack:** Python + FastAPI + SQLAlchemy + SQLite | Vue 3 + TypeScript + Tailwind v4
- **Licencia:** Propietaria (validación Ed25519)
- **Propósito:** Single-user, local-first, desktop

---

## 2. Filosofía

1. **Eliminar trabajo humano repetitivo.** Toda feature debe responder: "¿esto elimina trabajo humano o solo agrega complejidad?"
2. **ORION decide, los módulos ejecutan.** ORION es read-only con una excepción documentada (RewardLearner escribe ~40 bytes/tipo de vuln).
3. **Un pipeline oficial.** El scheduler es el único flujo que se ejecuta en runtime. No hay state machines paralelas.
4. **Persistencia ante todo.** Estado crítico sobrevive reinicios (SQLite WAL, EventBus persistente, SystemState en DB).
5. **Seguridad > Funcionalidad.** Sin secretos en código, CSRF en todas las rutas mutantes, auditoría JSONL, cifrado AES-256-GCM.

---

## 3. Capacidades del Sistema (por tarea real)

Cada capacidad incluye: qué hace, qué módulos participan, qué automatiza, qué hace el usuario, estado, y evidencia.

---

### 3.1 Quiero descubrir programas nuevos

| Aspecto | Detalle |
|---------|---------|
| Qué hace CATEYE | Scrapea 6 fuentes (HackerOne, Bugcrowd, Intigriti, YesWeHack, Immunefi, arkadiyt/bounty-targets-data) más escaneo web (security.txt, robots.txt). Convierte programas a Targets en DB. |
| Módulos | `cores/bounty_scraper/scraper.py` (566: `scrape_all()`), `cores/bounty_scraper/monitor.py` (14: `DiscoveryMonitor`), `api/scheduler.py` (114: `_stage_discover()`) |
| Automatiza | Scheduler ejecuta DISCOVER cada 3600s. DiscoveryMonitor corre cada 24h. |
| Qué hace el usuario | POST `/api/discovery/scan` para trigger manual. POST `/api/discovery/import-all` para importar en bulk. GET `/api/discovery/programs` para listar. |
| UI | `frontend/src/pages/Discovery.vue` (ruta `/discovery`), `ProgramCatalog.vue` (ruta `/program-catalog`) |
| Eventos | `opportunity:found` (scheduler:130), `discovery:completed` (scheduler:187) |
| Estado | ✅ VERIFICADO |
| Evidencia | `cores/bounty_scraper/scraper.py:145,210,256,306,352,430,488,566,619` |

---

### 3.2 Quiero hacer recon sobre un dominio

| Aspecto | Detalle |
|---------|---------|
| Qué hace CATEYE | Ejecuta pipeline de herramientas: subfinder (subdominios), httpx (HTTP probing), katana (crawling), wayback (URLs históricas), nuclei (vuln scanning), amass, gau, ffuf, crtsh, whois. Normaliza resultados a Endpoints en DB. |
| Módulos | `cores/orchestrator/scan_service.py` (11: `launch_scan()`), `cores/recon/runner.py` (84: `run_pipeline()`), 12 runners en `cores/recon/*_runner.py` |
| Automatiza | Scheduler ejecuta RECON cada 1800s con cooldown de 3600s por target. Prioriza targets vía ORION. |
| Qué hace el usuario | POST `/api/targets/{id}/scan` para lanzar scan. POST `/api/scans` para scan standalone. Elige modo: FAST, DEEP, API. |
| Modos | FAST (subfinder+katana), DEEP (+httpx+amass+nuclei), API (solo httpx+katana+nuclei) — `cores/recon/tools.py:110-142` |
| UI | `frontend/src/pages/PipelineMonitor.vue` (ruta `/pipelines`), `AttackSurface.vue` (ruta `/attack-surface`) |
| Eventos | `discovery:completed` (scheduler:187) |
| Estado | ✅ VERIFICADO |
| Evidencia | `cores/orchestrator/scan_service.py:11-145`, `cores/recon/tools.py:78-142` |

---

### 3.3 Quiero validar un posible IDOR

| Aspecto | Detalle |
|---------|---------|
| Qué hace CATEYE | Ejecuta 8 generadores rule-based de hipótesis (IDOR, auth bypass, SSRF, privesc, data exposure, graphql, business logic, file operation). Scoring y memoria de patrones. Validación vía RequestReplayer + LLM semantic analysis. |
| Módulos | `cores/engine/hypothesis/generators.py` (857-913: 8 generadores + nuclei + tech + paths), `cores/validation/loop_engine.py` (31: `evaluate()`), `cores/validation/replayer.py`, `cores/validation/llm_analyzer.py` |
| Automatiza | Scheduler ejecuta HYPOTHESIS cada 900s sobre endpoints sin hipótesis. VALIDATE cada 7200s sobre findings abiertos high/critical. |
| Qué hace el usuario | POST `/api/hypotheses/{target_id}` para generar. POST `/api/validation/validate` para validar endpoint. POST `/api/validation/batch` para lote. POST `/api/validation/record` para verificación manual. |
| UI | `frontend/src/pages/HypothesisQueue.vue` (ruta `/hypotheses`), `VerificationGuide.vue` (ruta `/verify`), `ReplayCenter.vue` (ruta `/replay`) |
| Estado | ✅ VERIFICADO |
| Evidencia | `cores/engine/hypothesis/generators.py:33-854`, `cores/validation/loop_engine.py:31-148` |

---

### 3.4 Quiero generar un reporte

| Aspecto | Detalle |
|---------|---------|
| Qué hace CATEYE | Crea reporte desde findings confirmados con 4 formatos de exportación (markdown, HTML, PDF, TXT). Versionado. |
| Módulos | `cores/pipeline/report_service.py` (102: `create_report_from_findings()`, 164: `get_report()`, 171: `list_reports()`, 226: `update_report()`), `api/main.py` (257-284: auto-report subscriber) |
| Automatiza | Scheduler REPORT cada 3600s. Auto-report subscriber: finding confirmado → genera borrador automáticamente. |
| Qué hace el usuario | POST `/api/reports` para crear. GET `/api/reports/{id}/export?format=md/html/pdf/txt` para exportar. PUT `/api/reports/{id}` para editar. POST `/api/reports/{id}/submit` para enviar a plataforma. |
| UI | `frontend/src/pages/ReportCenter.vue` (ruta `/reports`), `ReportDetail.vue`, `ReportHistory.vue`, `ReportQueue.vue` |
| Estados de reporte | draft → ready → submitted → under_review → triaged → resolved → paid → disclosed → declined → duplicate → outdated (`report_service.py:18-21`) |
| Eventos | `report:generated` (scheduler:304) |
| Estado | ✅ VERIFICADO |
| Evidencia | `cores/pipeline/report_service.py`, `api/routers/reports.py`, `api/main.py:257-284` |

---

### 3.5 Quiero seguir un bounty hasta el pago

| Aspecto | Detalle |
|---------|---------|
| Qué hace CATEYE | Tracking de submissions, sincronización de earnings vía plataformas, reconciliación contra ledger, detección de depósitos crypto. |
| Módulos | `cores/tracking/service.py`, `cores/financial/scheduler.py` (55: `sync_platforms()`), `cores/financial/truth_layer.py` (297: TruthLayer), `cores/financial/reconciliation.py` |
| Automatiza | FinancialSyncScheduler corre cada 1800s. |
| Qué hace el usuario | GET `/api/financial/state`, `/api/financial/state/by-platform`, `/api/financial/ledger`. GET `/api/reports/{id}` para estado. |
| UI | `frontend/src/pages/Bounties.vue` (ruta `/bounties`), `MoneyRadar.vue` (ruta `/money-radar`) |
| Estado | ✅ VERIFICADO |
| Evidencia | `cores/financial/truth_layer.py:297-408`, `cores/financial/scheduler.py:45-60` |

---

### 3.6 Quiero controlar mis pagos y wallet

| Aspecto | Detalle |
|---------|---------|
| Qué hace CATEYE | Mantiene estado financiero derivado del ledger. 4 conectores blockchain (BTC, ETH/ERC20, SOL, TRX). Gestión de withdrawals. Clasificación de valor en 5 categorías. |
| Módulos | `cores/financial/truth_layer.py`, `cores/crypto/btc.py`, `cores/crypto/evm.py`, `cores/crypto/solana.py`, `cores/crypto/tron.py`, `cores/financial/withdrawal.py` |
| Automatiza | SyncManager actualiza balances periódicamente. FinancialSyncScheduler sincroniza earnings. |
| Qué hace el usuario | POST `/api/financial/withdrawals` para solicitar retiro. POST `/api/financial/adjustment` para ajuste manual. GET `/api/financial/state` para estado completo. |
| UI | `frontend/src/pages/FinancialTruth.vue` (ruta `/financial-truth`), `Wallets.vue` (ruta `/wallets`) |
| Estado | ✅ VERIFICADO |
| Evidencia | `cores/financial/truth_layer.py`, `cores/crypto/`, `api/routers/financial_truth.py` |

---

### 3.7 Quiero reabrir un programa/investigación vieja

| Aspecto | Detalle |
|---------|---------|
| Qué hace CATEYE | Persiste targets, endpoints, findings, reports, verdicts en SQLite. Acceso histórico vía API con paginación, búsqueda y ordenamiento. |
| Módulos | `database/models.py` (29 tablas), `api/services/data_service.py` (53: `list_targets()`) |
| Automatiza | N/A — consulta manual |
| Qué hace el usuario | GET `/api/targets?search=&sort_by=&sort_order=`. GET `/api/findings`. GET `/api/reports`. GET `/api/system/replay/{target_id}` para historial completo. |
| UI | Múltiples páginas con listados y detalle |
| Estado | ✅ VERIFICADO |
| Evidencia | `api/routers/targets.py:27-36`, `api/routers/findings.py:72-83`, `api/routers/reports.py:84-112` |

---

## 4. ORION

### 4.1 ORION PUEDE

| Capacidad | Implementación | Evidencia |
|-----------|---------------|-----------|
| ✅ Priorizar programas | `NextAction.get_next_action()` — scoring EVH (40%) + execution ease (25%) + competition (20%) + confidence (15%) | `cores/orion/next_action.py:18-101` |
| ✅ Recomendar siguiente acción | Returns single best action (target + stage) | `cores/orion/next_action.py:101-132` |
| ✅ Leer contexto del sistema | `ContextEngine.get_context()` — summary, next_action, opportunities, pipeline progress. Cache 30s. | `cores/orion/context_engine.py:140-196` |
| ✅ Analizar oportunidades | `OpportunityAnalyzer.analyze_opportunity()` — reward, effort, EVH, required steps, learning resources | `cores/orion/opportunity_analyzer.py:44-134` |
| ✅ Aprender recompensas | `RewardLearner.analyze()` — ajusta estimaciones de payout por tipo de vulnerabilidad. Persiste a RecoveryStore. | `cores/intelligence/reward_learning.py:82-245` |
| ✅ Controlar scheduler | Scheduler consulta `get_next_action()` para priorizar targets. Usa `orion_score` como multiplier. | `api/scheduler.py:331-354` |
| ✅ Explicar decisiones | Scheduler logea: `[ORION] Auto-prioritized X (priority=Y, why=Z)` | `api/scheduler.py:168-170` |
| ✅ Calcular EV | EVH scoring integrado en `NextAction` | `cores/orion/next_action.py:18` |
| ✅ Detectar cambios | OpportunityEngine detecta nuevas oportunidades vía providers | `cores/opportunity/engine.py` |
| ✅ Gestionar scheduler | ORION determina qué target escanea el scheduler en cada ciclo RECON | `api/scheduler.py:331-337` |
| ✅ Publicar eventos | `opportunity:found` vía EventBus | `cores/opportunity/engine.py:86` |
| ✅ Chat conversacional | OrionAgent vía LLM (solo lectura de DB) | `cores/ai/orion_agent.py` |

### 4.2 ORION NUNCA

| Capacidad | Explicación |
|-----------|-------------|
| ❌ Enviar reportes a plataformas | ORION es read-only. El envío requiere acción explícita del usuario. |
| ❌ Gastar dinero | No ejecuta transacciones crypto/fiat. No firma withdrawals. |
| ❌ Borrar evidencia | No tiene permisos de escritura sobre findings, endpoints, evidence. |
| ❌ Modificar scopes | No altera programas ni sus scopes. |
| ❌ Aceptar TOS | No interactúa con plataformas externas. |
| ❌ Enviar exploits | No ejecuta payloads ni modifica requests fuera del pipeline de validación. |
| ❌ Ejecutar acciones irreversibles | Toda acción que modifica estado requiere intervención humana. |
| ❌ Reemplazar decisión humana | Findings, reportes, y submissions requieren aprobación. |
| ❌ Escribir en DB (excepto RewardLearner) | Única excepción: `learning_state` (~40 bytes por tipo de vuln). |

---

## 5. Capacidades del Usuario

### 5.1 CRUD

| Recurso | Crear | Leer | Actualizar | Eliminar |
|---------|-------|------|------------|----------|
| Targets | ✅ POST `/api/targets` | ✅ GET `/api/targets`, `/{id}` | ❌ | ❌ |
| Endpoints | ✅ POST `/api/endpoints` | ✅ GET `/api/endpoints`, `/{id}` | ❌ | ❌ |
| Findings | ✅ POST `/api/findings` | ✅ GET `/api/findings`, `/{id}` | ✅ PUT status | ❌ |
| Reports | ✅ POST `/api/reports` | ✅ GET `/api/reports`, `/{id}` | ✅ PUT `/{id}` | ❌ |
| Evidence | ✅ POST `/api/evidence/upload` | ✅ GET `/api/evidence` | ❌ | ❌ |
| Verdicts | ❌ (auto-generados) | ✅ GET `/api/verdicts`, `/{id}` | ❌ | ❌ |
| Financial | ✅ POST adjustment | ✅ GET state/ledger | ❌ | ❌ |
| Withdrawals | ✅ POST `/api/financial/withdrawals` | ✅ GET list | ✅ POST complete/fail | ❌ |

### 5.2 Acciones Trigger

| Acción | Endpoint |
|--------|----------|
| Ejecutar discovery scan | POST `/api/discovery/scan` |
| Importar programas descubiertos | POST `/api/discovery/import-all` |
| Iniciar/monitor/detener discovery monitor | POST `/api/discovery/monitor/start\|stop`, GET `/api/discovery/monitor` |
| Lanzar scan sobre target | POST `/api/targets/{id}/scan` |
| Lanzar scan standalone | POST `/api/scans`, `/api/scans/unified`, `/api/scans/nuclei` |
| Generar hipótesis | POST `/api/hypotheses/{target_id}` |
| Validar endpoint | POST `/api/validation/validate` |
| Validar batch | POST `/api/validation/batch` |
| Registrar verificación manual | POST `/api/validation/record` |
| Clasificar finding | POST `/api/findings/{id}/classification` |
| Generar reporte | POST `/api/reports` |
| Exportar reporte | GET `/api/reports/{id}/export?format=md\|html\|pdf\|txt` |
| Exportar finding | GET `/api/findings/{id}/export-markdown\|export-pdf` |
| Enviar reporte a plataforma | POST `/api/reports/{id}/submit` |
| Refrescar contexto ORION | POST `/api/orion/context/refresh` |
| Refrescar oportunidades | POST `/api/opportunity/refresh` |
| Solicitar retiro | POST `/api/financial/withdrawals` |
| Confirmar/fallar retiro | POST `/api/financial/withdrawals/{id}/complete\|fail` |
| Ajuste manual financiero | POST `/api/financial/adjustment` |
| Pausar/reanudar scheduler | (vía config/settings) |

### 5.3 Exportaciones

| Formato | Recurso | Endpoint |
|---------|---------|----------|
| Markdown | Finding | GET `/api/findings/{id}/export-markdown` |
| PDF (HTML) | Finding | GET `/api/findings/{id}/export-pdf` |
| Markdown | Report | GET `/api/reports/{id}/export?format=markdown` |
| HTML | Report | GET `/api/reports/{id}/export?format=html` |
| PDF | Report | GET `/api/reports/{id}/export?format=pdf` |
| TXT | Report | GET `/api/reports/{id}/export?format=txt` |
| CSV | Oportunidades | GET `/api/opportunity/top?fmt=csv` |
| Markdown | Oportunidades | GET `/api/opportunity/top?fmt=markdown` |
| Prometheus | Métricas | GET `/api/metrics` |

---

## 6. Automatizaciones

| Automatización | Disparador | Responsable | ¿Pausable? | ¿Requiere aprobación? | Persistencia | Estado | Evidencia |
|---------------|------------|-------------|-------------|----------------------|-------------|--------|-----------|
| DISCOVERY | Scheduler cada 3600s | `ScanScheduler._stage_discover()` | Sí (vía `_running`) | No | Crea Targets en DB | ✅ | `api/scheduler.py:30,114` |
| RECON | Scheduler cada 1800s | `ScanScheduler._stage_recon()` | Sí (cooldown 3600s) | No | Crea Endpoints en DB | ✅ | `api/scheduler.py:31,141` |
| HYPOTHESIS | Scheduler cada 900s | `ScanScheduler._stage_hypothesis()` | Sí | No | Asigna hipótesis a endpoints | ✅ | `api/scheduler.py:32,212` |
| VALIDATE | Scheduler cada 7200s | `ScanScheduler._stage_validate()` | Sí | No | Crea findings/verdicts | ✅ | `api/scheduler.py:34,244` |
| REPORT | Scheduler cada 3600s | `ScanScheduler._stage_report()` | Sí | No | Crea reports en DB | ✅ | `api/scheduler.py:35,282` |
| Auto-report | EventBus: finding confirmado | Subscriber en `api/main.py` | No (siempre activo) | Sí (borrador editable) | Crea report draft | ✅ | `api/main.py:257-284` |
| Discovery Monitor | Timer 24h | `DiscoveryMonitor` | Sí | No | Descubre nuevos programas | ✅ | `api/main.py:315-322` |
| Financial Sync | Scheduler cada 1800s | `FinancialSyncScheduler` | Sí | No | Sincroniza earnings | ✅ | `api/main.py:295-303` |
| Health Monitor | Timer 8s | `HealthMonitor` | Sí | No | Solo monitoreo | ✅ | `api/main.py:325-333` |
| System Health | Timer 30s | `SystemHealthEngine` | Sí | No | Solo monitoreo | ✅ | `api/main.py:337-342` |
| Notification bridges | EventBus | 6 bridges (DB, desktop, email, FCM, WhatsApp, Gmail, WS) | No | No | Persisten notificaciones | ✅ | `api/main.py:219-239` |
| AgentBus→EventBus | Evento de agente | Bridge subscriber | No | No | Forwarding de eventos | ✅ | `api/main.py:307-312` |
| Auto-optimization | Timer | `OptimizationEngine` | Sí | No | Ajusta config | ✅ | `api/main.py:345-350` |

---

## 7. Flujo Completo E2E

```
                    ┌──────────────────────────────┐
                    │  1. PROGRAMA DESCUBIERTO      │
                    │  BountyScraper / import manual │
                    │  → Target en DB               │
                    └──────────┬───────────────────┘
                               ▼
                    ┌──────────────────────────────┐
                    │  2. PRIORIZACIÓN ORION        │
                    │  NextAction.get_next_action() │
                    │  → "este target es prioritario"│
                    └──────────┬───────────────────┘
                               ▼
                    ┌──────────────────────────────┐
                    │  3. RECON                     │
                    │  launch_scan() + ReconRunner  │
                    │  → Endpoints en DB            │
                    └──────────┬───────────────────┘
                               ▼
                    ┌──────────────────────────────┐
                    │  4. HIPÓTESIS                 │
                    │  8 generadores rule-based     │
                    │  + nuclei + tech + paths      │
                    │  → Hipótesis asignadas        │
                    └──────────┬───────────────────┘
                               ▼
                    ┌──────────────────────────────┐
                    │  5. VALIDACIÓN                │
                    │  ValidationLoopEngine         │
                    │  + RequestReplayer + LLM      │
                    │  → Finding + Verdict          │
                    └──────────┬───────────────────┘
                               ▼
                    ┌──────────────────────────────┐
                    │  6. REVISIÓN HUMANA           │
                    │  El usuario revisa findings   │
                    │  Confirma / Rechaza / Edita   │
                    └──────────┬───────────────────┘
                               ▼
                    ┌──────────────────────────────┐
                    │  7. REPORTE                   │
                    │  create_report_from_findings  │
                    │  → Borrador automático        │
                    │  El usuario edita y exporta   │
                    └──────────┬───────────────────┘
                               ▼
                    ┌──────────────────────────────┐
                    │  8. ENVÍO A PLATAFORMA        │
                    │  POST /api/reports/{id}/submit│
                    │  → Submission vía API key     │
                    └──────────┬───────────────────┘
                               ▼
                    ┌──────────────────────────────┐
                    │  9. SEGUIMIENTO               │
                    │  Tracking service             │
                    │  → Estados: triaged → paid    │
                    └──────────┬───────────────────┘
                               ▼
                    ┌──────────────────────────────┐
                    │ 10. PAGO                      │
                    │  Financial TruthLayer         │
                    │  + detección crypto/fiat      │
                    │  → Ledger actualizado         │
                    └──────────┬───────────────────┘
                               ▼
                    ┌──────────────────────────────┐
                    │ 11. WALLET                    │
                    │  Conectores BTC/ETH/SOL/TRX   │
                    │  → Balance actualizado        │
                    └──────────┬───────────────────┘
                               ▼
                    ┌──────────────────────────────┐
                    │ 12. APRENDIZAJE               │
                    │  RewardLearner.analyze()      │
                    │  → Ajusta prioridades         │
                    └──────────┬───────────────────┘
                               ▼
                    ┌──────────────────────────────┐
                    │ 13. RETROALIMENTACIÓN ORION   │
                    │  NextAction se re-calcula     │
                    │  → Nueva recomendación        │
                    └──────────────────────────────┘
```

---

## 8. Integraciones

### ✅ VERIFICADAS

| Integración | Tipo | Funcionalidad | Evidencia |
|-------------|------|---------------|-----------|
| HackerOne | Scraper + API | Scrape público, sync earnings | `cores/bounty_scraper/scraper.py:145`, `cores/platforms/hackerone.py` |
| Bugcrowd | Scraper + API | Scrape público, sync earnings | `cores/bounty_scraper/scraper.py:210`, `cores/platforms/bugcrowd.py` |
| Intigriti | Scraper + API | Scrape público, sync earnings | `cores/bounty_scraper/scraper.py:256`, `cores/platforms/intigriti.py` |
| YesWeHack | Scraper + API | Scrape público, sync earnings | `cores/bounty_scraper/scraper.py:306`, `cores/platforms/yeswehack.py` |
| Gmail | AuthHub OAuth2 | Autenticación, envío de notificaciones | `cores/authhub/gmail.py` |
| WhatsApp | AuthHub | Notificaciones | `cores/authhub/whatsapp.py` |
| Telegram | AuthHub | Notificaciones | `cores/authhub/telegram.py` |
| BTC | Crypto wallet | Balance, transacciones, retiros | `cores/crypto/btc.py` |
| EVM (ETH) | Crypto wallet | Balance, transacciones, retiros | `cores/crypto/evm.py` |
| Solana | Crypto wallet | Balance, transacciones, retiros | `cores/crypto/solana.py` |
| Tron | Crypto wallet | Balance, transacciones, retiros | `cores/crypto/tron.py` |

### ⚠️ PARCIALES

| Integración | Tipo | Limitación |
|-------------|------|------------|
| Synack | Listada en system definitions | Sin scraper ni sync implementado |
| Immunefi | Scraper | Solo scrape de programas públicos |
| arkadiyt/bounty-targets-data | Scraper | Depende del repositorio externo |

### ❌ NO VERIFICADAS

N/A — todas las integraciones listadas están verificadas.

---

## 9. Herramientas de Recon

| Herramienta | Runner | Modos | Estado | Evidencia |
|-------------|--------|-------|--------|-----------|
| subfinder | `cores/recon/subfinder_runner.py` | FAST, DEEP | ✅ | Passive subdomain discovery |
| httpx | `cores/recon/httpx_runner.py` | FAST, DEEP, API | ✅ | HTTP probing |
| katana | `cores/recon/katana_runner.py` | FAST, DEEP, API | ✅ | Crawling |
| nuclei | `cores/recon/nuclei_runner.py` | DEEP, API | ✅ | Vulnerability scanning |
| amass | `cores/recon/amass_runner.py` | DEEP | ✅ | Passive subdomain enum |
| gau | `cores/recon/gau_runner.py` | DEEP | ✅ | URL gathering |
| ffuf | `cores/recon/ffuf_runner.py` | DEEP | ✅ | Fuzzing |
| wayback | `cores/recon/wayback_runner.py` | FAST, DEEP | ✅ | Archive URLs |
| crtsh | `cores/recon/crtsh_runner.py` | FAST, DEEP | ⚠️ (requiere aiohttp) | Certificate transparency |
| whois | `cores/recon/whois_runner.py` | FAST, DEEP | ✅ | WHOIS lookups |
| ZAP import | `cores/recon/zap_import.py` | — | ✅ | Importar resultados ZAP |
| Burp import | `cores/recon/burp_import.py` | — | ✅ | Importar resultados Burp |

---

## 10. Plataformas Soportadas

| Plataforma | Scraper | Sync Earnings | Subir Reportes | Evidencia |
|------------|---------|---------------|----------------|-----------|
| HackerOne | ✅ | ✅ | ✅ | `cores/platforms/hackerone.py` |
| Bugcrowd | ✅ | ✅ | ✅ | `cores/platforms/bugcrowd.py` |
| Intigriti | ✅ | ✅ | ✅ | `cores/platforms/intigriti.py` |
| YesWeHack | ✅ | ✅ | ✅ | `cores/platforms/yeswehack.py` |
| Synack | ❌ | ❌ | ❌ | Solo listada en system definitions |
| Immunefi | ✅ (scrape) | ❌ | ❌ | Solo scraping público |

---

## 11. Wallets y Crypto

| Red | Conector | Balance | Tx History | Retiros | Evidencia |
|-----|----------|---------|------------|---------|-----------|
| Bitcoin | `cores/crypto/btc.py` | ✅ | ✅ | ✅ | `BtcConnector` |
| EVM (ETH + ERC20) | `cores/crypto/evm.py` | ✅ | ✅ | ✅ | `EVMConnector` |
| Solana | `cores/crypto/solana.py` | ✅ | ✅ | ✅ | `SolanaConnector` |
| Tron | `cores/crypto/tron.py` | ✅ | ✅ | ✅ | `TronConnector` |
| Exchange | `cores/crypto/exchange.py` | ✅ | ✅ | ❌ | `ExchangeConnector` |
| Wallet Connect | `cores/crypto/wallet_connect.py` | — | — | — | Protocolo de conexión |
| Sync Manager | `cores/crypto/sync_manager.py` | Sincronización periódica de todas las wallets | | | |

---

## 12. Reportes

| Capacidad | Detalle | Estado |
|-----------|---------|--------|
| Crear reporte desde findings | `create_report_from_findings()` | ✅ |
| Listar con filtros y ordenamiento | `list_reports()` con search, sort, pagination | ✅ |
| Editar reporte | PUT `/api/reports/{id}` | ✅ |
| 11 estados de lifecycle | draft → ready → submitted → ... → paid | ✅ |
| Exportar Markdown | GET `/api/reports/{id}/export?format=markdown` | ✅ |
| Exportar HTML | GET `/api/reports/{id}/export?format=html` | ✅ |
| Exportar PDF | GET `/api/reports/{id}/export?format=pdf` | ✅ |
| Exportar TXT | GET `/api/reports/{id}/export?format=txt` | ✅ |
| Versionado | POST `/api/reports/{id}/versions`, GET versions list | ✅ |
| Enviar a plataforma | POST `/api/reports/{id}/submit` | ✅ |
| Auto-generación | Subscriber: finding confirmado → report draft | ✅ |
| RewardLearning feedback | `update_report()` ajusta estimaciones | ✅ |
| Stats agrupados | GET `/api/reports/stats` | ✅ |
| Submission tracking | `cores/tracking/service.py` | ✅ |

---

## 13. Dashboard y Métricas

| Endpoint | Qué muestra | Estado |
|----------|-------------|--------|
| GET `/api/health` | Health check simple | ✅ |
| GET `/api/version` | Versión del sistema | ✅ |
| GET `/api/stats` | Targets/endpoints/findings/verdicts/evidence/scan_runs | ✅ |
| GET `/api/system/status` | Watchdog, pipeline, agents, memory, CPU | ✅ |
| GET `/api/system/state` | SystemState + service health | ✅ |
| GET `/api/system/state/events` | EventBus history | ✅ |
| GET `/api/system/timeline` | Timeline de eventos | ✅ |
| GET `/api/system/definitions` | Plataformas, tools, OSINT services | ✅ |
| GET `/api/system/confidence` | Confidence stats | ✅ |
| GET `/api/system/review` | Review queue | ✅ |
| GET `/api/system/replay/{target_id}` | Replay de eventos por target | ✅ |
| GET `/api/project-dashboard/summary` | Resumen de proyecto | ✅ |
| GET `/api/project-dashboard/git` | Estado git | ✅ |
| GET `/api/project-dashboard/tests` | Resultados de tests | ✅ |
| GET `/api/project-dashboard/feature-matrix` | Feature matrix | ✅ |
| GET `/api/project-dashboard/architecture-tree` | Árbol de arquitectura | ✅ |
| GET `/api/opportunity/overview` | Overview de oportunidades | ✅ |
| GET `/api/opportunity/top` | Top oportunidades (formato JSON/CSV/MD) | ✅ |
| GET `/api/orion/context` | Contexto ORION completo | ✅ |
| GET `/api/orion/next-action` | Próxima acción recomendada | ✅ |
| GET `/api/metrics` | Métricas estilo Prometheus | ✅ |

---

## 14. Scheduler

El scheduler (`api/scheduler.py`) es el **único pipeline oficial** que se ejecuta en runtime.

| Propiedad | Valor |
|-----------|-------|
| Clase | `ScanScheduler` (`api/scheduler.py:43`) |
| Inicio | `api/main.py:193-200` — `asyncio.create_task(scheduler.start())` |
| Loop | `_loop()` cada `interval_minutes` (defecto 30) |
| Stages | 5: DISCOVER (3600s), RECON (1800s), HYPOTHESIS (900s), VALIDATE (7200s), REPORT (3600s) |
| Cooldown | `TARGET_COOLDOWN = 3600` — no re-escanear mismo target antes de 1h |
| Priorización | ORION `get_next_action()` + `RewardLearner.analyze()` + `orion_score` multiplier |
| Eventos | Publica `opportunity:found`, `discovery:completed`, `report:generated` |
| Estado | ✅ Corregido en v3.0 (launch_scan args fix + test loop_resilient fix) |

---

## 15. EventBus

| Propiedad | Valor |
|-----------|-------|
| Clase | `EventBus` (`cores/events/event_bus.py`) |
| Persistencia | SQLite vía `EventRecord` |
| Prioridades | 22 tipos de eventos clasificados (CRITICAL, HIGH, MEDIUM, LOW) |
| Suscripción | `subscribe(event_type, handler)` + `subscribe_async` |
| Publicación | `publish(event_type, **payload)` |
| Historial | `get_history(event_type, limit)` |
| Agentes | `AgentBus` (in-memory) con bridge → EventBus |
| Intelligence | `EventSystem` (wrapper tipado sobre EventBus) |
| Eventos del sistema | Ver `cores/events/event_bus.py:32-54` |

---

## 16. Base de Datos

| Propiedad | Valor |
|-----------|-------|
| Engine | SQLite (WAL + FK + synchronous NORMAL) |
| ORM | SQLAlchemy 2.0+ |
| Tablas | 36 (29 en `models.py` + 7 en `models_economic.py`) |
| Migraciones | Alembic (1 migración no-op — `init_db()` vía `create_all`) |
| Inicialización | `database/db.py:83` — `init_db()` + auto-migración de columnas |
| Path DB | `get_data_dir() / "catseye.db"` |
| Session | `SessionLocal()` — factory scoped |

---

## 17. Desktop

| Capacidad | Detalle | Estado |
|-----------|---------|--------|
| Multi-modo | browser, tray, service, safe-mode | ✅ |
| PyInstaller build | CATEYE.spec para empaquetado | ✅ |
| Boot guard | Validación de entorno antes de arrancar | ✅ |
| System tray | Icono + menú contextual | ✅ |
| Autostart | Registro en autostart del sistema | ✅ |
| Updater | Actualizaciones automáticas | ✅ |
| Notificaciones desktop | Native notifications | ✅ |
| First-run wizard | Configuración inicial guiada | ✅ |
| Service mode | Ejecución en background | ✅ |
| Safe mode | Arranque degradado ante errores | ✅ |

---

## 18. API REST

| Propiedad | Valor |
|-----------|-------|
| Framework | FastAPI |
| Routers | 64 registrados en `api/routers/` |
| Middleware | 6: CORS, SecurityHeaders, CSRF, RateLimit, Auth, Error Handling |
| Documentación | OpenAPI (accesible vía /docs) |
| Autenticación | Bearer JWT + device binding |
| Rate limiting | Por identity (token) + IP fallback |

---

## 19. Frontend

| Propiedad | Valor |
|-----------|-------|
| Framework | Vue 3 + TypeScript strict |
| UI | Tailwind CSS v4 |
| Build | Vite |
| Páginas | 57 en `frontend/src/pages/` |
| Componentes | 39 en `frontend/src/components/` |
| Stores | 15 Pinia stores |
| Router | 64 rutas |
| Tests | Vitest + Vue Test Utils (17 tests) |
| PWA | manifest.json + iconos |

---

## 20. Seguridad

| Medida | Implementación | Estado |
|--------|---------------|--------|
| CSRF | Double-submit cookie middleware | ✅ |
| Security Headers | Middleware dedicado | ✅ |
| Auth | JWT propio + session store cifrado AES-256-GCM | ✅ |
| Rate limiting | Por token + IP fallback | ✅ |
| Audit log | JSONL append-only (`~/.orion/audit.jsonl`, chmod 600) | ✅ |
| Identity Vault | AES-256-GCM, clave aleatoria de 32 bytes (chmod 600) | ✅ |
| License | Ed25519 asimétrico | ✅ |
| Error handling | Mensajes genéricos al cliente, log completo al server | ✅ |
| CORS | Restrictivo (orígenes específicos en prod) | ✅ |
| OAuth2 state | Generación criptográfica de state token | ✅ |
| Sin secretos en código | API keys vía env vars o IdentityVault | ✅ |

---

## 21. Límites del Sistema

**CATEYE NO hace:**

- ❌ Enviar reportes automáticamente sin aprobación humana
- ❌ Explotar vulnerabilidades fuera del pipeline de validación
- ❌ Modificar scopes de programas
- ❌ Aceptar TOS de plataformas externas
- ❌ Comprar exploits
- ❌ Vender o compartir información
- ❌ Romper CAPTCHAs
- ❌ Evadir WAF automáticamente
- ❌ Realizar explotación destructiva
- ❌ Actuar fuera del scope definido
- ❌ Hacer pentesting ilegal
- ❌ Ejecutar acciones irreversibles sin aprobación
- ❌ Inventar findings sin evidencia
- ❌ Borrar evidencia automáticamente
- ❌ Gastar dinero (crypto/fiat) sin orden explícita del usuario
- ❌ Reemplazar el criterio humano en decisiones de reportes
- ❌ Ser multi-usuario ni SaaS
- ❌ Ser un C2 ni malware
- ❌ Aprender sin persistencia (todo aprendizaje se guarda en SQLite)

---

## 22. Extensibilidad

El diseño actual permite agregar sin modificar la arquitectura:

| Extensión | Mecanismo | Ejemplo |
|-----------|-----------|---------|
| Nueva plataforma bug bounty | Nuevo archivo en `cores/platforms/` + registro en `PLATFORM_REGISTRY` | HackerOne, Bugcrowd, etc. |
| Nueva herramienta recon | Nuevo runner en `cores/recon/` + registro en tool registry | subfinder, httpx, etc. |
| Nuevo generador de hipótesis | Nueva función en `cores/engine/hypothesis/generators.py` | 8 existentes + nuclei + tech + paths |
| Nuevo LLM provider | Nuevo provider en `cores/ai/` | Gemini, Ollama, OpenAI |
| Nueva wallet blockchain | Nueva clase extendiendo `CryptoConnector` ABC en `cores/crypto/` | BTC, EVM, SOL, TRX |
| Nueva regla de validación | Nueva clase en `cores/validation/rules.py` | `ValidationRuleSet` |
| Nuevo canal de notificación | Nueva bridge en `cores/notifications/` | email, FCM, WhatsApp |
| Nuevo agente | Nueva clase extendiendo `BaseAgent` en `cores/agents/` | Research, Validator, etc. |

---

## 23. Preguntas Frecuentes

**Q: ¿Puedo usar CATEYE sin conexión a internet?**
R: Parcialmente. El scraper y las integraciones con plataformas requieren internet. El análisis local (hipótesis, validación sin LLM) funciona offline.

**Q: ¿CATEYE envía reportes automáticamente?**
R: No. Genera borradores automáticos, pero el envío requiere acción explícita del usuario.

**Q: ¿Qué pasa si reinicio CATEYE?**
R: Targets, endpoints, findings, reports, financial state, events, y system state persisten en SQLite. Las oportunidades en RAM se pierden (deben regenerarse vía `opportunity:refresh`).

**Q: ¿Puedo agregar mi propia herramienta de recon?**
R: Sí. Creá un runner en `cores/recon/` que implemente la interfaz esperada, registralo en el tool registry.

**Q: ¿CATEYE funciona con PostgreSQL?**
R: Sí. `DATABASE_URL` soporta PostgreSQL. Por defecto usa SQLite.

**Q: ¿Puedo usar CATEYE para equipos?**
R: No. Es single-user, local-first, de escritorio.

**Q: ¿ORION puede decidir qué vulnerabilidad explotar?**
R: No. ORION solo recomienda. La decisión final es humana.

**Q: ¿Qué datos persisten?**
R: Todo lo crítico: targets, endpoints, findings, reports, financial state, eventos del bus, estado del sistema, notificaciones, audit log. Lo único volátil son las oportunidades en RAM.

---

## 24. Checklist Completo de Capacidades

### Descubrimiento
- ☑ Scrape HackerOne público
- ☑ Scrape Bugcrowd público
- ☑ Scrape Intigriti público
- ☑ Scrape YesWeHack público
- ☑ Scrape Immunefi
- ☑ Scrape arkadiyt/bounty-targets-data (6 plataformas)
- ☑ Escaneo web (security.txt, robots.txt)
- ☑ Convertir programas a Targets en DB
- ☑ Monitor automático 24h
- ☑ Discovery manual vía API
- ☑ Importación bulk
- ☑ Discovery vía scheduler

### Recon
- ☑ subfinder (subdominios)
- ☑ httpx (HTTP probing)
- ☑ katana (crawling)
- ☑ nuclei (vuln scanning)
- ☑ amass (subdominios pasivo)
- ☑ gau (URL gathering)
- ☑ ffuf (fuzzing)
- ☑ wayback (URLs históricas)
- ☑ crtsh (certificate transparency)
- ☑ whois (WHOIS lookups)
- ☑ ZAP import
- ☑ Burp import
- ☑ 3 modos: FAST, DEEP, API
- ☑ Cooldown por target (1h)
- ☑ Priorización ORION en RECON

### Hipótesis
- ☑ IDOR
- ☑ Auth bypass
- ☑ SSRF
- ☑ Privilege escalation
- ☑ Data exposure
- ☑ GraphQL
- ☑ Business logic
- ☑ File operation
- ☑ Web3
- ☑ Nuclei enrichment
- ☑ Technology-based (8 stacks)
- ☑ Discovered paths (16 rutas sospechosas)
- ☑ Scoring engine
- ☑ Memory (patrones históricos)

### Validación
- ☑ RequestReplayer (baseline vs probe)
- ☑ LLM semantic analysis
- ☑ ConfidenceScorer
- ☑ ValidationRuleSet
- ☑ ReportGate (verdict admission)
- ☑ VerdictHandler (persistencia)
- ☑ EvidenceBuilder
- ☑ FeedbackEngine
- ☑ Hardening logic

### Reportes
- ☑ Crear desde findings
- ☑ 11 estados de lifecycle
- ☑ Export Markdown
- ☑ Export HTML
- ☑ Export PDF
- ☑ Export TXT
- ☑ Versionado
- ☑ Auto-generación (finding confirmado → draft)
- ☑ Envío a plataforma
- ☑ Submission tracking
- ☑ RewardLearning feedback

### ORION
- ☑ NextAction (priorización)
- ☑ ContextEngine (contexto unificado)
- ☑ OpportunityAnalyzer (análisis de oportunidad)
- ☑ RewardLearner (aprendizaje de recompensas)
- ☑ Chat vía LLM
- ☑ Control de scheduler
- ☑ Explicación de decisiones
- ☑ EVH scoring

### Dashboard
- ☑ Health check
- ☑ System status (watchdog, pipeline, agents, recursos)
- ☑ System state + service health
- ☑ EventBus history
- ☑ Timeline de eventos
- ☑ Project dashboard
- ☑ Feature matrix
- ☑ Architecture tree
- ☑ Confidence stats
- ☑ Review queue
- ☑ Replay por target

### Wallet / Financial
- ☑ TruthLayer (single source of truth)
- ☑ 5 categorías de valor
- ☑ Withdrawal management
- ☑ Reconciliation engine
- ☑ BTC connector
- ☑ EVM (ETH) connector
- ☑ Solana connector
- ☑ Tron connector
- ☑ Exchange connector
- ☑ Sync manager
- ☑ Bank payout support
- ☑ Financial auto-sync (1800s)

### Automatización
- ☑ Scheduler 5-stage (DISCOVER→RECON→HYPOTHESIS→VALIDATE→REPORT)
- ☑ Auto-report subscriber
- ☑ Discovery Monitor 24h
- ☑ Financial Sync 1800s
- ☑ Health Monitor 8s
- ☑ System Health 30s
- ☑ Notification bridges (6 canales)
- ☑ AgentBus→EventBus bridge

### Seguridad
- ☑ CSRF middleware
- ☑ Security headers
- ☑ Bearer JWT auth
- ☑ Rate limiting
- ☑ Audit log (JSONL, chmod 600)
- ☑ Identity Vault (AES-256-GCM)
- ☑ License (Ed25519)
- ☑ Error handling (sin fuga de información)
- ☑ CORS restrictivo
- ☑ OAuth2 state
- ☑ Sin secretos en código

### Persistencia
- ☑ Targets en SQLite
- ☑ Endpoints en SQLite
- ☑ Findings en SQLite
- ☑ Reports en SQLite
- ☑ Financial state en SQLite
- ☑ EventBus history en SQLite
- ☑ System state en SQLite
- ☑ Notifications en SQLite
- ☑ Audit log en JSONL

### Desktop
- ☑ Multi-modo (browser, tray, service, safe-mode)
- ☑ PyInstaller build
- ☑ Boot guard
- ☑ System tray
- ☑ Autostart
- ☑ Updater
- ☑ Notificaciones desktop
- ☑ First-run wizard

### API
- ☑ 64 routers
- ☑ 6 middleware
- ☑ OpenAPI docs
- ☑ Paginated responses
- ☑ Filtros y ordenamiento
- ☑ CRUD principales
- ☑ Exportaciones múltiples
- ☑ Prometheus metrics

### Frontend
- ☑ 57 páginas
- ☑ 39 componentes
- ☑ 15 Pinia stores
- ☑ 64 rutas
- ☑ Tailwind v4
- ☑ PWA
- ☑ Vitest configurado

---

## 25. Casos de Uso Completos

### Caso 1: Quiero encontrar un programa nuevo con pago en crypto

```
1. Usuario: Abre CATEYE → Dashboard
2. CATEYE: ORION muestra oportunidades priorizadas
3. Usuario: POST /api/discovery/scan (o espera scheduler)
4. CATEYE: BountyScraper.scrape_all() descubre programas
5. Usuario: GET /api/discovery/programs → revisa lista
6. CATEYE: Programs con reward en crypto detectados
7. Usuario: POST /api/discovery/programs/{path}/import
8. CATEYE: Crea Target en DB, publica opportunity:found
9. Usuario: GET /api/orion/next-action → ORION recomienda target
10. CATEYE: Target agregado al ciclo del scheduler
```

### Caso 2: Quiero hacer recon completo sobre un dominio

```
1. Usuario: Navega a Targets → selecciona target
2. Usuario: POST /api/targets/{id}/scan con mode=DEEP
3. CATEYE: launch_scan() → ReconRunner.run_pipeline()
   - subfinder descubre subdominios
   - httpx hace HTTP probing
   - katana crawlea
   - wayback recopila URLs históricas
   - amass enumera (modo DEEP)
   - nuclei escanea vulnerabilidades
4. CATEYE: Normaliza resultados → Endpoints en DB
5. Usuario: GET /api/endpoints?target_id=X → revisa resultados
6. CATEYE: Publica discovery:completed
7. Usuario: Navega a AttackSurface para vista general
```

### Caso 3: Encontré un posible IDOR, ¿cómo lo valido?

```
1. CATEYE: Scheduler ejecuta HYPOTHESIS → generate_idor() sobre endpoints
2. CATEYE: Scoring + memoria de patrones
3. Usuario: GET /api/hypotheses/{target_id} → revisa hipótesis generadas
4. Usuario: POST /api/validation/validate con endpoint ID
5. CATEYE: ValidationLoopEngine.evaluate()
   - RequestReplayer compara baseline vs probe
   - LLM semantic_compare() analiza diferencias
   - ConfidenceScorer asigna score
6. CATEYE: Crea Finding + Verdict
7. Usuario: Revisa finding en UI → confirma/rechaza
8. CATEYE: finding:status_changed publicado
9. CATEYE: (si confirmado) Auto-report subscriber genera borrador
```

### Caso 4: Quiero generar un reporte listo para enviar

```
1. CATEYE: Scheduler REPORT stage o auto-report subscriber
2. CATEYE: create_report_from_findings() genera borrador
3. Usuario: GET /api/reports → lista reportes
4. Usuario: GET /api/reports/{id} → revisa contenido
5. Usuario: PUT /api/reports/{id} → edita según need
6. Usuario: GET /api/reports/{id}/export?format=markdown
7. CATEYE: Reporte en Markdown listo para copiar/pegar
8. Usuario: POST /api/reports/{id}/submit → envía a plataforma
9. CATEYE: Tracking service registra submission
```

### Caso 5: Quiero seguir el estado de un bounty hasta el pago

```
1. CATEYE: Reporte enviado → tracking activo
2. CATEYE: FinancialSyncScheduler cada 1800s sincroniza earnings
3. Usuario: GET /api/reports/{id} → estado actual (submitted→triaged→paid)
4. CATEYE: Cuando el pago llega, TruthLayer detecta el cambio
5. Usuario: GET /api/financial/state → nuevo saldo reflejado
6. CATEYE: RewardLearner.analyze() ajusta prioridades futuras
7. Usuario: GET /api/financial/ledger → historial completo
```

### Caso 6: Quiero revisar cuánto gané este mes

```
1. Usuario: Navega a FinancialTruth
2. CATEYE: GET /api/financial/state/summary
3. Usuario: Ve total por categoría (VERIFIED_REAL, PENDING, etc.)
4. Usuario: GET /api/financial/state/by-platform
5. CATEYE: Muestra earnings por plataforma (H1, BC, etc.)
6. Usuario: GET /api/financial/ledger → historial detallado
7. CATEYE: GET /api/system/confidence → estadísticas de findings/reportes
```

### Caso 7: Quiero pausar todas las automatizaciones

```
Actualmente no hay un "pause all" único. El usuario debe:
1. Scheduler: Detener vía `sched.stop()` (no expuesto en API directa)
2. Discovery Monitor: No expuesto en API
3. Financial Sync: No expuesto en API
4. Alternativa: Detener el proceso CATEYE y reiniciar en modo manual

⚠️ PARCIAL: No hay endpoint único de "pause all"
```

### Caso 8: Quiero reanudar una investigación de hace tres meses

```
1. Usuario: GET /api/targets?search= → busca el programa
2. CATEYE: Lista targets (persistidos en SQLite)
3. Usuario: GET /api/targets/{id} → detalle
4. Usuario: GET /api/endpoints?target_id=X → endpoints previos
5. Usuario: GET /api/findings?target_id=X → findings anteriores
6. Usuario: GET /api/reports?search= → reportes generados
7. Usuario: GET /api/system/replay/{target_id} → historial completo
8. Usuario: POST /api/targets/{id}/scan → re-ejecuta recon
9. CATEYE: Nuevos endpoints + hipótesis + validación
```

---

*Documento generado desde código verificado — Julio 2026.*
*CATEYE v4.6.0 | Architecture v4.6 STABLE*
*Única fuente de verdad sobre capacidades reales del sistema.*
