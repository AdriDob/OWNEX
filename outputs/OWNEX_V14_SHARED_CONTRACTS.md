# OWENEX V14 — SHARED CONTRACTS

## 1. AUTHENTICATION CONTRACT

### Token-Based Auth (Shared Across All Interfaces)

**Endpoints:**
- `POST /api/auth/login` — Authenticate device, return JWT + set httpOnly cookie
- `POST /api/auth/refresh` — Refresh access token using refresh token
- `POST /api/auth/logout` — Invalidate session for device
- `GET /api/health` — Health check (no auth required)
- `GET /api/system/health` — Detailed system health (no auth required)

### Token Payload (JWT)
```json
{
  "sub": "device_id",         // Device identifier (binding)
  "user_id": "local",         // User identifier
  "iat": 1730000000,          // Issued at
  "exp": 1730086400,          // Expiration (30 days)
  "aud": "ownex-api"          // Audience
}
```

### Cookie Setup
- Name: `ownex_session`
- HttpOnly: True
- SameSite: "lax"
- Max-Age: 30 days (2592000 seconds)
- Secure: Only on HTTPS

### Device Binding
- Each token is bound to a device_id
- `validate_device_binding(token, device_id)` → True if token.sub == device_id
- Multiple devices per user allowed
- Each device maintains independent session

### Revocation
- `POST /api/auth/logout` — Revoke specific device
- `POST /api/auth/revoke-all` — Revoke all devices for user
- Token expiration after 30 days
- Manual revocation from any interface

## 2. EVENT BUS CONTRACT

### Shared Event System (All Interfaces)

**Event Types (Shared Vocabulary):**

| Event Type | Priority | Emitted By | Consumed By |
|------------|----------|------------|-------------|
| `opportunity:found` | high | Discovery | TUI, Mobile, Desktop |
| `quick_win:detected` | high | Scoring | Any interface |
| `report:generated` | medium | Pipeline | Any interface |
| `opportunity:updated` | medium | Updates | Any interface |
| `system:ready` | medium | Boot | All interfaces |
| `health_score_updated` | medium | Health checks | All interfaces |
| `sync:completed` | low | Sync operations | All interfaces |
| `discovery:completed` | low | Discovery jobs | All interfaces |
| `system:error` | critical | Any error | All interfaces |
| `anomaly_detected` | critical | Anomaly detector | All interfaces |

### Event Payload Structure
```json
{
  "type": "opportunity:found",
  "priority": "high",
  "source": "hackerone|bugcrowd|remote-jobs",
  "data": { /* opportunity data */ },
  "timestamp": "2026-11-09T20:00:00Z",
  "event_id": "uuid-generated"
}
```

### Event Dispatching
- All interfaces **subscribe** to same event types
- Same event → same reaction in Desktop/TUI/Mobile
- Priority engine filters before dispatch
- History persisted to SQLite via EventBusEntry model
- Idempotent: same event handled safely multiple times

## 3. PERMISSIONS CONTRACT

### Shared Permission Model

**Permission Levels:**
- `read` — Ver datos y estado
- `write` — Modificar configuración
- `execute` — Ejecutar acciones sensibles
- `admin` — Administración completa

**Permission Checks (All Interfaces):**
```python
# Example: Check if user can execute action
auth_manager.validate_device_binding(token, device_id)
auth_manager.get_session(device_id)  # Check active session
# Permission level determined by:
# - User role
# - Device trust level
# - Action sensitivity
# - Current context
```

**Action Sensitivity Matrix:**
| Action | Min Permission | Requires Confirmation |
|--------|---------------|----------------------|
| View opportunities | read | No |
| Save to Work Bank | write | No |
| Draft application | execute | Yes |
| Submit application | admin | Yes |
| Financial operations | admin | Yes |
| Change credentials | admin | Yes |
| Delete data | admin | Yes |
| Pause automation | execute | Yes |
| Resume automation | execute | Yes |

## 4. PERSISTENCE CONTRACT

