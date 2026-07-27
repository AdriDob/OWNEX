# OWNEX Design System v1.0
## Autonomous Work Operating Interface — "Dark Command Center, not Cyberpunk Hacker"

---

## 🎯 Filosofía Principal

> **"Tengo un sistema operativo personal que trabaja conmigo."**
>
> NO: *"Estoy hackeando una nave espacial de 1998."*

OWNEX NO es un dashboard SaaS genérico con 47 tarjetas y gráficos inútiles. Es un **Workspace OS** — una mezcla de:

| Inspiración | Qué aporta |
|-------------|------------|
| **Discord** | Navegación persistente, comunidades/canales, presencia de agentes |
| **Windows 11 Fluent** | Integración nativa, claridad, profundidad, materiales (mica/acrylic) |
| **Linear** | Productividad extrema, estados, ciclos, shortcuts |
| **Raycast** | Acciones rápidas y comando central (⌘K) |
| **Notion** | Conocimiento estructurado |
| **Bloomberg Terminal (limpio)** | Inteligencia operativa |
| **Mission Control (Apple)** | Visión global |

**Identidad propia:** *Autonomous Work Operating Interface*

---

## 1. Sistema Visual

### 1.1 Paleta Base (Casi Negro)

```css
/* Fondos progresivos */
--ownex-bg-deep:      #050505;  /* Fondo principal */
--ownex-bg-base:      #080808;  /* Paneles elevados */
--ownex-bg-surface:   #0F1117;  /* Tarjetas, modales */
--ownex-bg-glass:     rgba(15, 17, 23, 0.7);
--ownex-bg-glass-border: rgba(59, 130, 246, 0.12);
```

### 1.2 Colores de Identidad

```css
/* ── Primarios ───────────────────────────────────────── */
--ownex-blue:        #3B82F6;  /* Acciones, selección, inteligencia, navegación */
--ownex-white:       #FFFFFF;  /* Información importante, títulos, resultados */
--ownex-gold:        #F59E0B;  /* Dinero, recompensas, logros, oportunidades premium */

/* ── Estados (SOLO estos 3) ──────────────────────────── */
--ownex-green:       #10B981;  /* ✅ Activo / Éxito */
--ownex-red:         #EF4444;  /* ❌ Error / Riesgo */
--ownex-yellow:      #FBBF24;  /* ⚠️ Atención / Advertencia */

/* ── Texto ────────────────────────────────────────────── */
--ownex-text-primary:   #FFFFFF;
--ownex-text-secondary: #94A3B8;  /* slate-400 */
--ownex-text-muted:     #64748B;  /* slate-500 */
--ownex-text-disabled:  #475569;  /* slate-600 */
```

### 1.3 Tipografía

```css
/* Display — Solo para headlines hero, KPIs grandes */
--font-display: 'Space Grotesk', 'Orbitron', system-ui, sans-serif;

/* Body — Todo el resto */
--font-body: 'Inter', 'DM Sans', system-ui, sans-serif;

/* Mono — Código, terminales, hashes, montos, IPs */
--font-mono: 'JetBrains Mono', 'Fira Code', monospace;
```

### 1.4 Espaciado (Sistema 4px)

```css
--space-1:  4px;
--space-2:  8px;
--space-3:  12px;
--space-4:  16px;
--space-5:  24px;
--space-6:  32px;
--space-8:  48px;
--space-10: 64px;
```

### 1.5 Bordes y Materiales (Fluent-inspired)

```css
/* Glass / Acrylic */
--glass-bg:       rgba(15, 17, 23, 0.7);
--glass-border:   1px solid rgba(59, 130, 246, 0.12);
--glass-blur:     backdrop-filter: blur(20px) saturate(180%);

/* Mica (para paneles laterales) */
--mica-bg:        rgba(8, 8, 8, 0.9);
--mica-border:    1px solid rgba(59, 130, 246, 0.08);

/* Elevation shadows */
--shadow-sm:  0 1px 3px rgba(0,0,0,0.4);
--shadow-md:  0 4px 12px rgba(0,0,0,0.5);
--shadow-lg:  0 8px 32px rgba(0,0,0,0.6);
--shadow-glow: 0 0 24px rgba(59, 130, 246, 0.15);
```

### 1.6 Radio y Transiciones

