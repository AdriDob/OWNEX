# PLAN — ORION Vue Frontend

## Filosofía (vigente desde 2026-06-30)

ORION NO es un SaaS comercial.
ORION es un SaaS PRIVADO.

Cada componente debe responder: **¿Esto ayuda a ganar más dinero?**

El frontend es un **Centro de Inteligencia Económica**. El usuario abre ORION y en <20s debe entender:
- Cuánto dinero tiene
- Cuánto dinero puede cobrar
- Dónde está el mejor dinero
- Qué debe hacer ahora
- Cuánto tiempo debe invertir

## Estado Actual (v1.2.0)

### ✅ Completado
- [x] Análisis completo del backend FastAPI (52 routers, ~100 endpoints)
- [x] Análisis del frontend React actual (41 páginas, Zustand, React Query)
- [x] Creación de proyecto Vue 3 + Vite + TypeScript
- [x] ShadCN Vue + Tailwind CSS v4 + Lucide Icons
- [x] Proxy Vite → FastAPI
- [x] Tipos TypeScript alineados con API real
- [x] Layout con Sidebar (6 nav items)
- [x] Sidebar colapsable
- [x] Router con lazy loading (6 rutas)
- [x] Componentes ShadCN base
- [x] KPIGrid
- [x] OpportunityTable (sortable, paginada)
- [x] CopilotPanel (chat contextual, Ctrl+B)
- [x] Command Palette (Ctrl+K)
- [x] Dark mode + glassmorphism
- [x] TypeScript compila limpio

### 🚀 API Client
- [x] Auth token interceptor
- [x] Auto-login
- [x] Manejo de errores
- [x] Loading state tracker
- [x] Evento `auth:unauthorized`
- [x] Funciones tipadas

### 🔌 Páginas conectadas a API real
| Página | Endpoint | Estado |
|--------|----------|--------|
| MissionControl | `GET /api/orion/context` | ✅ |
| OpportunityRadar | `GET /api/targets` | ✅ |
| HotPaths | `GET /api/attack/decision` | ✅ |
| Findings | `GET /api/pipeline` + `GET /api/findings` | ✅ |
| ReportCenter | `GET /api/reports` | ✅ |
| CopilotPanel | `POST /api/assistant/orion-chat` | ✅ |

### 📅 Próximos módulos (ordenados por impacto económico)

#### Módulo 1 — Caza Autónoma
- [ ] Botón "Start Autonomous Hunt" en Mission Control
- [ ] Sidebar con estado Running/Paused
- [ ] API de start/stop
- [ ] Notificaciones de hallazgos relevantes

#### Módulo 2 — Generación Inteligente de Reportes
- [ ] Botón "Generar Borrador" por finding
- [ ] Drawer con preview Markdown + PDF
- [ ] IA local para PoC, severity, steps to reproduce, fix
- [ ] Export individual y bulk

#### Módulo 3 — Command Palette Mejorada (Ctrl+K)
- [ ] Acciones rápidas: New Hunt, Export Findings, Start Autonomous, Generate Report
- [ ] Búsqueda inteligente de targets
- [ ] Atajos de navegación mejorados

#### Módulo 4 — Cartera / Centro Económico (Wallets evolucionado)
- [ ] Resumen general: total histórico, pendiente, en revisión, aprobado, rechazado
- [ ] Promedios mensual/anual, mayor recompensa, mayor programa
- [ ] Tiempos promedio hasta cobrar y de triage
- [ ] Pipeline económico (Findings → Validados → Reportes → Triage → Pagados)
- [ ] Ingresos esperados (conservador/esperado/optimista)
- [ ] ROI del tiempo (USD/hora, USD/día, USD/programa, USD/vulnerabilidad)
- [ ] Money Radar con ORION SCORE
- [ ] ROI por programa y por vulnerabilidad
- [ ] Historial inteligente por pago
- [ ] Ranking de programas (rapidez, comunicación, claridad, etc.)
- [ ] Objetivos (mensual/anual/diario/horario)
- [ ] Retiros (wallets, USDT, USDC, BTC, ETH, PayPal, etc.)
- [ ] AI Finance Copilot contextual

#### Módulo 5 — Tabla de Oportunidades Premium
- [ ] Filtros avanzados (severidad, bounty range, plataforma)
- [ ] Bulk actions (selección múltiple)
- [ ] Export CSV
- [ ] Badges de severidad con colores intensos
- [ ] Integración con Money Radar

#### Módulo 6 — Experiencia Desktop
- [ ] Tray icon support (pywebview)
- [ ] Window title "Rastro — Investigation OS"
- [ ] Global shortcuts
- [ ] Manejo de ventana (minimize to tray, etc.)

### 📅 Backlog técnico
- [ ] Página de detalle de target (/target/:id)
- [ ] Sistema de notificaciones
- [ ] Tests unitarios (Vitest + Vue Test Utils)
- [ ] Responsive design (mobile sidebar → bottom nav)
- [ ] Estado offline / IndexedDB cache

## Stack oficial
- Backend: FastAPI + SQLAlchemy + SQLite
- Frontend: Vue 3 + Vite + TypeScript + Tailwind v4 + Pinia + ShadCN Vue + Lucide
- IA: agente híbrido OpenRouter → Ollama local
- Desktop: PyInstaller (Windows)