### Shared Database Schema (Single Source of Truth)

**Tables (Shared Across All Interfaces):**

| Table | Purpose | Shared |
|-------|---------|--------|
| `targets` | Bug bounty targets | ✅ |
| `scan_runs` | Scan execution history | ✅ |
| `reports` | Generated reports | ✅ |
| `verdicts` | Opportunity verdicts | ✅ |
| `programs` | Platform programs | ✅ |
| `event_bus_events` | Event history | ✅ |
| `scheduler_jobs` | Scheduled jobs | ✅ |
| `work_bank_items` | Saved opportunities | ✅ |
| `user_preferences` | Per-user settings | ✅ |
| `user_sessions` | Active sessions | ✅ |

**Database Access (Unified):**
- `SessionLocal` from `database/db.py`
- Engine: `sqlite:///./database/catseye.db` (dev) / PostgreSQL (prod)
- All interfaces use same ORM models
- Migrations applied once, used everywhere

## 5. SCHEDULER CONTRACT

### Shared Scheduler (All Interfaces)

**Job Scheduling (Unified):**
- 7 work cycles with 28+ scheduled jobs
- `cores/scheduler/jobs.py` — Core job definitions
- `cores/scheduler/scheduler.py` — Execution engine
- Jobs registered by type, not by interface

**Job Types (Shared):**
| Job Type | Cadence | Executed By | Visible In |
|----------|---------|-------------|------------|
| Weekly audit | 1d | Scheduler | Desktop, TUI, Mobile |
| Health snapshots | 1h | Scheduler | All interfaces |
| Income tracking | 4h | Scheduler | All interfaces |
| Security triage | 1d | Scheduler | All interfaces |
| Target discovery | 6h | Scheduler | All interfaces |
| Revenue reports | 1d | Scheduler | All interfaces |
| Agent cycles | 2h | Scheduler | All interfaces |

**Job State (Shared):**
- `pending` — Waiting to run
- `running` — In execution
- `completed` — Finished successfully
- `failed` — Error during execution
- `blocked` — Waiting for authorization
- States visible in all 3 interfaces

## 6. WORK BANK CONTRACT

### Shared Work Bank (All Interfaces)

**Operations (Shared Vocabulary):**
| Operation | Endpoint | Min Perm | Confirmation |
|-----------|----------|----------|--------------|
| Search opportunities | `GET /api/discovery/programs/ranked` | read | No |
| Save opportunity | `POST /api/opportunities/remote-jobs/{job_id}/save` | write | No |
| List saved | `GET /api/opportunities/remote-jobs/saved` | read | No |
| Draft application | `POST /api/opportunities/remote-jobs/{job_id}/draft` | execute | Yes |
| Pipeline transition | `POST /api/opportunities/remote-jobs/{job_id}/transition` | execute | Yes |

**Data Model (Shared):**
- Opportunity ID (unique across all sources)
- Source (hackerone, bugcrowd, remote-jobs, etc.)
- Title, description, URL
- Argentina flag (argentina_ok)
- Payment methods supported
- Score/evidence
- Status (saved, drafted, submitted, rejected)

## 7. FINANCIAL HUB CONTRACT

### Shared Financial Model (All Interfaces)

**Revenue Tracking (Unified):**
| Field | Type | Description |
|-------|------|-------------|
| `platform` | str | hackerone, bugcrowd, fiverr, etc. |
| `amount_usd` | float | Payout amount in USD |
| `payment_method` | str | payoneer, wise, paypal |
| `status` | str | pending, confirmed, paid |
| ` earned_at` | datetime | When earned |
| `paid_at` | datetime | When paid |
| `fee_percent` | float | Platform fee percentage |
| `argentina_ok` | bool | eligible for AR withdrawal |

**Financial Operations (Shared):**
- View earnings → `read` permission
- Withdraw → `admin` permission + confirmation
- View projections → `read` permission
- Income tracking → All interfaces show same data

## 8. DESKTOP CONTRACT (Tauri + Vue 3)

