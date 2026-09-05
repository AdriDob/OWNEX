import { api } from '@/lib/api'

// ── Types ──

export interface ThroughputStage {
  label: string
  value: number
  color: string
}

export interface AgentStatus {
  name: string
  status: 'online' | 'offline' | 'limited' | 'local'
  description: string
}

export interface OpportunityItem {
  id: string
  title: string
  source: string
  type: string
  reward: number
  confidence: number
  effort: string
  action: string
}

export interface NextActionItem {
  title: string
  reason: string
  effort: string
  estimatedReward: number
}

export interface KnowledgeItem {
  id: string
  type: 'pattern' | 'decision' | 'learning' | 'alert'
  typeLabel: string
  message: string
  timestamp: string
}

export interface RevenueSnapshotData {
  usdPerHour: number
  monthlyTotal: number
  pendingTotal: number
  bestPlatform: string
}

export interface WorkCycleData {
  id: string
  name: string
  icon: string
  color: string
  description: string
  status: 'active' | 'monitoring' | 'available' | 'tracking'
  statusLabel: string
  route: string
  badge: string
  badgeColor: string
}

export interface OwnexDashboardData {
  throughputStages: ThroughputStage[]
  throughputEfficiency: number
  agents: AgentStatus[]
  opportunities: OpportunityItem[]
  nextAction: NextActionItem | null
  knowledgeFeed: KnowledgeItem[]
  revenue: RevenueSnapshotData | null
  cycles: WorkCycleData[]
  systemHealth: number
  systemStatus: string
  pendingApprovals: number
  timestamp: string
}

// ── Backend response shapes ──

interface OverviewResponse {
  target_count: number
  endpoint_count: number
  finding_count: number
  confirmed_verdicts: number
  active_scans: number
  pipeline_stages?: {
    detected?: number
    validated?: number
    confirmed?: number
    reported?: number
  }
}

interface ActivityEvent {
  id: string
  type: string
  message: string
  timestamp: string
  severity?: string
}

interface RevenueSummaryResponse {
  success: boolean
  total_payout?: number
  monthly_payout?: number
  pending_total?: number
  best_platform?: string
  usd_per_hour?: number
}

const DEFAULT_STAGES = [
  { label: 'Oportunidades detectadas', value: 0, color: 'text-accent' },
  { label: 'Analizadas', value: 0, color: 'text-primary' },
  { label: 'Priorizadas', value: 0, color: 'text-warning' },
  { label: 'En ejecución', value: 0, color: 'text-primary' },
  { label: 'Completadas', value: 0, color: 'text-success' },
]

const DEFAULT_REVENUE: RevenueSnapshotData = {
  usdPerHour: 0,
  monthlyTotal: 0,
  pendingTotal: 0,
  bestPlatform: '—',
}

// ── Fetchers ──

async function fetchOverview(): Promise<ThroughputStage[]> {
  const data = await api.get<OverviewResponse>('/overview')
    const stages = [...DEFAULT_STAGES]
    if (data.pipeline_stages) {
      stages[0].value = data.pipeline_stages.detected ?? data.target_count ?? 0
      stages[1].value = data.pipeline_stages.validated ?? data.finding_count ?? 0
      stages[2].value = data.pipeline_stages.confirmed ?? data.confirmed_verdicts ?? 0
      stages[3].value = data.active_scans ?? 0
      stages[4].value = data.pipeline_stages.reported ?? 0
    } else {
      stages[0].value = data.target_count ?? 0
      stages[1].value = data.endpoint_count ?? 0
      stages[2].value = data.finding_count ?? 0
      stages[3].value = data.active_scans ?? 0
      stages[4].value = data.confirmed_verdicts ?? 0
    }
  return stages
}

interface OpportunityScoreItem {
  id: string
  name: string
  cycle: string
  source_type: string
  source_name: string
  reward: number
  effort_hours: number
  platform: string
  url: string | null
  score: {
    overall: number
    expected_value: number
    acceptance_probability: number
    speed_days: number
    difficulty: number
    competition: number
    personal_fit: number
    confidence: number
    reasoning: string[]
  }
}

interface Top5Response {
  generated_at: string
  total_scored: number
  diversification_note: string
  summary: string
  top5: OpportunityScoreItem[]
}

async function fetchOpportunities(): Promise<OpportunityItem[]> {
    const data = await api.get<Top5Response>('/opportunity-score/top5')
    const list = data.top5 || []
    return list.map((item) => ({
      id: item.id,
      title: item.name,
      source: item.source_name,
      type: item.cycle,
      reward: item.reward,
      confidence: Math.round((item.score.confidence ?? 0) * 100),
      effort: item.effort_hours < 2 ? 'Bajo' : item.effort_hours < 5 ? 'Medio' : 'Alto',
      action: item.score.overall > 0.7 ? 'Analizar' : item.score.overall > 0.5 ? 'Evaluar' : 'Revisar',
    }))
}

async function fetchActivity(): Promise<KnowledgeItem[]> {
    const data = await api.get<any>('/activity', { hours: 24 })
    const events = data?.events || data?.items || []
    return events.slice(0, 5).map((e: any) => ({
      id: String(e.id || Math.random()),
      type: e.severity === 'high' ? 'alert' : e.type === 'decision' ? 'decision' : e.type === 'pattern' ? 'pattern' : 'learning',
      typeLabel: e.severity === 'high' ? 'Evento' : e.type === 'decision' ? 'Decisión' : e.type === 'pattern' ? 'Patrón' : 'Actividad',
      message: e.title || e.message || `${e.type}: #${e.id}`,
      timestamp: e.timestamp || new Date().toISOString(),
    }))
}

export async function fetchMissionStatus(): Promise<{ health: number; status: string; nextAction: NextActionItem | null; timestamp: string }> {
    const data = await api.get<any>('/mission/status')
    const nextAction = data.next_action
      ? {
          title: data.next_action.title || 'Sin acción pendiente',
          reason: data.next_action.why_now || '',
          effort: data.next_action.effort || 'Bajo',
          estimatedReward: data.next_action.estimated_reward || 0,
        }
      : null
    return {
      health: data.system?.health_score ?? 0,
      status: data.system?.status ?? 'unknown',
      nextAction,
      timestamp: data.system?.timestamp ?? new Date().toISOString(),
    }
}

/** Income Plan combinado (backend: cores/direct_work_engine/income_plan.py).
 *  Fase 2 visual (2026-08-25): alimenta el Next Action real de Mission Control. */
export interface IncomePayoffRange {
  low: number
  high: number
}
export interface IncomePlanAction {
  source: 'workbank' | 'first_day' | 'applications'
  title: string
  detail?: string
  why?: string
  url?: string | null
  human_hours?: number | null
  ev_per_human_hour_usd?: number | null
  payoff_range?: IncomePayoffRange | null
  cash_speed_days?: number | null
  zero_experience?: boolean
  assessment_required?: boolean
  access_probability?: string
  // New honest-economics fields (backend returns these but UI wasn't rendering)
  expected_cash?: { date: string | null; confidence: string; note: string } | null
  htroi?: number | null
  confidence_band?: string | null
}
export interface IncomePlanState {
  generated_at?: string
  philosophy: string
  next_action: IncomePlanAction | null
  phases: { now: IncomePlanAction[]; this_week: IncomePlanAction[]; waiting: Array<{ key: string; name: string; status: string }> }
  tracks: {
    active: { label: string; first_day_progress_pct: number; workbank_ready_to_deliver: number }
    passive: { label: string; progress_pct: number; by_status: Record<string, number>; accepted_streams?: string[] }
  }
}

