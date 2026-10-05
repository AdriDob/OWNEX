/* ════════════════════════════════════════════════════════════
   usePreloadData — Fetches critical data during startup splash
   Ensures dashboard has data ready before first render.
   ══════════════════════════════════════════════════════════ */

import { api } from '@/lib/api'
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
  /** @deprecated sin consumidor y sin endpoint en backend (404 por arranque). */
  summary?: {
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
    // NOTE (ship-day 2026-09-28): se quitó `/api/dashboard/summary` — ese
    // router fue archivado y el endpoint NUNCA existió en él (solo /status,
    // /models, /ws/logs). Era un 404 en cada arranque y `cache.summary` no lo
    // consumía nadie. Restaurarlo por el llamador sería inventar contrato.
    const results = await Promise.allSettled([
      api.get<any>('/api/system/health').catch(() => null),
      api.get<any>('/api/system/readiness').catch(() => null),
    ])

    cache.value = {
      health: results[0].status === 'fulfilled' ? results[0].value : null,
      readiness: results[1].status === 'fulfilled' ? results[1].value : null,
    }

    if (results.every((r) => r.status === 'rejected')) {
      error.value = 'No se pudo conectar con el backend'
    }

    loading.value = false
    return cache.value
  }

  return { cache, loading, error, preload }
}
