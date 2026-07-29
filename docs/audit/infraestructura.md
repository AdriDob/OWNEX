# FASE 8 — Auditoría de Infraestructura Tecnológica

**Proyecto:** CATEYE / OWNEX / Rastro  
**Versión:** 5.1.0  
**Fecha:** 29 Julio 2026  
**Objetivo:** Evaluar objetivamente cada tecnología del stack e identificar redundancias, superposiciones, y tecnologías no justificadas.

---

## 1. LENGUAJES DE PROGRAMACIÓN

| Tecnología | Versión | Dónde se usa | Justificación |
|---|---|---|---|
| **Python** | ≥3.10 | Backend completo (API, cores, database, desktop desktop) | ✅ Justificado — ecosistema bug bounty, ML, scraping |
| **TypeScript** | ~5.8 | Frontend Vue 3 | ✅ Justificado — tipado en frontend grande |
| **Rust** | 2021 | Tauri shell (src-tauri/) | ✅ Justificado — wrappeo nativo para bandeja + menú |
| **Java/Gradle** | - | Android (android/) | ⚠️ Cobertura mobile — Capacitor wrapper, probablemente no se usa activamente |
| **JavaScript** | ES2022 | Root package.json (Capacitor dependencies) | ⚠️ Dependencia fantasma (solo capacitor) |

**Hallazgo:** Android (Carpeta `android/` con Gradle + Java) es una dependency fantasma. Capacitor está configurado pero no hay evidencia de builds Android activos ni de que la app se publique en Google Play. La carpeta `android/` ocupa espacio de mantenimiento.

---

## 2. FRAMEWORKS BACKEND

| Tecnología | Versión | Propósito | Justificación |
|---|---|---|---|
| **FastAPI** | ≥0.95 | API REST principal | ✅ Justificado — moderno, async, OpenAPI |
| **Uvicorn** | ≥0.22 | Servidor ASGI | ✅ Justificado | 
| **httpx** | ≥0.24 | Cliente HTTP async | ✅ Justificado |
| **requests** | ≥2.31 | Cliente HTTP sync | ⚠️ REDUNDANCIA PARCIAL — `httpx` también hace HTTP sync. Se usa para integraciones legacy. |
| **aiohttp** | ≥3.9 | Cliente HTTP async alternativo | ⚠️ REDUNDANCIA TOTAL — `httpx` ya cubre todo el uso async. `aiohttp` es innecesario. |

**Hallazgo:** `aiohttp` está en requirements.txt pero NO aparece importado en ningún módulo del proyecto activo. Es basura. `requests` se solapa con `httpx` que puede hacer sync también.

---

## 3. FRAMEWORKS FRONTEND

| Tecnología | Versión | Propósito | Justificación |
|---|---|---|---|
| **Vue 3** | ^3.5.13 | UI framework | ✅ Justificado |
| **Vite** | ^6.3.5 | Bundler / dev server | ✅ Justificado |
| **Vue Router** | ^4.5.1 | Routing SPA | ✅ Justificado |
| **Pinia** | ^3.0.4 | State management | ✅ Justificado |
| **TypeScript** | ~5.8 | Tipado | ✅ Justificado |
| **Tailwind CSS 4** | ^4.1.6 | Utility CSS | ✅ Justificado |
| **Chart.js** | ^4.5.1 | Charting | ✅ Justificado |
| **vue-chartjs** | ^5.3.3 | Wrapper Vue para Chart.js | ✅ Justificado |
| **Motion** | ^12.43 | Animaciones (framer motion) | ✅ Justificado — UX premium |
| **Lucide Vue** | ^1.22 | Iconos SVG | ✅ Justificado |
| **class-variance-authority** | ^0.7.1 | Variantes CSS | ✅ Justificado |
| **clsx** | ^2.1.1 | Clases condicionales | ✅ Justificado |
| **tailwind-merge** | ^3.2.0 | Merge de clases Tailwind | ✅ Justificado |
| **xterm / @xterm/xterm** | ^5.3/^6.0 | Terminal embebido | ✅ Justificado — terminal en dashboard |
| **@xterm/addon-fit** | ^0.11.0 | Ajuste terminal | ✅ Justificado |

**Hallazgo:** `xterm@^5.3.0` Y `@xterm/xterm@^6.0.0` son la MISMA librería. `xterm` (v5) es legacy; `@xterm/xterm` (v6) es la versión moderna con scoped package. Tener ambas duplica el bundle size. SOLO `@xterm/xterm` debería estar presente.

