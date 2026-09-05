import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import * as SecureStore from 'expo-secure-store';
import { AuthState, SystemState, AgentState, WorkflowState, NotificationState, OpportunityState } from '@types/store';

interface OWEXStore extends AuthState, SystemState, AgentState, WorkflowState, NotificationState, OpportunityState {
  // Auth
  setAuth: (auth: AuthState) => void;
  clearAuth: () => void;
  refreshAuth: () => Promise<void>;
  setTheme: (theme: 'light' | 'dark') => void;
  
  // System
  updateSystemStatus: (status: Partial<SystemState>) => void;
  setConnectedDevices: (devices: SystemState['connectedDevices']) => void;
  
  // Agents
  updateAgent: (agentId: string, data: Partial<AgentState['agents'][0]>) => void;
  setAgents: (agents: AgentState['agents']) => void;
  
  // Workflows
  updateWorkflow: (workflowId: string, data: Partial<WorkflowState['workflows'][0]>) => void;
  setWorkflows: (workflows: WorkflowState['workflows']) => void;
  
  // Notifications
  addNotification: (notification: Omit<NotificationState['notifications'][0], 'id' | 'timestamp'>) => void;
  markNotificationRead: (id: string) => void;
  clearNotifications: () => void;
  
  // Opportunities
  updateOpportunity: (id: string, data: Partial<OpportunityState['opportunities'][0]>) => void;
  setOpportunities: (opportunities: OpportunityState['opportunities']) => void;
  
  // MERLIN
  setMerlinState: (state: Partial<MerlinState>) => void;
  addMerlinMessage: (message: MerlinMessage) => void;
  clearMerlinHistory: () => void;
}

interface MerlinState {
  status: 'idle' | 'thinking' | 'responding' | 'error';
  messages: MerlinMessage[];
  suggestions: string[];
  context: Record<string, unknown>;
}

interface MerlinMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: number;
  metadata?: Record<string, unknown>;
}

const secureStorage = {
  getItem: async (name: string) => {
    try {
      return await SecureStore.getItemAsync(name);
    } catch {
      return null;
    }
  },
  setItem: async (name: string, value: string) => {
    try {
      await SecureStore.setItemAsync(name, value);
    } catch (e) {
      console.warn('SecureStore setItem failed:', e);
    }
  },
  removeItem: async (name: string) => {
    try {
      await SecureStore.deleteItemAsync(name);
    } catch (e) {
      console.warn('SecureStore removeItem failed:', e);
    }
  },
};

const initialMerlinState: MerlinState = {
  status: 'idle',
  messages: [],
  suggestions: [
    'System status',
    'Active workflows',
    'New opportunities',
    'Agent health',
    'Run diagnostic',
  ],
  context: {},
};

export const useStore = create<OWEXStore>()(
  persist(
    (set, get) => ({
      // Auth
      auth: {
        token: null,
        refresh: null,
        user: null,
        isAuthenticated: false,
      },
      setAuth: (auth) => set({ auth: { ...auth, isAuthenticated: !!auth.token } }),
      clearAuth: () => set({ auth: { token: null, refresh: null, user: null, isAuthenticated: false } }),
      refreshAuth: async () => {
        const { auth, setAuth } = get();
        if (auth.refresh) {
          try {
            const response = await fetch(`${process.env.EXPO_PUBLIC_API_URL}/api/auth/refresh`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ refresh_token: auth.refresh }),
            });
            if (response.ok) {
              const data = await response.json();
              setAuth({ token: data.token, refresh: data.refresh, user: auth.user });
            } else {
              get().clearAuth();
            }
          } catch {
            get().clearAuth();
          }
        }
      },
      theme: 'dark',
      setTheme: (theme) => set({ theme }),
      
      // System
      system: {
        status: 'connecting',
        aiRuntime: 'unknown',
        connectedDevices: [],
        agentsActive: 0,
        workflowsRunning: 0,
        cpu: 0,
        memory: 0,
        disk: 0,
        lastSync: null,
      },
      updateSystemStatus: (status) => set((state) => ({ system: { ...state.system, ...status } })),
      setConnectedDevices: (devices) => set((state) => ({ system: { ...state.system, connectedDevices: devices } })),
      
      // Agents
      agents: [],
      updateAgent: (agentId, data) => set((state) => ({
        agents: state.agents.map(a => a.id === agentId ? { ...a, ...data } : a)
      })),
      setAgents: (agents) => set({ agents }),
      
      // Workflows
      workflows: [],
      updateWorkflow: (workflowId, data) => set((state) => ({
        workflows: state.workflows.map(w => w.id === workflowId ? { ...w, ...data } : w)
      })),
      setWorkflows: (workflows) => set({ workflows }),
      
      // Notifications
      notifications: [],
      unreadCount: 0,
      addNotification: (notification) => set((state) => {
        const newNotification = {
          ...notification,
          id: `notif-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          timestamp: Date.now(),
          read: false,
        };
        return {
          notifications: [newNotification, ...state.notifications].slice(0, 100),
          unreadCount: state.unreadCount + 1,
        };
      }),
      markNotificationRead: (id) => set((state) => ({
        notifications: state.notifications.map(n => n.id === id ? { ...n, read: true } : n),
        unreadCount: Math.max(0, state.unreadCount - 1),
      })),
      clearNotifications: () => set({ notifications: [], unreadCount: 0 }),
      
      // Opportunities
      opportunities: [],
      updateOpportunity: (id, data) => set((state) => ({
        opportunities: state.opportunities.map(o => o.id === id ? { ...o, ...data } : o)
      })),
      setOpportunities: (opportunities) => set({ opportunities }),
      
      // MERLIN
      merlin: initialMerlinState,
      setMerlinState: (state) => set((prev) => ({ merlin: { ...prev.merlin, ...state } })),
      addMerlinMessage: (message) => set((prev) => ({
        merlin: {
          ...prev.merlin,
          messages: [...prev.merlin.messages, message].slice(-50),
        }
      })),
      clearMerlinHistory: () => set({ merlin: { ...initialMerlinState, suggestions: get().merlin.suggestions } }),
    }),
    {
      name: 'ownex-omega-store',
      storage: createJSONStorage(() => secureStorage),
      partialize: (state) => ({
        auth: state.auth,
        theme: state.theme,
        merlin: { ...state.merlin, messages: state.merlin.messages.slice(-20) },
      }),
    }
  )
);

// Selectors
export const selectAuth = (state: OWEXStore) => state.auth;
export const selectTheme = (state: OWEXStore) => state.theme;
export const selectSystem = (state: OWEXStore) => state.system;
export const selectAgents = (state: OWEXStore) => state.agents;
export const selectWorkflows = (state: OWEXStore) => state.workflows;
export const selectNotifications = (state: OWEXStore) => state.notifications;
export const selectUnreadCount = (state: OWEXStore) => state.unreadCount;
export const selectOpportunities = (state: OWEXStore) => state.opportunities;
export const selectMerlin = (state: OWEXStore) => state.merlin;