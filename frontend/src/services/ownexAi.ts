/**
 * OWNEX canonical AI service.
 *
 * Single entry point for the AI Command Center. It never chats against an
 * isolated conversation: every answer is grounded in canonical state
 * (command-center/today, autopilot/one-action, daily-brief, workbank,
 * capital) and executed through the OAR provider router
 * (POST /api/copilot/chat).
 *
 * No new backend. Composes existing endpoints, best-effort with timeouts.
 */
import { api } from '@/lib/api'
import {
  fetchCapitalSnapshot,
  fetchDirectWorkDailyBrief,
  fetchDirectWorkWorkBank,
  fetchOneAction,
  fetchRevenueSummary,
  sendChatMessage,
  executeCommand,
  type ChatMessage,
  type CopilotChatResponse,
} from '@/services/ownexData'
import type { CanonicalContext, NextBestAction } from '@/types/ownex'

const HISTORY_KEY = 'ownex-ai-history-v1'
const MAX_HISTORY = 60

export interface GroundedAnswer {
  text: string
  provider: string
  model: string
  usedContext: boolean
}

function withTimeout<T>(p: Promise<T>, ms: number, fallback: T): Promise<T> {
  return Promise.race([
    p,
    new Promise<T>((resolve) => setTimeout(() => resolve(fallback), ms)),
  ])
}

/** Build the canonical context the AI consults. Best-effort, never blocks. */
export async function buildCanonicalContext(): Promise<CanonicalContext> {
  const [actionRes, briefRes, bankRes, capitalRes, revenueRes] = await Promise.allSettled([
    withTimeout(fetchOneAction({}), 8000, null),
    withTimeout(fetchDirectWorkDailyBrief(5), 10000, null),
    withTimeout(fetchDirectWorkWorkBank(), 8000, null),
    withTimeout(fetchCapitalSnapshot(), 8000, null),
    withTimeout(fetchRevenueSummary(), 8000, null),
  ])

  const action = actionRes.status === 'fulfilled' ? actionRes.value : null
  const brief = briefRes.status === 'fulfilled' ? briefRes.value : null
  const bank = bankRes.status === 'fulfilled' ? bankRes.value : null
  const capital = capitalRes.status === 'fulfilled' ? capitalRes.value : null
  const revenue = revenueRes.status === 'fulfilled' ? revenueRes.value : null

  let nextAction: NextBestAction | null = null
  if (action) {
    nextAction = {
      title: action.title,
      why: action.why || action.description || '',
      expectedValueUsd: action.expected_value_usd ?? null,
      expectedNetUsd: null,
      evPerHourUsd: action.ev_per_human_hour_usd ?? null,
      humanHours: action.estimated_human_hours ?? null,
      risk: 'UNKNOWN',
      platform: action.platform_name ?? null,
      platformUrl: action.platform_url ?? action.url ?? null,
      successCondition: null,
      nextAfterSuccess: null,
      actionId: action.action_id,
      urgency: action.urgency ?? 'today',
    }
  }

  const topOpportunities = (brief?.ranked ?? []).slice(0, 5).map((r: any) => ({
    id: String(r?.opportunity?.id ?? r?.id ?? Math.random()),
    title: String(r?.opportunity?.title ?? r?.title ?? 'Oportunidad'),
    platform: String(r?.opportunity?.platform ?? r?.platform ?? ''),
    engine: 'other' as const,
    expectedValueUsd: Number(r?.expected_value ?? 0),
    evPerHumanHourUsd: r?.ev_per_human_hour_usd ?? r?.htroi ?? null,
    acceptanceProbability: r?.acceptance_probability ?? null,
    humanHours: null,
    cashSpeedDays: null,
    risk: 'UNKNOWN' as const,
    paymentNote: null,
    blocked: false,
    directLink: r?.opportunity?.url ?? null,
    status: 'ready' as const,
  }))

  return {
    generatedAt: new Date().toISOString(),
    system: { status: 'operational', health: 0 },
    nextAction,
    workBank: bank
      ? {
          readyToDeliver: bank.ready_to_deliver ?? 0,
          needsAccess: bank.needs_access ?? 0,
          preparing: 0,
          delivered: bank.delivered ?? 0,
          totalActive: bank.total_in_bank ?? 0,
        }
      : null,
    revenue: revenue
      ? {
          realizedUsd: revenue.total_earned ?? 0,
          pendingUsd: revenue.pending_amount ?? 0,
          last30dUsd: revenue.earnings_30d ?? 0,
          hasAny: (revenue.total_earned ?? 0) > 0 || (revenue.pending_amount ?? 0) > 0,
        }
      : null,
    capital: capital
      ? {
          totalUsd: capital.total_usd ?? 0,
          investmentUsd: capital.investment?.total_usd ?? 0,
          cryptoUsd: capital.crypto?.total_usd ?? 0,
        }
      : null,
    topOpportunities,
  }
}

