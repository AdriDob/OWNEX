# OWNEX Desktop — Tauri v2 Architecture

> **Generated from actual codebase** — This document reflects the real implementation.

## Overview

OWNEX Desktop is a Tauri v2 application that bundles a Vue 3 frontend with a Python FastAPI backend sidecar. The desktop application provides the deepest OWNEX surface with full access to all work cycles, AI chat, terminal, and system operations.

## Architecture

```
OWNEX.exe / OWNEX.app
├── Frontend (Vue 3 + Vite dist)
│   └── dist/ → loaded via `tauri://localhost` (WebView2 on Windows)
├── src-tauri/
│   ├── src/
│   │   ├── main.rs              # Entry point, window config, CSP
│   │   ├── python_sidecar.rs    # Spawns/monitors FastAPI sidecar
│   │   ├── ollama_manager.rs    # Auto-starts/stops Ollama
│   │   ├── ipc/
│   │   │   ├── commands.rs      # Tauri invoke commands
│   │   │   └── events.rs        # Event emission to frontend
│   │   ├── system_tray.rs       # System tray integration
│   │   ├── window_state.rs      # Persist position/size/state
│   │   └── updater.rs           # GitHub Releases auto-update
│   ├── Cargo.toml
│   └── tauri.conf.json
├── python/                      # Bundled FastAPI (PyInstaller ONEFILE)
│   └── ownex-backend.exe        # Self-contained backend
└── resources/
    ├── icon.ico / icon.icns
    └── splash.png
```

## Tauri Configuration (`src-tauri/tauri.conf.json`)

```json
{
  "identifier": "com.ownex.app",
  "productName": "OWNEX",
  "version": "7.0.0",
  "build": {
    "frontendDist": "../dist",
    "devUrl": "http://localhost:5173",
    "beforeDevCommand": "npm run dev",
    "beforeBuildCommand": "npm run build"
  },
  "app": {
    "windows": [{
      "title": "OWNEX — Autonomous Work OS",
      "width": 1440,
      "height": 900,
      "minWidth": 1024,
      "minHeight": 720,
      "decorations": false,
      "transparent": true,
      "titleBarStyle": "overlay",
      "hiddenTitle": true
    }],
    "security": {
      "csp": "default-src 'self' data: blob:; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self' http://localhost:* ws://localhost:*"
    }
  },
  "bundle": {
    "active": true,
    "targets": "all",
    "icon": ["resources/icon.png", "resources/icon.icns", "resources/icon.ico"],
    "windows": {
      "webviewInstallMode": "embedBootstrapper",
      "allowDowngrades": false
    },
    "macOS": {
      "minimumSystemVersion": "13.0",
      "exceptionDomain": "localhost"
    }
  },
  "plugins": {
    "shell": { "open": true },
    "dialog": { "open": true, "save": true },
    "fs": { "scope": ["$APPDATA/ownex/*", "$HOME/.ownex/*"] },
    "updater": { "active": true, "endpoints": ["https://releases.ownex.dev"] },
    "notification": { "active": true },
    "globalShortcut": { "active": true }
  }
}
```

## Backend Sidecar (`python_sidecar.rs`)

### Spawn Logic
```rust
pub fn spawn_python_sidecar(app: &tauri::AppHandle) -> Result<(), Box<dyn std::error::Error>> {
    let python_path = if cfg!(target_os = "windows") {
        app.path().resolve("python/python.exe", tauri::path::BaseDirectory::Resource)?
    } else {
        app.path().resolve("python/bin/python", tauri::path::BaseDirectory::Resource)?
    };
    
    let script_path = app.path().resolve("python/main.py", tauri::path::BaseDirectory::Resource)?;
    
    let mut child = Command::new(python_path)
        .arg(script_path)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()?;
    
    // Health check loop in background thread
    std::thread::spawn(move || {
        loop {
            std::thread::sleep(std::time::Duration::from_secs(5));
            if !is_healthy("http://localhost:8000/health") {
                restart_python_sidecar(app);
            }
        }
    });
    
    Ok(())
}
```

### Key Behaviors
- **ONEFILE**: PyInstaller bundles entire Python runtime + deps into single `ownex-backend.exe` (~50MB+)
- **Port**: Fixed at 8000 (configurable via `--port` arg)
- **Health Check**: `GET /api/health` every 5s, 1.5s timeout
- **Auto-restart**: On health failure, sidecar is killed and respawned
- **Data Dir**: Passed via `--data-dir` argument → `%LOCALAPPDATA%/OWNEX` (Windows) / `~/.ownex` (Linux)
- **Dev Mode**: If backend already running on 8000, sidecar reuses it (no conflict)

## Frontend-Backend Communication

| Channel | Purpose | Implementation |
|---------|---------|----------------|
| HTTP REST | All API calls | `fetch` to `http://localhost:8000/api/*` |
| WebSocket | Terminal, real-time | `ws://localhost:8000/api/ws/terminal` |
| Tauri IPC | Native commands | `invoke('command_name', args)` |
| Events | Backend→Frontend push | `listen('event_name', handler)` |

