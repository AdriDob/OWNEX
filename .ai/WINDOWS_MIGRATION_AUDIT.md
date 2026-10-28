# OWNEX — Migración Windows 11 nativo · FASE 1: Auditoría (solo lectura)

Fecha: 2026-10-15 · Rama: `release/win11-stable` · Entorno de auditoría: Linux/WSL (no Windows nativo).
Estado Git al auditar: hay cambios locales concurrentes sin commitear (p. ej. `api/main.py`, `api/adapters/direct_work_github_bounty.py`, móviles). No se tocó código del repo en esta fase.

## 1. Método

Conteos con `grep -rE` sobre `cores/ api/ scripts/ database/` (*.py). Sin ejecución en Windows.
Clasificación: WINDOWS_COMPATIBLE · NEEDS_ADAPTATION · LINUX_ONLY · EXTERNAL_DEPENDENCY · UNKNOWN.

## 2. Matriz de compatibilidad

| # | Dependencia | Archivos afectados (top) | Clase | Riesgo | Solución propuesta | Prueba necesaria |
|---|-------------|--------------------------|-------|--------|--------------------|------------------|
| 1 | Rutas `/home/` hardcodeadas (10 ficheros) | `cores/learning/training_pipeline.py`, `cores/offensive/reasoners/generic.py`, `cores/utils/paths.py`, `cores/content_factory/service.py`, `api/routers/merlin.py`, scripts de reparación/migración | NEEDS_ADAPTATION | Medio: datos fuera de `%LOCALAPPDATA%`, rupturas silenciosas | Centralizar en `cores/utils/paths.py` + `OWNEX_DATA_DIR` (ya existe el patrón en `database/db.py`, `api/main.py`) | Grep cero `/home/` en runtime + test de resolución en Windows |
| 2 | `fcntl` (locks POSIX, 2 ficheros) | `cores/scheduler/runs.py`, `scripts/finisher/state.py` | LINUX_ONLY | Alto: FINISHER y scheduler dependen de locks para no duplicar trabajo | Capa de locks multiplataforma (`msvcrt.locking` en Windows, `fcntl` en POSIX) tras una interfaz única | Test de exclusión mutua + crash-recovery en Windows real |
| 3 | `os.kill` / señales POSIX (3 ficheros) | `api/routers/terminal_ws.py`, `api/routers/system.py`, `scripts/finisher/main.py` | NEEDS_ADAPTATION | Alto: terminar workers y shutdown graceful | `subprocess` + `psutil` (ya usado en `worker.py`) en vez de señales; `CTRL_BREAK`/job objects solo si hace falta | Test de timeout/cancelación de workers en Windows |
| 4 | `shell=True` (3 ficheros) | `cores/tool_registry.py`, `cores/ai/devin_tool.py`, `scripts/finisher/verification.py` | PARTIAL | Medio: `cmd.exe` interpreta distinto; riesgo de inyección | `shell=True` funciona en ambos SO (usa `cmd.exe`/`COMSPEC` en Windows): no se cambia el flag; la restricción pasa al *contenido* de los comandos de verificación, que deben ser portables. Sin cambio de código en esta fase | Tests de verificación/comandos en Windows |
| 5 | `systemd` mencionado (2 ficheros) | `cores/direct_work_engine/execution_planner.py`, `api/main.py` | WINDOWS_COMPATIBLE | Ninguno: ambas son comentarios/cadenas, sin dependencia de código | Ninguno | Ninguna |
| 6 | `cron` mencionado (35 ficheros) | Scheduler y jobs | WINDOWS_COMPATIBLE | Ninguno: grep confirma cero `crontab`/`/etc/cron`/`cron.d` reales; todo es scheduler en-proceso | Ninguno | Tick del scheduler en Windows |
| 7 | `xdg-open` (1 fichero + monitor) | Monitor de escritorio (ya corregido a `os.startfile`/`open`/`xdg-open`) | NEEDS_ADAPTATION | Bajo | Abstracción `open_path()` (hecha en el monitor) | Abrir carpetas en Windows real |
| 8 | Scripts `#!/bin/bash` | `scripts/ci_complete.sh`, `scripts/orion-ollama-optimized.sh` | LINUX_ONLY | Bajo (CI/dev, no runtime) | Reescribir en Python o `.ps1` solo si el instalador los necesita | Instalador en Windows |
| 9 | Rutas Windows ya previstas | `database/db.py`, `api/main.py`, `cores/projects/registry.py`, etc. usan `LOCALAPPDATA`/`OWNEX_DATA_DIR`/`CATEYE_DATA_DIR` | WINDOWS_COMPATIBLE | Bajo | Extender el patrón al resto (punto 1) | Test de resolución de dirs en Windows |
| 10 | Daemon persistente | FINISHER como proceso de usuario vs Windows Service | UNKNOWN | Medio: sesión de usuario, permisos, reinicio | Decidir tras Fase 2; proceso supervisado + autostart es lo simple | Cierre de UI con daemon vivo; reinicio de Windows |

