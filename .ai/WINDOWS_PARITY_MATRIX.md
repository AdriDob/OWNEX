# OWNEX — Matriz de paridad WSL (referencia) → Windows nativo

Fecha: 2026-10-15 · Principio: el mismo OWNEX, mismas capacidades. WSL es la
referencia funcional; no se desinstala hasta paridad verificada. Nada se
recorta para ahorrar RAM: el rendimiento se mide, no se declara.

| Capacidad | Referencia WSL (cómo comprobar) | Estado nativo | Verificación Windows pendiente |
|---|---|---|---|
| Núcleo (reglas, lógica, decisiones) | Suite 63/63 en Linux | PASS en Linux; código idéntico (mismo repo) | Re-correr suite en Windows |
| Oportunidades (fuentes, integraciones) | Adapters con retry+backoff; `test_*opportunity*` | PASS en Linux | Probar fuentes reales con credenciales del owner |
| FINISHER (cola, checkpoints, recuperación) | Boot recovery + locks portables + 15 tests nuevos | PASS en Linux | Arranque, kill mid-task, reinicio, no-duplicación |
| Automatizaciones (scheduler) | `job_lock` portable; sin crontab real | PASS en Linux | Tick + exclusión mutua en Windows |
| Finanzas y capital | Ledger `UniqueConstraint(event,source_id)`; memoria unificada a engine canónico | PASS en Linux | Conciliación contra extractos reales |
| Interfaz y monitor | Monitor distingue EN VIVO/SNAPSHOT; `INICIAR.bat` | Inspección PASS | Abrir y operar en Windows real |
| Seguridad y aprobaciones | Gates humanos intactos; sin cambios en políticas | Sin cambios (PASS por no-tocado) | Flujo de aprobación en Windows |
| Datos existentes | `database/db.py` + `cores/database/manager.py` + `cores/utils/paths.py` respetan `OWNEX_DATA_DIR`/`LOCALAPPDATA`; memoria unificada (sin 5ª base); `Path.home()/.orion` puntuales: escribibles en Windows, fuera de convención pero sin pérdida | PASS en Linux | Instalación limpia: una sola BD canónica, cero archivos dispersos |
| Inicio sin WSL | `system.py`: venv por SO, detach por SO, `NameError` de `env` corregido | Lógica PASS en Linux | Arranque real + cierre UI con daemon vivo |

Divergencias aceptadas (documentadas, no recortes): `terminal_ws` termina en vez de apagado elegante en Windows; `shell=True` usa `cmd.exe` (comandos deben ser portables); `.finisher` en Windows parte vacío hasta primer arranque + snapshot como puente.
