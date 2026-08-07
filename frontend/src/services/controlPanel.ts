import { api } from '@/lib/api'

// ── Mega Fast Mode ──

export interface MegaFastStatus {
  success: boolean
  active?: boolean
  enabled?: boolean
  status?: string
  started_at?: string
  target_weekly_usd?: number
  min_confidence_threshold?: number
  daily_plan?: string[]
}

export async function getMegaFastStatus(): Promise<MegaFastStatus> {
  return api.get<MegaFastStatus>('/api/mega-fast/status').catch(() => ({}))
}

export async function activateMegaFast(): Promise<MegaFastStatus> {
  return api.post<MegaFastStatus>('/api/mega-fast/activate', {})
}

export async function deactivateMegaFast(): Promise<MegaFastStatus> {
  return api.post<MegaFastStatus>('/api/mega-fast/deactivate', {})
}

// ── First-Time Mode ──

export interface FirstTimeStatus {
  success: boolean
  active?: boolean
  enabled?: boolean
  completed?: boolean
  phase?: string
  next_steps?: string[]
}

export async function getFirstTimeStatus(): Promise<FirstTimeStatus> {
  return api.get<FirstTimeStatus>('/api/first-time/status').catch(() => ({}))
}

export async function activateFirstTime(): Promise<FirstTimeStatus> {
  return api.post<FirstTimeStatus>('/api/first-time/activate', {})
}

export async function deactivateFirstTime(): Promise<FirstTimeStatus> {
  return api.post<FirstTimeStatus>('/api/first-time/deactivate', {})
}

// ── VPN / Argentina access ──

export interface VpnStatusData {
  online: boolean
  public_ip: string
  country_code: string
  country_name: string
  isp: string
  provider: string
  compatible: boolean
  reason: string
}

export interface VpnInstallInfo {
  key: string
  name: string
  url: string
  free: string
  installed: boolean
  needs_install: boolean
  install_step: string
}

export interface VpnInfo {
  success: boolean
  os?: string
  is_wsl?: boolean
  status?: VpnStatusData
  options?: Array<{ name: string; cost: string; reliability: string; extra: string; recommended?: boolean }>
  vpns?: VpnInstallInfo[]
  missing_count?: number
  missing?: string[]
  present?: string[]
  vpn_plan?: string[]
}

export async function getVpnInfo(): Promise<VpnInfo> {
  return api.get<VpnInfo>('/api/vpn/info').catch(() => ({ success: false }))
}

export async function checkVpnOutlier(): Promise<{ compatible: boolean; country?: string; country_code?: string; ip?: string; verdict?: string }> {
  return api.post('/api/vpn/check-outlier', {}).catch(() => ({ compatible: false, verdict: 'Sin conexión al API' }))
}

export async function installWindscribe(): Promise<{ success: boolean; message?: string; note?: string }> {
  return api.post('/api/vpn/install-windscribe', {}).catch(() => ({ success: false, message: 'No se pudo instalar' }))
}

export interface WindscribeConnect {
  success: boolean
  installed?: boolean
  running?: boolean
  aimed_country?: string
  next_steps?: string[]
  country_code?: string
}

export async function connectWindscribeWindows(): Promise<WindscribeConnect> {
  return api.post<WindscribeConnect>('/api/vpn/windscribe-connect', {}).catch(() => ({ success: false, next_steps: ['Error al contactar el asistente VPN.'] }))
}

// ── Obsidian ──

export interface ObsidianSyncResult {
  success: boolean
  synced?: number
  files?: string[]
  message?: string
  error?: string
}

export async function syncObsidian(): Promise<ObsidianSyncResult> {
  return api.post<ObsidianSyncResult>('/api/obsidian/sync', {}).catch(() => ({ success: false, error: 'API no disponible' }))
}

// ── Life Assistant ──

export interface LifeSnapshot {
  success: boolean
  tasks?: number
  goals?: string[]
  pending_tasks?: string[]
}

export async function getLifeSnapshot(): Promise<LifeSnapshot> {
  return api.get<LifeSnapshot>('/api/life/snapshot').catch(() => ({}))
}

export async function runLifeCycle(): Promise<LifeSnapshot> {
  return api.post<LifeSnapshot>('/api/life/cycle', {}).catch(() => ({}))
}

// ── Action Required (Notifications) ──

export interface ActionRequiredItem {
  id: string
  action_id: string
  title: string
  reason: string
  priority: string
  category: string
  created_at: string
  steps?: string[]
}

export async function getActionRequired(): Promise<ActionRequiredItem[]> {
  const res = await api.get<{ items?: ActionRequiredItem[]; actions?: ActionRequiredItem[] }>(
    '/api/investment/action-required',
  ).catch(() => null)
  return res?.items || res?.actions || []
}