### Desktop-Specific Details

**Technology Stack:**
- Frontend: Vue 3 + TypeScript + Tailwind CSS v4
- Backend: FastAPI (same as other interfaces)
- Wrapper: Tauri v2 (Rust + WebView2)
- State: Shared via EventBus + SQLite

**Desktop Capabilities (Beyond Mobile/TUI):**
- Full configuration UI
- Installer generation (PyInstaller)
- Local tool execution
- Large file handling
- Advanced settings panel

**Desktop-Only Features:**
- `python run.py --backup` — Manual backup
- `python run.py --add-target` — Add new target
- Tauri-specific: tray menu, shortcuts
- PyInstaller builds

## 9. TUI CONTRACT (Terminal User Interface)

### TUI Requirements (New Implementation)

**Technology Evaluation:**
- [ ] **Textual** — Modern, Python-first, active maintenance
- [ ] **Rich** — Rich text/box drawing, large ecosystem
- [ ] **Typer** — CLI focused, command-based
- [ ] **Cement** — Traditional TUI framework
- [ ] **Urwid** — Python classic, mature

**Decision Criteria:**
- ✅ Maintainable (few dependencies)
- ✅ Keyboard navigation
- ✅ Rich visual formatting
- ✅ Works in Windows Terminal, PowerShell, Linux Terminal, macOS Terminal
- ✅ Fallback for monochrome terminals
- ✅ No graphics ASCII unnecessary

**TUI Main Screen (Example from V14 Prompt):**
```
OWNEX
Personal Work & Capital System

ESTADO GENERAL      OPERATIVO
Ingresos reales:            $0
Oportunidades nuevas:       12
Tareas pendientes:           3
Conexiones activas:           5
Procesos en ejecución:      2

1. Inicio
2. Oportunidades
3. Trabajo
4. Finanzas
5. Inversiones
6. Conexiones
7. Automatizaciones
8. Agentes
9. Actividad
0. Salir
```

**TUI Navigation:**
- Flechas (up/down/left/right)
- Enter — Seleccionar / Ejecutar
- Escape — Retroceder / Cancelar
- Atajos (F1-F12 configurables)
- Búsqueda — `/` + query + Enter
- Filtros — Definir en cada pantalla
- Paginación — Navegar páginas cuando muchos items
- Formularios — Input fields con validación
- Confirmaciones — "¿Estás seguro? [Y/n]"
- Ayuda contextual — Mostrar atajos disponibles

**TUI Functionalities (Shared with Other Interfaces):**

WORK:
- Consultar oportunidades ✅ (via API)
- Buscar ✅ (via search endpoint)
- Filtrar ✅ (via query params)
- Guardar favoritas ✅ (via Work Bank save)
- Consultar detalles ✅ (via opportunity endpoints)
- Actualizar estados ✅ (via API write)
- Gestionar tareas ✅ (via scheduler)
- Consultar postulaciones ✅ (via draft endpoint)

FINANCE:
- Consultar ingresos ✅ (via revenue endpoints)
- Consultar movimientos ✅ (via financial events)
- Ver comisiones ✅ (via fee data)
- Consultar cuentas ✅ (via auth sessions)
- Consultar saldos sincronizados ✅ (via same DB)
- Consultar historial ✅ (via event history)

INVESTMENTS:
- Consultar carteras ✅ (via investment data)
- Ver mercados ✅ (via market data endpoints)
- Consultar señales ✅ (via signal endpoints)
- Ver estrategias ✅ (via strategy data)
- Consultar backtests ✅ (via test data)
- Consultar paper trading ✅ (via dry-run mode)

AUTOMATIONS:
- Consultar tareas programadas ✅ (via scheduler listing)
- Activar y pausar procesos permitidos ✅ (with confirmation)
- Consultar resultados ✅ (via event history / verdicts)

AGENTS:
- Consultar agentes registrados ✅ (via auth + agent bus)
- Ver tareas ✅ (via agent assignments)
- Consultar progreso ✅ (via task tracking)
- Revisar bloqueos ✅ (via block status)

