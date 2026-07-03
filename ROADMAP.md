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

## v1.2 — Vue 3 Frontend (Complete — 100%)
- [x] Proyecto Vue 3 + Vite + TypeScript
- [x] ShadCN Vue + Tailwind CSS v4 + Lucide Icons
- [x] Dark mode con glassmorphism
- [x] Layout con Sidebar navegación (13 items en 3 secciones, colapsable)
- [x] Command Palette (Ctrl+K) + Copilot (⌘B)
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
- [x] Settings con auto-save, validación de import, tools verify, reset con doble confirmación
- [x] Páginas de detalle (target, endpoint, finding, report, pipeline, investigation)
- [x] Onboarding 5 pasos con skip con confirmación

## v1.3 — Polish & Performance (Complete)
- [x] Audit UX completa (24 fricciones resueltas)
- [x] Skeleton loading states en todas las páginas
- [x] Manejo global de errores (401 → re-login, catch silenciosos → console.warn)
- [x] Sidebar reducida 36→13 items, scrollbar visible
- [x] Auto-save visual feedback, breadcrumbs dinámicos
- [x] Scanline overlay con CSS variable, no hardcoded
- [x] WebSocket status indicator, keyboard shortcuts visibles
- [x] Onboarding 9→5 pasos, tutorial corregido
- [x] Banner R A S T R O → C A T E Y E, RASTRO_* → CATEYE_* env vars
- [x] Unificación de paths (tray/updater → cores/utils/paths.py)
- [x] cache_size migrado a EnvConfig, RastroConfig deprecated

## v1.4 — Testing & Infrastructure (Current — ~0%)
- [ ] Testing (Vitest + Vue Test Utils)
- [ ] Python tests (pytest)
- [ ] Rebuild Android compiled assets (python scripts/build_android.py)

## v1.5 — Mobile & Desktop
- [ ] Responsive design (mobile sidebar → bottom nav)
- [ ] PWA support (service worker)
- [ ] Capacitor integration (Android)
- [ ] Desktop Tauri build

## v1.6 — Enterprise
- [ ] Audit logging
- [ ] API key management
- [ ] SSO integration