export async function resolveActionRequired(id: string): Promise<{ success: boolean }> {
  return api.post<{ success: boolean }>(`/api/investment/action-required/${id}/resolve`, {}).catch(() => ({ success: false }))
}

// ── File Manager ──

export async function listUserFiles(): Promise<string[]> {
  const res = await api.get<{ files?: string[] }>('/api/files/list').catch(() => null)
  return res?.files || []
}

// ── Startup Checks ──

export interface StartupCheckResult {
  success: boolean
  checks?: Array<{ title: string; status: string; detail?: string }>
}

export async function runStartupChecks(): Promise<StartupCheckResult> {
  return api.post<StartupCheckResult>('/api/investment/startup-checks', {}).catch(() => ({}))
}

// ── Master Guide ──

export interface MasterGuideStep {
  id: string
  title: string
  action: string
  status: string
  done: boolean
}

export interface MasterGuideCategory {
  id: string
  title: string
  desc: string
  steps: MasterGuideStep[]
}

export interface MasterGuideData {
  success: boolean
  categories: MasterGuideCategory[]
  total_steps: number
  done_steps: number
  progress: number
}

export async function fetchMasterGuide(): Promise<MasterGuideData> {
  return api.get<MasterGuideData>('/api/guide/master').catch(() => ({ success: false, categories: [], total_steps: 0, done_steps: 0, progress: 0 }))
}

// ── Money Plan ──

export interface MoneyPlanData {
  success: boolean
  plan?: {
    hours_per_day?: number
    days_per_week?: number
    weekly_hours?: number
    target_weekly?: number
    priority?: string[]
  }
  projection?: {
    weekly_hours: number
    real_hours: number
    saved_hours: number
    assistant_enabled: boolean
    pulse_rate: number
    pulse_income: number
    forge_income: number
    bug_income_expect: number
    total_estimate: number
    target_weekly: number
    gap_to_target: number
  }
}

export async function fetchMoneyPlan(): Promise<MoneyPlanData> {
  return api.get<MoneyPlanData>('/api/money-plan').catch(() => ({ success: false }))
}

export async function updateMoneyPlan(payload: Record<string, unknown>): Promise<MoneyPlanData> {
  return api.post<MoneyPlanData>('/api/money-plan/update', payload).catch(() => ({ success: false }))
}

// ── Task Assistant ──

export interface TaskAssistantResult {
  success: boolean
  task_type?: string
  words?: number
  response?: string
  sections?: Array<{ title: string; body: string }>
  error?: string
}

export async function analyzeTask(task: string): Promise<TaskAssistantResult> {
  return api.post<TaskAssistantResult>('/api/task-assistant/analyze', { task }).catch(() => ({ success: false, error: 'No se pudo conectar' }))
}

// ── Dev Bounty Autopilot ──

export interface DevBountyStatus {
  success?: boolean
  active?: boolean
  auto_discover?: boolean
  auto_proposal?: boolean
  requires_validation?: boolean
  beginner_mode?: boolean
  platforms?: string[]
  ready_to_validate?: number
}

export interface DevBountyProposal {
  id: string
  title: string
  platform: string
  repo: string
  status: string
  validated: boolean
  solution_preview?: string
  verdict?: string
  user_action?: string
}

export interface DevBountyQueue {
  success: boolean
  pending?: DevBountyProposal[]
  count?: number
  workflow_note?: string
}

export async function getDevBountyStatus(): Promise<DevBountyStatus> {
  return api.get<DevBountyStatus>('/api/dev-bounty/status').catch(() => ({}))
}

export async function activateDevBounty(): Promise<DevBountyStatus> {
  return api.post<DevBountyStatus>('/api/dev-bounty/activate', {}).catch(() => ({}))
}

export async function deactivateDevBounty(): Promise<DevBountyStatus> {
  return api.post<DevBountyStatus>('/api/dev-bounty/deactivate', {}).catch(() => ({}))
}

export async function runDevBountyCycle(): Promise<{ success?: boolean; discovered?: number; proposals_ready?: number; pending_validation?: number }> {
  return api.post('/api/dev-bounty/run', {}).catch(() => ({ success: false }))
}

export async function getDevBountyQueue(): Promise<DevBountyQueue> {
  return api.get<DevBountyQueue>('/api/dev-bounty/queue').catch(() => ({ success: false }))
}

export async function validateDevBounty(proposalId: string, action: string = 'approved'): Promise<{ success: boolean }> {
  return api.post(`/api/dev-bounty/validate/${proposalId}`, { action }).catch(() => ({ success: false }))
}

export async function setDevBountyBeginnerMode(enabled: boolean): Promise<{ success: boolean; beginner_mode?: boolean }> {
  return api.post('/api/dev-bounty/beginner-mode', { enabled }).catch(() => ({ success: false }))
}