export async function fetchIncomePlan(): Promise<IncomePlanState> {
  return api.get<IncomePlanState>('/applications/income-plan')
}

// ── Platform Operations (onboarding + ranking) ──

export interface OnboardingStep {
  id: string
  title: string
  detail: string
  done: boolean
  est_minutes: number
  human_required: boolean
}

export interface PlatformOnboarding {
  platform: string
  name: string
  url: string
  status: string
  readiness_pct: number
  total_steps: number
  completed_steps: number
  checklist: OnboardingStep[]
  next_action: { step_id: string; title: string; detail: string; est_minutes: number; url: string } | null
  payment_ready: boolean
  pay_range: string
  payout: string
  why: string
}

export interface PlatformRankingItem {
  platform: string
  name: string
  readiness_pct: number
  documented_rate_usd_h: number | null
  effective_rate_usd_h: number | null
  status: string
  next_action: { step_id: string; title: string; detail: string; est_minutes: number; url: string } | null
  recommendation: 'WORK_HERE' | 'FINISH_SETUP' | 'START_ONBOARDING' | 'ACTIVE_STREAM'
}

export async function fetchPlatformOnboarding(platform: string): Promise<PlatformOnboarding> {
  return api.get<PlatformOnboarding>(`/applications/${platform}/onboarding`)
}

export async function fetchAllOnboarding(): Promise<{ platforms: PlatformOnboarding[]; count: number }> {
  return api.get<{ platforms: PlatformOnboarding[]; count: number }>('/applications/onboarding/all')
}

export async function fetchPlatformRanking(): Promise<{ ranking: PlatformRankingItem[]; top_recommendation: PlatformRankingItem | null; count: number }> {
  return api.get<{ ranking: PlatformRankingItem[]; top_recommendation: PlatformRankingItem | null; count: number }>('/applications/platform-ranking')
}

async function fetchSystemStatus(): Promise<AgentStatus[]> {
  // Honest mapping: no hardcoded fallback fleet — backend down must be
  // visible, and an empty service list renders as empty state.
  const data = await api.get<any>('/system/state')
  const services = data?.services || []
  return services.map((s: any) => ({
    name: s.name || s.id || 'Servicio',
    status: s.status === 'healthy' ? 'online' : s.status === 'degraded' ? 'limited' : 'offline',
    description: s.description || s.type || '',
  }))
}

async function fetchRevenueSnapshot(): Promise<RevenueSnapshotData | null> {
    const data = await api.get<RevenueSummaryResponse>('/economic/financial-summary')
    return {
      usdPerHour: data.usd_per_hour ?? 0,
      monthlyTotal: data.monthly_payout ?? 0,
      pendingTotal: data.pending_total ?? 0,
      bestPlatform: data.best_platform ?? '—',
    }
}

// ── Cycle fetchers ──

interface CycleApiResponse {
  cycles: Array<{
    id: number
    name: string
    slug: string
    description: string
    category: string
    status: string
    enabled: boolean
    priority: number
    config: Record<string, any>
    created_at: string
    updated_at: string
  }>
  total: number
}

interface CycleMetricsApiResponse {
  [slug: string]: {
    cycle_id: number
    slug: string
    name: string
    category: string
    status: string
    metrics: {
      opportunities_found: number
      tasks_active: number
      tasks_completed: number
      estimated_value: number
      success_rate: number
      last_execution: string | null
      next_action: string | null
      throughput_score: number
    }
  }
}

export async function fetchCycles(): Promise<WorkCycleData[]> {
  try {
    const data = await api.get<CycleApiResponse>('/cycles')
    const metricsData = await api.get<CycleMetricsApiResponse>('/cycles/metrics').catch(() => ({})) as CycleMetricsApiResponse

    const statusMap: Record<string, WorkCycleData['status']> = {
      running: 'active',
      idle: 'available',
      paused: 'monitoring',
      error: 'monitoring',
      completed: 'tracking',
      inactive: 'available',
    }

    const statusLabelMap: Record<string, string> = {
      running: 'Activo',
      idle: 'Disponible',
      paused: 'Pausado',
      error: 'Error',
      completed: 'Completado',
      inactive: 'Inactivo',
    }

    const iconMap: Record<string, string> = {
      security: 'Shield',
      forge: 'Globe',
      pulse: 'Bot',
      vault: 'DollarSign',
      atlas: 'Compass',
    }

    const colorMap: Record<string, string> = {
      security: 'text-primary',
      forge: 'text-intigriti',
      pulse: 'text-success',
      vault: 'text-warning',
      atlas: 'text-muted-foreground',
    }

    const badgeColorMap: Record<string, string> = {
      security: 'bg-primary/20 text-primary',
      forge: 'bg-intigriti/20 text-intigriti',
      pulse: 'bg-success/20 text-success',
      vault: 'bg-warning/20 text-warning',
      atlas: 'bg-muted/20 text-muted-foreground',
    }

    const routeMap: Record<string, string> = {
      security: '/targets',
      forge: '/integrations/platforms',
      pulse: '/pulse',
      vault: '/capital',
      atlas: '/copilot/memory',
    }

    const badgeMap: Record<string, string> = {
      security: 'Bug Bounty',
      forge: 'Dev',
      pulse: 'AI',
      vault: 'Finanzas',
      atlas: 'Intel',
    }

    return data.cycles.map((cycle) => {
      const metrics = metricsData[cycle.slug]?.metrics
      const status = statusMap[cycle.status] || 'available'
      const nextAction = metrics?.next_action || '—'

      return {
        id: cycle.slug,
        name: cycle.name,
        icon: iconMap[cycle.category] || 'Shield',
        color: colorMap[cycle.category] || 'text-primary',
        description: cycle.description || nextAction,
        status,
        statusLabel: statusLabelMap[cycle.status] || 'Disponible',
        route: routeMap[cycle.slug] || '',
        badge: badgeMap[cycle.slug] || cycle.category,
        badgeColor: badgeColorMap[cycle.slug] || 'bg-primary/20 text-primary',
      }
    })
  } catch {
    return []
  }
}

async function fetchApprovals(): Promise<number> {
  try {
    const data = await api.get<{ count: number }>('/capability-expansion/approvals')
    return data.count ?? 0
  } catch {
    return 0
  }
}

// ── Main fetch ──

