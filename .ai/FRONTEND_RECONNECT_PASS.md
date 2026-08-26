# FRONTEND RECONNECT PASS — Matriz de visibilidad (2026-08-26)

> Hallazgo medible: **111 rutas top-level · 93 SIN entrada directa en Sidebar**.
> Muchas son children alcanzables vía tabs del padre; otras están genuinamente
> invisibles aunque funcionen. Origen: cleanups históricos + reverts entre procesos.

## Cómo leer esta matriz

- `CHILD_OK` = alcanzable como tab/child del padre navegable → visible indirectamente.
- `HIDDEN` = ruta funcional pero ningún camino de navegación la alcanza → RECONNECT.
- `VERIFY` = determinar si el flujo real la alcanza desde otro lado antes de tocar nada.

## Inventario generado (script node sobre router/index.ts vs *Sidebar*.vue)

Ver `/tmp` script — reproducible:
```js
// routes = path:'...' del router; visible = strings '/x' en Sidebars
hidden = top.filter(r => !visible.some(v => r===v || r.startsWith(v+'/')))
```

## Grupos detectados (muestra — completar en sesión de reconnect)

| Grupo | Rutas | Clasificación inicial |
|---|---|---|
| Auth/setup | /activation, /verify, /welcome | CHILD_OK (públicas por diseño) |
| Dashboards duplicados | /dashboard, /classic | VERIFY (legacy vs IncomeHome '/') |
| Intelligence tabs | findings, hypotheses, evidence, investigations, confidence, differential | CHILD_OK (children de /intelligence) |
| Targets tabs | discovery, attack-surface, prioritization, endpoints/:id | CHILD_OK |
| Reports tabs | queue, center, history, verification | CHILD_OK |
| Operations | executive, work-queue, pipelines, scheduler, tools, health, settings, workflows, replay, version-backup, logs | **HIDDEN parcial** — executive (CEO View) y work-queue (superficie nueva parity) críticos |
| Integrations tabs | connections, wallets, accounts, platforms, sync, outlook | CHILD_OK |

## Plan de reconnect (siguiente sesión, 2-3h)

1. Ejecutar script completo → clasificar las 93 una a una con navegación real abierta.
2. HIDDEN confirmados → agregar entrada al grupo correcto del Sidebar (1 línea c/u).
3. Regla: solo conectar páginas que consuman endpoints VIVOS (paridad con FRONTEND_FEATURE_PARITY_AUDIT.md).
4. Lo que no tenga backend vivo → sección 1.1 de este archivo, NO conectar pantallas muertas.
5. Verificación: vue-tsc 0 + vitest + build + smoke manual de cada nueva entrada.

## Regla permanente

Ninguna página nueva entra al router sin entrada simultánea en navegación.
Ninguna página se desconecta del sidebar sin registrar dónde sobrevive.