// ── Evidence Claim (for reclamos/payment disputes) ──

export interface EvidenceClaim {
  finding_id: string
  bounty_id?: string
  outcome: string
  detail: string
  timestamp_utc: string
  sha256: string
  path: string
}

export async function saveEvidenceClaim(
  findingId: string,
  data: { outcome?: string; detail?: string; bountyId?: string; extra?: Record<string, unknown> },
): Promise<EvidenceClaim> {
  return api.post<EvidenceClaim>('/api/evidence/claim', {
    finding_id: findingId,
    outcome: data.outcome ?? 'done',
    detail: data.detail ?? '',
    bounty_id: data.bountyId ?? null,
    extra: data.extra ?? {},
  }).catch(() => ({ finding_id: findingId, outcome: data.outcome ?? 'done', detail: data.detail ?? '', timestamp_utc: new Date().toISOString(), sha256: '', path: '' }))
}

// ── Profile Builder ──


export interface ProfileBuilderStatus {
  success?: boolean
  linked?: boolean
  username?: string
  has_token?: boolean
  portfolio_repo?: string
  auto_push?: boolean
  score?: number
  score_detail?: Record<string, { points: number; [key: string]: unknown }>
  audit?: Record<string, unknown>
  recommendations?: Array<{ priority: string; action: string; why: string }>
  contributions?: Array<{ kind: string; title: string; url: string; created_at: string; push?: { success?: boolean; message?: string; folder?: string; commit?: string } }>
}

export interface ProfileBuilderReadme {
  success: boolean
  username?: string
  readme?: string
}

export async function getProfileBuilderStatus(): Promise<ProfileBuilderStatus> {
  return api.get<ProfileBuilderStatus>('/api/profile-builder/status').catch(() => ({}))
}

export async function linkProfileBuilder(username: string): Promise<ProfileBuilderStatus> {
  return api.post<ProfileBuilderStatus>('/api/profile-builder/link', { username }).catch(() => ({}))
}

export async function auditProfileBuilder(): Promise<ProfileBuilderStatus> {
  return api.post<ProfileBuilderStatus>('/api/profile-builder/audit', {}).catch(() => ({}))
}

export async function setProfilePortfolioRepo(repo: string): Promise<{ success: boolean; portfolio_repo?: string; message?: string }> {
  return api.post('/api/profile-builder/portfolio-repo', { repo }).catch(() => ({ success: false }))
}

export async function setProfileAutoPush(enabled: boolean): Promise<{ success: boolean; auto_push?: boolean }> {
  return api.post('/api/profile-builder/auto-push', { enabled }).catch(() => ({ success: false }))
}

export async function getProfileBuilderRecommendations(): Promise<{ success: boolean; recommendations: Array<{ priority: string; action: string; why: string }> }> {
  return api.get('/api/profile-builder/recommendations').catch(() => ({ success: false, recommendations: [] }))
}

export async function generateProfileReadme(): Promise<ProfileBuilderReadme> {
  return api.post<ProfileBuilderReadme>('/api/profile-builder/readme', {}).catch(() => ({ success: false }))
}

export async function recordProfileContribution(kind: string, title: string, url: string): Promise<{ success: boolean; contributions?: number }> {
  return api.post('/api/profile-builder/record-contribution', { kind, title, url }).catch(() => ({ success: false }))
}

// ── Daily Task Board ──

export interface DailyTask {
  id: string
  day: number
  title: string
  detail?: string
  status?: string
  cat?: string
  link?: string
  completed_at?: string
}

export interface DailyTasksResult {
  success?: boolean
  day?: number
  started_on?: string
  tasks?: DailyTask[]
  progress?: number
  done?: number
  total?: number
  message?: string
}

export async function getDailyTasks(forceRefresh: boolean = false): Promise<DailyTasksResult> {
  return api.get<DailyTasksResult>(`/api/daily-tasks${forceRefresh ? '?force_refresh=true' : ''}`).catch(() => ({}))
}

export async function setDailyTaskStatus(taskId: string, status: string): Promise<{ success: boolean; task_id?: string; status?: string }> {
  return api.post(`/api/daily-tasks/${taskId}/status`, { status }).catch(() => ({ success: false }))
}

export async function advanceDailyTaskDay(): Promise<DailyTasksResult> {
  return api.post<DailyTasksResult>('/api/daily-tasks/advance-day', {}).catch(() => ({}))
}

export async function completeDailyTasksFromState(): Promise<DailyTasksResult> {
  return api.post<DailyTasksResult>('/api/daily-tasks/complete-done', {}).catch(() => ({}))
}