export async function fetchOwnexDashboard(): Promise<OwnexDashboardData> {
  const [stages, opportunities, activity, mission, agents, revenue, cycles, pendingApprovals] = await Promise.all([
    fetchOverview(),
    fetchOpportunities(),
    fetchActivity(),
    fetchMissionStatus(),
    fetchSystemStatus(),
    fetchRevenueSnapshot(),
    fetchCycles(),
    fetchApprovals(),
  ])

  const completedCount = stages.length > 0 ? stages[stages.length - 1].value : 0
  const totalInput = stages.length > 0 ? stages[0].value : 1
  const efficiency = totalInput > 0 ? Math.round((completedCount / totalInput) * 100) : 0

  return {
    throughputStages: stages,
    throughputEfficiency: Math.min(efficiency, 100),
    agents,
    opportunities,
    nextAction: mission.nextAction,
    knowledgeFeed: activity,
    revenue,
    cycles,
    systemHealth: mission.health,
    systemStatus: mission.status,
    pendingApprovals,
    timestamp: mission.timestamp,
  }
}

// ── Direct Work Engine ──

export interface DirectWorkOpportunity {
  id: string
  title: string
  platform: string
  category: string
  payment: number
  remote: boolean
  employment_type: string
}

export interface DirectWorkRanked {
  rank: number
  opportunity: DirectWorkOpportunity
  expected_value: number
  acceptance_probability: number
  overall_recommendation_score: number
  strategy: string | null
  recommendation_reasoning: string[]
  zero_barrier_score: {
    total: number
    barrier_level: string
    enablers: string[]
    blockers: string[]
   }
   payout_method: string
   payout_method_rationale: string
   payment_compat_score: number
   payment_compat_notes: string[]
 }
 
 export interface DirectWorkRecommendResponse {
  ranked: DirectWorkRanked[]
}

export function buildDirectWorkProfile(): Record<string, unknown> {
  return {
    name: 'Adriel',
    country: 'Argentina',
    languages: ['es', 'en'],
    skills: ['python', 'go', 'unity', 'typescript'],
    experience_level: 'none',
    remote_only: true,
    accepts_ai_tools: true,
  }
}

export async function fetchDirectWorkRecommendations(
  opportunities: Record<string, unknown>[] = [],
): Promise<DirectWorkRanked[]> {
  const data = await api.post<DirectWorkRecommendResponse>('/direct-work/recommend', {
    profile: buildDirectWorkProfile(),
    opportunities,
    limit: 5,
  })
  return data.ranked
}

// ── Work Bank ──

export interface WorkBankTarget {
  target: number
  achieved: number
  ready_total: number
  pct: number
}

export interface WorkBankItem {
  id: string
  title: string
  platform: string
  category: string
  reward: number
  barrier_score: number
  employment_type: string
  status: string
  access_status: string
  access_requirement: string
  deliverables: string[]
  created_at: string
  ready_to_deliver: boolean
  payout_method: string
  payout_method_rationale: string
}

export interface WorkBankState {
  store_path: string
  scanned: number
  eligible_zero_barrier: number
  new_items_added: number
  total_in_bank: number
  ready_to_deliver: number
  needs_access: number
  delivered: number
  targets: {
    daily: WorkBankTarget
    weekly: WorkBankTarget
    monthly: WorkBankTarget
  }
  weekly_best: WorkBankItem[]
  items: WorkBankItem[]
}

export interface DailyBriefSource {
  name: string
  url: string
  category: string
  trust_score: number
  earning_potential: string
  average_reward: string
}

export interface DailyBrief {
  generated_at: string
  scanned: number
  summary: string
  top_opportunity: DirectWorkRanked | null
  ranked: DirectWorkRanked[]
  learning: {
    missing_skills: string[]
    plan: Array<{ skill: string; resource: string; estimated_hours: number }>
  } | null
  best_sources?: DailyBriefSource[]
}

export async function fetchDirectWorkWorkBank(): Promise<WorkBankState> {
  return api.get<WorkBankState>('/direct-work/workbank')
}

export async function runDirectWorkCycle(target: number = 10): Promise<WorkBankState> {
  const summary = await api.post<{ scanned: number; new_items_added: number; ready_to_deliver: number; needs_access: number }>(
    '/direct-work/workbank/cycle',
    { target },
  )
  const state = await fetchDirectWorkWorkBank()
  return { ...state, ...summary }
}

export async function fetchDirectWorkDailyBrief(limit: number = 5): Promise<DailyBrief> {
  return api.post<DailyBrief>('/direct-work/daily-brief', { profile: buildDirectWorkProfile(), limit })
}

// ── Assisted delivery ──

export interface DeliveryPackage {
  item_id: string
  platform: string
  title: string
  ready_to_deliver: boolean
  need_user_action: string
  package_path: string
  files: string[]
  submission_url: string | null
  guide_url: string | null
  deliverables: string[]
}

export interface DeliverableItem {
  id: string
  title: string
  platform: string
  reward: number
  deliverables: string[]
  url: string
  payout_method: string
  payout_method_rationale: string
}

export async function fetchDeliveryQueue(): Promise<{ count: number; items: DeliverableItem[] }> {
  return api.get<{ count: number; items: DeliverableItem[] }>('/direct-work/deliver/pending')
}

// ── Daily Operation Mode (GOOD MORNING) ──

export interface GoodMorningState {
  generated_at: string
  summary: string
  system: { status: string; score: number }
  memory: { healthy: boolean; entries: number; namespaces: Record<string, number>; namespace_count: number }
  important_tasks: Array<{ title: string; platform: string; reward?: number; requirement?: string }>
  opportunities: {
    scanned_sources: number
    best_sources: Array<{ name: string; category: string; trust_score: number; earning_potential: string }>
  }
  unfinished_work: {
    ready_to_deliver: Array<{ title: string; platform: string; reward: number }>
    needs_access: Array<{ title: string; platform: string; requirement: string }>
    targets: Record<string, unknown>
  }
  improvements_suggested: Array<{ type: string; name: string; benefit: string; priority: string }>
  pending_approvals: Array<{ id: string; message: string; level?: string }>
  setup_progress: {
    complete_pct: number
    complete: boolean
    next_task: {
      id: string
      phase_label: string
      title: string
      why: string
      est_minutes: number
      how_to: string
    } | null
  }
}

export async function fetchGoodMorning(): Promise<GoodMorningState> {
  return api.get<GoodMorningState>('/system/good-morning')
}

// ── Global Radar (Platform Analysis System) ──

export interface PlatformAnalysisCard {
  name: string
  url: string
  category: string
  source_type: string
  country_availability: string
  argentina_compatibility: string
  argentina_reason: string
  payment_method: string
  average_reward: string
  entry_barrier: string
  interview_required: boolean
  portfolio_required: boolean
  experience_required: boolean
  task_transparency: number
  trust_score: number
  earning_potential: string
  recommendation: string
  priority: number
}

export interface SourceIntelResponse {
  analyzed: number
  total_curated_sources: number
  stats: {
    by_category: Record<string, number>
    by_recommendation: Record<string, number>
    argentina_compatible: number
    avg_trust_score: number
  }
  uncovered_categories: string[]
  sources: PlatformAnalysisCard[]
}

export async function fetchSourceIntel(options?: {
  categories?: string[]
  query?: string
  min_trust?: number
}): Promise<SourceIntelResponse> {
  return api.post<SourceIntelResponse>('/direct-work/source-intel', options ?? {})
}



