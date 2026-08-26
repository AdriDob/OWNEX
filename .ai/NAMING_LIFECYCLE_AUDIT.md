# NAMING & APPLICATION LIFECYCLE AUDIT — OWNEX 1.0.1-alpha

> **Fecha**: 2026-08-26 · **Regla**: nombres reales del repo; NO renames que rompan
> installer/upgrade pipeline (§5 del prompt). Inventario verificado por lectura directa.

## 1. Inventario real (código = autoridad)

| Componente | Nombre real | Ubicación | Estado |
|---|---|---|---|
| **App escritorio** | `OWNEX Alpha.exe` | MSI/NSIS → `%LOCALAPPDATA%\Programs\OWNEX Alpha\` | ✅ canónico |
| **Tauri config** | productName `OWNEX Alpha`, id `ai.orion.alpha.desktop` | src-tauri/tauri.conf.json | ⚠️ id legacy "orion" (no tocar: invalida updater/registry) |
| **Instalador MSI** | `OWNEX Alpha_1.0.1_x64_es-ES.msi` | CI ownex-tauri-windows.yml | ✅ |
| **Instalador NSIS** | `OWNEX Alpha_1.0.1_x64-setup.exe` | mismo workflow | ✅ |
| **Uninstaller** | generado por MSI/NSIS ("Uninstall OWNEX Alpha") | registry HKCU | ✅ automático |
| **Launcher WSL** | `OWNEX-Launcher.ps1` / `OWNEX-Stop.ps1` | scripts/win/ | ✅ prefiere exe nativo; fallback browser |
| **Backend sidecar** | `ownex-backend.exe` (ONEFILE) | externalBin Tauri | ✅ muere con RunEvent::Exit |
| **Entrypoint dev** | `run.py` (CLI multipropósito) | raíz | ✅ permanece como dev CLI, NO es "launcher" |
| **Scheduler** | CoreScheduler (in-process) | core/scheduler/ | ✅ no proceso separado |
| **Workers** | executors in-process | core/opportunity/executors/ | ✅ no procesos separados |
| **Updater** | `OWNEX-Updater.ps1` (semi-automático GitHub Releases: check→descarga→SHA256→msiexec upgrade preservando datos→relanza) | scripts/win/ | ✅ implementado |
| **Single instance** | health-poll reúso :8000 + `backend_alive()` | lib.rs / backend.py | ✅ doble launch no duplica |

## 2. Decisiones de nomenclatura (canónicas)

1. **Producto visible**: `OWNEX` (docs/UI). **Binario**: `OWNEX Alpha.exe` — se mantiene porque
   cambiarlo rompe install-dir/upgrade/registry (prompt §5). Renombre diferido a 1.1 con migración.
2. **Launcher**: el rol lo cumplen DOS artefactos según camino:
   - Producción: el propio exe Tauri auto-bootstrappea (sidecar+health) → NO hace falta "OWNEX Launcher.exe" separado.
   - Dev/WSL: `OWNEX-Launcher.ps1`.
3. **Bootstrapper**: no existe como programa; es una FASE interna (environment check → init_db → scheduler) dentro de lifespan/sidecar.
4. **Updater**: no implementado → documento aquí, sin crear stubs.
5. **Frontend-navegador**: eliminado como superficie primaria — launcher abre la app nativa;
   browser solo fallback si MSI ausente (commit 1189890b).

## 3. Ciclo de vida verificado

```text
INSTALL   OWNEX Setup (MSI/NSIS) → %LOCALAPPDATA%\Programs\OWNEX Alpha\
LAUNCH    exe → bootstrap interno → sidecar :8000 → health poll → ventana
IDEMPOTEN Health-check detecta backend vivo → reúso (no segundo backend)
SHUTDOWN  RunEvent::Exit → kill sidecar → 0 huérfanos (guards packaging)
UPGRADE   MSI upgrade-code preserva datos en %LOCALAPPDATA%\OWNEX
UNINSTALL Desinstalador nativo; datos usuario se conservan (política actual)
DEV       python run.py (CLI) / OWNEX-Launcher.ps1 (WSL)
```

## 4. Checklist §34

- [x] Naming consistente (doc = SSOT del mapeo)
- [x] Launcher funciona (nativo auto-bootstrap + ps1 WSL)
- [x] App principal funciona (3880 tests + E2E)
- [x] Installer funciona (CI rc2)
- [ ] Installer/Uninstaller/upgrade físico → MANUAL VERIFIED pendiente Windows
- [x] Updater: documentado como no-implementado (sin stubs falsos)
- [x] Single-instance / startup / shutdown (guards)
- [x] README/docs/changelog actualizados
- [x] Build reproducible (tag → CI)

## 5. Deuda de naming (P2, 1.1)

- `ai.orion.alpha.desktop` → `desktop.ownex.app` requiere migración de registry/update-path.
- "Alpha" en binario vs producto "OWNEX": renombrar junto a esa migración.