export interface FullCycleResult {
  success: boolean
  result?: Record<string, unknown>
}

export async function runFullCycle(): Promise<FullCycleResult> {
  return api.post<FullCycleResult>('/api/automation/full-cycle', {}).catch(() => ({ success: false }))
}

// ── Auto modules status ──

export interface AutoModuleInfo {
  name: string
  enabled: boolean
  stats?: Record<string, unknown>
  monthly?: Record<string, unknown>
  allocation?: Record<string, unknown>
  credentials?: Record<string, unknown>
  template?: unknown
}

export interface AutoModulesResult {
  success: boolean
  modules?: Record<string, AutoModuleInfo>
}

export async function getAutoModules(): Promise<AutoModulesResult> {
  return api.get<AutoModulesResult>('/api/automation/modules').catch(() => ({}))
}

// ── Skill Method ──

export interface SkillLevel {
  id: string
  name: string
  progress: number
  total: number
  skills: string[]
}

export interface SkillTrack {
  id: string
  icon: string
  name: string
  goal?: string
  done: number
  total: number
  levels: SkillLevel[]
}

export interface SkillSession {
  id: string
  track: string
  track_name: string
  type: string
  title: string
  notes: string
  created_at: string
}

export interface SkillMethodStatus {
  success?: boolean
  started_on?: string
  current_track?: string
  tracks?: SkillTrack[]
  sessions?: SkillSession[]
  completed?: string[]
  score?: number
  done_skills?: number
  total_skills?: number
  stats?: Record<string, number>
  message?: string
  session_types?: Record<string, string>
}

export async function getSkillMethod(): Promise<SkillMethodStatus> {
  return api.get<SkillMethodStatus>('/api/skill-method').catch(() => ({}))
}

export async function setSkillTrack(trackId: string): Promise<{ success: boolean; current_track?: string }> {
  return api.post('/api/skill-method/track', { track_id: trackId }).catch(() => ({ success: false }))
}

export async function registerSkillSession(trackId: string, sessionType: string, title: string, notes: string): Promise<{ success: boolean; completed?: number; entry?: SkillSession }> {
  return api.post('/api/skill-method/session', { track_id: trackId, session_type: sessionType, title, notes }).catch(() => ({ success: false }))
}

// ── Capital Bar ──

export interface CapitalThreshold {
  key: string
  name: string
  amount: number
  mode: string
  reached: boolean
  gap: number
  pct: number
}

export interface CapitalRecord {
  amount: number
  feed_ratio: number
  feed: number
  source: string
  note?: string
  created_at: string
}

export interface CapitalBarStatus {
  success?: boolean
  pool?: number
  feed_ratio?: number
  thresholds?: CapitalThreshold[]
  monthly_passive?: number
  records?: CapitalRecord[]
  started_on?: string
  message?: string
}

export async function getCapitalBar(): Promise<CapitalBarStatus> {
  return api.get<CapitalBarStatus>('/api/capital-bar').catch(() => ({}))
}

export async function setCapitalRatio(ratio: number): Promise<{ success: boolean; feed_ratio?: number }> {
  return api.post('/api/capital-bar/ratio', { ratio }).catch(() => ({ success: false }))
}

export async function recordCapitalIncome(amount: number, source: string, note: string): Promise<{ success: boolean; pool?: number; feed?: number }> {
  return api.post('/api/capital-bar/income', { amount, source, note }).catch(() => ({ success: false }))
}

export async function adjustCapitalPool(amount: number, note: string): Promise<{ success: boolean; pool?: number }> {
  return api.post('/api/capital-bar/adjust', { amount, note }).catch(() => ({ success: false }))
}

// ── Goal Evaluator ──

export interface GoalEvalContext {
  last_month: number
  avg_monthly: number
  plan_monthly_projection: number
  pool_capital: number
}

export interface GoalEvalResult {
  success?: boolean
  goal?: { type: string; amount: number; multiplier?: number }
  context?: GoalEvalContext
  evaluation?: {
    status: string
    verdict: string
    realistic_projection: number
    feasible: boolean
    multiple_to_target: number
  }
  breakdown?: Array<{ name: string; monthly_est: number; note: string }>
  gaps?: Array<{ label: string; why: string; priority: string }>
}

export async function evaluateGoal(goalType: string, amount: number, multiplier: number): Promise<GoalEvalResult> {
  return api.post<GoalEvalResult>('/api/goal-evaluator/evaluate', { goal_type: goalType, amount, multiplier }).catch(() => ({}))
}

export interface GoalEvaluatorStatus {
  success?: boolean
  last_eval?: GoalEvalResult | null
  history?: GoalEvalResult[]
}