// ── Income Projector ──

export interface IncomeProjectionRequest {
  work_income_usd_per_month: number
  savings_usd_per_month: number
  start_capital_usd: number
  annual_return_rate: number
  target_monthly_usd: number
}

export interface IncomeProjectionResult {
  months_to_target: number
  final_capital: number
  monthly_progression: Array<{ month: number; capital: number; income: number }>
  recommendations: string[]
}

export async function projectIncome(payload: IncomeProjectionRequest): Promise<IncomeProjectionResult> {
  return api.post<IncomeProjectionResult>('/direct-work/income-projector', payload)
}

// ── Payment Compatibility ──

export interface PaymentAccount {
  id: string
  name: string
  layer: string
  function: string
  regions: string[]
  currencies: string[]
  methods: string[]
  networks: string[]
  kyc_required: boolean
  withdrawal_available: boolean
  notes: string[]
  payout_ref: string | null
}

export interface PaymentVerdict {
  compatible: boolean
  viable: boolean
  score: number
  requirement: Record<string, unknown>
  matches: Array<{ account_id: string; account_name: string; layer: string; function: string; reason: string; score: number }>
  off_ramp: Array<{ account_id: string; account_name: string; layer: string; function: string; reason: string; score: number }>
  missing: string[]
  honest_notes: string[]
}

export interface PaymentNetworkResponse {
  summary: {
    total_accounts: number
    by_layer: Record<string, string[]>
    by_function: Record<string, string[]>
    by_region: Record<string, string[]>
  }
  accounts: PaymentAccount[]
}

export interface PaymentEvaluateRequest {
  method: string
  currency: string
  region: string
  amount?: number
  required_documentation?: string
  platform?: string
  final_currency?: string
}

export async function fetchPaymentNetwork(): Promise<PaymentNetworkResponse> {
  return api.get<PaymentNetworkResponse>('/payment-compat')
}

export async function evaluatePayment(
  payload: PaymentEvaluateRequest,
  chain: boolean = false,
): Promise<PaymentVerdict> {
  const path = chain ? '/payment-compat/evaluate/chain' : '/payment-compat/evaluate'
  return api.post<PaymentVerdict>(path, payload)
}

// ── Evolution Report ──

export interface EvolutionReport {
  generated_at: string
  improvements_completed: string[]
  performance_gains: Array<{ area: string; before: number; after: number; unit: string }>
  new_capabilities: string[]
  problems_detected: string[]
  next_actions: Array<{ action: string; priority: string; impact: string }>
  expected_impact: string
}

export async function fetchEvolutionReport(): Promise<EvolutionReport> {
  return api.post<EvolutionReport>('/direct-work/evolution-report', {})
}

export interface EvolutionReportHistory {
  history: EvolutionReport[]
}

export async function fetchEvolutionReportHistory(limit: number = 30): Promise<EvolutionReportHistory> {
  return api.get<EvolutionReportHistory>(`/direct-work/evolution-report/history?limit=${limit}`)
}

// ── Success Stats ──

export interface SuccessStats {
  total_opportunities: number
  success_rate: number
  average_payout: number
  total_earnings: number
  best_platform: string
  by_platform: Record<string, { opportunities: number; success_rate: number; total_earnings: number }>
}

export async function fetchSuccessStats(): Promise<SuccessStats> {
  return api.get<SuccessStats>('/direct-work/success-stats')
}

export async function prepareDelivery(itemId: string): Promise<DeliveryPackage> {
  return api.post<DeliveryPackage>(`/direct-work/workbank/${itemId}/deliver/prepare`, {})
}

export async function approveDelivery(itemId: string): Promise<{ status: string; reward: number }> {
  return api.post<{ status: string; reward: number }>(`/direct-work/workbank/${itemId}/deliver/approve`, {})
}

// ── Wear OS ──

export interface WearOSStatus {
  system_online: boolean
  scheduler_running: boolean
  active_workflows: number
  pending_approvals: number
  findings_total: number
  findings_confirmed: number
  targets_active: number
  health_score: number
  last_updated: string
}

export interface WearOSNotification {
  notification_id: string
  title: string
  message: string
  level: 'critical' | 'high' | 'medium' | 'low'
  created_at: string
  read: boolean
  requires_action: boolean
  action_type: string | null
}

export interface WearOSApproval {
  request_id: string
  title: string
  description: string
  workflow_id: string | null
  created_at: string
  responded: boolean
  approved: boolean | null
}

export async function fetchWearOSStatus(): Promise<WearOSStatus> {
  return api.get<WearOSStatus>('/wear-os/status')
}

export async function fetchWearOSNotifications(
  options?: { level?: string; unread_only?: boolean; limit?: number },
): Promise<WearOSNotification[]> {
  const params = new URLSearchParams()
  if (options?.level) params.set('level', options.level)
  if (options?.unread_only) params.set('unread_only', 'true')
  if (options?.limit) params.set('limit', String(options.limit))
  const qs = params.toString()
  return api.get<WearOSNotification[]>(`/wear-os/notifications${qs ? `?${qs}` : ''}`)
}

export async function markWearOSNotificationRead(notificationId: string): Promise<{ success: boolean }> {
  return api.put<{ success: boolean }>(`/wear-os/notification/${notificationId}/read`)
}

export async function sendWearOSNotification(payload: {
  title: string
  message: string
  level?: string
  requires_action?: boolean
  action_type?: string
}): Promise<WearOSNotification> {
  return api.post<WearOSNotification>('/wear-os/notification', payload)
}

export async function fetchWearOSPendingApprovals(): Promise<WearOSApproval[]> {
  return api.get<WearOSApproval[]>('/wear-os/approvals/pending')
}

export async function requestWearOSApproval(payload: {
  title: string
  description: string
  workflow_id?: string
}): Promise<WearOSApproval> {
  return api.post<WearOSApproval>('/wear-os/approval-request', payload)
}

export async function respondWearOSApproval(
  requestId: string,
  approved: boolean,
): Promise<{ success: boolean; approved: boolean }> {
  return api.post<{ success: boolean; approved: boolean }>(`/wear-os/approval/${requestId}/respond`, { approved })
}

export async function clearWearOSNotifications(days = 7): Promise<{ success: boolean; cleared_count: number }> {
  return api.post<{ success: boolean; cleared_count: number }>('/wear-os/clear-notifications', { days })
}

// ── Max Daily Income ──

export interface MaxDailyItem {
  platform: string
  title: string
  category: string
  reward: number
  acceptance_probability: number
  probability_base: number
  probability_full: number
  cash_speed: number
  cash_window: string
  expected_value_usd: number
  hours_estimate: number
  blocked: boolean
  direct_link: string
}

export interface MaxDailyIncomePlan {
  generated_at: string
  daily_target_usd: number
  conservative_max_usd: number
  realistic_max_usd: number
  optimistic_max_usd: number
  unlock_potential_usd: number
  gap_usd: number
  optimism_arguments: string[]
  items: MaxDailyItem[]
  needs_access_count: number
  actions: string[]
  notes: string[]
  digest: { text: string }
}

