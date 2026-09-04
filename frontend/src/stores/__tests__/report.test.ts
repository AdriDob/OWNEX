import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useReportStore } from '@/stores/report'

const mockApi = vi.hoisted(() => ({
  post: vi.fn(),
  get: vi.fn(),
}))
vi.mock('@/lib/api', () => ({
  api: mockApi,
  getToken: vi.fn(() => 'mock-token'),
  ApiError: class ApiError extends Error {},
}))

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
})

const mockDraft = {
  finding_id: 1,
  title: 'SQL Injection',
  severity: 'critical',
  vulnerability: 'SQLi',
  description: 'Blind SQLi in id param',
  steps_to_reproduce: ['Step 1'],
  impact: 'Data exfiltration',
  recommended_fix: 'Parameterize queries',
  poc: 'curl ...',
  references: ['CWE-89'],
}

describe('report store', () => {
  it('starts with no draft', () => {
    const store = useReportStore()
    expect(store.draft).toBeNull()
    expect(store.generating).toBe(false)
    expect(store.error).toBeNull()
    expect(store.recentDrafts).toEqual([])
  })

  it('generateDraft sets draft on success', async () => {
    mockApi.post.mockResolvedValue(mockDraft)
    const store = useReportStore()
    const result = await store.generateDraft(1)
    expect(result).toEqual(mockDraft)
    expect(store.draft).toEqual(mockDraft)
    expect(store.generating).toBe(false)
    expect(store.recentDrafts).toHaveLength(1)
    expect(store.recentDrafts[0].finding_id).toBe(1)
    expect(store.recentDrafts[0].title).toBe('SQL Injection')
  })

  it('generateDraft handles error', async () => {
    mockApi.post.mockRejectedValue(new Error('API error'))
    const store = useReportStore()
    const result = await store.generateDraft(1)
    expect(result).toBeNull()
    expect(store.error).toBe('API error')
    expect(store.generating).toBe(false)
    expect(store.draft).toBeNull()
  })

  it('generateDraft sets default error if no message', async () => {
    mockApi.post.mockRejectedValue(new Error())
    const store = useReportStore()
    await store.generateDraft(1)
    expect(store.error).toBe('Error al generar borrador')
  })

  it('exportMarkdown returns markdown string', async () => {
    mockApi.get.mockResolvedValue({ markdown: '# Report\nContent' })
    const store = useReportStore()
    const result = await store.exportMarkdown(1)
    expect(result).toBe('# Report\nContent')
    expect(mockApi.get).toHaveBeenCalledWith('/findings/1/export-markdown')
  })

  it('exportMarkdown returns null on error', async () => {
    mockApi.get.mockRejectedValue(new Error('fail'))
    const store = useReportStore()
    const result = await store.exportMarkdown(1)
    expect(result).toBeNull()
  })

  it('exportPdf returns blob on success', async () => {
    const blob = new Blob(['pdf content'], { type: 'application/pdf' })
    global.fetch = vi.fn().mockResolvedValue({ ok: true, blob: () => blob })
    const store = useReportStore()
    const result = await store.exportPdf(1)
    expect(result).toBeInstanceOf(Blob)
    expect(global.fetch).toHaveBeenCalledWith('/api/findings/1/export-pdf', expect.any(Object))
  })

  it('exportPdf returns null on fetch failure', async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error('fail'))
    const store = useReportStore()
    const result = await store.exportPdf(1)
    expect(result).toBeNull()
  })

  it('exportPdf returns null on non-ok response', async () => {
    global.fetch = vi.fn().mockResolvedValue({ ok: false })
    const store = useReportStore()
    const result = await store.exportPdf(1)
    expect(result).toBeNull()
  })

  it('clearDraft resets draft and error', () => {
    const store = useReportStore()
    store.draft = mockDraft as any
    store.error = 'some error'
    store.clearDraft()
    expect(store.draft).toBeNull()
    expect(store.error).toBeNull()
  })
})
