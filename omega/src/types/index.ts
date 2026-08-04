// OWNEX Omega Type Definitions

// Auth
export interface AuthState {
  auth: {
    token: string | null;
    refresh: string | null;
    user: User | null;
    isAuthenticated: boolean;
  };
}

export interface User {
  id: string;
  username: string;
  email: string;
  role: 'admin' | 'operator' | 'viewer';
  devices: string[];
  createdAt: string;
  lastLogin: string;
}

// System
export interface SystemState {
  system: {
    status: 'online' | 'offline' | 'connecting' | 'error' | 'maintenance';
    aiRuntime: 'healthy' | 'degraded' | 'offline' | 'unknown';
    connectedDevices: ConnectedDevice[];
    agentsActive: number;
    workflowsRunning: number;
    cpu: number;
    memory: number;
    disk: number;
    lastSync: number | null;
  };
}

export interface ConnectedDevice {
  id: string;
  name: string;
  type: 'desktop' | 'mobile' | 'watch' | 'server';
  status: 'online' | 'offline' | 'syncing';
  lastSeen: number;
  capabilities: string[];
  platform: string;
  version: string;
}

// Agents
export interface AgentState {
  agents: Agent[];
}

export interface Agent {
  id: string;
  name: string;
  type: 'scanner' | 'analyzer' | 'validator' | 'reporter' | 'learning' | 'custom';
  status: 'idle' | 'running' | 'paused' | 'error' | 'offline';
  currentTask: string | null;
  progress: number;
  lastHeartbeat: number;
  metrics: AgentMetrics;
  config: Record<string, unknown>;
}

export interface AgentMetrics {
  tasksCompleted: number;
  tasksFailed: number;
  avgDuration: number;
  successRate: number;
  findingsGenerated: number;
}

// Workflows
export interface WorkflowState {
  workflows: Workflow[];
}

export interface Workflow {
  id: string;
  name: string;
  type: 'scan' | 'analysis' | 'validation' | 'report' | 'discovery' | 'custom';
  status: 'pending' | 'running' | 'paused' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  currentStep: string | null;
  steps: WorkflowStep[];
  startedAt: number | null;
  completedAt: number | null;
  triggeredBy: 'manual' | 'scheduled' | 'event' | 'webhook';
  metadata: Record<string, unknown>;
}

export interface WorkflowStep {
  id: string;
  name: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
  agentId: string | null;
  startedAt: number | null;
  completedAt: number | null;
  output: Record<string, unknown> | null;
  error: string | null;
}

// Notifications
export interface NotificationState {
  notifications: Notification[];
  unreadCount: number;
}

export interface Notification {
  id: string;
  type: 'info' | 'success' | 'warning' | 'critical' | 'approval' | 'agent' | 'workflow' | 'finding' | 'system';
  title: string;
  message: string;
  priority: 'low' | 'medium' | 'high' | 'critical';
  read: boolean;
  timestamp: number;
  actionUrl?: string;
  actionLabel?: string;
  metadata?: Record<string, unknown>;
  source: 'system' | 'agent' | 'workflow' | 'merlin' | 'desktop' | 'api';
}

// Opportunities
export interface OpportunityState {
  opportunities: Opportunity[];
}

export interface Opportunity {
  id: string;
  type: 'bounty' | 'freelance' | 'dev' | 'data' | 'investment' | 'trading' | 'crypto';
  platform: string;
  title: string;
  description: string;
  reward: {
    min: number;
    max: number;
    currency: string;
    type: 'fixed' | 'range' | 'percentage' | 'unknown';
  };
  difficulty: 'trivial' | 'easy' | 'medium' | 'hard' | 'expert';
  tags: string[];
  url: string;
  deadline: number | null;
  status: 'new' | 'analyzing' | 'ready' | 'in_progress' | 'submitted' | 'accepted' | 'rejected' | 'expired';
  confidence: number;
  aiAnalysis: string | null;
  discoveredAt: number;
  updatedAt: number;
  metadata: Record<string, unknown>;
}

// MERLIN
export interface MerlinState {
  status: 'idle' | 'thinking' | 'responding' | 'error';
  messages: MerlinMessage[];
  suggestions: string[];
  context: Record<string, unknown>;
}

export interface MerlinMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: number;
  metadata?: Record<string, unknown>;
}

// Theme
export interface Theme {
  colors: ThemeColors;
  spacing: ThemeSpacing;
  typography: ThemeTypography;
  shadows: ThemeShadows;
  borderRadius: ThemeBorderRadius;
  animations: ThemeAnimations;
  zIndex: ThemeZIndex;
}

