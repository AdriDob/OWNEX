/**
 * OWNEX canonical frontend domain types.
 *
 * Single source of truth for the Mission Control UI. Mirrors the backend
 * contracts (direct_work, autopilot/one-action, max-daily-income, capital,
 * revenue) without inventing fields. All money in USD unless noted.
 */

/** The three opportunity engines. Everything else is noise. */
export type OpportunityEngine = 'dev' | 'bug' | 'ai' | 'other'

/** Canonical opportunity row for the Opportunity Radar. */
export interface CanonicalOpportunity {
  id: string
  title: string
  platform: string
  engine: OpportunityEngine
  /** Expected value in USD (probability-weighted). */
  expectedValueUsd: number
  /** Expected net USD per human hour. Null when hours unknown. */
  evPerHumanHourUsd: number | null
  /** Acceptance probability 0-1. Null when unknown. */
  acceptanceProbability: number | null
  /** Estimated human hours. Null when unknown. */
  humanHours: number | null
  /** Days until cash. Null when unknown. */
  cashSpeedDays: number | null
  /** LOW | MEDIUM | HIGH | UNKNOWN */
  risk: 'LOW' | 'MEDIUM' | 'HIGH' | 'UNKNOWN'
  /** Payment compatibility note, if evaluated. */
  paymentNote: string | null
  blocked: boolean
  directLink: string | null
  status: 'ready' | 'needs_access' | 'preparing' | 'unknown'
}

/** Work Bank summary for the Mission Control strip. */
export interface WorkBankSummary {
  readyToDeliver: number
  needsAccess: number
  preparing: number
  delivered: number
  totalActive: number
}

/** Revenue snapshot — realized vs pipeline, never mixed. */
export interface RevenueSnapshot {
  realizedUsd: number
  pendingUsd: number
  last30dUsd: number
  hasAny: boolean
}

/** Capital snapshot (SSOT patrimonio). */
export interface CapitalSnapshot {
  totalUsd: number
  investmentUsd: number
  cryptoUsd: number
}

/** Next Best Action — answers the 6 questions. */
export interface NextBestAction {
  title: string
  why: string
  expectedValueUsd: number | null
  expectedNetUsd: number | null
  evPerHourUsd: number | null
  humanHours: number | null
  risk: 'LOW' | 'MEDIUM' | 'HIGH' | 'UNKNOWN'
  platform: string | null
  platformUrl: string | null
  successCondition: string | null
  nextAfterSuccess: string | null
  actionId: string | null
  urgency: 'immediate' | 'today' | 'this_week' | 'this_month' | 'flexible'
}

/** Semantic tags for AI answers. Grounded in API data, never invented. */
export type SemanticTag = 'FACT' | 'INFERENCE' | 'RECOMMENDATION' | 'UNKNOWN'

export interface SemanticBlock {
  tag: SemanticTag
  text: string
}

/** Canonical AI message in the single conversation. */
export interface AiMessage {
  id: number
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  provider?: string
  model?: string
  taskType?: string
  /** Semantic blocks when the answer is grounded in canonical state. */
  semantics?: SemanticBlock[]
  /** Pending tool approval, if any. */
  toolApproval?: AiToolApproval | null
  status: 'sending' | 'typing' | 'completed' | 'error'
}

export interface AiToolApproval {
  id: number
  name: string
  args: Record<string, unknown>
  danger: boolean
  description: string
}

/** Live context — the canonical state the AI consults. */
export interface CanonicalContext {
  generatedAt: string
  system: { status: string; health: number }
  nextAction: NextBestAction | null
  workBank: WorkBankSummary | null
  revenue: RevenueSnapshot | null
  capital: CapitalSnapshot | null
  topOpportunities: CanonicalOpportunity[]
}

/** Classify a raw category/platform string into one of the three engines. */
export function classifyEngine(category: string, platform: string, title: string): OpportunityEngine {
  const hay = `${category} ${platform} ${title}`.toLowerCase()
  if (
    hay.includes('bug') ||
    hay.includes('secur') ||
    hay.includes('hackerone') ||
    hay.includes('bugcrowd') ||
    hay.includes('intigriti') ||
    hay.includes('immunefi') ||
    hay.includes('code4rena') ||
    hay.includes('yeswehack') ||
    hay.includes('audit') ||
    hay.includes('vuln') ||
    hay.includes('pentest')
  )
    return 'bug'
  if (
    hay.includes('ai_evaluation') ||
    hay.includes('ai-training') ||
    hay.includes('ai training') ||
    hay.includes('outlier') ||
    hay.includes('mindrift') ||
    hay.includes('dataannotation') ||
    hay.includes('data annotation') ||
    hay.includes('opyre') ||
    hay.includes('annotation') ||
    hay.includes('label')
  )
    return 'ai'
  if (
    hay.includes('dev') ||
    hay.includes('opire') ||
    hay.includes('issuehunt') ||
    hay.includes('algora') ||
    hay.includes('gitcoin') ||
    hay.includes('superteam') ||
    hay.includes('code') ||
    hay.includes('pr') ||
    hay.includes('github') ||
    hay.includes('freelance')
  )
    return 'dev'
  return 'other'
}
