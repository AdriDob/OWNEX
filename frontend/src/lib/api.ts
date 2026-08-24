import type { OrionContext } from '@/types'
import { API_BASE } from '@/lib/backend'

const BASE = API_BASE

// ── Auth ──

const AUTH_KEY = 'CATEYE-token'
const SESSION_EXPIRES_KEY = 'CATEYE-session-expires'

export function getToken(): string | null {
  try {
    return localStorage.getItem(AUTH_KEY)
  } catch {
    return null
  }
}

export function setToken(token: string) {
  localStorage.setItem(AUTH_KEY, token)
}

export function clearToken() {
  localStorage.removeItem(AUTH_KEY)
}

export function setSessionExpiry(expiresAt: string) {
  localStorage.setItem(SESSION_EXPIRES_KEY, expiresAt)
}

export function getSessionExpiry(): string | null {
  try {
    return localStorage.getItem(SESSION_EXPIRES_KEY)
  } catch {
    return null
  }
}

export function clearSessionExpiry() {
  localStorage.removeItem(SESSION_EXPIRES_KEY)
}

export function clearSession() {
  clearToken()
  clearSessionExpiry()
  // Purge the httpOnly session cookie server-side (best effort, no await)
  void fetch(`${BASE}/auth/logout`, { method: 'POST', credentials: 'include' }).catch(() => undefined)
}

export function isSessionExpired(): boolean {
  const expiresAt = getSessionExpiry()
  if (!expiresAt) return false
  const timestamp = new Date(expiresAt).getTime()
  if (Number.isNaN(timestamp)) return false
  return Date.now() >= timestamp
}

export function isSessionValid(): boolean {
  return !!getToken() && !isSessionExpired()
}

// ── Error class ──

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

// ── Loading tracker (simple ref counter) ──

type LoadingListener = (loading: boolean) => void
const loadingListeners: LoadingListener[] = []

let _activeRequests = 0

function notifyLoading() {
  const loading = _activeRequests > 0
  for (const fn of loadingListeners) fn(loading)
}

export function onLoadingChange(fn: LoadingListener) {
  loadingListeners.push(fn)
  return () => {
    const idx = loadingListeners.indexOf(fn)
    if (idx >= 0) loadingListeners.splice(idx, 1)
  }
}

// ── Core request ──

export interface RequestOptions {
  method?: string
  body?: unknown
  params?: Record<string, string | number | boolean | undefined | null>
  skipAuth?: boolean
}

async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, params, skipAuth } = opts

  let url = `${BASE}${path}`
  if (params) {
    const search = new URLSearchParams()
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== null) search.set(k, String(v))
    }
    const qs = search.toString()
    if (qs) url += `?${qs}`
  }

  const headers: Record<string, string> = {}
  if (body) headers['Content-Type'] = 'application/json'

  const token = getToken()
  if (token && !skipAuth) {
    headers['Authorization'] = `Bearer ${token}`
  }

  _activeRequests++
  notifyLoading()

  try {
    const res = await fetch(url, {
      method,
      headers,
      credentials: 'include',
      body: body ? JSON.stringify(body) : undefined,
    })

    if (res.status === 401) {
      clearSession()
      window.dispatchEvent(new CustomEvent('auth:unauthorized'))
      throw new ApiError(401, 'Sesión expirada. Reautenticación requerida.')
    }

    if (!res.ok) {
      const text = await res.text().catch(() => '')
      throw new ApiError(res.status, text || `HTTP ${res.status}`)
    }

    // Handle 204 No Content
    if (res.status === 204) return undefined as T

    return res.json()
  } catch (e) {
    if (e instanceof ApiError) throw e
    if (e instanceof TypeError && (e as Error).message === 'Failed to fetch') {
      throw new ApiError(0, 'No se pudo conectar con el servidor')
    }
    throw e
  } finally {
    _activeRequests--
    notifyLoading()
  }
}

// ── Public API helpers ──

export const api = {
  get: <T>(path: string, params?: Record<string, string | number | boolean | undefined | null>) =>
    request<T>(path, { params }),

  post: <T>(path: string, body?: unknown, skipAuth?: boolean) =>
    request<T>(path, { method: 'POST', body, skipAuth }),

  put: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'PUT', body }),

  patch: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'PATCH', body }),

  delete: <T>(path: string) =>
    request<T>(path, { method: 'DELETE' }),
}

import type { LoginResponse, ErrorResponse } from '@/types'