**TUI Design Principles (V14):**
- Interfaz limpia — Pocos elementos simultáneos
- Jerarquía visual clara — Estados destacados
- Tablas legibles — Datos estructurados
- Estados comprensibles — Sin jerga técnica
- Adaptación a tamaños — Responsive terminal
- Windows Terminal, PowerShell, Linux, macOS compatibility
- Fallback sin colores — modo monocromo

**TUI Commands (Natural Language Examples):**
- "Buscá nuevas oportunidades"
- "Mostrame mis ingresos"
- "¿Qué tareas están pendientes?"
- "Sincronizá mis conexiones"
- "¿Qué agentes están trabajando?"
- "Pausá esta automatización"

**Before sensitive action:**
- Show exactly what will happen
- Request approval
- No arbitrary model execution
- Use canonical services + permissions

## 10. MOBILE CONTRACT (Capacitor/PWA)

### Mobile Requirements (Android First, iOS Eval)

**Technology Evaluation:**
- [ ] **Capacitor** — Web → Native, shared codebase
- [ ] **Tauri Mobile** — Extender Desktop backend
- [ ] **PWA Installable** — Web site, installable app
- [ ] **React Native** — Separate codebase (not recommended)
- [ ] **Flutter** — Separate codebase (not recommended)

**Decision:** Capacitor + shared backend — Single source of truth

**Mobile Dashboard (Read-Only Initial):**
Mostrar:
- Estado de OWNEX
- Ingresos reales
- Alertas importantes
- Nuevas oportunidades
- Tareas pendientes
- Procesos activos
- Estado de conexiones
- Estado de sincronizaciones
- Estado de agentes
- Notificaciones

**Diseño para pantallas pequeñas:**
- Layout vertical optimizado
- Tokens espaciales grandes
- Estados con iconos claros
- Menú hamburguesa para navegación
- Pull-to-refresh
- Offline cache de datos recientes

**Remote Actions (Authorized):**
WORK:
- Consultar oportunidades ✅
- Guardar favoritas ✅
- Cambiar estados ✅ (with confirmation)
- Revisar tareas ✅
- Consultar postulaciones ✅

AUTOMATIONS:
- Ejecutar tareas autorizadas ✅ (with confirmation)
- Pausar automatizaciones ✅ (with confirmation)
- Reanudar automatizaciones ✅ (with confirmation)
- Consultar resultados ✅ (via event history)

CONNECTIONS:
- Consultar estado ✅
- Solicitar sincronización ✅
- Ver errores ✅
- Recibir avisos de autenticación pendiente ✅

AGENTS:
- Consultar agentes ✅
- Supervisar procesos ✅
- Pausar tareas seguras ✅ (with confirmation)
- Consultar resultados ✅ (via event history)

FINANCE:
- Consultar ingresos ✅
- Consultar movimientos ✅
- Revisar saldos sincronizados ✅
- Consultar operaciones pendientes ✅ (read-only)

INVESTMENTS:
- Consultar carteras ✅
- Ver señales ✅
- Consultar mercados ✅
- Ver paper trading ✅ (read-only, no real trading)
- Consultar riesgos ✅ (via risk data)

**Mobile Security:**
- HTTPS only — No local API exposure
- OAuth 2.0 / Access tokens cortos
- Refresh token rotation
- Biometría local cuando disponible
- Rate limiting por dispositivo
- Auditoría completa
- Protección contra replay
- Protección contra CSRF
- No contraseñas en texto plano
- No credenciales permanentes en app
- No clave API estática compartida
- Ver sesiones activas ✅
- Revocar dispositivos ✅
- Desconectar teléfono ✅
- Cerrar todas las sesiones ✅
- Consultar actividad remota ✅

**Sensitive Actions (Require Explicit Confirmation):**
- Operaciones financieras
- Compras, ventas, transferencias
- Retiros
- Firmas blockchain
- Cambios de credenciales
- Eliminación de datos
- Envíos definitivos
- Cambios críticos de configuración

