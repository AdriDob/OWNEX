# DESKTOP BUILD — OWNEX Alpha

## Product Name

**OWNEX Alpha** is the official name of the desktop application.

| Context | Name | Notes |
|---------|------|-------|
| User-visible (window, installer, Start Menu) | `OWNEX Alpha` | Branding |
| Tauri `productName` | `OWNEX Alpha` | Controls MSI/exe name |
| Tauri `identifier` | `ai.orion.omega.desktop` | Technical, keep for compat |
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
