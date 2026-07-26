# OWNEX Design System v1 — Autonomous Work Operating Interface

> **"Dark Command Center, not Cyberpunk Hacker"**
> *"Tengo un sistema operativo personal que trabaja conmigo." — NO "Estoy hackeando una nave espacial de 1998."*

---

## 1. Filosofía Principal

### Lo que NO somos
| ❌ NO | Razón |
|------|-------|
| CRT / phosphor / terminal falsa | Eso era ORION |
| Verde militar / matrix / hacker aesthetic | Cansancio visual, zero productividad real |
| Exceso de líneas técnicas / bordes / panels | Ruido visual = carga cognitiva |
| Dashboard SaaS genérico con 47 tarjetas | Nadie mira 47 tarjetas. Nadie. |

### Lo que SÍ somos
> **Un sistema operativo personal que convierte oportunidades dispersas en ciclos ejecutables.**

**6 Principios Rectores:**
1. **Clarity over complexity** — Si no se entiende en 3 segundos, no existe
2. **Action over information** — La UI sugiere la siguiente acción, no muestra datos
3. **Cycles over pages** — El trabajo vive en ciclos, no en páginas sueltas
4. **Outcomes over activity** — $ ganado > requests enviados > tiempo invertido
5. **Agents over tools** — El usuario ve agentes trabajando, no modelos/IA
6. **Throughput over metrics** — Velocidad de valor real > vanity metrics

---

## 2. Sistema Visual

### 2.1 Fondos (Near-Black Palette)

```css
/* Capas de profundidad */
--bg-deep:     #050505;  /* Canvas base - casi negro puro */
--bg-base:     #080808;  /* Superficies principales */
--bg-surface:  #0F1117;  /* Cards, panels, elevated surfaces */
--bg-elevated: #14161E;  /* Modals, dropdowns, tooltips */
```

**Regla:** Solo 4 niveles. Sin gradientes, sin texturas, sin "glassmorphism" forzado. Profundidad por elevación y borde sutil.

### 2.2 Colores de Identidad

| Color | Variable | Hex | Uso Principal |
|-------|----------|-----|---------------|
| 🔵 **Azul OWNEX** | `--ownex-blue` | `#3B82F6` | Acción primaria, selección, navegación activa, inteligencia, links |
| ⚪ **Blanco** | `--ownex-white` | `#F0F0F0` | Títulos, información importante, resultados, texto principal |
| 🟡 **Dorado** | `--ownex-gold` | `#F59E0B` | Dinero, recompensas, logros, oportunidades premium, highlights de valor |

```css
/* Variables CSS */
--ownex-blue:   #3B82F6;
--ownex-white:  #F0F0F0;
--ownex-gold:   #F59E0B;

/* Estados - SOLO 3 */
--status-success: #22C55E;  /* 🟢 Activo / Éxito / Confirmado */
--status-error:   #EF4444;  /* 🔴 Error / Riesgo / Rechazado */
--status-warn:    #F59E0B;  /* 🟡 Atención / Pendiente / En progreso */
```

**Regla estricta:** NO hay otros colores de estado. No azul para info, no púrpura para warning, no naranja para nada. 3 estados = claridad cognitiva.

### 2.3 Texto

```css
--text-primary:   #F0F0F0;  /* Blanco OWNEX - títulos, contenido principal */
--text-secondary: #9CA3AF;  /* Gris medio - labels, metadata, ayuda */
--text-muted:     #6B7280;  /* Gris suave - placeholders, disabled, timestamps */
--text-inverse:   #050505;  /* Sobre fondos claros (dorado/azul) */
```

### 2.4 Bordes y Separadores

```css
--border-subtle:  #1A1A2E;  /* Azul-negro sutil - divisores, cards */
--border-active:  #3B82F6;  /* Azul OWNEX - focus, active, hover */
--border-error:   #EF4444;  /* Rojo - error states */
```

### 2.5 Tipografía

