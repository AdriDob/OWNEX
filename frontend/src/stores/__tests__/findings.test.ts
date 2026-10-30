import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useFindingsStore } from '@/stores/findings'

const mockApi = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
}))
vi.mock('@/lib/api', () => ({ api: mockApi }))

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
})

const mockFindings = [
  {
    id: 1,
    target_id: 1,
    title: 'SQLi',
    severity: 'critical',
    payout: 5000,
    target_name: 'test.com',
    endpoint_path: '/api?id=1',
  },
  {
    id: 2,
    target_id: 1,
    title: 'XSS',
    severity: 'high',
    payout: 2000,
    target_name: 'test.com',
    endpoint_path: '/search?q=1',
  },
  {
    id: 3,
    target_id: 1,
    title: 'Info',
    severity: 'info',
    payout: 0,
    target_name: 'test.com',
    endpoint_path: '/robots.txt',
  },
]

const mockPipeline = {
  detected: [{ id: 1 }],
  validated: [{ id: 2 }],
  confirmed: [{ id: 3 }],
  reported: [],
}

describe('findings store', () => {
  it('starts with empty state', () => {
    const store = useFindingsStore()
    expect(store.findings).toEqual([])
    expect(store.pipeline).toBeNull()
    expect(store.selectedFinding).toBeNull()
    expect(store.loading).toBe(false)
    expect(store.error).toBeNull()
  })

  it('fetchFindings populates findings', async () => {
    mockApi.get.mockResolvedValue({ items: mockFindings, total: 3 })
    const store = useFindingsStore()
    await store.fetchFindings({ limit: 200 })
    expect(store.findings).toHaveLength(3)
    expect(store.loading).toBe(false)
  })

  it('fetchFindings handles error', async () => {
    mockApi.get.mockRejectedValue(new Error('Network error'))
    const store = useFindingsStore()
    await store.fetchFindings()
    expect(store.error).toBe('Network error')
    expect(store.findings).toEqual([])
    expect(store.loading).toBe(false)
  })

  it('fetchPipeline populates pipeline', async () => {
    mockApi.get.mockResolvedValue(mockPipeline)
    const store = useFindingsStore()
    await store.fetchPipeline()
    expect(store.pipeline).toEqual(mockPipeline)
  })

  it('fetchPipeline sets null on error', async () => {
    mockApi.get.mockRejectedValue(new Error('fail'))
    const store = useFindingsStore()
    await store.fetchPipeline()
    expect(store.pipeline).toBeNull()
  })

  it('fetchAll calls both fetchFindings and fetchPipeline', async () => {
    mockApi.get.mockResolvedValueOnce({ items: mockFindings, total: 3 })
    mockApi.get.mockResolvedValueOnce(mockPipeline)
    const store = useFindingsStore()
    await store.fetchAll()
    expect(store.findings).toHaveLength(3)
    expect(store.pipeline).toEqual(mockPipeline)
    expect(mockApi.get).toHaveBeenCalledTimes(2)
  })

  it('findingsBySeverity groups correctly', () => {
    const store = useFindingsStore()
    store.findings = mockFindings as any
    const grouped = store.findingsBySeverity
    expect(grouped.critical).toHaveLength(1)
    expect(grouped.high).toHaveLength(1)
    expect(grouped.info).toHaveLength(1)
  })

  it('pipelineCounts returns zeros when pipeline is null', () => {
    const store = useFindingsStore()
    expect(store.pipelineCounts).toEqual({ detected: 0, validated: 0, confirmed: 0, reported: 0 })
  })

  it('pipelineCounts returns counts from pipeline', () => {
    const store = useFindingsStore()
    store.pipeline = mockPipeline as any
    expect(store.pipelineCounts).toEqual({ detected: 1, validated: 1, confirmed: 1, reported: 0 })
  })

  it('selectFinding sets selectedFinding', () => {
    const store = useFindingsStore()
    const f = { id: 1 } as any
    store.selectFinding(f)
    expect(store.selectedFinding).toEqual(f)
    store.selectFinding(null)
    expect(store.selectedFinding).toBeNull()
  })

  it('updateStatus calls put and re-fetches', async () => {
    mockApi.put.mockResolvedValue({})
    mockApi.get.mockResolvedValue({ items: [], total: 0 })
    mockApi.get.mockResolvedValue(mockPipeline)
    const store = useFindingsStore()
    await store.updateStatus(1, 'confirmed')
    expect(mockApi.put).toHaveBeenCalledWith('/findings/1/status', { status: 'confirmed' })
  })

  it('regenerateNarrative returns narrative', async () => {
    mockApi.post.mockResolvedValue({ narrative: 'narrative text' })
    const store = useFindingsStore()
    const result = await store.regenerateNarrative(1)
    expect(result).toEqual({ narrative: 'narrative text' })
    expect(mockApi.post).toHaveBeenCalledWith('/findings/1/regen-narrative')
  })

  it('submitAsReport creates report and submits', async () => {
    mockApi.post.mockResolvedValueOnce({ id: 99 })
    mockApi.post.mockResolvedValueOnce({ success: true, external_id: 'EXT-1', url: 'https://example.com/report/1' })
    const store = useFindingsStore()
    store.selectedFinding = { id: 1, payout: 5000 } as any
    const result = await store.submitAsReport(1, 'hackerone')
    expect(result).toEqual({ success: true, external_id: 'EXT-1', url: 'https://example.com/report/1' })
    expect(mockApi.post).toHaveBeenCalledWith('/reports', { finding_ids: [1], estimated_reward: 5000 })
    expect(mockApi.post).toHaveBeenCalledWith('/reports/99/submit', { platform: 'hackerone' })
  })

  it('submitAsReport throws when report creation fails', async () => {
    mockApi.post.mockResolvedValueOnce({})
    const store = useFindingsStore()
    store.selectedFinding = { id: 1 } as any
    await expect(store.submitAsReport(1, 'hackerone')).rejects.toThrow('No se pudo crear el reporte')
  })
})
