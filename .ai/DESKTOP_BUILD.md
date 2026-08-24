# DESKTOP BUILD — OWNEX Alpha

## Product Name

**OWNEX Alpha** is the official name of the desktop application.

| Context | Name | Notes |
|---------|------|-------|
| User-visible (window, installer, Start Menu) | `OWNEX Alpha` | Branding |
| Tauri `productName` | `OWNEX Alpha` | Controls MSI/exe name |
| Tauri `identifier` | `ai.orion.alpha.desktop` | Technical |
| Cargo `package.name` | `orion_desktop` | Technical, keep for compat |
| npm `package.name` | `ownex-omega` | Technical, keep for workspaces |

**RULE:** `OMEGA`, `ORION`, `orion_desktop` are INTERNAL identifiers. They must NOT appear as user-visible branding. Only `OWNEX Alpha` is visible to the user.

## Architecture

```text
OWNEX Alpha
│
├── Tauri 2 (Rust)
│   ├── Window + WebView
│   ├── System tray
│   ├── Backend lifecycle (spawn, health check, shutdown)
│   └── MSI/NSIS packaging
│
├── Vue 3 (TypeScript)
│   └── frontend/dist/ (static assets served by Tauri)
│
└── FastAPI (Python → PyInstaller → ownex-backend.exe)
    └── Sidecar: externalBin in tauri.conf.json
```

## Build Strategy

### Sidecar (Backend)

- **Strategy:** `externalBin` (Tauri sidecar)
- **Spec:** `OWNEX-Backend.spec`
- **Entrypoint:** `src-tauri/binaries/start_backend.py`
- **CLI args:** `--port`, `--host`, `--data-dir`, `--log-level`
- **Output:** `dist/ownex-backend/ownex-backend.exe`
- **Tauri naming:** `src-tauri/binaries/ownex-backend-{target-triple}[.exe]`

### Frontend

- **Strategy:** `frontendDist` in tauri.conf.json
- **Build:** `cd frontend && npm run build`
- **Output:** `frontend/dist/`
- **URL:** `index.html` (Tauri serves from dist)

### Dynamic Port

- Rust scans ports 8000-8099 via `TcpListener::bind`
- Backend receives `--port` arg
- Tauri emits `backend-ready` event with port
- Frontend listens and updates `API_BASE` dynamically

## CI Pipeline

`.github/workflows/ownex-tauri-windows.yml`:
1. Node.js → `npm ci`
2. Python → PyInstaller → sidecar
3. Copy sidecar to `src-tauri/binaries/`
4. Rust → `npx tauri build`
5. Upload MSI/NSIS artifacts

## Data Directory

- **Windows:** `%LOCALAPPDATA%\OWNEX`
- **Linux:** `~/.local/share/OWNEX`

Contents: `database/`, `logs/`, config files.

## Legacy Files (DO NOT DELETE)

| File | Status | Notes |
|------|--------|-------|
| `OWNEX-Desktop-Alpha.spec` | LEGACY | PySide6 build, superseded |
| `CATEYE.spec` | LEGACY | Old name |
| `ORION.spec` | LEGACY | Old name |
| `desktop/native/` | LEGACY | PySide6 desktop, superseded by Tauri |
| `installer/OWNEX-Desktop-Alpha.nsi` | LEGACY | NSIS installer, superseded |

## Artifact Verification (2026-08-24)

Canonical artifacts are ONLY produced by `ownex-tauri-windows.yml` (tags `v*`).
The pipeline proves sidecar inclusion by construction — no byte-probing needed:

1. **Size guard**: sidecar exe must be ≥ 50 MB (ONEFILE self-contained;
   the broken 19.91 MB stub of 2026-08-24 cannot pass).
2. **Runtime smoke**: the built sidecar is spawned on :8199 and must answer
   `/api/health` within ~90 s, else the release is blocked BEFORE packaging.
3. Only then: `npx tauri build` → MSI + NSIS.

### Current verified artifacts (local, `ownexinstalador/windows/checksums.txt`)

| Artifact | SHA256 |
|---|---|
| `OWNEX Alpha_7.0.0_x64_es-ES.msi` (27.5 MB) | `7a7e215dae1813b84779788ee700a8616672159fb9b5aa519882dc2d2e4cda5f` |
| `OWNEX Alpha_7.0.0_x64-setup.exe` (25.7 MB) | `9833315e4a6ab892066864bd4e49b13cb5a808622c311600b739368661646e86` |

Provenance: CI run post-`ff747816`. MSI branding probe: `OWNEX Alpha` ×15,
`OWNEX OMEGA` ×0. **Pending: real-Windows validation** (install → auto-start
backend → health → Vue local → persistence → shutdown → relaunch) per
WINDOWS_SUCCESS_CRITERIA before declaring Gen3 done and retiring Gen2.