export async function getGoalEvaluatorStatus(): Promise<GoalEvaluatorStatus> {
  return api.get<GoalEvaluatorStatus>('/api/goal-evaluator').catch(() => ({}))
}
// ── Work Log ──

export interface WorkSession {
  id: string
  hours: number
  foco: string
  detail: string
  momentum: number
  created_at: string
}

export interface WorkLogStatus {
  success?: boolean
  sessions?: WorkSession[]
  total_sessions?: number
  total_hours?: number
  hours_7d?: number
  hours_30d?: number
  by_foco?: Record<string, number>
  avg_momentum?: number
  foco_options?: string[]
  message?: string
}

export async function getWorkLog(): Promise<WorkLogStatus> {
  return api.get<WorkLogStatus>('/api/work-log').catch(() => ({}))
}

export async function registerWorkSession(hours: number, foco: string, detail: string, momentum: number): Promise<{ success: boolean }> {
  return api.post('/api/work-log/session', { hours, foco, detail, momentum }).catch(() => ({ success: false }))
}

// ── Post Mortem ──

export interface PostMortemEntry {
  id: string
  item_type: string
  item_title: string
  outcome: string
  learned: string
  repeat: string
  avoid: string
  created_at: string
}

export interface PostMortemStatus {
  success?: boolean
  episodes?: PostMortemEntry[]
  total?: number
  approved?: number
  rejected?: number
  closed?: number
  learnings?: string[]
}

export async function getPostMortem(): Promise<PostMortemStatus> {
  return api.get<PostMortemStatus>('/api/postmortem').catch(() => ({}))
}

export async function registerPostMortem(itemType: string, itemTitle: string, outcome: string, learned: string, repeat: string, avoid: string): Promise<{ success: boolean }> {
  return api.post('/api/postmortem/register', { item_type: itemType, item_title: itemTitle, outcome, learned, repeat, avoid }).catch(() => ({ success: false }))
}

// ── Account Health ──

export interface HealthEvent {
  type: string
  detail: string
  impact: number
  created_at: string
}

export interface HealthAccount {
  platform: string
  name: string
  created_at: string
  health_score: number
  events: HealthEvent[]
  notes: string
}

export interface AccountHealthStatus {
  success?: boolean
  accounts?: HealthAccount[]
  total?: number
  alerts?: Array<{ platform: string; level: string; why: string }>
}

export async function getAccountHealth(): Promise<AccountHealthStatus> {
  return api.get<AccountHealthStatus>('/api/account-health').catch(() => ({}))
}

export async function registerHealthAccount(platform: string, name: string): Promise<{ success: boolean }> {
  return api.post('/api/account-health/register', { platform, name }).catch(() => ({ success: false }))
}

export async function reportHealthEvent(platform: string, eventType: string, detail: string, impact: number): Promise<{ success: boolean }> {
  return api.post('/api/account-health/event', { platform, event_type: eventType, detail, impact }).catch(() => ({ success: false }))
}

// ── Payout Planner ──

export interface PayoutPlatform {
  id: string
  name: string
  method: string
  arrival_days: number
  note: string
  configured: boolean
}

export interface PayoutPlannerStatus {
  success?: boolean
  platforms?: PayoutPlatform[]
  message?: string
}

export async function getPayoutPlanner(): Promise<PayoutPlannerStatus> {
  return api.get<PayoutPlannerStatus>('/api/payout-planner').catch(() => ({}))
}

export async function configurePayoutPlatform(platformId: string): Promise<{ success: boolean }> {
  return api.post('/api/payout-planner/configure', { platform_id: platformId }).catch(() => ({ success: false }))
}

// ── Brand Writer ──

export interface BrandDraft {
  channel: string
  text: string
  published?: boolean
}

export interface BrandDraftEntry {
  id: string
  topic: string
  created_at: string
  drafts: BrandDraft[]
  published: boolean
}

export interface BrandWriterStatus {
  success?: boolean
  drafts?: BrandDraftEntry[]
  total?: number
}

export async function getBrandWriter(): Promise<BrandWriterStatus> {
  return api.get<BrandWriterStatus>('/api/brand-writer').catch(() => ({}))
}

export async function generateBrandDraft(topic: string, detail: string, channels?: string[]): Promise<{ success: boolean; entry?: BrandDraftEntry }> {
  return api.post('/api/brand-writer/generate', { topic, detail, channels }).catch(() => ({ success: false }))
}

export async function publishBrandDraft(draftId: string, channel: string): Promise<{ success: boolean }> {
  return api.post('/api/brand-writer/publish', { draft_id: draftId, channel }).catch(() => ({ success: false }))
}

// ── Vault Lock ──

export interface VaultLockStatus {
  success?: boolean
  mode?: string
  protected?: string[]
  has_passphrase_fingerprint?: boolean
  updated_at?: string
  message?: string
}