// ── Additional types for API responses ──

interface RevenueSummary {
  success: boolean;
  total_payout?: number;
}

interface SubmissionsResponse {
  submissions: SubmissionRecord[];
  total: number;
}

interface FindingsResponse {
  items: FindingItem[];
  total: number;
}

// ── Auth API (no token needed) ──

export async function login(deviceId: string, deviceInfo?: string) {
  return api.post<{ session: LoginResponse }>('/auth/login', { device_id: deviceId, device_info: deviceInfo }, true)
}

export async function checkLicense() {
  return api.get<{ valid: boolean; reason?: string }>('/license/status', undefined)
}

export async function activateLicense(key: string) {
  return api.post<{ status: string; key: string }>('/license/activate', { key }, true)
}

// ── Platform Connections / Identity ──

export interface PlatformAccount {
  provider: string
  connected: boolean
  username?: string
  email?: string
  earnings?: number
  pending?: number
  last_sync?: string
  created_at?: string
  has_credentials?: boolean
  last_checked?: string
  session_state?: string
  health_status?: string
}

export async function getPlatformAccounts() {
  return api.get<{ accounts: PlatformAccount[] }>('/opportunity/identity/accounts')
}

export async function storePlatformCredentials(provider: string, email: string, token: string) {
  return api.post('/opportunity/identity/store', { provider, email, token })
}

export async function removePlatformAccount(provider: string) {
  return api.post(`/opportunity/identity/remove/${provider}`, {})
}

export async function getPlatformStatus(provider: string) {
  return api.get(`/opportunity/identity/status/${provider}`)
}

// ── Bank / Payout Accounts ──

export interface PayoutAccount {
  id: string
  connected: boolean
  bank_name?: string
  account_type?: string
  last_four?: string
  currency?: string
  country?: string
  withdrawable?: number
  pending?: number
  total_withdrawn?: number
  type?: string
  label?: string
  is_default?: boolean
  network?: string
}

export async function getPayoutAccounts() {
  return api.get<{ accounts: PayoutAccount[] }>('/connections/payout-accounts')
}

export async function getWithdrawalHistory() {
  return api.get<{ withdrawals: Withdrawal[] }>('/connections/withdrawals')
}

export interface Withdrawal {
  id: string
  amount: number
  currency: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  destination: string
  created_at: string
  completed_at?: string
}

// ── Submission History ──

export interface SubmissionRecord {
  id: number
  report_id: number
  platform: string
  external_id?: string
  status: string
  reward?: number
  submitted_at: string
  last_update?: string
}

export async function getSubmissionHistory(params?: { limit?: number; platform?: string; status?: string }) {
  return api.get<{ submissions: SubmissionRecord[]; total: number }>('/reports/submissions', params as any)
}

// ── Revenue Metrics ──

export interface RevenueMetricsData {
  payout_summary: {
    total_payout: number
    pending_total: number
    avg_payout: number
    by_platform: Record<string, number>
    by_currency: Record<string, number>
  }
  monthly_revenue: { month: string; total: number; count: number }[]
  roi_by_program: { program: string; platforms: string[]; total_payout: number; count: number }[]
  roi_by_vuln_type: { vuln_type: string; total_programs: number; total_payout: number; count: number; avg_payout: number }[]
  finding_pipeline: {
    findings: { total: number; confirmed: number; rejected: number; open: number; confirmation_rate: number }
    submissions: { total: number; accepted: number; rejected: number; pending: number; acceptance_rate: number }
  }
  findings_by_type: { vuln_type: string; total: number; confirmed: number; rejected: number; confirmation_rate: number }[]
  acceptance_rate: Record<string, { accepted: number; total: number; acceptance_rate: number }>
  time_metrics: { avg_days_to_acceptance: number | null; acceptance_samples: number; avg_days_to_payout: number | null; payout_samples: number }
}

