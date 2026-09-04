import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { api } from '@/lib/api'

export const useHuntStore = defineStore('hunt', () => {
  const status = ref<'idle' | 'running' | 'paused'>('idle')
  const startedAt = ref<string | null>(null)
  const findingsFound = ref(0)
  const targetsScanned = ref(0)
  const loading = ref(false)

  const isActive = computed(() => status.value === 'running' || status.value === 'paused')
  const label = computed(() => {
    if (status.value === 'running') return 'Running'
    if (status.value === 'paused') return 'Paused'
    return 'Idle'
  })

  async function start() {
    loading.value = true
    try {
      const res = await api.post<{ status: string; started_at: string }>('/hunt/start')
      status.value = 'running'
      startedAt.value = res.started_at
    } catch {
      status.value = 'idle'
    } finally {
      loading.value = false
    }
  }

  async function pause() {
    loading.value = true
    try {
      await api.post('/hunt/pause')
      status.value = 'paused'
    } catch {
      // keep current
    } finally {
      loading.value = false
    }
  }

  async function resume() {
    loading.value = true
    try {
      await api.post('/hunt/resume')
      status.value = 'running'
    } catch {
      // keep current
    } finally {
      loading.value = false
    }
  }

  async function stop() {
    loading.value = true
    try {
      await api.post('/hunt/stop')
      status.value = 'idle'
      startedAt.value = null
    } catch {
      // keep current
    } finally {
      loading.value = false
    }
  }

  async function fetchStatus() {
    try {
      const res = await api.get<{
        status: 'idle' | 'running' | 'paused'
        started_at: string | null
        findings_found: number
        targets_scanned: number
      }>('/hunt/status')
      status.value = res.status
      startedAt.value = res.started_at
      findingsFound.value = res.findings_found
      targetsScanned.value = res.targets_scanned
    } catch {
      // backend might not have the endpoint yet
    }
  }

  return {
    status,
    startedAt,
    findingsFound,
    targetsScanned,
    loading,
    isActive,
    label,
    start,
    pause,
    resume,
    stop,
    fetchStatus,
  }
})
