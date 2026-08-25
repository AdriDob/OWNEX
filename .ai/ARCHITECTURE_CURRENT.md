# OWNEX — Arquitectura ACTUAL (v1.0.0-alpha)

> Estado real verificado 2026-08-25. Sin aspiraciones: solo lo que existe y funciona.

## Desktop (Windows)

```
OWNEX Alpha.exe (Tauri 2 · WebView2 · tray)
├── Vue 3 SPA — frontend/dist embebido (frontendDist)
│     └── lib/backend.ts: descubrimiento dinámico de puerto (event → invoke → scan 8000-8099)
│     └── lib/api.ts: cliente único (auth Bearer + cookie httpOnly, normalización /api)
├── Sidecar ownex-backend.exe (PyInstaller ONEFILE, ≥50MB guard en CI)
│     ├── uvicorn api.main:app (--port/--host/--data-dir/--log-level)
│     └── Datos: %LOCALAPPDATA%\OWNEX\{database,logs} (11 SQLite stores)
└── Lifecycle: backend-ready event · kill-on-exit + watchdog ≤8s anti-huérfanos
```

## Backend único

`api.main:app` — FastAPI, 1.236 rutas OpenAPI. Un solo motor consumido por
todos los shells (Tauri sidecar, PySide6 legacy, dev uvicorn).
Routers root-mounted SIN prefijo `/api`: direct-work/*, mobile/*, wear-os/*.

## Motores principales

| Motor | Entrada API | Estado |
|---|---|---|
| Pipeline CATEYE | targets→endpoints→findings→hypotheses→validation→reports | producción |
| Direct Work Engine | /direct-work/* (root) · workbank · income-plan | producción |
| Economic SSOT | cores/direct_work_engine/economics.py (EV único, UNKNOWN≠1.0) | producción |
| Taxonomía | cores/work_taxonomy.py (4 enums → canónico DWE 38) | producción |
| Trading | /trading/* copy-trading DRY_RUN + DNA + sub-adapters (34 rutas) | producción |
| AI providers | settings/ai/providers (catálogo dinámico 7) + config aplicada en vivo | producción |
| Knowledge bridge | /knowledge/* (17 eps) | producción |

## Reglas vigentes

- ZERO_EXPERIENCE ≠ ZERO_BARRIER (assessment = costo amortizado, jamás fricción de contratación)
- Probabilidades desconocidas se etiquetan (`"desconocida"`), nunca inventadas
- Revenue Rule para toda feature nueva
- Congelamiento Alpha 1.0: cambios solo como v1.0.x/v1.1.0 según impacto
