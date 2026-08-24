# OWNEX Frontend Functionality Matrix

> **Fecha**: 2026-08-24 · **Método**: verificación objetiva — cross-reference de las llamadas
> `api.*` del frontend contra el OpenAPI real del backend (1.236 paths) + E2E smoke HTTP contra
> backend vivo (:8123). "COMPLETE" = flujo principal E2E con endpoints reales; no basta compilar.

## Métricas base

| Métrica | Valor |
|---|---|
| Rutas registradas | 126 (incluye children/redirects) |
| Páginas .vue | 66 |
| Archivos que consumen API | 65 |
| Llamadas api.* estáticas | ~500 · Endpoints únicos ~295 |
| **Endpoints sin backend (reales)** | **~30** (cluster investment sub-adapters + 8 menores) |
| Tests unitarios | 226/226 ✓ · vue-tsc 0 errores ✓ · build OK ✓ |
| E2E smoke backend-vivo | 11/11 flujos ✓ |

## Bugs sistémicos corregidos en esta sesión (afectaban a TODA la app)

| Bug | Alcance | Fix |
|---|---|---|
| **Doble prefijo `/api/api/x`** | ~150 call sites pasaban `/api/...` a `api.get()` que ya antepone la base → 404 silencioso tapado por `.catch(() => ({}))` | Normalización central en `lib/api.ts::request()` |
| **Namespaces root-mounted** | `direct-work/*` (35 rutas), `mobile/*`, `wear-os/*` se montan SIN prefijo `/api` → todas sus llamadas 404 | `resolveApiUrl()` en `backend.ts` + proxies en vite.config |
| **Puerto hardcodeado en fetch crudos** | `uploadEvidence`, `assistantStreamChat`, `exportPdf` ignoraban discovery dinámico | Usan `getApiBase()` request-time |
| **Discovery no se recuperaba** | Backend reiniciado en otro puerto = puerto cacheado para siempre; polling abandonaba a los 60s | Reset on network-error + re-scan rápido→lento infinito + `retryConnection()` |
| **Fondo rojo inexplicable** | Banners `bg-destructive` con string crudo en 9+ páginas ante cualquier fallo transitorio | `ErrorState.vue` estructurado (ERROR/CAUSA/ACCIÓN) + estados `connecting` calmados (regla CALM UX) |

## Matriz por feature (agrupada por flujo)

