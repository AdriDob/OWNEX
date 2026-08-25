# FRONTEND VISUAL AUDIT — OWNEX Alpha 1.0 (FASE 0)

> Fecha: 2026-08-25 · Base: main@59246d2c+ · Método: código real como verdad + métricas medibles.
> Alcance: diagnóstico completo previo a implementación visual. NO incluye cambios.

## 1. Design system existente (lo que YA hay y hay que consolidar, no duplicar)

| Pieza | Ubicación | Estado |
|---|---|---|
| Tokens CSS | `frontend/src/design/tokens.css` (--ownex-bg-*, --ownex-red #E82127, green/yellow/gold/text-*) | ✅ SSOT declarado; **sub-aplicado** (ver §2) |
| Theme engine | `composables/useThemeEngine.ts` + `public/assets/branding/themes/*.json` (6 temas) | ✅ funcional; tesla.json default alineado post-fix bfcf799d |
| Brand identity v3 | `assets/branding/OWNEX_BRAND_IDENTITY.md` + `.ai/OWNEX_DESIGN_SYSTEM.md` | ✅ documentos vigentes |
| Componentes UI base | `components/ui/`: OwnexButton, OwnexBadge, ErrorState, Card, Modal, Toast(useToast) | ✅ existen; cobertura parcial |
| Command palette | `CommandPalette.vue` montado en AppLayout | ✅ verificar integración rutas reales |
| Layout global | `AppLayout.vue` + `AppSidebar.vue` + overlays (CopilotPanel, InspectorPanel) | ✅ único shell activo |

## 2. Problemas medibles (evidencia)

| Métrica | Valor | Impacto |
|---|---|---|
| Hex hardcodeados en .vue | **1.073** | Tokens bypaseados → temas no gobiernan todo; riesgo de regresión cromática recurrente |
| border-radius distintos | **9 escalones** (3,4,6,8,10,12,9999,999px + %) | Sin escala; inconsistencia visible entre páginas |
| Hits mock/fake/coming-soon (pages+services) | **104** | Riesgo "dato inventado como real"; requiere clasificación §24 |
| Capa legacy jarvis | `styles/tesla-jarvis-theme.css` vivo con gradientes rojos; 4 consumidores (`MobileCompanion`, 2 wizards, OmegaChatNative-huérfano) | Páginas que "parecen otro producto" |
| Página mock ruteada | `SecurityCycle.vue` ("Simulate API call" setTimeout :287) | Única sección SECURITY = fake |
| ErrorState contrato dual | resuelto `242c6466`; verificar adopción en resto de páginas | — |
| ownexData swallowing | resuelto para 6 feeders de dashboard; otros servicios aún tragán (p.ej. fetchCycles error→monitoring) | errores silenciosos remanentes |
| Huérfanos confirmados | 26 componentes + Dashboard.vue + broken import Progress | limpieza FASE 7 (gateada) |

## 3. Inconsistencias estructurales (jerarquía/navegación)

- **Sidebar**: un solo nivel plano largo (40+ ítems históricos en secciones) — sin agrupación por intención OPERATE/INTELLIGENCE/AUTOMATION/SYSTEM; `OrionSidebar.vue` huérfano compite conceptualmente con `AppSidebar`.
- **Mission Control ×3**: `/` WelcomePage (estática), `/dashboard` GamingConsole, `/classic` MissionControl — tres "homes" compitiendo; ninguna implementa jerarquía NEXT ACTION dominante (spec §4-6).
- **Dinero sin semántica**: potential/expected/confirmed mezclados en cards (Capital tabs lo separa bien; dashboards no).
- **Estados de sistema**: dots dispersos (TitleBar WS, AgentFleet, WorkCycleCard) sin componente StatusBadge único ni vocabulario compartido (OPERATIONAL/SCANNING/…).
- **Tablas**: QTable-like sin sorting/filter consistente; densidades distintas por página.
- **Loading**: mezcla spinner genérico / skeletons manuales por página; sin Skeleton component compartido.
- **Accesibilidad**: focus visible inconsistente; varios botones-div; aria ausente en icon-only.

## 4. Páginas prioritarias — estado actual

| Página | Funcional | Visual | Gap principal |
|---|---|---|---|
| MissionControl (/classic) | ✅ datos+retry OK | 🟡 | sin NEXT ACTION; KPIs planos |
| GamingConsole (/dashboard) | ✅ tras fixes | 🔴 | sin empty states ×3 listas; estética gamer (violación §28) |
| WelcomePage (/) | estática | 🟡 | no comunica estado real del sistema |
| IntelligenceDashboard | 🟡 catch-ignore | 🟡 | sin error state; secciones vacías |
| TargetsPage | ✅ mejor alumno | 🟢 | patrón a replicar |
| Capital | ✅ | 🟡 | retry bug ya resuelto; densidad alta |
| Settings | ✅ sólida | 🟡 | catálogo providers dinámico ya wired |
| SecurityCycle | ❌ MOCK | 🔴 | decidir: wire real o desrutar hasta implementar |
| ApplicationsAssistant / FirstDayGuide | ✅ API+UI | 🟡 | integrarlas al ciclo central (NEXT ACTION source) |

## 5. Decisiones de diseño VIGENTES (no re-discutir)

1. TESLA mandate: negro puro, blanco primario, **rojo solo error/destructivo**, azul oscuro fondo ambiental (directiva owner 2026-08-25), sin neón/glow/gradients gratuitos.
2. CALM UX (DECISIONS 2026-08-10): sin drama, sin urgencia falsa.
3. Tokens.css = única fuente cromática; temas = variantes sobre tokens.
4. Nombres de rutas existentes NO se renombran (compatibilidad).

## 6. Plan de fases (mapeado al spec) — orden ejecutable

> **✅ F1 núcleo CERRADO (2026-08-25)**: tokens semánticos `--color-*` + escala tipográfica + `.money` (`65ab6b69`). **Trío de componentes base completo**: `MoneyValue.vue` (4 semánticas económicas, `f213b01e`) · `StatusBadge.vue` (9 estados sistema, `aa5de3b4`) · `Skeleton.vue`+`LoadingState.vue` (preexistentes, API verificada). **F1b restante = SOLO adopción** en páginas prioritarias: TopBar (StatusBadge reemplaza dot WS), MissionControl/GamingConsole/Capital (MoneyValue en montos), IntelligenceDashboard (LoadingState en secciones). Sin crear más componentes hasta que la adopción demuestre un gap real.

- **F1 Design System**: extender tokens.css con escala completa (color semantic set §prompt-8, spacing 4-64, radius sm/md/lg/xl+pill, shadows sutiles, tipografía display/body/label/numeric-mono); migración incremental hex→var() por página tocada (prohibido big-bang); Skeleton + StatusBadge + MoneyValue + SectionHeader/PageHeader nuevos (verificando no-dup contra ui/*).
- **F2 App Shell**: AppSidebar agrupado por intención (colapsable), TopBar con StatusBadge global (fuente: /api/system/health ya existente), CommandPalette audit contra router real.
- **F3 Mission Control**: unificar homes → NEXT ACTION card dominante (fuente real: GET /applications/overview.next_action + workbank best_ready + daily-brief top pick), OpportunityRadar top-3, Activity pipeline (discovery→scoring→filtering→recommendation con counts reales de ownexData), fila inferior earnings/opps/automation/tasks.
- **F4 Opportunities**: OpportunityCard según spec §10 usando SOLO campos existentes (payment/acceptance_probability/payment_compat/barrier/reasoning de RankedOpportunity); filtros/sorting DataTable.
- **F5 Work/Applications**: flujo prepare→review→deliver visible paso a paso (endpoints ya existen).
- **F6 Extensión**: aplicar sistema vía componentes compartidos; migrar 4 consumidores jarvis-legacy; SecurityCycle: wire a /security/executive real o quitar de nav hasta implementar (decisión owner).
- **F7 Cleanup**: batch huérfanos gateado + clasificación de los 104 hits mock (eliminar inventados; documentar fallbacks legítimos).

## 7. Criterios de aceptación por fase
type-check 0 · build OK · suite fast backend verde · grep radius fuera de escala = decreciente · hex hardcodeados decreciente por página tocada · cero dato mostrado sin fuente backend · screen-review checklist (§33) por página.

## 8. Riesgos
- Migración masiva hex→tokens en un solo commit = regresiones visuales globales → PROHIBIDO; ir página por página.
- No romper contratos ownexData/api.ts al rediseñar cards.
- WIP concurrente activo en guided-mode/GuidedDashboard.vue → coordinar antes de tocar esa zona.
