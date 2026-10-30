/* ════════════════════════════════════════════════════════════
   usePreloadData — Fetches critical data during startup splash
   Ensures dashboard has data ready before first render.
   ══════════════════════════════════════════════════════════ */

import { ref } from 'vue'
import type { ServiceCheck, SystemSpecs } from '@/shared/types'

export interface PreloadCache {
  health: {
    status: string
    timestamp: string
    services: Record<string, string>
  } | null
  readiness: {
    score: number
    checks: ServiceCheck[]
    specs: SystemSpecs | null
  } | null
  summary: {
    revenue_today: number
    revenue_week: number
    throughput: number
    active_targets: number
    pending_findings: number
  } | null
}

export function usePreloadData() {
  const cache = ref<PreloadCache>({
    health: null,
    readiness: null,
    summary: null,
  })
  const loading = ref(true)
  const error = ref<string | null>(null)

  async function preload(): Promise<PreloadCache> {
    loading.value = true
    error.value = null

    // Fetch all endpoints in parallel; don't block on failures
    const results = await Promise.allSettled([
      fetch('/api/system/health').then((r) => (r.ok ? r.json() : null)),
      fetch('/api/system/readiness').then((r) => (r.ok ? r.json() : null)),
      fetch('/api/dashboard/summary').then((r) => (r.ok ? r.json() : null)),
    ])

    cache.value = {
      health: results[0].status === 'fulfilled' ? results[0].value : null,
      readiness: results[1].status === 'fulfilled' ? results[1].value : null,
      summary: results[2].status === 'fulfilled' ? results[2].value : null,
    }

    if (results.every((r) => r.status === 'rejected')) {
      error.value = 'No se pudo conectar con el backend'
    }

    loading.value = false
    return cache.value
  }

  return { cache, loading, error, preload }
}