**Biometría:** No sustituye la autorización del backend.

**Mobile Notifications Configurable:**
- Nueva oportunidad importante
- Error de conexión
- Sincronización completada
- Agente bloqueado
- Tarea terminada
- Alerta de seguridad
- Movimiento financiero relevante
- Riesgo de inversión

Evitar notificaciones duplicadas.
Permitir definir prioridades y silenciar categorías.
No enviar información financiera sensible en notificaciones visibles sin protección.

## 11. SYNCHRONIZATION CONTRACT

### Shared State Across All Interfaces

**Event-Driven Synchronization:**
- All interfaces subscribe to same EventBus topics
- State changes propagate automatically
- No polling needed for real-time updates

**State Machine (Shared):**
```
Solicitada → En curso → Completada
   ↓               ↓              ↓
Fallida → Requiere autorización
```

**Synchronization Mechanisms:**
1. **WebSocket** — Real-time (preferred when available)
2. **SSE** — Server-Sent Events (fallback)
3. **Polling** — Every 30s (last resort)

**Reconnection Handling:**
- Automatic reconnection
- Queue pending operations during offline
- Show "solicitada / en curso / completada / fallida" status
- No asumir que acción remota terminó solo por recibir solicitud

**Conflict Resolution:**
- Last-write-wins for non-sensitive data
- Authorization required for sensitive changes
- Idempotent operations where possible
- User confirmation for conflicts

**Idempotency:**
- Same operation repeated → same result
- Operation tokens for critical actions
- Duplicate detection in event history
- User notification if duplicate detected

## 12. ACCESSIBILITY & USABILITY CONTRACT

**Shared Usability Standards:**

**Language:**
- Simple, no technical jargon
- Actions explained: what, why, needs, consequences
- Help contextual en cada pantalla
- Errores accionables

**Visual:**
- Contraste adecuado (WCAG AA minimum)
- Tamaños legibles (mínimo 16px body)
- Estados distinguibles sin depender solo del color
- Navegación por teclado en todas interfaces
- Etiquetas claras en formularios
- Diseño responsive (mobile-first)

**Testing:**
- Usabilidad con personas sin conocimientos técnicos
- Las 3 interfaces deben producir los mismos resultados
- Para las mismas operaciones
- Sin documentación técnica requerida

**Accessibility Features:**
- Lectores de pantalla compatible
- Contraste de color WCAG AA
- Navegación keyboard-only
- Focus indicators visibles
- Alt text en imágenes
- Color no es la única forma de conveyed information

## 13. PERFORMANCE CONTRACT

**Shared Performance Standards:**

**Desktop:**
- Startup < 3 seconds
- API response < 500ms
- TUI refresh < 1 second
- Memory < 500MB typical

**TUI:**
- Startup < 1 second
- Keyboard navigation instant
- No graphics overhead
- Works on minimal terminals (80x24)

**Mobile:**
- Startup < 2 seconds
- API response < 500ms (on 3G)
- Offline cache of recent data
- Battery efficient

**Shared Metrics:**
- Time to first meaningful data
- API endpoint latency percentiles
- Memory usage per interface
- Battery impact (mobile)
- Concurrent users supported

## 14. TESTING CONTRACT

**Shared Test Suites:**

**TUI Tests:**
- Keyboard navigation
- Menu selection
- Form input
- Confirmation dialogs
- State consistency

**Mobile Tests:**
- Authentication flow
- Notification permissions
- Offline behavior
- Reconnection
- Sensitive action confirmations

**API Contract Tests:**
- Same endpoints return same schema
- Auth across interfaces
- Event publishing/consistency
- Permission enforcement
- Scheduler job execution

**Cross-Interface Tests:**
- Same operation → same result
- State sync between Desktop/TUI/Mobile
- Permission enforcement consistent
- Event propagation reliable
- No data contradictions

**Regression Tests:**
- V14 changes don't break V12.1
- Backward compatibility
- No duplicate logic
- Performance budgets maintained

