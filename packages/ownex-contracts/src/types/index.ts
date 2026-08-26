/**
 * OWNEX Shared Contracts — Single Source of Truth
 * Types used across Desktop, Mobile, Watch, Backend
 * Version: 1.0.0-alpha
 */

// ============================================
// CORE IDENTIFIERS
// ============================================

export type DeviceId = string & { readonly __brand: unique symbol };
export type UserId = string & { readonly __brand: unique symbol };
export type OpportunityId = string & { readonly __brand: unique symbol };
export type WorkItemId = string & { readonly __brand: unique symbol };
export type ExecutionId = string & { readonly __brand: unique symbol };
export type TransactionId = string & { readonly __brand: unique symbol };
export type NotificationId = string & { readonly __brand: unique symbol };
export type ApprovalId = string & { readonly __brand: unique symbol };
export type SessionId = string & { readonly __brand: unique symbol };

export function createDeviceId(): DeviceId {
  return `dev_${crypto.randomUUID()}` as DeviceId;
}

export function createUserId(): UserId {
  return `usr_${crypto.randomUUID()}` as UserId;
}

// ============================================
// ENUMS - Single Source of Truth
// ============================================

export enum OpportunityStage {
  DISCOVERED = 'discovered',
  QUALIFIED = 'qualified',
  RECOMMENDED = 'recommended',
  PREPARED = 'prepared',
  APPROVAL_REQUIRED = 'approval_required',
  APPROVED = 'approved',
  IN_PROGRESS = 'in_progress',
  SUBMITTED = 'submitted',
  VERIFICATION = 'verification',
  PAID = 'paid',
  REJECTED = 'rejected',
  EXPIRED = 'expired',
  CANCELLED = 'cancelled',
}

export enum PaymentStatus {
  PENDING = 'pending',
  REVIEWING = 'reviewing',
  ACCEPTED = 'accepted',
  PAID = 'paid',
  FAILED = 'failed',
  CANCELLED = 'cancelled',
}

export enum ExecState {
  DISCOVERED = 'discovered',
  QUALIFIED = 'qualified',
  READY = 'ready',
  QUEUED = 'queued',
  EXECUTING = 'executing',
  WAITING_HUMAN = 'waiting_human',
  SUBMITTED = 'submitted',
  VERIFICATION = 'verification',
  PAID = 'paid',
  REJECTED = 'rejected',
  BLOCKED = 'blocked',
  FAILED = 'failed',
  DEAD_LETTER = 'dead_letter',
}

export enum OpportunityCategory {
  BUG_BOUNTY = 'bug_bounty',
  DEV_BOUNTY = 'dev_bounty',
  AI_EVALUATION = 'ai_evaluation',
  DATA_ANNOTATION = 'data_annotation',
  QA_TESTING = 'qa_testing',
  CODE_REVIEW = 'code_review',
  PROMPT_ENGINEERING = 'prompt_engineering',
  TECHNICAL_WRITING = 'technical_writing',
  SECURITY_AUDIT = 'security_audit',
  PENETRATION_TESTING = 'penetration_testing',
  RESEARCH = 'research',
  OSS_CONTRIBUTION = 'oss_contribution',
  GAME_DEV = 'game_dev',
  OTHER = 'other',
}

export enum WorkPlatform {
  HACKERONE = 'hackerone',
  BUGCROWD = 'bugcrowd',
  INTIGRITI = 'intigriti',
  YESWEHACK = 'yeswehack',
  SYNACK = 'synack',
  IMMUNEFI = 'immunefi',
  OPIRE = 'opire',
  ISSUEHUNT = 'issuehunt',
  ALGORA = 'algora',
  FREELANCER = 'freelancer',
  UPWORK = 'upwork',
  TOTAL = 'total',
  GITHUB = 'github',
  GITLAB = 'gitlab',
  OUTLIER = 'outlier',
  MERCOR = 'mercor',
  ALIGNERR = 'alignerr',
  MINDRIFT = 'mindrift',
  DATAANNOTATION = 'dataannotation',
  OTHER = 'other',
}