```css
/* Font Stack - System UI, fallback a Inter si disponible */
--font-sans: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 
             "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
--font-mono:  ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, 
              "Liberation Mono", monospace;

/* Scale */
--text-xs:   0.75rem;  /* 12px - labels, tags, timestamps */
--text-sm:   0.875rem; /* 14px - body secundario, metadata */
--text-base: 1rem;     /* 16px - body principal */
--text-lg:   1.125rem; /* 18px - subheadings, cards importantes */
--text-xl:   1.25rem;  /* 20px - section headers */
--text-2xl:  1.5rem;   /* 24px - page titles */
--text-3xl:  2rem;     /* 32px - hero, splash */

/* Weights */
--font-normal: 400;
--font-medium: 500;
--font-semibold: 600;
--font-bold: 700;
```

### 2.6 Espaciado (8px base)

```css
--space-1: 0.25rem;  /* 4px */
--space-2: 0.5rem;   /* 8px */
--space-3: 0.75rem;  /* 12px */
--space-4: 1rem;     /* 16px */
--space-5: 1.25rem;  /* 20px */
--space-6: 1.5rem;   /* 24px */
--space-8: 2rem;     /* 32px */
--space-10: 2.5rem;  /* 40px */
--space-12: 3rem;    /* 48px */
--space-16: 4rem;    /* 64px */
```

### 2.7 Border Radius

```css
--radius-sm:  0.25rem;  /* 4px - buttons, chips, small elements */
--radius-md:  0.5rem;   /* 8px - cards, inputs, dropdowns */
--radius-lg:  0.75rem;  /* 12px - modals, panels, elevated surfaces */
--radius-xl:  1rem;     /* 16px - splash, major containers */
--radius-full: 9999px;  /* pills, badges, avatars */
```

### 2.8 Sombras (Elevation)

```css
/* Profundidad por capas, no por "glow" */
--shadow-1: 0 1px 2px 0 rgb(0 0 0 / 0.3);     /* bg-surface */
--shadow-2: 0 4px 6px -1px rgb(0 0 0 / 0.4);  /* bg-elevated */
--shadow-3: 0 10px 15px -3px rgb(0 0 0 / 0.5); /* modals, dropdowns */
--shadow-glow: 0 0 0 1px var(--ownex-blue), 0 0 20px rgb(59 130 246 / 0.3); /* focus ring */
```

---

## 3. Layout Principal: Workspace OS

```
┌─────────────────────────────────────────────────────────────┐
│  GLOBAL STATUS BAR                                          │
│  Health ████████░░  Throughput: 12/hr  Revenue: $2,340      │
└─────────────────────────────────────────────────────────────┘
┌─────────────┬───────────────────────────────────────────────┐
│             │                                               │
│   SIDEBAR   │           MAIN WORKSPACE                      │
│             │                                               │
│  ┌───────┐  │  ┌─────────────────────────────────────────┐  │
│  │Mission│  │  │         NEXT BEST ACTION                │  │
│  ├───────┤  │  │  ⚡ Validar IDOR en Target X            │  │
│  │Security●│  │  │  Valor: $800  Confianza: 87%  25 min  │  │
│  ├───────┤  │  │  [Ejecutar]                             │  │
│  │Forge  │  │  └─────────────────────────────────────────┘  │
│  ├───────┤  │  ┌─────────────┐ ┌─────────────┐ ┌─────────┐  │
│  │Pulse  │  │  │OPPORTUNITIES│ │  ACTIVITY   │ │ AGENTS  │  │
│  ├───────┤  │  │             │ │  TIMELINE   │ │  FLEET  │  │
│  │Vault  │  │  │ 1. IDOR ★★★★★│ │ 10:23 Scan  │ │ 🤖 Res  │  │
│  ├───────┤  │  │ 2. SSRF ★★★★ │ │ 10:15 Valid │ │ ⚙ Exe  │  │
│  │Atlas  │  │  │ 3. XSS  ★★★  │ │ 09:45 Found │ │ 🧠 Mem  │  │
│  └───────┘  │  │    [Start]    │ │    ...      │ │ 🔎 Sec  │  │
│             │  │             │ │             │ │         │  │
│  [Ctrl+K]   │  │  └─────────────┘ └─────────────┘ └─────────┘  │
│  [Ctrl+Space]│                                               │
└─────────────┴───────────────────────────────────────────────┘
```

