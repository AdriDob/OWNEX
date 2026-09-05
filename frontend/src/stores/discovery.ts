import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { api } from '@/lib/api'

export interface BountyProgram {
  name: string
  platform: string
  url: string
  source: string
  description: string
  status: string
  rewards_range: string
  max_payout: number
  technologies: string[]
  confidence: number
  imported: boolean
  import_error: string
  discovered_at: string
}

export interface DiscoveryStats {
  total_discovered: number
  imported: number
  by_platform: Record<string, number>
  by_source: Record<string, number>
}

export const useDiscoveryStore = defineStore('discovery', () => {
  const programs = ref<BountyProgram[]>([])
  const stats = ref<DiscoveryStats | null>(null)
  const loading = ref(false)
  const scanning = ref(false)
  const error = ref<string | null>(null)
  const monitorStatus = ref<Record<string, any> | null>(null)

  const totalDiscovered = computed(() => stats.value?.total_discovered ?? 0)
  const importedCount = computed(() => stats.value?.imported ?? 0)
  const platforms = computed(() =>
    Object.entries(stats.value?.by_platform ?? {}).map(([k, v]) => ({ name: k, count: v })),
  )

  async function fetchPrograms(params?: {
    platform?: string
    source?: string
    imported?: boolean
    limit?: number
    offset?: number
  }) {
    loading.value = true
    error.value = null
    try {
      const query = new URLSearchParams()
      if (params?.platform) query.set('platform', params.platform)
      if (params?.source) query.set('source', params.source)
      if (params?.imported !== undefined) query.set('imported', String(params.imported))
      if (params?.limit) query.set('limit', String(params.limit))
      if (params?.offset) query.set('offset', String(params.offset))
      const qs = query.toString()
      const res = await api.get<{ programs: BountyProgram[] }>(`/discovery/programs${qs ? `?${qs}` : ''}`)
      programs.value = res.programs
      return res
    } catch (e: any) {
      error.value = e.message
      return null
    } finally {
      loading.value = false
    }
  }

  async function fetchStats() {
    try {
      const res = await api.get<{ stats: DiscoveryStats; monitor: Record<string, any> }>('/discovery/stats')
      stats.value = res.stats
      monitorStatus.value = res.monitor
      return res
    } catch (e: any) {
      error.value = e.message
      return null
    }
  }

  async function runScan(domains?: string[]) {
    scanning.value = true
    error.value = null
    try {
      const res = await api.post('/discovery/scan', domains ? { domains } : undefined)
      await fetchPrograms()
      await fetchStats()
      return res
    } catch (e: any) {
      error.value = e.message
      return null
    } finally {
      scanning.value = false
    }
  }

  async function importProgram(url: string, autoRecon = false) {
    try {
      const res = await api.post(`/discovery/programs/${encodeURIComponent(url)}/import`, { auto_recon: autoRecon })
      await fetchPrograms()
      await fetchStats()
      return res
    } catch (e: any) {
      error.value = e.message
      return null
    }
  }

  async function importAll(platform?: string) {
    try {
      const res = await api.post('/discovery/import-all', platform ? { platform } : undefined)
      await fetchPrograms()
      await fetchStats()
      return res
    } catch (e: any) {
      error.value = e.message
      return null
    }
  }

  return {
    programs,
    stats,
    loading,
    scanning,
    error,
    monitorStatus,
    totalDiscovered,
    importedCount,
    platforms,
    fetchPrograms,
    fetchStats,
    runScan,
    importProgram,
    importAll,
  }
})
