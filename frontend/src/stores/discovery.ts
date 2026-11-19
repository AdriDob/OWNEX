import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
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
  const platforms = computed(() => Object.entries(stats.value?.by_platform ?? {}).map(([k, v]) => ({ name: k, count: v })))

  async function fetchPrograms(params?: { platform?: string; source?: string; imported?: boolean; limit?: number; offset?: number }) {
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

  // ── Live opportunity pipeline ──────────────────────────────────────
  const liveStats = ref<Record<string, any> | null>(null)
  const liveOpportunities = ref<any[]>([])
  const liveConnections = ref<Record<string, any> | null>(null)
  const liveRevenue = ref<Record<string, any> | null>(null)
  const liveLoading = ref(false)

  async function fetchLiveStats() {
    try {
      const res = await api.get<Record<string, any>>('/discovery/live/stats')
      liveStats.value = res
      return res
    } catch {
      return null
    }
  }

  async function fetchLiveOpportunities(status?: string, limit = 50) {
    try {
      const qs = new URLSearchParams({ limit: String(limit) })
      if (status) qs.set('status', status)
      const res = await api.get<{ opportunities: any[] }>(`/discovery/live/opportunities?${qs}`)
      liveOpportunities.value = res.opportunities ?? []
      return res
    } catch {
      return null
    }
  }

  async function fetchLiveConnections() {
    try {
      const res = await api.get<Record<string, any>>('/discovery/live/connections')
      liveConnections.value = res
      return res
    } catch {
      return null
    }
  }

  async function fetchLiveRevenue() {
    try {
      const res = await api.get<Record<string, any>>('/discovery/live/revenue/summary')
      liveRevenue.value = res
      return res
    } catch {
      return null
    }
  }

  async function runLiveScan() {
    liveLoading.value = true
    try {
      const res = await api.post<Record<string, any>>('/discovery/live/scan')
      await Promise.all([fetchLiveStats(), fetchLiveOpportunities(), fetchLiveRevenue()])
      return res
    } catch (e: any) {
      error.value = e.message
      return null
    } finally {
      liveLoading.value = false
    }
  }

  async function prepareLiveOpportunity(key: string) {
    try {
      return await api.post<Record<string, any>>(`/discovery/live/${encodeURIComponent(key)}/prepare`)
    } catch (e: any) {
      return { error: e.message }
    }
  }

  const liveRank = ref<any[] | null>(null)

  async function fetchLiveRank(limit = 20) {
    try {
      const res = await api.get<{ ranked: any[] }>(`/discovery/live/rank?limit=${limit}`)
      liveRank.value = res.ranked ?? []
      return res
    } catch {
      return null
    }
  }

  async function analyzeLiveOpportunity(key: string, runTests = false) {
    try {
      return await api.post<Record<string, any>>(
        `/discovery/live/${encodeURIComponent(key)}/analyze?run_tests=${runTests}`,
      )
    } catch (e: any) {
      return { error: e.message }
    }
  }

  async function approveLiveOpportunity(key: string, approved: boolean, note = '') {
    try {
      return await api.post<Record<string, any>>(`/discovery/live/${encodeURIComponent(key)}/approve`, {
        approved,
        approved_by: 'user',
        note,
      })
    } catch (e: any) {
      return { error: e.message }
    }
  }

  async function paymentInquiryLive(key: string) {
    try {
      return await api.post<Record<string, any>>(`/discovery/live/${encodeURIComponent(key)}/payment-inquiry`)
    } catch (e: any) {
      return { error: e.message }
    }
  }

  async function recordLiveStatus(
    key: string,
    status: string,
    evidence: Record<string, any>,
    amount?: number,
    currency?: string,
  ) {
    try {
      const res = await api.post<Record<string, any>>(`/discovery/live/${encodeURIComponent(key)}/status`, {
        status,
        evidence,
        ...(amount !== undefined ? { amount } : {}),
        ...(currency ? { currency } : {}),
      })
      await fetchLiveOpportunities()
      await fetchLiveRevenue()
      return res
    } catch (e: any) {
      return { error: e.message }
    }
  }

  return {
    programs, stats, loading, scanning, error, monitorStatus,
    totalDiscovered, importedCount, platforms,
    fetchPrograms, fetchStats, runScan, importProgram, importAll,
    liveStats, liveOpportunities, liveConnections, liveRevenue, liveLoading,
    fetchLiveStats, fetchLiveOpportunities, fetchLiveConnections,
    fetchLiveRevenue, runLiveScan, prepareLiveOpportunity,
    liveRank, fetchLiveRank, analyzeLiveOpportunity, approveLiveOpportunity,
    paymentInquiryLive, recordLiveStatus,
  }
})