### CSP Configuration
The CSP explicitly allows WebSocket connections to localhost:
```
connect-src 'self' http://localhost:* ws://localhost:*
```

## Startup Sequence

```
1. Tauri launches → creates WebView2 window (Windows) / WebKit (Linux/macOS)
2. Rust `main()` runs → spawns python_sidecar thread
3. Sidecar starts FastAPI on 127.0.0.1:8000
4. Frontend loads (tauri://localhost) → Vue app mounts
5. Frontend polls `/api/health` until backend ready (~30-60s)
6. Auto-refresh timer (10s) updates Mission Control views
7. User sees "Source: api" with real data
```

### Timing
- **Window visible**: ~3s
- **Backend healthy**: ~30-60s (depends on `discover_all` timeout 30s)
- **Full data**: ~60-90s

## Data Persistence

### Database Location
| Platform | Path |
|----------|------|
| Windows | `%LOCALAPPDATA%/OWNEX/database/cateye.db` |
| Linux | `~/.ownex/database/cateye.db` |
| macOS | `~/Library/Application Support/OWNEX/database/cateye.db` |

### Configuration
- **Environment**: `CATEYE_DATA_DIR` set by Rust before spawning sidecar
- **DATABASE_URL**: `sqlite:///{data_dir}/database/cateye.db`
- **Device Identity**: `%LOCALAPPDATA%/OWNEX/desktop_device.json` (persists across reinstalls)

### Schema Initialization
- `database/db.py` → `_ensure_db_dir()` runs at module level (before `create_engine`)
- `init_db()` called by sidecar on startup (idempotent)
- Creates tables if missing: targets, endpoints, findings, scan_runs, verdicts, evidence, memory_records, etc.

## System Tray (`system_tray.rs`)

### Menu Items
- **Show/Hide Window** — Toggle main window visibility
- **Open Mission Control** — Navigate to main view
- **Backend Status** — 🟢/🟡/🔴 with health detail
- **Restart Backend** — Manual sidecar restart
- **Quit** — Graceful shutdown (stops sidecar, saves window state)

### Behavior
- Click tray icon → Shows window (if hidden) or focuses (if visible)
- Close window → Minimizes to tray (does not quit)
- Quit from tray → Full shutdown

## Auto-Updater (`updater.rs`)

```rust
"updater": {
  "active": true,
  "endpoints": ["https://releases.ownex.dev"]
}
```

- **Channel**: GitHub Releases (tagged `v*`)
- **Format**: MSI (Windows), DMG (macOS), AppImage (Linux)
- **Verification**: SHA256 checksums from `SHA256SUMS.txt`
- **Background**: Checks on startup, downloads silently, prompts install

## Window State Persistence (`window_state.rs`)

Persisted to `%APPDATA%/OWNEX/window_state.json`:
```json
{
  "width": 1440,
  "height": 900,
  "x": 100,
  "y": 100,
  "maximized": false,
  "last_tab": "mission-control"
}
```

Restored on next launch.

## Global Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+K` / `Cmd+K` | Open Command Palette |
| `Ctrl+Space` / `Cmd+Space` | Quick Action / Agent |
| `Ctrl+Shift+T` | Toggle Terminal |
| `Ctrl+Shift+C` | Open Command Palette (alt) |

Registered via Tauri `globalShortcut` plugin.

