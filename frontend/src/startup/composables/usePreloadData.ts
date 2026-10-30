/* ════════════════════════════════════════════════════════════
   usePreloadData — Fetches critical data during startup splash
   ══════════════════════════════════════════════════════════ */

import { api } from '@/lib/api'
import { ref } from 'vue'

export interface PreloadCache {
  health: {
    status: string
    timestamp?: string
    services?: Record<string, string>
  } | null
}

export function usePreloadData() {
  const cache = ref<PreloadCache>({ health: null })
  const loading = ref(true)
  const error = ref<string | null>(null)

  async function preload(): Promise<PreloadCache> {
    loading.value = true
    error.value = null

    // Un solo endpoint, y existe.
    //
    // Aquí se quitaron dos llamadas que eran 404 en cada arranque:
    // `/api/dashboard/summary` (2026-09-28: el router se archivó y el
    // endpoint nunca existió) y `/api/system/readiness` (2026-10-08: **no
    // existe ningún readiness en el backend**; verificado contra
    // `app.openapi()['paths']`). Ninguna devolvía nada útil.
    //
    // `readiness` no era "falta un endpoint": el dashboard de readiness que
    // la consumía (`mission-control/MissionControlView.vue`) está huérfano
    // — nada lo importa y a su vez importa `./stores/readinessStore`, que no
    // existe en el repo. Ver KNOWN_DEBT #73.
    const [health] = await Promise.allSettled([
      api.get<PreloadCache['health']>('/api/system/health').catch(() => null),
    ])

    cache.value = {
      health: health.status === 'fulfilled' ? health.value : null,
    }

    if (health.status === 'rejected') {
      error.value = 'No se pudo conectar con el backend'
    }

    loading.value = false
    return cache.value
  }

  return { cache, loading, error, preload }
}
