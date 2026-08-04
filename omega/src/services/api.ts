import { ApiResponse, AuthState } from '@types';

const API_BASE = process.env.EXPO_PUBLIC_API_URL || 'https://api.ownex.local';

class ApiService {
  private baseUrl: string;
  private token: string | null = null;

  constructor(baseUrl: string = API_BASE) {
    this.baseUrl = baseUrl;
  }

  setToken(token: string | null) {
    this.token = token;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...(this.token && { Authorization: `Bearer ${this.token}` }),
      ...options.headers,
    };

    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      ...options,
      headers,
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new Error(data.error?.message || `HTTP ${response.status}`);
    }

    return data as ApiResponse<T>;
  }

  // Auth
  async login(username: string, password: string): Promise<ApiResponse<{ token: string; refresh: string; user: any }>> {
    return this.request('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    });
  }

  async refreshToken(refreshToken: string): Promise<ApiResponse<{ token: string; refresh: string }>> {
    return this.request('/api/auth/refresh', {
      method: 'POST',
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
  }

  async validateToken(token: string): Promise<boolean> {
    try {
      await this.request('/api/auth/validate', {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      return true;
    } catch {
      return false;
    }
  }

  async logout(): Promise<void> {
    await this.request('/api/auth/logout', { method: 'POST' });
  }

  // System
  async getSystemStatus(): Promise<ApiResponse<any>> {
    return this.request('/api/system/status');
  }

  async getSystemHealth(): Promise<ApiResponse<any>> {
    return this.request('/api/system/health');
  }

  async getSystemMetrics(): Promise<ApiResponse<any>> {
    return this.request('/api/system/metrics');
  }

  async getConnectedDevices(): Promise<ApiResponse<any[]>> {
    return this.request('/api/system/devices');
  }

  // Daemon control
  async getDaemonStatus(): Promise<ApiResponse<any>> {
    return this.request('/api/system/daemon/status');
  }

  async startDaemon(): Promise<ApiResponse<any>> {
    return this.request('/api/system/daemon/start', { method: 'POST' });
  }

  async stopDaemon(): Promise<ApiResponse<any>> {
    return this.request('/api/system/daemon/stop', { method: 'POST' });
  }

  // Agents
  async getAgents(): Promise<ApiResponse<any[]>> {
    return this.request('/api/agents');
  }

  async getAgent(agentId: string): Promise<ApiResponse<any>> {
    return this.request(`/api/agents/${agentId}`);
  }

  async startAgent(agentId: string): Promise<ApiResponse<any>> {
    return this.request(`/api/agents/${agentId}/start`, { method: 'POST' });
  }

  async stopAgent(agentId: string): Promise<ApiResponse<any>> {
    return this.request(`/api/agents/${agentId}/stop`, { method: 'POST' });
  }

  async pauseAgent(agentId: string): Promise<ApiResponse<any>> {
    return this.request(`/api/agents/${agentId}/pause`, { method: 'POST' });
  }

  async getAgentLogs(agentId: string, limit: number = 100): Promise<ApiResponse<any[]>> {
    return this.request(`/api/agents/${agentId}/logs?limit=${limit}`);
  }

  // Workflows
  async getWorkflows(params?: { status?: string; limit?: number }): Promise<ApiResponse<any[]>> {
    const query = new URLSearchParams();
    if (params?.status) query.set('status', params.status);
    if (params?.limit) query.set('limit', params.limit.toString());
    return this.request(`/api/workflows?${query.toString()}`);
  }

  async getWorkflow(workflowId: string): Promise<ApiResponse<any>> {
    return this.request(`/api/workflows/${workflowId}`);
  }

  async startWorkflow(workflowId: string, config?: Record<string, unknown>): Promise<ApiResponse<any>> {
    return this.request(`/api/workflows/${workflowId}/start`, {
      method: 'POST',
      body: JSON.stringify(config || {}),
    });
  }

  async stopWorkflow(workflowId: string): Promise<ApiResponse<any>> {
    return this.request(`/api/workflows/${workflowId}/stop`, { method: 'POST' });
  }

  async pauseWorkflow(workflowId: string): Promise<ApiResponse<any>> {
    return this.request(`/api/workflows/${workflowId}/pause`, { method: 'POST' });
  }

  async approveWorkflowStep(workflowId: string, stepId: string, approved: boolean): Promise<ApiResponse<any>> {
    return this.request(`/api/workflows/${workflowId}/steps/${stepId}/approve`, {
      method: 'POST',
      body: JSON.stringify({ approved }),
    });
  }

  // Opportunities
  async getOpportunities(params?: { type?: string; status?: string; platform?: string; limit?: number }): Promise<ApiResponse<any[]>> {
    const query = new URLSearchParams();
    if (params?.type) query.set('type', params.type);
    if (params?.status) query.set('status', params.status);
    if (params?.platform) query.set('platform', params.platform);
    if (params?.limit) query.set('limit', params.limit.toString());
    return this.request(`/api/opportunities?${query.toString()}`);
  }

  async getOpportunity(opportunityId: string): Promise<ApiResponse<any>> {
    return this.request(`/api/opportunities/${opportunityId}`);
  }

  async analyzeOpportunity(opportunityId: string): Promise<ApiResponse<any>> {
    return this.request(`/api/opportunities/${opportunityId}/analyze`, { method: 'POST' });
  }

  async submitOpportunity(opportunityId: string, data: Record<string, unknown>): Promise<ApiResponse<any>> {
    return this.request(`/api/opportunities/${opportunityId}/submit`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // Findings
  async getFindings(params?: { status?: string; severity?: string; limit?: number }): Promise<ApiResponse<any[]>> {
    const query = new URLSearchParams();
    if (params?.status) query.set('status', params.status);
    if (params?.severity) query.set('severity', params.severity);
    if (params?.limit) query.set('limit', params.limit.toString());
    return this.request(`/api/findings?${query.toString()}`);
  }

  async getFinding(findingId: string): Promise<ApiResponse<any>> {
    return this.request(`/api/findings/${findingId}`);
  }

  async validateFinding(findingId: string, validated: boolean): Promise<ApiResponse<any>> {
    return this.request(`/api/findings/${findingId}/validate`, {
      method: 'POST',
      body: JSON.stringify({ validated }),
    });
  }

  // Notifications
  async getNotifications(params?: { unreadOnly?: boolean; limit?: number }): Promise<ApiResponse<any[]>> {
    const query = new URLSearchParams();
    if (params?.unreadOnly) query.set('unread', 'true');
    if (params?.limit) query.set('limit', params.limit.toString());
    return this.request(`/api/notifications?${query.toString()}`);
  }

  async markNotificationRead(notificationId: string): Promise<ApiResponse<any>> {
    return this.request(`/api/notifications/${notificationId}/read`, { method: 'POST' });
  }

  async markAllNotificationsRead(): Promise<ApiResponse<any>> {
    return this.request('/api/notifications/read-all', { method: 'POST' });
  }

  // MERLIN
  async merlinChat(message: string, context?: Record<string, unknown>): Promise<ApiResponse<any>> {
    return this.request('/api/merlin/chat', {
      method: 'POST',
      body: JSON.stringify({ message, context }),
    });
  }

  async merlinCommand(command: string, args?: Record<string, unknown>): Promise<ApiResponse<any>> {
    return this.request('/api/merlin/command', {
      method: 'POST',
      body: JSON.stringify({ command, args }),
    });
  }

  async getMerlinSuggestions(): Promise<ApiResponse<string[]>> {
    return this.request('/api/merlin/suggestions');
  }

  // Targets
  async getTargets(params?: { active?: boolean; platform?: string }): Promise<ApiResponse<any[]>> {
    const query = new URLSearchParams();
    if (params?.active !== undefined) query.set('active', params.active.toString());
    if (params?.platform) query.set('platform', params.platform);
    return this.request(`/api/targets?${query.toString()}`);
  }

  async addTarget(target: { name: string; domain: string; platform?: string }): Promise<ApiResponse<any>> {
    return this.request('/api/targets', {
      method: 'POST',
      body: JSON.stringify(target),
    });
  }

  // Reports
  async getReports(params?: { type?: string; limit?: number }): Promise<ApiResponse<any[]>> {
    const query = new URLSearchParams();
    if (params?.type) query.set('type', params.type);
    if (params?.limit) query.set('limit', params.limit.toString());
    return this.request(`/api/reports?${query.toString()}`);
  }

  async generateReport(type: string, config: Record<string, unknown>): Promise<ApiResponse<any>> {
    return this.request('/api/reports/generate', {
      method: 'POST',
      body: JSON.stringify({ type, config }),
    });
  }

  // Settings
  async getSettings(): Promise<ApiResponse<any>> {
    return this.request('/api/settings');
  }

  async updateSettings(settings: Record<string, unknown>): Promise<ApiResponse<any>> {
    return this.request('/api/settings', {
      method: 'PATCH',
      body: JSON.stringify(settings),
    });
  }

  // Health check
  async healthCheck(): Promise<{ status: string; app: string; version: string }> {
    const response = await fetch(`${this.baseUrl}/api/health`);
    return response.json();
  }
}

export const apiService = new ApiService();