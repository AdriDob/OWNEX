/**
 * TypeScript Type Definitions for OWNEX Alpha
 *
 * Interfaces específicas para respuestas de API y datos del sistema
 * para evitar el uso excesivo de `any`.
 */

// ==================== AUTH TYPES ====================

export interface LoginResponse {
  session: {
    token: string;
    user_id: string;
    expires_at: string;
  };
}

export interface DeviceInfo {
  device_id: string;
  device_type: string;
  os: string;
  browser: string;
  ip_address: string;
}

// ==================== TASK TYPES ====================

export interface Task {
  task_id: string;
  title: string;
  description: string;
  category: TaskCategory;
  priority: TaskPriority;
  status: TaskStatus;
  created_at: string;
  completed_at?: string;
  assigned_to?: string;
}

export type TaskCategory = 'bug_bounty' | 'dev_bounty' | 'data_annotation' | 'learning' | 'planning' | 'admin' | 'break';
export type TaskPriority = 'critical' | 'high' | 'medium' | 'low';
export type TaskStatus = 'pending' | 'in_progress' | 'completed' | 'blocked' | 'cancelled';

// ==================== WORKFLOW TYPES ====================

export interface Workflow {
  workflow_id: string;
  title: string;
  description: string;
  status: WorkflowStatus;
  tasks: Task[];
  created_at: string;
  updated_at: string;
}

export type WorkflowStatus = 'pending' | 'running' | 'paused' | 'completed' | 'failed' | 'cancelled';

// ==================== MERLIN TYPES ====================

export interface MerlinMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  emotion?: string;
}

export interface MerlinMemory {
  memory_id: string;
  type: MemoryType;
  content: string;
  tags: string[];
  created_at: string;
}

export type MemoryType = 'conversation' | 'pattern' | 'workflow' | 'strategy' | 'knowledge' | 'note';

export interface MerlinNote {
  note_id: string;
  title: string;
  content: string;
  created_at: string;
  updated_at: string;
}

// ==================== INTEGRATION TYPES ====================

export interface Integration {
  integration_id: string;
  name: string;
  category: string;
  status: 'connected' | 'disconnected' | 'error';
  last_sync?: string;
  config: Record<string, unknown>;
}

export interface IntegrationsData {
  integrations: Integration[];
  by_category: Record<string, Integration[]>;
  by_status: Record<string, number>;
}

// ==================== BACKUP TYPES ====================

export interface Backup {
  backup_id: string;
  created_at: string;
  size: number;
  version: string;
  description?: string;
  checksum: string;
}

// ==================== PLANET TYPES ====================

export interface Planet {
  id: string;
  name: string;
  icon: string;
  color: string;
  description: string;
  category: string;
}

// ==================== PLATFORM GUIDE TYPES ====================

export interface PlatformGuide {
  platform_id: string;
  name: string;
  description: string;
  url: string;
  category: string;
  difficulty: string;
  rewards: {
    min: number;
    max: number;
    currency: string;
  };
}

// ==================== SETTING TYPES ====================

export interface Setting {
  key: string;
  value: unknown;
  type: 'string' | 'number' | 'boolean' | 'object' | 'array';
  category: string;
  description?: string;
}

// ==================== ERROR TYPES ====================

export interface ErrorResponse {
  error: string;
  message?: string;
  details?: Record<string, unknown>;
}

// ==================== NOTIFICATION TYPES ====================

export interface Notification {
  notification_id: string;
  title: string;
  message: string;
  level: NotificationLevel;
  created_at: string;
  read: boolean;
  requires_action: boolean;
  action_type?: string;
}

export type NotificationLevel = 'critical' | 'high' | 'medium' | 'low';

// ==================== WEAR OS TYPES ====================

export interface WatchNotification {
  notification_id: string;
  title: string;
  message: string;
  level: NotificationLevel;
  created_at: string;
  read: boolean;
  requires_action: boolean;
  action_type?: string;
}

export interface WatchApprovalRequest {
  request_id: string;
  title: string;
  description: string;
  workflow_id?: string;
  created_at: string;
  responded: boolean;
  approved?: boolean;
}

export interface WatchStatus {
  system_online: boolean;
  scheduler_running: boolean;
  active_workflows: number;
  pending_approvals: number;
  findings_total: number;
  findings_confirmed: number;
  targets_active: number;
  health_score: number;
  last_updated: string;
}

// ==================== PRODUCTIVITY TYPES ====================

