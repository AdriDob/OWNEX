# DEPENDENCY MAP — OWNEX (2026-09-30)

## Layer Dependencies (Allowed → Violation)

```
DESKTOP (Tauri v2)
    │
    ├── Frontend (Vue 3) ──► API Client (lib/api.ts) ──► HTTP/WS ──► BACKEND (FastAPI)
    │
    ├── Backend Sidecar (PyInstaller ONEFILE)
    │
    └── Frontend (dist) ──► Static Server (spa-server.cjs) ──► HTTP/WS ──► BACKEND
```

## Critical Dependency Violations

| From | To | Count | Type |
|------|-----|-------|------|
| `cores/` | `api/` | 14 | **Inversion** (layering) |
| `api/` | `desktop/` | 2 | Module access |
| `desktop/` | `cores/` | 2 | Acceptable |
| `apps/` | `cores/` | 46 | Acceptable |
| `apps/` | `api/` | 4 | Acceptable |
| `api/` | `apps/` | 0 | Clean |
| `cores/` → `api/` (inverted) | 14 imports | CRITICAL |

### Inverted Imports Detail (`cores/` → `api/`)

| File:Line | Import |
|-----------|--------|
| `cores/agenda/__init__.py:95` | `from api.routers.mission_hub import _load_state` |
| `cores/ai/tools.py:166` | `from api.services.data_service import get_pipeline_stages` |
| `cores/automation/kill_scale.py:186` | `from api.routers.mission_hub import _load_state, _save_state` |
| `cores/ai/tools.py:166` | `from api.services.data_service import get_pipeline_stages` |
| `cores/copilot/orion_context.py:132` | `from api.scheduler import get_scheduler_status` |
| `cores/direct_work_engine/autonomous_discovery.py:1256` | `from api.routers.direct_work import get_engine` |
| `cores/direct_work_engine/workbank.py:655` | `from api.adapters.legacy import build_default_adapters` |
| `cores/direct_work_engine/workbank.py:670` | `from api.adapters.direct_work_bugbounty import BugBountyDweAdapter` |
| `cores/health/checks.py:31` | `from api.scheduler import scheduler_instance` |
| `cores/notifications/telegram/handlers.py:82,110` | `from api.main import app` |
| `cores/operations.py:605` | `from api.main import app` |
| `cores/direct_work_engine/autonomous_discovery.py:1256` | `from api.routers.direct_work import get_engine` |
| `cores/copilot/orion_context.py:132` | `from api.scheduler import get_scheduler_status` |
| `cores/recovery/engine.py:302` | `from api.scheduler import scheduler_instance` |
| `cores/solver/solver.py:227` | `from api.routers import copilot` |

---

## Backend Internal Dependencies

### Router Classification (198 routers)

| Class | Count | Criteria |
|-------|-------|----------|
| Direct DB access | 44 | `database` import / `SessionLocal` / `.query()` / `db.add()` / `commit()` |
| Business logic inline | 25 | ≥2 private helpers, no direct DB |
| Thin transport | 129 | 0 direct DB, <2 private helpers |

**Direct-DB routers (44)**: `alerts, atlas_app, attack, auth_user, auth_users, auto_submit, command_center, connections, copilot, cycles, daily, daily_digest, differential_intelligence, discovery, economic, findings, forge_app, help_center, hunter, hypotheses, idor, investigations, mission_hub, mobile, mobile_approvals, notifications, observation, operations, outlook, overview, pulse_app, quick_wins, report_pipeline, reports, reports_acceptance, reports_quality, roi, scans, screenshots, settings_unified, targets, validation, vault_app, version_backup`

### API → Core Dependencies

| API Module | Cores Packages Imported | Count |
|------------|------------------------|-------|
| `api/routers/control.py` | 42 cores packages | Highest coupling |
| `api/routers/direct_work.py` | 44 | Highest |
| `api/routers/copilot.py` | 15 | |
| `api/routers/copilot.py` | 15 | |
| `api/routers/economic.py` | 12 | |

---

## Frontend Dependencies

### Import Graph (Key Paths)

```
frontend/src/main.ts
    ├── App.vue
    │   ├── router (97 routes)
    │   ├── stores (9 pinia)
    │   ├── components (128)
    │   ├── composables (21)
    │   ├── services (6)
    │   └── lib/
    │       ├── api.ts (70 importers)
    │       ├── backend.ts (6 importers)
    │       ├── offline.ts (0 importers - DEAD)
    │       └── utils.ts (19 importers)
```

### Frontend → Backend Contract