---

## 4. BASES DE DATOS

| Tecnología | Propósito | Justificación |
|---|---|---|
| **SQLite** (catseye.db, test_financial_hub.db, rastro.db) | DB principal por defecto | ✅ Justificado para single-user desktop |
| **PostgreSQL** (psycopg2-binary en requirements) | DB opcional para producción | ⚠️ NO JUSTIFICADO — no se usa. `DATABASE_URL` default = SQLite. psycopg2 es una dependencia muerta. |
| **SQLite** (astase.db in-memory en tests) | Tests | ✅ |

**Hallazgo:** PostgreSQL (`psycopg2-binary`) está en requirements.txt pero el sistema siempre usa SQLite por defecto y no hay una configuración activa de PostgreSQL. El ORM (SQLAlchemy) es agnóstico, así que la dependencia no es necesaria a menos que se use PostgreSQL activamente.

---

## 5. ORM / MIGRACIONES

| Tecnología | Versión | Propósito | Justificación |
|---|---|---|---|
| **SQLAlchemy** | ≥2.0 | ORM completo | ✅ Justificado |
| **Alembic** | ≥1.13 | Migraciones de esquema | ✅ Justificado |

**Hallazgo:** `database/db.py` todavía tiene un sistema **legacy de migración manual** (`_migrate_columns`, `_migrate_indexes`) que se ejecuta en `init_db()`. El propio código dice "NOTE: Schema migrations are now managed via Alembic... The _migrate_columns() function below is legacy and will be removed once all deployments have run `alembic upgrade head`." Esto es DEUDA TÉCNICA — el legacy lleva meses ahí y debería eliminarse.

---

## 6. MENSAJERÍA / EVENTOS

| Tecnología | Propósito | Justificación |
|---|---|---|
| **EventBus** (in-process + SQLite) | Pub/sub interno | ✅ Justificado |
| **WebSocket** (FastAPI + cores/ws/) | Comunicación bidireccional frontend-backend | ✅ Justificado |

**Hallazgo:** No hay sistema de mensajería externo (RabbitMQ, Kafka, Redis Pub/Sub, Celery). Para una app single-user/desktop, el event bus in-process es suficiente. No hay redundancia aquí.

---

## 7. STACK DESKTOP

| Tecnología | Propósito | Justificación |
|---|---|---|
| **Tauri 2** (Rust) | Shell de escritorio nativo con bandeja | ✅ Justificado |
| **pywebview** | Segunda ventana webview desktop | ⚠️ REDUNDANCIA — Tauri YA maneja la ventana nativa. pywebview se usa en `desktop/main_desktop.py` como fallback, pero Tauri es el entrypoint principal. |
| **PyInstaller** (desktop/build/) | Empaquetado desktop (CATEYE.exe) | ✅ Justificado — Tauri empaqueta el shell, PyInstaller empaqueta Python |
| **pystray** | System tray icon | ⚠️ REDUNDANCIA — Tauri ya tiene tray-icon nativo. pywebview + pystray es el stack legacy. |
| **plyer** | Notificaciones de escritorio | ⚠️ REDUNDANCIA — Tauri tiene tauri-plugin-notification. |
| **Pillow** | Manipulación de imágenes (íconos tray) | ✅ Justificado |

**Hallazgo GRAVE:** Hay **DOS stacks de escritorio completos**:
1. **Stack moderno:** Tauri 2 (Rust) → abre frontend Vue → backend Python se lanza como child process
2. **Stack legacy:** pywebview + pystray + PyInstaller → backend in-process, ventana webview nativa, bandeja propia

`desktop/main_desktop.py` (577 líneas) y `desktop/tray.py` implementan el stack legacy. `run.py` (838 líneas) es el launcher que orquesta ambos modos. El proyecto mantiene **dos arquitecturas desktop paralelas** para el mismo propósito. Esto duplica mantenimiento y pruebas.

---

## 8. CACHÉ

| Tecnología | Propósito | Justificación |
|---|---|---|
| **Memoria in-process** (dicts, listas) | Caché en EventBus, metrics, etc. | ✅ Justificado para single-user |
| **No hay Redis / Memcached** | - | ✅ Correcto — no se necesita para single-user |

**Hallazgo:** SQLite actúa como persistencia en varios lugares (EventBus history, observability_core, memory). No hay un sistema de caché dedicado externo, lo cual es adecuado. Qdrant (vector DB) existe como extension pero es opt-in.

---

## 9. LOGGING