export enum PaymentPlatform {
  PAYPAL = 'paypal',
  PAYONEER = 'payoneer',
  WISE = 'wise',
  BINANCE = 'binance',
  COINBASE = 'coinbase',
  MERCADOPAGO = 'mercadopago',
  BANK_TRANSFER = 'bank_transfer',
  CRYPTO = 'crypto',
  OTHER = 'other',
}

export enum BarrierType {
  NONE = 'none',
  INTERVIEW = 'interview',
  PORTFOLIO = 'portfolio',
  EXPERIENCE = 'experience',
  DEGREE = 'degree',
  CERTIFICATION = 'certification',
  LOCATION = 'location',
  VISA = 'visa',
  LANGUAGE = 'language',
  TECHNICAL_TEST = 'technical_test',
  REGISTRATION = 'registration',
  KYC = 'kyc',
  BACKGROUND_CHECK = 'background_check',
  SECURITY_CLEARANCE = 'security_clearance',
  OTHER = 'other',
}

export enum PaymentMethod {
  PAYPAL = 'paypal',
  PAYONEER = 'payoneer',
  WISE = 'wise',
  BANK_WIRE = 'bank_wire',
  BANK_TRANSFER = 'bank_transfer',
  CRYPTO = 'crypto',
  STABLECOIN = 'stablecoin',
  MERCADOPAGO = 'mercadopago',
  BANK_ACCOUNT = 'bank_account',
  CREDIT_CARD = 'credit_card',
  OTHER = 'other',
}

export enum DevicePlatform {
  DESKTOP = 'desktop',
  MOBILE = 'mobile',
  WATCH = 'watch',
  WEB = 'web',
}

export enum NotificationLevel {
  CRITICAL = 'critical',
  HIGH = 'high',
  MEDIUM = 'medium',
  LOW = 'low',
}

export enum NotificationType {
  OPPORTUNITY_HIGH_VALUE = 'opportunity_high_value',
  APPROVAL_REQUIRED = 'approval_required',
  TASK_READY = 'task_ready',
  TASK_BLOCKED = 'task_blocked',
  PAYMENT_RECEIVED = 'payment_received',
  SYSTEM_ERROR = 'system_error',
  SCHEDULER_FAILURE = 'scheduler_failure',
  BACKEND_OFFLINE = 'backend_offline',
  EXECUTION_COMPLETE = 'execution_complete',
  VERIFICATION_COMPLETE = 'verification_complete',
  APPROVAL_RESULT = 'approval_result',
}

export enum ApprovalAction {
  APPROVE = 'approve',
  REJECT = 'reject',
  REQUEST_MORE_INFO = 'request_more_info',
  ESCALATE = 'escalate',
}

export enum SyncStatus {
  SYNCED = 'synced',
  SYNCING = 'syncing',
  OFFLINE = 'offline',
  CONFLICT = 'conflict',
  ERROR = 'error',
}

// ============================================
// CORE DATA MODELS
// ============================================

export interface Money {
  amount: number;
  currency: string;
  formatted: string;
}

export function createMoney(amount: number, currency: string = 'USD'): Money {
  return {
    amount,
    currency,
    formatted: new Intl.NumberFormat('es-AR', {
      style: 'currency',
      currency,
      minimumFractionDigits: 2,
    }).format(amount),
  };
}

export interface DeviceIdentity {
  deviceId: string;
  platform: DevicePlatform;
  name: string;
  pushToken?: string;
  lastSeen: string;
  registeredAt: string;
  capabilities: string[];
}

export interface UserProfile {
  userId: string;
  name: string;
  email?: string;
  country: string;
  timezone: string;
  skills: string[];
  languages: string[];
  preferredPayment: PaymentPlatform[];
  preferredCategories: OpportunityCategory[];
  barriers: BarrierType[];
  experienceLevel: 'entry' | 'junior' | 'mid' | 'senior' | 'expert';
  hourlyRateExpectation?: Money;
  workPreferences: {
    remoteOnly: boolean;
    maxHoursPerWeek: number;
    preferredTimezone: string;
  };
}