export interface DailyPlan {
  date: string;
  tasks: Task[];
  total_estimated_minutes: number;
  total_completed_minutes: number;
  progress_percentage: number;
  breaks_scheduled: number;
  breaks_taken: number;
  focus_sessions: number;
  created_at: string;
  updated_at: string;
}

export interface ProductivityMetrics {
  date: string;
  tasks_completed: number;
  tasks_total: number;
  focus_hours: number;
  break_hours: number;
  revenue_generated: number;
  bugs_found: number;
  reports_submitted: number;
  learning_hours: number;
  efficiency_score: number;
}

// ==================== ONBOARDING TYPES ====================

export interface OnboardingLesson {
  lesson_id: string;
  day: string;
  title: string;
  description: string;
  content: string;
  duration_minutes: number;
  status: LessonStatus;
  completed_at?: string;
  notes: string;
}

export type LessonStatus = 'not_started' | 'in_progress' | 'completed' | 'skipped';

export interface OnboardingProgress {
  user_name: string;
  current_day: string;
  lessons_completed: number;
  lessons_total: number;
  completion_percentage: number;
  started_at: string;
  completed_at?: string;
  notes: string[];
}

// ==================== PERSONALIZATION TYPES ====================

export interface PersonalProfile {
  name: string;
  preferred_name: string;
  timezone: string;
  language: string;
  experience_level: ExperienceLevel;
  work_mode: WorkMode;
  guidance_level: GuidanceLevel;
  primary_goal: string;
  secondary_goals: string[];
  income_target_monthly: number;
  is_first_time_user: boolean;
  days_using: number;
  completed_onboarding: boolean;
  voice_enabled: boolean;
  voice_language: string;
  obsidian_enabled: boolean;
  obsidian_vault_path: string;
  obsidian_daily_notes: boolean;
  work_hours_start: string;
  work_hours_end: string;
  work_days: string[];
  break_reminders: boolean;
  daily_tasks_enabled: boolean;
  daily_planning_enabled: boolean;
  progress_tracking: boolean;
  calendar_integration: boolean;
  email_integration: boolean;
  task_integration: string;
  assistant_name: string;
  assistant_tone: string;
  assistant_proactivity: string;
  bug_bounty_focus: boolean;
  dev_bounty_focus: boolean;
  data_annotation_focus: boolean;
  productivity_focus: boolean;
  created_at: string;
  updated_at: string;
}

export type ExperienceLevel = 'beginner' | 'intermediate' | 'advanced' | 'expert';
export type WorkMode = 'bug_bounty' | 'dev_bounty' | 'data_annotation' | 'freelance' | 'mixed';
export type GuidanceLevel = 'high_guidance' | 'medium_guidance' | 'low_guidance' | 'self_directed';

// ==================== API RESPONSE WRAPPER ====================

export interface ApiResponse<T = unknown> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

// ==================== PAGINATION TYPES ====================

export interface PaginatedResponse<T = unknown> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// ==================== HEALTH TYPES ====================

export interface HealthStatus {
  status: 'healthy' | 'degraded' | 'unhealthy';
  score: number;
  checks: HealthCheck[];
  last_updated: string;
}

export interface HealthCheck {
  name: string;
  status: 'pass' | 'fail' | 'warn';
  message?: string;
  duration_ms?: number;
}

// ==================== WIZARD TYPES ====================

export interface WizardQuestion {
  id: string;
  question: string;
  type: 'text' | 'number' | 'time' | 'select' | 'boolean';
  placeholder?: string;
  required: boolean;
  default?: unknown;
  options?: Array<{ value: string; label: string }>;
  condition?: string;
  description?: string;
}

export interface WizardStep {
  step_id: string;
  title: string;
  description: string;
  questions: WizardQuestion[];
  is_required: boolean;
  can_skip: boolean;
}

/** Shape of GET /orion/context/system (dashboard aggregate). */
export interface OrionContextCounts {
  targets: number
  endpoints?: number
  findings?: number
  reports?: number
}

export interface OrionContextFindings {
  by_severity: Partial<Record<'critical' | 'high' | 'medium' | 'low', number>>
  total?: number
}

export interface OrionContextVerdicts {
  by_status: Partial<Record<string, number>>
}

export interface OrionContextOpportunity {
  id?: number
  title?: string
  score?: number
  platform?: string
}

export interface OrionContext {
  counts: OrionContextCounts
  findings: OrionContextFindings
  verdicts: OrionContextVerdicts
  opportunities: { total: number; top: OrionContextOpportunity[] }
  scans?: Partial<Record<string, number>>
  _meta?: { version?: string; generated_at?: string }
}
