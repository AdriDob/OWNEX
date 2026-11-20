# OWENEX V15 — Wear OS Integration Audit

## 1. Estado Actual de la Integración

### 1.1 `cores/wear_os/integration.py`

**Fortalezas:**
- Arquitectura sólida con dataclasses bien definidas
- Singleton pattern para consistencia
- Almacenamiento JSON persistente
- 10+ métodos cubriendo el ciclo completo de notificaciones y aprobaciones
- Tipos de evento claros y enumerados

**Componentes definidos:**
- `WatchEventType` — 6 tipos de eventos (NOTIFICATION, APPROVAL_REQUEST, etc.)
- `WatchNotificationLevel` — 4 niveles (CRITICAL, HIGH, MEDIUM, LOW)
- `WatchNotification` — notification_id, title, message, level, read, requires_action, action_type
- `WatchApprovalRequest` — request_id, title, description, workflow_id, responded, approved
- `WatchStatus` — system_online, scheduler_running, active_workflows, pending_approvals, findings totals, targets_active, health_score
- `WearOSIntegration` class — métodos completos para notificaciones, aprobaciones, estado

**Almacenamiento:**
- `~/.ownex/wear_os/notifications.json` — Hasta 50 notificaciones
- `~/.ownex/wear_os/approvals.json` — Hasta 20 solicitudes de aprobación
- _load_state() / _save_state() — Persistencia en cada modificación

### 1.2 `frontend/src/pages/MobileCompanionJarvis.vue`

**Fortalezas:**
- Interfaz Vue 3 completa con Tailwind styling
- Conexión doble: Android + Wear OS
- MERLIN Mini chat integrado
- Secciones: Dashboard, Notificaciones, Aprobaciones, Estado, Acciones Rápidas
- Refrescado automático cada 120s
- Manejo de estado conectado/desconectado

**Componentes de UI:**
- Status indicators con dots online/offline
- Device cards con conectar/desconectar
- Notifications list con badges de nivel
- Approvals list con ✓/✗ buttons
- Status grid: findings, targets, scheduler, next action
- Quick actions grid: refresh, MERLIN, Dashboard, notifications toggle

## 2. Brechas de Integración V15

### 2.1 Auth & Token Management

**Actual V14/V15:**
- Backend AuthFastAPI usa `AuthManager` con tokens JWT + httpOnly cookies
- `validate_device_binding(token, device_id)` — valida token.sub == device_id
- Sesiones 30 días, refresh tokens, revoke-all endpoint

**Wear OS Actual:**
- Almacenamiento JSON local `~/.ownex/wear_os/`
- Sin validación contra backend AuthManager
- No hay device binding en nivel de sistema

**Actualización V15 Necesaria:**
- ✅ Usar JWT tokens del AuthManager para todas las API calls
- ✅ Device binding validation en cada endpoint wear OS
- ✅ Refresh token rotation (corta duración, rotación automática)
- ✅ Session revocation from any interface
- ✅ Single source of truth: backend AuthManager, no almacenamiento duplicado

### 2.2 Event Bus Synchronization

**Actual V14:**
- `event_bus.py` — 40+ event types con priority engine
- Events publicados/consomidos por todas las interfaces
- History persistida en SQLite `event_bus_events`

**Wear OS Actual:**
- Storage JSON aislado, sin conexión al event_bus
- Notificaciones y aprobaciones en silo independiente

**Actualización V15 Necesaria:**
- ✅ Publicar eventos al `event_bus` cuando se envían notificaciones/wear OS approvals
- ✅ Suscribirse a eventos del sistema y convertirlos en notificaciones wear OS
- ✅ Event types mapping:
  - `system:alert` → `notification` level CRITICAL/HIGH
  - `opportunity:found` → `notification` level HIGH
  - `report:generated` → `notification` level MEDIUM
  - `coordinator:bounty_completed` → `notification` level MEDIUM
  - `approval:requested` → `approval_request` event type
  - `approval:responded` → `approval_response` event type

