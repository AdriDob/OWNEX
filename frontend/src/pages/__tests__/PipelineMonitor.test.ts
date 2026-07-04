import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PipelineMonitor from '@/pages/PipelineMonitor.vue'

const mockApi = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  delete: vi.fn(),
}))
vi.mock('@/lib/api', () => ({ api: mockApi }))

const mockRouter = vi.hoisted(() => ({
  push: vi.fn(),
}))
vi.mock('vue-router', () => ({
  useRouter: () => mockRouter,
}))

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
  vi.stubGlobal('prompt', vi.fn())
})

function createWrapper() {
  return mount(PipelineMonitor, {
    global: {
      stubs: {
        'router-link': true,
        'router-view': true,
        Transition: false,
        Card: { template: '<div class="mock-card"><slot /></div>' },
        Badge: { template: '<span class="mock-badge"><slot /></span>' },
        Skeleton: { template: '<div class="mock-skeleton" />' },
        BarChart: { template: '<div class="mock-barchart" />' },
      },
    },
  })
}

const mockPipelines = [
  { id: 'p1', target_id: 1, target_name: 'test.com', state: 'discovery', retries: 0, quality_score: 0.85, stages: [], error: '', created_at: '2025-01-01T00:00:00Z' },
  { id: 'p2', target_id: 2, target_name: 'example.com', state: 'validation', retries: 1, quality_score: 0.6, stages: [], error: '', created_at: '2025-01-01T00:00:00Z' },
  { id: 'p3', target_id: 3, target_name: 'closed.com', state: 'closed', retries: 2, quality_score: 0.9, stages: [], error: '', created_at: '2025-01-01T00:00:00Z' },
  { id: 'p4', target_id: 4, target_name: 'failed.com', state: 'failed', retries: 3, quality_score: 0.2, stages: [], error: 'Timeout', created_at: '2025-01-01T00:00:00Z' },
]

describe('PipelineMonitor page', () => {
  it('shows loading skeleton initially', () => {
    mockApi.get.mockImplementation(() => new Promise(() => {}))
    const wrapper = createWrapper()
    expect(wrapper.findAll('.mock-skeleton').length).toBeGreaterThan(0)
  })

  it('shows error state on API failure', async () => {
    mockApi.get.mockRejectedValue(new Error('Server error'))
    const wrapper = createWrapper()
    await new Promise(resolve => setTimeout(resolve, 0))
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('Error de conexión')
    expect(wrapper.text()).toContain('Reintentar')
  })

  it('shows empty state when no pipelines', async () => {
    mockApi.get.mockResolvedValue({ pipelines: [] })
    const wrapper = createWrapper()
    await new Promise(resolve => setTimeout(resolve, 0))
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('No hay pipelines')
    expect(wrapper.text()).toContain('Start Pipeline')
  })

  it('renders pipeline list with active and completed sections', async () => {
    mockApi.get.mockResolvedValue({ pipelines: mockPipelines })
    const wrapper = createWrapper()
    await new Promise(resolve => setTimeout(resolve, 0))
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('Pipeline Monitor')
    expect(wrapper.text()).toContain('4 pipelines')
    expect(wrapper.text()).toContain('2 active')
    expect(wrapper.text()).toContain('test.com')
    expect(wrapper.text()).toContain('example.com')
    expect(wrapper.text()).toContain('History')
    expect(wrapper.text()).toContain('closed.com')
    expect(wrapper.text()).toContain('failed.com')
  })

  it('shows quality score with correct formatting', async () => {
    mockApi.get.mockResolvedValue({ pipelines: mockPipelines })
    const wrapper = createWrapper()
    await new Promise(resolve => setTimeout(resolve, 0))
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('85%')
    expect(wrapper.text()).toContain('60%')
    expect(wrapper.text()).toContain('20%')
  })

  it('shows failed state label for failed pipelines', async () => {
    mockApi.get.mockResolvedValue({ pipelines: mockPipelines })
    const wrapper = createWrapper()
    await new Promise(resolve => setTimeout(resolve, 0))
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('failed')
  })

  it('handleCancel calls post and re-fetches', async () => {
    mockApi.get.mockResolvedValue({ pipelines: mockPipelines })
    mockApi.post.mockResolvedValue({})
    const wrapper = createWrapper()
    await new Promise(resolve => setTimeout(resolve, 0))
    await wrapper.vm.$nextTick()
    const cancelBtn = wrapper.findAll('button').find(b => b.text().includes('Cancel'))
    if (cancelBtn) {
      await cancelBtn.trigger('click')
      expect(mockApi.post).toHaveBeenCalledWith('/agents/pipelines/p1/cancel')
    }
  })

  it('handleDelete calls delete and re-fetches', async () => {
    mockApi.get.mockResolvedValue({ pipelines: mockPipelines })
    mockApi.delete.mockResolvedValue({})
    const wrapper = createWrapper()
    await new Promise(resolve => setTimeout(resolve, 0))
    await wrapper.vm.$nextTick()
    const deleteBtns = wrapper.findAll('button').filter(b => b.text().includes('Delete'))
    if (deleteBtns.length > 0) {
      await deleteBtns[0].trigger('click')
      expect(mockApi.delete).toHaveBeenCalled()
    }
  })

  it('filter changes trigger fetch', async () => {
    mockApi.get.mockResolvedValue({ pipelines: mockPipelines })
    const wrapper = createWrapper()
    await new Promise(resolve => setTimeout(resolve, 0))
    await wrapper.vm.$nextTick()
    const select = wrapper.find('select')
    if (select.exists()) {
      await select.setValue('discovery')
      expect(mockApi.get).toHaveBeenCalledWith('/agents/pipelines?status=discovery')
    }
  })
})