export async function fetchMaxDailyIncome(dailyTarget?: number): Promise<MaxDailyIncomePlan> {
  return api.post<MaxDailyIncomePlan>('/direct-work/max-daily-income', {
    opportunities: [],
    daily_target_usd: dailyTarget ?? 0,
  })
}

// ── Pending Actions (Notifications) ──

export interface PendingAction {
  action_id: string
  title: string
  reason: string
  impact: string
  steps: string[]
  ui_path: string
  category: string
  priority: string
  created_at: string
  subject_id: string
  subject_type: string
  metadata: Record<string, unknown>
}

export async function fetchPendingActions(): Promise<PendingAction[]> {
  return api.get<PendingAction[]>('/api/notifications/pending-actions')
}

export async function resolveAction(actionId: string): Promise<{ success: boolean }> {
  return api.post<{ success: boolean }>(`/api/notifications/actions/${actionId}/resolve`, {})
}

// ── Investment Status ──

export interface InvestmentStatusData {
  success: boolean
  status: {
    total_capital: number
    deployed: number
    available: number
    high_risk_deployed: number
    high_risk_limit: number
    paused: boolean
    active_strategies: string[]
    paused_strategies: string[]
    summary: Record<string, unknown>
  }
}

export async function fetchInvestmentStatus(): Promise<InvestmentStatusData> {
  return api.get<InvestmentStatusData>('/api/investment/status')
}

export async function fetchInvestmentMetrics(): Promise<Record<string, unknown>> {
  return api.get<Record<string, unknown>>('/api/investment/metrics')
}

// ── Pending Deliveries ──

export interface PendingDelivery {
  item_id: string
  platform: string
  title: string
  reward: number
  ready_to_deliver: boolean
  package_path: string
  submission_url: string
  deliverables: string[]
}

export async function fetchPendingDeliveries(): Promise<PendingDelivery[]> {
  return api.get<PendingDelivery[]>('/direct-work/deliver/pending')
}

// ── Copilot Chat ──

export interface ChatMessage {
  role: string
  content: string
}

export interface CopilotChatResponse {
  status: string
  response: string
  provider: string
  model: string
  duration_ms: number
  error: string | null
}

export async function sendChatMessage(
  message: string,
  history: ChatMessage[] = [],
  taskType: string = 'chat',
): Promise<CopilotChatResponse> {
  return api.post<CopilotChatResponse>('/api/copilot/chat', {
    message,
    history,
    task_type: taskType,
  })
}

export async function executeCommand(
  action: string,
  params: Record<string, unknown> = {},
): Promise<{ status: string; result: unknown }> {
  return api.post<{ status: string; result: unknown }>('/api/copilot/execute', {
    action,
    params,
  })
}

// ── System Commands ──

export interface CommandInfo {
  name: string
  description: string
  category: string
  permission: string
}

export async function listCommands(): Promise<CommandInfo[]> {
  const res = await api.get<{ commands: CommandInfo[] }>('/api/commands')
  return res.commands
}

export async function runCommand(
  commandName: string,
  args: Record<string, unknown> = {},
): Promise<{ status: string; output: string }> {
  return api.post<{ status: string; output: string }>(`/api/commands/${commandName}/execute`, args)
}

// ── Daily Companion ──

export interface DailyCompanionState {
  generated_at: string
  system: {
    status: string
    score: number
    running: boolean
    snapshots: number
  }
  personal: {
    pending_tasks: number
    delivered_today: number
    learning_goals: string[]
  }
  market: {
    opportunities: number
    top_sources: Array<{
      name: string
      category: string
      trust_score: number
      earning_potential: string
    }>
    new_ecosystems: number
    recommendation: string
  }
  focus: {
    stop: string[]
    automate: string[]
    delegate: string[]
    improve: string[]
  }
  briefing: {
    greeting: string
    system_health: string
    important_tasks: string
    recommended_actions: string[]
    focus_note: string
  }
  projection: {
    crossing_months: number | null
    months_to_target: number | null
    monthly_curve: Array<{ month: number; projected_usd: number }>
    note: string
  }
}

export async function fetchDailyCompanion(
  workIncomeUsdPerMonth = 0,
  savingsUsdPerMonth = 0,
  startCapitalUsd = 0,
  annualReturnRate = 0.10,
  targetMonthlyUsd = 100000
): Promise<DailyCompanionState> {
  return api.post<DailyCompanionState>('/direct-work/daily-companion', {
    work_income_usd_per_month: workIncomeUsdPerMonth,
    savings_usd_per_month: savingsUsdPerMonth,
    start_capital_usd: startCapitalUsd,
    annual_return_rate: annualReturnRate,
    target_monthly_usd: targetMonthlyUsd,
  })
}

// ── Profile Kit ──

export interface ProfileKitProfile {
  name: string
  country: string
  skills: string[]
  experience_level: string
  availability_hours: number
  github_url: string
  linkedin_url: string
  portfolio_url: string
}

export interface ProfileKitField {
  key: string
  label: string
  text: string
}

export interface ProfileKitStatus {
  saved: boolean
  available_platforms: string[]
  profile: ProfileKitProfile
}

export interface ProfileKitResponse {
  kits: Record<string, Record<string, ProfileKitField[]>>
}

export async function fetchProfileKitStatus(): Promise<ProfileKitStatus> {
  return api.get<ProfileKitStatus>('/api/profile-kit/')
}

export async function saveProfileKit(profile: ProfileKitProfile): Promise<{ success: boolean; saved: ProfileKitProfile }> {
  return api.post<{ success: boolean; saved: ProfileKitProfile }>('/api/profile-kit/', profile)
}

export async function generateProfileKit(profile: ProfileKitProfile): Promise<ProfileKitResponse> {
  return api.post<ProfileKitResponse>('/api/profile-kit/generate', profile)
}

// ── Outlook Calendar + Microsoft To Do Sync ──

export interface OutlookStatus {
  configured: boolean
  connected: boolean
  user: string
}

export interface OutlookEvent {
  id: string
  subject: string
  start: string
  end: string
  location: string
  organizer: string
  is_online: boolean
  body_preview: string
}

export interface OutlookAgenda {
  configured: boolean
  connected: boolean
  events: OutlookEvent[]
  unread: number
}

export interface OutlookSyncTask {
  id: number
  title: string
  status: string
  priority: string
  due_date: string
  calendar_event_id: string | null
  synced_to_calendar: boolean
  todo_task_id: string | null
  synced_to_todo: boolean
  last_synced_at: string
}

export interface OutlookTodoList {
  id: string
  display_name: string
  is_owner: boolean
}

export interface OutlookTodoTask {
  id: string
  title: string
  status: string
  importance: string
  due_date: string
  list_id: string
  list_name: string
}

export interface OutlookTodoData {
  configured: boolean
  connected: boolean
  lists: OutlookTodoList[]
  tasks: OutlookTodoTask[]
}

export interface OutlookSyncSummary {
  created: number
  updated: number
  deleted: number
  skipped: number
  errors: number
}

export interface OutlookTodoSyncSummary {
  todo_created: number
  todo_updated: number
  todo_deleted: number
  todo_skipped: number
  todo_errors: number
}