## Terminal Integration (`TerminalView.vue` + `terminal_ws.py`)

### Backend (`api/routers/terminal_ws.py`)
```python
@app.websocket("/api/ws/terminal")
async def terminal_ws(websocket: WebSocket):
    await websocket.accept()
    # Spawn shell: bash (Linux/macOS) or powershell (Windows)
    # Bridge stdin/stdout/stderr ↔ WebSocket messages
    # Cleanup on disconnect
```

### Frontend (`TerminalView.vue`)
- **xterm.js** with OWNEX theme (PS5 dark `#0a0a0f`)
- **Scrollback**: 10,000 lines
- **Auto-connect**: On mount, reconnects on disconnect
- **MOTD**: Shows OWNEX version, backend status

## Ollama Manager (`ollama_manager.rs`)

- **Health Check**: `GET http://localhost:11434/api/tags`
- **Auto-start**: `ollama serve` if not running
- **Model Check**: Verifies `qwen2.5:3b-instruct` available
- **Pull**: Downloads model if missing (background)

## Build Process

### Development
```bash
# Terminal 1: Backend
cd /home/adriel/projects/Rastro
.venv/bin/python -m api.main

# Terminal 2: Frontend
cd frontend
npm run dev

# Terminal 3: Tauri
cd src-tauri
cargo tauri dev
```

### Production Build
```bash
# 1. Build frontend
cd frontend && npm run build

# 2. Build Python sidecar (ONEFILE)
cd /home/adriel/projects/Rastro
.venv/bin/pyinstaller OWNEX-Backend.spec --clean --noconfirm

# 3. Build Tauri bundle
cd src-tauri
cargo tauri build --target x86_64-pc-windows-msvc
```

### Artifacts (Windows)
| Artifact | Size | Purpose |
|----------|------|---------|
| `OWNEX Alpha_7.0.0_x64_es-ES.msi` | ~340MB | Windows Installer (WiX) |
| `OWNEX Alpha_7.0.0_x64-setup.exe` | ~340MB | NSIS Installer |
| `ownex-backend.exe` | ~50MB | Embedded in bundle |

## Troubleshooting

### Backend Won't Start
1. Check port 8000 not in use: `netstat -an | findstr 8000`
2. Check `%LOCALAPPDATA%/OWNEX/logs/ownex-api.log`
3. Verify `ownex-backend.exe` exists in bundle resources
4. Run manually: `%LOCALAPPDATA%/OWNEX/ownex-backend.exe --port 8000`

### Frontend Shows "Backend Not Responding"
1. Wait 60-90s for initial `discover_all` to complete
2. Check health endpoint: `curl http://localhost:8000/api/health`
3. Restart via System Tray → "Restart Backend"

### Database Locked
1. Ensure only one OWNEX instance running
2. Check for stale processes: `taskkill /f /im ownex-backend.exe`
3. Delete `%LOCALAPPDATA%/OWNEX/database/cateye.db-wal` / `-shm`

### Ollama Not Found
1. Install: `winget install Ollama.Ollama` (Windows)
2. Start service: `ollama serve`
3. Pull model: `ollama pull qwen2.5:3b-instruct`

### Updater Fails
1. Check internet connectivity
2. Verify `https://releases.ownex.dev` accessible
3. Manual install: Download MSI from GitHub Releases

## Security

- **CSP**: Restricts to `self`, `localhost:*`, `ws://localhost:*`
- **No External Origins**: Production bundle only talks to local backend
- **Certificate Pinning**: Not implemented (local-only)
- **Sidecar Isolation**: Runs as user process, no elevated privileges

## Development vs Release

| Aspect | Development | Release |
|--------|-------------|---------|
| Frontend | Vite dev server (`localhost:5173`) | Bundled `dist/` |
| Backend | `python -m api.main` | PyInstaller ONEFILE sidecar |
| Backend Port | 8000 (configurable) | 8000 (fixed) |
| Data Dir | `./data` | `%LOCALAPPDATA%/OWNEX` |
| CSP | Relaxed | Strict |
| Auto-restart | Manual | Watchdog (5s health check) |
| Updater | Disabled | Enabled (GitHub Releases) |

---

*Document generated from codebase. Last verified: 2026-08-27*