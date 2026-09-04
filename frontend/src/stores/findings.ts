import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { api } from '@/lib/api'
import type { Finding, PipelineStages } from '@/types'

export const useFindingsStore = defineStore('findings', () => {
  const findings = ref<Finding[]>([])
  const pipeline = ref<PipelineStages | null>(null)
  const selectedFinding = ref<Finding | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const findingsBySeverity = computed(() => {
    const map: Record<string, Finding[]> = {}
    for (const f of findings.value) {
      const s = f.severity || 'info'
      if (!map[s]) map[s] = []
      map[s].push(f)
    }
    return map
  })

  const pipelineCounts = computed(() => {
    if (!pipeline.value) return { detected: 0, validated: 0, confirmed: 0, reported: 0 }
    return {
      detected: pipeline.value.detected.length,
      validated: pipeline.value.validated.length,
      confirmed: pipeline.value.confirmed.length,
      reported: pipeline.value.reported.length,
    }
  })

  async function fetchFindings(params?: { target_id?: number; limit?: number; skip?: number }) {
    loading.value = true
    error.value = null
    try {
      const res = await api.get<{ items: Finding[]; total: number }>('/findings', params as any)
      findings.value = res.items || []
    } catch (e: any) {
      error.value = e?.message || 'Error al cargar findings'
      findings.value = []
    } finally {
      loading.value = false
    }
  }

  async function fetchPipeline() {
    try {
      pipeline.value = await api.get<PipelineStages>('/pipeline')
    } catch {
      pipeline.value = null
    }
  }

  async function fetchAll() {
    await Promise.all([fetchFindings({ limit: 200 }), fetchPipeline()])
  }

  function selectFinding(f: Finding | null) {
    selectedFinding.value = f
  }

  async function updateStatus(id: number, status: string) {
    await api.put(`/findings/${id}/status`, { status })
    await fetchAll()
  }

  async function regenerateNarrative(id: number) {
    return api.post<{ narrative: string }>(`/findings/${id}/regen-narrative`)
  }

  async function submitAsReport(id: number, platform: string) {
    const report = await api.post<{ id: number }>('/reports', {
      finding_ids: [id],
      estimated_reward: selectedFinding.value?.payout || 0,
    })
    if (report?.id) {
      return api.post<{ success: boolean; external_id?: string; url?: string }>(`/reports/${report.id}/submit`, {
        platform,
      })
    }
    throw new Error('No se pudo crear el reporte')
  }

  return {
    findings,
    pipeline,
    selectedFinding,
    loading,
    error,
    findingsBySeverity,
    pipelineCounts,
    fetchFindings,
    fetchPipeline,
    fetchAll,
    selectFinding,
    updateStatus,
    regenerateNarrative,
    submitAsReport,
  }
})