export async function getOutlookStatus() {
  return api.get<{ data: OutlookStatus }>('/outlook/status')
}

export async function getOutlookAgenda(daysAhead = 14, maxResults = 50) {
  return api.get<{ data: OutlookAgenda }>('/outlook/agenda', { days_ahead: daysAhead, max_results: maxResults })
}

export async function getOutlookTodo() {
  return api.get<{ data: OutlookTodoData }>('/outlook/todo')
}

export async function syncOutlookCalendar() {
  return api.post<{ data: { summary: OutlookSyncSummary; todo: OutlookTodoSyncSummary } }>('/outlook/sync')
}

export async function getOutlookTasks(limit = 100) {
  return api.get<{ data: { tasks: OutlookSyncTask[] } }>('/outlook/tasks', { limit })
}

// ════════════════════════════════════════════════════════════════
// FEATURE PARITY LAYER — Execution Queue · Capital · AI Providers ·
// Revenue Center · Risk/Emergency (spec: FRONTEND FEATURE-PARITY)
// ════════════════════════════════════════════════════════════════

// ── Execution Queue ──

export type ExecState =
  | 'discovered'
  | 'qualified'
  | 'ready'
  | 'queued'
  | 'executing'
  | 'waiting_human'
  | 'submitted'
  | 'verification'
  | 'paid'
  | 'rejected'
  | 'blocked'
  | 'failed'
  | 'dead_letter'

export interface ExecutionQueueItem {
  item_id: string
  state: ExecState
  payload: Record<string, unknown>
  history: string[]
}

export const EXEC_QUEUE_COLUMNS: Array<{ key: string; states: ExecState[]; label: string }> = [
  { key: 'now', states: ['queued', 'executing'], label: 'NOW' },
  { key: 'next', states: ['discovered', 'qualified', 'ready'], label: 'NEXT' },
  { key: 'waiting', states: ['waiting_human', 'submitted', 'verification'], label: 'WAITING' },
  { key: 'done', states: ['paid', 'rejected', 'blocked', 'failed', 'dead_letter'], label: 'DONE' },
]

export async function fetchExecutionQueue(): Promise<ExecutionQueueItem[]> {
  return api.get<ExecutionQueueItem[]>('/execution-queue')
}

export async function transitionExecutionItem(itemId: string, targetState: string): Promise<ExecutionQueueItem> {
  return api.post<ExecutionQueueItem>(`/execution-queue/${itemId}/transition`, { target_state: targetState })
}

export async function fetchValidTransitions(current: string): Promise<string[]> {
  return api.get<string[]>('/execution-queue/states/transitions', { current })
}

// ── Capital Snapshot (SSOT de patrimonio) ──

export interface CapitalSnapshot {
  generated_at?: string
  bounty?: { pagado_usd?: number; pendiente_usd?: number }
  work_income?: { entregado_usd: number; pendiente_usd: number; total_usd: number }
  investment?: { total_usd: number; estrategias: Array<{ name?: string; value?: number }> }
  atlas?: { total_usd?: number }
  crypto?: { total_usd?: number }
  expected_cash?: Array<{ rail?: string; amount_usd?: number; date?: string }>
  payment_compat?: { compatible?: number; total?: number }
  total_usd?: number
}

export async function fetchCapitalSnapshot(): Promise<CapitalSnapshot> {
  return api.get<CapitalSnapshot>('/financial/capital/snapshot')
}

// ── AI Providers (settings/ai + OAR + resilience) ──

export interface AiProviderStatus {
  id: string
  name: string
  available: boolean
  active?: boolean
  model?: string
}

export interface AiResilienceMode {
  mode: 'normal' | 'degraded' | 'offline_ai'
  since: string
  reason: string
}

export interface AiQuotaSnapshot {
  rpm_observed: number
  tokens_today: number
  day: string
  limits: { rpm?: number | null; rpd?: number | null; tpd?: number | null }
  limits_known: boolean
}

export interface OarStatus {
  initialized: boolean
  providers?: Array<{ id?: string; [k: string]: unknown }>
  message?: string
  resilience?: {
    mode?: AiResilienceMode | { mode: string; reason: string }
    recent_events?: Array<{ ts: string; mode: string; reason: string; healthy: string[] }>
    quotas?: Record<string, AiQuotaSnapshot>
  }
}

export interface AiCenterState {
  providers: AiProviderStatus[]
  config: {
    provider_type: string
    host: string
    model: string
    api_base: string
    active_provider: string
    available: boolean
  } | null
  oar: OarStatus | null
  errors: string[]
}

export async function fetchAiCenter(): Promise<AiCenterState> {
  const state: AiCenterState = { providers: [], config: null, oar: null, errors: [] }
  const [provRes, cfgRes, oarRes] = await Promise.allSettled([
    api.get<{ providers: AiProviderStatus[] }>('/settings/ai/providers'),
    api.get<AiCenterState['config']>('/settings/ai/config'),
    api.get<NonNullable<AiCenterState['oar']>>('/oar/status'),
  ])
  if (provRes.status === 'fulfilled') state.providers = provRes.value.providers ?? []
  else state.errors.push('providers')
  if (cfgRes.status === 'fulfilled') state.config = cfgRes.value
  else state.errors.push('config')
  if (oarRes.status === 'fulfilled') state.oar = oarRes.value
  else state.errors.push('oar')
  return state
}

// ── Revenue Summary (realized vs pending) ──

export interface RevenueSummary {
  total_earned: number
  pending_amount: number
  earnings_30d?: number
  by_platform?: Array<{ platform: string; earned: number; pending: number }>
  submissions?: number
}

export interface RevenueSubmission {
  id: string
  platform?: string
  title?: string
  status?: string
  amount?: number
  submitted_at?: string
}

export async function fetchRevenueSummary(): Promise<RevenueSummary> {
  const data = await api.get<Partial<RevenueSummary>>('/revenue/summary')
  return {
    total_earned: data.total_earned ?? 0,
    pending_amount: data.pending_amount ?? 0,
    earnings_30d: data.earnings_30d ?? 0,
    by_platform: data.by_platform ?? [],
    submissions: data.submissions ?? 0,
  }
}

export async function fetchRevenueSubmissions(): Promise<RevenueSubmission[]> {
  const data = await api.get<{ submissions?: RevenueSubmission[] } | RevenueSubmission[]>('/revenue/submissions')
  if (Array.isArray(data)) return data
  return data.submissions ?? []
}

// ── Risk / Emergency Mode ──

export interface EmergencyModeState {
  active: boolean
  reason?: string
  triggered_at?: string
  analysis?: Record<string, unknown>
}

export async function fetchEmergencyMode(): Promise<EmergencyModeState> {
  try {
    const data = await api.get<Partial<EmergencyModeState>>('/emergency-mode')
    return { active: !!data.active, reason: data.reason, triggered_at: data.triggered_at }
  } catch {
    return { active: false }
  }
}

// ── Daily Decision Digest ──

export interface DigestDecision {
  type: string
  title: string
  platform?: string
  reward?: number
  severity?: string
  action: string
  url?: string
  priority: number
}