export async function getVaultLock(): Promise<VaultLockStatus> {
  return api.get<VaultLockStatus>('/api/vault-lock').catch(() => ({}))
}

export async function secureVault(passphrase: string): Promise<{ success: boolean; message?: string }> {
  return api.post('/api/vault-lock/secure', { passphrase }).catch(() => ({ success: false, message: 'API no disponible' }))
}

export async function unlockVault(passphrase: string): Promise<{ success: boolean; message?: string }> {
  return api.post('/api/vault-lock/unlock', { passphrase }).catch(() => ({ success: false, message: 'API no disponible' }))
}

// ── Emergency Mode ──

export interface EmergencyAction {
  title: string
  impact: string
  why: string
  detail?: string
}

export interface EmergencyAnalysis {
  success?: boolean
  level?: string
  verdict?: string
  projection?: number
  gap?: number
  plan?: EmergencyAction[]
  signals?: { bount_pending: number; hours_7d: number; vpn_ready: boolean }
  triggered_at?: string
}

export async function analyzeEmergency(targetMonthly: number, goalType: string): Promise<EmergencyAnalysis> {
  return api.post<EmergencyAnalysis>('/api/emergency-mode/analyze', { target_monthly: targetMonthly, goal_type: goalType }).catch(() => ({}))
}

export async function getEmergencyStatus(): Promise<{ success?: boolean; last?: string; triggered_at?: string }> {
  return api.get('/api/emergency-mode').catch(() => ({}))
}

// ── Payout Net ──

export interface PayoutMethod {
  id: string
  name: string
  cat: string
  kyc: string
  cotiz: string
  dias: number
  costo: string
  fallbacks: string[]
}

export interface PayoutCatalog {
  success?: boolean
  total?: number
  categories?: Record<string, number>
  methods?: PayoutMethod[]
}

export interface PayoutResolveResult {
  success?: boolean
  method?: string
  problem?: string
  fix?: string
  fallbacks?: string[]
  key?: string
}

export async function getPayoutCatalog(cat: string = ''): Promise<PayoutCatalog> {
  return api.get<PayoutCatalog>(`/api/payout-net${cat ? `?cat=${cat}` : ''}`).catch(() => ({}))
}

export async function recommendPayout(source: string): Promise<{ success?: boolean; source?: string; recommended?: PayoutMethod[] }> {
  return api.post('/api/payout-net/recommend', { source }).catch(() => ({}))
}

export async function resolvePayoutProblem(methodId: string, problem: string): Promise<PayoutResolveResult> {
  return api.post('/api/payout-net/resolve', { method_id: methodId, problem }).catch(() => ({}))
}

export async function getPayoutNetStatus(): Promise<{ success?: boolean; total_methods?: number; incidents?: number }> {
  return api.get('/api/payout-net/status').catch(() => ({}))
}

// ── Payment Tracker ──

export interface PaymentEvent {
  id: string
  platform: string
  opportunity_id: string
  amount_usd: number
  currency: string
  status: string
  detected_at: string
  confirmed_at: string | null
  metadata: Record<string, unknown>
}

export interface PaymentTrackerStatus {
  total_payments: number
  pending_confirmation: number
  confirmed: number
  total_earnings_30d_usd: number
  platforms_with_webhooks: number
  platforms_with_polling: number
  platforms: string[]
}

export async function getPaymentTrackerStatus(): Promise<PaymentTrackerStatus> {
  return api.get<PaymentTrackerStatus>('/api/payment-tracker').catch(() => ({
    total_payments: 0,
    pending_confirmation: 0,
    confirmed: 0,
    total_earnings_30d_usd: 0,
    platforms_with_webhooks: 0,
    platforms_with_polling: 0,
    platforms: [],
  }))
}

export async function confirmPayment(paymentId: string): Promise<{ success: boolean; payment?: PaymentEvent }> {
  return api.post('/api/payment-tracker/confirm', { payment_id: paymentId }).catch(() => ({ success: false }))
}

export async function getPendingPayments(): Promise<{ pending: PaymentEvent[]; total: number }> {
  return api.get('/api/payment-tracker/pending').catch(() => ({ pending: [], total: 0 }))
}

// ── Trust Engine ──

export interface TrustMetrics {
  platform: string
  total_opportunities: number
  accepted: number
  rejected: number
  paid: number
  unpaid: number
  total_earnings_usd: number
  avg_payment_usd: number
  avg_time_to_payment_days: number
  success_rate: number
  payment_rate: number
  trust_level: string
  last_updated: string
}

export interface TrustEngineStatus {
  platforms_with_data: number
  platforms_with_high_trust: number
  high_trust_platforms: string[]
  auto_approval_enabled: boolean
  auto_approval_threshold_usd: number
  min_trust_level: string
  total_opportunities_tracked: number
  total_earnings_tracked_usd: number
}