export async function getRevenueMetrics(): Promise<RevenueMetricsData> {
  // Aggregate from multiple endpoints
  const [summaryRes, submissionRes, findingRes] = await Promise.allSettled([
    api.get<RevenueSummary>('/revenue/summary'),
    api.get<SubmissionsResponse>('/reports/submissions'),
    api.get<FindingsResponse>('/findings'),
  ])
  const summary: RevenueSummary = summaryRes.status === 'fulfilled' ? summaryRes.value : { success: false }
  const subs: SubmissionsResponse = submissionRes.status === 'fulfilled' ? submissionRes.value : { submissions: [], total: 0 }
  const finds: FindingsResponse = findingRes.status === 'fulfilled' ? findingRes.value : { items: [], total: 0 }
  const submissions = subs.submissions || []
  const findings = finds.items || []

  const accepted = submissions.filter(s => s.status === 'accepted')
  const rejected = submissions.filter(s => s.status === 'rejected')
  const pending = submissions.filter(s => s.status === 'pending' || s.status === 'submitted')
  const totalPayout = summary.total_payout || 0

  const byPlatform: Record<string, number> = {}
  submitted_total: for (const s of submissions) {
    if (s.reward) {
      byPlatform[s.platform] = (byPlatform[s.platform] || 0) + s.reward
    }
  }

  const platformAcceptance: Record<string, { accepted: number; total: number }> = {}
  for (const s of submissions) {
    if (!platformAcceptance[s.platform]) platformAcceptance[s.platform] = { accepted: 0, total: 0 }
    platformAcceptance[s.platform].total++
    if (s.status === 'accepted') platformAcceptance[s.platform].accepted++
  }

  const acceptanceRate: Record<string, { accepted: number; total: number; acceptance_rate: number }> = {}
  for (const [p, v] of Object.entries(platformAcceptance)) {
    acceptanceRate[p] = { ...v, acceptance_rate: v.total > 0 ? v.accepted / v.total : 0 }
  }

  return {
    payout_summary: {
      total_payout: totalPayout,
      pending_total: pending.reduce((s, p) => s + (p.reward || 0), 0),
      avg_payout: accepted.length > 0 ? accepted.reduce((s, a) => s + (a.reward || 0), 0) / accepted.length : 0,
      by_platform: byPlatform,
      by_currency: { USD: totalPayout },
    },
    monthly_revenue: [],
    roi_by_program: [],
    roi_by_vuln_type: [],
    finding_pipeline: {
      findings: {
        total: finds.total,
        confirmed: findings.filter(f => (f as any).status === 'confirmed').length,
        rejected: findings.filter(f => (f as any).status === 'rejected').length,
        open: findings.filter(f => (f as any).status === 'open' || (f as any).status === 'pending').length,
        confirmation_rate: finds.total > 0 ? findings.filter(f => (f as any).status === 'confirmed').length / finds.total : 0,
      },
      submissions: {
        total: submissions.length,
        accepted: accepted.length,
        rejected: rejected.length,
        pending: pending.length,
        acceptance_rate: submissions.length > 0 ? accepted.length / submissions.length : 0,
      },
    },
    findings_by_type: [],
    acceptance_rate: acceptanceRate,
    time_metrics: {
      avg_days_to_acceptance: null,
      acceptance_samples: accepted.length,
      avg_days_to_payout: null,
      payout_samples: accepted.length,
    },
  }
}

// ── System Timeline Calendar ──

export interface TimelineEvent {
  event_type: string
  timestamp: string
  source: string
  description: string
  target_id?: number
  target_name?: string
  report_title?: string
  finding_id?: number
  confidence?: number
  metadata?: Record<string, any>
}

export interface TimelineResponse {
  events: TimelineEvent[]
  total_events: number
  generated_at: string
}

export async function getTimeline(params?: { target_id?: number; limit?: number; offset?: number; event_type?: string }) {
  return api.get<TimelineResponse>('/system/timeline', params as any)
}

// ── Platform Sync ──

export interface PlatformStatus {
  name: string
  connected: boolean
  username?: string
  earnings?: number
  pending?: number
  last_sync?: string
}

export async function getPlatformsStatus() {
  return api.get<{ platforms: PlatformStatus[] }>('/platforms/status')
}

// ── Bank Account ──

export interface BankAccount {
  connected: boolean
  bank_name?: string
  last_four?: string
  currency?: string
  withdrawable?: number
  pending?: number
}

export async function getBankAccount() {
  return api.get<BankAccount>('/economic/bank-account')
}

// ── Orion Context ──

export async function getOrionContext(refresh = false) {
  return api.get<OrionContext>('/orion/context/system', { refresh: refresh || undefined })
}

// ── Targets ──

export interface TargetItem {
  id: number
  name: string
  domain: string
  endpoint_count: number
  finding_count: number
  confirmed_findings: number
  estimated_payout: number
  roi: number
  risk_score: number
  opportunity_score: number
  competition_score: number
  freshness_score: number
  created_at: string | null
}

