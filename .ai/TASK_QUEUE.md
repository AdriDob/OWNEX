# Task Queue — Tareas Pendientes

> **FILTRO PREVIO**: toda tarea debe responder: ¿aumenta la probabilidad de encontrar una vulnerabilidad válida, demostrarla mejor o conseguir que el reporte sea aceptado? Si la respuesta es no, su prioridad es baja.
>
> **ESTRATEGIA**: Revenue Ready primero. Offensive Intelligence > Evidence > Acceptance > Hunting Loops > Revenue Analytics > Documentation > Companion > Installer.
>
> **SIMPLIFICACIONES COMPLETADAS**: AppRegistry + ExtensionRegistry unificados vía `core/plugin/discovery.py`. Journal → EventStore persistencia. SecretsManager single Vault path. Revenue Pipeline completo con 31 tests. FULL RUFF CLEAN. 1386 tests pasan.

## PRIORIDAD MÁXIMA — Revenue Ready (Q3 2026)

### 0. Revenue Pipeline ✅ COMPLETED — Julio 2026
- **Qué**: Finding → Evidence → Report → Platform → Payout. `RevenuePipeline` orchestrator with `submit_report()`, `check_submission_status()`, `sync_platform_payouts()`, `record_payout()`, `revenue_summary()`, `list_submissions()`. 6 API endpoints. 6 revenue events. 5 capabilities. 31 tests, Ruff clean.
- **Archivos**: `core/revenue/pipeline.py`, `api/routers/revenue.py`, `database/models_economic.py` (2 new models), `core/events/types.py` (6 new events), `api/main.py` (router registration)
- **Impacto**: Cierra el ciclo de revenue conectando todos los componentes existentes (platforms, models, ledger, events)

## PRIORIDAD MÁXIMA — Revenue Ready (Q3 2026)

### 1. Offensive Intelligence Engine ✅ COMPLETED — Julio 2026
- **Qué**: IDOR, SSRF, XSS, SQLi, Auth Bypass reasoners. Planner, Curiosity Engine, Relationship Graph, ContradictionEngine, Triager, Templates, Publisher. 8 API endpoints. 101 tests.
- **Archivos**: `core/offensive/`, `api/routers/offensive.py`
- **Impacto**: Aumenta directamente detección de vulnerabilidades.

### 2. Evidence Engine ✅ COMPLETED — Julio 2026
- **Qué**: PoC, requests, responses, curl, Python exploit, timeline, CVSS, CWE, CAPEC, OWASP, MITRE, report readiness score. 37 tests.
- **Archivos**: `core/evidence/composer.py`
- **Impacto**: Aumenta tasa de aceptación de reportes.

### 3. Report Acceptance Optimizer
- **Qué**: Aprende de Hacktivity/HackerOne/Bugcrowd/Intigriti qué hace que un reporte sea aceptado vs rechazado. Adapta estilo automáticamente.
- **Impacto**: Aumenta directamente revenue.
- **Dependencias**: Knowledge Graph, COPILOT.
- **Criterio**: Reportes generados tienen probabilidad de aceptación estimada + aprenden de outcomes.
- **Estado**: Base implementada (Quality Gate), falta aprendizaje de outcomes reales.

### 4. Recon Intelligence
- **Qué**: Subfinder → Katana → Wayback → Knowledge Graph → COPILOT → "Este endpoint tiene patrón IDOR" → Prioridad → PoC → Evidence → Report.
- **Impacto**: Pipeline completo de descubrimiento a reporte.
- **Dependencias**: Execution Platform, Offensive Intelligence, Evidence Engine.
- **Criterio**: Pipeline corre end-to-end sin intervención humana.

### 5. Revenue Analytics
- **Qué**: El dinero como entidad de primer nivel. Expected Revenue por target/vuln/programa. ROI tracking. Estrategia basada en datos reales.
- **Impacto**: Prioriza el trabajo más rentable.
- **Dependencias**: Knowledge Graph, Financial Layer.
- **Criterio**: ORION puede responder "¿qué estrategia generó más revenue en los últimos 6 meses?".

## PRIORIDAD MEDIA — Platform Hardening

### 6. Configuration Wizard v2 (SETUP CENTER)
- **Estado**: ✅ COMPLETED — Julio 2026
- **Qué**: Wizard extensible (6 pasos), persistente en disco, metadata-driven, API endpoints para go-back/skip/reset/steps. 14 tests, Ruff clean.
- **Archivos**: `core/setup/` (refactorizado), `core/api/routers.py` (nuevos endpoints)

### 7. Documentation Platform
- **Qué**: Generación automática de 13 documentos desde metadatos del sistema (introspect, wizard, capabilities, events, API).
- **Estado**: ⏸ Pausada — pospuesta post Revenue Ready.
- **Base existente**: `core/documentation/` con models, registrar, introspect (18 módulos auto-registrados).

### 8. ORION Companion (Android)
- **Qué**: App Kotlin + Jetpack Compose. Dashboard, COPILOT, approvals, notificaciones.
- **Estado**: ⏸ Pausada — pospuesta post Revenue Ready.

### 9. ORION Watch (Wear OS)
- **Qué**: Extension del Companion. Alertas críticas, estado del sistema, approvals rápidas.
- **Estado**: ⏸ Pausada — pospuesta post Revenue Ready.

### 10. Command System Fase 1 ✅ COMPLETED — Julio 2026
- **Qué**: Command Registry (107 commands, 14 categories, 5 permission levels). Permission Validator with COPILOT authority levels. EventBus publishing (command:executed/failed/rejected). Execution history. CapabilityRegistry integration. 6 API endpoints. 45 tests, Ruff clean.
- **Archivos**: `core/commands/` (models, registry, dispatcher), `api/routers/commands.py`, `core/events/types.py`
- **Impacto**: ORION now has a runtime operational language. COPILOT, Companion, and dashboard can execute 107 commands with permission validation.

### 11. Desktop Installer
- **Qué**: Instalador Windows con auto-update, repair, backup, diagnóstico.
- **Estado**: ⏸ Pausada — pospuesta post Revenue Ready.