export interface Opportunity {
  id: OpportunityId;
  platform: WorkPlatform;
  title: string;
  description: string;
  url: string;
  category: OpportunityCategory;
  specialization?: string;
  remote: boolean;
  payment: Money;
  paymentMethod: PaymentMethod;
  paymentProven: boolean;
  timeToPayoutDays: number;
  estimatedHours: number;
  difficulty: 'beginner' | 'intermediate' | 'advanced' | 'expert';
  experienceRequired: string;
  portfolioRequired: boolean;
  interviewRequired: boolean;
  testRequired: boolean;
  registrationRequired: boolean;
  countryRestrictions: string[];
  barriers: BarrierType[];
  reputation: number;
  risk: number;
  stability: number;
  acceptsBeginner: boolean;
  acceptsFreelancers: boolean;
  acceptsIndividuals: boolean;
  acceptsAiTools: boolean;
  source: string;
  discoveredAt: string;
  expiresAt?: string;
  stage: OpportunityStage;
  score?: number;
  evPerHumanHour?: number;
  availabilityState?: 'available' | 'limited' | 'unknown' | 'unavailable' | 'stale';
}

export interface WorkItem {
  id: WorkItemId;
  opportunityId: OpportunityId;
  platform: WorkPlatform;
  title: string;
  description: string;
  url: string;
  status: ExecState;
  preparedAt?: string;
  approvedAt?: string;
  executedAt?: string;
  submittedAt?: string;
  verifiedAt?: string;
  paidAt?: string;
  estimatedHours: number;
  actualHours?: number;
  expectedPayment: Money;
  actualPayment?: Money;
  risk: number;
  blockers: string[];
  nextAction: string;
  humanGateRequired: boolean;
  humanGateReason?: string;
  createdAt: string;
  updatedAt: string;
}

export interface ExecutionPlan {
  executionId: ExecutionId;
  workItemId: WorkItemId;
  steps: ExecutionStep[];
  estimatedTotalHours: number;
  actualTotalHours?: number;
  aiAssistance: AiAssistance[];
  humanGates: HumanGate[];
  currentStep: number;
  status: 'planned' | 'in_progress' | 'waiting_human' | 'completed' | 'failed';
  createdAt: string;
  startedAt?: string;
  completedAt?: string;
}

export interface ExecutionStep {
  stepId: string;
  name: string;
  description: string;
  type: 'ai' | 'human' | 'automated' | 'verification';
  estimatedHours: number;
  actualHours?: number;
  status: 'pending' | 'in_progress' | 'completed' | 'failed' | 'skipped';
  dependencies: string[];
  artifacts: string[];
}

export interface AiAssistance {
  assistanceId: string;
  stepId: string;
  type: 'code_generation' | 'research' | 'analysis' | 'testing' | 'documentation' | 'review';
  prompt: string;
  result?: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  tokensUsed?: number;
  cost?: Money;
  createdAt: string;
  completedAt?: string;
}

export interface HumanGate {
  gateId: string;
  stepId: string;
  type: 'approval' | 'review' | 'decision' | 'credential' | 'manual_action';
  description: string;
  required: boolean;
  status: 'pending' | 'approved' | 'rejected' | 'requested_info' | 'escalated';
  requestedAt: string;
  resolvedAt?: string;
  resolvedBy?: string;
  resolution?: string;
}

export interface RevenueRecord {
  recordId: TransactionId;
  workItemId: WorkItemId;
  platform: WorkPlatform;
  amount: Money;
  status: PaymentStatus;
  platformTransactionId?: string;
  platformFee?: Money;
  netAmount: Money;
  exchangeRate: number;
  receivedAt?: string;
  verifiedAt?: string;
  metadata: Record<string, unknown>;
}