export async function getTargets(params?: {
  skip?: number; limit?: number; sort_by?: string; sort_order?: string; search?: string
}) {
  return api.get<{ items: TargetItem[]; total: number }>('/targets', params as any)
}

export async function getTarget(targetId: number) {
  return api.get<any>(`/targets/${targetId}`)
}

export interface EVTarget {
  target_id: number
  target_name: string
  expected_value: number
  estimated_reward: number
  acceptance_probability: number
  confidence: number
  priority_score: number
  attack_plan: { phases: string[]; estimated_hours: number } | null
}

export async function getEVRankedTargets(limit = 20): Promise<{ ranked: EVTarget[]; total_targets: number }> {
  return api.get<{ ranked: EVTarget[]; total_targets: number }>(`/targets/ev-ranking?limit=${limit}`)
}

// ── Findings ──

export interface FindingItem {
  id: number
  target_id: number
  endpoint_id: number | null
  title: string
  severity: string
  description: string | null
  payout: number
  target_name: string
  endpoint_path: string
  created_at: string | null
}

export async function getFindings(params?: {
  target_id?: number; endpoint_id?: number; skip?: number; limit?: number
  sort_by?: string; sort_order?: string; search?: string
}) {
  return api.get<{ items: FindingItem[]; total: number }>('/findings', params as any)
}

// ── Pipeline ──

export interface PipelineResponse {
  detected: FindingItem[]
  validated: FindingItem[]
  confirmed: FindingItem[]
  reported: FindingItem[]
}

export async function getPipeline() {
  return api.get<PipelineResponse>('/pipeline')
}

// ── Reports ──

export interface ReportItem {
  id: number
  program: string
  target: string
  vulnerability: string
  severity: string
  status: string
  estimated_reward: number
  confirmed_reward: number
  currency: string
  evidence_count: number
  summary: string
  created_at: string | null
  updated_at: string | null
}

export async function getReports(params?: {
  limit?: number; offset?: number; status?: string; search?: string
  sort_by?: string; sort_order?: string
}) {
  return api.get<{ items: ReportItem[]; total: number }>('/reports', params as any)
}

export async function getReportStats() {
  return api.get<{ total: number; status_counts: Record<string, number>; paid_count: number; total_rewards: number; estimated_rewards: number }>('/reports/stats')
}

// ── Attack / Hot Paths ──

export interface HotPathItem {
  path: string
  method: string
  target_id: number | null
  risk_score: number
  vector: string
  ownership_risk: boolean
  reason: string
  suggestions: string[]
}

export interface AttackDecisionResponse {
  summary: string
  high_value_targets: HotPathItem[]
  attack_vectors: Array<{ vector: string; endpoints: string[]; count: number }>
  ownership_risks: HotPathItem[]
  manual_test_suggestions: string[]
}

export async function getAttackDecision(params?: { target_id?: number; limit?: number }) {
  return api.get<AttackDecisionResponse>('/attack/decision', params as any)
}

// ── Verdicts ──

export interface VerdictItem {
  id: number
  hot_path_id: string | null
  status: string
  confidence: number
  reproducibility_score: number
  reason: string | null
  created_at: string | null
}

export async function getVerdicts(params?: { status?: string; limit?: number; target_id?: number; confidence_min?: number }) {
  return api.get<VerdictItem[]>('/verdicts', params as any)
}

// ── System ──

export async function getSystemHealth() {
  return api.get<any>('/system/health')
}

export async function getSystemDefinitions() {
  return api.get<{
    platforms: { id: string; name: string; color: string; url: string }[]
    tools: { id: string; name: string; desc: string }[]
    osint_services: { id: string; name: string; free: boolean; url: string }[]
    languages: { id: string; name: string }[]
    event_types: string[]
  }>('/system/definitions')
}

export async function getOverview() {
  return api.get<any>('/overview')
}

// ── Findings Actions ──

export async function updateFindingStatus(id: number, status: string) {
  return api.put<any>(`/findings/${id}/status`, { status })
}

export async function regenerateNarrative(id: number) {
  return api.post<{ narrative: string }>(`/findings/${id}/regen-narrative`)
}

// ── Report Submission ──

export async function submitReport(reportId: number, platform: string) {
  return api.post<{ success: boolean; external_id?: string; url?: string }>(
    `/reports/${reportId}/submit`, { platform }
  )
}

