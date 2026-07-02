// ── Core Domain ──

export interface Target {
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

export interface Finding {
  id: number
  target_id: number
  endpoint_id: number | null
  title: string
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info'
  description: string | null
  payout: number
  target_name: string
  endpoint_path: string
  created_at: string | null
  poc_path?: string
  suggested_responses?: string[]
}

export interface Verdict {
  id: number
  hot_path_id: string | null
  endpoint_id: number
  status: 'confirmed' | 'rejected' | 'inconclusive' | 'pending'
  confidence: number
  reproducibility_score: number
  reason: string | null
  validation_report: Record<string, any>
  created_at: string | null
}

export interface EvidenceItem {
  id: number
  verdict_id: number
  endpoint_id: number
  attempt_label: string
  request_url: string
  request_method: string
  response_status: number
  consistent: boolean
  curl_command: string | null
  body_diff_ratio: number
  request_body: string | null
  response_body: string | null
}

export interface Report {
  id: number
  investigation_id: number | null
  format: string
  program: string
  target: string
  vulnerability: string
  severity: string
  status: 'draft' | 'pending' | 'submitted' | 'paid' | 'rejected'
  estimated_reward: number
  confirmed_reward: number
  currency: string
  evidence_count: number
  summary: string
  content: Record<string, any> | null
  created_at: string | null
  updated_at: string | null
}

// ── WebSocket ──

export type WsConnectionStatus = 'disconnected' | 'connecting' | 'connected'

export interface WsEvent {
  type: string
  payload: Record<string, any>
  ts: number
}

// ── Financial ──

export interface ProgramPayout {
  program: string
  report_count: number
  confirmed_count: number
  acceptance_rate: number
  total_confirmed: number
  avg_payout: number
  highest_payout: number
  avg_response_days: number
}

export interface TypePayout {
  vulnerability_type: string
  count: number
  confirmed_count: number
  total_estimated: number
  total_confirmed: number
  avg_estimated: number
  avg_confirmed: number
  base_payout: number
  learned_payout: number
  adjustment_factor: number
}

export interface RewardLearning {
  generated_at: string
  total_reports: number
  total_confirmed: number
  total_confirmed_value: number
  overall_acceptance_rate: number
  by_type: Record<string, TypePayout>
  by_program: Record<string, ProgramPayout>
  top_programs_by_payout: ProgramPayout[]
  top_programs_by_acceptance: ProgramPayout[]
  prediction_accuracy: number
  summary: string
}

export interface FinancialMetrics {
  total_earned: number
  pending_payouts: number
  paid_payouts: number
  monthly_breakdown: { month: string; amount: number; paid: number }[]
  value_per_hour: number
  hours_tracked: number
}

// ── Hot Path / Attack Decision ──

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

export interface AttackDecision {
  summary: string
  high_value_targets: HotPathItem[]
  attack_vectors: Array<{ vector: string; endpoints: string[]; count: number }>
  ownership_risks: HotPathItem[]
  manual_test_suggestions: string[]
}

// ── Orion Context ──

export interface OrionContext {
  timestamp: string
  system: { status: string; health_score: number; details: string[]; uptime_hours: number }
  counts: {
    targets: number; endpoints: number; findings: number; verdicts: number
    confirmed_findings: number; total_estimated_payout: number
    pending_rewards: number; reports_ready: number; active_scans: number
  }
  findings: { by_severity: Record<string, number>; new_24h: number }
  verdicts: { by_status: Record<string, number>; confirmed: number; rejected: number; inconclusive: number }
  reports: { by_status: Record<string, number>; total_rewards: number; pending_rewards: number; ready_for_approval: number }
  earnings: { total: number; pending: number; paid: number }
  opportunities: {
    total: number
    top: Array<{ id: number; name: string; domain: string; opportunity_score: number; endpoints: number; competition: number; freshness: number }>
  }
  next_action: { target_id: number; title: string; why_now: string; effort: string; estimated_reward: string; type: string } | null
  scans: { active: number; recent: Array<{ id: number; target_id: number; mode: string; status: string; endpoints: number; started: string }> }
  activity_24h: { total: number; events: Array<{ type: string; id: number; severity?: string; timestamp: string }> }
  pipeline: { detected: number; validated: number; confirmed: number; reported: number }
  _meta: { cached_at: number; ttl_seconds: number; version?: string; error?: string }
}

// ── Pipeline ──

export interface PipelineStages {
  detected: Finding[]
  validated: Finding[]
  confirmed: Finding[]
  reported: Finding[]
}

// ── Scan ──

export interface ScanRun {
  id: number
  target_id: number
  mode: string
  status: string
  endpoint_count: number
  started_at: string | null
  finished_at: string | null
}

// ── ZAP Integration ──

export interface ZapAlert {
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

export interface ZapSpiderResult {
  status: string
  urls_found: string[]
  url_count: number
  scan_id: string
}

export interface ZapPassiveResult {
  status: string
  target_url: string
  alerts: ZapAlert[]
  alert_count: number
}

export interface ZapHypothesisResult {
  status: string
  target_url: string
  hypotheses: HypothesisItem[]
  total: number
}

// ── Enriched Hypothesis with Didactic Fields ──

export interface HypothesisItem {
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

// ── Verification Guide ──

export type VerificationStepStatus = 'pending' | 'in_progress' | 'completed' | 'failed'

export interface VerificationStep {
  id: string
  label: string
  description: string
  status: VerificationStepStatus
  type: 'check' | 'command' | 'screenshot' | 'note'
}

export interface VerificationSession {
  hypothesis_id: string
  vulnerability_type: string
  target_name: string
  target_url: string
  steps: VerificationStep[]
  current_step: number
  started_at: string | null
  completed_at: string | null
  result: 'pending' | 'confirmed' | 'rejected' | 'inconclusive' | null
}
