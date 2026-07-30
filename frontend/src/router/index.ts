import type { RouteLocationNormalized, RouteRecordRaw } from 'vue-router'
import { isSessionValid } from '@/lib/api'

// Pages that don't require auth
const publicPages = ['login', 'activation']

export function isPublicRoute(to: Pick<RouteLocationNormalized, 'name' | 'meta'>) {
  return !!to.meta?.public || publicPages.includes(to.name as string)
}

export function canAccessRoute(to: Pick<RouteLocationNormalized, 'name' | 'meta'>) {
  if (isPublicRoute(to)) return true
  return isSessionValid()
}

// ─────────────────────────────────────────────────────────────────
// CONSOLIDATED ROUTES — 8 Main Sections
// ─────────────────────────────────────────────────────────────────
//
// 1. MISSION CONTROL      → /                    (Dashboard ejecutivo + HUNT button)
// 2. INTELLIGENCE         → /intelligence        (Findings, Hypotheses, Evidence, Investigations)
// 3. TARGETS              → /targets             (Targets, Discovery, Attack Surface, Prioritization)
// 4. REPORTS              → /reports             (Report Queue, Report Center, History, Submission)
// 5. CAPITAL              → /capital             (Revenue, Payouts, EV Targets, Platform Speed, Economics)
// 6. OPERATIONS           → /operations          (Scheduler, Pipelines, Tools, Health, Settings)
// 7. INTEGRATIONS         → /integrations        (Connections, Wallets, Accounts, Platforms)
// 8. COPILOT              → /copilot             (Assistant, Memory, Learning, Recommendations)
// ─────────────────────────────────────────────────────────────────