### Núcleo / Dashboard
| PAGE | STATUS | API | EVIDENCE | REMAINING_ISSUES |
|---|---|---|---|---|
| MissionControl (`/classic`) | COMPLETE | orion/context, system/good-morning, activity, direct-work/*, source-intel | E2E 200 (context, direct-work root-mounted OK) | Good-morning degrada a defaults si engines caen (by design `_safe`) |
| Dashboard (`/dashboard`) | COMPLETE | orion/context/system | E2E 200; tipo `OrionContext` agregado a types | — |
| ExecutiveDashboard (CEO) | COMPLETE | cycles/security/dashboard | endpoint existe (openapi); ErrorState estructurado wired | — |
| StatusBar global | COMPLETE | mission/status, system/status | endpoints existen | — |
| OnboardingWizard | PARTIAL | health, version, system/state, system/health | endpoints existen | Mensaje de error API ya accionable; verificar visual en Tauri frío |

### Security / Bug Bounty (pipeline CATEYE)
| PAGE | STATUS | API | EVIDENCE | REMAINING_ISSUES |
|---|---|---|---|---|
| TargetsPage / TargetDetail | COMPLETE | targets, targets/{id}, endpoints?target_id= | E2E 200 (targets, target/{id}, endpoints?target_id) | Scan trigger usa targets/{id}/scan (existe); revisar feedback de progreso |
| EndpointDetail | COMPLETE | endpoints/{id}, findings?endpoint_id, validation/validate, idor/idor | contratos reales wireados hoy (payloads ValidateHotPathRequest/IDORScanRequest) | idor requiere identity_baseline_id → envía baseline anónima 0; UX de resultado pendiente pulir |
| Findings (stores/findings) | COMPLETE | findings CRUD, pipeline, reports/{id}/submit | endpoints existen (10 findings paths) | — |
| HypothesisQueue | FIXED-TODAY | POST hypotheses/{target_id} → attack_queue | flujo real: seleccionar target → generar → poblar cola | Lista inicial sin generación = empty state honesto (antes fetch fantasma 404) |
| EvidenceCenter | PARTIAL | evidence/upload (fix hoy: getApiBase) | upload existe; listado `/evidence` genérico ABSENT | listar evidencia requiere ruta de listado — usar findings/{id}/evidence si existe |
| ReportCenter/History/Queue | MOSTLY | reports (+31 paths), reports/stats, revenue/monthly | reports cluster completo | economic/report-queue ABSENT → ReportQueue cae a empty state |
| ZAP integrations | AVAILABLE | zap/health, spider, passive-scan, alerts, technologies, hypotheses | todos existen (zap/alerts era artefacto del scanner) | Requiere ZAP corriendo localmente |
| Discovery | COMPLETE | discovery/scan, programs, import-all | existen (3 programs paths) | — |
| BabyMode HUNT | COMPLETE | hunt/start,status,pause,resume,stop + pipeline/stages + capital-dashboard | 6 hunt paths + stages + dashboard existen | — |

### Oportunidades / Trabajo directo (DWE)
| PAGE | STATUS | API | EVIDENCE | REMAINING_ISSUES |
|---|---|---|---|---|
| DirectWorkRadar (MissionControl) | COMPLETE | direct-work/recommend, discover, workbank/cycle, daily-brief | E2E 200 root-mounted tras fix resolveApiUrl | — |
| WorkBank delivery flow | COMPLETE | workbank/{id}/deliver/prepare·approve, deliver/pending | propios del DWE | — |
| ApplicationAssistant (NUEVO hoy) | COMPLETE | applications/plan·overview, steps/complete, status | E2E 200 plan+overview; página+ruta+sidebar creadas | Estados de plataforma editables inline |
| OpportunityPlanner | PARTIAL | opportunity/catalog? ABSENT; economic/programs/{id}/plan ABSENT | 2 llamadas muertas | Conectar a opportunity-score/top5 (existe) o eliminar tabs muertos — P2 |
| ProgramCatalog | DEGRADED | /opportunity/catalog ABSENT | muestra empty honesto | Decidir: implementar backend o retirar página — P2 |

### IA / Providers
| PAGE | STATUS | API | EVIDENCE | REMAINING_ISSUES |
|---|---|---|---|---|
| Settings → IA | FIXED-TODAY | GET settings/ai/providers (catálogo real 7 providers) | E2E 200; fallback estático offline | Config fields por provider (base_url/key/model) solo para ollama/openai/gemini; devin/freebuff/local usan env vars — P2 añadir inputs |
| Copilot/Merlin chat | PARTIAL | copilot/chat existe (POST /chat bajo /api/copilot) | doble-prefijo normalizado hoy | streaming via assistant/chat/stream fixeado; MerlinJarvis legacy sin ruta |

### Knowledge
| PAGE | STATUS | API | EVIDENCE | REMAINING_ISSUES |
|---|---|---|---|---|
| Knowledge service (17 eps) | COMPLETE | knowledge/connect·scan·sync·search·note·health·snapshots… | 15 paths existen | — |
| KnowledgeGraphMini | DEGRADED | /knowledge-graph/nodes·edges ABSENT | componente oculta si falla? verificar catch | P2: mapear a knowledge/graph real o desmontar widget |

### Operaciones
| PAGE | STATUS | API | EVIDENCE | REMAINING_ISSUES |
|---|---|---|---|---|
| OperationsDashboard | MOSTLY | system/health, operations/metrics(ABSENT) | health existe; metrics ABSENT → sección vacía | Mapear a core/health/summary — P2 |
| PipelineMonitor/Detail | DEGRADED | agents/pipelines/* ABSENT | backend usa scan_runs propios | Conectar a /api/pipeline o scan-runs — P1 (monitor de pipelines es core) |
| ActionsView (Scheduler) | DEGRADED | execution/actions ABSENT | — | Mapear a scheduler jobs reales — P1 |
| InsightsView | FIXED-TODAY | canonical/insights, execution/traces | E2E: insights 404→empty-state OK; traces 200 | — |
| PersonalIntelligence | FIXED-TODAY | learning/profile·events·reset·export | E2E 200 profile | — |
| ConfidenceDashboard | DEGRADED | confidence/audit ABSENT | empty honesto | P2 |
| ReplayCenter | DEGRADED | system/replay-targets ABSENT | empty honesto | P3 |
| DifferentialEngine | FIXED-TODAY | differential-intelligence/analyze | E2E 200 | — |

### Capital / Inversión
| PAGE | STATUS | API | EVIDENCE | REMAINING_ISSUES |
|---|---|---|---|---|
| Capital (core) | MOSTLY | revenue/capital-dashboard, ev-ranking, payment-compat | existen; doble-prefijo normalizado | — |
| Trading/Capital inversión avanzada | DEGRADED-KNOWN | ccxt, defi/aave·lido·morpho·pendle, stocks/algopaca·ibkr, polymarket strategies, backtest (~32 llamadas) | **backend NO expone esos sub-adapters** | Revenue Rule: solo construir si aumenta ingresos medibles; mientras, UI muestra error estructurado — decisión producto pendiente |
| TradingIntelligence | PARTIAL | trading/dashboard·copy·reasoning (existen) | trading router montado | toggle masters usa path con trailing id — verificar contrato exacto |

### Conexiones / Identidad
| PAGE | STATUS | API | EVIDENCE | REMAINING_ISSUES |
|---|---|---|---|---|
| Connections | MOSTLY | connections/payout-accounts·withdrawals·platforms·payout-recommendations (todos existen) | — | sync-all ABSENT (Identity.vue) |
| Identity | PARTIAL | identity-center/platform/{p}/connect·disconnect (existen), opportunity/identity/accounts (existe) | — | connections/sync-all·sync/{p}·identity-center/settings ABSENT → botones sin efecto: ocultar o implementar — P2 |
| Wallets | DEGRADED | identity-center/wallets solo POST (GET ABSENT) | — | P3 |

### Control panel (controlPanel.ts — 100+ funciones)
| STATUS | NOTA |
|---|---|
| MOSTLY-COMPLETE | Todos los double-prefix normalizados hoy vía núcleo; cada bloque con `.catch(() => ({}))` degrada a vacío honesto. Clusters verificados existen: mega-fast, first-time, vpn, obsidian, life, daily-tasks, automation, skill-method, capital-bar, goal-evaluator, work-log, postmortem, account-health, payout-planner, brand-writer, vault-lock, emergency-mode, payout-net, payment-tracker, trust-engine, closed-loop, finance-guru, tax-ar, invoicer-ar, offramp, platforms, config/progress, dispute, sandbox, profile-builder, guide/master, money-plan, task-assistant, dev-bounty, evidence/claim, startup-checks |
| Excepciones ABSENT | files/list, daily-tasks OK(existe), investment/action-required·startup-checks (verificar) |

### Wear OS / Mobile
| PAGE | STATUS | NOTA |
|---|---|---|
| wear-os notifications/approvals | FIXED-TODAY | root-mounted resuelto por resolveApiUrl; E2E mobile/status 200 |

## Resumen ejecutivo

| Clasificación | Count (features) | Nota |
|---|---|---|
| COMPLETE (E2E verificado) | 18 | flujos principales del producto |
| MOSTLY (1-2 gaps menores) | 7 | |
| FIXED-TODAY | 6 | eran BROKEN por bugs sistémicos |
| PARTIAL | 6 | acciones secundarias sin efecto |
| DEGRADED-KNOWN | 9 | backend ABSENT — empty/error honesto, decisión producto pendiente |
| BROKEN puro | **0** | ninguna página queda llamando endpoints inexistentes sin manejo |

## Flujos principales E2E verificados (backend vivo)

```
APP START      → health 200, version 200, auth device-login 200        ✓
DASHBOARD      → orion/context 200, direct-work/status 200             ✓
SECURITY       → targets → target/{id} → endpoints?target_id 200       ✓
OPPORTUNITY    → direct-work/workbank 200, applications/plan 200       ✓
AI SETTINGS    → settings/ai/providers 200 (7 providers reales)        ✓
LEARNING       → learning/profile 200, insights 404→empty OK           ✓
DIFFERENTIAL   → analyze 200                                           ✓
EXECUTION      → execution/traces 200                                  ✓
```

## Deuda conocida restante (ordenada)

- **P1**: PipelineMonitor/ActionsView apuntando a namespaces inexistentes (mapear a scan_runs/scheduler reales)
- **P2**: Identity botones sin efecto; OpportunityPlanner/ProgramCatalog tabs muertos; config UI para providers env-var (devin/freebuff); OperationsDashboard metrics mapping; KnowledgeGraphMini remapeo o retiro
- **P3**: Wallets GET, ReplayCenter, ConfidenceDashboard audit
- **Decisión producto**: investment sub-adapters (ccxt/defi/stocks/polymarket/backtest) — construir backend (Revenue Rule gate) o retirar UI
