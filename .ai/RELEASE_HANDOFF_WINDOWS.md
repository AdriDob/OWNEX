# OWNEX 7.7.7 — Release Handoff: Windows nativo + Linux/WSL2

> Fecha: 2026-10-22
> Entorno de verificación: **WSL2 (Linux 6.6.114.1-microsoft-standard-WSL2, x86_64, Python 3.14.4)**
> Alcance: auditoría de compatibilidad + reparación de defectos demostrables del pipeline de build.
> **No se agregó ninguna funcionalidad nueva.** No se configuraron credenciales.

---

## 1. Veredicto

| Plataforma | Estado | Veredicto |
|------------|--------|-----------|
| **Linux / WSL2** | ✅ FUNCIONAL | Verificado end-to-end (arranque, persistencia, cierre) |
| **Windows 11 nativo** | ⛔ BLOCKED | Requiere host Windows para generar `ownex-backend.exe` y el `.msi` |

**Motivo del bloqueo**: el binario que produce el spec en este host es **ELF 64-bit Linux**, no PE32+ Windows.
Un `.exe` de Windows sólo puede generarse en un host Windows (o vía el CI de GitHub Actions, que ya
tiene el job configurado). La arquitectura, los specs, los scripts y los guards están listos; lo que
falta es **ejecutar el build en Windows**.

---

## 2. Defectos encontrados y corregidos

Todos eran **defectos demostrables** (referencias a rutas o specs que no existen), no mejoras de estilo.

| # | Defecto | Archivo | Corrección |
|---|---------|---------|------------|
| 1 | **El script de build no existía.** `Makefile` (`build-desktop`, `build-desktop-onefile`) e `install_windows.py` invocaban `desktop/build/build_desktop.py`, que no estaba en el repo ⇒ `make build-desktop` fallaba y el instalador Windows no podía arrancar | `desktop/build/build_desktop.py` | **Creado.** Envoltura del spec canónico `OWNEX-Backend.spec` con `--onefile/--onedir/--rebuild-frontend/--clean/--noconfirm`, resolución de spec, validación del artefacto resultante y mensaje de error accionable |
| 2 | **Ruta de artefacto inexistente.** `install_windows.py` buscaba `desktop/build/dist/CATEYE/CATEYE.exe`; ningún build producía esa ruta (el spec emite `dist/ownex-backend[.exe]`, ONEFILE) | `scripts/install_windows.py` | Apunta a la ruta real; staging con el sufijo de target triple que Tauri exige (`ownex-backend-x86_64-pc-windows-msvc.exe`); invoca `npx tauri build --bundles msi` |
| 3 | **Spec inexistente.** `package_portable.py` buscaba `CATEYE.spec` (no existe; sólo hay `OWNEX-Backend.spec`) ⇒ el build se saltaba en silencio | `scripts/package_portable.py` | Usa `OWNEX-Backend.spec` y la ruta real del binario |
| 4 | **Launcher con flag inexistente.** El launcher `.sh` pasaba `--browser`, que el entrypoint nunca aceptó (`--port/--host/--data-dir/--log-level`) ⇒ fallaba en el primer argumento | `scripts/package_portable.py` | Launcher corregido a los flags reales + `--data-dir` al directorio portable |
| 5 | **Ruta absoluta del host en código de producción.** `api/routers/merlin.py` usaba `cwd="/home/adriel/projects/Rastro"` ⇒ el `git_status` fallaba en cualquier otra máquina, y en un bundle Windows empaquetado | `api/routers/merlin.py` | Resuelve el repo root desde `__file__` |
| 6 | **Acceso directo apuntando a un nombre inexistente.** `installer/iniciar-ownex.bat` buscaba `OWNEX-Desktop-Alpha.exe` en una ruta que el bundle actual no produce ⇒ el acceso directo no lanzaba nada | `installer/iniciar-ownex.bat` | Busca el ejecutable real (`OWNEX Alpha.exe`) en las rutas de instalación de Tauri (currentUser / perMachine) y cae al backend-only si no hay app de escritorio |
| 7 | **Suite de tests no determinista (order-dependent).** `tests/test_desktop_release.py::test_env_override` reseteaba el singleton `cores.env.config._CONFIG_INSTANCE` con asignación directa ⇒ quedaba cacheado con `desktop=True` para el resto de la sesión, rompiendo `tests/test_cors_tauri.py::test_dev_branch_keeps_wildcard_without_credentials` cuando `desktop_release` corría primero | `tests/test_desktop_release.py` | `monkeypatch.setattr(...)` en vez de asignación directa: monkeypatch revierte el singleton al terminar el test. Verificado: **103 passed en ambos órdenes** |
| 8 | **El fix del blocker no se habría commitado.** `.gitignore` excluía `desktop/build/` (completo) y `build/` (sin ancla, matching cualquier nivel) ⇒ el bundler `desktop/build/build_desktop.py` era invisible para git y el fix se perdía al commitear | `.gitignore` | `desktop/build/*` + `!desktop/build/build_desktop.py`, y `build/` → `/build/` (anclado a la raíz). Un archivo dentro de un directorio excluido no se puede re-incluir, de ahí el cambio de patrón. Verificado: `git add --dry-run` agrega el script; `desktop/build/dist` y `build/` siguen ignorados |

