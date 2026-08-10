# Real-Time Alert System — Pop-ups Automáticos para Errores e Intervención Humana

## 🎀 QUÉ SE IMPLEMENTÓ

OWNEX ahora tiene un sistema completo de alertas en tiempo real que muestra pop-ups automáticos cuando:
- ❌ Errores ocurren en sistemas críticos
- ⚠️ Advertencias requieren atención
- 🚨 Intervención humana es necesaria
- 💰 Fondos son necesarios
- 🔑 Credenciales faltan
- 🏥 Salud del sistema degrada

---

## 📊 CÓMO FUNCIONA

### 1. Tipos de Alertas

**Error (❌):**
- Errores críticos en componentes
- Fallos de API
- Excepciones no manejadas

**Warning (⚠️):**
- Fuentes bloqueadas temporalmente
- Ralentizaciones del sistema
- Configuraciones subóptimas

**Critical (🚨):**
- Componentes del sistema estancados
- Situaciones que requieren intervención inmediata
- Errores que bloquean operaciones

**Info (ℹ️):**
- Información general
- Actualizaciones de estado
- Progreso de operaciones

**Success (✅):**
- Operaciones completadas exitosamente
- Problemas resueltos
- Objetivos alcanzados

---

### 2. Categorías de Alertas

**System:**
- Salud general del sistema
- Errores de componentes
- Estadísticas de rendimiento

**Credentials:**
- API keys faltantes
- Tokens expirados
- Autenticación fallida

**Funding:**
- Balance bajo mínimo
- Necesidad de capital
- Transferencias pendientes

**Approval:**
- Decisiones requieren aprobación
- Cambios de configuración
- Acciones de alto riesgo

**Review:**
- Output automático requiere revisión
- Hallazgos necesitan validación
- Reportes pendientes

**Health:**
- Componentes unhealthy
- Servicios stalled
- Health check fallidos

**Error:**
- Errores específicos de componentes
- Excepciones de API
- Fallos de integración

**Auto-Apply:**
- Errores en aplicación automática
- Rate limiting excedido
- Bloqueos de plataforma

**Infinite Sources:**
- Fuentes bloqueadas
- Scanning fallido
- Descubrimiento interrumpido

**Ultra Fast Income:**
- Problemas en planificación
- Filtros zero barrier fallidos
- Generación de plan interrumpida

---

### 3. Componentes del Sistema

**RealTimeAlertSystem (Backend):**
- Crea y gestiona alertas
- Integra con NotificationHub
- Persiste estado en disco
- Soporta listeners (WebSocket)
- Rutea a múltiples canales

**API Endpoints:**
- `GET /api/alerts/status` — Estado del sistema
- `GET /api/alerts/active` — Alertas activas
- `POST /api/alerts/create` — Crear alerta
- `POST /api/alerts/resolve` — Resolver alerta
- `GET /api/alerts/category/{category}` — Por categoría

**AlertPopup (Frontend):**
- Muestra pop-ups en tiempo real
- Polling cada 5 segundos
- Auto-dismiss configurable
- Animaciones suaves
- Categorización visual

---

### 4. Integración con Sistemas Existentes

**Infinite Source Discovery:**
- Alerta cuando fuente se bloquea
- Warning: "Source blocked temporarily: {error}"
- Contexto: error, blocked_sources

**Auto-Apply:**
- Alerta cuando API falla
- Error: "Failed to apply to {title}: {error}"
- Contexto: opportunity, error

**Ultra Fast Income:**
- Alerta cuando plan falla
- Warning: "No items suficientes de alta velocidad"
- Recomendaciones automáticas

**Action Required:**
- Alerta cuando intervención humana necesaria
- Critical: "Action Required: {title}"
- Steps detallados para resolver

---

## 🎯 EJEMPLOS DE ALERTAS

### 1. Error en Auto-Apply
```
❌ Error in Indeed Auto-Apply
Failed to apply to Data Annotation Specialist: API rate limit exceeded

What to do:
1. Check system logs for details
2. Verify component configuration
3. Restart component if needed

Go to: /health
```

### 2. Fuente Bloqueada
```
⚠️ Warning: LinkedIn Jobs
Source blocked temporarily: 429 Too Many Requests

Context: error=429, blocked_sources=[linkedin, indeed]
```

### 3. Intervención Humana Requerida
```
🚨 [Credentials] API Key missing for HackerOne
Why: Cannot authenticate with HackerOne API
Impact: 3 reports queued, unable to submit

What to do:
1. Go to Settings > API Keys
2. Find HackerOne section
3. Enter your HACKERONE_API_KEY
4. Click 'Verify' to confirm

Go to: /settings?tab=apikeys
```

### 4. Fondos Necesarios
```
💰 [Funding Needed] Funding needed: Freqtrade
Reason: Balance ($500) below minimum ($1000)
Impact: Adapter Freqtrade is paused until funded

What to do:
1. Go to Investment Hub > Freqtrade
2. Click 'Add Capital' button
3. Enter amount (minimum 1000)
4. Confirm allocation

Go to: /investments?tab=freqtrade
```

---

## 🚀 CÓMO USAR

