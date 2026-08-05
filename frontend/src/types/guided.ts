export interface GuidedMode {
  guided: 'guided'
  assisted: 'assisted'
  autonomous: 'autonomous'
  expert: 'expert'
}

export interface ModeInfo {
  title: string
  subtitle: string
  desc: string
  features: string[]
}

export interface ExplanationLayer {
  what: string
  why: string
  how: string
  result: string
  nextStep: string
  confidence?: {
    level: 'high' | 'medium' | 'low'
    detail: string
  }
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

export interface IncomeGuidance {
  title: string
  summary: string
  difficulty: 'beginner' | 'intermediate' | 'advanced' | 'expert'
  required: {
    programming: boolean
    portfolio: boolean
    interview: boolean
  }
  own_prep_pct: number
  user_action: string
  explanation: ExplanationLayer
  confidence: {
    level: 'high' | 'medium' | 'low'
    detail: string
  }
}

export interface DirectWorkRanked {
  rank: number
  opportunity: {
    id: string
    title: string
    platform: string
    category: string
    payment: number
    currency: string
    payment_method: string
    difficulty: string
    language_required: string
    estimated_time_hours: number
    experience_required: string
    portfolio_required: boolean
    interview_required: boolean
    technical_test_required: boolean
    registration_required: boolean
    time_to_payout_days: number | null
    reputation: number
    risk: number
    payment_proven: boolean
    stability: number
    accepts_beginner: boolean
    accepts_freelancers: boolean
    accepts_individuals: boolean
    accepts_ai_tools: boolean
    asynchronous: boolean
    technology_tags: string[]
    employment_type: string
    zero_barrier_score?: {
      total: number
      barrier_level: string
      enablers: string[]
      blockers: string[]
    }
  }
  zero_barrier_score: {
    total: number
    barrier_level: string
    enablers: string[]
    blockers: string[]
  }
  expected_value: number
  acceptance_probability: number
  compatibility_score: number
  speed_score: number
  reputation_score: number
  risk_score: number
  overall_recommendation_score: number
  strategy: string
  recommendation_reasoning: string[]
}

export interface DailyBriefSource {
  name: string
  url: string
  category: string
  trust_score: number
  earning_potential: string
  average_reward: string
}