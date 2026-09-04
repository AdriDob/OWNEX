import type { RouteLocationNormalized, RouteRecordRaw } from 'vue-router'
import { isSessionValid } from '@/lib/api'

// Pages that don't require auth
const publicPages = ['activation']

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
  // ── PERSONALIZATION WIZARD (público, para primer uso) ──
  {
    path: '/setup/personalization',
    name: 'personalization',
    component: () => import(/* webpackChunkName: "setup" */ '@/pages/PersonalizationWizard.vue'),
    meta: { title: 'Personalización', public: true },
  },
  {
    path: '/setup/enhanced',
    name: 'enhanced-personalization',
    component: () => import(/* webpackChunkName: "enhanced-setup" */ '@/pages/EnhancedPersonalizationWizard.vue'),
    meta: { title: 'Configuración Personalizada', public: true },
  },

  // ── MERLIN (Office Retro Modernized Assistant) ──
  {
    path: '/merlin',
    name: 'merlin',
    component: () => import(/* webpackChunkName: "merlin" */ '@/components/merlin/MerlinJarvis.vue'),
    meta: { title: 'MERLIN' },
  },
  {
    path: '/chat',
    name: 'ownex-chat',
    component: () => import(/* webpackChunkName: "ownex-chat" */ '@/components/ownex-chat/OwnexChat.vue'),
    meta: { title: 'MERLIN Chat' },
  },

  // ── AUTH ──
  {
    path: '/activation',
    name: 'activation',
    component: () => import(/* webpackChunkName: "auth" */ '@/pages/Activation.vue'),
    meta: { title: 'Activación', public: true },
  },
  {
    path: '/verify',
    name: 'verify-email',
    component: () => import(/* webpackChunkName: "auth" */ '@/pages/VerifyPage.vue'),
    meta: { title: 'Verificar Correo', public: true },
  },

  // ── 1. COMMAND CENTER ──
  {
    // 2026-08-30: '/' = OWNEX Command Center (IncomeHome).
    // Único entry point. Otros dashboards legacy redirigen aquí.
    path: '/',
    name: 'command-center',
    component: () => import(/* webpackChunkName: "command-center" */ '@/pages/IncomeHome.vue'),
    meta: { title: 'OWNEX Command Center' },
  },
  // Legacy redirects → Command Center
  { path: '/welcome', redirect: '/' },
  { path: '/dashboard', redirect: '/' },
  { path: '/classic', redirect: '/' },
  { path: '/home', redirect: '/' },

  // ── 2. INTELLIGENCE (Consolidated) ──
  {
    path: '/intelligence',
    name: 'intelligence',
    component: () => import(/* webpackChunkName: "intelligence" */ '@/pages/IntelligenceConsolidated.vue'),
    meta: { title: 'Inteligencia' },
  },
  {
    path: '/intelligence/evidence',
    name: 'intelligence-evidence',
    component: () => import(/* webpackChunkName: "intelligence" */ '@/pages/EvidenceCenter.vue'),
    meta: { title: 'Evidencia' },
  },
  {
    path: '/intelligence/investigations',
    name: 'intelligence-investigations',
    component: () => import(/* webpackChunkName: "intelligence" */ '@/pages/InvestigationsConsolidated.vue'),
    meta: { title: 'Investigaciones' },
  },
  // Legacy redirects
  { path: '/intelligence/findings', redirect: '/intelligence' },
  { path: '/intelligence/hypotheses', redirect: '/intelligence' },
  { path: '/intelligence/confidence', redirect: '/intelligence' },
  { path: '/intelligence/differential', redirect: '/intelligence' },

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

  // ── 4. REPORTS (Consolidated) ──
  {
    path: '/reports',
    name: 'reports',
    component: () => import(/* webpackChunkName: "reports" */ '@/pages/ReportsConsolidated.vue'),
    meta: { title: 'Reportes' },
  },
  {
    path: '/reports/:id',
    name: 'report-detail',
    component: () => import(/* webpackChunkName: "reports" */ '@/pages/ReportDetail.vue'),
    meta: { title: 'Editor de Reporte' },
  },
  {
    path: '/reports/verification',
    name: 'reports-verification',
    component: () => import(/* webpackChunkName: "reports" */ '@/pages/VerificationGuide.vue'),
    meta: { title: 'Guía de Validación' },
  },
  // Legacy redirects
  { path: '/reports/queue', redirect: '/reports' },
  { path: '/reports/center', redirect: '/reports' },
  { path: '/reports/history', redirect: '/reports' },

  // ── 5. CAPITAL ──
  {
    path: '/capital',
    name: 'capital',
    component: () => import('@/pages/Capital.vue'),
    meta: { title: 'Capital' },
    children: [
      {
        path: 'progressive-scaling',
        name: 'progressive-scaling',
        component: () => import('@/pages/ProgressiveScaling.vue'),
        meta: { title: 'Escalado Progresivo' },
      },
    ],
  },

  // ── 5.5 SECURITY (Consolidated) ──
  {
    path: '/security',
    name: 'security',
    component: () => import('@/pages/SecurityConsolidated.vue'),
    meta: { title: 'Security Cycle' },
  },
  // Legacy redirects
  { path: '/security/executive', redirect: '/security' },

  // ── 6. OPERATIONS (Consolidated) ──
  {
    path: '/operations',
    name: 'operations',
    component: () => import('@/pages/OperationsConsolidated.vue'),
    meta: { title: 'Operaciones' },
  },
  // Health & Settings separated for clarity
  {
    path: '/operations/health',
    name: 'operations-health',
    component: () => import('@/pages/OperationsConsolidated.vue'),
    meta: { title: 'Health' },
  },
  {
    path: '/operations/settings',
    name: 'operations-settings',
    component: () => import('@/pages/Settings.vue'),
    meta: { title: 'Configuración' },
  },
  // Non-consolidated operations routes (standalone)
  {
    path: '/operations/work-queue',
    name: 'work-queue',
    component: () => import('@/pages/WorkQueue.vue'),
    meta: { title: 'Cola de Trabajo' },
  },
  {
    path: '/operations/work-room/:id',
    name: 'work-room',
    component: () => import('@/components/work/WorkRoom.vue'),
    meta: { title: 'Work Room' },
  },
  {
    path: '/operations/worker',
    name: 'worker-control',
    component: () => import('@/pages/WorkerControl.vue'),
    meta: { title: 'WorkerCore Control' },
  },
  {
    path: '/operations/agenda',
    name: 'agenda',
    component: () => import('@/pages/AgendaView.vue'),
    meta: { title: 'Agenda' },
  },
  {
    path: '/operations/pipelines',
    name: 'operations-pipelines',
    component: () => import('@/pages/PipelineMonitor.vue'),
    meta: { title: 'Pipelines' },
  },
  {
    path: '/operations/pipelines/:id',
    name: 'pipeline-detail',
    component: () => import('@/pages/PipelineDetail.vue'),
    meta: { title: 'Detalle Pipeline' },
  },
  {
    path: '/operations/scheduler',
    name: 'operations-scheduler',
    component: () => import('@/pages/ActionsView.vue'),
    meta: { title: 'Scheduler / Acciones' },
  },
  {
    path: '/operations/tools',
    name: 'operations-tools',
    component: () => import('@/pages/OpportunityPlanner.vue'),
    meta: { title: 'Herramientas' },
  },
  {
    path: '/operations/settings',
    name: 'operations-settings',
    component: () => import('@/pages/Settings.vue'),
    meta: { title: 'Configuración' },
  },
  {
    path: '/operations/applications',
    name: 'operations-applications',
    component: () => import('@/pages/ApplicationAssistant.vue'),
    meta: { title: 'Application Assistant' },
  },
  {
    path: '/operations/workflows',
    name: 'operations-workflows',
    component: () => import('@/pages/Workflows.vue'),
    meta: { title: 'Workflows' },
  },
  {
    path: '/operations/replay',
    name: 'operations-replay',
    component: () => import('@/pages/ReplayCenter.vue'),
    meta: { title: 'Replay Center' },
  },
  {
    path: '/operations/version-backup',
    name: 'operations-version-backup',
    component: () => import('@/pages/VersionBackup.vue'),
    meta: { title: 'Backup de Versión' },
  },
  {
    path: '/operations/self-healer',
    name: 'operations-self-healer',
    component: () => import('@/pages/SelfHealer.vue'),
    meta: { title: 'Self-Healer' },
  },
  { path: '/operations/logs', redirect: '/operations' },

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
        path: 'outlook',
        name: 'integrations-outlook',
        component: () => import('@/pages/OutlookCalendar.vue'),
        meta: { title: 'Outlook Calendar' },
      },
      {
        path: 'identity',
        name: 'integrations-identity',
        component: () => import('@/pages/Identity.vue'),
        meta: { title: 'Identidad' },
      },
    ],
  },

  // ── 8. COPILOT (Consolidated) ──
  {
    path: '/copilot',
    name: 'copilot',
    component: () => import('@/pages/CopilotConsolidated.vue'),
    meta: { title: 'Copilot' },
  },
  {
    path: '/copilot/computer-use',
    name: 'copilot-computer-use',
    component: () => import('@/pages/ComputerUse.vue'),
    meta: { title: 'Computer Use' },
  },
  {
    path: '/copilot/notifications',
    name: 'copilot-notifications',
    component: () => import('@/pages/NotificationsPage.vue'),
    meta: { title: 'Notificaciones' },
  },
  // Legacy redirects
  { path: '/copilot/assistant', redirect: '/copilot' },
  { path: '/copilot/memory', redirect: '/copilot' },
  { path: '/copilot/learning', redirect: '/copilot' },
  { path: '/copilot/recommendations', redirect: '/copilot' },

  // ── LEGACY REDIRECTS REMOVED (UX Consolidation 2026-09-04) ──
  // All legacy redirects removed to simplify navigation.
  // Use canonical routes: /, /intelligence, /reports, /capital, /operations, /integrations, /copilot

  // ── APPS SATELITE (consolidated in sidebar, accessible but not main flow) ──
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
    path: '/trading',
    name: 'trading',
    component: () => import('@/pages/TradingConsolidated.vue'),
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
  {
    path: '/profile-kit',
    name: 'profile-kit',
    component: () => import('@/pages/ProfileConsolidated.vue'),
    meta: { title: 'Profile' },
  },
  {
    path: '/knowledge',
    name: 'knowledge',
    component: () => import(/* webpackChunkName: "knowledge" */ '@/pages/Knowledge.vue'),
    meta: { title: 'Knowledge Vault' },
  },
  {
    path: '/knowledge/graph',
    name: 'knowledge-graph',
    component: () => import(/* webpackChunkName: "knowledge-graph" */ '@/components/knowledge-graph/KnowledgeGraphExplorer.vue'),
    meta: { title: 'Knowledge Graph Explorer' },
  },
  {
    path: '/quick-capture',
    name: 'quick-capture',
    component: () => import(/* webpackChunkName: "quick-capture" */ '@/pages/QuickCapture.vue'),
    meta: { title: 'Quick Capture' },
  },

  // ── Catch-all ──
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('@/pages/NotFound.vue'),
    meta: { title: 'No Encontrado', public: true },
  },
]
