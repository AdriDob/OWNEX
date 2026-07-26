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
  { label: 'Analizadas', value: 0, color: 'text-blue-400' },
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
      security: 'text-blue-400',
      forge: 'text-purple-400',
      pulse: 'text-green-400',
      vault: 'text-amber-400',
      atlas: 'text-sky-400',
    }

    const badgeColorMap: Record<string, string> = {
      security: 'bg-blue-500/20 text-blue-400',
      forge: 'bg-purple-500/20 text-purple-400',
      pulse: 'bg-green-500/20 text-green-400',
      vault: 'bg-amber-500/20 text-amber-400',
      atlas: 'bg-sky-500/20 text-sky-400',
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

// ── Main fetch ──

export async function fetchOwnexDashboard(): Promise<OwnexDashboardData> {
  const [stages, opportunities, activity, mission, agents, revenue, cycles] = await Promise.all([
    fetchOverview(),
    fetchOpportunities(),
    fetchActivity(),
    fetchMissionStatus(),
    fetchSystemStatus(),
    fetchRevenueSnapshot(),
    fetchCycles(),
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
    timestamp: mission.timestamp,
  }
}