export async function getTrustEngineStatus(): Promise<TrustEngineStatus> {
  return api.get<TrustEngineStatus>('/api/trust-engine').catch(() => ({
    platforms_with_data: 0,
    platforms_with_high_trust: 0,
    high_trust_platforms: [],
    auto_approval_enabled: false,
    auto_approval_threshold_usd: 50,
    min_trust_level: 'high',
    total_opportunities_tracked: 0,
    total_earnings_tracked_usd: 0,
  }))
}

export async function getPlatformTrust(platform: string): Promise<TrustMetrics | null> {
  return api.get<TrustMetrics>(`/api/trust-engine/platform/${platform}`).catch(() => null)
}

export async function checkAutoApprove(platform: string, amountUsd: number): Promise<{ can_approve: boolean; reason: string }> {
  return api.post('/api/trust-engine/can-auto-approve', { platform, amount_usd: amountUsd }).catch(() => ({ can_approve: false, reason: 'Error' }))
}

// ── Closed Loop ──

export interface ClosedLoopStatus {
  config: {
    auto_learn_from_payments: boolean
    auto_update_trust: boolean
    auto_update_profile: boolean
  }
  recommendation_improvement: {
    trust_status: TrustEngineStatus
    payment_status: PaymentTrackerStatus
    learning_active: boolean
    profile_updates_enabled: boolean
    trust_updates_enabled: boolean
  }
}

export async function getClosedLoopStatus(): Promise<ClosedLoopStatus> {
  return api.get<ClosedLoopStatus>('/api/closed-loop').catch(() => ({
    config: {
      auto_learn_from_payments: false,
      auto_update_trust: false,
      auto_update_profile: false,
    },
    recommendation_improvement: {
      trust_status: {
        platforms_with_data: 0,
        platforms_with_high_trust: 0,
        high_trust_platforms: [],
        auto_approval_enabled: false,
        auto_approval_threshold_usd: 50,
        min_trust_level: 'high',
        total_opportunities_tracked: 0,
        total_earnings_tracked_usd: 0,
      },
      payment_status: {
        total_payments: 0,
        pending_confirmation: 0,
        confirmed: 0,
        total_earnings_30d_usd: 0,
        platforms_with_webhooks: 0,
        platforms_with_polling: 0,
        platforms: [],
      },
      learning_active: false,
      profile_updates_enabled: false,
      trust_updates_enabled: false,
    },
  }))
}

// ── Finance Guru ──

export interface FinanceAccount {
  id: string
  name: string
  region: string
  kyc: string
  llc_needed: boolean
  dias: string
  costo: string
  para: string[]
  pasos: string[]
  problemas: Record<string, string>
  fallbacks: string[]
}

export interface FinanceAskResult {
  success?: boolean
  intent?: string
  answer?: string
  recommended?: Array<{ id: string; name: string; dias: string }>
  message?: string
}

export interface FinanceResolveResult {
  success?: boolean
  account?: string
  problem?: string
  fix?: string
  fallbacks?: string[]
  pasos?: string[]
}

export async function askFinanceGuru(query: string): Promise<FinanceAskResult> {
  return api.post<FinanceAskResult>('/api/finance-guru/ask', { query }).catch(() => ({}))
}

export async function resolveFinanceAccount(accountId: string, problem: string): Promise<FinanceResolveResult> {
  return api.post<FinanceResolveResult>('/api/finance-guru/resolve', { account_id: accountId, problem }).catch(() => ({}))
}

export async function getFinanceAccounts(): Promise<{ success?: boolean; total?: number; accounts?: FinanceAccount[] }> {
  return api.get('/api/finance-guru/accounts').catch(() => ({}))
}

export async function getFinanceGuruStatus(): Promise<{ success?: boolean; accounts_total?: number; qa_count?: number }> {
  return api.get('/api/finance-guru').catch(() => ({}))
}

// ── Tax AR ──

export interface TaxARStatus {
  success?: boolean
  cuil?: string
  categoria?: string
  cuota_mensual?: number
  ingresos_usd?: number
  facturas?: number
  gastos_deducibles?: Record<string, number>
  proxima_recategorizacion?: string
}

export async function getTaxAR(): Promise<TaxARStatus> {
  return api.get<TaxARStatus>('/api/tax-ar').catch(() => ({}))
}

export async function setTaxCUIL(cuil: string): Promise<{ success: boolean }> {
  return api.post('/api/tax-ar/cuil', { cuil }).catch(() => ({ success: false }))
}

export async function setTaxCategoria(cat: string): Promise<{ success: boolean }> {
  return api.post('/api/tax-ar/categoria', { categoria: cat }).catch(() => ({ success: false }))
}