| Tecnología | Propósito | Justificación |
|---|---|---|
| **logging estándar Python** + **PrefixedFormatter** | Logging estructurado consola | ✅ Justificado |
| **Soporte JSON output** | Logging machine-readable | ✅ Buena práctica |

**Hallazgo:** No hay integración con sistemas externos (Sentry, Datadog, Loki). Para desktop single-user es correcto. El custom `PrefixedFormatter` con `PREFIX_MAP` para 50+ módulos es meramente cosmético.

---

## 10. TESTING

| Tecnología | Versión | Propósito | Justificación |
|---|---|---|---|
| **pytest** | - | Test runner | ✅ Justificado |
| **pytest-cov** | ≥5.0 | Cobertura de código | ✅ Justificado |
| **Vitest** | ^4.1 | Test runner frontend | ✅ Justificado |
| **@vitest/coverage-v8** | ^4.1 | Cobertura frontend | ✅ Justificado |
| **@vue/test-utils** | ^2.4 | Testing componentes Vue | ✅ Justificado |
| **jsdom** | ^29.1 | DOM simulado para tests Vue | ✅ Justificado |
| **.coveragerc** | - | Config covereage | ✅ Justificado |
| **pre-commit** | - | Hooks pre-commit con ruff + pytest | ✅ Justificado |

**Hallazgo:** ~150 tests de backend en `tests/`, tests de frontend en `frontend/src/__tests__/` y `frontend/src/stores/__tests__/`. Cobertura mímina `fail_under=80` para cores general, 90 para revenue, 95 para módulos críticos. Suficiente aunque hay tests de integración manuales (`test_cores_integration.py`, `test_imports.py`) que deberían integrarse a pytest.

---

## 11. OBSERVABILIDAD / MONITOREO