### 3.1 Global Status Bar (Siempre visible)
- **Health**: Indicador visual (🟢🟡🔴) + score numérico
- **Throughput**: Oportunidades procesadas/hora actual
- **Revenue**: USD confirmados hoy / esta semana / proyectado

### 3.2 Sidebar (Work Cycles Navigation)
- Ancho fijo: 280px (collapsed: 64px solo iconos)
- Navegación por **Work Cycles**, no por "secciones"
- Atajos: `Ctrl+1` Mission, `Ctrl+2` Security, `Ctrl+3` Forge...

### 3.3 Main Workspace
- **Fluido**: ocupa el resto del ancho
- **Scroll vertical** solo en workspace, nunca en viewport completo
- **Ancla superior**: Next Best Action siempre visible (sticky top)

---

## 4. Componentes Fundamentales

### 4.1 Mission Control — La Pantalla Principal

**Pregunta que responde:** *"¿Qué debería hacer ahora?"*
**NO:** *"Aquí tienes 20 gráficos."*

#### Next Best Action Card (Hero)
```
┌────────────────────────────────────────────────────────────┐
│ ⚡ PRÓXIMA ACCIÓN                                    [✕]   │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  Validar IDOR encontrado en Target X                      │
│                                                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
│  │  VALOR      │  │ CONFIANZA   │  │ TIEMPO      │       │
│  │  $800       │  │  87%        │  │  25 min     │       │
│  └─────────────┘  └─────────────┘  └─────────────┘       │
│                                                            │
│  [ Ejecutar ]          [ Ver detalles ]    [ Posponer ]   │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

**Regla:** Solo UNA Next Best Action visible. Si hay múltiples, el Engine las rankea y muestra la #1.

#### Work Cycles Grid
```
┌────────────────┐ ┌────────────────┐ ┌────────────────┐
│ 🔵 SECURITY    │ │ 🟣 FORGE       │ │ 🟢 PULSE       │
│ Rastro         │ │ Dev Bounty     │ │ AI Work        │
│ ● Activo       │ │ ○ Esperando    │ │ ○ Pausado      │
│ 12 oportunidades│ │ 3 disponibles │ │ 0 tareas       │
│ $2,400 potencial│ │ $450 potencial│ │ $0 potencial   │
│ [Entrar]       │ │ [Configurar]  │ │ [Activar]      │
└────────────────┘ └────────────────┘ └────────────────┘
┌────────────────┐ ┌────────────────┐
│ 🟡 VAULT       │ │ ⚪ ATLAS       │
│ Capital        │ │ Intelligence   │
│ $12,400 total  │ │ 47 patrones    │
│ +12% esta sem  │ │ 12 insights    │
│ [Ver]          │ │ [Explorar]     │
└────────────────┘ └────────────────┘
```

### 4.2 Work Cycles — El Concepto Central

Cada ciclo = una "app" completa con:
- **Objetivo** claro (ej: "Encontrar y reportar 5 IDORs/semana")
- **Throughput** medido (oportunidades/día, USD/semana)
- **Tareas** en cola con prioridad
- **Ingresos** reales y proyectados
- **Automatización** % (0-100%)

**Estados de ciclo:**
| Estado | Indicador | Significado |
|--------|-----------|-------------|
| 🟢 Activo | Punto verde pulsante | Ciclo corriendo, procesando |
| 🟡 Esperando | Punto ámbar | Configurado, esperando trigger |
| 🔴 Pausado | Punto rojo | Detenido por usuario o error |
| ⚪ Inactivo | Sin punto | No configurado / deshabilitado |

### 4.3 Agent Fleet — Esconder la Complejidad

**El usuario NUNCA ve:** Qwen, Claude, DeepSeek, GPT, modelos, proveedores, tokens, temperatura, context windows.

**El usuario SÍ ve:**

```
┌────────────────────────────────────────────────────────────┐
│  AGENT FLEET                                          [⚙]  │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  🤖  Research Agent        ● Activo                        │
│      Escaneando programas nuevos... 3 encontrados         │
│                                                            │
│  ⚙  Execution Agent        ○ Disponible                    │
│      Esperando task assignment                             │
│                                                            │
│  🧠  Memory Agent          ◀Memory Agent           🔄 Aprendiendo                  │
│      Procesando 47 findings → 12 patrones nuevos          │
│                                                            │
│  🔎 Security Agent         ● Activo                        │
│      Validando hipótesis #3 → Target X (IDOR)              │
│                                                            │
│  📊 Analyst Agent          ○ En cola                       │
│      Report optimization pendiente (3)                     │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