```css
--radius-sm:  6px;
--radius-md:  10px;
--radius-lg:  16px;
--radius-xl:  24px;
--radius-full: 9999px;

--transition-fast:  120ms ease-out;
--transition-base:  200ms ease-out;
--transition-slow:  350ms ease-out;
```

---

## 2. Layout Principal — Workspace OS

```
┌─────────────────────────────────────────────────────────────────┐
│ GLOBAL STATUS BAR (siempre visible, 40px)                       │
│ Health │ Throughput │ Revenue │ Agent Fleet │ 🔔 │ ⌘K │ 👤     │
├──────────────┬──────────────────────────────────────────────────┤
│              │                                                  │
│   SIDEBAR    │         MAIN WORKSPACE (flex-1)                  │
│   (280px)    │                                                  │
│              │  ┌──────────────────────────────────────────┐   │
│  ┌────────┐  │  │ TABS:  [Ciclo Actual] [Oportunidades]    │   │
│  │ LOGO   │  │  │ [Agentes] [Conocimiento] [Capital]       │   │
│  ├────────┤  │  ├──────────────────────────────────────────┤   │
│  │ Mission│  │  │ CONTENIDO DINÁMICO POR TAB               │   │
│  │Security│  │  │                                          │   │
│  │ Forge  │  │  │  Next Best Action  │  Work Cycles Grid   │   │
│  │ Pulse  │  │  │  ┌──────────────┐  │  ┌────┐ ┌────┐     │   │
│  │ Vault  │  │  │  │ ⚡ Próxima    │  │  │ 🔵 │ │ 🟣 │     │   │
│  │ Atlas  │  │  │  │    acción    │  │  │Sec │ │For │     │   │
│  ├────────┤  │  │  └──────────────┘  │  └────┘ └────┘     │   │
│  │Agentes │  │  │                                          │   │
│  │Salud   │  │  │  Opportunity Radar  │  Knowledge Feed    │   │
│  │Config  │  │  │  ┌──────────────┐  │  ┌──────────────┐  │   │
│  └────────┘  │  │  │ 🔥 IDOR Prog X│  │  │ 🧠 Aprendizaje│  │   │
│              │  │  │  $800  30m    │  │  │   nuevo      │  │   │
│  [Collapse]  │  │  │  [Start Cycle] │  │  └──────────────┘  │   │
└──────────────┘  │  └──────────────────┘  └──────────────────┘  │
                  │                                                  │
                  └──────────────────────────────────────────────────┘
```

### 2.1 Global Status Bar (40px, fixed top)

| Elemento | Comportamiento |
|----------|----------------|
| **Health** | 🟢🟡🔴 — Click → System Health Modal |
| **Throughput** | `12/h` — Click → Throughput Detail |
| **Revenue** | `$2.4k/mes` — Click → Vault Tab |
| **Agent Fleet** | `5/6 🟢` — Hover → tooltip con estados |
| **Notificaciones** | Badge count — Click → Notification Center |
| **⌘K Command Palette** | Global search + actions |
| **Avatar** | Perfil, settings, switch workspace |

### 2.2 Sidebar (280px, colapsible a 64px)

**Secciones (orden fijo):**

1. **Brand** — Logo + "OWNEX" (colapsado: solo logo)
2. **Mission Control** — Landing principal
3. **Security** — Bug bounty, targets, hallazgos
4. **Forge** — Dev bounty, código, PRs
5. **Pulse** — IA, modelos, entrenamiento
6. **Vault** — Capital, payouts, wallet
7. **Atlas** — Inteligencia, patrones, conocimiento
8. **Divider**
9. **Agent Fleet** — Estado de cada agente
10. **System Health** — Mini dashboard
11. **Settings** — Configuración

**Estados:**
- **Expanded** (280px): Icon + Label + Badge
- **Collapsed** (64px): Solo icon + tooltip on hover
- **Mobile**: Drawer from left

---

## 3. Componentes Fundamentales

### 3.1 Mission Control (Pantalla Principal)

**Pregunta central:** *"¿Qué debería hacer ahora?"* — No *"Aquí tienes 20 gráficos."*

#### A) Next Best Action Card (Hero)