export const routes: RouteRecordRaw[] = [
  // ── AUTH ──
  {
    path: '/login',
    name: 'login',
    component: () => import(/* webpackChunkName: "auth" */ '@/pages/LoginPage.vue'),
    meta: { title: 'Iniciar Sesión', public: true },
  },
  {
    path: '/activation',
    name: 'activation',
    component: () => import(/* webpackChunkName: "auth" */ '@/pages/Activation.vue'),
    meta: { title: 'Activación', public: true },
  },

  // ── 1. MISSION CONTROL ──
  {
    path: '/',
    name: 'mission-control',
    component: () => import(/* webpackChunkName: "mission-control" */ '@/pages/GamingConsole.vue'),
    meta: { title: 'Control de Misión' },
  },
  {
    path: '/classic',
    name: 'classic-mission-control',
    component: () => import(/* webpackChunkName: "mission-control" */ '@/pages/MissionControl.vue'),
    meta: { title: 'Classic Mission Control' },
  },

  // ── 2. INTELLIGENCE ──
  {
    path: '/intelligence',
    name: 'intelligence',
    component: () => import(/* webpackChunkName: "intelligence" */ '@/pages/IntelligenceDashboard.vue'),
    meta: { title: 'Inteligencia' },
    children: [
      { path: '', redirect: { name: 'intelligence-findings' } },
      {
        path: 'findings',
        name: 'intelligence-findings',
        component: () => import(/* webpackChunkName: "intelligence" */ '@/pages/Findings.vue'),
        meta: { title: 'Hallazgos' },
      },
      {
        path: 'hypotheses',
        name: 'intelligence-hypotheses',
        component: () => import(/* webpackChunkName: "intelligence" */ '@/pages/HypothesisQueue.vue'),
        meta: { title: 'Hipótesis' },
      },
      {
        path: 'evidence',
        name: 'intelligence-evidence',
        component: () => import(/* webpackChunkName: "intelligence" */ '@/pages/EvidenceCenter.vue'),
        meta: { title: 'Evidencia' },
      },
      {
        path: 'investigations',
        name: 'intelligence-investigations',
        component: () => import(/* webpackChunkName: "intelligence" */ '@/pages/InvestigationCenter.vue'),
        meta: { title: 'Investigaciones' },
      },
      {
        path: 'investigations/:id',
        name: 'investigation-detail',
        component: () => import(/* webpackChunkName: "intelligence" */ '@/pages/InvestigationDetail.vue'),
        meta: { title: 'Detalle Investigación' },
      },
      {
        path: 'confidence',
        name: 'intelligence-confidence',
        component: () => import(/* webpackChunkName: "intelligence" */ '@/pages/ConfidenceDashboard.vue'),
        meta: { title: 'Confianza' },
      },
      {
        path: 'differential',
        name: 'intelligence-differential',
        component: () => import(/* webpackChunkName: "intelligence" */ '@/pages/DifferentialEngine.vue'),
        meta: { title: 'Análisis Diferencial' },
      },
    ],
  },

  // ── 3. TARGETS ──
  {
    path: '/targets',
    name: 'targets',
    component: () => import(/* webpackChunkName: "targets" */ '@/pages/TargetsPage.vue'),
    meta: { title: 'Targets' },
    children: [
      { path: '', redirect: { name: 'targets-list' } },
      {
        path: 'list',
        name: 'targets-list',
        component: () => import(/* webpackChunkName: "targets" */ '@/pages/TargetsPage.vue'),
        meta: { title: 'Lista de Targets' },
      },
      {
        path: 'discovery',
        name: 'targets-discovery',
        component: () => import(/* webpackChunkName: "targets" */ '@/pages/Discovery.vue'),
        meta: { title: 'Discovery' },
      },
      {
        path: 'attack-surface',
        name: 'targets-attack-surface',
        component: () => import(/* webpackChunkName: "targets" */ '@/pages/AttackSurface.vue'),
        meta: { title: 'Superficie de Ataque' },
      },
      {
        path: 'prioritization',
        name: 'targets-prioritization',
        component: () => import(/* webpackChunkName: "targets" */ '@/pages/OpportunityRadar.vue'),
        meta: { title: 'Priorización EV' },
      },
      {
        path: ':id',
        name: 'target-detail',
        component: () => import(/* webpackChunkName: "targets" */ '@/pages/TargetDetail.vue'),
        meta: { title: 'Detalle Target' },
      },
      {
        path: 'endpoints/:id',
        name: 'endpoint-detail',
        component: () => import(/* webpackChunkName: "targets" */ '@/pages/EndpointDetail.vue'),
        meta: { title: 'Detalle Endpoint' },
      },
    ],
  },

  // ── 4. REPORTS ──
  {
    path: '/reports',
    name: 'reports',
    component: () => import(/* webpackChunkName: "reports" */ '@/pages/ReportCenter.vue'),
    meta: { title: 'Reportes' },
    children: [
      { path: '', redirect: { name: 'reports-queue' } },
      {
        path: 'queue',
        name: 'reports-queue',
        component: () => import(/* webpackChunkName: "reports" */ '@/pages/ReportQueue.vue'),
        meta: { title: 'Cola Priorizada' },
      },
      {
        path: 'center',
        name: 'reports-center',
        component: () => import(/* webpackChunkName: "reports" */ '@/pages/ReportCenter.vue'),
        meta: { title: 'Centro de Reportes' },
      },
      {
        path: 'history',
        name: 'reports-history',
        component: () => import(/* webpackChunkName: "reports" */ '@/pages/ReportHistory.vue'),
        meta: { title: 'Historial' },
      },
      {
        path: ':id',
        name: 'report-detail',
        component: () => import(/* webpackChunkName: "reports" */ '@/pages/ReportDetail.vue'),
        meta: { title: 'Editor de Reporte' },
      },
      {
        path: 'verification',
        name: 'reports-verification',
        component: () => import(/* webpackChunkName: "reports" */ '@/pages/VerificationGuide.vue'),
        meta: { title: 'Guía de Validación' },
      },
    ],
  },

  // ── 5. CAPITAL ──
  {
    path: '/capital',
    name: 'capital',
    component: () => import('@/pages/Capital.vue'),
    meta: { title: 'Capital' },
  },

  // ── 5.5 SECURITY ──
  {
    path: '/security',
    name: 'security',
    component: () => import('@/pages/SecurityCycle.vue'),
    meta: { title: 'Security Cycle' },
  },

  // ── 6. OPERATIONS ──
  {
    path: '/operations',
    name: 'operations',
    component: () => import('@/pages/OperationsDashboard.vue'),
    meta: { title: 'Operaciones' },
    children: [
      { path: '', redirect: { name: 'operations-dashboard' } },
      {
        path: 'dashboard',
        name: 'operations-dashboard',
        component: () => import('@/pages/OperationsDashboard.vue'),
        meta: { title: 'Panel de Operaciones' },
      },
      {
        path: 'pipelines',
        name: 'operations-pipelines',
        component: () => import('@/pages/PipelineMonitor.vue'),
        meta: { title: 'Pipelines' },
      },
      {
        path: 'pipelines/:id',
        name: 'pipeline-detail',
        component: () => import('@/pages/PipelineDetail.vue'),
        meta: { title: 'Detalle Pipeline' },
      },
      {
        path: 'scheduler',
        name: 'operations-scheduler',
        component: () => import('@/pages/ActionsView.vue'),
        meta: { title: 'Scheduler / Acciones' },
      },
      {
        path: 'tools',
        name: 'operations-tools',
        component: () => import('@/pages/OpportunityPlanner.vue'),
        meta: { title: 'Herramientas' },
      },
      {
        path: 'health',
        name: 'operations-health',
        component: () => import('@/pages/HealthCenter.vue'),
        meta: { title: 'Health Center' },
      },
      {
        path: 'settings',
        name: 'operations-settings',
        component: () => import('@/pages/Settings.vue'),
        meta: { title: 'Configuración' },
      },
      {
        path: 'workflows',
        name: 'operations-workflows',
        component: () => import('@/pages/Workflows.vue'),
        meta: { title: 'Workflows' },
      },
      {
        path: 'replay',
        name: 'operations-replay',
        component: () => import('@/pages/ReplayCenter.vue'),
        meta: { title: 'Replay Center' },
      },
      {
        path: 'version-backup',
        name: 'operations-version-backup',
        component: () => import('@/pages/VersionBackup.vue'),
        meta: { title: 'Backup de Versión' },
      },
      { path: 'logs', redirect: '/operations/health' },
    ],
  },

  // ── 7. INTEGRATIONS ──
  {
    path: '/integrations',
    name: 'integrations',
    component: () => import('@/pages/Connections.vue'),
    meta: { title: 'Integraciones' },
    children: [
      { path: '', redirect: { name: 'integrations-connections' } },
      {
        path: 'connections',
        name: 'integrations-connections',
        component: () => import('@/pages/Connections.vue'),
        meta: { title: 'Conexiones' },
      },
      {
        path: 'wallets',
        name: 'integrations-wallets',
        component: () => import('@/pages/Wallets.vue'),
        meta: { title: 'Billeteras' },
      },
      {
        path: 'accounts',
        name: 'integrations-accounts',
        component: () => import('@/pages/AccountsHub.vue'),
        meta: { title: 'Cuentas' },
      },
      {
        path: 'platforms',
        name: 'integrations-platforms',
        component: () => import('@/pages/ProgramCatalog.vue'),
        meta: { title: 'Plataformas / Programas' },
      },
      {
        path: 'sync',
        name: 'integrations-sync',
        component: () => import('@/pages/SyncCenter.vue'),
        meta: { title: 'Sync Center' },
      },
      {
        path: 'identity',
        name: 'integrations-identity',
        component: () => import('@/pages/Identity.vue'),
        meta: { title: 'Identidad' },
      },
    ],
  },

  // ── 8. COPILOT ──
  {
    path: '/copilot',
    name: 'copilot',
    component: () => import('@/pages/AgentCenter.vue'),
    meta: { title: 'Copilot' },
    children: [
      { path: '', redirect: { name: 'copilot-assistant' } },
      {
        path: 'assistant',
        name: 'copilot-assistant',
        component: () => import('@/pages/AgentCenter.vue'),
        meta: { title: 'Asistente' },
      },
      {
        path: 'memory',
        name: 'copilot-memory',
        component: () => import('@/pages/MemoryPatterns.vue'),
        meta: { title: 'Memoria / Patrones' },
      },
      {
        path: 'learning',
        name: 'copilot-learning',
        component: () => import('@/pages/PersonalIntelligence.vue'),
        meta: { title: 'Aprendizaje' },
      },
      {
        path: 'recommendations',
        name: 'copilot-recommendations',
        component: () => import('@/pages/InsightsView.vue'),
        meta: { title: 'Recomendaciones' },
      },
      {
        path: 'notifications',
        name: 'copilot-notifications',
        component: () => import('@/pages/NotificationsPage.vue'),
        meta: { title: 'Notificaciones' },
      },
    ],
  },

  // ── LEGACY REDIRECTS (mantener compatibilidad) ──
  // Revenue pages → Capital
  { path: '/revenue', redirect: '/capital' },
  { path: '/revenue-multiplier', redirect: '/capital' },
  { path: '/money-radar', redirect: '/capital?tab=targets' },
  { path: '/financial-truth', redirect: '/capital' },
  { path: '/finance-intel', redirect: '/capital' },

  // Findings/Reports legacy
  { path: '/findings', redirect: '/intelligence/findings' },
  { path: '/hypotheses', redirect: '/intelligence/hypotheses' },
  { path: '/evidence', redirect: '/intelligence/evidence' },
  { path: '/investigations', redirect: '/intelligence/investigations' },
  { path: '/confidence', redirect: '/intelligence/confidence' },
  { path: '/differential', redirect: '/intelligence/differential' },

  // Targets legacy
  { path: '/radar', redirect: '/targets/prioritization' },
  { path: '/hot-paths', redirect: '/targets/prioritization' },
  { path: '/attack-surface', redirect: '/targets/attack-surface' },
  { path: '/discovery', redirect: '/targets/discovery' },
  { path: '/opportunities', redirect: '/targets/prioritization' },
  { path: '/bounties', redirect: '/integrations/platforms' },
  { path: '/program-catalog', redirect: '/integrations/platforms' },

  // Reports legacy
  { path: '/report-queue', redirect: '/reports/queue' },
  { path: '/verify', redirect: '/reports/verification' },

  // Operations legacy
  { path: '/pipelines', redirect: '/operations/pipelines' },
  { path: '/actions', redirect: '/operations/scheduler' },
  { path: '/daily', redirect: '/operations/dashboard' },
  { path: '/next-action', redirect: '/operations/scheduler' },
  { path: '/tasks', redirect: '/operations/scheduler' },
  { path: '/project-dashboard', redirect: '/operations/dashboard' },
  { path: '/account-health', redirect: '/operations/health' },
  { path: '/health-center', redirect: '/operations/health' },
  { path: '/workflows', redirect: '/operations/workflows' },
  { path: '/replay', redirect: '/operations/replay' },

  // Integrations legacy
  { path: '/connections', redirect: '/integrations/connections' },
  { path: '/wallets', redirect: '/integrations/wallets' },
  { path: '/accounts-hub', redirect: '/integrations/accounts' },
  { path: '/sync-center', redirect: '/integrations/sync' },
  { path: '/identity', redirect: '/integrations/identity' },

  // Copilot legacy
  { path: '/agents', redirect: '/copilot/assistant' },
  { path: '/intelligence', redirect: '/intelligence' },
  { path: '/insights', redirect: '/copilot/recommendations' },
  { path: '/personal-intelligence', redirect: '/copilot/learning' },
  { path: '/memory-patterns', redirect: '/copilot/memory' },
  { path: '/notifications', redirect: '/copilot/notifications' },
  { path: '/truth-inspector', redirect: '/intelligence/confidence' },

  // Apps (mantener separadas - son micro-apps completas)
    {
      path: '/ownex/',
      name: 'ownex-home',
      component: () => import('@/shell/OrionHome.vue'),
      meta: { title: 'OWNEX OMEGA Platform' },
    },
  {
    path: '/investments',
    name: 'investment-hub',
    component: () => import('@/pages/InvestmentHub.vue'),
    meta: { title: 'Investment Hub' },
  },
  {
    path: '/atlas/',
    name: 'atlas-dashboard',
    component: () => import('@/apps/atlas/DashboardAtlas.vue'),
    meta: { title: 'ATLAS — Inversiones' },
  },
  {
    path: '/atlas/settings',
    name: 'atlas-settings',
    component: () => import('@/apps/atlas/SettingsAtlas.vue'),
    meta: { title: 'Configuración ATLAS' },
  },
  {
    path: '/odyssey/',
    name: 'odyssey-dashboard',
    component: () => import('@/apps/odyssey/DashboardOdyssey.vue'),
    meta: { title: 'ODYSSEY — Analítica' },
  },
  {
    path: '/odyssey/settings',
    name: 'odyssey-settings',
    component: () => import('@/apps/odyssey/SettingsOdyssey.vue'),
    meta: { title: 'Configuración ODYSSEY' },
  },
  {
    path: '/aegis/',
    name: 'aegis-dashboard',
    component: () => import('@/apps/aegis/DashboardAegis.vue'),
    meta: { title: 'AEGIS — Pentesting' },
  },
  {
    path: '/aegis/settings',
    name: 'aegis-settings',
    component: () => import('@/apps/aegis/SettingsAegis.vue'),
    meta: { title: 'Configuración AEGIS' },
  },
  {
    path: '/polymarket',
    name: 'polymarket-trading',
    component: () => import('@/pages/PolymarketTrading.vue'),
    meta: { title: 'Polymarket Trading' },
  },
  {
    path: '/trading',
    name: 'trading',
    component: () => import('@/pages/Trading.vue'),
    meta: { title: 'Trading' },
  },

  // ── Special pages ──
  {
    path: '/terminal',
    name: 'terminal',
    component: () => import('@/pages/TerminalView.vue'),
    meta: { title: 'Terminal' },
  },
  {
    path: '/baby-mode',
    name: 'baby-mode',
    component: () => import('@/pages/BabyMode.vue'),
    meta: { title: 'Baby Mode' },
  },
  {
    path: '/faqs',
    name: 'faqs',
    component: () => import('@/pages/FaqPage.vue'),
    meta: { title: 'Preguntas Frecuentes' },
  },

  // ── Catch-all ──
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('@/pages/NotFound.vue'),
    meta: { title: 'No Encontrado', public: true },
  },
]