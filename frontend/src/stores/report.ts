import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { ApiError, api, getToken } from '@/lib/api'
import { getApiBase } from '@/lib/backend'

export interface ReportDraft {
  finding_id: number
  title: string
  severity: string
  vulnerability: string
  description: string
  steps_to_reproduce: string[]
  impact: string
  recommended_fix: string
  poc: string
  references: string[]
}

export const useReportStore = defineStore('report', () => {
  const draft = ref<ReportDraft | null>(null)
  const generating = ref(false)
  const error = ref<string | null>(null)
  const recentDrafts = ref<Array<{ finding_id: number; title: string; generated_at: string }>>([])

  async function generateDraft(findingId: number): Promise<ReportDraft | null> {
    generating.value = true
    error.value = null
    draft.value = null
    try {
      const res = await api.post<ReportDraft>(`/findings/${findingId}/generate-report`)
      draft.value = res
      recentDrafts.value.unshift({
        finding_id: findingId,
        title: res.title,
        generated_at: new Date().toISOString(),
      })
      return res
    } catch (e: any) {
      error.value = e?.message || 'Error al generar borrador'
      return null
    } finally {
      generating.value = false
    }
  }

  async function exportMarkdown(findingId: number): Promise<string | null> {
    try {
      const res = await api.get<{ markdown: string }>(`/findings/${findingId}/export-markdown`)
      return res.markdown
    } catch {
      return null
    }
  }

  async function exportPdf(findingId: number): Promise<Blob | null> {
    try {
      const token = getToken()
      // getApiBase() at request time — respects dynamic backend port (Tauri).
      const res = await fetch(`${getApiBase()}/findings/${findingId}/export-pdf`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      })
      if (!res.ok) throw new Error()
      return await res.blob()
    } catch {
      return null
    }
  }

  function clearDraft() {
    draft.value = null
    error.value = null
  }

  return {
    draft,
    generating,
    error,
    recentDrafts,
    generateDraft,
    exportMarkdown,
    exportPdf,
    clearDraft,
  }
})
