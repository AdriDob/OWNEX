# Sincronización Mobile Companion — Plan de Implementación

## Estado Actual

**Apps actuales (Demo):**
- Android Companion: Datos simulados, no hay sincronización real
- Wear OS Companion: Datos simulados, no hay sincronización real
- No hay autenticación con cuenta OWNEX
- No hay vinculación con PC
- No hay comunicación real con backend

## Opciones de Sincronización

### Opción 1: Vinculación con PC (Local Sync)

**Cómo funciona:**
- PC corre servidor OWNEX con WebSocket server
- App Android se conecta al PC vía Wi-Fi o Bluetooth
- Sincronización en tiempo real sin necesidad de internet
- QR code pairing para vincular dispositivos

**Archivos a crear:**
- `cores/mobile/pc_sync.py` — PC sync server
- `api/routers/mobile_sync.py` — API endpoints para mobile sync
- Android: `pc_sync/` package con Bluetooth/Wi-Fi Direct
- Wear OS: `pc_sync/` package con Bluetooth sync

**Pros:**
- Sincronización local (sin internet)
- Latencia baja
- Más privado (no pasa por nube)
- Funciona offline

**Contras:**
- PC debe estar encendido
- Requiere configuración de red
- Más complejo de implementar

### Opción 2: Vinculación con Cuenta OWNEX (Cloud Sync)

**Cómo funciona:**
- Usuario crea cuenta OWNEX (email/password)
- App Android se autentica con la cuenta
- Sincronización vía backend en la nube
- Datos sincronizados en todos los dispositivos

**Archivos a crear:**
- `cores/auth/user_auth.py` — Sistema de autenticación de usuarios
- `api/routers/auth_user.py` — Auth endpoints (login, register, logout)
- Database: `users` table, `sessions` table, `devices` table
- Android: `auth/` package con login/register UI
- Wear OS: `auth/` package con auth UI

**Pros:**
- Funciona desde cualquier lugar
- Historial persistente
- Multi-device sync fácil
- No requiere PC encendido

**Contras:**
- Requiere internet
- Latencia más alta
- Datos en la nube (menos privado)

### Opción 3: Híbrido (PC + Cloud) — **RECOMENDADO**

**Cómo funciona:**
- App puede sincronizar con PC (local) cuando está cerca
- App también puede sincronizar con cloud cuando PC no está disponible
- Prioridad local sobre cloud
- Fallback automático

**Archivos a crear:**
- Todo de Opción 1 + Opción 2
- `cores/mobile/hybrid_sync.py` — Hybrid sync manager
- Lógica de prioridad y fallback

**Pros:**
- Mejor de ambos mundos
- Sincronización local cuando es posible
- Cloud sync como fallback
- Máxima flexibilidad

**Contras:**
- Más complejo de implementar
- Más tiempo de desarrollo

---

## Plan de Implementación (Híbrido)

### Fase 1: Autenticación de Usuarios (Cloud)

**Backend:**
```python
# cores/auth/user_auth.py
class UserAuth:
    -register(email, password, device_info)
    -login(email, password, device_info)
    -logout(session_token)
    -verify_token(session_token)
    -refresh_token(refresh_token)
```

**Database:**
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE sessions (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    device_type VARCHAR(50),
    device_token VARCHAR(255),
    access_token VARCHAR(255),
    refresh_token VARCHAR(255),
    expires_at TIMESTAMP
);

CREATE TABLE devices (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    device_type VARCHAR(50),
    device_name VARCHAR(255),
    last_seen TIMESTAMP
);
```

**API Endpoints:**
- `POST /api/auth/register` — Register new user
- `POST /api/auth/login` — Login
- `POST /api/auth/logout` — Logout
- `POST /api/auth/refresh` — Refresh token
- `GET /api/auth/verify` — Verify token

**Android:**
- Login screen con email/password
- Register screen
- Token storage (EncryptedSharedPreferences)
- Auto-login con token guardado

**Wear OS:**
- Pair con Android Companion (Bluetooth)
- Heredar auth de Android
- No auth directo (seguridad)

### Fase 2: PC Sync (Local)

**Backend:**
```python
# cores/mobile/pc_sync.py
class PCSyncServer:
    -start_server(host, port)
    -stop_server()
    -handle_connection(client_socket)
    -broadcast_message(message)
    -get_connected_devices()
```

**API Endpoints:**
- `GET /api/pc/sync/status` — PC sync status
- `POST /api/pc/sync/pair` — Initiate pairing
- `GET /api/pc/sync/qr` — Get QR code for pairing
- `POST /api/pc/sync/approve` — Approve device pairing

**Android:**
- `pc_sync/PCSyncManager.kt` — PC sync manager
- WiFi Direct para descubrimiento
- QR code generation/scanning
- WebSocket client para comunicación
- Bluetooth pairing

**Wear OS:**
- Bluetooth sync con Android Companion
- No directo con PC (por seguridad)

### Fase 3: Hybrid Sync Manager

**Backend:**
```python
# cores/mobile/hybrid_sync.py
class HybridSyncManager:
    - sync_with_pc(data) — Try PC sync first
    - sync_with_cloud(data) — Fallback to cloud
    - get_sync_status() — Current sync mode
    - prioritize_sync() — Choose sync method