export async function getRewardLearning() {
  return api.get<any>('/reports/reward-learning')
}

// ── Evidence ──

export async function uploadEvidence(findingId: number, file: File) {
  const form = new FormData()
  form.append('file', file)
  form.append('finding_id', String(findingId))
  const token = getToken()
  const res = await fetch(`/api/evidence/upload`, {
    method: 'POST',
    headers: token ? { 'Authorization': `Bearer ${token}` } : {},
    body: form,
  })
  if (!res.ok) throw new ApiError(res.status, 'Error al subir evidencia')
  return res.json()
}

// ── Scans ──

export async function triggerScan(targetId: number, mode: string = 'quick') {
  return api.post<{ scan_id: number; status: string }>(`/targets/${targetId}/scan`, { mode })
}

// ── Assistant / Copilot ──

export async function getAssistantChat(message: string, history?: { role: string; content: string }[]) {
  return api.post<{ response: string; engine: string }>('/assistant/orion-chat', { message, history })
}

// ── ZAP Integration ──

export interface ZapAlertItem {
  alert: string
  risk: string
  risk_score: number
  confidence: string
  url: string
  param: string
  description: string
  solution: string
  cwe_id: string
  plugin_id: string
  evidence: string
  is_passive: boolean
}

export interface ZapHypothesisItem {
  id: string
  vulnerability_type: string
  target_id: number
  target_name: string
  endpoint: Record<string, any>
  likelihood: number
  impact: number
  confidence: number
  priority_score: number
  evidence: string[]
  reasoning: string
  suggested_actions: string[]
  source: string
  vector: string
  what_is_this: string
  why_suspected: string
  real_world_impact: string
  how_to_verify: string[]
  estimated_difficulty: string
  estimated_time_minutes: number
  estimated_reward_range: string
}

export async function zapHealth() {
  return api.get<{ running: boolean; version?: string; error?: string }>('/zap/health')
}

export async function zapSpider(targetUrl: string, maxChildren = 10) {
  return api.post<{ status: string; urls_found: string[]; url_count: number; scan_id: string }>(
    '/zap/spider', { target_url: targetUrl, max_children: maxChildren }
  )
}

export async function zapPassiveScan(targetUrl: string) {
  return api.post<{ status: string; target_url: string; alerts: ZapAlertItem[]; alert_count: number }>(
    '/zap/passive-scan', { target_url: targetUrl }
  )
}

export async function zapGetAlerts(targetUrl: string, riskLevel?: string) {
  const params = riskLevel ? `?risk_level=${riskLevel}` : ''
  return api.post<{ target_url: string; alerts: ZapAlertItem[]; alert_count: number }>(
    `/zap/alerts${params}`, { target_url: targetUrl }
  )
}

export async function zapGetTechnologies(targetUrl: string) {
  return api.post<{ target_url: string; technologies: string[] }>(
    '/zap/technologies', { target_url: targetUrl }
  )
}

export async function zapGenerateHypotheses(targetId: number, targetUrl: string) {
  return api.post<{ status: string; target_url: string; hypotheses: ZapHypothesisItem[]; total: number }>(
    `/zap/hypotheses/${targetId}`, { target_url: targetUrl }
  )
}

// ── Verification Guide ──

export interface VerificationStepItem {
  id: string
  label: string
  description: string
  status: 'pending' | 'in_progress' | 'completed' | 'failed'
  type: 'check' | 'command' | 'screenshot' | 'note'
}

export async function saveVerificationResult(
  hypothesisId: string,
  result: 'confirmed' | 'rejected' | 'inconclusive',
  notes: string,
  stepStatuses: Record<string, string>,
) {
  return api.post<{ success: boolean; message: string }>('/validation/record', {
    hypothesis_id: hypothesisId,
    result,
    notes,
    step_statuses: stepStatuses,
  })
}

export async function assistantStreamChat(
  message: string,
  history: { role: string; content: string }[],
  onToken: (token: string) => void,
  context?: string,
  signal?: AbortSignal,
): Promise<void> {
  const token = getToken()
  const res = await fetch('/api/assistant/chat/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ message, history, context }),
    signal,
  })
  if (!res.ok) throw new ApiError(res.status, 'Error al conectar con el asistente')
  const reader = res.body?.getReader()
  if (!reader) throw new Error('No se pudo leer el stream')
  const decoder = new TextDecoder()
  let buffer = ''
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = line.slice(6).trim()
        if (data === '[DONE]') return
        try {
          const parsed = JSON.parse(data)
          if (parsed.token) onToken(parsed.token)
        } catch { /* ignore partial */ }
      }
    }
  }
}

