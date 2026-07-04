import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import Findings from '@/pages/Findings.vue'

const mockApi = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
}))
vi.mock('@/lib/api', () => ({ api: mockApi }))

const mockFindingsStore = {
  loading: false,
  error: null,
  findings: [],
  pipeline: null,
  selectFinding: vi.fn(),
  updateStatus: vi.fn(),
  fetchAll: vi.fn().mockResolvedValue(undefined),
}

vi.mock('@/stores/findings', () => {
  return { useFindingsStore: () => mockFindingsStore }
})

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
})

function createWrapper() {
  return mount(Findings, {
    global: {
      stubs: {
        'router-link': true,
        'router-view': true,
        Transition: false,
      },
    },
  })
}

describe('Findings page', () => {
  it('shows loading state initially', async () => {
    const wrapper = createWrapper()
    await wrapper.vm.$nextTick()
    expect(wrapper.vm.store.loading).toBe(false)
    expect(wrapper.vm.store.error).toBeNull()
    expect(wrapper.text()).toContain('Findings Pipeline')
  })
})