# OWNEX — Professional Presence Acceleration Plan

> **Objetivo estratégico transversal (2026-08-10).** Construir UNA identidad profesional
> verificable y honesta en GitHub + LinkedIn + Fiverr lo más rápido posible. Tres interfaces,
> una misma identidad técnica. Registrado en `.ai/` como SSOT del plan (owner: Adriel).

## Principio core

NO optimizar por: cantidad de repos, commits, followers, activity graphs fabricados, repos
vacíos, filler AI. SÍ optimizar por: trabajo real, resultados visibles, profundidad técnica,
presentación profesional, reproducibilidad, documentación, capacidad verificable.

**Credibility Rule: nunca fabricar stars, followers, clientes, reviews, empleo, certificaciones,
cobros de bug bounty, commits, contribuidores, métricas de uso, revenue.**

## Posicionamiento objetivo

Software Engineer · AI Automation · Cybersecurity · Autonomous Systems
(verdadero a los proyectos; evidencia > adjetivos)

## Portfolio de 11 proyectos (arquitectura de portfolio, NO 11 monolitos)

OWNEX = flagship (~50% de atención visual). Rastro = sistema de seguridad sustancial.
El resto = proyectos medianos/pequeños pulidos. Un proyecto terminado de 800 líneas vale más
que uno inconcluso de 80.000.

| # | Proyecto | Demuestra | Estrategia de origen |
|---|----------|-----------|----------------------|
| ⭐1 | **OWNEX** | Producto: IA, agentes, automatización, orquestación, UI, arquitectura, modelos local/cloud | repo principal (renombrar `rastrohunteralpha` → pendiente decisión) |
| 2 | **Rastro** | Bug bounty / security automation: recon, target intel, endpoints, authorization, reporting | pipeline CATEYE real (discover→recon→hypo→validate→report→ai_bounty) |
| 3 | **ReconForge** | Asset discovery, subdomains, HTTP analysis, tool orchestration | módulos `cores/recon/` + `cores/tools/` (extracción) |
| 4 | **IDOR-Lab** | Laboratorio educativo seguridad (multi-tenant, IDOR, metodología — legal/educativo) | crear pequeño standalone |
| 5 | **ReportSmith** | Reportes técnicos automáticos: structured data, Markdown, templates, evidence | pipeline de reporting exists + evidencia (extracción) |
| 6 | **AgentFlow** | Orquestación de agentes: lifecycle, routing, tool calling, state, memory, model abstraction | `cores/workflow/` + `core/autonomy/` (extracción) |
| 7 | **DevScout** | Descubrimiento de oportunidades dev: ingest clasificado, filtrado, ranking | `cores/opportunity/` (extracción) |
| 8 | **DataFlow** | Automatización datos: CSV/JSON, validación, transformación, dedup, human-review | módulos de datos DWE (extracción) |
| 9 | **LocalAI-Gateway** | Abstracción de providers IA: Ollama, routing, fallbacks, conf, local inference | OAR `cores/ai/runtime/` (extracción) |
| 10 | **EvidenceVault** | Evidencia: screenshots, hashing, metadata, integridad, export | evidence composer/storage (extracción) |
| 11 | **TaskPilot** | Automatización general: scheduling, retries, logging, plugins, CLI/UI | scheduler/task layer (extracción) |

**Regla de extracción**: cada repo extraído debe ser usable standalone (con sus deps
copiadas), pasar BUILD + TESTS + DOC + SCREENSHOT antes de publicarse. No repo abierto a medias.

## Shared engineering

Componentes comunes reutilizables entre repos (AI provider abstraction, logging, config,
CLI patterns, test utils, report generation, evidence handling, data validation, agent
interfaces). Prohibido copy-paste masivo; prohibidos microservicios artificiales.

## Estándar de repo profesional (donde aplique)

README.md · LICENSE · CHANGELOG.md · CONTRIBUTING.md · SECURITY.md · `.gitignore` ·
tests/ · docs/ · examples/ · CI · config example · instalación · arquitectura ·
screenshots · usage · limitations · roadmap. Solo secciones que tengan sentido real.

## README standard

Primeros 30 segundos excelentes: QUÉ ES · POR QUÉ · QUÉ HACE · TECNOLOGÍAS · SCREENSHOT/DEMO ·
INSTALACIÓN · QUICK START · ARQUITECTURA · EJEMPLOS · LIMITACIONES · ROADMAP · LICENSE.

## Visual standard

Familia visual coherente (design system OWNEX: black `#05060A`, white, tesla red
`#e82127` solo acento saturado, sin neón). Misma tipografía/calidad de docs/treatment de
screenshots/diagramas. No idénticos: misma ingeniería, identidad propia por proyecto.

## No AI slop