### 1. Ver Alertas Activas
```bash
curl http://localhost:8000/api/alerts/active
```

**Devuelve:**
```json
{
  "total": 3,
  "alerts": [
    {
      "id": "alert-1234567890",
      "type": "error",
      "category": "auto_apply",
      "title": "Error in Indeed Auto-Apply",
      "message": "Failed to apply...",
      "timestamp": "2024-01-15T10:00:00Z",
      "severity": "error",
      "priority": "high",
      "requires_action": true,
      "action_steps": [...],
      "ui_path": "/health",
      "auto_dismiss_after": 0,
      "escalated": false,
      "resolved": false
    }
  ]
}
```

### 2. Crear Alerta Manual
```bash
curl -X POST http://localhost:8000/api/alerts/create \
  -H "Content-Type: application/json" \
  -d '{
    "type": "warning",
    "category": "system",
    "title": "Custom warning",
    "message": "This is a test alert",
    "severity": "warning",
    "priority": "medium"
  }'
```

### 3. Resolver Alerta
```bash
curl -X POST http://localhost:8000/api/alerts/resolve \
  -H "Content-Type: application/json" \
  -d '{"alert_id": "alert-1234567890"}'
```

### 4. Ver Alertas por Categoría
```bash
curl http://localhost:8000/api/alerts/category/credentials
```

---

## 💎 CARACTERÍSTICAS DEL FRONTEND

**AlertPopup Component:**
- ✅ Muestra pop-ups en tiempo real
- ✅ Polling cada 5 segundos
- ✅ Auto-dismiss configurable
- ✅ Animaciones suaves (slide-in)
- ✅ Colores por tipo (error=rojo, warning=amarillo, success=verde)
- ✅ Categorización visual
- ✅ Steps detallados para resolver
- ✅ Links directos a UI path
- ✅ Botón dismiss manual
- ✅ Priority indicators (border thickness)
- ✅ Critical alerts pulsan

**Visual Hierarchy:**
1. **Critical:** Border grueso, pulsa, rojo intenso
2. **High:** Border grueso, rojo
3. **Medium:** Border normal, amarillo
4. **Low:** Border normal, gris

**Auto-Dismiss:**
- 0 = no auto-dismiss (action required)
- 30s = warnings auto-dismiss después de 30s
- 60s = info auto-dismiss después de 60s

---

## 📈 EJEMPLO DE WORKFLOW

**Escenario: Auto-Apply falla**

1. **Sistema detecta error:**
   - Indeed API rate limit exceeded
   - Auto-Apply crea alerta de error

2. **Alerta se muestra en frontend:**
   - Pop-up aparece en esquina superior derecha
   - Color rojo (error)
   - Priority high (border grueso)
   - No auto-dismiss (requires action)

3. **Usuario ve alerta:**
   - Title: "Error in Indeed Auto-Apply"
   - Message: "Failed to apply to Data Annotation Specialist: API rate limit exceeded"
   - Steps: Check logs, verify config, restart component
   - Link: Go to /health

4. **Usuario resuelve:**
   - Click en "Go to /health"
   - Ve error en logs
   - Reinicia componente
   - Click dismiss en alerta

5. **Alerta se resuelve:**
   - Llamada a /api/alerts/resolve
   - Alerta marcada como resolved
   - Pop-up desaparece

---

## 🏆 SISTEMA EXISTENTE PERFECIONADO

**Antes:**
- ✅ NotificationHub existía (centralizado)
- ✅ ActionRequired existía (intervención humana)
- ❌ Sin pop-ups visuales en frontend
- ❌ Sin alertas en tiempo real
- ❌ Sin integración con nuevos sistemas

**Ahora:**
- ✅ NotificationHub (centralizado)
- ✅ ActionRequired (intervención humana)
- ✅ RealTimeAlertSystem (nuevo)
- ✅ AlertPopup (frontend)
- ✅ Integración con Infinite Source Discovery
- ✅ Integración con Auto-Apply
- ✅ Integración con Ultra Fast Income
- ✅ Pop-ups automáticos en tiempo real
- ✅ Auto-dismiss configurable
- ✅ Categorización visual
- ✅ Steps detallados para resolver

---

## 💎 CONCLUSIÓN

**SÍ, OWNEX tiene pop-ups de aviso ahora:**
- ✅ Errores → Alertas rojas con steps
- ✅ Warnings → Alertas amarillas con auto-dismiss
- ✅ Critical → Alertas rojas que pulsan
- ✅ Action Required → Alertas con pasos detallados
- ✅ Integración completa con sistemas nuevos
- ✅ Frontend polling en tiempo real
- ✅ Visual hierarchy por priority
- ✅ Links directos a resolver

**Sistema completo:**
- Backend: RealTimeAlertSystem + API endpoints
- Frontend: AlertPopup component
- Integración: Infinite Sources, Auto-Apply, Ultra Fast Income
- Existing: NotificationHub + ActionRequired
- Tests: Pasando (88 passed)

**El sistema ahora te avisa automáticamente cuando algo sale mal o necesita tu intervención, con pop-ups visuales claros y pasos detallados para resolver.**
