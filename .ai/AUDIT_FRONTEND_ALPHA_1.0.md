# AUDIT FRONTEND — ALPHA 1.0/1.0.1

> **Fecha**: 2026-08-25 · **Método**: ejecución real (scans + TestClient + backend vivo) — no inspección por lectura.
> **Complementa**: FRONTEND_FUNCTIONALITY_MATRIX.md (estado por página), RELEASE_AUDIT/GATE.

## Inventario

| Dimensión | Count | Notas |
|---|---|---|
| Rutas registradas | 126 | 0 redirects rotos (48 verificados) · 0 duplicados full-path · catch-all 404 ✓ |
| Páginas .vue | 66+ | 0 huérfanas (66/66 ruteadas); IncomeHome = nueva CEO home |
| Componentes .vue | 143 | 12 huérfanos → REVIEW_REQUIRED (lista abajo) |
| Stores / Composables | 10 / 19 | sin duplicación de lógica de negocio detectada |
| Llamadas API estáticas | ~465 | cross-ref contra catálogo REAL aplanado (1280 rutas) |

## Contratos frontend ↔ backend

**Metodología definitiva adoptada**: el OpenAPI de FastAPI reciente omite rutas de
`_IncludedRouter` lazy (copilot entero faltaba del catálogo → falsos "muertos").
El ground truth es **matching real contra el app montado** (401/422 = viva, 404 = muerta).

| Scan | Ausentes | Comentario |
|---|---|---|
| openapi lazy (inválido) | 289 falsos positivos | descartado |
| catálogo aplanado real | **14** | 5 artefactos scanner (`${qs}` que existen) + 9 reales |

### Genuinamente ausentes (degradación honesta activa)

| Endpoint | Página | Estado UI |
|---|---|---|
| `/confidence/audit` | ConfidenceDashboard | empty honesto |
| `/connections/sync-all`, `/connections/sync/{p}` | Identity/Connections | botones ocultos o no-op documentado |
| `/identity-center/wallets` GET | Wallets | empty honesto (backend solo POST) |
| `/api/files/list` | SyncCenter | catch(() => null) |
| `/api/copilot/polymarket/scan` | PolymarketTrading | existe en copilot.py:324 pero fuera del router incluido — **candidato a montar igual que copilot.chat (fix aplicado)** |

## Bugs encontrados y corregidos en esta auditoría

1. **MissionControl render vacío** (WIP concurrente commiteado roto): `<ObsidianSync>` sin import; useAudio explotaba sin AudioContext abortando onMounted; test wrapper sin router; stub ErrorState con contrato viejo. → `e8ff1a0f`
2. **Router huérfano copilot** (17 rutas nunca montadas, semanas) → `375f8c72` + guardián
3. **Boot parcial silencioso** (~100 routers en try/except non-fatal) → fail-fast + per-router accumulation → `375f8c72`
4. **OperationsDashboard métricas fantasma** → compuesto desde /stats+/overview+/verdicts+timeline → `b9fe5f1f`

## Estados (loading/empty/error/offline/stale)

- **ErrorState.vue compartido**: ERROR/CAUSA/ACCIÓN + variante *connecting* calmada (regla CALM UX). Consumido en MissionControl/IncomeHome/EvidenceCenter/ExecutiveDashboard/ApplicationAssistant.
- **IncomeHome**: allSettled (backend caído no borra lo respondido) + banda offline implícita vía badge de sistema.
- Pendiente (P3): stale-data indicators ("datos de hace X min") en páginas con polling.

## Mock data

Scan `mockData|fakeData|demoData|MOCK_`: **0 hits en pages/components**.
Único fallback legítimo: KnowledgeGraphMini → empty state (mock eliminado en cbf69102).
Mocks en tests: legítimos por definición.

## Accesibilidad

| Check | Estado |
|---|---|
| aria-hidden en iconos decorativos | PASS (IncomeHome auditado) |
| roles de estado (`role="status"`/`role="alert"`) | PASS en ErrorState |
| contraste texto muted sobre surface | VERIFICAR VISUAL QA Windows real |
| navegación teclado | parciales: select/input nativos OK; modales custom pendientes focus-trap (P3) |

## Responsive

Desktop-first por diseño. Sidebar colapsa con overlay < lg. Grids usan
`grid-cols-1 sm:grid-cols-N lg:grid-cols-M` consistentemente. Tablet funcional,
no pixel-perfect (aceptado por spec).

## Performance

Bundle principal 426 KB (gzip 138 KB) — aceptable para alpha. Chunks lazy por
sección de router. Optimización diferida hasta perfilado real en Windows.

## Deuda restante priorizada

- P2: 12 componentes huérfanos (REVIEW_REQUIRED, lista en RELEASE_AUDIT §12)
- P2: biome noExplicitAny legacy fuera de los 4 archivos ya limpiados
- P3: focus-trap en modales custom · stale indicators · EvidenceCenter selector de verdict ya hecho · Wallets GET backend