Prohibido: CRUD genéricos, weather/todo/calculator apps, chatbots falsos, wrappers vacíos,
tutoriales copiados, "AI-powered" sin profundidad. Cada proyecto demuestra un concepto real.

## Maturidad por proyecto

FLAGSHIP / PRODUCTION-LIKE / TECHNICAL TOOL / EDUCATIONAL LAB / EXPERIMENT — jamás vender un
experimento como producción.

## GitHub profile README (repo `AdriDob/AdriDob`)

Identidad OWNEX · posicionamiento corto · tecnologías core · proyectos destacados · OWNEX como
flagship · áreas técnicas · screenshots seleccionados · links (GitHub/LinkedIn/Fiverr). Tono:
ingeniero técnico competente, NO marketing corporativo. Diseño: secciones cortas, jerarquía
visual, badges limitados, screenshots reales, sin badge spam, sin metros de texto, sin métricas
falsas, sin manipulación del graph de contribuciones.

## Pinned (6)

OWNEX · Rastro · ReconForge · AgentFlow · LocalAI-Gateway · ReportSmith
(ajustar si la calidad real lo dicta; calidad > nombres)

## LinkedIn

Narrativa coherente con la evidencia GitHub. Titles solo verdaderos. Featured: OWNEX, GitHub,
mejor proyecto técnico, artículo/documentación, portfolio. Por proyecto: short description,
problem, solution, technologies, result, GitHub link, screenshots. Contenido: descubrimientos
técnicos, progreso, arquitectura, metodología security, lessons, releases, demos. Sin spam de
posts AI. Distinguir claramente: PROYECTO PERSONAL / OPEN SOURCE / EXPERIMENT / CLIENT WORK /
EXPERIENCIA PROFESIONAL.

## Fiverr

Gigs enfocados, solo capacidades reales: AI Automation · Python Development · Web Automation ·
Bug Fixing · API Integration · Data Processing. Portfolio con evidencia visual real de los
proyectos (screenshots, dashboards, arquitectura, antes/después, ejemplos de reportes). Nada de
"puedo hacer de todo". Trabajo personal etiquetado como personal.

## Cross-platform consistency

Mismo nombre, posicionamiento, avatar, foco tecnológico, nombres de proyecto, links, lenguaje
de portfolio. Idioma adaptado: GitHub técnico · LinkedIn profesional · Fiverr comercial.

## Portfolio evidence system (`docs/portfolio/<project>/`)

overview · screenshots · arquitectura · features · decisiones técnicas · demo · instalación ·
resultados · limitaciones · stack. El MISMO paquete alimenta GitHub + LinkedIn + Fiverr + CV +
website.

## Professional website (post-portfolio)

Solo después de que el portfolio sea fuerte. Dominio, homepage, showcase OWNEX, projects,
services, contact, links.

## Fases de entrega (speed strategy)

- **PHASE 1 — Credibility Foundation**: OWNEX (rename + polish), GitHub profile README,
  branding, portfolio evidence, LinkedIn alignment, Fiverr foundation.
- **PHASE 2 — Supporting**: Rastro, ReconForge, AgentFlow, ReportSmith, LocalAI-Gateway.
- **PHASE 3 — Specialized**: IDOR-Lab, DevScout, DataFlow, EvidenceVault, TaskPilot.

Parallelizable: branding, documentation, testing, portfolio screenshots, repo init, CI, READMEs,
architecture docs. No paralelizar ediciones conflictivas del mismo archivo.

## Quality gate (antes de publicar cada repo)

BUILD · TEST · DOCUMENTATION · SECURITY · SCREENSHOT · INSTALLATION · LINK · README · LICENSE ·
SECRETS · QUALITY. Publication gate: buscar API keys, tokens, passwords, private keys, info
personal, paths locales, temp files, debug logs, config específica de máquina → sanitizar.

## Portfolio Priority Score (no publicar bajo scoring)

Technical depth 25% · Completeness 20% · Demonstrability 15% · Documentation 10% ·
Visual quality 10% · Relevance to services 10% · Maintainability 5% · Originality 5%.

## Objetivo final

Hacer DIFÍCIL que un reviewer razonable descarte el perfil por presentación pobre o falta de
evidencia. Señal: "construye sistemas complejos, entiende IA/automatización/seguridad/software,
y sabe terminar y presentar lo que construye".

## Estado (sesión 2026-08-10)

- [x] Plan registrado en `.ai/`
- [ ] Renombrar repo flagship (decisión pendiente: `OWNEX` vs `Rastro`)
- [ ] GitHub profile README (`AdriDob/AdriDob`)
- [ ] Portfolio evidence `docs/portfolio/ownnex/` + `docs/portfolio/rastro/`
- [ ] Pinned 6 repos
- [ ] PHASE 2/3 (ver TASK_QUEUE.md)