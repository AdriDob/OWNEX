# ORION Companion — Guía de Configuración Profesional

Guía completa de configuración de ORION Companion para Android y Wear OS, estilo producto comercial premium.

## 📋 Tabla de Contenidos

1. [Requisitos](#requisitos)
2. [Instalación Desktop](#instalación-desktop)
3. [Companion Android](#companion-android)
4. [Watch Companion Wear OS](#watch-companion-wear-os)
5. [Configuración Guiada](#configuración-guiada)
6. [Health Check](#health-check)
7. [Seguridad](#seguridad)
8. [Actualizaciones](#actualizaciones)
9. [Solución de Problemas](#solución-de-problemas)

---

## 📦 Requisitos

### Desktop
- **OS**: Windows 10+, macOS 10.15+, Linux (Ubuntu 20.04+)
- **Python**: 3.11+
- **RAM**: 8GB mínimo, 16GB recomendado
- **Espacio**: 10GB libre
- **Internet**: Conexión estable

### Android Companion
- **OS**: Android 10+ (API 29+)
- **RAM**: 4GB mínimo
- **Espacio**: 500MB libre
- **Bluetooth**: 4.0+
- **Internet**: Conexión estable

### Wear OS
- **OS**: Wear OS 3+
- **RAM**: 2GB mínimo
- **Espacio**: 100MB libre
- **Bluetooth**: 4.0+
- **Internet**: Conexión estable (WiFi o celular)

---

## 💻 Instalación Desktop

### 1. Descargar ORION

```bash
# Clonar repositorio
git clone https://github.com/your-repo/Rastro.git
cd Rastro

# Ejecutar instalador universal
python install.py
```

### 2. Configuración Inicial

El instalador ejecutará automáticamente el **Enhanced Personalization Wizard**:

```
┌─────────────────────────────────────────┐
│  🧙 Enhanced Personalization Wizard     │
│  Jarvis 2030 Style                      │
└─────────────────────────────────────────┘

Paso 1/8: Welcome
─────────────────────────────────
¿Cómo te llamas? [Adriel]
¿Cómo prefieres que te llame? [Adriel]

Paso 2/8: Experience
─────────────────────────────────
¿Cuál es tu nivel de experiencia?
○ Principiante - Estoy aprendiendo
● Intermedio - Tengo algo de experiencia
○ Avanzado - Tengo experiencia sólida
○ Experto - Soy profesional

¿En qué quieres trabajar principalmente?
● Bug Bounty - Encontrar vulnerabilidades
○ Dev Bounty - Encontrar bugs en código
○ Data Annotation - Anotación de datos
○ Freelance - Varios proyectos
○ Mixto - Un poco de todo

Paso 3/8: Guidance
─────────────────────────────────
¿Cuánta guía necesitas?
● Alta - Llévame de la mano paso a paso
○ Media - Guía cuando sea necesario
○ Baja - Solo sugerencias ocasionales
○ Autónomo - Prefiero hacerlo solo

[...]
```

### 3. Verificar Instalación

```bash
# Iniciar ORION
python run.py

# Verificar health
curl http://localhost:8000/api/health
```

---

## 📱 Companion Android

### 1. Instalar APK

Descargar el APK desde: `https://your-repo/releases/orion-companion-latest.apk`

```bash
# Instalar via ADB (opcional)
adb install orion-companion-latest.apk
```

### 2. Primer Inicio

Al abrir ORION Companion por primera vez:

```
┌─────────────────────────────────────────┐
│  📱 ORION Companion                    │
│  Android Extension                     │
└─────────────────────────────────────────┘

Welcome to ORION Companion!

Let's connect to your ORION Desktop.

[🔗 Connect to Desktop]
   IP Address: [192.168.1.100]
   Port: [8000]

[⚙️ Setup Connection]
   ✓ API Token
   ✓ Encryption Key
   ✓ Sync Interval
```

### 3. Conectar a Desktop

**Opción A: Auto-Discovery (Recomendado)**
- Ambos dispositivos en la misma red WiFi
- Companion detecta automáticamente el desktop
- Confirma la conexión

**Opción B: Manual**
- Ingresa la IP del desktop
- Ingresa el puerto (default: 8000)
- Genera y confirma el API token

### 4. Características del Companion

#### Dashboard Móvil
- Estado del sistema en tiempo real
- Findings totales/confirmados/pendientes
- Targets activos
- Scheduler status
- Próxima acción

#### MERLIN Chat
- Chat con el asistente
- Respuestas personalizadas
- Comandos de voz
- Notas rápidas

#### Notificaciones
- Alertas de workflows
- Errores del sistema
- Aprobaciones pendientes
- Oportunidades nuevas

#### Aprobaciones
- Aprobar workflows desde el móvil
- Ver detalles de aprobaciones
- Historial de decisiones

#### Targets
- Ver objetivos activos
- Status de escaneos
- Priorización

#### Capital
- Gestión financiera móvil
- Métricas de ingresos
- Proyecciones

---

## ⌚ Watch Companion Wear OS

### 1. Instalar desde Companion

**Transferencia desde Companion móvil:**
1. Abre ORION Companion en Android
2. Ve a Settings → Wear OS
3. Toca "Install on Watch"
4. Confirma la transferencia Bluetooth
5. El watch instalará automáticamente

**Alternativa: Manual**
```bash
# Instalar via ADB (requiere watch conectado)
adb -s <watch-id> install orion-watch-companion.apk
```

### 2. Vincular Watch

```
┌─────────────────────────────────────────┐
│  ⌚ ORION Watch Companion               │
│  Wear OS Extension                     │
└─────────────────────────────────────────┘

Connecting to ORION...

✓ Connection established
✓ Sync enabled
✓ Notifications active
```

### 3. Características del Watch

#### Notificaciones Críticas
- Alertas de alto nivel
- Errores del sistema
- Aprobaciones urgentes
- Solo lo importante

#### Aprobaciones Rápidas
- Aprobar con un tap
- Rechazar con un tap
- Ver detalles
- Historial breve

#### Estado del Sistema
- 🟢 ORION Online
- N workflows activos
- M aprobaciones pendientes
- Health score

#### MERLIN Resumen
- Decisiones importantes
- Resumen diario
- Alertas personalizadas
- Progreso de objetivos

### 4. Modo Critical-Only

Para reducir notificaciones:

```
Settings → Notifications → Critical Only
```

Solo recibirás:
- Aprobaciones urgentes
- Errores críticos
- Alertas de seguridad

---

## ⚙️ Configuración Guiada

### Flujo Completo

```
Instalar → Conectar → Configurar → Verificar → Usar → Optimizar
```

### 1. Instalar

- Desktop: `python install.py`
- Android: Instalar APK
- Wear OS: Transferir desde Companion

### 2. Conectar

- Desktop ↔ Android: WiFi local
- Android ↔ Wear OS: Bluetooth
- Verificar: Status indicators 🟢

### 3. Configurar

**Identity**
- Nombre de usuario
- API Token
- Encryption Key

**Desktop**
- IP Address
- Port
- Sync Interval

**COPILOT**
- Guidance Level
- Work Mode
- Voice Enabled

**Integrations**
- Obsidian
- Calendario
- Email

**Smartwatch**
- Critical Only
- Notification Level
- Sync Frequency

### 4. Verificar

**Desktop Health Check**
```bash
python run.py --health-check
```

**Android Health Check**
```
Settings → Diagnostics → Run Health Check
```

**Wear OS Health Check**
```
Settings → Health → System Status
```

### 5. Usar

- Dashboard → Ver estado
- MERLIN → Chat y comandos
- Tasks → Gestión de tareas
- Settings → Configuración

### 6. Optimizar

- Ajustar sync intervals
- Configurar notificaciones
- Personalizar dashboard
- Optimizar battery usage

---

## 🏥 Health Check

### Diagnóstico Automático

**Desktop**
```bash
python run.py --health-check
```

Output:
```
ORION Health Check
══════════════════

✓ System Online
✓ Scheduler Running
✓ EventBus Active
✓ AgentBus Active
✓ RecoveryEngine Running
✓ Database Connected
✓ API Server Running

Health Score: 95/100
```

**Android**
```
Settings → Diagnostics → Run Health Check
```

Output:
```
ORION Companion Health Check
════════════════════════════

✓ Desktop Connected
✓ API Token Valid
✓ Sync Active
✓ Notifications Enabled
✓ Wear OS Connected

Health Score: 98/100
```

**Wear OS**
```
Settings → Health → System Status
```

Output:
```
ORION Watch Health Check
════════════════════════

✓ Companion Connected
✓ Sync Active
✓ Notifications Active
✓ Battery Normal

Health Score: 100/100
```

### Indicadores de Salud

| Componente | 🟢 Healthy | 🟡 Warning | 🔴 Critical |
|-----------|-----------|-----------|------------|
| Desktop API | Response < 100ms | Response < 500ms | Response > 500ms |
| Scheduler | Running | Delayed | Stopped |
| Database | Connected | Slow | Disconnected |
| Companion | Connected | Sync delayed | Disconnected |
| Watch | Connected | Sync delayed | Disconnected |

---

## 🔒 Seguridad

### Autenticación

**Desktop**
- API Token generado automáticamente
- Rotación cada 30 días
- Encrypted at rest

**Android**
- Biometric unlock (opcional)
- API Token encrypted
- Session timeout: 1h

**Wear OS**
- No authentication (trusted device)
- Secure pairing with Companion
- Auto-lock after 5m inactivity

### Dispositivos Conectados

**Ver dispositivos:**
```
Settings → Security → Connected Devices
```

**Desconectar dispositivo:**
```
Settings → Security → Device → Disconnect
```

### Sesiones

**Ver sesiones activas:**
```
Settings → Security → Active Sessions
```

**Cerrar sesión:**
```
Settings → Security → Session → Revoke
```

---

## 🔄 Actualizaciones

### Desktop

**Auto-update (enabled by default):**
```bash
python run.py --update
```

**Manual:**
```bash
git pull
python install.py
```

### Android

**Auto-update:**
```
Settings → Updates → Auto-update: On
```

**Manual:**
```
Settings → Updates → Check for Updates
```

### Wear OS

**Auto-update:**
```
Settings → Updates → Auto-update: On
```

**Manual:**
```
Settings → Updates → Check for Updates
```

---

## 🔧 Solución de Problemas

### Desktop no responde

**Síntomas:**
- API timeout
- Health check fails
- Scheduler stopped

**Soluciones:**
```bash
# 1. Verificar logs
python run.py --logs

# 2. Reiniciar servicios
python run.py --restart

# 3. Verificar puerto
lsof -i :8000

# 4. Limpiar cache
python run.py --clean-cache
```

### Companion no conecta

**Síntomas:**
- Connection timeout
- API invalid
- Sync fails

**Soluciones:**
```
1. Verificar WiFi (mismo network)
2. Verificar IP address correcta
3. Regenerar API token
4. Desconectar y reconectar
5. Reinstalar Companion
```

### Watch no sincroniza

**Síntomas:**
- Notifications not received
- Sync fails
- Status outdated

**Soluciones:**
```
1. Verificar Bluetooth pairing
2. Verificar Companion connected
3. Force sync: Settings → Sync → Force Sync
4. Reinstall Watch Companion
5. Restart watch
```

### Notificaciones no llegan

**Síntomas:**
- No notifications on Android
- No notifications on Watch
- Delayed notifications

**Soluciones:**
```
1. Verificar permissions granted
2. Verificar notifications enabled
3. Verificar battery optimization disabled
4. Verificar critical-only mode
5. Force sync
```

---

## 📞 Soporte

### Documentación
- Wiki: https://wiki.orion.dev
- API Docs: https://api.orion.dev
- Forums: https://community.orion.dev

### Contacto
- Email: support@orion.dev
- Discord: https://discord.gg/orion
- Twitter: @orion_dev

---

## 🎯 Roadmap

### Próximas Features
- [ ] iOS Companion (beta)
- [ ] Watch OS Companion
- [ ] Advanced Analytics
- [ ] Custom Dashboards
- [ ] Voice Commands Enhanced
- [ ] Offline Mode
- [ ] Multi-device Sync
- [ ] Cloud Backup

---

**ORION Companion — Premium Minimalist Cyber Intelligence**

*Designed for professionals who demand excellence.*