| Tecnología | Propósito | Justificación |
|---|---|---|
| **observability.py** | Timing context manager + metrics in-memory | ✅ Justificado |
| **observability_core.py** | SQLite persistente con MetricType, AlertSeverity, AgentExecution | ⚠️ SOBREINGENIERÍA — 687 líneas para una app single-user. Duplica funcionalidad del logging + EventBus. |
| **system_health.py** | Health checks | ✅ Justificado |
| **system_state.py** | State tracking | ✅ Justificado |
| **health/** (cores + core) | Módulos de salud | ✅ |

**Hallazgo:** `observability_core.py` (687 líneas) implementa un sistema completo de observabilidad con tipos de métricas, alertas, ejecuciones de agente, y SQLite persistence. Esto es desproporcionado para una app desktop single-user. Se solapa con `EventBus` para eventos y con el logging para rastreo. Las métricas en memoria en `observability.py` (50 líneas) cumplen la misma función con 1/10 del código.

---

## 12. SEGURIDAD

| Tecnología | Propósito | Justificación |
|---|---|---|
| **cryptography** | Encriptación | ✅ Justificado |
| **AuthMiddleware** | FastAPI middleware de autenticación | ✅ |
| **CSRFMiddleware** | Protección CSRF | ✅ |
| **RateLimitMiddleware** | Rate limiting | ✅ |
| **SecurityHeadersMiddleware** | Headers de seguridad | ✅ |
| **ErrorHandlingMiddleware** | Manejo de errores seguro | ✅ |
| **identity_vault.py** | Almacenamiento seguro de identidad | ✅ |
| **vault_crypto.py** | Crypto para vault | ✅ |
| **.auth_secret** | Secret file | ✅ |
| **CATEYE_AUTH_SECRET** | Env var | ✅ |
| **credentials/** | Gestión de credenciales | ✅ |
| **secrets/** | Módulo de secretos | ✅ |

**Hallazgo:** Postura de seguridad robusta. 5 middlewares diferentes en FastAPI. Sistema de identidad completo. Sin embargo, `cores/secrets` y `core/credentials` pueden solaparse en funcionalidad.

---

## 13. IA / LLM

| Tecnología | Propósito | Justificación |
|---|---|---|
| **Model Router** (core/ai/model_router.py) | 4 tiers: OmniRoute → FCC → Ollama → OpenCode free | ✅ Justificado |
| **Provider abstraction** (cores/ai/provider.py) | Provider unificado (Ollama, OpenAI compat, Gemini) | ✅ Justificado |
| **AI Assistant** (cores/ai/assistant.py) | ScanAssistant + nuevo Assistant | ✅ |
| **AI Advisor** (cores/ai/advisor.py) | Consultas | ✅ |
| **Context Builder** (cores/ai/context_builder.py) | Contexto para LLM | ✅ |
| **AI Memory** (cores/ai/memory.py) | Almacen de interacciones | ✅ |
| **Insights** (cores/ai/insights.py) | Generación de insights | ✅ |
| **Recommendations** (cores/ai/recommendations.py) | Recomendaciones | ✅ |
| **AI Router** (core/ai_router/) | Enrutamiento adicional | ⚠️ REDUNDANCIA PARCIAL — se solapa con `cores/ai/provider.py` |
| **core/ai/runtime.py** | Agent runtime | ✅ |
| **AI Bounty** (core/ai_bounty/) | AI para bug bounty | ✅ |
| **Gemini API** (env var) | Provider específico | ✅ |
| **OpenAI API** (env var) | Provider específico | ✅ |
| **Ollama** | Provider local | ✅ |

**Hallazgo:** Hay archivos AI en **dos lugares**: `core/ai/` y `cores/ai/`. El primero (`core/`) es la nueva arquitectura ORION, el segundo (`cores/`) es la legacy CATEYE. Ambas coexisten sin migración completa.

---

## 14. OTRAS TECNOLOGÍAS SIGNIFICATIVAS

| Tecnología | Propósito | Justificación |
|---|---|---|
| **Playwright** (requirements + extension) | Browser automation | ✅ Justificado |
| **Qdrant** (extension) | Vector DB para memoria semántica | ✅ Opt-in, hot-reloadable |
| **MCP Extension** | Model Context Protocol | ✅ |
| **Aider Extension** | AI coding assistant | ✅ |
| **Git Extension** | Git automation | ✅ |
| **WebSocket** (api/routers/terminal_ws.py) | Terminal interactiva | ✅ |
| **FCM** (Firebase Cloud Messaging) | Notificaciones push | ⚠️ NO USADO ACTIVAMENTE |
| **Twilio** (WhatsApp) | Notificaciones WhatsApp | ⚠️ NO USADO ACTIVAMENTE |
| **SMTP** (Email) | Notificaciones email | ⚠️ CONFIGURADO PERO NO ACTIVO |
| **Gmail OAuth2** | Notificaciones Gmail | ⚠️ CONFIGURADO PERO NO ACTIVO |
| **Shodan / Censys / VirusTotal / etc.** | OSINT APIs | ✅ Justificado — core del producto |
| **Service Worker** (frontend) | PWA offline | ⚠️ INCOMPLETO — registrado pero funcionalidad mínima |
| **Screenshots** (cores/screenshot/, api/routers/screenshots.py) | Captura de pantallas | ✅ Justificado |
| **Vision Gateway** (vision_gateway/) | Procesamiento de imágenes vía LLM | ✅ |
| **Web3 / DeFi / Crypto** | Integraciones blockchain | ✅ Justificado para FASE -1 |

---

## 15. REDUNDANCIAS CRÍTICAS

### 🔴 RED #1: DOS STACKS DE ESCRITORIO
- **Tauri 2 (Rust)** — shell moderno con tray-icon, menú nativo, notificaciones, auto-update
- **pywebview + pystray + PyInstaller** — stack legacy con tray, ventana webview, build propio
- Ambos coexisten. `run.py` y `desktop/main_desktop.py` implementan el legacy. Tauri es el nuevo entrypoint.
- **Costo:** ~1,500 líneas de código duplicado, dos sistemas de build, dos estrategias de empaquetado.

### 🔴 RED #2: DOS ORMs / MIGRACIONES
- **Alembic** — sistema formal de migraciones
- **`_migrate_columns()` en db.py** — migración manual legacy (el propio código dice que es legacy)
- **Costo:** ~160 líneas legacy que deberían eliminarse.

### 🔴 RED #3: TRES CLIENTES HTTP
- **httpx** (async + sync) ✅ actual
- **requests** (sync only) — legacy
- **aiohttp** (async only) — no se importa activamente
- **Costo:** Dependencia muerta (aiohttp), redundancia parcial (requests).

### 🔴 RED #4: DOS SISTEMAS DE OBSERVABILIDAD
- **`observability.py`** (50 líneas) — timing simple en memoria
- **`observability_core.py`** (687 líneas) — sistema completo con SQLite, alertas, tipos de métricas
- **Costo:** ~700 líneas de sobreingeniería. `observability_core.py` es desproporcionado para single-user.

### 🔴 RED #5: DOS SISTEMAS DE IA EN PARALELO
- **`cores/ai/`** — legacy CATEYE AI (provider, assistant, memory, insights, recommendations, summary)
- **`core/ai/`** — nuevo ORION AI (model_router, runtime con multi-agent)
- **Costo:** Ambas arquitecturas coexisten, duplicando lógica de provider routing y gestión de modelos.

### 🟡 RED #6: DOS VERSIONES DE XTERM
- **`xterm@^5.3.0`** — legacy (npm package antiguo)
- **`@xterm/xterm@^6.0.0`** — versión moderna scoped
- **Costo:** Bundle size duplicado para el mismo terminal.

### 🟡 RED #7: NOTIFICACIONES MULTICANAL SIN USO
- **Email SMTP, WhatsApp Twilio, FCM, Gmail OAuth2** — 4 canales configurados en `.env.example`
- Ninguno se usa activamente en el código. Solo existe la configuración.

### 🟡 RED #8: ANDROID / CAPACITOR
- **Carpeta `android/`** completa con Gradle, Java
- **Capacitor config** en root `package.json`
- Sin evidencia de builds Android activos ni publicación en stores.

---

## 16. TECNOLOGÍAS NO JUSTIFICADAS

| Tecnología | Razón |
|---|---|
| **aiohttp** | No se importa en ningún módulo activo. `httpx` cubre todo. |
| **psycopg2-binary** | PostgreSQL no se usa. SQLite es la DB por defecto y única activa. |
| **pywebview** | Redundante con Tauri 2. |
| **pystray** | Redundante con Tauri tray-icon nativo. |
| **plyer** | Redundante con tauri-plugin-notification. |
| **FCM / Twilio / Gmail OAuth2 / SMTP** | Canales de notificación configurados pero sin implementación activa. |
| **Android (Gradle/Java)** | Sin uso activo. |
| **`xterm@^5.3.0`** | Reemplazado por `@xterm/xterm@^6.0.0`. Debe eliminarse. |

---

## 17. RECOMENDACIONES PRIORIZADAS

### Inmediatas (Alto Impacto)
1. **Eliminar aiohttp** de requirements.txt — dependencia muerta.
2. **Eliminar xterm@^5.3.0** — duplicado de @xterm/xterm. Solo mantener la v6.
3. **Eliminar `_migrate_columns()` legacy** de `database/db.py` — la deuda explícita debe pagarse.
4. **Resolver dualidad escritorio**: Elegir entre Tauri (moderno) o pywebview (legacy), eliminar el otro.

### Corto Plazo (Medio Impacto)
5. **Resolver dualidad `core/ai/` vs `cores/ai/`**: Unificar bajo una sola arquitectura.
6. **Resolver dualidad observabilidad**: Elegir entre `observability.py` o `observability_core.py`.
7. **Evaluar si pywin32 es necesario** en Linux/WSL (requirement condicional `sys_platform == 'win32'`).

### Largo Plazo (Mantenimiento)
8. **Consolidar clientes HTTP** a solo `httpx` — eliminar `requests` progresivamente.
9. **Evaluar si psycopg2-binary debe mantenerse** o si la arquitectura es definitivamente SQLite-only.
10. **Limpiar canales de notificación** — implementar o eliminar FCM/Twilio/Gmail/SMTP.

---

## RESUMEN

| Categoría | Estado | Tecnologías redundantes | Tecnologías no justificadas |
|---|---|---|---|
| Lenguajes | ✅ | - | Java (Android) |
| Backend framework | ✅ | aiohttp, requests | aiohttp |
| Frontend framework | ✅ | xterm v5 | - |
| Base de datos | ⚠️ | - | psycopg2-binary |
| ORM | ✅ | _migrate_columns legacy | - |
| Mensajería | ✅ | - | - |
| Desktop | 🔴 | Tauri + pywebview + pystray | pywebview, pystray, plyer |
| Caché | ✅ | - | - |
| Logging | ✅ | - | - |
| Testing | ✅ | - | - |
| Observabilidad | ⚠️ | observabilidad x2 | observability_core.py sobreingeniería |
| Seguridad | ✅ | - | - |
| IA | ⚠️ | core/ai/ + cores/ai/ | - |
| Notificaciones | 🟡 | 4 canales sin uso | FCM, Twilio, Gmail, SMTP |

**Total tecnologías identificadas:** ~65  
**Redundancias detectadas:** 8  
**Tecnologías no justificadas:** 6  
**Líneas de código duplicado / innecesario estimado:** ~4,500–6,000
