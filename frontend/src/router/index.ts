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

export const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/pages/LoginPage.vue'),
    meta: { title: 'Iniciar Sesión', public: true },
  },
  {
    path: '/',
    name: 'home',
    component: () => import('@/pages/Dashboard.vue'),
    meta: { title: 'Centro de Inteligencia CATEYE' },
  },
  {
    path: '/mission-control',
    name: 'mission-control',
    component: () => import('@/pages/MissionControl.vue'),
    meta: { title: 'Control de Misión' },
  },
  {
    path: '/radar',
    name: 'radar',
    component: () => import('@/pages/OpportunityRadar.vue'),
    meta: { title: 'Radar de Oportunidades' },
  },
  {
    path: '/hot-paths',
    name: 'hot-paths',
    component: () => import('@/pages/HotPaths.vue'),
    meta: { title: 'Rutas Críticas' },
  },
  {
    path: '/findings',
    name: 'findings',
    component: () => import('@/pages/Findings.vue'),
    meta: { title: 'Pipeline de Hallazgos' },
  },
  {
    path: '/reports',
    name: 'reports',
    component: () => import('@/pages/ReportCenter.vue'),
    meta: { title: 'Centro de Reportes' },
  },
  {
    path: '/settings',
    name: 'settings',
    component: () => import('@/pages/Settings.vue'),
    meta: { title: 'Configuración' },
  },
  {
    path: '/money-radar',
    name: 'money-radar',
    component: () => import('@/pages/MoneyRadar.vue'),
    meta: { title: 'Money Radar' },
  },
  {
    path: '/programs/:id',
    name: 'program-intel',
    component: () => import('@/pages/ProgramIntel.vue'),
    meta: { title: 'Inteligencia de Programa' },
  },
  {
    path: '/programs/:id/plan',
    name: 'opportunity-planner',
    component: () => import('@/pages/OpportunityPlanner.vue'),
    meta: { title: 'Plan de Cacería' },
  },
  {
    path: '/verify',
    name: 'verification-guide',
    component: () => import('@/pages/VerificationGuide.vue'),
    meta: { title: 'Guía de Validación' },
  },
  {
    path: '/report-queue',
    name: 'report-queue',
    component: () => import('@/pages/ReportQueue.vue'),
    meta: { title: 'Cola Priorizada' },
  },
  {
    path: '/memory-patterns',
    name: 'memory-patterns',
    component: () => import('@/pages/MemoryPatterns.vue'),
    meta: { title: 'Patrones Aprendidos' },
  },
  {
    path: '/connections',
    name: 'connections',
    component: () => import('@/pages/Connections.vue'),
    meta: { title: 'Conexiones' },
  },
  {
    path: '/agents',
    name: 'agent-center',
    component: () => import('@/pages/AgentCenter.vue'),
    meta: { title: 'Centro de Agentes' },
  },
  {
    path: '/pipelines',
    name: 'pipeline-monitor',
    component: () => import('@/pages/PipelineMonitor.vue'),
    meta: { title: 'Monitor de Pipelines' },
  },
  {
    path: '/evidence',
    name: 'evidence-center',
    component: () => import('@/pages/EvidenceCenter.vue'),
    meta: { title: 'Centro de Evidencia' },
  },
  {
    path: '/confidence',
    name: 'confidence-dashboard',
    component: () => import('@/pages/ConfidenceDashboard.vue'),
    meta: { title: 'Confianza' },
  },
  {
    path: '/history',
    name: 'history-view',
    component: () => import('@/pages/HistoryView.vue'),
    meta: { title: 'Historial' },
  },
  {
    path: '/daily',
    name: 'daily-mode',
    component: () => import('@/pages/DailyMode.vue'),
    meta: { title: 'Hoy' },
  },
  {
    path: '/actions',
    name: 'actions-view',
    component: () => import('@/pages/ActionsView.vue'),
    meta: { title: 'Acciones' },
  },
  {
    path: '/intelligence',
    name: 'intelligence-dashboard',
    component: () => import('@/pages/IntelligenceDashboard.vue'),
    meta: { title: 'Inteligencia Adaptativa' },
  },
  {
    path: '/attack-surface',
    name: 'attack-surface',
    component: () => import('@/pages/AttackSurface.vue'),
    meta: { title: 'Superficie de Ataque' },
  },
  {
    path: '/opportunities',
    name: 'opportunities',
    component: () => import('@/pages/Opportunities.vue'),
    meta: { title: 'Oportunidades' },
  },
  {
    path: '/bounties',
    name: 'bounties',
    component: () => import('@/pages/Bounties.vue'),
    meta: { title: 'Bounties' },
  },
  {
    path: '/discovery',
    name: 'discovery',
    component: () => import('@/pages/Discovery.vue'),
    meta: { title: 'Program Discovery' },
  },
  {
    path: '/next-action',
    name: 'next-action',
    component: () => import('@/pages/NextAction.vue'),
    meta: { title: 'Próxima Acción' },
  },
  {
    path: '/investigations',
    name: 'investigations',
    component: () => import('@/pages/InvestigationCenter.vue'),
    meta: { title: 'Investigaciones' },
  },
  {
    path: '/investigations/:id',
    name: 'investigation-detail',
    component: () => import('@/pages/InvestigationDetail.vue'),
    meta: { title: 'Detalle de Investigación' },
  },
  {
    path: '/hypotheses',
    name: 'hypothesis-queue',
    component: () => import('@/pages/HypothesisQueue.vue'),
    meta: { title: 'Hipótesis' },
  },
  {
    path: '/differential',
    name: 'differential-engine',
    component: () => import('@/pages/DifferentialEngine.vue'),
    meta: { title: 'Análisis Diferencial' },
  },
  {
    path: '/insights',
    name: 'insights-view',
    component: () => import('@/pages/InsightsView.vue'),
    meta: { title: 'Insights del Sistema' },
  },
  {
    path: '/wallets',
    name: 'wallets',
    component: () => import('@/pages/Wallets.vue'),
    meta: { title: 'Billeteras' },
  },
  {
    path: '/financial-truth',
    name: 'financial-truth',
    component: () => import('@/pages/FinancialTruth.vue'),
    meta: { title: 'Financial Truth' },
  },
  {
    path: '/accounts-hub',
    name: 'accounts-hub',
    component: () => import('@/pages/AccountsHub.vue'),
    meta: { title: 'Accounts Hub' },
  },
  {
    path: '/sync-center',
    name: 'sync-center',
    component: () => import('@/pages/SyncCenter.vue'),
    meta: { title: 'Sync Center' },
  },
  {
    path: '/account-health',
    name: 'account-health',
    component: () => import('@/pages/AccountHealth.vue'),
    meta: { title: 'Account Health' },
  },
  {
    path: '/truth-inspector',
    name: 'truth-inspector',
    component: () => import('@/pages/TruthInspector.vue'),
    meta: { title: 'Truth Inspector' },
  },
  {
    path: '/identity',
    name: 'identity',
    component: () => import('@/pages/Identity.vue'),
    meta: { title: 'Identidad' },
  },
  {
    path: '/operations',
    name: 'operations-dashboard',
    component: () => import('@/pages/OperationsDashboard.vue'),
    meta: { title: 'Panel de Operaciones' },
  },
  {
    path: '/tasks',
    name: 'task-queue',
    component: () => import('@/pages/TaskQueue.vue'),
    meta: { title: 'Tareas' },
  },
  {
    path: '/program-catalog',
    name: 'program-catalog',
    component: () => import('@/pages/ProgramCatalog.vue'),
    meta: { title: 'Catálogo de Programas' },
  },
  {
    path: '/replay',
    name: 'replay-center',
    component: () => import('@/pages/ReplayCenter.vue'),
    meta: { title: 'Reproducir' },
  },
  {
    path: '/personal-intelligence',
    name: 'personal-intelligence',
    component: () => import('@/pages/PersonalIntelligence.vue'),
    meta: { title: 'Perfil de Aprendizaje' },
  },
  {
    path: '/screenshots',
    name: 'screenshot-center',
    component: () => import('@/pages/ScreenshotCenter.vue'),
    meta: { title: 'Capturas' },
  },
  {
    path: '/project-dashboard',
    name: 'project-dashboard',
    component: () => import('@/pages/ProjectDashboard.vue'),
    meta: { title: 'Proyecto' },
  },
  {
    path: '/report-history',
    name: 'report-history',
    component: () => import('@/pages/ReportHistory.vue'),
    meta: { title: 'Historial de Reportes' },
  },
  {
    path: '/targets/:id',
    name: 'target-detail',
    component: () => import('@/pages/TargetDetail.vue'),
    meta: { title: 'Detalle de Target' },
  },
  {
    path: '/endpoints/:id',
    name: 'endpoint-detail',
    component: () => import('@/pages/EndpointDetail.vue'),
    meta: { title: 'Detalle de Endpoint' },
  },
  {
    path: '/findings/:id',
    name: 'finding-detail',
    component: () => import('@/pages/FindingDetail.vue'),
    meta: { title: 'Detalle de Hallazgo' },
  },
  {
    path: '/reports/:id',
    name: 'report-detail',
    component: () => import('@/pages/ReportDetail.vue'),
    meta: { title: 'Editor de Reporte' },
  },
  {
    path: '/pipelines/:id',
    name: 'pipeline-detail',
    component: () => import('@/pages/PipelineDetail.vue'),
    meta: { title: 'Detalle de Pipeline' },
  },
  {
    path: '/activation',
    name: 'activation',
    component: () => import('@/pages/Activation.vue'),
    meta: { title: 'Activación', public: true },
  },
  {
    path: '/faqs',
    name: 'faqs',
    component: () => import('@/pages/FaqPage.vue'),
    meta: { title: 'Preguntas Frecuentes' },
  },
  // ── ORION Platform ──
  {
    path: '/orion/',
    name: 'orion-home',
    component: () => import('@/shell/OrionHome.vue'),
    meta: { title: 'ORION Platform' },
  },
  // ── ATLAS (Inversiones) ──
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
  // ── ODYSSEY (Analítica de Apuestas) ──
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
  // ── Notification / Sync pages ──
  {
    path: '/notifications',
    name: 'notifications',
    component: () => import('@/pages/NotificationsPage.vue'),
    meta: { title: 'Notificaciones' },
  },
  // ── Catch-all ──
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('@/pages/NotFound.vue'),
    meta: { title: 'No Encontrado', public: true },
  },
]