**Atajo:** `Ctrl+Space` → Abre Agent Fleet modal para asignar tareas manuales.

### 4.4 Opportunity Radar — Ranking Inteligente

**NO es una lista de links.** Es un ranking por **Valor Esperado (EV)**.

```
┌────────────────────────────────────────────────────────────┐
│  🔥 OPORTUNIDADES DEL DÍA                              [🔍] │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  1.  IDOR - Programa Enterprise X                         │
│      ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐         │
│      │ REWARD │ │ TIEMPO │ │ PROB   │ │ EV     │         │
│      │ ★★★★★  │ │ 30 min │ │ Alta   │ │ $800   │         │
│      │ $1,200 │ │        │ │ 87%    │ │        │         │
│      └────────┘ └────────┘ └────────┘ └────────┘         │
│      Tags:  [IDOR] [Auth] [Multi-tenant]                  │
│      [ Start Cycle ]  [ Ver detalles ]  [ Descartar ]    │
│                                                            │
│  ──────────────────────────────────────────────────────   │
│                                                            │
│  2.  SSRF - API Gateway Y                                 │
│      ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐         │
│      │ REWARD │ │ TIEMPO │ │ PROB   │ │ EV     │         │
│      │ ★★★★☆  │ │ 45 min │ │ Media  │ │ $420   │         │
│      │ $800   │ │        │ │ 65%    │ │        │         │
│      └────────┘ └────────┘ └────────┘ └────────┘         │
│      [ Start Cycle ]  [ Ver detalles ]                   │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

**Métricas mostradas (y solo estas):**
- **Reward**: Bounty máximo del programa
- **Tiempo**: Estimado para validar + reportar
- **Probabilidad**: Score del Opportunity Engine (0-100%)
- **EV (Expected Value)**: Reward × Probabilidad × (1 - Dificultad normalizada)

### 4.5 Knowledge Feed — Un Cerebro, No Un Log

```
┌────────────────────────────────────────────────────────────┐
│  🧠 APRENDIZAJE NUEVO                                 [🧠]  │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  ┌─ NUEVO PATRÓN ──────────────────────────────────────┐  │
│  │ "Los programas SaaS multi-tenant tienen 3.2x más   │  │
│  │  probabilidad de IDOR en endpoints /api/v1/users/  │  │
│  │  /{id}/profile que single-tenant"                   │  │
│  │                                                      │  │
│  │  📊 Confianza: 91%  (47 findings, 14 confirmados)  │  │
│  │  🔵 Aplicado a: Security Cycle → Rastro             │  │
│  │  📅 Descubierto: Hoy 10:23                          │  │
│  │  [ Aplicar a targets actuales ]  [ Ver evidencia ]  │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                            │
│  ┌─ INSIGHT FINANCIERO ────────────────────────────────┐  │
│  │ "HackerOne paga 40% más rápido que Bugcrowd        │  │
│  │  para IDORs críticos (media: 14 vs 23 días)"       │  │
│  │                                                      │  │
│  │  🟡 Aplicado a: Vault → Platform routing            │  │
│  │  📅 Actualizado: Ayer                                │  │
│  │  [ Ajustar routing ]                                 │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

**Regla:** Cada entrada = aprendizaje accionable. No "se escaneó X". Sí "descubrimos patrón Y que cambia cómo hacemos Z".

---

## 5. Interacción

### 5.1 Keyboard First (Shortcuts Principales)