/** Render canonical context as compact prompt text for the model. */
export function renderContextPrompt(ctx: CanonicalContext): string {
  const lines: string[] = ['[OWNEX canonical state — ground every claim in this. Mark unknowns as UNKNOWN.]']
  if (ctx.nextAction) {
    const n = ctx.nextAction
    lines.push(
      `NEXT BEST ACTION: ${n.title} | EV $${n.expectedValueUsd ?? '?'} | EV/h $${n.evPerHourUsd ?? '?'} | hours ${n.humanHours ?? '?'} | platform ${n.platform ?? '?'} | why: ${n.why}`,
    )
  } else {
    lines.push('NEXT BEST ACTION: UNKNOWN (no action available)')
  }
  if (ctx.workBank) {
    lines.push(
      `WORKBANK: ready=${ctx.workBank.readyToDeliver} needs_access=${ctx.workBank.needsAccess} delivered=${ctx.workBank.delivered}`,
    )
  }
  if (ctx.revenue) {
    lines.push(
      `REVENUE (realized, never pipeline): earned=$${ctx.revenue.realizedUsd} pending=$${ctx.revenue.pendingUsd} 30d=$${ctx.revenue.last30dUsd}`,
    )
  }
  if (ctx.capital) {
    lines.push(`CAPITAL total=$${ctx.capital.totalUsd} investment=$${ctx.capital.investmentUsd} crypto=$${ctx.capital.cryptoUsd}`)
  }
  if (ctx.topOpportunities.length) {
    lines.push('TOP OPPORTUNITIES:')
    for (const o of ctx.topOpportunities) {
      lines.push(`- ${o.title} (${o.platform}) EV $${o.expectedValueUsd} EV/h $${o.evPerHumanHourUsd ?? '?'}`)
    }
  }
  lines.push('RULES: distinguish FACT (from state above) vs INFERENCE vs RECOMMENDATION vs UNKNOWN. Never invent rewards, probabilities, or payouts.')
  return lines.join('\n')
}

export interface AiSendResult {
  response: CopilotChatResponse
  usedContext: boolean
}

/** Send a message through the canonical path (OAR provider router). */
export async function sendAiMessage(
  message: string,
  history: ChatMessage[] = [],
  opts: { taskType?: string; includeState?: boolean } = {},
): Promise<AiSendResult> {
  const includeState = opts.includeState !== false
  let finalMessage = message
  let usedContext = false
  if (includeState) {
    try {
      const ctx = await withTimeout(buildCanonicalContext(), 9000, null)
      if (ctx) {
        finalMessage = `${renderContextPrompt(ctx)}\n\nUSER QUESTION: ${message}`
        usedContext = true
      }
    } catch {
      usedContext = false
    }
  }
  const response = await sendChatMessage(finalMessage, history, opts.taskType ?? 'chat')
  return { response, usedContext }
}

/** Execute a tool action behind an approval card. */
export async function executeAiTool(
  action: string,
  params: Record<string, unknown> = {},
): Promise<{ status: string; result: unknown }> {
  return executeCommand(action, params)
}

/** Persistent single conversation (localStorage). */
export function loadHistory(): ChatMessage[] {
  try {
    const raw = localStorage.getItem(HISTORY_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed.slice(-MAX_HISTORY) : []
  } catch {
    return []
  }
}

export function saveHistory(history: ChatMessage[]): void {
  try {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(history.slice(-MAX_HISTORY)))
  } catch {
    /* storage full or unavailable — non-fatal */
  }
}

export function clearHistory(): void {
  try {
    localStorage.removeItem(HISTORY_KEY)
  } catch {
    /* noop */
  }
}
