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

export interface OwnexDashboardData {
  throughputStages: ThroughputStage[]
  throughputEfficiency: number
  agents: AgentStatus[]
  opportunities: OpportunityItem[]
  nextAction: NextActionItem | null
  knowledgeFeed: KnowledgeItem[]
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

interface OpportunityTopItem {
  id?: string
  title?: string
  source?: string
  type?: string
  estimated_payout?: number
  score?: number
  confidence?: number
  priority?: string
  effort?: string
  platform?: string
  reward?: number
}

interface ActivityEvent {
  id: string
  type: string
  message: string
  timestamp: string
  severity?: string
}

const DEFAULT_STAGES = [
  { label: 'Oportunidades detectadas', value: 0, color: 'text-accent' },
  { label: 'Analizadas', value: 0, color: 'text-blue-400' },
  { label: 'Priorizadas', value: 0, color: 'text-warning' },
  { label: 'En ejecución', value: 0, color: 'text-primary' },
  { label: 'Completadas', value: 0, color: 'text-success' },
]

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

async function fetchOpportunities(): Promise<OpportunityItem[]> {
  try {
    const data = await api.get<{ opportunities?: OpportunityTopItem[]; items?: OpportunityTopItem[] }>('/opportunity/top')
    const list = data.opportunities || data.items || []
    return list.slice(0, 5).map((item, i) => ({
      id: item.id || `opp-${i}`,
      title: item.title || 'Oportunidad sin título',
      source: item.source || item.platform || 'Desconocida',
      type: item.type || 'General',
      reward: item.estimated_payout || item.reward || 0,
      confidence: Math.round((item.confidence ?? 0) * 100),
      effort: item.effort || (item.priority === 'high' ? 'Bajo' : item.priority === 'medium' ? 'Medio' : '—'),
      action: item.score && item.score > 0.7 ? 'Analizar' : 'Revisar',
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

// ── Main fetch ──

export async function fetchOwnexDashboard(): Promise<OwnexDashboardData> {
  const [stages, opportunities, activity, mission, agents] = await Promise.all([
    fetchOverview(),
    fetchOpportunities(),
    fetchActivity(),
    fetchMissionStatus(),
    fetchSystemStatus(),
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
    systemHealth: mission.health,
    systemStatus: mission.status,
    timestamp: mission.timestamp,
  }
}