export interface RevenueMetrics {
  platform: string;
  currency: string;
  totalEarned: Money;
  pendingAmount: Money;
  completedAmount: Money;
  failedAmount: Money;
  expectedAmount: Money;
  avgProcessingTimeHours: number;
  successRate: number;
  lastUpdated: string;
}

export interface Notification {
  notificationId: NotificationId;
  type: NotificationType;
  level: NotificationLevel;
  title: string;
  message: string;
  targetDevices: DevicePlatform[];
  deepLink?: string;
  actionRequired: boolean;
  actionType?: string;
  payload: Record<string, unknown>;
  createdAt: string;
  readAt?: string;
  dismissedAt?: string;
}

export interface ApprovalRequest {
  approvalId: ApprovalId;
  workItemId?: WorkItemId;
  title: string;
  description: string;
  amount?: Money;
  riskLevel: 'low' | 'medium' | 'high' | 'critical';
  requestedBy: string;
  requestedAt: string;
  expiresAt?: string;
  status: 'pending' | 'approved' | 'rejected' | 'expired' | 'escalated';
  approverId?: string;
  decidedAt?: string;
  decision?: ApprovalAction;
  resolution?: string;
  targetDevices: DevicePlatform[];
  deepLink?: string;
}

export interface ApprovalResponse {
  approvalId: ApprovalId;
  action: ApprovalAction;
  respondedBy: string;
  respondedAt: string;
  resolution?: string;
}

export interface DeviceStatus {
  deviceId: string;
  platform: DevicePlatform;
  name: string;
  online: boolean;
  lastSeen: string;
  batteryLevel?: number;
  pushEnabled: boolean,
  notificationsEnabled: boolean,
  approvalsEnabled: boolean,
  syncStatus: SyncStatus,
  lastSyncAt?: string,
}

export interface SystemStatus {
  backendOnline: boolean;
  schedulerRunning: boolean;
  activeWorkflows: number;
  pendingApprovals: number;
  findingsTotal: number;
  findingsConfirmed: number;
  targetsActive: number;
  healthScore: number;
  lastUpdated: string;
  queueDepth: number;
  sidecarRunning: boolean;
  diskUsagePercent: number;
  memoryUsagePercent: number;
}

export interface SyncEvent {
  eventId: string;
  entityType: string;
  entityId: string;
  operation: 'create' | 'update' | 'delete' | 'sync';
  payload: Record<string, unknown>;
  deviceId: string;
  timestamp: string;
  version: number;
}

export interface ConflictResolution {
  entityId: string;
  localVersion: Record<string, unknown>;
  remoteVersion: Record<string, unknown>;
  resolution: 'local' | 'remote' | 'merge' | 'manual';
  resolvedAt: string;
  resolvedBy: string;
}

// ============================================
// API CONTRACTS (Request/Response)
// ============================================

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
  meta?: {
    timestamp: string;
    requestId: string;
    version: string;
  };
}

export interface PaginatedResponse<T> extends ApiResponse<T[]> {
  meta: {
    timestamp: string;
    requestId: string;
    version: string;
    pagination: {
      page: number;
      limit: number;
      total: number;
      totalPages: number;
    };
  };
}

export interface HealthResponse {
  status: 'ok' | 'degraded' | 'down';
  version: string;
  uptime: number;
  checks: Record<string, { status: 'ok' | 'degraded' | 'down'; latency?: number; message?: string }>;
}

export interface DeviceRegisterRequest {
  deviceId: string;
  platform: DevicePlatform;
  name: string;
  pushToken?: string;
  capabilities: string[];
}

export interface DeviceRegisterResponse {
  deviceId: string;
  registered: boolean;
  authToken: string;
  expiresAt: string;
}

export interface SyncRequest {
  deviceId: string;
  lastSyncAt: string;
  events: SyncEvent[];
}