### 2.3 API Endpoints Integración

**Endpoints Existente Backend (necesitan testing/consumo wear OS):**

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `POST /api/notifications` | Post | Enviar notificación (requiere auth) |
| `GET /api/notifications` | Get | Listar notificaciones (paginado, filtros) |
| `POST /api/approvals/request` | Post | Solicitar aprobación nueva |
| `POST /api/approvals/respond` | Post | Responder aprobación (approved/rejected) |
| `GET /api/approvals/pending` | Get | Listar aprobaciones pendientes |
| `GET /api/system/health` | Get | Health check (usado por watchStatus) |

**Wear OS Actual:**
- Llamadas a métodos locales: `integration.send_notification()`, etc.
- Sin autenticación explícita en nivel de código

**Actualización V15 Necesaria:**
- ✅ Todos los calls pasar por endpoints `/api/...` con validação de token
- ✅ Endpoint `GET /api/wear-os/status` (o usar `/api/system/health` existente)
- ✅ Endpoint `GET /api/wear-os/notifications` con filtros level/unread
- ✅ Endpoint `GET /api/wear-approvals/pending` para pending approvals
- ✅ Error handling estandarizado (mismo formato error que resto de API)

## 3. Plan de Actualización V15

### 3.1 `cores/wear_os/integration.py` — Actualizaciones Necesarias

**A agregar/actualizar:**

```python
# Importar AuthManager para validación de tokens
from cores.auth.auth_manager import get_auth_manager
from cores.auth.session_validator import verify_token


# Nuevo: Validar token en cada operación crítica
def _validate_wear_token(token: str, device_id: str) -> bool:
    """Validar token JWT contra AuthManager canónico."""
    manager = get_auth_manager()
    data = verify_token(token)
    return data is not None and data.get("sub") == device_id


# Nuevo: Usar endpoints API en lugar de storage local puro
# Los métodos aún pueden usar storage local como cache,
# pero la fuente de verdad es el backend + event_bus
```

**Métodos a mantener/adapter:**

| Método Actual | Actualización V15 |
|--------------|------------------|
| `send_notification()` | ✅ Mantener, pero añadir `token` y `device_id` params; llamar `POST /api/notifications` detrás |
| `request_approval()` | ✅ Mantener, pero validar token primero; POST `/api/approvals/request` |
| `respond_approval()` | ✅ Mantener, pero validar token; POST `/api/approvals/respond` |
| `get_status()` | ✅ Mantener, usar `GET /api/system/health` + `GET /api/wear-os/status` |
| `get_notifications()` | ✅ Mantener, usar `GET /api/notifications` con filtros; storage local como cache |
| `get_pending_approvals()` | ✅ Mantener, usar `GET /api/approvals/pending` |
| `_load_state()` / `_save_state()` | ⚠️ Mantener como cache local sync, pero source of truth es backend |

### 3.2 `frontend/src/pages/MobileCompanionJarvis.vue` — Actualizaciones Necesarias

**A actualizar en el script `<script setup>`:**

```typescript
// Importar services actualizados
import {
  fetchWearOSStatus,         // Usar GET /api/system/health + wearable data
  fetchWearOSNotifications,  // Usar GET /api/notifications?level=&unread_only=&limit=
  fetchWearOSPendingApprovals, // Usar GET /api/approvals/pending
  markWearOSNotificationRead, // Usar POST /api/notifications/:id/read o query param
  respondWearOSApproval,     // Usar POST /api/approvals/respond?approved=true/false
  type WearOSStatus,
  type WearOSNotification,
  type WearOSApproval,
} from '@/services/ownexData'
```

**A actualizar en las functions:**

