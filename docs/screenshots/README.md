# CATEYE — Screenshots

Imágenes del sistema CATEYE. Todos los screenshots son SVGs generados con la estética cyber/terminal del sistema (verde `#00ff41` sobre negro `#050505`).

## Pantallas principales

| Screenshot | Descripción |
|---|---|
| [![Dashboard](screenshots/dashboard-main.svg)](screenshots/dashboard-main.svg) | **Economic Dashboard** — KPIs en tiempo real, gráficos de severidad y veredictos, oportunidades prioritarias. La pantalla principal que responde a: ¿cuánto dinero tengo? ¿qué debo hacer ahora? |
| [![Pipeline](screenshots/pipeline-monitor.svg)](screenshots/pipeline-monitor.svg) | **Findings Pipeline** — Flujo completo desde detección hasta reporte pagado. Visualiza las 5 etapas (Detectado → Validado → Confirmado → Reportado → Pagado) con conteo y acciones por hallazgo. |
| [![Report Center](screenshots/report-detail.svg)](screenshots/report-detail.svg) | **Report Center** — Generación de reportes profesionales con IA. PoC, impacto, remediación y CVSS en un solo clic. Exportación a Markdown/PDF. |
| [![Identity Vault](screenshots/identity-center.svg)](screenshots/identity-center.svg) | **Identity Vault** — Bóveda de credenciales cifradas con AES-256-GCM para HackerOne, Bugcrowd, Intigriti y más. Gestión de cuentas de cobro (USDT, BTC, PayPal). |
| [![System Health](screenshots/system-health.svg)](screenshots/system-health.svg) | **System Health** — Monitoreo en tiempo real de todos los componentes: backend, base de datos, IA local, herramientas de recon, WebSocket, integraciones y recursos del sistema. |

## Navegación adicional

| Página | Ruta | Descripción |
|---|---|---|
| **Money Radar** | `/money-radar` | Programas rankeados por ORION Score con búsqueda y filtros |
| **Opportunity Radar** | `/radar` | Tabla de oportunidades ordenable y paginada |
| **Hot Paths** | `/hot-paths` | Vectores de ataque priorizados con scoring de riesgo |
| **Program Intel** | `/programs/:id` | Inteligencia profunda por programa: scope, tech stack, tiers |
| **Memory Patterns** | `/memory-patterns` | Patrones aprendidos del historial de cacería |
| **AI Copilot** | `Ctrl+B` | Asistente contextual con conocimiento completo del sistema |
| **Settings** | `/settings` | Configuración general, IA, herramientas, API keys y apariencia |
| **Connections** | `/connections` | Gestión de conexiones a plataformas y cuentas de cobro |

## Convenciones visuales

- **Fondo**: `#050505` con grid subtle y scanline overlay
- **Verde**: `#00ff41` — primario, éxito, activo
- **Cian**: `#00b8ff` — acento informativo
- **Rojo**: `#ff1744` — crítico, destructivo, desconectado
- **Naranja**: `#ffab00` / `#ff6600` — warning, medio-alto
- **Tipografía**: JetBrains Mono (mono), Inter (sans)
- **Tarjetas**: Glass effect con borde sutil `rgba(0,255,65,0.08)` y glow superior

## Notas

- Los SVGs son generados y no requieren conexión a backend para visualizarse
- Representan el estado del sistema con datos de ejemplo realistas
- El diseño es responsivo y se adapta al theme del README (claro/oscuro)
