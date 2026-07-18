# ORION Desktop Edition — Audit Report (CICLO 1)

> Fecha: Julio 2026
> Modo: Solo lectura. 0 modificaciones.

---

## 1. Arquitectura Actual

```
frontend/          → Vue 3 + TypeScript + Tailwind CSS v4 + Vite
  ├── 65 pages     → Dashboard, MissionControl, KG, Reports, etc.
  ├── 11 components→ ui/, widgets/, layout/, charts/, assistant/, etc.
  ├── shell/       → OrionSidebar.vue, OrionHome.vue
  └── stores/      → Pinia state management

src-tauri/         → Tauri wrapper (Rust)
  ├── main.rs      → Entry point (6 líneas)
  ├── lib.rs       → Builder con 5 plugins (shell, dialog, notification, fs, process)
  ├── tauri.conf.json → v4.3.2, ventana 1400x900, decoraciones nativas
  └── icons/       → PNG/ICO/ICNS (íconos existentes)

core/              → Python: Offensive, Evidence, Execution, Knowledge Graph, etc.
cores/             → Python legacy: auth, license, orchestrator, etc.
api/               → FastAPI routers (60+)
```

## 2. Hallazgos

### 🔴 Discrepancias Críticas

| Hallazgo | Detalle | Impacto |
|----------|---------|---------|
| **Versión inconsistente** | `tauri.conf.json` dice v4.3.2, README dice v4.6.0 | Bajo — cosmético |
| **ARCHITECTURE.md desactualizado** | No menciona `core/` (Offensive Engine, Evidence Graph, Execution Runtime, etc.) | Alto — desorienta a nuevos agentes |
| **Tauri mínimo** | Sin titlebar custom, sin menú, sin tray icon, sin atajos globales | Medio — experiencia desktop pobre |

### 🟡 Oportunidades de Mejora

| Área | Hallazgo |
|------|----------|
| **Sidebar** | Lucide icons, colapso funcional, pero sensación de admin template genérico |
| **65 páginas** | Muchas páginas individuales — oportunidad de consolidar |
| **Widgets** | Sistema de 10 widgets existe, pero layout es web, no desktop |
| **Fonts** | Tailwind + system fonts. Orbitron/Press Start 2P instalados pero no en sidebar |
| **Logo** | `Activity` icon de Lucide como placeholder. Sin logo real |
| **Tauri window** | `decorations: true` (titlebar nativo de OS). Sin personalización |
| **PyInstaller** | Desktop build alternativo existe en `desktop/` |

### 🟢 Fortalezas

- Backend robusto, 1400+ tests, Ruff clean
- Frontend completo: 65 páginas funcionales, widgets, tema oscuro
- Knowledge Graph, Mission Control, Revenue Dashboard existen y funcionan
- Sistema de asistentes (7 personajes) con pixel art
- Setup Wizard, Health Center, Notifications
- Tailwind CSS v4 con temas retro/retrowave ya implementados

## 3. Framework Desktop — Evaluación

| Criterio | Tauri (actual) | Electrón | Neutralino |
|----------|----------------|----------|------------|
| RAM idle | ~80-120MB | ~200-400MB | ~40-60MB |
| Bundle size | ~5-8MB | ~150MB | ~3-5MB |
| Rust backend | ✅ Nativo | ❌ Node | ❌ |
| Python integration | ❌ Manual | ❌ Manual | ❌ |
| DX | ✅ Buena | ✅ Madura | ⚠️ Limitada |
| Windows installer | ✅ MSI/NSIS | ✅ Squirrel/NSIS | ✅ |
| Auto-update | ⚠️ Manual | ✅ electron-builder | ⚠️ |

**Conclusión**: Tauri es adecuado. RAM idle estimado <120MB. Startup <2s. **No migrar.** Solo mejorar la experiencia desktop existente.

## 4. Riesgos del Rediseño

| Riesgo | Severidad | Mitigación |
|--------|-----------|------------|
| Romper 65 páginas | Alta | No tocar lógica de páginas, solo layout/shell |
| Desactualizar docs | Media | Actualizar ARCHITECTURE.md primero |
| Degradar performance | Media | Animar con CSS, no JS; lazy load widgets |
| Perder compatibilidad web | Media | Mantener Vue 3; mejoras solo en shell Tauri |

## 5. Plan de Ejecución Recomendado

### CICLO 2 — Brand System (estima: 2-3h)
1. Logo SVG premium (orbital/core/cyber)
2. Favicon + iconos Windows/Android
3. Paleta de colores definitiva (negro/violeta/dorado)
4. Tipografía: Orbitron headers + Inter body + JetBrains Mono code
5. Splash screen + loading screen

### CICLO 3 — Desktop Experience (estima: 3-4h)
1. Custom titlebar sin decoraciones nativas (Tauri `decorations: false`)
2. Sidebar premium con glassmorphism + iconos nuevos
3. Dock de apps horizontal
4. Keyboard shortcuts globales
5. Tray icon + notificaciones nativas

### CICLO 4 — Módulos Visuales (estima: 5-8h)
1. **Mission Control** — KPIs grandes, timeline, next action, health score
2. **Knowledge Graph** — Inspiración Neo4j/Maltego
3. **Revenue Terminal** — Bloomberg terminal simplificado
4. **Reports Queue** — Estilo Jira profesional
5. **Assistant Hub** — Pixel art HD + burbujas contextuales
6. **Android mockups** — Coherentes con desktop

### CICLO 5 — Documentación (estima: 2-3h)
1. README — Hero, screenshots nuevas, desktop focus
2. ARCHITECTURE.md — Actualizar con `core/`, Tauri, multi-surface
3. Screenshots nuevas del rediseño

### CICLO 6 — Backend Audit (estima: 2h)
1. TODO/FIXME/HACK review
2. Servicios sin uso
3. Endpoints obsoletos
4. Tests faltantes

## 6. Versiones

| Archivo | Versión actual | Versión objetivo |
|---------|---------------|-----------------|
| README.md | v4.6.0 | v4.7.0 |
| tauri.conf.json | v4.3.2 | v4.7.0 |
| `.ai/CURRENT_STATE.md` | v4.5.0 | v4.7.0 |

---

**Fin del CICLO 1. 0 archivos modificados. Solo lectura.**

Próximo paso: aprobar CICLO 2 (Brand System) o ajustar el plan.