| Shortcut | Acción |
|----------|--------|
| `Ctrl + K` | Command Palette (buscar cualquier cosa: targets, findings, reports, actions) |
| `Ctrl + Space` | Agent Fleet — asignar tarea manual a agente |
| `Ctrl + Shift + O` | Abrir Opportunity Radar |
| `Ctrl + 1` | Mission Control |
| `Ctrl + 2` | Security Cycle (Rastro) |
| `Ctrl + 3` | Forge Cycle |
| `Ctrl + 4` | Pulse Cycle |
| `Ctrl + 5` | Vault (Wealth) |
| `Ctrl + 6` | Atlas (Intelligence) |
| `Ctrl + Shift + H` | Global Health / Status |
| `Esc` | Cerrar modal / Deseleccionar / Volver |
| `Enter` | Ejecutar acción primaria en card enfocada |
| `Tab` / `Shift+Tab` | Navegación focus entre cards accionables |

### 5.2 Command Palette (Navegación Principal)

```
┌────────────────────────────────────────────────────────────┐
│  ⌘K  Buscar cualquier cosa...                              │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  > ACCIONES                                                │
│    ▸ Ejecutar: Validar IDOR Target X          [$800]       │
│    ▸ Ejecutar: Scan recon Target Y                        │
│    ▸ Ejecutar: Generar reporte Finding #234               │
│    ▸ Aprobar: Auto-submission Finding #231               │
│                                                            │
│  🎯 OPORTUNIDADES                                          │
│    ▸ IDOR Programa X          ★★★★★  $800  30m            │
│    ▸ SSRF API Gateway Y       ★★★★☆  $420  45m            │
│    ▸ XSS Dashboard Z          ★★★☆☆  $180  20m            │
│                                                            │
│  🎯 TARGETS                                                │
│    ▸ target-enterprise-x.com    🔵 Activo  12 findings   │
│    ▸ api-gateway-y.io           🟡 En recon  3 findings  │
│                                                            │
│  📄 REPORTES                                               │
│    ▸ Report #234 - IDOR         🟢 Enviado  $1,200       │
│    ▸ Report #231 - SSRF         🟡 Pendiente $800        │
│                                                            │
│  ⚙ AGENTES                                                 │
│    ▸ Research Agent             ● Activo                 │
│    ▸ Execution Agent            ○ Disponible             │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

**Scopes en Command Palette:**
- `>` Acciones ejecutables
- `/` Navegación / páginas
- `@` Agentes / asignar tareas
- `#` Tags / filtros
- `$` Dinero / revenue / payouts

### 5.3 Mouse Friendly
- Todo lo teclado-accessible también es clickable
- Hover states claros en todas las cards accionables
- Drag & drop para reordenar prioridades en Opportunity Radar
- Context menus (right-click) en findings, targets, reports

---

## 6. Desktop: Windows 11 Native (Tauri + Vue 3)

### 6.1 Por qué Tauri

| Criterio | Tauri | Electron |
|----------|-------|----------|
| RAM (idle) | ~40-60 MB | ~120-200 MB |
| Binary size | ~3-8 MB | ~60-100 MB |
| Windows native | ✅ WebView2 (sistema) | ❌ Chromium bundled |
| Startup time | <500ms | 1-3s |
| Rust backend | ✅ Sidecar nativo | ❌ Node.js only |
| System tray / notifications | ✅ Native | ⚠️ Via modules |

### 6.2 Arquitectura OWNEX.exe

```
OWNEX.exe (Tauri App)
├── Frontend (Vue 3 + TypeScript + Tailwind v4)
│   ├── Components (Design System)
│   ├── Pages (Mission Control, Cycles, etc.)
│   ├── Composables (state, agents, opportunities)
│   └── Router (Lazy-loaded cycles)
│
├── Rust Shell (tauri::Builder)
│   ├── Window management (frameless, custom titlebar)
│   ├── System tray + notifications
│   ├── Auto-updater (GitHub releases)
│   ├── Sidecar management (Python backend)
│   ├── Secure storage (OS keychain)
│   └── Native menus / shortcuts
│
├── Python Backend (Sidecar)
│   ├── FastAPI server (localhost:8765)
│   ├── CATEYE cores (security, revenue, learning)
│   ├── SQLite + SQLAlchemy
│   ├── Scheduler + EventBus
│   ├── Ollama client (local LLM)
│   └── FCC Proxy client (remote LLM)
│
├── Local AI (Bundled / Sidecar)
│   └── Ollama + qwen2.5:3b-instruct (3GB)
│
└── Data
    ├── SQLite (config, findings, targets, learning)
    ├── Vector DB (embeddings - opcional, lazy-load)
    └── Cache (recon, program data, prices)
```