## 3. Lo que NO se afirma

- Nada de lo anterior está verificado en Windows nativo: todo lo que requiera ejecución real queda **BLOCKED** hasta probar en Windows 11.
- No se modificó código del repo en Fase 1. Cambios solo en `~/Desktop/ownex_monitor/` (fuera del repo) y este archivo.
- No se elimina ni se oculta la dependencia de WSL en ningún doc/config.

## 4. Siguiente fase propuesta (no iniciada)

Fase 2: capa de compatibilidad central (rutas `pathlib` + `OWNEX_DATA_DIR`, locks `fcntl`/`msvcrt`, procesos sin señales POSIX), empezando por `scripts/finisher/state.py` y `cores/scheduler/runs.py`, con tests de regresión en Linux antes de tocar Windows.

## 5. FASE 0 ejecutada (2026-10-15)

- Rama `release/win11-stable`, decenas de ficheros modificados concurrentes + 4 untracked (`scripts/finisher/state.py`, `scripts/finisher/main.py`, `cores/utils/oscompat.py`, `tests/test_oscompat.py` — estos dos últimos son de este trabajo).
- No se descartó ni reformateó nada ajeno: ediciones quirúrgicas por cadena exacta en `cores/scheduler/runs.py`, `scripts/finisher/state.py`, `api/routers/system.py`, `scripts/finisher/main.py`.
- `terminal_ws.py` no se tocó: `send_signal(SIGTERM)`+`kill()` ya funciona en ambos SO (en Windows termina el proceso; sin apagado elegante de consola, documentado y aceptado).
- `cores/utils/paths.py` ya centraliza rutas con soporte Windows: no se duplicó, solo se extiende su uso.

## 6. FASE 1 implementada — `cores/utils/oscompat.py` (nuevo)