// ── Crypto API ──

export async function getCryptoWallets() {
  return api.get<{ wallets: any[]; summary: any }>('/crypto/wallets')
}

export async function getCryptoWallet(walletId: string) {
  return api.get<any>(`/crypto/wallets/${walletId}`)
}

export async function syncCryptoWallet(walletId: string) {
  return api.post<any>(`/crypto/wallets/${walletId}/sync`)
}

export async function syncAllCryptoWallets() {
  return api.post<any>('/crypto/sync-all')
}

export async function getCryptoSummary() {
  return api.get<any>('/crypto/summary')
}

// ── Accounts Hub API ──

export async function getAccountsHub() {
  return api.get<any>('/accounts-hub/status')
}

export async function getSyncHistory() {
  return api.get<any[]>('/accounts-hub/sync-history')
}

// ── Integration Center ──

export interface IntegrationItem {
  name: string
  category: string
  status: string
  description: string
  icon: string
  last_sync: string | null
  latency_ms: number | null
  error: string | null
  permissions: string[]
  tags: string[]
  checked_at: string
}

export interface IntegrationsSummary {
  total: number
  by_status: Record<string, number>
  by_category: Record<string, number>
  categories: string[]
  integrations: IntegrationItem[]
}

export async function getIntegrations() {
  return api.get<IntegrationsSummary>('/core/integrations')
}

export async function testIntegration(name: string) {
  return api.post<{ name: string; status: string; error: string | null; checked_at: string }>(`/core/integrations/${name}/test`)
}

export async function getIntegrationStatus(name: string) {
  return api.get<IntegrationItem>(`/core/integrations/${name}`)
}

// ── Investment API ──

export interface InvestmentStatus {
  total_capital: number
  deployed: number
  available: number
  paused: boolean
  drawdown_protection: boolean
  active_strategies: number
  strategies: Record<string, {
    id: string
    paused: boolean
    total_deployed: number
    risk_level: string
  }>
  summary: {
    total_trades: number
    win_rate: number
    sharpe: number
    max_drawdown_pct: number
    total_pnl: number
    total_pnl_pct: number
    in_drawdown: boolean
  }
}

export interface StrategyAllocation {
  strategy_id: string
  allocated_usd: number
  deployed_usd: number
  available_usd: number
  pnl_usd: number
  pnl_pct: number
  roi_pct: number
}

export interface StrategyDetail {
  profile: {
    id: string
    name: string
    type: string
    risk_level: string
    max_allocation_pct: number
    expected_roi_pct: number
    description: string
    tags: string[]
  }
  allocation: StrategyAllocation
  risk_metrics: {
    sharpe_ratio: number
    win_rate: number
    profit_factor: number
    total_trades: number
    winning_trades: number
    losing_trades: number
    current_drawdown_pct: number
    max_drawdown_pct: number
    avg_win_pct: number
    avg_loss_pct: number
    is_drawdown: boolean
    should_pause: boolean
    is_healthy: boolean
    consecutive_losses: number
  }
  paused: boolean
}

export interface ConsolidateMetrics {
  total_trades: number
  winning_trades: number
  total_pnl: number
  win_rate: number
  strategies: Record<string, Record<string, number | boolean>>
  snapshots_count: number
}

export interface PnLPoint {
  date: string
  pnl: number
}

export async function getInvestmentStatus() {
  return api.get<{ success: boolean; status: InvestmentStatus }>('/investment/status')
}

export async function getInvestmentSnapshot() {
  return api.get<{ success: boolean; snapshot: any }>('/investment/snapshot')
}

export async function getInvestmentStrategies() {
  return api.get<{ success: boolean; strategies: any[]; total: number }>('/investment/strategies')
}

export async function getStrategyDetail(id: string) {
  return api.get<{ success: boolean; strategy: StrategyDetail }>(`/investment/strategies/${id}`)
}

export async function deployStrategy(id: string, amount: number) {
  return api.post<{ success: boolean; result: any }>(`/investment/strategies/${id}/deploy`, { amount })
}

export async function pauseStrategy(id: string) {
  return api.post<{ success: boolean }>(`/investment/strategies/${id}/pause`)
}

export async function resumeStrategy(id: string) {
  return api.post<{ success: boolean }>(`/investment/strategies/${id}/resume`)
}