## 14. GOVERNANCE CONTRACT

**Shared Governance:**

**ADRs (Architecture Decision Records):**
- Create for important decisions
- Store in `outputs/adr/`
- Reference in all interfaces
- Update when context changes

**Quality Gates (make check):**
- Ruff: Python lint ✅
- Mypy: Type check ✅
- Pytest: 100+ tests ✅
- TypeScript: Frontend lint ✅
- Cross-interface consistency ✅

**Agent Coordination:**
- Frontend: Vue 3 + Tailwind
- Backend: FastAPI + Python
- Security: IdentityVault + AuthManager
- TUI: New implementation (Textual/Rich eval)
- Mobile: Capacitor eval
- QA: Cross-interface tests

**No simultaneous writes to same module without coordination.**

## 15. IMPLEMENTATION ROADMAP (V14 Phases)

**FASE 0: Auditoría** ✅
- Arquitectura validada
- Backend shareable confirmado
- Tests pasando
- Sin Upwork references

**FASE 1: Contratos Compartidos** 🔄
- Documentar todos los contratos arriba
- Validar que las 3 interfaces pueden usarlos
- Tests de consistencia
- Este documento

**FASE 2: TUI Implementación** 📅
- Elegir tecnología (Textual vs Rich)
- Implementar pantalla principal
- Navegación por teclado
- Conectar al backend real
- Tests de navegación

**FASE 3: Mobile Dashboard** 📅
- Evaluar Capacitor vs PWA
- Dashboard de solo lectura
- Autenticación segura
- Notificaciones configurables

**FASE 4: Natural Language Commands** 📅
- Interpretador de comandos sencillos
- "Buscá nuevas oportunidades"
- Confirmación antes de acciones sensibles
- No chatbot que substituya navegación

**FASE 5: Sincronización en Tiempo Real** 📅
- WebSocket / SSE implementation
- Estados: Solicitada → En curso → Completada
- Manejo de reconexión y offline
- Conflict resolution

**FASE 6: Onboarding Guiado** 📅
- Bienvenida explicativa
- Estado inicial
- Configuración opcional
- Tutorial breve
- Dashboard listo en 5 minutos

**FASE 7: Tests Integrales y Accesibilidad** 📅
- Tests TUI, Mobile, API
- Accessibility testing
- Performance testing
- Regression testing

**FASE 8: Release V14** 📅
- Las 3 interfaces operativas
- Documentación completa
- User guide
- Release notes

No intentar construir todo simultáneamente.
Entregar funcionalidades completas por fases.

## 16. DELIVERABLES V14

Crear o consolidar en `outputs/`:
- `OWNEX_V14_INTERFACE_AUDIT.md` — Auditoria de interfaces
- `OWNEX_V14_ARCHITECTURE.md` — Arquitectura unificada
- `OWNEX_V14_TUI_IMPLEMENTATION.md` — Implementación TUI
- `OWNEX_V14_MOBILE_IMPLEMENTATION.md` — Implementación Mobile
- `OWNEX_V14_REMOTE_SECURITY.md` — Seguridad remota
- `OWNEX_V14_SHARED_CONTRACTS.md` — Contratos compartidos (este documento)
- `OWNEX_V14_UX_AUDIT.md` — Auditoria UX
- `OWNEX_V14_TESTS.md` — Tests integrales
- `OWNEX_V14_USER_GUIDE.md` — Guía de usuario
- `OWNEX_V14_BLOCKERS.md` — Bloqueos identificados

No crear documentos duplicados si ya existen equivalentes.

---

**Principio V14:** Cualquier persona debe poder utilizar OWNEX sin conocer su arquitectura, tecnologías, módulos internos ni conceptos técnicos. La complejidad permanece detrás de la interfaz.

**Objetivo:** Experiencia unificada, simple, segura, rápida y coherente en las 3 interfaces (Desktop, TUI, Mobile) compartiendo un único backend, dominio, permisos, persistencia, servicios, eventos y estado.