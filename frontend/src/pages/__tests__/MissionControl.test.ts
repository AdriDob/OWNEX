import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import MissionControl from '@/pages/MissionControl.vue'

const mockGetOrionContext = vi.hoisted(() => vi.fn())
vi.mock('@/lib/api', () => ({
  getOrionContext: (...args: any[]) => mockGetOrionContext(...args),
}))

const mockHuntStore = vi.hoisted(() => ({
  status: 'idle',
  isActive: false,
  loading: false,
  findingsFound: 0,
  targetsScanned: 0,
  start: vi.fn(),
  pause: vi.fn(),
  resume: vi.fn(),
  stop: vi.fn(),
  fetchStatus: vi.fn(),
}))
vi.mock('@/stores/hunt', () => ({
  useHuntStore: () => mockHuntStore,
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

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
  mockHuntStore.status = 'idle'
  mockHuntStore.isActive = false
  mockHuntStore.loading = false
  mockHuntStore.findingsFound = 0
  mockHuntStore.targetsScanned = 0
})

function createWrapper() {
  return mount(MissionControl, {
    global: {
      stubs: {
        'router-link': true,
        'router-view': true,
        Transition: false,
        Skeleton: { template: '<div class="mock-skeleton"><slot /></div>' },
        Badge: { template: '<span class="mock-badge"><slot /></span>' },
        Button: { template: '<button class="mock-btn" @click="$emit(\'click\', $event)"><slot /></button>' },
        Tooltip: { template: '<span class="mock-tooltip"><slot /></span>' },
        DoughnutChart: { template: '<div class="mock-chart" />' },
        OnboardingWizard: { template: '<div class="mock-onboarding" />' },
      },
    },
  })
}

describe('MissionControl page', () => {
  it('shows loading skeleton initially', async () => {
    mockGetOrionContext.mockImplementation(() => new Promise(() => {}))
    const wrapper = createWrapper()
    expect(wrapper.find('.mock-skeleton').exists()).toBe(true)
  })

  it('shows error state on API failure', async () => {
    mockGetOrionContext.mockRejectedValue(new Error('Connection refused'))
    const wrapper = createWrapper()
    await new Promise(resolve => setTimeout(resolve, 0))
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('Error de conexión')
    expect(wrapper.text()).toContain('Connection refused')
  })

  it('shows empty state when no targets and no findings', async () => {
    mockGetOrionContext.mockResolvedValue({
      counts: { targets: 0, endpoints: 0, findings: 0, confirmed_findings: 0, total_estimated_payout: 0, reports_ready: 0 },
      pipeline: { detected: 0, validated: 0, confirmed: 0, reported: 0 },
      system: { status: 'healthy', health_score: 85 },
      findings: { new_24h: 0 },
      next_action: null,
      opportunities: { top: [] },
      activity_24h: { events: [] },
      _meta: { version: '1.0' },
      scans: { active: 0 },
      verdicts: { by_status: { confirmed: 0, rejected: 0, inconclusive: 0, pending: 0 } },
    })
    mockSettingsStore.onboardingNeeded = false
    const wrapper = createWrapper()
    await new Promise(resolve => setTimeout(resolve, 0))
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('Bienvenido a CATEYE')
  })

  it('shows mission control with KPIs when data is loaded', async () => {
    mockGetOrionContext.mockResolvedValue({
      counts: { targets: 5, endpoints: 120, findings: 15, confirmed_findings: 3, total_estimated_payout: 5000, reports_ready: 1 },
      pipeline: { detected: 15, validated: 8, confirmed: 3, reported: 0 },
      system: { status: 'healthy', health_score: 92 },
      findings: { new_24h: 2 },
      next_action: { title: 'Test SQLi', why_now: 'High impact', effort: 'low', estimated_reward: '$1000' },
      opportunities: { top: [{ id: 1, name: 'Target A', domain: 'a.com', endpoints: 10, opportunity_score: 8.5 }] },
      activity_24h: { events: [{ type: 'finding', id: 1, severity: 'high' }] },
      _meta: { version: '1.0' },
      scans: { active: 0 },
      verdicts: { by_status: { confirmed: 0, rejected: 0, inconclusive: 0, pending: 0 } },
    })
    mockSettingsStore.onboardingNeeded = false
    const wrapper = createWrapper()
    await new Promise(resolve => setTimeout(resolve, 0))
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('CATEYE MISSION CONTROL')
    expect(wrapper.text()).toContain('TestOp')
    expect(wrapper.text()).toContain('Targets')
    expect(wrapper.text()).toContain('5')
    expect(wrapper.text()).toContain('Endpoints')
    expect(wrapper.text()).toContain('120')
    expect(wrapper.text()).toContain('Pipeline')
    expect(wrapper.text()).toContain('CAZA AUTÓNOMA')
    expect(wrapper.text()).toContain('IDLE')
    expect(wrapper.text()).toContain('Oportunidades prioritarias')
    expect(wrapper.text()).toContain('Actividad 24h')
  })

  it('handles hunt start/pause/resume toggle', async () => {
    mockGetOrionContext.mockResolvedValue({
      counts: { targets: 1, endpoints: 10, findings: 1, confirmed_findings: 0, total_estimated_payout: 0, reports_ready: 0 },
      pipeline: { detected: 1, validated: 0, confirmed: 0, reported: 0 },
      system: { status: 'healthy', health_score: 80 },
      findings: { new_24h: 0 },
      next_action: null,
      opportunities: { top: [] },
      activity_24h: { events: [] },
      _meta: { version: '1.0' },
      scans: { active: 0 },
      verdicts: { by_status: { confirmed: 0, rejected: 0, inconclusive: 0, pending: 0 } },
    })
    const wrapper = createWrapper()
    await new Promise(resolve => setTimeout(resolve, 0))
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('IDLE')

    const btn = wrapper.find('.mock-btn')
    await btn.trigger('click')
    await wrapper.vm.$nextTick()
    expect(mockHuntStore.start).toHaveBeenCalled()
  })

  it('shows hunt stats when active', async () => {
    mockHuntStore.status = 'running'
    mockHuntStore.isActive = true
    mockHuntStore.findingsFound = 5
    mockHuntStore.targetsScanned = 3
    mockGetOrionContext.mockResolvedValue({
      counts: { targets: 1, endpoints: 10, findings: 5, confirmed_findings: 1, total_estimated_payout: 0, reports_ready: 0 },
      pipeline: { detected: 5, validated: 2, confirmed: 1, reported: 0 },
      system: { status: 'healthy', health_score: 80 },
      findings: { new_24h: 0 },
      next_action: null,
      opportunities: { top: [] },
      activity_24h: { events: [] },
      _meta: { version: '1.0' },
      scans: { active: 0 },
      verdicts: { by_status: { confirmed: 0, rejected: 0, inconclusive: 0, pending: 0 } },
    })
    const wrapper = createWrapper()
    await new Promise(resolve => setTimeout(resolve, 0))
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('ACTIVE')
    expect(wrapper.text()).toContain('5')
  })
})