export async function getInvestmentMetrics() {
  return api.get<{ success: boolean; metrics: ConsolidateMetrics; pnl_chart: PnLPoint[] }>('/investment/metrics')
}

export async function getAllocation() {
  return api.get<{ success: boolean; allocation: any; config: any }>('/investment/allocation')
}

export async function getExposure() {
  return api.get<{ success: boolean; exposure: any }>('/investment/exposure')
}

export async function getInvestmentEvents(limit = 50) {
  return api.get<{ success: boolean; events: any[] }>(`/investment/events?limit=${limit}`)
}

export async function allocatePayout(amount: number, source = '') {
  return api.post<{ success: boolean; allocation: any }>('/investment/allocation/allocate-payout', { amount, source })
}

export async function updateInvestmentCapital(total_usd: number) {
  return api.post<{ success: boolean }>('/investment/allocation/update-capital', { total_usd })
}

export async function pauseAllInvestments() {
  return api.post<{ success: boolean }>('/investment/pause')
}

export async function resumeAllInvestments() {
  return api.post<{ success: boolean }>('/investment/resume')
}

export async function activateMaxRevenue() {
  return api.post<{ success: boolean; result: any }>('/investment/max-revenue')
}

export async function updateInvestmentConfig(config: Record<string, any>) {
  return api.post<{ success: boolean; config: any }>('/investment/config', config)
}

export async function getCcxtInfo(exchange = 'binance') {
  return api.get<{ success: boolean; exchange: string; info: any }>(`/investment/ccxt/info?exchange=${exchange}`)
}

export async function connectCcxt(exchange: string, api_key: string, api_secret: string) {
  return api.post<{ success: boolean; connected: boolean }>('/investment/ccxt/connect', { exchange, api_key, api_secret })
}

export async function getCcxtBalance(exchange = 'binance') {
  return api.get<{ success: boolean; balance: any }>(`/investment/ccxt/balance?exchange=${exchange}`)
}

export async function getAcceptanceSummary() {
  return api.get<{
    total_observations: number; accepted: number; rejected: number; acceptance_rate: number
    platforms: string[]; adapted_weights: Record<string, number>; profiles: Record<string, any>
    weight_deltas: Record<string, number>
  }>('/reports/acceptance/summary')
}

export async function predictAcceptance(findingId: number, platform = 'hackerone') {
  return api.get<{
    finding_id: number; prediction: {
      probability: number; platform: string; confidence: string
      weak_dimensions: { dimension: string; current: number; accepted_avg: number; gap: number }[]
      recommendations: string[]; score: number; min_accepted_score: number
    }; quality_score: any
  }>(`/reports/acceptance/predict?finding_id=${findingId}&platform=${platform}`)
}

export async function recordAcceptanceOutcome(submissionId: number) {
  return api.post<any>(`/reports/acceptance/record-outcome?submission_id=${submissionId}`)
}

export async function getAcceptanceProfiles() {
  return api.get<{ profiles: Record<string, any>; total_platforms: number }>('/reports/acceptance/profiles')
}

export async function getAcceptancePlatformProfile(platform: string) {
  return api.get<any>(`/reports/acceptance/profiles/${platform}`)
}

export async function getAcceptanceObservations(limit = 50) {
  return api.get<{ observations: any[]; total: number }>(`/reports/acceptance/observations?limit=${limit}`)
}

export async function syncAcceptanceFromDb() {
  return api.post<{ synced: number; summary: any }>('/reports/acceptance/sync')
}

// ─── Stocks & Options ───

export async function getAlpacaInfo() {
  return api.get<{ success: boolean; adapter: string; connected: boolean }>('/investment/stocks/algopaca')
}

export async function connectAlpaca(api_key: string, secret_key: string, base_url?: string) {
  return api.post<{ success: boolean; connected: boolean }>('/investment/stocks/algopaca/connect', { api_key, secret_key, base_url })
}

export async function getAlpacaAccount() {
  return api.get<{ success: boolean; account: any }>('/investment/stocks/algopaca/account')
}

export async function getAlpacaPositions() {
  return api.get<{ success: boolean; positions: any[] }>('/investment/stocks/algopaca/positions')
}

export async function placeAlpacaOrder(symbol: string, side: string, qty: number, order_type?: string, take_profit?: number, stop_loss?: number) {
  return api.post<{ success: boolean; result: any }>('/investment/stocks/algopaca/order', { symbol, side, qty, order_type, take_profit, stop_loss })
}