- Locks por `O_CREAT|O_EXCL` + PID + reclamo de stale (reemplaza `fcntl.flock`). `LockHeldError` hereda de `BlockingIOError`: las cláusulas `except` existentes conservan su significado sin cambios de lógica.
- `pid_alive()` (psutil → `os.kill(0)` POSIX → `OpenProcess` Windows, fail-closed) y `terminate_pid()` (terminate→wait→kill).
- `scripts/finisher/state.py`: instance lock sin `fcntl`, sin `_lock_fh`; `api/routers/system.py`: `pid_alive`/`terminate_pid`, venv `.venv/Scripts/python.exe` en Windows, `DETACHED_PROCESS` vs `start_new_session`; **bug preexistente corregido**: `env` solo existía en la rama fallback → `NameError` si `.venv/bin/python` existía.
- `scripts/finisher/main.py` stop: `terminate_pid` en vez de `os.kill(SIGTERM)`.
- Diferencia de semántica declarada: los locks ya no son reentrantes en el mismo proceso (verificado: `job_lock` no se anida en `scheduler.py`/`scheduler_v2.py).

## 7. FASE 2 tests (Linux) — 55/55 PASS

- Nuevo `tests/test_oscompat.py` (9 tests: roundtrip, doble-adquisición, stale reclaim, ownership, pid_alive, terminate real, exclusión entre procesos, `job_lock`).
- Anteriores 46 intactos. Ruff limpio en todos los ficheros tocados/creados por este trabajo (quedan 5 avisos preexistentes en `scripts/finisher/state.py`, fichero untracked ajeno: no tocados).
- **BLOCKED en Windows nativo**: ejecución real, instalación limpia, reinicio, cierre de UI con daemon vivo, RAM comparada. Sin runner Windows aquí, no se declara nada de eso.

## 8. CONTINUACIÓN FASE 2 (2026-10-15)

- `StateManager.recover_interrupted_tasks()` (nuevo, `scripts/finisher/state.py`): al arrancar, el daemon con lock reencola tareas RUNNING/VERIFYING huérfanas (READY, o BLOCKED si se agotaron intentos; worker stale → CRASHED). Workers vivos jamás se tocan (verificación por `is_expected_process`, import diferido sin ciclos). Llamado desde `FinisherDaemon.start()` — el gap medido era real: la liberación solo existía en `_recovery_mode` (tras 5 fallos), nunca al arrancar.
- Persistencia verificada por diseño: `save()` atómico (tmp+fsync+rename); test `test_recovery_persists` recarga desde disco.
- Nuevo `tests/test_finisher_boot_recovery.py` (6 tests). Nuevo `scripts/measure_ram.py` (portable Linux/Windows, solo lectura, copia temporal): línea base Linux en `.ai/RAM_BASELINE.json` — baseline 13.9 MB, oscompat 17.0, state_load 20.1, scheduler_lock 18.6, boot_recovery 25.0 MB RSS (Python 3.14.4). Repetir en Windows con `python scripts/measure_ram.py --pretty`.
- Matriz actualizada: `shell=True` → PARTIAL (el flag funciona en ambos SO; la restricción es el contenido de los comandos), `systemd` → solo comentarios (sin dependencia), `cron` → confirmado en-proceso (cero crontab real).
- Suite: **61/61 PASS en Linux** (46 previos + 9 oscompat + 6 boot-recovery). Ruff limpio en lo tocado.
- Sigue **BLOCKED**: ejecución en Windows nativo, instalación limpia, reinicio/recuperación real, cierre de UI con daemon vivo, RAM comparada Windows-vs-WSL. La prueba de 8h requiere autorización explícita: no iniciada.

## 10. PARIDAD SIN RECORTES (2026-10-15)

- `cores/memory/system.py`: eliminados 3 engines contra `sqlite:///./database/catseye.db` relativo (una BD por CWD); ahora usa el engine canónico de `database.db` (`MemoryRecord` ya vive ahí). Guard: `tests/test_memory_canonical_db.py` (2 tests).
- Verificado sin cambios: `cores/database/manager.py` respeta `OWNEX_DATA_DIR`; `terminal_ws.py` ya elige shell por SO; `systemd`/`cron` solo menciones.
- Nueva `.ai/WINDOWS_PARITY_MATRIX.md`: 9 capacidades con referencia WSL, estado nativo y verificación pendiente. Divergencias aceptadas y documentadas (no recortes).
- Suite: **63/63 PASS en Linux**. Ruff limpio. Funciones congeladas salvo lo listado aquí.
- Sigue **BLOCKED**: todo lo que exige Windows real, más la comparativa de capacidades WSL-vs-nativo y la prueba de 8h (sin autorización).

## 9. PAQUETE DE VALIDACIÓN WINDOWS (2026-10-15, sin ejecutar aquí)

- `scripts/measure_ram.py`: el state file pasó a opcional — sin `.finisher/state.json` las etapas de estado reportan `{"skipped": ...}` (exit 0) en vez de fallar. Verificado en Linux con y sin state.
- Nuevo `scripts/validate_windows.ps1` (solo lectura, sin admin): 1) versión de Python (usa `.venv\Scripts\python.exe` si existe), 2) `measure_ram.py --pretty` → `RAM_WINDOWS.json`, 3) pytest de los 15 tests portables, 4) checklist manual (arranque nativo, interrupción→recuperación, apagado+reinicio, comparativa RAM, prohibición 8h sin autorización).
- El `.ps1` **no** pudo verificarse aquí (sin PowerShell en Linux): revisado a ojo, ejecución **BLOCKED** hasta correrlo en Windows 11 real.