```tsx
<NextBestAction>
  <ActionIcon type="validation" />
  <Content>
    <Title>Validar IDOR encontrado en Target X</Title>
    <Meta>
      <Reward>Valor estimado: $800</Reward>
      <Confidence>Confianza: 87%</Confidence>
      <Time>Tiempo: 25 min</Time>
    </Meta>
  </Content>
  <CTA variant="primary">Ejecutar Ciclo</CTA>
  <CTA variant="ghost">Ver Detalles</CTA>
</NextBestAction>
```

**Estados:**
- **Primary**: Acción recomendada por IA
- **Secondary**: Alternativa manual
- **Empty**: "Sistema nominal. No hay acciones urgentes."

---

#### B) Work Cycles Grid

Cada ciclo = una "app" dentro de OWNEX.

```tsx
<WorkCycleCard
  id="security"
  icon={Shield}
  color="blue"
  name="Security"
  subtitle="Rastro Bug Bounty"
  status="active"
  throughput={87}    // %
  revenue={2400}     // USD/mes
  automation={73}    // %
  tasks={[
    { label: "Recon Passivo", done: true },
    { label: "Fuzzing Activo", done: true },
    { label: "Validación IDOR", done: false },
    { label: "Reporte HackerOne", done: false }
  ]}
/>
```

**Estados de ciclo:** `active` 🟢 | `available` ⚪ | `blocked` 🔴 | `completed` ✅

---

#### C) Agent Fleet

**Los modelos desaparecen.** El usuario NO ve: ❌ Qwen, ❌ Claude, ❌ DeepSeek.

Ve:
```
🤖 Research Agent     ● Activo      → "Escaneando 47 endpoints"
⚙️  Execution Agent   ○ Disponible  → "Listo para validar"
🧠 Memory Agent       🔄 Aprendiendo → "Consolidando patrones IDOR"
🔎 Security Agent     ● Escaneando  → "Fuzzing target X (12/200)"
```

**Propiedades:**
- `name`, `role`, `status` (active/idle/learning/error)
- `currentTask` — descripción humana
- `progress` — opcional (0-100)
- `model` — **oculto** (solo en debug mode)

---

#### D) Opportunity Radar (Ranking Inteligente)

NO lista de links. **Ranking con contexto.**

```tsx
<OpportunityCard
  rank={1}
  title="IDOR en API REST /users/{id}"
  program="Acme Corp (HackerOne)"
  severity="high"
  reward="$800"
  timeEstimate="30 min"
  confidence={87}
  tags={["IDOR", "API", "Multi-tenant"]}
  evidence={3}
  poc="ready"
  action="Iniciar Ciclo de Validación"
/>
```

**Métricas visibles:**
- ⭐ Reward tier (★★★★★)
- ⏱ Tiempo estimado
- 🎯 Probabilidad (Alta/Media/Baja)
- 📎 Evidencias adjuntas
- 💣 PoC status

---

#### E) Knowledge Feed (Cerebro, no Log)

```tsx
<KnowledgeItem
  type="pattern"
  title="Los SaaS multi-tenant tienen mayor probabilidad de IDOR"
  appliedTo="Security Cycle"
  confidence={0.91}
  source="Auto-extracted from 12 findings"
  timestamp="Hace 2h"
  actionable={true}
  action="Aplicar a 3 targets en cola"
/>
```

**Tipos:**
- `pattern` 🔵 — Patrón detectado
- `technique` 🟣 — Nueva técnica aprendida
- `correction` 🟡 — Falso positivo corregido
- `milestone` 🟢 — Logro (ej. "Primer $1k mes")
- `alert` 🔴 — Requiere atención

---

### 3.2 Componentes UI Base

#### Button Variants

```css
/* Primary — Acción principal (Blue) */
.btn-primary {
  background: var(--ownex-blue);
  color: white;
  &:hover { background: #2563EB; box-shadow: var(--shadow-glow); }
}

/* Secondary — Acción secundaria (Glass) */
.btn-secondary {
  background: var(--glass-bg);
  border: var(--glass-border);
  color: var(--ownex-white);
  &:hover { background: var(--ownex-bg-surface); }
}

/* Ghost — Acción terciaria (Solo texto) */
.btn-ghost {
  background: transparent;
  color: var(--ownex-text-secondary);
  &:hover { color: var(--ownex-white); background: var(--ownex-bg-surface); }
}

/* Danger — Destructivo (Red) */
.btn-danger {
  background: var(--ownex-red);
  color: white;
}

/* Gold — Oportunidad premium (Gold) */
.btn-gold {
  background: linear-gradient(135deg, var(--ownex-gold), #D97706);
  color: #050505;
}
```

