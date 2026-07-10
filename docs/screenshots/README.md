# ORION Platform — Screenshots

Imágenes del sistema ORION Platform v4.1.0. Todos los screenshots son SVGs generados con la estética cyber/terminal del sistema (verde `#00ff41` sobre negro `#050505`).

## Pantallas principales

| Screenshot | Descripción |
|---|---|
| [![Dashboard](screenshots/dashboard-main.svg)](screenshots/dashboard-main.svg) | **Economic Dashboard v2** — KPIs en tiempo real, gráficos de severidad y veredictos, oportunidades prioritarias. Seguridad: AES-256-GCM, CSRF activo, audit log operativo. |
| [![Pipeline](screenshots/pipeline-monitor.svg)](screenshots/pipeline-monitor.svg) | **Findings Pipeline** — Flujo completo desde detección hasta reporte pagado. Visualiza las 5 etapas (Detectado → Validado → Confirmado → Reportado → Pagado) con conteo y acciones por hallazgo. |
| [![Report Center](screenshots/report-detail.svg)](screenshots/report-detail.svg) | **Report Center** — Generación de reportes profesionales con IA. PoC, impacto, remediación y CVSS en un solo clic. Exportación a Markdown/PDF. |
| [![Identity Vault](screenshots/identity-center.svg)](screenshots/identity-center.svg) | **Identity Vault v2** — Bóveda de credenciales cifradas con AES-256-GCM (clave aleatoria, no derivada). Gestión de cuentas de cobro (USDT, BTC, PayPal). Audit log de autenticación. |
| [![System Health](screenshots/system-health.svg)](screenshots/system-health.svg) | **System Health v2** — Monitoreo en tiempo real de todos los componentes: backend, DB, IA local, herramientas de recon, WebSocket, circuit breaker, y estado de seguridad. |
| [![Financial Dashboard](screenshots/financial-dashboard.svg)](screenshots/financial-dashboard.svg) | **Financial Dashboard v4.1** — Patrimonio total, breakdown por activo, objetivo Libertad 30K, ingresos del mes, precios CoinGecko, estado Takenos. |
| [![Integration Center](screenshots/integration-center.svg)](screenshots/integration-center.svg) | **Integration Center v4.1** — Estado de todas las integraciones (🟢🟡🔴), última sincronización, errores, botones Test/Sync. |

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
| **Financial Dashboard** | `/financial` | Dashboard financiero unificado con CoinGecko, Takenos, ATLAS |
| **Integration Center** | `/integrations` | Estado y test de todas las integraciones del sistema |

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