export interface DailyDigestState {
  generated_at: string
  decisions: DigestDecision[]
  money: {
    ready_to_deliver: number
    public_ready: number
    total_potential_usd: number
    best_target?: { title: string; reward: number }
  }
  best_action: DigestDecision | null
  system_health: { services: Array<{ name: string; status: string }> }
  counts: { pending_decisions: number }
}

export async function fetchDailyDigest(): Promise<DailyDigestState> {
  return api.get<DailyDigestState>('/daily-digest')
}

// ── Career / Zero-Barrier / Revenue Timeline (conexión feature-parity) ──

export interface CareerStatus {
  status?: string
  skill_gaps?: Array<{ skill: string; category: string; priority: string }>
  daily_training?: { tasks?: Array<{ title: string; description?: string }> }
}

export async function fetchCareerStatus(): Promise<CareerStatus> {
  return api.get<CareerStatus>('/career/status')
}

export interface ZeroBarrierStats {
  total_opportunities?: number
  platforms?: Array<{ platform: string; count: number; avg_reward?: number }>
}

export async function fetchZeroBarrierStats(): Promise<ZeroBarrierStats> {
  return api.get<ZeroBarrierStats>('/zero-barrier/stats')
}

export interface RevenueTimelineResult {
  milestones?: Array<{ label: string; months?: number; monthly_income?: number }>
  current_monthly?: number
  target_monthly?: number
}

export async function fetchRevenueTimeline(targetMonthly = 3000): Promise<RevenueTimelineResult> {
  return api.post<RevenueTimelineResult>('/revenue-timeline/calculate', { target_monthly: targetMonthly })
}

// ── Unified Agenda ──

export interface AgendaItem {
  date: string
  horizon: string
  source: string
  title: string
  progress_pct: number
  reward?: number
  url?: string | null
  action?: string | null
}

export interface UnifiedAgendaState {
  generated_at: string
  total_items: number
  today: AgendaItem[]
  short_term: AgendaItem[]
  medium_term: AgendaItem[]
  long_term: AgendaItem[]
  counts: Record<string, number>
  best_action: AgendaItem | null
}

export async function fetchAgenda(): Promise<UnifiedAgendaState> {
  return api.get<UnifiedAgendaState>('/agenda')
}

// ── OneAction Autopilot ──

export interface OneAction {
  action_id: string
  action_type: string
  title: string
  description: string
  why: string
  instruction: string
  urgency: 'immediate' | 'today' | 'this_week' | 'this_month' | 'flexible'
  confidence_band: 'high' | 'medium' | 'low' | 'unknown'
  success_probability: number | null
  acceptance_probability: number | null
  payment_probability: number | null
  expected_value_usd: number | null
  ev_per_human_hour_usd: number | null
  estimated_human_hours: number | null
  cash_speed_days: number | null
  platform_name: string | null
  platform_readiness_pct: number
  platform_url: string | null
  prerequisites: string[]
  url: string | null
  expires_at: string | null
}

export async function fetchOneAction(params: { force_refresh?: boolean } = {}): Promise<OneAction | null> {
  return api.post<OneAction | null>('/autopilot/one-action', params)
}

// ════════════════════════════════════════════════════════════════════════
// TRADING LAB API
// ═══════════════════════════════════════════════════════════════════════

export interface TradingLabDashboard {
  generated_at: string
  system: { status: string; score: number }
  memory: { healthy: boolean; entries: number; namespaces: Record<string, number>; namespace_count: number }
  important_tasks: Array<{ title: string; platform: string; reward?: number; requirement?: string }>
  opportunities: {
    scanned_sources: number
    best_sources: Array<{ name: string; category: string; trust_score: number; earning_potential: string }>
  }
  unfinished_work: { ready_to_deliver: Array<{ title: string; platform: string; reward: number }>; needs_access: Array<{ title: string; platform: string; requirement: string }>; targets: Record<string, unknown> }
  improvements_suggested: Array<{ type: string; name: string; benefit: string; priority: string }>
  pending_approvals: Array<{ id: string; message: string; level?: string }>
  setup_progress: {
    complete_pct: number
    complete: boolean
    next_task: {
      id: string
      phase_label: string
      title: string
      why: string
      est_minutes: number
      how_to: string
    } | null
  }
}

export interface StrategyScore {
  strategy_id: string
  engine_id: string
  name: string
  rank: number
  composite_score: number
  return_score: number
  risk_adjusted_score: number
  consistency_score: number
  liquidity_score: number
  execution_quality_score: number
  robustness_score: number
  drawdown_penalty: number
  overfit_penalty: number
  correlation_penalty: number
  fee_penalty: number
  slippage_penalty: number
  data_quality_penalty: number
  regime_scores: Record<string, number>
  expected_value: number
  expected_value_usd: number
  sharpe: number
  max_drawdown: number
  win_rate: number
}

export interface CapitalSnapshot {
  generated_at: string
  total_usd: number
  bounty: { pagado_usd: number; pendiente_usd: number }
  work_income: { entregado_usd: number; pendiente_usd: number; total_usd: number }
  investment: { total_usd: number; estrategias: any[] }
  atlas: { total_usd: number }
  crypto: { total_usd: number }
  expected_cash: { total: number; by_rail: Array<{ rail: string; amount_usd: number; date: string }> }
  payment_compat: { compatible: number; total: number }
  work_income: { by_strategy: Array<any> }
}

export interface RiskSummary {
  metrics: {
    total_exposure: number
    daily_pnl: number
    weekly_pnl: number
    current_drawdown: number
    max_drawdown: number
    leverage: number
    liquidity: number
  }
  limits: {
    max_total_exposure: number
    max_strategy_exposure: number
    max_asset_exposure: number
    max_exchange_exposure: number
    max_daily_loss: number
    max_weekly_loss: number
    max_drawdown: number
    max_leverage: number
    min_liquidity: number
  }
  kill_switches: {
    global: boolean
    strategies: Record<string, boolean>
    exchanges: Record<string, boolean>
    assets: Record<string, boolean>
  }
}

export interface EngineHealthStatus {
  engine_id: string
  health: string
  last_check: string
  latency_ms: number | null
  error: string | null
  active_strategies: number
  cpu_percent: number | null
  memory_mb: number | null
  api_connected: boolean
  exchange_connected: Record<string, boolean>
  last_error: string | null
}

export interface ValidationStatus {
  overall_passed: boolean
  current_phase: string
  started_at: string
  completed_at: string | null
  phases: Record<string, {
    passed: boolean
    started_at: string
    completed_at: string | null
    error: string | null
    details: string
  }>
  overfit_report?: {
    overall_score: number
    risk_level: string
    checks: Array<{
      check_name: string
      passed: boolean
      severity: string
      details: any
      description: string
    }>
  }
  phases: Record<string, {
    passed: boolean
    started_at: string
    completed_at: string | null
    error: string | null
    details: string
  }>
}

export async function fetchTradingLabDashboard(): Promise<TradingLabDashboard> {
  return api.get<TradingLabDashboard>('/trading-lab/dashboard')
}