#### Card Base (Glass)

```css
.card {
  background: var(--glass-bg);
  border: var(--glass-border);
  border-radius: var(--radius-lg);
  backdrop-filter: var(--glass-blur);
  transition: all var(--transition-base);
}
.card:hover {
  border-color: rgba(59, 130, 246, 0.25);
  box-shadow: var(--shadow-lg), var(--shadow-glow);
}
.card-elevated {
  background: var(--ownex-bg-surface);
  box-shadow: var(--shadow-md);
}
```

#### Input / Search

```css
.input {
  background: var(--ownex-bg-base);
  border: 1px solid rgba(148, 163, 184, 0.15);
  border-radius: var(--radius-md);
  color: var(--ownex-white);
  padding: 10px 14px;
  font-family: var(--font-body);
  transition: all var(--transition-fast);
}
.input:focus {
  outline: none;
  border-color: var(--ownex-blue);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15);
}
.input::placeholder { color: var(--ownex-text-muted); }
```

#### Badge / Status Pill

```css
.badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: var(--radius-full);
  font-size: 11px;
  font-weight: 600;
  font-family: var(--font-mono);
}
.badge-green { background: rgba(16, 185, 129, 0.15); color: var(--ownex-green); }
.badge-yellow { background: rgba(251, 191, 36, 0.15); color: var(--ownex-yellow); }
.badge-red { background: rgba(239, 68, 68, 0.15); color: var(--ownex-red); }
.badge-blue { background: rgba(59, 130, 246, 0.15); color: var(--ownex-blue); }
.badge-gold { background: rgba(245, 158, 11, 0.15); color: var(--ownex-gold); }
```

#### KPI Display

```css
.kpi {
  font-family: var(--font-display);
  font-weight: 700;
  letter-spacing: -0.02em;
}
.kpi-xl { font-size: 48px; line-height: 1.1; }
.kpi-lg { font-size: 32px; line-height: 1.2; }
.kpi-md { font-size: 24px; line-height: 1.3; }
.kpi-sm { font-size: 18px; line-height: 1.4; }
.kpi-label {
  font-family: var(--font-body);
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--ownex-text-muted);
  font-weight: 500;
}
```

---

## 4. Interacción — Keyboard First, Mouse Friendly

### 4.1 Atajos Globales (⌘K / Ctrl+K = Command Palette)

| Shortcut | Acción |
|----------|--------|
| `⌘K` / `Ctrl+K` | Command Palette (buscar todo, ejecutar acciones) |
| `⌘Space` | Ejecutar agente / Quick Action |
| `⌘Shift+O` | Abrir Opportunity Radar |
| `⌘Shift+C` | Abrir Work Cycles |
| `⌘Shift+A` | Agent Fleet |
| `⌘Shift+K` | Knowledge Feed |
| `⌘Shift+V` | Vault / Capital |
| `⌘/` | Ayuda / Shortcuts |
| `⌘,` | Settings |
| `Tab` / `Shift+Tab` | Navegación por tabs y paneles |
| `Escape` | Cerrar modal, dismiss toast, salir comando |

### 4.2 Command Palette (⌘K) — Centro Nervioso

