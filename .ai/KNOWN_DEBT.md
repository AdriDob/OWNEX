# Known Debt — Deuda Técnica Conocida

> Deuda identificada durante el audit arquitectónico. Cada entrada incluye evidencia de su existencia.

## 18. Contract drift frontend↔backend (audit §17, 2026-09-15): prefix-root + rutas ficticias

- **Contexto**: auditoría completa de las 222 llamadas `api.*` del frontend contra las rutas reales del backend (fuente de verdad `app.routes` runtime, no openapi lazy). Resultado: 165 matchean, **57 no responden** (55 por ruta inexistente + 2 por método 405).
- **Resuelto en el audit (P0/P1)**:
  - **Cluster A — prefix drift (11 rutas → 404)**: `first-money`, `result-based`, `platform-guides` se montan en **raíz** en `api/main.py` (`include_router(router)` sin `/api`) pero `frontend/src/lib/backend.ts::resolveApiUrl` los resolvía bajo `/api/*` → FirstMoney, ResultBased y PlatformGuides NUNCA funcionaron desde el frontend. Fix: `ROOT_MOUNTED_PREFIXES` ahora incluye `['/direct-work','/mobile','/wear-os','/first-money','/result-based','/platform-guides']`. Nuevo guard de regresión `tests/test_frontend_api_contract.py` (3 tests) pin que cada router root-mounted del backend tiene contraparte en el front.
  - **Cluster E (método 405)**: `ownexData.ts::updateFinding` llamaba `PUT /api/findings/{id}` pero el backend expone `PATCH /{finding_id}` → migrado a `api.patch`. `updateFindingStatus` ya usa `PUT /{id}/status` (correcto).
  - **Dead code §12**: eliminado `cores/intelligence/next_best_action.py` (219 líneas, 0 callers/imports/tests/exports/packaging — verificado exhaustivamente) y `frontend/src/services/capitalApi.ts` (274 líneas, 29 llamadas a rutas inexistentes, 0 imports).
- **Documentado, NO arreglado (decisión: estabilidad > novelty, no expandir)**:
  - **Cluster B — WorkRoom** (`frontend/src/components/work/WorkRoom.vue`, ruta `/operations/work-room/:id`): 10 sub-recursos ficticios (`PUT/POST/DELETE /workbank/{id}`, `/files`, `/evidence`, `/deliverables`). El backend solo expone `/workbank/{id}/file/{filename}` (GET/PUT) + `/deliver/*`. La sala nunca funcionó; no es parte del flujo diario crítico. Opciones: reescribir WorkRoom al contrato real (`file/{filename}` existente) o quitar la ruta — diferido, no bloquea.
  - **Cluster D — CommandPalette muertas (4)**: `/api/memory/query` (no existe), `/api/hypotheses` GET (solo POST `/{target_id}`), `/direct-work/queue` (no existe), `/api/scheduler/jobs` (no existe). Son comandos de búsqueda/atajos no críticos; fallan silencioso.
  - **Cluster E resto**: `Connections.vue` `/api/connections/sync-*` (no existen), `Wallets.vue` `PUT /identity-center/wallets/{id}` (solo POST), y los 8 endpoints de `capitalApi.ts` que vivían bajo `/api/economic|revenue|financial` pero el módulo ya fue eliminado.
- **Régimen**: cada nueva ruta frontend debe existir en el backend (o prefijo dinámico); el guard `test_frontend_api_contract.py` pin los root-mounted; los clusters B/D/E quedan como deuda explícita de frontend legacy, no como jobs/fixes de producción.

## 17. ✅ core/ eliminado (2026-09-14) — cierra §16