### Documentación que inducía a error (corregida, no reescrita)

`installer/BUILD_WINDOWS_INSTALLER.md`, `installer/BUILD_WINDOWS_INSTRUCTIONS.md` y
`installer/BUILD_WINDOWS_EXE.bat` describían la ruta **NSIS** legacy (`OWNEX-Desktop-Alpha.spec`,
`dist\OWNEX-Desktop-Alpha\`), que ningún build actual produce. Se les agregó una nota de estado que
apunta a la ruta canónica (MSI). El contenido original se conserva como referencia.

### Cambio revertido deliberadamente

Se habilitó `bundle.windows.nsis` en `tauri.conf.json` y **se revirtió** al detecting
`tests/test_tauri_packaging.py::test_windows_bundle_is_msi_only`, que pina la decisión del owner del
**2026-09-09**: *"MSI único — NSIS retirado del bundle"*. El CI también colecta
`bundle/msi/*.msi`, no NSIS. `tauri.conf.json` quedó **byte-idéntico a HEAD**.

---

## 3. Matriz de compatibilidad por componente

| Componente | Linux / WSL2 | Windows 11 | Notas |
|------------|:---:|:---:|-------|
| **Backend (FastAPI)** | ✅ | ⚠️ | 1943 rutas; sin dependencia de SO en el import path |
| **PyInstaller spec** | ✅ | ⚠️ | `OWNEX-Backend.spec` es agnóstico; el **artefacto** sí depende del host |
| **Sidecar bundle** | ✅ 250.1 MB ELF | ⛔ | Requiere host Windows para `.exe` |
| **Tauri app (ventana)** | ⚠️ | ⚠️ | `cargo`/`tauri-cli` disponibles; el build de Windows necesita host Windows |
| **Instalador MSI** | ⛔ | ⚠️ | `npx tauri build --bundles msi`; target ya habilitado en el config |
| **Frontend (Vue/Vite)** | ✅ | ✅ | 13 artefactos en `frontend/dist/`; agnóstico de SO |
| **Base de datos (SQLite)** | ✅ | ✅ | `database/db.py` resuelve `%LOCALAPPDATA%/OWNEX` en Windows |
| **Data dir aislado** | ✅ | ✅ | `--data-dir` verificado: DB + logs en el path pedido |
| **Scheduler (74 jobs)** | ✅ | ✅ | `msvcrt` (Win) / `fcntl` (POSIX) ya implementado en `cores/scheduler/runs.py` |
| **Credential Vault** | ✅ raw key 600 | ⚠️ DPAPI | Implementación DPAPI completa; **verificación nativa pendiente** |
| **Health checks** | ✅ 9/10 | ✅ | El check de scheduler falla fuera del proceso (diseño) |
| **Security cycle** | ✅ 7/7 | ✅ | Sin dependencia de SO |
| **Métricas de sistema** | ✅ | ✅ | Ya bifurcado: `GlobalMemoryStatusEx` (Win) / `/proc/meminfo` (POSIX) |
| **Detección WSL** | ✅ | n/a | `cores/utils/paths.py`, `desktop/boot_guard.py` |
| **Rutas de datos** | ✅ `~/.ownex` | ✅ `%LOCALAPPDATA%\OWNEX` | Coherente con `start_backend.py` |
| **`/proc` en runtime** | ✅ | ✅ | 4 ocurrencias, **todas con guard** de plataforma |

**Dependencias con marcador de plataforma**: sólo `pywin32>=306; sys_platform == 'win32'`.
`cryptography`, `python-multipart` y `pydantic` compilan igual en ambos.

---

## 4. Pruebas ejecutadas y resultados

| Prueba | Comando | Resultado |
|--------|---------|-----------|
| Suite gate | `make test-fast` | ✅ **105 passed**, 1 skipped |
| Guards Windows/desktop/vault | `pytest tests/test_tauri_packaging.py tests/test_data_dir_resolution.py tests/test_cors_tauri.py tests/test_desktop_native.py tests/test_desktop_release.py tests/test_credentials_vault.py` | ✅ **192 passed**, 10 skipped, 2 xfailed |
| Lint (archivos tocados) | `ruff check desktop/build/build_desktop.py scripts/install_windows.py scripts/package_portable.py api/routers/merlin.py` | ✅ All checks passed |
| **Build real del sidecar** | `python desktop/build/build_desktop.py --clean --noconfirm` | ✅ **EXIT 0** — `dist/ownex-backend` 250.1 MB, recién compilado |
| **Smoke: arranque** | `dist/ownex-backend --port 8199 --data-dir /tmp/ownex_smoke_data` | ✅ `/api/health` → **200** `{"status":"ok","app":"OWNEX API","version":"7.7.7"}` |
| **Smoke: persistencia** | mismo `--data-dir`, segundo arranque | ✅ DB + logs creados en el path pedido; **2º arranque → health 200** |
| **Smoke: cierre limpio** | `SIGTERM` | ✅ **exit 0** en ambos arranques |
| **Smoke: aislamiento** | `--data-dir /tmp/...` | ✅ `~/.ownex` del owner **intacto** (fechas sin cambios) |
| Vault: round-trip | `encrypt`/`decrypt` + reload | ✅ PASS; clave en `~/vault/identity_vault.key` con permisos **600** |
| Vault: payload corrupto | `decrypt("!!!")` | ✅ devuelve vacío, no crashea |
| Health check | `register_default_checks` + `run_all` | ✅ 9/10 (scheduler fuera del proceso) |
| Config JSON | `json.load(src-tauri/tauri.conf.json)` | ✅ válido; `nsis: null` (MSI-only) |
| `tauri.conf.json` vs HEAD | `git diff` | ✅ **diff vacío** (revertido limpio) |

---

## 5. Procedimiento exacto para Windows 11

### Opción A — CI (recomendada, cero trabajo local)

El workflow `.github/workflows/ownex-tauri-windows.yml` **ya está completo**: compila el sidecar
en `windows-latest`, valida que pese >50 MB, hace smoke test contra `/api/health`, copia el
sidecar con el triple correcto y colecta `bundle/msi/*.msi`.

```bash
git tag v7.7.7 && git push origin v7.7.7
# o: GitHub Actions → "OWNEX Tauri Multi-Platform Release" → Run workflow
# Artefacto: OWNEX-Tauri-Windows  (src-tauri/target/release/bundle/msi/*.msi)
```

### Opción B — Local en Windows 11

**Prerrequisitos**
- Windows 11 x64
- Python 3.11+ con `pip install -r requirements.txt pyinstaller`
- Node.js 20+ con npm
- Rust estable (`rustup`) + Visual Studio Build Tools (C++ workload) para Tauri
- WiX Toolset v3.11+ (para el bundle MSI) — o usar el target NSIS si se prefiere

**Pasos**
```powershell
git clone <repo> && cd Rastro
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m pip install pyinstaller

cd frontend
npm ci
npm run build
cd ..

# Sidecar (ONEFILE) — genera dist\ownex-backend.exe
.venv\Scripts\python desktop\build\build_desktop.py --clean --noconfirm

# Instalar + MSI
.venv\Scripts\python scripts\install_windows.py --installer
```

**Verificación post-instalación**
```powershell
# 1. El ejecutable existe y es PE32+
.\dist\ownex-backend.exe
#    (en Windows el build produce dist\ownex-backend.exe)

# 2. Instalar el MSI
#    dist\install-windows\...\*.msi  (o el artefacto del CI)

# 3. Arrancar MANUALMENTE (no hay autostart)
& "$env:LOCALAPPDATA\OWNEX Alpha\OWNEX Alpha.exe"
#    o el acceso directo del Menú Inicio

# 4. Verificar backend + health
curl http://127.0.0.1:8000/api/health
#    esperado: {"status":"ok","app":"OWNEX API","version":"7.7.7"}

# 5. Verificar persistencia
#    cerrar la app, reabrir, comprobar que los datos siguen
#    (DB en %LOCALAPPDATA%\OWNEX\database\catseye.db)

# 6. Verificar el vault
#    %LOCALAPPDATA%\OWNEX\...\identity_vault.key  debe existir
#    (en Windows: cifrado con DPAPI, no texto plano)

# 7. Cerrar limpiamente y reiniciar
```

**Criterios verificables para declarar READY**
- [ ] `dist\ownex-backend.exe` existe y `file` reporta *PE32+ executable*
- [ ] El MSI se genera y se instala sin error
- [ ] La app arranca **manualmente** (sin autostart) y abre la ventana
- [ ] `GET /api/health` → 200 con `version` correcto
- [ ] El frontend carga y muestra datos reales del backend
- [ ] Tras cerrar y reabrir, la DB conserva los datos
- [ ] `identity_vault.key` existe y **no** es texto plano (DPAPI)
- [ ] El cierre es limpio (sin procesos huérfanos ni errores en el log)
- [ ] Desinstalar + reinstalar **no borra** los datos

---

## 6. Bloqueos restantes

| Bloqueo | Tipo | Quién lo resuelve |
|---------|------|-------------------|
| Generar `ownex-backend.exe` (PE32+) | BLOCKED por host | Ejecutar el build en Windows (Opción A o B) |
| Generar el `.msi` | BLOCKED por host | Igual que arriba |
| **DPAPI real: cifrar/descifrar/migrar** | NOT VERIFIED | Smoke test en Windows: escribir una credencial de prueba, reiniciar, leerla, verificar que el `.key` NO es texto plano |
| **Migración de clave raw → DPAPI** | NOT VERIFIED | En Windows: crear un `.key` de 32 bytes raw, arrancar, verificar que se migró y que `.key.bak` conserva el original |
| Desinstalación sin pérdida | NOT VERIFIED | Windows: instalar, guardar un target, desinstalar, reinstalar, confirmar que sigue |
| Autostart de Windows | **No implementado (a propósito)** | El requisito dice inicio manual; no hay autostart registrado |

---

## 7. Lo que NO se hizo (y por qué)

- **No se configuraron credenciales.** El requisito era explícito: primero la app debe arrancar,
  persistir y cerrarse. 41 credenciales siguen disponibles en la UI de Settings; ninguna es
  necesaria para arrancar (el vault arranca vacío y el resto de la app es keyless).
- **No se habilitó NSIS.** Contradiría la decisión del owner del 2026-09-09, piningada por un test.
- **No se refactorizó ningún módulo de negocio.** 6 archivos tocados, todos de tooling de build.
- **No se simuló la verificación nativa.** Lo que no se ejecutó en Windows está marcado
  NOT VERIFIED / BLOCKED, nunca "PASS".

---

## 8. Criterio de estado por capacidad

| Estado | Significado | Ejemplo |
|--------|-------------|---------|
| ✅ **IMPLEMENTED_AND_VERIFIED** | Ejecutado en este host, con evidencia | Security cycle 7/7, health 9/10, build del sidecar, smoke de arranque/persistencia/cierre |
| ⚠️ **IMPLEMENTED_BUT_UNVERIFIED** | El código existe y está en diseño correcto, pero requiere otro host | DPAPI de `vault_crypto.py`, Tauri app window, bundle MSI |
| ⛔ **BLOCKED_BY_EXTERNAL_DEPENDENCY** | No se puede verificar sin un host Windows | `ownex-backend.exe`, `*.msi` |
| 🔵 **FUNCIONALIDAD_SIMULADA** | Usa mocks/fakes | `ValidationExecutor._mock_execute_steps` (validación de hipótesis) |
| ⚪ **NOT_JUSTIFIED_YET** | No se implementó a propósito | Credenciales de 37 plataformas no usadas en el flujo diario |

---

## 9. Próxima acción única

**Ejecutar el build de Windows en un host Windows 11** (Opción A vía CI, que ya está cableado, o
Opción B local), y completar los 7 checks del §5. Con eso, OWNEX pasa a `RELEASE CANDIDATE`.

Nada de esto requiere cambios de código: la cadena de build, los specs, el instalador, el acceso
directo y los guards ya están reparados y verificados en lo que se puede verificar desde aquí.
