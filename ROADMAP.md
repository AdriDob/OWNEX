# CATEYE Roadmap

## v1.0 — Foundation (Complete)
- [x] Backend FastAPI con todos los routers
- [x] Base de datos SQLAlchemy con modelos completos
- [x] Orion Context Engine (core/ai/context/engine.py)
- [x] Frontend React inicial

## v1.1 — AI & Intelligence (Complete)
- [x] AI Copilot con OpenRouter + Ollama
- [x] OrionAgent con tool-calling
- [x] Sistema de memoria e inteligencia
- [x] Pipeline de ejecución autónoma

## v1.2 — Vue 3 Frontend (Current — ~90% complete)
- [x] Proyecto Vue 3 + Vite + TypeScript
- [x] ShadCN Vue + Tailwind CSS v4 + Lucide Icons
- [x] Dark mode con glassmorphism
- [x] Layout con Sidebar navegación (6 rutas, colapsable)
- [x] Command Palette (Ctrl+K)
- [x] API Client con auth interceptor, auto-login, loading tracker
- [x] Mission Control Dashboard
  - [x] KPI Cards (datos reales de OrionContext)
  - [x] Next Action card (datos reales)
  - [x] Pipeline funnel chart (datos reales)
  - [x] Top Opportunities table (datos reales, sortable, paginated)
  - [x] Recent Activity feed (datos reales)
- [x] Opportunity Radar — targets reales con búsqueda
- [x] Hot Paths — datos reales de `/api/attack/decision`
- [x] Findings Pipeline — pipeline + hallazgos reales
- [x] Report Center — reportes reales con stats
- [x] AI Copilot panel — chat contextual con API real
- [x] Settings page (placeholder UI)
- [ ] Pages de detalle (target, endpoint, finding, report)

## v1.3 — Polish & Performance (Next)
- [ ] Skeleton loading states en todas las páginas (ya implementados)
- [ ] Manejo global de errores (401 → re-login)
- [ ] Testing (Vitest + Vue Test Utils)

## v1.4 — Mobile & Desktop
- [ ] Responsive design (mobile sidebar → bottom nav)
- [ ] PWA support (service worker)
- [ ] Capacitor integration (Android)
- [ ] Desktop Tauri build

## v1.5 — Enterprise
- [ ] Multi-user auth
- [ ] Team workspaces
- [ ] Audit logging
- [ ] API key management
- [ ] SSO integration
