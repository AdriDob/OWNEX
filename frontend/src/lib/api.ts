import type { OrionContext } from '@/types'

const BASE = '/api'

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

// ── Auth API (no token needed) ──

export async function login(deviceId: string, deviceInfo?: string) {
  return api.post<{ session: any }>('/auth/login', { device_id: deviceId, device_info: deviceInfo }, true)
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
  return api.get<{ accounts: PlatformAccount[] }>('/opportunity_intelligence/identity/accounts')
}

export async function storePlatformCredentials(provider: string, email: string, token: string) {
  return api.post('/opportunity_intelligence/identity/store', { provider, email, token })
}

export async function removePlatformAccount(provider: string) {
  return api.post(`/opportunity_intelligence/identity/remove/${provider}`, {})
}

export async function getPlatformStatus(provider: string) {
  return api.get(`/opportunity_intelligence/identity/status/${provider}`)
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
