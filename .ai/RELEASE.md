# OWNEX 7.1.0 — FINAL STABLE (freeze 2026-09-11)

> Núcleo congelado tras cierre de producto. Cambios posteriores solo como
> BUG/SECURITY/DATA/RELIABILITY/COMPATIBILITY/SMALL-UX fix. NEW FEATURE no
> entra automáticamente al Stable Core.

## Estado del freeze

- Versión canónica: **7.1.0** (11 superficies sincronizadas vía `scripts/sync_version.py`)
- `cores/` árbol canónico único; `core/` sombra en eliminación diferida (bloqueada a validación Windows física)
- Reglas permanentes vigentes: PAID solo con evidencia · Human Gate en acciones externas · UNKNOWN etiquetado, jamás inventado · bug bounty = upside

## Gates verificados al congelar

- `import api.main` OK · fast suite 100/1 · suites afectadas 195 passed
- `vite build` OK · `vue-tsc` 0 · `cargo check` OK
- Endpoints: `/api/health` 200 · `/api/version` in_sync · `/direct-work/*` (8 modos con contrato) · `/api/system/health` 200 con DB · auth 401 correcto
- Ruff: 0 errores nuevos en archivos tocados (drift preexistente documentado)

## No verificado aquí (ver docs/KNOWN_LIMITATIONS.md)

- Instalación física Windows + firma · Mobile en hardware · suite completa con drift del flujo concurrente · trading live (DRY_RUN por diseño)
