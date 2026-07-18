import type { Component } from 'vue'

export interface WidgetSize {
  cols: number
  rows: number
}

export interface WidgetDef {
  id: string
  name: string
  description: string
  icon: string
  defaultSize: WidgetSize
  component: () => Promise<Component>
  dataSource: string
  refreshInterval: number
}

const registry: Record<string, WidgetDef> = {
  'health-score': {
    id: 'health-score',
    name: 'Health Score',
    description: 'System health score KPI',
    icon: 'HeartPulse',
    defaultSize: { cols: 2, rows: 1 },
    component: () => import('./widgets/HealthScoreWidget.vue'),
    dataSource: '/api/core/health/summary',
    refreshInterval: 30,
  },
  'active-targets': {
    id: 'active-targets',
    name: 'Active Targets',
    description: 'Active targets count with change indicator',
    icon: 'Target',
    defaultSize: { cols: 1, rows: 1 },
    component: () => import('./widgets/ActiveTargetsWidget.vue'),
    dataSource: '/api/mission/widget',
    refreshInterval: 30,
  },
  'findings-summary': {
    id: 'findings-summary',
    name: 'Findings Summary',
    description: 'Findings by severity level',
    icon: 'Bug',
    defaultSize: { cols: 2, rows: 1 },
    component: () => import('./widgets/FindingsSummaryWidget.vue'),
    dataSource: '/api/findings',
    refreshInterval: 30,
  },
  'revenue-overview': {
    id: 'revenue-overview',
    name: 'Revenue Overview',
    description: 'Revenue summary cards',
    icon: 'DollarSign',
    defaultSize: { cols: 2, rows: 1 },
    component: () => import('./widgets/RevenueOverviewWidget.vue'),
    dataSource: '/api/revenue/mission-summary',
    refreshInterval: 60,
  },
  'scheduler-status': {
    id: 'scheduler-status',
    name: 'Scheduler Status',
    description: 'Scheduler pipeline status',
    icon: 'Clock',
    defaultSize: { cols: 2, rows: 1 },
    component: () => import('./widgets/SchedulerStatusWidget.vue'),
    dataSource: '/api/system/status',
    refreshInterval: 15,
  },
  'recent-activity': {
    id: 'recent-activity',
    name: 'Recent Activity',
    description: 'Recent system activity feed',
    icon: 'Activity',
    defaultSize: { cols: 3, rows: 1 },
    component: () => import('./widgets/RecentActivityWidget.vue'),
    dataSource: '/api/activity',
    refreshInterval: 30,
  },
  'knowledge-graph-mini': {
    id: 'knowledge-graph-mini',
    name: 'Knowledge Graph',
    description: 'Mini knowledge graph visualization',
    icon: 'Network',
    defaultSize: { cols: 3, rows: 1 },
    component: () => import('./widgets/KnowledgeGraphMiniWidget.vue'),
    dataSource: '/api/knowledge-graph/nodes',
    refreshInterval: 120,
  },
  'top-priorities': {
    id: 'top-priorities',
    name: 'Top Priorities',
    description: 'Priority actions list',
    icon: 'Bell',
    defaultSize: { cols: 2, rows: 1 },
    component: () => import('./widgets/TopPrioritiesWidget.vue'),
    dataSource: '/api/mission/status',
    refreshInterval: 30,
  },
  'bounty-summary': {
    id: 'bounty-summary',
    name: 'Bounty Summary',
    description: 'Bounty and earnings summary',
    icon: 'TrendingUp',
    defaultSize: { cols: 1, rows: 1 },
    component: () => import('./widgets/BountySummaryWidget.vue'),
    dataSource: '/api/revenue/mission-summary',
    refreshInterval: 60,
  },
  'assistant-tip': {
    id: 'assistant-tip',
    name: 'Assistant Tip',
    description: 'Contextual assistant tip',
    icon: 'Sparkles',
    defaultSize: { cols: 2, rows: 1 },
    component: () => import('./widgets/AssistantTipWidget.vue'),
    dataSource: '/api/mission/status',
    refreshInterval: 120,
  },
}

export function getWidgetDef(id: string): WidgetDef | undefined {
  return registry[id]
}

export function getAvailableWidgets(): WidgetDef[] {
  return Object.values(registry)
}
