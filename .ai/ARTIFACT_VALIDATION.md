# Artifact Validation — OWNEX Alpha 1.0.1 RC1

> **Release**: v7.0.0-rc1 (Alpha 1.0.1) · **Commit**: 7b11455faac9a3b0a40801dddfbd0c265dafc123 · **Date**: 2026-08-25

## Artifact Inventory

| Artifact | Tipo | Tamaño | SHA256 | Verificado |
|---|---|---|---|---|
| `ownex-backend.exe` | Backend sidecar (PyInstaller ONEFILE) | 131.5 MB | `1de10cd23252ea8156febc5d4da93274a2c1038438cc2b06aabd01160c78a82d` | ✅ |
| `OWNEX Alpha_1.0.1_x64_es-ES.msi` | Windows Installer (WiX) | 137.5 MB | `48e6d8dbce858ab895e4e9878485896cf548b809b779905835a1809161489354` | ✅ |
| `OWNEX Alpha_1.0.1_x64-setup.exe` | Windows Installer (NSIS) | 135.3 MB | `a354004f3cbf9fca98f08a4d520e9d83cf76d1b05563f02e51388e31d0a17a1c` | ✅ |
| `OWNEX-Tauri-Windows.zip` | Contenedor MSI + NSIS | 272.6 MB | `2e30516398a51caf9e188f82a8fffdc19a5c7c2375da55f170d495f7b70e0c8d` | ✅ |

## Backend Sidecar Verification

### Build Details
- **Spec**: `OWNEX-Backend.spec` (ONEFILE, no UPX — avoids Defender false positives)
- **Collects**: `api`, `database`, `core`, `cores`, `apps`, `cryptography`, `uvicorn`, `fastapi`, `sqlalchemy`, `pydantic`, etc.
- **Entry point**: `api.main:app` → `uvicorn.Server(...).run()`
- **Port**: 8000 (loopback only — no firewall prompt)
- **Health endpoint**: `GET /api/health` (no auth required)

### Smoke Test (WSL)
```bash
# From artifact directory
./ownex-backend.exe &
sleep 10
curl http://127.0.0.1:8000/api/health
# {"status":"ok","version":{"current":"1.0.1",...},"system":{"status":"ok","score":100,...}}
```

**Resultado**: ✅ **PASS** — Backend arranca, health 200, API respondiendo.

### Size Check
- 131.5 MB (ONEFILE, sin UPX) — dentro del presupuesto esperado (100-200 MB para PyInstaller con deps completas)
- CI guard: `test_tauri_packaging.py` valida `size > 50MB` (anti-stub)

## Tauri Windows Installers

### MSI (WiX)
- **Archivo**: `OWNEX Alpha_1.0.1_x64_es-ES.msi` (137.5 MB)
- **Product Name**: "OWNEX Alpha"
- **Product Version**: 1.0.1
- **Upgrade Code**: estable entre builds
- **Install Scope**: Per-user (no admin required) → `%LOCALAPPDATA%\OWNEX`
- **Shortcut**: Escritorio + Menú Inicio
- **Upgrade**: Detecta versión previa → migra datos automáticamente

### NSIS
- **Archivo**: `OWNEX Alpha_1.0.1_x64-setup.exe` (135.3 MB)
- **Install Type**: Per-user (request execution level: user)
- **Uninstaller**: Generado automáticamente (`uninstall.exe`)
- **Shortcut**: Escritorio + Menú Inicio
- **Registry**: `HKCU\Software\OWNEX Alpha`

### Shared Resources (ambos)
- **Frontend dist**: Embebido en `resources/app.nw` / `resources/app.asar`
- **Sidecar**: `ownex-backend.exe` incluido via `externalBin` en `tauri.conf.json`
- **CSP**: `connect-src 'self' http://localhost:8000 ws://localhost:8000`
- **Icon**: `assets/icon.ico` (multi-res)
- **Localización**: es-ES (código de idioma 3082)

## Verification Commands (Windows)

### MSI
```powershell
# Install
msiexec /i "OWNEX Alpha_1.0.1_x64_es-ES.msi" /quiet /norestart
# Verify
Get-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*" | Where-Object {$_.DisplayName -like "OWNEX Alpha*"}
# Launch
Start-Process "$env:LOCALAPPDATA\OWNEX Alpha\OWNEX Alpha.exe"
# Health check
Invoke-WebRequest http://localhost:8000/api/health
```

### NSIS
```powershell
# Install
.\"OWNEX Alpha_1.0.1_x64-setup.exe" /S
# Verify
Get-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*" | Where-Object {$_.DisplayName -like "OWNEX Alpha*"}
# Launch
Start-Process "$env:LOCALAPPDATA\OWNEX Alpha\OWNEX Alpha.exe"
```

## CI Pipeline Verification

| Step | Status | Evidencia |
|---|---|---|
| `npm ci` (root workspace) | ✅ | Lockfile committed |
| `cd frontend && npm run build` | ✅ | dist/ generado |
| `pyinstaller OWNEX-Backend.spec` | ✅ | ownex-backend.exe 131MB |
| `cargo check` | ✅ | Tauri compila limpio |
| `cargo tauri build` | ✅ | MSI + NSIS generados |
| `test_tauri_packaging.py` | ✅ | 9 guards passed |

## Checksums

Ver `SHA256SUMS.txt` en el directorio de artefactos.

## Known Limitations

| Item | Impacto |
|---|---|
| UPX desactivado | Tamaño mayor pero evita Defender false positives |
| Sidecar ONEFILE | Extracción en %TEMP% en primer arranque (~10-30s) |
| Puerto 8000 hardcoded | Loopback only — no configurable sin rebuild |
| es-ES only | Localización única; otros idiomas requieren rebuild |

## Verification Status

| Check | Status |
|---|---|
| Sidecar health endpoint 200 | ✅ |
| MSI installs clean (per-user) | 🟡 Pendiente validación Windows |
| NSIS installs clean (per-user) | 🟡 Pendiente validación Windows |
| Upgrade test (prev → 1.0.1) | 🟡 Pendiente validación Windows |
| 24h stability soak | 🟡 Pendiente validación Windows |
| Data persistence `%LOCALAPPDATA%\OWNEX` | ✅ Código verificado (`database/db.py:user_data_dir()`) |
| Sidecar shutdown on app close | ✅ `RunEvent::Exit` handler en `lib.rs` |

## Next Steps

1. **Usuario**: Descargar `OWNEX-Tauri-Windows.zip` + `SHA256SUMS.txt` desde CI artifacts
2. **Usuario**: Extraer y ejecutar instalador en Windows 11 limpio
3. **Usuario**: Ejecutar upgrade test (instalar sobre versión previa si existe)
4. **Usuario**: Dejar corriendo 24h → validar estabilidad
4. **Fase 4**: Si todo verde → `RELEASE_READY` → tag `v1.0.1-alpha`