```typescript
async function refreshStatus() {
  loading.value = true
  try {
    // Usar API endpoints en lugar de llamadas locales
    const [wearNotifs, wearApprovals] = await Promise.all([
      fetchWearOSNotifications({ unread_only: true, limit: 10 }),
      fetchWearOSPendingApprovals(),
    ])
    notifications.value = wearNotifs
    pendingApprovals.value = wearApprovals
  } catch {
    // Fallback a storage local si API falla
  } finally {
    loading.value = false
  }
}

async function loadWearOSStatus() {
  try {
    wearStatus.value = await fetchWearOSStatus()
    // Formato: { system_online, scheduler_running, active_workflows, ... }
  } catch {
    wearStatus.value = fallbackDefaults
  }
}

async function markNotificationRead(id: string) {
  try {
    await markWearOSNotificationRead(id)
    // Actualizar estado local + optimistic UI
    notifications.value = notifications.value.map(n =>
      n.notification_id === id ? { ...n, read: true } : n
    )
  } catch { /* ignore */ }
}

async function respondApproval(requestId: string, approved: boolean) {
  try {
    await respondWearOSApproval(requestId, approved)
    // Remover de pending list + optimistic update
    pendingApprovals.value = pendingApprovals.value.filter(a => a.request_id !== requestId)
  } catch { /* ignore */ }
}
```

**A actualizar en tipos/imports:**

Los types `WearOSStatus`, `WearOSNotification`, `WearOSApproval` deben alinearse con los responses de API:
- `WearOSStatus` → Mapear desde `WatchStatus` + fields extra API
- `WearOSNotification` → Mapear desde `Notification` API response
- `WearOSApproval` → Mapear desde `ApprovalRequest` API response

### 3.3 Sincronización Event Bus → Wear OS

**Flujo propuesto V15:**

1. **Core event** publicado en `event_bus.py` (ej: `opportunity:found`, `system:alert`, `approval:requested`)
2. **Consumer** (nuevo servicio) suscribe al event bus
3. **Transform** event → Wear OS format (notification/approval)
4. **Publish** a `wear_os` topic o tabla `wear_os_events` en SQLite
5. **Wear OS frontend** se suscribe a `/api/wear-os/updates` (SSE/WebSocket) o polling `GET /api/wear-os/notifications`
6. **UI actualiza** automáticamente en MobileCompanionJarvis.vue

**Eventos que deben propagarse:**

| Evento Core | Wear OS Translation | Priority |
|-------------|--------------------|----------|
| `system:error` | Notification CRITICAL | critical |
| `system:alert` | Notification HIGH | high |
| `opportunity:found` | Notification HIGH | high |
| `report:generated` | Notification MEDIUM | medium |
| `approval:requested` | Approval request | high |
| `coordinator:bounty_completed` | Notification MEDIUM | medium |
| `health_score_updated` | Status update | medium |

## 4. Checklist de Migración V15 → Usable

### 4.1 Backend (`cores/wear_os/integration.py`)

- [ ] Agregar import AuthManager + token validation
- [ ] Adapter methods para usar endpoints `/api/...` detrás de escenas
- [ ] Mantener storage local JSON como cache/offline fallback
- [ ] Agregar método `get_integration_status()` que reporte health del integración
- [ ] Probar con tokens JWT reales vs storage local simulado

### 2. Frontend (`MobileCompanionJarvis.vue`)

- [ ] Actualizar imports a usar `services/ownexData` endpoints API
- [ ] Actualizar `refreshStatus()` para consumir `GET /api/notifications`, `GET /api/approvals/pending`
- [ ] Actualizar `loadWearOSStatus()` para usar `GET /api/system/health` + data wearable
- [ ] Actualizar `markNotificationRead()` para usar endpoint POST/DELETE
- [ ] Actualizar `respondApproval()` para usar POST `/api/approvals/respond`
- [ ] Manejar error cases: token expirado, sesión vencida, reconexión
- [ ] Optimistic UI updates con fallback a storage local
- [ ] Types alineados con responses API

### 3. Event Bus Integration