| Layer | Mechanism |
|-------|-----------|
| API Client | `lib/api.ts` (70 importers) |
| URL Resolution | `lib/backend.ts` (ROOT_MOUNTED_PREFIXES, Tauri detection) |
| Auth | `stores/auth.ts` + `lib/api.ts` (Bearer + cookie) |
| WebSocket | `lib/backend.ts:wsUrl()` + `stores/notifications.ts` |
| Types | Hand-written in `services/ownexData.ts` (149 types, 0 codegen) |

---

## Desktop Dependencies

```
desktop/
├── src-tauri/
│   ├── Cargo.toml (tauri v2, tauri-plugin-shell)
│   ├── src/lib.rs (sidecar spawn, port discovery)
│   └── binaries/ (sidecar binaries)
└── native/ (PySide6 legacy, 888 LOC)
```

**Sidecar Resolution**: Tauri resolves sidecar via `app.shell().sidecar("ownex-backend")` → resolves to `binaries/ownex-backend-<target-triple>` (Linux) or `ownex-backend.exe` (Windows).

**Critical**: Sidecar binary must match target triple exactly. Current bug: `ownex-backend-x86_64-unknown-linux-gnu` (ONEDIR, broken) vs `ownex-backend` (ONEFILE, works). Fixed by copying ONEFILE to target-triple name.

---

## External Service Dependencies

| Service | Protocol | Auth | Used By |
|---------|----------|------|---------|
| HackerOne | REST + GraphQL | Bearer token | `adapters/security/hackerone.py` |
| Bugcrowd | REST | API key | `adapters/security/bugcrowd.py` |
| Intigriti | REST | API key | `adapters/security/intigriti.py` |
| GitHub | REST + GraphQL | PAT | `adapters/direct_work_github.py` |
| GitLab | REST | Token | `adapters/gitlab.py` |
| BugBountyHQ | REST | API key | `adapters/direct_work_bugbounty.py` |
| Algora | REST | Bearer | `adapters/direct_work_algora.py` |
| Opire | REST | Bearer | `adapters/direct_work_opire.py` |
| GitHub API | GraphQL | PAT | `cores/opportunity/executors/github_executor.py` |
| OpenAI | REST | Bearer | `cores/ai/` |
| Anthropic | REST | Bearer | `cores/ai/` |
| FCC Proxy | HTTP | Local | `cores/ai/providers/` |
| MPT (Money Printer) | HTTP | Local | `services/moneyprinter.ts` |

---

## Build Dependencies

### Frontend
```json
{
  "dependencies": { "vue": "^3.5.13", "pinia": "^3.0.4", "vue-router": "^4.5.1", "axios": "^1.19.0" },
  "devDependencies": { "vite": "^6.3.5", "vitest": "^4.1.9", "playwright": "^1.62.1", "vue-tsc": "^2.2.12" }
}
```

### Backend (Python)
```toml
# pyproject.toml key deps
fastapi, uvicorn, sqlalchemy, alembic, httpx, pydantic, python-jose, passlib, cryptography
aiohttp (MISSING - causes run_autonomous_research_cycle failure)
playwright (for testing)
```

### Desktop (Rust)
```toml
[dependencies]
tauri = { version = "2", features = ["tray-icon"] }
tauri-plugin-shell = "2"
tauri-plugin-dialog = "2"
tauri-plugin-notification = "2"
tauri-plugin-fs = "2"
tauri-plugin-process = "2"
tauri-plugin-http = "2"
serde = { version = "1", features = ["derive"] }
serde_json = "1"
reqwest = { version = "0.12", features = ["json", "rustls-tls", "blocking"] }
tokio = { version = "1", features = ["full"] }
```

### Build Commands
```bash
# Frontend
cd frontend && npm run build          # → frontend/dist/

# Desktop (Linux)
cd src-tauri && cargo build --release  # → target/release/orion_desktop

# Sidecar (Python)
pyinstaller OWNEX-Backend.spec --distpath dist-pyinstaller --workpath /tmp/pyi-work --noconfirm
```

---

## Critical Dependency Risks

| Risk | Impact | Location |
|------|--------|----------|
| `aiohttp` missing | `run_autonomous_research_cycle` handler fails | `cores/direct_work_engine/autonomous_discovery.py:19` |
| `aiohttp` not in pyproject.toml | Sidecar build may miss it | `pyproject.toml` |
| `core/` (singular) missing | `graft` skills confused | `ls -d core` → not found |
| `aiohttp` not in pyproject.toml | Sidecar build may miss it | `pyproject.toml` |
| Sidecar binary stale | 26 backend commits behind | `src-tauri/binaries/ownex-backend` (Sep 5) vs HEAD |
| Display env missing | Tauri window won't open | `DISPLAY=:0` required |
| WebKit compositor issues | WebView rendering glitches | `WEBKIT_DISABLE_COMPOSITING_MODE=1` required |