```

**Logic:**
1. Check if PC is available (ping/heartbeat)
2. If PC available → sync with PC
3. If PC not available → sync with cloud
4. Queue changes for when PC comes back online
5. Bidirectional sync (PC ↔ Cloud)

---

## Arquitectura de Comunicación

### Local Sync (PC ↔ Mobile)

```
PC (OWNEX Server)
    ↓ WebSocket (ws://192.168.1.100:8000/ws)
Android Companion
    ↓ Bluetooth
Wear OS Companion
```

### Cloud Sync (Backend ↔ Mobile)

```
Backend (API Server)
    ↓ HTTPS (api.ownex.com)
Android Companion
    ↓ Bluetooth
Wear OS Companion
```

### Hybrid Sync

```
PC (OWNEX Server)
    ↓ Local WebSocket
Android Companion
    ↓ HTTPS Cloud
Backend (API Server)
    ↓ Bluetooth
Wear OS Companion
```

---

## Implementación Detallada

### Step 1: User Authentication (Priority 1)

**Files to create:**
1. `cores/auth/user_auth.py` — User auth system
2. `api/routers/auth_user.py` — Auth API endpoints
3. `database/migrations/001_add_users.sql` — Database migration
4. Android: `app/src/main/java/ai/catseye/app/auth/` — Auth UI
5. Wear OS: `app/src/main/java/ai/catseye/wearos/auth/` — Auth bridge

**Estimated time:** 4-6 hours

### Step 2: PC Sync Server (Priority 2)

**Files to create:**
1. `cores/mobile/pc_sync.py` — PC sync server
2. `api/routers/pc_sync.py` — PC sync API
3. Android: `app/src/main/java/ai/catseye/app/pc_sync/` — PC sync manager
4. Backend WebSocket server

**Estimated time:** 6-8 hours

### Step 3: Cloud Sync API (Priority 3)

**Files to create:**
1. `cores/mobile/cloud_sync.py` — Cloud sync manager
2. API endpoints para sync data
3. Mobile sync client libraries

**Estimated time:** 4-6 hours

### Step 4: Hybrid Sync Manager (Priority 4)

**Files to create:**
1. `cores/mobile/hybrid_sync.py` — Hybrid sync manager
2. Logic de prioridad y fallback
3. Queue system para offline sync

**Estimated time:** 4-6 hours

### Step 5: Mobile UI Updates (Priority 5)

**Files to modify:**
1. Android: Add login/register screens
2. Android: Add PC pairing screen
3. Android: Add sync status indicator
4. Wear OS: Add pairing with Android
5. Wear OS: Add sync status

**Estimated time:** 4-6 hours

---

## Cronograma de Implementación

### Día 1 (6-8 horas)
- User Authentication (register, login, logout)
- Database schema for users, sessions, devices
- Android auth UI

### Día 2 (6-8 horas)
- PC Sync Server (WebSocket server)
- PC Sync API endpoints
- Android PC sync manager
- QR code pairing

### Día 3 (4-6 horas)
- Cloud Sync Manager
- API endpoints para cloud sync
- Mobile sync client

### Día 4 (4-6 horas)
- Hybrid Sync Manager
- Priority logic
- Fallback system

### Día 5 (4-6 horas)
- Mobile UI updates
- Login/register screens
- PC pairing screens
- Sync status indicators

**Total:** 24-40 horas de desarrollo

---

## Alternativa Rápida (MVP)

Si quieres algo rápido para empezar:

**Solo Cloud Sync (sin PC local):**
- Implementar solo autenticación de usuarios
- Implementar solo cloud sync via API
- Android y Wear OS se conectan directamente al backend
- Tiempo estimado: 8-12 horas

**Esto permitiría:**
- ✅ Login con cuenta OWNEX
- ✅ Sincronización desde cualquier lugar
- ✅ Multi-device sync
- ❌ Sincronización local sin internet
- ❌ Comunicación directa con PC

---

## Recomendación

**Para empezar:**
1. Implementar **Solo Cloud Sync** (8-12 horas)
2. Esto te dará sincronización funcional rápidamente
3. Luego agregar **PC Sync** más adelante

**Para completa experiencia:**
1. Implementar **Hybrid Sync** completo (24-40 horas)
2. Mejor experiencia de usuario
3. Máxima flexibilidad

---

## Pregunta para Ti

**¿Qué prefieres?**

**Opción A:** Implementar solo Cloud Sync (rápido, 8-12 horas)
- Login con cuenta OWNEX
- Sincronización vía nube
- Funciona desde cualquier lugar

**Opción B:** Implementar Hybrid Sync completo (completo, 24-40 horas)
- Sincronización local con PC
- Sincronización cloud como fallback
- Mejor experiencia de usuario

**Opción C:** Implementar solo PC Sync (medio, 12-16 horas)
- Sincronización local con PC
- Sin sincronización cloud
- Más privado, pero limitado

Dime qué opción prefieres y la implemento.