### 6.3 Native Windows Features

- **Frameless window** con custom titlebar (drag region, min/max/close native)
- **Mica/Acrylic backdrop** en Windows 11 (`windowEffect: "mica"`)
- **System tray** con status health + quick actions
- **Toast notifications** nativas (Windows 10/11)
- **Jump List** tasks recientes
- **Protocol handler** `ownex://` para deep links
- **Auto-start** opcional (Task Scheduler / Registry)
- **Single instance** enforcement

---

## 7. Android: OWNEX Companion

**No es una copia reducida.** Es un *companion* diseñado para móvil.

### 7.1 Funciones Core

| Feature | Descripción |
|---------|-------------|
| 🔔 **Notificaciones críticas** | Finding validado, payout recibido, aprobación requerida, agente atascado |
| ✅ **Approvals** | One-tap: "Aprobar reporte #234", "Enviar finding", "Rechazar oportunidad" |
| 🔥 **Opportunity Radar** | Top 5 oportunidades del día, swipe para Start Cycle |
| 📊 **Métricas** | Revenue hoy/semana/mes, throughput, agent health |
| 💰 **Wallet / Vault** | Balance total, desglose crypto/fiat, gráfico 30d |
| 🤖 **Agent Status** | Fleet overview, tap para ver detalle / reasignar |
| ⚙️ **Quick Settings** | Pausar ciclo, cambiar modo (auto/manual), silenciar notifs |

### 7.2 UI Móvil - Principios

- **Bottom Navigation** (5 tabs): Mission, Opportunities, Agents, Vault, Settings
- **Pull-to-refresh** en todos los feeds
- **Swipe actions** en listas (aprobar, descartar, ver)
- **Offline-first**: cache último estado, sync en background
- **Biometric auth** para aprobaciones sensibles
- **Widget** opcional: Revenue today + Agent health en home screen

### 7.3 Arquitectura

```
OWNEX Companion (Android)
├── Kotlin + Jetpack Compose (Material 3)
├── Room DB (cache local)
├── WorkManager (background sync)
├── FCM / Push (notificaciones)
├── WebView (Mission Control embed opcional)
└── TLS + mTLS (conexión a desktop backend)
```

### 7.4 Sincronización

- **WebSocket** persistente a `desktop:8765/ws/companion`
- **Event-driven**: solo push cambios, no polling
- **Conflict resolution**: desktop = source of truth
- **Pairing**: QR code en desktop → escanear en app → trust establecida

---

## 8. Nombre Interno del Framework

# **OWNEX OS Design System v1**

### **"Autonomous Work Operating Interface"**

---

## 9. Referencia Rápida: Tokens CSS

