## Sesión 2026-07-28 — Desktop Terminal Integrado + TS Fixes

### Completed
- **Terminal WebSocket** — `api/routers/terminal_ws.py`: Shell spawn (bash/zsh/PowerShell), MOTD, I/O bridge bidireccional, cleanup automático
- **CSRF Middleware Fix** — WebSocket connections bypass CSRF check (early return en dispatch)
- **TerminalView.vue** — xterm.js integrado con theme PS5 dark (#0a0a0f), scrollback 10k, WebSocket auto-conexión
- **Sidebar + Routing** — Entry "Terminal" en Operaciones, ruta `/terminal`
- **Tauri Config** — v5.0.0 + sidecar + CSP con ws:// en tauri.conf.json
- **Rust Sidecar** — `start_backend` command + auto-launch en release
- **Sidecar Launcher** — `src-tauri/binaries/start_backend.py` para Windows build
- **Auth Middleware** — `/api/system/health` ahora público
- **Scheduler Tests** — 17/17 passed ✅
- **Rust Toolchain** — `rustc 1.97.0` ready

### Remaining
| Task | Status | Priority |
|------|--------|----------|
| Fix frontend TS build errors → vue-tsc + vite build ✅ | ✅ Done | High |
| Tauri Windows build (npm run tauri build) | ⏳ Pending | High |
| Credentials setup (opportunity.env) | ⏳ Pending | High |
| Python backend Windows sidecar (PyInstaller) | ⏳ Pending | Medium |

### System Health
```
✅ API /api/health              [CRIT] Online
✅ Terminal WebSocket /api/ws/terminal  [CRIT] Funcionando
⚠️  Circuit breakers OPEN (agents_status, scheduler_status — legacy)
```

### Desktop Architecture
```
OWNEX Desktop (Tauri v2)
├─ Vue 3 Dashboard (pestañas normales)
├─ TerminalView.vue ← xterm.js (nueva pestaña)
│    └─ WebSocket → ws://127.0.0.1:8000/api/ws/terminal
│                   → Shell real (bash/powershell)
├─ Python Backend (sidecar en release)
└─ Installer: WiX + NSIS (Windows)
```