export interface SyncResponse {
  success: boolean;
  events: SyncEvent[];
  conflicts: ConflictResolution[];
  serverTime: string;
}

export interface WatchStatusResponse {
  systemOnline: boolean;
  schedulerRunning: boolean;
  activeWorkflows: number;
  pendingApprovals: number;
  findingsTotal: number;
  findingsConfirmed: number;
  targetsActive: number;
  healthScore: number;
  lastUpdated: string;
}

export interface WatchNotificationPayload {
  title: string;
  message: string;
  level: 'critical' | 'high' | 'medium' | 'low';
  requiresAction: boolean;
  actionType?: string;
}

export interface WatchApprovalPayload {
  title: string;
  description: string;
  workflowId?: string;
}

export interface MobileAppConfig {
  deviceId: string;
  userId: string;
  syncInterval: number;
  pushEnabled: boolean;
  notificationsEnabled: boolean;
  approvalsEnabled: boolean;
  autoSync: boolean;
  offlineMode: boolean;
  theme: 'tesla' | 'system';
  language: string;
  timezone: string;
}

export interface WorkBankSummary {
  totalItems: number;
  readyToDeliver: number;
  needsAccess: number;
  inProgress: number;
  deliveredToday: number;
  expectedToday: Money;
  expectedWeek: Money;
  expectedMonth: Money;
  topOpportunities: Opportunity[];
  dailyTarget: number;
  weeklyTarget: number;
  monthlyTarget: number;
  progress: {
    daily: number;
    weekly: number;
    monthly: number;
  };
}

export interface IncomePlanPhase {
  phase: 'today' | 'this_week' | 'this_month';
  opportunities: Opportunity[];
  totalExpected: Money;
  totalHours: number;
  topPick: Opportunity | null;
  skillGap: string[];
}

export interface ApplicationAssistantStep {
  stepId: string;
  platform: WorkPlatform;
  title: string;
  description: string;
  requirements: string[];
  estimatedTimeMinutes: number;
  completed: boolean;
  current: boolean;
  fields: ApplicationField[];
}

export interface ApplicationField {
  fieldId: string;
  label: string;
  type: 'text' | 'email' | 'password' | 'url' | 'select' | 'multiselect' | 'file' | 'textarea' | 'boolean';
  required: boolean;
  placeholder?: string;
  options?: string[];
  validation?: string;
  suggestion?: string;
}

export interface ApplicationPlan {
  platform: WorkPlatform;
  priority: number;
  estimatedEarnings: Money;
  estimatedTimeHours: number,
  barrierLevel: 'zero' | 'low' | 'medium' | 'high',
  steps: ApplicationAssistantStep[],
  nextStep: ApplicationAssistantStep | null,
  progress: number,
  status: 'not_started' | 'in_progress' | 'completed' | 'rejected' | 'paused',
}

export interface ExecutionQueueStatus {
  total: number;
  byStatus: Record<ExecState, number>;
  oldestPending?: string;
  processing: number;
  waitingHuman: number;
}

export interface SchedulerJob {
  jobId: string;
  name: string;
  schedule: string;
  enabled: boolean;
  lastRun?: string;
  nextRun?: string;
  lastStatus: 'success' | 'failed' | 'running' | 'pending';
  lastDuration?: number;
  lastError?: string;
}

export interface HealthCheck {
  name: string;
  status: 'ok' | 'degraded' | 'down';
  latencyMs?: number;
  message?: string;
  lastCheck: string;
}

export interface SystemHealthResponse {
  status: 'ok' | 'degraded' | 'down';
  score: number;
  checks: HealthCheck[];
  timestamp: string;
  version: string;
}

export interface EconomicIndicators {
  evPerHumanHour: number;
  expectedCashPerHour: number;
  acceptanceRate: number;
  paymentReliability: number;
  cashSpeedDays: number;
  qualificationCostHours: number;
  automationRatio: number;
  riskScore: number;
}

