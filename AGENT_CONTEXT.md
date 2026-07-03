# AGENT_CONTEXT.md — Protocolo de Coordinación Multi-IA

## Última actualización
2026-06-30

## Roles asignados

| Asistente | Rol | Puede ejecutar código en el repo |
|-----------|-----|-----------------------------------|
| OpenCode (VS Code) | Único motor de ejecución. Escribe, corre y commitea código. | SÍ — único autorizado |
| Claude | Arquitecto y coordinador. Revisa reportes, diseña prompts, detecta riesgos. | NO |
| GPT | Segunda opinión técnica puntual, debugging contrastado. | NO |
| Grok | Brainstorming de producto, ideas de features, contexto de mercado. | NO |
| Qwen (Brave) | Consultas rápidas de sintaxis/comandos del día a día. | NO |
| Meta AI | Recordatorios y agenda personal. Sin relación con el código. | NO |

## Regla de oro

NINGÚN asistente que no sea OpenCode debe generar código que se
ejecute directamente sobre este repositorio. Si otro asistente (GPT,
Grok, Qwen) sugiere una idea o un cambio, esa sugerencia debe pasar
primero por revisión humana o por Claude antes de convertirse en un
prompt para OpenCode. Esto evita trabajo duplicado, contradictorio,
o huérfano (ej: el caso de la carpeta Vue duplicada que fue integrada
como frontend/ principal recién después de decisión del dueño).

## Antes de crear cualquier archivo o carpeta nueva

OpenCode debe:
1. Verificar si ya existe algo equivalente en el repo
   (buscar por nombre similar, por funcionalidad, por convención)
2. Si la tarea implica una reestructuración grande (nuevo frontend,
   nuevo framework, nueva carpeta de nivel raíz), confirmar
   explícitamente con el usuario antes de proceder, aunque el prompt
   no lo haya pedido en detalle
3. Registrar en este archivo, en la sección "Decisiones recientes",
   cualquier adición estructural significativa

## Decisiones recientes

- 2026-07-02 — **FASE 4 — UX/UI Audit CATEYE completada:**
  - Tema CATEYE cyber security aplicado globalmente (verde #00ff41, negro #050505, blanco #e0f0e0)
  - `frontend/src/style.css` — overhaul completo con scanlines, cyber-card, glass-terminal, matrix effects
  - `frontend/src/App.vue` — scanline overlay global, CATEYE title
  - `frontend/src/components/layout/AppSidebar.vue` — logo CATEYE (Eye icon), tipografía mono, cyber-card balance
  - `frontend/src/components/layout/AppLayout.vue` — topbar con badge CATEYE
  - `frontend/src/components/layout/Breadcrumbs.vue` — font-mono consistente
  - `frontend/src/pages/Dashboard.vue` — centro de inteligencia CATEYE: intel bar (detectados/confirmados/tasa), KPI cyber-cards, colores por severidad, footer system status
  - `frontend/src/components/copilot/CopilotPanel.vue` — branding CATEYE, glass-terminal messages, modo contextual
  - `frontend/src/components/ui/Card.vue` — usa cyber-card en lugar de glass-card
  - `frontend/src/components/ui/Badge.vue` — font-mono con bordes
  - `frontend/src/components/ui/Button.vue` — font-mono, sombras primary/destructive
  - `frontend/src/components/ui/Tooltip.vue` — nuevo: tooltips contextuales con hover delay, 4 posiciones
  - `frontend/src/components/ui/ContextMenu.vue` — nuevo: menú contextual right-click con acciones
  - `frontend/index.html` — title actualizado a "CATEYE — Security Intelligence OS"
  - `frontend/src/router/index.ts` — meta title CATEYE
- 2026-07-02 — **FASE 5 — OSINT Integration (16 APIs) completada:**
  - `cores/recon/osint_api.py` — 16 clientes OSINT asíncronos: Shodan, Censys, VirusTotal, SecurityTrails, AlienVault OTX, URLScan.io, Hunter.io, BuiltWith, Have I Been Pwned, GreyNoise, IntelX, Pulsedive, ThreatFox, IPInfo, SpoofCheck
  - `api/routers/osint.py` — router `/api/osint/` con listado, query simple y bulk
  - `.env.example` — 14 nuevas variables para API keys OSINT

## Stack oficial del proyecto (no debe haber alternativas paralelas)

- Backend: Python 3.10+ + FastAPI + SQLAlchemy + SQLite/PostgreSQL
- Frontend: Vue 3 + TypeScript + Vite + Tailwind v4 + Pinia + Radix Vue + Lucide
- IA: Gemini (primario), OpenRouter (fallback cloud), Ollama local (qwen3:14b)
- Empaquetado desktop: PyInstaller + PyWebView + Pystray, build nativo en Windows
- Marca oficial: **CATEYE** (anteriormente ORION/Rastro)

## Cómo retomar trabajo en una nueva sesión

Cualquier IA (especialmente OpenCode al iniciar una tarea nueva) debe
leer este archivo completo antes de proponer cambios. Si el archivo
contradice lo que la IA cree saber del proyecto, este archivo tiene
prioridad porque refleja el estado real verificado, no el estado
asumido.