export async function addTaxIncome(usd: number, fecha: string): Promise<{ success: boolean }> {
  return api.post('/api/tax-ar/ingreso', { usd, fecha }).catch(() => ({ success: false }))
}

export async function calcTaxGastos(ingresos_usd: number, usd_ars: number): Promise<{ success: boolean; gastos?: Record<string, number> }> {
  return api.post('/api/tax-ar/gastos', { ingresos_usd, usd_ars }).catch(() => ({ success: false }))
}

export async function addTaxFactura(cliente: string, usd: number, fecha: string, cae: string): Promise<{ success: boolean }> {
  return api.post('/api/tax-ar/factura', { cliente, usd, fecha, cae }).catch(() => ({ success: false }))
}

export async function exportTaxCSV(path: string): Promise<{ success: boolean }> {
  return api.post('/api/tax-ar/csv', { path }).catch(() => ({ success: false }))
}

// ── Invoicer AR ──

export interface InvoicerARStatus {
  success?: boolean
  cuit?: string
  punto_venta?: number
  modo?: string
  certificado?: string
  facturas_emitidas?: number
  ultimo_cae?: number
}

export interface InvoicerFactura {
  cliente_cuit: string
  cliente_nombre: string
  usd: number
  descripcion?: string
  moneda?: string
  cotizacion?: number
}

export async function getInvoicerAR(): Promise<InvoicerARStatus> {
  return api.get<InvoicerARStatus>('/api/invoicer-ar').catch(() => ({}))
}

export function configInvoicerAR(cuit: string, cert: string, key: string, pv: number, modo: string): Promise<{ success: boolean }> {
  return api.post('/api/invoicer-ar/config', { cuit, cert_path: cert, key_path: key, punto_venta: pv, modo }).catch(() => ({ success: false }))
}

export function emitInvoicerAR(f: InvoicerFactura): Promise<{ success: boolean }> {
  return api.post('/api/invoicer-ar/emitir', f).catch(() => ({ success: false }))
}

export function pdfInvoicerAR(factura: any): Promise<{ success: boolean }> {
  return api.post('/api/invoicer-ar/pdf', factura).catch(() => ({ success: false }))
}

// ── Offramp Executor ──

export interface OfframpProvider {
  name: string
  type: string
  base_url: string
  requires_kyc: boolean
  min_usd: number
}

export interface OfframpExecution {
  id: string
  provider: string
  provider_name: string
  amount_usd: number
  url: string
  type: string
  created_at: string
  status: string
}

export interface OfframpStatus {
  success?: boolean
  default?: string
  pending?: number
  completed?: number
  total_volume_usd?: number
  recent?: OfframpExecution[]
  providers?: Record<string, OfframpProvider>
}

export async function getOfframpProviders(): Promise<{ success?: boolean; providers?: Record<string, OfframpProvider>; default?: string }> {
  return api.get('/api/offramp/providers').catch(() => ({}))
}

export async function getOfframpStatus(): Promise<OfframpStatus> {
  return api.get<OfframpStatus>('/api/offramp').catch(() => ({}))
}

export async function setOfframpDefault(provider: string): Promise<{ success: boolean }> {
  return api.post('/api/offramp/default', { provider }).catch(() => ({ success: false }))
}

export async function executeOfframp(provider: string, amount_usd: number, extra?: Record<string, any>): Promise<{ success?: boolean; execution?: OfframpExecution }> {
  return api.post('/api/offramp/execute', { provider, amount_usd, extra }).catch(() => ({}))
}

export async function markOfframpDone(execution_id: string, txid: string): Promise<{ success: boolean }> {
  return api.post('/api/offramp/done', { execution_id, txid }).catch(() => ({ success: false }))
}

// ── Platform Connectors ──

export interface PlatformStatus {
  success?: boolean
  platforms?: Record<string, { enabled: boolean; has_creds: boolean }>
  last_sync?: Record<string, string>
}

export interface PlatformSyncResult {
  success?: boolean
  results?: Record<string, { connected: boolean; opportunities?: number; payments?: number; error?: string }>
}

export async function getPlatformsStatus(): Promise<PlatformStatus> {
  return api.get<PlatformStatus>('/api/platforms').catch(() => ({}))
}

export async function setPlatformConfig(platform: string, enabled: boolean, credentials?: Record<string, string>): Promise<{ success: boolean }> {
  return api.post('/api/platforms/config', { platform, enabled, credentials }).catch(() => ({ success: false }))
}

export async function syncPlatforms(): Promise<PlatformSyncResult> {
  return api.post<PlatformSyncResult>('/api/platforms/sync', {}).catch(() => ({}))
}