export async function fetchStrategyRankings(): Promise<StrategyScore[]> {
  return api.get<StrategyScore[]>('/trading-lab/strategies/rankings')
}


export async function fetchRiskSummary(): Promise<RiskSummary> {
  return api.get<RiskSummary>('/trading-lab/risk/summary')
}

export async function fetchEngineRegistry(): Promise<{ engines: EngineHealthStatus[] }> {
  return api.get<{ engines: EngineHealthStatus[] }>('/trading-lab/engines')
}

export async function fetchValidationStatus(): Promise<ValidationStatus> {
  return api.get<ValidationStatus>('/trading-lab/validation/status')
}

export async function fetchStrategyDetail(strategyId: string): Promise<any> {
  return api.get<any>(`/trading-lab/strategies/${strategyId}`)
}

// Trading Lab specific capital snapshot (different endpoint)
export async function fetchTradingLabCapitalSnapshot(): Promise<CapitalSnapshot> {
  return api.get<CapitalSnapshot>('/trading-lab/capital/snapshot')
}

// Availability snapshot for Mission Control
export async function fetchAvailabilitySnapshot(): Promise<any> {
  return api.get<any>('/availability/snapshot')
}

// One Best Action for Command Center
export interface OneBestAction {
  action_type: string
  title: string
  description: string
  why_now: string
  platform: string
  opportunity_id: string | null
  work_item_id: string | null
  estimated_human_hours: number
  expected_value_usd: number
  acceptance_probability: number
  cash_speed_days: number | null
  urgency: string
  prerequisites: string[]
  url: string | null
  next_step_instruction: string
  metadata: Record<string, unknown>
}

export async function fetchOneBestAction(): Promise<OneBestAction | null> {
  return api.get<OneBestAction | null>('/direct-work/one-best-action')
}

// ── Work Streams (Category-aware UI) ──

export type WorkStreamKey =
  | 'bug_bounty'
  | 'dev_bounty'
  | 'ai_work'
  | 'game_dev'
  | 'open_source'
  | 'tech_content'

export interface WorkStreamConfig {
  key: WorkStreamKey
  label: string
  icon: string
  description: string
  platforms: string[]
  access_type: 'api_key' | 'mixed' | 'manual_setup'
  deliverables: string[]
  quick_actions: string[]
  automation: string
  user_decides: string[]
}

export interface WorkStreamsResponse {
  streams: WorkStreamConfig[]
  category_to_stream: Record<string, WorkStreamKey>
  platform_to_stream: Record<string, WorkStreamKey>
}

export interface StreamOpportunitiesResponse {
  stream: WorkStreamKey
  stream_config: WorkStreamConfig
  total_found: number
  filtered: number
  ranked: Array<{
    rank: number
    opportunity: {
      id: string
      title: string
      platform: string
      category: string
      stream: string
      payment: number
      reward: number
    }
    overall_recommendation_score: number
    expected_value: number
    barrier_score: number
    payment_compat_score: number
    payout_method: string
  }>
}

export interface StreamWorkBankResponse {
  stream: WorkStreamKey
  stream_config: WorkStreamConfig
  total: number
  ready_to_deliver: number
  needs_access: number
  delivered: number
  items: {
    ready: WorkBankItem[]
    needs_access: WorkBankItem[]
    delivered: WorkBankItem[]
  }
  targets: Record<string, WorkBankTarget>
}

export async function fetchWorkStreams(): Promise<WorkStreamsResponse> {
  return api.get<WorkStreamsResponse>('/direct-work/streams')
}

export async function fetchStreamOpportunities(
  streamKey: WorkStreamKey,
  limit: number = 20,
): Promise<StreamOpportunitiesResponse> {
  return api.get<StreamOpportunitiesResponse>(`/direct-work/streams/${streamKey}/opportunities`, { params: { limit } })
}

export async function fetchStreamWorkBank(streamKey: WorkStreamKey): Promise<StreamWorkBankResponse> {
  return api.get<StreamWorkBankResponse>(`/direct-work/streams/${streamKey}/workbank`)
}

export async function runStreamCycle(
  streamKey: WorkStreamKey,
  target: number | null = null,
): Promise<WorkBankState> {
  const summary = await api.post<{ scanned: number; new_items_added: number; ready_to_deliver: number; needs_access: number }>(
    `/direct-work/streams/${streamKey}/cycle`,
    { target },
  )
  const state = await fetchStreamWorkBank(streamKey)
  return { ...state, ...summary } as any
}

// ── Knowledge Graph ──

export interface KnowledgeGraphStats {
  nodes: number
  edges: number
  node_types: Record<string, number>
  relationships: Record<string, number>
}

export interface KnowledgeGraphNode {
  id: string
  type: string
  name: string
  properties: Record<string, any>
  confidence: number
  created_at: string
  last_updated: string
}

export interface KnowledgeGraphEdge {
  source: string
  target: string
  relationship: string
  strength: number
  properties: Record<string, any>
  confidence: number
}

export interface KnowledgeGraphSubgraph {
  center_id: string
  nodes: KnowledgeGraphNode[]
  edges: KnowledgeGraphEdge[]
  depth: number
}

export async function fetchKnowledgeGraphStats(): Promise<KnowledgeGraphStats> {
  return api.get<KnowledgeGraphStats>('/api/knowledge-graph/stats')
}

export async function fetchKnowledgeGraphNodes(
  params: { type?: string; limit?: number } = {}
): Promise<KnowledgeGraphNode[]> {
  return api.get<KnowledgeGraphNode[]>('/api/knowledge-graph/nodes', { params })
}

export async function searchKnowledgeGraphNodes(
  query: string,
  params: { type?: string; limit?: number } = {}
): Promise<KnowledgeGraphNode[]> {
  return api.get<KnowledgeGraphNode[]>('/api/knowledge-graph/nodes/search', { params: { q: query, ...params } })
}

export async function fetchKnowledgeGraphSubgraph(
  nodeId: string,
  depth: number = 2,
  limit: number = 100
): Promise<KnowledgeGraphSubgraph> {
  return api.get<KnowledgeGraphSubgraph>(`/api/knowledge-graph/subgraph/${nodeId}`, { params: { depth, limit } })
}

export async function fetchKnowledgeGraphEdges(
  params: { node_id?: string; direction?: string; relationship?: string; limit?: number } = {}
): Promise<{ edges: KnowledgeGraphEdge[]; count: number }> {
  return api.get('/api/knowledge-graph/edges', { params })
}

export async function createKnowledgeGraphEdge(
  sourceId: string,
  targetId: string,
  relationship: string,
  strength: number = 1
): Promise<{ source_id: string; target_id: string; relationship: string; strength: number }> {
  return api.post('/api/knowledge-graph/edges', { source_id: sourceId, target_id: targetId, relationship, strength })
}

export async function upsertKnowledgeGraphNode(
  type: string,
  name: string,
  properties: Record<string, any> | null = null,
  nodeId: string | null = null
): Promise<KnowledgeGraphNode> {
  return api.post('/api/knowledge-graph/nodes', { type, name, properties, node_id: nodeId })
}
