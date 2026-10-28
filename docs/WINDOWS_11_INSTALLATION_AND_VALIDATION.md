# WINDOWS 11 — Instalación y Validación (W1-W12)

> Release: **7.1.x** (freeze, ver `.VERSION.txt` + `scripts/sync_version.py` 11 superficies).
> Artefactos CI (tag `v*`): `OWNEX-Setup-*.msi` + `OWNEX-Setup-*.exe` + `SHA256SUMS.txt`.
> Este documento es la **única guía de validación física**: ningún `.msi` se marca PASS sin W1-W12 ejecutados en **PC real con Windows 11**.

## Requisitos

- Windows 11 (22H2+), 8GB RAM, 2GB disco, WebView2 (Evergreen, preinstalado en 11).
- Sin WSL/Linux: la validación es en hardware/so real, no en CI.

## Instalación (W1-W3)

| # | Paso | Esperado | Evidencia |
|---|------|---------|-----------|
| W1 | Descargar MSI (o EXE) + `SHA256SUMS.txt` desde Releases / artefacto CI tag `v7.1.x` | Archivo coincide con SHA | `certutil -hashfile *.msi SHA256` vs `SHA256SUMS.txt` |
| W2 | Instalar (doble clic MSI, Install → Finish). Si SmartScreen: Más info → Ejecutar de todas formas | Sin error, icono OWNEX en escritorio + menú | Screenshot instalador paso final |
| W3 | Primer launch (icono / menú). Esperar 5-15s. | Ventana OWNEX abre, Mission Control visible (>30s sin cierre) | Screenshot Mission Control |

## Arranque del sistema (W4-W7)

| # | Check | Cómo verificar | PASS |
|---|-------|----------------|------|
| W4 | Backend/sidecar | `http://localhost:8000/api/health` → 200 (puerto dinámico tolerado: `netstat -ano \| findstr 8000`) | Backend + sidecar reportan `healthy` |
| W5 | Mission Control | KPIs (targets/findings/ops) cargan, `/api/cycles` 200, `/api/direct-work/recommend` responde | No “Backend no responde” |
| W6 | DB / migrations | Crear 1 target en UI → cerrar app → reabrir → target persiste | Persistencia ok |
| W7 | OAR / AI | `/api/chat` (o chat UnifiedChat) responde; `/api/intelligence/feeds/health` 200 | Chat + 7 feeds listados |

## Operación (W8-W12)

| # | Check | Cómo verificar | PASS |
|---|-------|----------------|------|
| W8 | Opportunity / WorkBank | `/api/direct-work/recommend` devuelve `ranked[]` + `public_work`; WorkBank daily cycle prepara items | Items visibles |
| W9 | Revenue / Capital | `Revenue` + `Capital` páginas abren, `/api/capital/snapshot` responde | Sin 500 |
| W10 | Restart / persistence | Reiniciar app (cerrar → abrir) → datos W6/W8 siguen | Misma data |
| W11 | Offline / degraded | Desconectar red → refresh → UI muestra cache/degraded, no crash | Degradación honesta |
| W12 | Uninstall / reinstall | Panel → Desinstalar → borrar `%LOCALAPPDATA%/Programs/OWNEX` + `%LOCALAPPDATA%/OWNEX` si pide clean → reinstall W1 → W3 PASS | Limpio |

## Plantilla de reporte por W#

```
W#: PASS / FAIL / BLOCKED / NOT_TESTED
Esperado:
Observado:
Error (si FAIL):
Log (ruta):
Screenshot: sí / no
Reproducible: sí / no
```

## Failure loop (si cualquier W FAIL)

```
IDENTIFY W# → COLLECT ERROR+LOG → REPRODUCE → ROOT CAUSE → MINIMAL FIX → TEST → NEW BUILD → REINSTALL → RERUN W#
```

No marcar PASS sin evidencia. No asumir Linux/WSL == Windows.
