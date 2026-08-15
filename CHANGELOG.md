# Changelog

All notable changes to OWNEX, tracked from the git history of the default branch.

## [Unreleased]

### Added
- **Outlook Calendar Sync** — two-way integration with Microsoft Graph:
  - `update_calendar_event` / `delete_calendar_event` added to `OutlookConnector`
  - `cores/integrations/outlook/sync.py`: push local tasks (con `due_date`) al calendario, agenda pull (eventos + no leídos)
  - Canal de notificación `outlook` en `NotificationHub` (email vía Graph, requiere `CATEYE_OUTLOOK_NOTIFICATION_TO`)
  - API: `GET /api/outlook/status`, `GET /api/outlook/agenda`, `POST /api/outlook/sync`, `GET /api/outlook/tasks`
  - `Task` model: `due_date`, `calendar_event_id`, `synced_to_calendar`, `last_synced_at` (+ migración automática)
  - Job de scheduler `outlook_calendar_sync` (cada 15 min, ciclo `integrations`)
  - Frontend: página `OutlookCalendar.vue` en Integraciones (`/integrations/outlook`)
- **Microsoft To Do** — tasks locales también se materializan en To Do:
  - `OutlookConnector`: `list_todo_lists`, `get_or_create_todo_list`, `list_todo_tasks`, `create_todo_task`, `update_todo_task`, `delete_todo_task` (Graph `/me/todo/lists`, permiso `Tasks.ReadWrite`)
  - `sync_tasks_to_todo()`: crea/actualiza en la lista `OWNEX` (autocreada); borra al completar la task
  - `pull_todo_lists()`: lists + tasks para la UI; `Task` model: `todo_task_id`, `synced_to_todo`
  - API: `GET /api/outlook/todo`; `POST /api/outlook/sync` ahora devuelve resumen de calendario + To Do
  - Frontend: sección Microsoft To Do (lists + tasks) en `OutlookCalendar.vue`

## [7.0.0] — 2026-08-01

### Added
- **7 Work Cycles operational**: Security, Forge, Pulse, Vault, Atlas, Direct Work, QA — 28 scheduled jobs
- **Direct Work Engine**: zero-barrier scoring (0-100 spectrum), IntelligentRecommender, Work Bank (autonomous preparation of ready-to-deliver jobs), Daily Companion, Evolution layer, Fast Income Mode
- **OAR AI Runtime** (`cores/ai/runtime`): provider registry, smart routing by task type, cost tracker with daily USD budget, failover circuit breakers, semantic cache — API mounted (`/oar/*`, `/career/*`)
- **Security pipeline E2E**: `run_pipeline()` connecting 7 stage executors (recon → attack_surface → hypothesis → validation → evidence → report → learning)
- **Executive Dashboard** backend + frontend (CEO view, weekly verdict)
- **Brand identity v3 — "The Aperture Nexus"**: deterministic vector pipeline (`scripts/brand/`), design tokens SSOT
- **Desktop release**: Tauri v2 `OWNEX OMEGA 7.0.0` (deb/rpm/AppImage), Android namespace unified `ai.rastro.app`
- Career Engine, Guided Assistance System (4 modes), Magic Experience Engine, income dashboard

### Fixed
- Scheduler runtime wiring (AUD-1): 26+ jobs now execute their handlers
- Knowledge capture persistence via UnifiedMemoryStore (SQLite)
- Lint cleanup: 117 → 0 errors (AUD-9)
- Cycle config parsing: `/api/cycles` 500 → 200
- Version backup tests 13 failing → 24/24 (AUD-5)

### Removed / Discarded
- Wear OS native (AUD-14): negative ROI, redundant with mobile companion

## [3.0.0] — 2026-07-08

### Added
- Release hardening: 12 fixes from prolonged-use audit
- Validation + Learning + Evolution + Knowledge Graph (v6 engine wave, 2026-07-29)
- Execution Pipeline: Plan → Prepare → Execute (v6 wave)
- OMEGA (Expo/React Native) mobile skeleton

### Fixed
- 12 prolonged-use audit fixes
- 359 tests green, dead code archived

## [1.0.0] — 2026-06-29

### Added
- Rastro baseline: bug bounty discovery → recon → hypothesis → validation → report pipeline
- OS infrastructure, desktop packaging, one-command launcher

## [0.2.0] — pre-release

### Added
- os-ui wave (tag `v0.2-os-ui`)

## [0.1.0] — pre-release

### Added
- Initial alpha (tag `v0.1-alpha`)