export async function getAlpacaMarketData(symbol: string) {
  return api.get<{ success: boolean; data: any }>(`/investment/stocks/algopaca/market-data?symbol=${symbol}`)
}

export async function getAlpacaOptionsChain(underlying: string) {
  return api.get<{ success: boolean; options: any[] }>(`/investment/stocks/algopaca/options-chain?underlying=${underlying}`)
}

export async function getIbkrInfo() {
  return api.get<{ success: boolean; adapter: string; connected: boolean }>('/investment/stocks/ibkr')
}

export async function connectIbkr(host?: string, port?: number, client_id?: number) {
  return api.post<{ success: boolean; connected: boolean }>('/investment/stocks/ibkr/connect', { host, port, client_id })
}

export async function getIbkrAccount() {
  return api.get<{ success: boolean; account: any }>('/investment/stocks/ibkr/account')
}

export async function getIbkrPositions() {
  return api.get<{ success: boolean; positions: any[] }>('/investment/stocks/ibkr/positions')
}

export async function placeIbkrOrder(symbol: string, side: string, qty: number, order_type?: string, sec_type?: string, strike?: number, right?: string) {
  return api.post<{ success: boolean; result: any }>('/investment/stocks/ibkr/order', { symbol, side, qty, order_type, sec_type, strike, right })
}

// ─── DeFi Yield ───

export async function getAaveInfo() {
  return api.get<{ success: boolean; adapter: string; connected: boolean }>('/investment/defi/aave/info')
}

export async function connectAave(chain?: string) {
  return api.post<{ success: boolean; connected: boolean }>('/investment/defi/aave/connect', { chain })
}

export async function getAaveSupplyApy(asset?: string) {
  return api.get<{ success: boolean; data: any }>(`/investment/defi/aave/supply-apy?asset=${asset}`)
}

export async function getAaveTopAssets() {
  return api.get<{ success: boolean; assets: any[] }>('/investment/defi/aave/top-assets')
}

export async function getMorphoInfo() {
  return api.get<{ success: boolean; adapter: string; connected: boolean }>('/investment/defi/morpho/info')
}

export async function connectMorpho(chain?: string) {
  return api.post<{ success: boolean; connected: boolean }>('/investment/defi/morpho/connect', { chain })
}

export async function getMorphoMarketApy(market_id: string) {
  return api.get<{ success: boolean; data: any }>(`/investment/defi/morpho/market-apy?market_id=${market_id}`)
}

export async function getMorphoTopMarkets() {
  return api.get<{ success: boolean; markets: any[] }>('/investment/defi/morpho/top-markets')
}

export async function getPendleInfo() {
  return api.get<{ success: boolean; adapter: string; connected: boolean }>('/investment/defi/pendle/info')
}

export async function connectPendle(chain?: string) {
  return api.post<{ success: boolean; connected: boolean }>('/investment/defi/pendle/connect', { chain })
}

export async function getPendleYieldOpportunities() {
  return api.get<{ success: boolean; opportunities: any[] }>('/investment/defi/pendle/yield-opportunities')
}

export async function getPendlePtYield(market_id: string) {
  return api.get<{ success: boolean; data: any }>(`/investment/defi/pendle/pt-yield?market_id=${market_id}`)
}

export async function getLidoInfo() {
  return api.get<{ success: boolean; adapter: string; connected: boolean }>('/investment/defi/lido/info')
}

export async function connectLido(chain?: string) {
  return api.post<{ success: boolean; connected: boolean }>('/investment/defi/lido/connect', { chain })
}

export async function getLidoStakingApy() {
  return api.get<{ success: boolean; data: any }>('/investment/defi/lido/staking-apy')
}

export async function getLidoProtocolMetrics() {
  return api.get<{ success: boolean; metrics: any }>('/investment/defi/lido/protocol-metrics')
}

// ─── Polymarket Strategies ───

export async function getPolymarketStrategies() {
  return api.get<{ success: boolean; strategies: any }>('/investment/polymarket/strategies')
}

export async function runPolymarketStrategy(strategy_name: string) {
  return api.post<{ success: boolean; result: any }>(`/investment/polymarket/strategies/${strategy_name}/run`)
}

export async function getPolymarketDiagnostic() {
  return api.get<{ success: boolean; diagnostic: any }>('/investment/polymarket/strategies/diagnostic')
}