```css
:root {
  /* Fondos */
  --bg-deep: #050505;
  --bg-base: #080808;
  --bg-surface: #0F1117;
  --bg-elevated: #14161E;
  
  /* Identidad */
  --ownex-blue: #3B82F6;
  --ownex-white: #F0F0F0;
  --ownex-gold: #F59E0B;
  
  /* Estados (SOLO 3) */
  --status-success: #22C55E;
  --status-error: #EF4444;
  --status-warn: #F59E0B;
  
  /* Texto */
  --text-primary: #F0F0F0;
  --text-secondary: #9CA3AF;
  --text-muted: #6B7280;
  --text-inverse: #050505;
  
  /* Bordes */
  --border-subtle: #1A1A2E;
  --border-active: #3B82F6;
  --border-error: #EF4444;
  
  /* Espaciado */
  --space-1: 0.25rem; --space-2: 0.5rem; --space-3: 0.75rem;
  --space-4: 1rem; --space-5: 1.25rem; --space-6: 1.5rem;
  --space-8: 2rem; --space-10: 2.5rem; --space-12: 3rem;
  
  /* Radio */
  --radius-sm: 0.25rem; --radius-md: 0.5rem;
  --radius-lg: 0.75rem; --radius-xl: 1rem;
  --radius-full: 9999px;
  
  /* Sombras */
  --shadow-1: 0 1px 2px 0 rgb(0 0 0 / 0.3);
  --shadow-2: 0 4px 6px -1px rgb(0 0 0 / 0.4);
  --shadow-3: 0 10px 15px -3px rgb(0 0 0 / 0.5);
  --shadow-glow: 0 0 0 1px var(--ownex-blue), 0 0 20px rgb(59 130 246 / 0.3);
  
  /* Transiciones */
  --transition-fast: 120ms ease-out;
  --transition-base: 200ms ease-out;
  --transition-slow: 300ms ease-out;
}
```

---

## 10. Checklist de Implementación (Por Componente)

| Componente | Tokens | Vue Component | Tests | Storybook | Docs |
|------------|--------|---------------|-------|-----------|------|
| Colors / CSS Variables | ✅ | — | — | — | ✅ |
| Typography | ✅ | — | — | — | ✅ |
| Spacing / Radius / Shadows | ✅ | — | — | — | ✅ |
| Button (Primary/Secondary/Ghost/Danger) | ✅ | `OwnexButton` | ✅ | ✅ | ✅ |
| Card (Elevated/Outlined/Interactive) | ✅ | `OwnexCard` | ✅ | ✅ | ✅ |
| Input / Select / Textarea | ✅ | `OwnexInput` | ✅ | ✅ | ✅ |
| Badge / Pill (Status, Cycle, Priority) | ✅ | `OwnexBadge` | ✅ | ✅ | ✅ |
| Sidebar (Collapsible, Cycle Nav) | ✅ | `AppSidebar` | ✅ | ✅ | ✅ |
| Global Status Bar | ✅ | `GlobalStatusBar` | ✅ | — | ✅ |
| Next Best Action Card | ✅ | `NextBestAction` | ✅ | ✅ | ✅ |
| Work Cycle Card | ✅ | `WorkCycleCard` | ✅ | ✅ | ✅ |
| Agent Fleet Card | ✅ | `AgentFleetCard` | ✅ | ✅ | ✅ |
| Opportunity Card (Radar) | ✅ | `OpportunityCard` | ✅ | ✅ | ✅ |
| Knowledge Feed Card | ✅ | `KnowledgeCard` | ✅ | ✅ | ✅ |
| Command Palette | ✅ | `CommandPalette` | ✅ | — | ✅ |
| Activity Timeline | ✅ | `ActivityTimeline` | ✅ | ✅ | ✅ |
| Modal / Drawer / Toast | ✅ | `OwnexModal` | ✅ | ✅ | ✅ |
| Mobile Bottom Nav | ✅ | `MobileBottomNav` | ✅ | — | ✅ |

---

## 11. Versionado y Evolución

| Versión | Foco | Estado |
|---------|------|--------|
| **v1.0** | Core tokens, Mission Control, Work Cycles, Agent Fleet, Opportunity Radar, Knowledge Feed, Command Palette, Tauri desktop | 🔄 En desarrollo (FASE 1) |
| **v1.1** | Android Companion, Offline sync, Biometric auth | 📝 Planificado (FASE 6) |
| **v1.2** | Advanced theming (user colors), Plugin UI components, Accessibility audit (WCAG AA) | 📝 Futuro |
| **v2.0** | Multi-window, Workspaces, Team collaboration, Enterprise SSO | 📝 Post-revenue |

---

**OWNEX Design System v1** — *Autonomous Work Operating Interface*  
*Clarity over complexity. Action over information. Cycles over pages. Outcomes over activity. Agents over tools. Throughput over metrics.*