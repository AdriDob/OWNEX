# OWNEX 9.0 — FRONTEND COMPLETION AUDIT

**Fecha:** 2026-11-05  
**Agente:** OpenCode  
**Propósito:** Inventario inicial antes de ingeniería frontend completa  
**Estado:** INVENTARIO REAL — No judgments, solo hechos medibles

---

## 0.1 — RAMA Y CONTEXTO

| Item | Valor |
|------|-------|
| **Branch actual** | `main` |
| **Último commit** | `5830971b feat: consolidate MERLIN→COPILOT, update documentation, integrate workbank and economic models` |
| **Worktrees activos** | `/home/adriel/projects/Rastro/work/ownex-economy-active-earn` (checkout `5ce8866b`) |
| **Archivos modificados sin commit** | `cognee`, `core/mcp_bridge.py`, `core/workflow_connector.py`, `cores/source_intelligence/registry.py`, `cores/zero_barrier_eligibility.py`, `frontend/src/pages/Discovery.vue`, `work/ownex-economy-active-earn/` |
| **Branch de trabajo** | Sin branches adicionales (sobre `main`) |

---

## 0.2 — INVENTARIO DE RECURSOS FRONTEND

### 0.2.1 — Estructura de Archivos

| Categoría | Count | Ubicación |
|-----------|-------|-----------|
| **Componentes Vue** | 137 | `frontend/src/components/` |
| **Páginas Vue** | 76 | `frontend/src/pages/` |
| **Archivos .ts/.js** (no tests) | 87 | `frontend/src/` (incluye lib/, composables/, utils/) |
| **Stores Pinia** | 15 | `frontend/src/stores/` |
| **Archivos de configuración** | Vite, TS, Tailwind | `frontend/vite.config.ts`, `frontend/tsconfig.json` |
| **Servicios API** | 5 | `frontend/src/lib/` |

### 0.2.2 — Rutas y Navegación

| Item | Count/Estado |
|------|------------|
| **Rutas definidas** | 85 | En `frontend/src/router/index.ts` |
| **Rutas con `path: '/'`** | 85 | Total de rutas registradas |
| **Rutas legacy redirect** | `/welcome` → `/`, `/dashboard` → `/`, `/classic` → `/`, `/home` → `/` |
| **Ruta pública `/`** | `IncomeHome.vue` | Componente principal Command Center |
| **Rutas protegidas** | Reglas en `router.beforeEach` | `isPublicRoute` check + `auth.isAuthenticated` + `auth.autoLogin()` |

### 0.2.3 — Stores de Estado

| Store | Propósito | Archivo |
|-------|-----------|---------|
| **auth** | Autenticación device-first, token, user session | `src/stores/auth.ts` |
| **pinia** | Global state management | `src/pinia.ts` (o `createPinia()` en main.ts) |
| **Otros stores** | 14 stores adicionales | `src/stores/` |

### 0.2.4 — Servicios API

| Servicio | Endpoints | Propósito |
|----------|-----------|-----------|
| **API client** | Configuración base | `src/lib/backend.ts` |
| **Proxy config** | Routes root-mounted (13 namespaces sin `/api` prefix) | Proxy dev → `http://127.0.0.1:8000` |

### 0.2.5 — Layouts y Composables

| Layout/Composable | Descripción |
|------------------|-------------|
| **AppLayout.vue** | Layout principal con sidebar, header, outlet |
| **IncomeHome.vue** | Comando Center — dashboard de ingresos |
| **useI18n** | Internacionalización |
| **useGuidedMode** | Modo guiado/asistido/autónomo |

### 0.2.6 — Componente Count (Resumen)

| Tipo | Cantidad |
|------|----------|
| **Componenes Vue (.vue)** | 137 |
| **Páginas (.vue bajo `/pages`)** | 76 |
| **Archivos de lógica (.ts/.js)** | 87 |
| **Stores Pinia** | 15 |
| **Total archivos fuente** | ~301 (sin tests, sin assets) |

---

## 0.3 — INVENTARIO DE INTEGRACIONES BACKEND

| Endpoint | Estado | Comentario |
|----------|--------|------------|
| `/auth/login` | ✅ Conectado | Device ID only, POST |
| `/auth/token` | ✅ Conectado | Validación |
| `/mobile/dashboard` | ✅ Conectado | Resumen móvil |
| `/api/opportunities/quick-wins` | ⚠️ Limitaciones | Véase Fase 3 |
| `/api/mobile/dashboard` | ✅ Conectado | Dashboard móvil |
| `/api/digest` | ⚠️ Limitaciones | Configurado pero ver |
| `/api/overview` | ⚠️ Limitaciones | Revisar |
| `/api/*` (13 namespaces root-mounted) | ✅ Conectados | Proxy dev configurado |

**Notas de integración:**
- 13 namespaces routing sin `/api` prefix (configurado en `vite.config.ts` server.proxy)
- `autoLogin()` usa `/auth/login` con `{device_id, device_info}`
- `isAuthenticated` usa `isSessionValid()`
- Sin login form `email/password` en UI (removido)

---

## 0.4 — INVENTARIO DE AUDITORÍAS PREVIOUS

| Archivo | Propósito | Estado |
|---------|-----------|--------|
| `.ai/AUDIT_FRONTEND_ALPHA_1.0.md` | Auditoría frontend alpha 1.0 | Histórico |
| `.ai/AUDIT_BACKEND_ALPHA_1.0.md` | Auditoría backend alpha 1.0 | Histórico |
| `.ai/AUDIT_FINAL_SESSION.md` | Auditoría sesión final | Histórico |
| `.ai/AUTONOMY_READINESS.md` | readiness autónomo | Actualizable |
| `.ai/ARCHITECTURE_FINAL.md` | Arquitectura final | Actualizable |
| `.ai/FRONTEND_FUNCTIONALITY_MATRIX.md` (repositorio público) | Matriz funcionalidad frontend | Referencia externa |

---

## 0.5 — BUENAS PRACTICES ACTUALES

| Práctica | Estado |
|----------|--------|
| **TypeScript estricto** | Configurado (ver tsconfig) |
| **Build Vite** | Pasa (2000+ modules transformados) |
| **Tests vitest** | 226/226 passing (baseline) |
| **Lint (Biome)** | Passing |
| **Service Worker** | `public/service-worker.js` configurado |
| **Auth sin email/password** | `loginWithCredentials` y `register` removidos |
| **autoLogin device-first** | Implementado en `src/stores/auth.ts` |
| **Recovery SW automático** | Integrado en `src/main.ts` |
| **Responsive** | Pending validación completa |
| **Accesibilidad** | Pendiente audición WCAG |
| **Tauri integration** | Pending verificación |

---

## 0.5 — BLOQUEOS IDENTIFICADOS (Inicial)

| Bloqueo | Severidad | Comentario |
|---------|-----------|------------|
| **Router usa `isSessionValid()`** | Media | Necesita validación contra auth actual |
| **DashboardOdyssey muestra apuestas** | Alta | No tiene sección Source Intelligence |
| **Matriz pública docs 126 rutas** | Media | Discrepancia con realidad actual (76 páginas) |
| **Calls API sin verificación** | Baja | Necesita clasificación Fase 3 |
| **Depósitos sin commit** | Media | `cognee`, archivos core modificados |

---

**Fin del Inventario de Estado Real (Fase 0)**

*Este documento sirve como base para todas las fases subsiguientes. No contiene juicios de valor, solo hechos medibles extraídos del repositorio actual.*