```
┌─────────────────────────────────────────────────────────────┐
│ ⌘K  Buscar objetivos, acciones, conocimiento, agentes...    │
├─────────────────────────────────────────────────────────────┤
│ 🎯 Acciones Sugeridas                                       │
│   ▸ Iniciar ciclo de validación IDOR (Target X)   ⌘Enter   │
│   ▸ Ejecutar recon pasivo en Target Y              ⌘Enter   │
│   ▸ Generar reporte para HackerOne                 ⌘Enter   │
│                                                             │
│ 🔍 Objetivos                                               │
│   ▸ Target X (acme.com)          Security  ▸ 12 endpoints │
│   ▸ Target Y (beta.corp.io)      Forge     ▸ 3 PRs open   │
│                                                             │
│ 🤖 Agentes                                                 │
│   ▸ Research Agent — Activo                              │
│   ▸ Execution Agent — Disponible                         │
│                                                             │
│ 📚 Conocimiento                                            │
│   ▸ Patrón: IDOR multi-tenant (confianza 91%)            │
│                                                             │
│ ⚡ Comandos Rápidos                                         │
│   ▸ Reiniciar sistema                                    │
│   ▸ Ver health check completo                            │
│   ▸ Exportar datos                                       │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. Desktop App — Tauri + Vue 3

### 5.1 Stack Técnico

| Capa | Tecnología |
|------|------------|
| **Shell** | Tauri v2 (Rust) |
| **UI** | Vue 3 + TypeScript + Tailwind CSS v4 |
| **Backend** | Python (FastAPI) embebido via sidecar |
| **DB** | SQLite (dev) / PostgreSQL (prod) |
| **Local LLM** | Ollama (sidecar o system) |
| **Agents** | Procesos Python/Node comunicados via stdio/Unix socket |

### 5.2 Arquitectura Tauri

```
OWNEX.app / OWNEX.exe
├── Frontend (Vue 3 + Vite)
│   ├── src/
│   │   ├── components/     # UI Components
│   │   ├── pages/          # MissionControl, Security, Forge, etc.
│   │   ├── stores/         # Pinia stores
│   │   ├── services/       # API, Tauri IPC, WebSocket
│   │   ├── composables/    # useAgents, useCycles, etc.
│   │   └── styles/         # OWNEX Design Tokens (CSS vars)
│   └── dist/               # Built assets
├── src-tauri/
│   ├── src/
│   │   ├── main.rs         # Entry point
│   │   ├── python_sidecar.rs  # Gestión proceso Python
│   │   ├── ollama_manager.rs  # Health check, auto-start Ollama
│   │   ├── ipc/            # Commands & Events
│   │   ├── system_tray.rs  # System tray integration
│   │   ├── window_state.rs # Persist position/size
│   │   └── updater.rs      # Auto-updater (GitHub Releases)
│   ├── Cargo.toml
│   └── tauri.conf.json
├── python/
│   ├── main.py             # FastAPI app
│   ├── agents/             # Agent implementations
│   ├── cores/              # Business logic
│   └── requirements.txt
└── resources/
    ├── icon.icns / icon.ico
    └── splash.png
```

### 5.3 Tauri Config Clave

```json
{
  "identifier": "com.ownex.app",
  "productName": "OWNEX",
  "version": "4.7.0",
  "build": {
    "frontendDist": "../dist",
    "devUrl": "http://localhost:5173",
    "beforeDevCommand": "npm run dev",
    "beforeBuildCommand": "npm run build"
  },
  "app": {
    "windows": [
      {
        "title": "OWNEX — Autonomous Work OS",
        "width": 1440,
        "height": 900,
        "minWidth": 1024,
        "minHeight": 720,
        "decorations": false,
        "transparent": true,
        "titleBarStyle": "overlay",
        "hiddenTitle": true
      }
    ],
    "security": {
      "csp": "default-src 'self' data: blob:; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self' http://localhost:* ws://localhost:*"
    }
  },
  "bundle": {
    "active": true,
    "targets": "all",
    "icon": ["resources/icon.png", "resources/icon.icns", "resources/icon.ico"],
    "windows": {
      "webviewInstallMode": "embedBootstrapper",
      "allowDowngrades": false
    },
    "macOS": {
      "minimumSystemVersion": "13.0",
      "exceptionDomain": "localhost"
    }
  },
  "plugins": {
    "shell": { "open": true },
    "dialog": { "open": true, "save": true },
    "fs": { "scope": ["$APPDATA/ownex/*", "$HOME/.ownex/*"] },
    "updater": { "active": true, "endpoints": ["https://releases.ownex.dev"] },
    "notification": { "active": true },
    "globalShortcut": { "active": true }
  }
}
```

### 5.4 Python Sidecar (FastAPI)

```rust
// src-tauri/src/python_sidecar.rs
use tauri::Manager;
use std::process::{Command, Stdio};