export interface OpportunityFilters {
  categories?: OpportunityCategory[];
  platforms?: WorkPlatform[];
  minPayment?: number;
  maxPayment?: number;
  maxHours?: number;
  minEvPerHour?: number;
  maxRisk?: number;
  paymentMethods?: PaymentMethod[];
  countries?: string[];
  remoteOnly?: boolean;
  zeroBarrierOnly?: boolean;
  availability?: 'available' | 'limited' | 'unknown' | 'unavailable' | 'stale';
  search?: string;
  sortBy?: 'ev' | 'payment' | 'hours' | 'risk' | 'discovered';
  sortOrder?: 'asc' | 'desc';
  limit?: number;
  offset?: number;
}

export interface RecommendationRequest {
  profile: UserProfile;
  opportunities: Opportunity[];
  filters?: OpportunityFilters;
  mode?: 'balanced' | 'fast_income' | 'max_success' | 'max_income';
  limit?: number;
}

export interface RecommendationResponse {
  recommendations: Array<{
    opportunity: Opportunity;
    score: number;
    evPerHumanHour: number;
    acceptanceProbability: number;
    cashSpeedDays: number;
    reasoning: string;
    riskFactors: string[];
    enablers: string[];
    blockers: string[];
  }>;
  fallbackUsed: boolean;
  warnings: string[];
  totalAnalyzed: number;
}

export interface WorkBankCycleRequest {
  target?: number;
  filters?: OpportunityFilters;
  forceRefresh?: boolean;
}

export interface WorkBankCycleResponse {
  summary: WorkBankSummary;
  newItems: number;
  prepared: number;
  rejected: number;
  durationMs: number;
}

export interface IncomePlanRequest {
  profile: UserProfile;
  horizon: 'today' | 'this_week' | 'this_month' | 'custom';
  customDays?: number;
  mode?: 'balanced' | 'conservative' | 'aggressive';
}

export interface IncomePlanResponse {
  phases: IncomePlanPhase[];
  totalExpected: Money;
  totalHours: number;
  commandCenter: {
    today: Money;
    thisWeek: Money;
    thisMonth: Money;
    conservative: Money;
    optimistic: Money;
    variables: {
      acceptanceRate: number;
      hoursPerWeek: number;
      automationRatio: number;
    };
  };
}

export interface NextBestAction {
  action: 'discover' | 'prepare' | 'execute' | 'approve' | 'deliver' | 'verify' | 'learn' | 'wait';
  title: string;
  description: string;
  opportunityId?: string;
  workItemId?: string;
  estimatedHours: number;
  expectedPayment: Money;
  evPerHumanHour: number;
  acceptanceProbability: number;
  cashSpeedDays: number;
  risk: number;
  reasoning: string;
  deepLink?: string;
  urgency: 'low' | 'medium' | 'high' | 'critical';
}

export interface WatchPreviewData {
  status: WatchStatusResponse;
  notifications: Array<{
    notificationId: string;
    title: string;
    message: string;
    level: string;
    requiresAction: boolean;
    actionType?: string;
  }>;
  pendingApprovals: Array<{
    approvalId: string;
    title: string;
    description: string;
    amount?: Money;
    riskLevel: string;
  }>;
  quickActions: Array<{
    action: 'approve' | 'reject' | 'acknowledge' | 'open_phone' | 'pause' | 'resume';
    label: string;
    targetId?: string;
  }>;
}

export interface MobileAppState {
  deviceId: string;
  userId: string;
  syncStatus: SyncStatus;
  lastSyncAt?: string;
  pendingSyncCount: number;
  offlineMode: boolean;
  notifications: Notification[];
  pendingApprovals: ApprovalRequest[];
  workBank: WorkBankSummary;
  incomePlan: IncomePlanResponse;
  nextBestAction: NextBestAction | null;
  watchPreview: WatchPreviewData;
  systemStatus: SystemStatus;
}



export const CONTRACT_VERSION = '1.0.0-alpha';
export const CONTRACT_DATE = '2026-08-26';