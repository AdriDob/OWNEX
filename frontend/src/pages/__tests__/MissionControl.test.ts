import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'
import MissionControl from '@/pages/MissionControl.vue'
import type { OwnexDashboardData } from '@/services/ownexData'

const mockFetchDashboard = vi.hoisted(() => vi.fn())
const mockFetchIncomePlan = vi.hoisted(() => vi.fn())
vi.mock('@/services/ownexData', () => ({
  // Factory explícito: cualquier export nuevo que consuma MissionControl
  // debe agregarse acá (o el componente muere en setup con render vacío).
  fetchOwnexDashboard: (...args: unknown[]) => mockFetchDashboard(...args),
  fetchIncomePlan: (...args: unknown[]) => mockFetchIncomePlan(...args),
}))

const mockSettingsStore = vi.hoisted(() => ({
  data: {
    general: { userName: 'TestOp' },
    missionControl: { autoMode: false, parallelism: 2, speed: 'normal', depth: 3 },
    onboarding: { completed: true, skipped: false },
  },
  onboardingNeeded: false,
  loadFromBackend: vi.fn(),
}))
vi.mock('@/stores/settings', () => ({
  useSettingsStore: () => mockSettingsStore,
}))

function makeDashboard(overrides: Partial<OwnexDashboardData> = {}): OwnexDashboardData {
  return {
    throughputStages: [
      { label: 'Detectado', value: 4, color: 'var(--ownex-text-primary)' },
      { label: 'Validado', value: 2, color: 'var(--ownex-text-secondary)' },
      { label: 'Confirmado', value: 1, color: 'var(--ownex-green)' },
      { label: 'Reportado', value: 0, color: 'var(--ownex-yellow)' },
    ],
    throughputEfficiency: 25,
    agents: [
      { name: 'Hermes', status: 'online', description: 'Orquestación' },
      { name: 'OpenCode', status: 'online', description: 'Implementación' },
    ],
    opportunities: [],
    nextAction: null,
    knowledgeFeed: [],
    revenue: null,
    cycles: [],
    systemHealth: 92,
    systemStatus: 'healthy',
    pendingApprovals: 0,
    timestamp: new Date().toISOString(),
    ...overrides,
  }
}

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
  // Default: plan resuelto vacío (los tests que lo necesiten lo pisan).
  mockFetchIncomePlan.mockResolvedValue({ next_action: null, income_command_center: {} })
})

function createWrapper() {
  // MissionControl usa useRouter() (acción real de NextBestAction) → el
  // wrapper necesita un router instalado, no solo stubs de router-link.
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/:pathMatch(.*)*', component: { template: '<div />' } }],
  })
  return mount(MissionControl, {
    global: {
      plugins: [router],
      stubs: {
        'router-link': true,
        'router-view': true,
        Transition: false,
        LoadingState: { template: '<div class="mock-loading" />' },
        // Espeja el contrato real de components/shared/ErrorState.vue
        ErrorState: {
          props: ['title', 'error', 'action'],
          template: '<div class="mock-error">{{ title }} {{ error }}</div>',
        },
        ThroughputCore: { template: '<div class="mock-throughput" />' },
        AgentFleet: { template: '<div class="mock-fleet" />' },
        OpportunityRadar: { template: '<div class="mock-radar" />' },
        NextBestAction: { template: '<div class="mock-nba" />' },
        DirectWorkRadar: { template: '<div class="mock-dwr" />' },
        ReportPipeline: { template: '<div class="mock-rp" />' },
        WorkCyclesGrid: { template: '<div class="mock-wcg" />' },
        KnowledgeFeed: { template: '<div class="mock-kf" />' },
      },
    },
  })
}

describe('MissionControl page', () => {
  it('shows loading state initially', async () => {
    mockFetchDashboard.mockImplementation(() => new Promise(() => {}))
    const wrapper = createWrapper()
    expect(wrapper.find('.mock-loading').exists()).toBe(true)
  })

  it('shows error state on API failure', async () => {
    mockFetchDashboard.mockRejectedValue(new Error('Connection refused'))
    const wrapper = createWrapper()
    await new Promise((resolve) => setTimeout(resolve, 0))
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('Error al cargar Mission Control')
    expect(wrapper.text()).toContain('Connection refused')
  })

  it('shows empty state when no targets and no findings', async () => {
    mockFetchDashboard.mockResolvedValue(makeDashboard())
    const wrapper = createWrapper()
    await new Promise((resolve) => setTimeout(resolve, 0))
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('OWNEX MISSION CONTROL')
    expect(wrapper.text()).toContain('Salud del sistema')
  })

  it('shows mission control with KPIs when data is loaded', async () => {
    mockFetchDashboard.mockResolvedValue(
      makeDashboard({
        throughputStages: [
          { label: 'Detectado', value: 15, color: 'var(--ownex-text-primary)' },
          { label: 'Validado', value: 8, color: 'var(--ownex-text-secondary)' },
          { label: 'Confirmado', value: 3, color: 'var(--ownex-green)' },
          { label: 'Reportado', value: 0, color: 'var(--ownex-yellow)' },
        ],
        opportunities: [
          {
            id: '1',
            title: 'Target A',
            source: 'bugcrowd',
            type: 'bug-bounty',
            reward: 1000,
            confidence: 85,
            effort: 'low',
            action: 'review',
          },
        ],
        nextAction: { title: 'Test SQLi', reason: 'High impact', effort: 'low', estimatedReward: 1000 },
        systemHealth: 92,
        systemStatus: 'healthy',
      }),
    )
    const wrapper = createWrapper()
    await new Promise((resolve) => setTimeout(resolve, 0))
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('OWNEX MISSION CONTROL')
    expect(wrapper.text()).toContain('Operador')
    expect(wrapper.text()).toContain('Salud del sistema')
    expect(wrapper.text()).toContain('Acciones rápidas')
  })

  it('shows degraded banner when refresh fails after initial load', async () => {
    mockFetchDashboard.mockResolvedValueOnce(makeDashboard())
    mockFetchDashboard.mockRejectedValueOnce(new Error('timeout'))
    const wrapper = createWrapper()
    await new Promise((resolve) => setTimeout(resolve, 0))
    await wrapper.vm.$nextTick()
    wrapper.vm.$options.methods
    // trigger a second load via the refresh button
    const refreshBtn = wrapper.findAll('button').find((b) => b.text().includes('Actualizar'))
    expect(refreshBtn).toBeDefined()
    await refreshBtn!.trigger('click')
    await new Promise((resolve) => setTimeout(resolve, 0))
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('Datos parciales')
  })
})