- [ ] Mapear 6-8 eventos core → tipos Wear OS
- [ ] Crear consumidor event_bus → wearable notifications
- [ ] Probar que eventos core → aparecen en MobileCompanionJarvis.vue
- [ ] Verificar priority engine respeta niveles CRITICAL/HIGH/MEDIUM/LOW

### 4. Seguridad V15

- [ ] HTTPS only para todas las llamadas wear OS (no HTTP local)
- [ ] Token validation en cada endpoint wearable
- [ ] Device binding validation (token.sub == device_id)
- [ ] Rate limiting por dispositivo wearable
- [ ] No almacenar credenciales permanentes en wearable
- [ ] Revocar sesiones desde Desktop/TUI/Mobile → afecta wearable
- [ ] Audit log de todas las operaciones wear OS (quién, cuándo, qué acción)

### 5. Testing V15

- [ ] Unit tests: `send_notification` con token válido vs inválido
- [ ] Unit tests: `respond_approval` approved/rejected paths
- [ ] Integration tests: API endpoints `/api/notifications`, `/api/approvals/...`
- [ ] End-to-end: Desktop → Event Bus → Wear OS notification appears
- [ ] End-to-end: Wear OS approval → actualiza core state + visible en Desktop/TUI
- [ ] Offline test: wearable funciona sin conexión (usando cache local)
- [ ] UI test: MobileCompanionJarvis.vue renders correctamente con datos reales

## 5. Roadmap Migración V14 → V15 Wear OS

| Hitos | Descripción | Fecha Estimada |
|-------|-------------|----------------|
| **V15-FECHA-0** | Auditoría completa (este documento) | Completa |
| **V15-FECHA-1** | Actualizar `cores/wear_os/integration.py` con validação token + endpoints API | Sprint 1 |
| **V15-FECHA-2** | Actualizar `MobileCompanionJarvis.vue` consumir API endpoints | Sprint 1-2 |
| **V15-FECHA-3** | Conectar event_bus Wear OS propagation | Sprint 2 |
| **V15-FECHA-4** | Testing: unit + integration + end-to-end | Sprint 3 |
| **V15-FECHA-5** | Security review: auth, token, device binding | Sprint 3 |
| **V15-FECHA-6** | Documentation: Wear OS integration guide | Sprint 4 |
| **V15-FECHA-7** | Release candidate + deploy a testing users | Sprint 4-5 |

**Condición de "DONE":** Las 3 interfaces (Desktop, TUI, Mobile) + Wear OS muestran el mismo estado, usan los mismos endpoints API, y las operaciones sensibles requieren autorización explícita en todas las interfaces.

## 6. Consideraciones Finales

**Qué se preserva del diseño actual:**
- ✅ Arquitectura de notificaciones y aprobaciones (ya está bien diseñada)
- ✅ Dataclasses WatchNotification, WatchApprovalRequest, WatchStatus
- ✅ Flujo singleton + storage local JSON
- ✅ Interfaz Vue MobileCompanionJarvis.vue (needs API alignment)
- ✅ Concepto de "aprobaciones rápidas desde el reloj"
- ✅ MERLIN Chat mini integrado

**Qué cambia para V15:**
- 🔄 Autenticación: JWT tokens del AuthManager (no storage aislado)
- 🔄 Sincronización: Event Bus → Wear OS (no silo aislado)
- 🔄 API calls: Endpoints reales `/api/...` (no métodos locales puros)
- 🔄 Seguridad: Token validation, device binding, rate limiting
- 🔄 Offline-first: Cache local sincronizado cuando recupera conexión

**Principio V15 cumplido:** "Cualquier persona debe poder utilizar OWNEX sin conocer su arquitectura" — el usuario del reloj ve alertas y botones de ✓/✗, no necesita saber que hay un AuthManager, event_bus, o JWT tokens detrás. Eso permanece oculto.

---

**Próximo paso:** Actualizar `cores/wear_os/integration.py` para usar auth validation + endpoints API, manteniendo compatibilidad backwards con storage local existente.