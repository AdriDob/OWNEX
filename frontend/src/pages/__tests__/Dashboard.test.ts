import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import Dashboard from '@/pages/Dashboard.vue'

const mockGetOrionContext = vi.hoisted(() => vi.fn())
vi.mock('@/lib/api', () => ({
  getOrionContext: (...args: any[]) => mockGetOrionContext(...args),
}))

const mockSettingsStore = vi.hoisted(() => ({
  data: {
    general: { userName: 'DashOp' },
  },
}))
vi.mock('@/stores/settings', () => ({
  useSettingsStore: () => mockSettingsStore,
}))

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
})

function createWrapper() {
  return mount(Dashboard, {
    global: {
      stubs: {
        'router-link': true,
        'router-view': true,
        Transition: false,
        Skeleton: { template: '<div class="mock-skeleton" />' },
        Badge: { template: '<span class="mock-badge"><slot /></span>' },
        Button: { template: '<button class="mock-btn" @click="$emit(\'click\', $event)"><slot /></button>' },
        Card: { template: '<div class="mock-card"><slot /></div>' },
        BarChart: { template: '<div class="mock-barchart" />' },
        DoughnutChart: { template: '<div class="mock-doughnut" />' },
      },
    },
  })
}

const mockOrionContext = {
  counts: { targets: 10, endpoints: 250, findings: 45, confirmed_findings: 12, total_estimated_payout: 15000 },
  pipeline: { detected: 45, validated: 22, confirmed: 12, reported: 3 },
  system: { status: 'healthy', health_score: 88 },
  findings: { new_24h: 3, by_severity: { critical: 2, high: 5, medium: 10, low: 15, info: 13 } },
  next_action: { title: 'Test XSS', why_now: 'Easy win', effort: 'low', estimated_reward: '$500' },
  opportunities: { total: 8, top: [{ id: 1, name: 'Target X', domain: 'x.com', endpoints: 25, opportunity_score: 7.5 }] },
  activity_24h: { events: [{ type: 'finding', id: 1, severity: 'critical' }] },
  _meta: { version: '1.5.0' },
  scans: { active: 1 },
  verdicts: { by_status: { confirmed: 12, rejected: 3, inconclusive: 5, pending: 25 } },
}

describe('Dashboard page', () => {
  it('shows loading state on mount', () => {
    mockGetOrionContext.mockImplementation(() => new Promise(() => {}))
    const wrapper = createWrapper()
    expect(wrapper.findAll('.mock-skeleton').length).toBeGreaterThan(0)
  })

  it('shows error state on API failure', async () => {
    mockGetOrionContext.mockRejectedValue(new Error('Network error'))
    const wrapper = createWrapper()
    await new Promise(resolve => setTimeout(resolve, 0))
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('Error de conexión')
    expect(wrapper.text()).toContain('Reconectar')
  })

  it('shows empty state when no targets', async () => {
    const emptyCtx = {
      ...mockOrionContext,
      counts: { targets: 0, endpoints: 0, findings: 0, confirmed_findings: 0, total_estimated_payout: 0 },
    }
    mockGetOrionContext.mockResolvedValue(emptyCtx)
    const wrapper = createWrapper()
    await new Promise(resolve => setTimeout(resolve, 0))
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('Ningún target en radar')
    expect(wrapper.text()).toContain('Agregar Target')
  })

  it('renders KPIs with data', async () => {
    mockGetOrionContext.mockResolvedValue(mockOrionContext)
    const wrapper = createWrapper()
    await new Promise(resolve => setTimeout(resolve, 0))
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('Centro de Inteligencia OWNEX')
    expect(wrapper.text()).toContain('DashOp')
    expect(wrapper.text()).toContain('ACTIVO')
  })

  it('shows intel summary bar', async () => {
    mockGetOrionContext.mockResolvedValue(mockOrionContext)
    const wrapper = createWrapper()
    await new Promise(resolve => setTimeout(resolve, 0))
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('DETECTADOS')
    expect(wrapper.text()).toContain('45')
    expect(wrapper.text()).toContain('CONFIRMADOS')
    expect(wrapper.text()).toContain('12')
    expect(wrapper.text()).toContain('TASA ÉXITO')
  })

  it('shows charts when findings exist', async () => {
    mockGetOrionContext.mockResolvedValue(mockOrionContext)
    const wrapper = createWrapper()
    await new Promise(resolve => setTimeout(resolve, 0))
    await wrapper.vm.$nextTick()
    expect(wrapper.find('.mock-barchart').exists()).toBe(true)
    expect(wrapper.find('.mock-doughnut').exists()).toBe(true)
  })

  it('shows opportunity list', async () => {
    mockGetOrionContext.mockResolvedValue(mockOrionContext)
    const wrapper = createWrapper()
    await new Promise(resolve => setTimeout(resolve, 0))
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('Oportunidades prioritarias')
    expect(wrapper.text()).toContain('Target X')
  })

  it('kpi items render correct values', async () => {
    mockGetOrionContext.mockResolvedValue(mockOrionContext)
    const wrapper = createWrapper()
    await new Promise(resolve => setTimeout(resolve, 0))
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('10')  // targets
    expect(wrapper.text()).toContain('250') // endpoints
  })

  it('error retry calls fetchData', async () => {
    mockGetOrionContext.mockRejectedValue(new Error('fail'))
    const wrapper = createWrapper()
    await new Promise(resolve => setTimeout(resolve, 0))
    await wrapper.vm.$nextTick()
    mockGetOrionContext.mockResolvedValue(mockOrionContext)
    await wrapper.find('.mock-btn').trigger('click')
    await new Promise(resolve => setTimeout(resolve, 0))
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('ACTIVO')
  })
})
