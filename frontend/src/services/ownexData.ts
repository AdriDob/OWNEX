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
  try {
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
  } catch {
    return DEFAULT_STAGES
  }
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
  try {
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
  } catch {
    return []
  }
}

async function fetchActivity(): Promise<KnowledgeItem[]> {
  try {
    const data = await api.get<any>('/activity', { hours: 24 })
    const events = data?.events || data?.items || []
    return events.slice(0, 5).map((e: any) => ({
      id: String(e.id || Math.random()),
      type: e.severity === 'high' ? 'alert' : e.type === 'decision' ? 'decision' : e.type === 'pattern' ? 'pattern' : 'learning',
      typeLabel: e.severity === 'high' ? 'Evento' : e.type === 'decision' ? 'Decisión' : e.type === 'pattern' ? 'Patrón' : 'Actividad',
      message: e.title || e.message || `${e.type}: #${e.id}`,
      timestamp: e.timestamp || new Date().toISOString(),
    }))
  } catch {
    return []
  }
}

async function fetchMissionStatus(): Promise<{ health: number; status: string; nextAction: NextActionItem | null; timestamp: string }> {
  try {
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
  } catch {
    return { health: 0, status: 'offline', nextAction: null, timestamp: new Date().toISOString() }
  }
}

async function fetchSystemStatus(): Promise<AgentStatus[]> {
  try {
    const data = await api.get<any>('/system/state')
    const services = data?.services || []
    if (services.length > 0) {
      return services.map((s: any) => ({
        name: s.name || s.id || 'Servicio',
        status: s.status === 'healthy' ? 'online' : s.status === 'degraded' ? 'limited' : 'offline',
        description: s.description || s.type || '',
      }))
    }
    return [
      { name: 'Hermes', status: 'online', description: 'Orquestación' },
      { name: 'OpenCode', status: 'online', description: 'Implementación' },
      { name: 'Cline', status: 'online', description: 'Edición IDE' },
      { name: 'Ollama', status: 'local', description: 'Modelo local' },
      { name: 'FCC', status: 'limited', description: 'Router IA' },
    ]
  } catch {
    return [
      { name: 'Hermes', status: 'online', description: 'Orquestación' },
      { name: 'OpenCode', status: 'online', description: 'Implementación' },
      { name: 'Cline', status: 'online', description: 'Edición IDE' },
      { name: 'Ollama', status: 'local', description: 'Modelo local qwen2.5' },
      { name: 'FCC', status: 'limited', description: 'Router multi-provider' },
    ]
  }
}

async function fetchRevenueSnapshot(): Promise<RevenueSnapshotData | null> {
  try {
    const data = await api.get<RevenueSummaryResponse>('/economic/financial-summary')
    return {
      usdPerHour: data.usd_per_hour ?? 0,
      monthlyTotal: data.monthly_payout ?? 0,
      pendingTotal: data.pending_total ?? 0,
      bestPlatform: data.best_platform ?? '—',
    }
  } catch {
    return null
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
}

export async function fetchDeliveryQueue(): Promise<{ count: number; items: DeliverableItem[] }> {
  return api.get<{ count: number; items: DeliverableItem[] }>('/direct-work/deliver/pending')
}

// ── Daily Operation Mode (GOOD MORNING) ──

export interface GoodMorningState {
  generated_at: string
  summary: string
  system: { status: string; score: number }
  memory: { healthy: boolean; entries: number; namespaces: Record<string, number> }
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

export async function prepareDelivery(itemId: string): Promise<DeliveryPackage> {
  return api.post<DeliveryPackage>(`/direct-work/workbank/${itemId}/deliver/prepare`, {})
}

export async function approveDelivery(itemId: string): Promise<{ status: string; reward: number }> {
  return api.post<{ status: string; reward: number }>(`/direct-work/workbank/${itemId}/deliver/approve`, {})
}