pub fn spawn_python_sidecar(app: &tauri::AppHandle) -> Result<(), Box<dyn std::error::Error>> {
    let python_path = if cfg!(target_os = "windows") {
        app.path().resolve("python/python.exe", tauri::path::BaseDirectory::Resource)?
    } else {
        app.path().resolve("python/bin/python", tauri::path::BaseDirectory::Resource)?
    };
    
    let script_path = app.path().resolve("python/main.py", tauri::path::BaseDirectory::Resource)?;
    
    let mut child = Command::new(python_path)
        .arg(script_path)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()?;
    
    // Health check loop
    std::thread::spawn(move || {
        loop {
            std::thread::sleep(std::time::Duration::from_secs(5));
            if !is_healthy("http://localhost:8000/health") {
                restart_python_sidecar(app);
            }
        }
    });
    
    Ok(())
}
```

---

## 6. Android — OWNEX Companion

**NO es una copia reducida.** Es un **compañero táctil** para decisiones rápidas.

### 6.1 Funciones Core

| Feature | Descripción |
|---------|-------------|
| **Notificaciones Críticas** | Alertas de hallazgos, aprobaciones, errores |
| **Aprobaciones One-Tap** | "Iniciar ciclo", "Enviar reporte", "Aceptar riesgo" |
| **Opportunity Radar Mobile** | Top 5 oportunidades con swipe actions |
| **Agent Fleet Status** | Vista compacta: 🟢🟡🔴 + tarea actual |
| **Vault / Wallet** | Balance, payouts pendientes, historial |
| **System Health** | 🟢🟡🔴 + métricas clave |
| **COPILOT Resumen** | Decisiones importantes, resumen diario |

### 6.2 Stack Android

- **Kotlin + Compose Multiplatform** (compartir lógica con desktop)
- **Material 3 Expressive** (adaptado a OWNEX tokens)
- **Firebase Cloud Messaging** para push
- **Biometric Auth** (huella/face) para aprobaciones
- **Wear OS Module** para smartwatch

### 6.3 Wear OS — OWNEX Watch Companion

**Extensión del sistema, NO standalone.**

```
┌─────────────────────┐
│ 🟢 ORION ONLINE     │
│ 3 ciclos activos    │
│ 2 aprobaciones 🔔   │
├─────────────────────┤
│ ⚡ Próxima acción   │
│ Validar IDOR Target X│
│ $800 · 87% · 25m    │
│ [Aprobar] [Luego]   │
├─────────────────────┤
│ 🤖 Agentes: 5/6 🟢  │
│ 💰 $2.4k este mes   │
└─────────────────────┘
```

**Interacciones:**
- Tap → Aprobar/Rechazar
- Swipe up → Detalle
- Swipe down → Dismiss
- Long press → Abrir en móvil

---

## 7. Principios de Diseño (6 Pillars)

| # | Principio | Aplicación |
|---|-----------|------------|
| 1 | **Clarity over Complexity** | Un concepto = un nombre. Nada de "User/Client/Customer". |
| 2 | **Action over Information** | Cada pantalla responde: *"¿Qué hago ahora?"* |
| 3 | **Cycles over Pages** | Work Cycles = apps. No navegación por menús. |
| 4 | **Outcomes over Activity** | Métricas de resultado (revenue, findings) > vanidad (clicks, vistas). |
| 5 | **Agents over Tools** | IA invisible. Usuario ve capacidades, no modelos. |
| 6 | **Throughput over Metrics** | Flujo continuo > snapshots estáticos. |

---

## 8. Naming Convention (Single Source of Truth)

| Concepto | Nombre Canónico | NO usar |
|----------|-----------------|---------|
| Usuario operador | **Operador** | User, Admin, Client |
| Ciclo de trabajo | **Work Cycle / Ciclo** | Project, Task, Job |
| Agente IA | **Agent / Agente** | Bot, Worker, Model |
| Hallazgo validado | **Finding / Hallazgo** | Vuln, Bug, Issue |
| Oportunidad | **Opportunity / Oportunidad** | Lead, Target, Prospect |
| Recompensa | **Reward / Recompensa** | Payout, Bounty, Payment |
| Conocimiento | **Knowledge / Conocimiento** | Learning, Insight, Pattern |
| Capital | **Vault / Capital** | Wallet, Portfolio, Funds |
| Inteligencia | **Atlas / Inteligencia** | Analytics, Intel, Reports |

---

## 9. Implementación — Checklist

### 9.1 Design Tokens (CSS Variables)

- [ ] Crear `src/styles/ownex-tokens.css` con todas las variables
- [ ] Importar en `style.css` antes de Tailwind
- [ ] Configurar Tailwind v4 para usar variables CSS nativas

### 9.2 Component Library

- [ ] `OwnexButton` (variants: primary, secondary, ghost, danger, gold)
- [ ] `OwnexCard` (base, elevated, glass, interactive)
- [ ] `OwnexInput` / `OwnexSearch` (con ⌘K shortcut)
- [ ] `OwnexBadge` (status, reward-tier, confidence)
- [ ] `OwnexKPI` (xl, lg, md, sm + label)
- [ ] `OwnexAvatar` (agent, operator, program)
- [ ] `OwnexTooltip` / `OwnexPopover`
- [ ] `OwnexModal` / `OwnexDrawer` (mobile sidebar)
- [ ] `OwnexToast` / `OwnexNotification`
- [ ] `OwnexTable` / `OwnexDataGrid` (virtualized)
- [ ] `OwnexTabs` (work cycle tabs)
- [ ] `OwnexCommandPalette` (⌘K)

### 9.3 Layout Components

- [ ] `GlobalStatusBar` (fixed top)
- [ ] `Sidebar` (collapsible, mobile drawer)
- [ ] `WorkCycleGrid` (responsive grid)
- [ ] `NextBestAction` (hero card)
- [ ] `AgentFleet` (compact list)
- [ ] `OpportunityRadar` (ranked list + detail)
- [ ] `KnowledgeFeed` (infinite scroll)
- [ ] `VaultSummary` (revenue, pending, history)

### 9.4 Pages / Work Cycles

- [ ] `MissionControl` (landing)
- [ ] `SecurityCycle` (bug bounty)
- [ ] `ForgeCycle` (dev bounty)
- [ ] `PulseCycle` (AI/ML)
- [ ] `VaultCycle` (capital)
- [ ] `AtlasCycle` (intelligence)

### 9.5 Tauri Integration

- [ ] Python sidecar manager
- [ ] Ollama health + auto-start
- [ ] System tray + notifications
- [ ] Window state persistence
- [ ] Auto-updater (GitHub Releases)
- [ ] Global shortcuts (⌘K, ⌘Space)
- [ ] Biometric auth (mobile/desktop)

### 9.6 Android / Wear OS

- [ ] Compose Multiplatform setup
- [ ] Shared ViewModels (Kotlin)
- [ ] Push notifications (FCM)
- [ ] Biometric approval flow
- [ ] Wear OS companion app
- [ ] Offline-first sync

---

## 10. Recursos y Referencias

### 10.1 Assets de Marca

```
/brand/ownex/
├── logo-mark.svg           # Solo isotipo (para favicon, watch)
├── logo-horizontal.svg     # Logotipo completo
├── logo-mono-white.svg     # Versión monocromo blanca
├── logo-mono-dark.svg      # Versión monocroma oscura
├── app-icon-1024.png       # Source para generar todos los tamaños
├── splash-screen.png       # 2732x2732 (iOS) / 3200x1920 (Android)
└── og-image.png            # 1200x630 para social
```

### 10.2 Fuentes (Descargar y self-host)

```bash
# Space Grotesk (Display)
wget https://github.com/googlefonts/space-grotesk/releases/download/v1.001/space-grotesk-v1.001.zip

# Inter (Body)  
wget https://github.com/rsms/inter/releases/download/v4.0/Inter-4.0.zip

# JetBrains Mono (Mono)
wget https://github.com/JetBrains/JetBrainsMono/releases/download/v2.304/JetBrainsMono-2.304.zip
```

### 10.3 Iconos

- **Lucide** (base) — `lucide-vue-next`
- **Custom OWNEX icons** — SVG en `/brand/ownex/icons/`

---

## 11. Versionado del Design System

| Versión | Fecha | Cambios |
|---------|-------|---------|
| **1.0.0** | 2025-07-26 | Definición inicial completa |
| 1.1.0 | — | Component library v1 |
| 1.2.0 | — | Tauri integration |
| 2.0.0 | — | Android Companion v1 |

---

> **OWNEX Design System v1.0** — *Autonomous Work Operating Interface*
>
> "No construimos dashboards. Construimos sistemas operativos para trabajo autónomo."
>
> — OWNEX Team