export interface ThemeColors {
  black: string;
  black50: string;
  black100: string;
  black200: string;
  black300: string;
  graphite: string;
  graphite50: string;
  graphite100: string;
  graphite200: string;
  white: string;
  white50: string;
  white100: string;
  white200: string;
  cyan: string;
  cyan50: string;
  cyan100: string;
  cyan200: string;
  cyan300: string;
  cyanDim: string;
  cyanDim50: string;
  electric: string;
  electric50: string;
  electric100: string;
  electricDim: string;
  success: string;
  success50: string;
  success100: string;
  successDim: string;
  warning: string;
  warning50: string;
  warning100: string;
  warningDim: string;
  critical: string;
  critical50: string;
  critical100: string;
  criticalDim: string;
  merlin: string;
  merlin50: string;
  merlinDim: string;
}

export interface ThemeSpacing {
  0: number;
  1: number;
  2: number;
  3: number;
  4: number;
  5: number;
  6: number;
  8: number;
  10: number;
  12: number;
  16: number;
  20: number;
  24: number;
}

export interface ThemeTypography {
  fontFamilies: {
    sans: string;
    mono: string;
    display: string;
  };
  fontSizes: {
    displayXL: number;
    displayLG: number;
    displayMD: number;
    displaySM: number;
    headingXL: number;
    headingLG: number;
    headingMD: number;
    headingSM: number;
    bodyLG: number;
    body: number;
    bodySM: number;
    caption: number;
    captionSM: number;
  };
  lineHeights: {
    tight: number;
    normal: number;
    relaxed: number;
  };
  letterSpacings: {
    tight: number;
    normal: number;
    wide: number;
  };
}

export interface ThemeShadows {
  sm: ViewShadow;
  md: ViewShadow;
  lg: ViewShadow;
  xl: ViewShadow;
  glow: ViewShadow;
  glowLG: ViewShadow;
  merlinGlow: ViewShadow;
}

export interface ViewShadow {
  shadowColor: string;
  shadowOffset: { width: number; height: number };
  shadowOpacity: number;
  shadowRadius: number;
  elevation: number;
}

export interface ThemeBorderRadius {
  none: number;
  sm: number;
  md: number;
  lg: number;
  xl: number;
  '2xl': number;
  full: number;
}

export interface ThemeAnimations {
  durations: {
    instant: number;
    fast: number;
    normal: number;
    medium: number;
    slow: number;
    slower: number;
    slowest: number;
  };
  easings: {
    spring: string;
    springSlow: string;
    easeOutQuart: string;
    easeInQuart: string;
  };
}

export interface ThemeZIndex {
  dropdown: number;
  sticky: number;
  modal: number;
  popover: number;
  tooltip: number;
  toast: number;
}

// API
export interface ApiResponse<T = unknown> {
  version: string;
  schema: string;
  data: T;
  error: ApiError | null;
  timestamp: string;
}

export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

// WebSocket
export interface WSMessage {
  type: string;
  payload: unknown;
  timestamp: number;
  id: string;
}

export interface WSEvent {
  event: string;
  data: unknown;
  priority: 'low' | 'medium' | 'high' | 'critical';
}

// Navigation
export type RootStackParamList = {
  Main: undefined;
  Auth: undefined;
  Onboarding: undefined;
  Settings: undefined;
  Profile: undefined;
  AgentDetail: { agentId: string };
  WorkflowDetail: { workflowId: string };
  OpportunityDetail: { opportunityId: string };
  MerlinChat: undefined;
  Notifications: undefined;
  SystemDiagnostics: undefined;
};

export type MainTabParamList = {
  Dashboard: undefined;
  Agents: undefined;
  Workflows: undefined;
  Opportunities: undefined;
  Merlin: undefined;
};

// Settings
export interface SettingsState {
  theme: 'light' | 'dark' | 'system';
  notifications: {
    push: boolean;
    email: boolean;
    inApp: boolean;
    criticalOnly: boolean;
  };
  sync: {
    autoSync: boolean;
    interval: number; // minutes
    wifiOnly: boolean;
  };
  security: {
    biometric: boolean;
    autoLock: number; // minutes
    sessionTimeout: number; // hours
  };
  merlin: {
    voiceEnabled: boolean;
    language: string;
    personality: 'professional' | 'casual' | 'technical' | 'minimal';
  };
  display: {
    compactMode: boolean;
    showMetrics: boolean;
    animations: boolean;
    haptics: boolean;
  };
}

// Watch companion types
export interface WatchState {
  systemStatus: 'online' | 'offline' | 'degraded';
  merlinAvailable: boolean;
  criticalAlerts: number;
  pendingApprovals: number;
  activeWorkflows: number;
  batteryLevel: number;
  isConnected: boolean;
  lastSync: number;
}

export interface WatchAction {
  type: 'approve' | 'reject' | 'pause' | 'resume' | 'status' | 'command';
  targetId: string;
  targetType: 'workflow' | 'agent' | 'approval' | 'system';
  payload?: Record<string, unknown>;
}