import { onMounted, onUnmounted, ref } from 'vue'
import { api } from '@/lib/api'

let pollTimer: ReturnType<typeof setInterval> | null = null
const status = ref<Record<string, any>>({})
const lastPoll = ref<string | null>(null)

export function useCompanion() {
  async function pollStatus() {
    try {
      status.value = await api.get<Record<string, any>>('/mobile/status')
      lastPoll.value = new Date().toISOString()
    } catch {
      /* offline */
    }
  }

  function startPolling(intervalMs = 120_000) {
    if (pollTimer) return
    pollStatus()
    pollTimer = setInterval(pollStatus, intervalMs)
  }

  function stopPolling() {
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
  }

  return { status, lastPoll, pollStatus, startPolling, stopPolling }
}
