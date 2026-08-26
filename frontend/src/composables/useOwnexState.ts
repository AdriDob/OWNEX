/**
 * useOwnexState — Global reactive state shared across all pages.
 *
 * Eliminates duplicate API calls: Dashboard, Assistant, Mobile all read
 * from the same reactive refs instead of firing independent requests.
 *
 * Usage in any component:
 *   const { digest, money, aiOk, refresh } = useOwnexState()
 *   // digest.value is shared — if another page already loaded it, no new request
 *
 * Refresh strategy: stale-while-revalidate with 60s TTL per domain.
 */

import { ref, computed, type Ref } from 'vue'
import {
  fetchDailyDigest,
  fetchCapitalSnapshot,
  fetchAiCenter,
  fetchIncomePlan,
  type DailyDigestState,
  type CapitalSnapshot,
  type AiCenterState,
  type IncomePlanState,
} from '@/services/ownexData'

// ── Module-level singleton refs (shared across ALL component instances) ──

const digest: Ref<DailyDigestState | null> = ref(null)
const capital: Ref<CapitalSnapshot | null> = ref(null)
const ai: Ref<AiCenterState | null> = ref(null)
const incomePlan: Ref<IncomePlanState | null> = ref(null)

const loading = ref(false)
const lastFetch = ref(0)
const TTL_MS = 60_000 // 60 seconds

let inflight: Promise<void> | null = null

async function fetchAll(force = false): Promise<void> {
  const now = Date.now()
  if (!force && now - lastFetch.value < TTL_MS) return
  if (inflight) return inflight // dedup: one request at a time

  loading.value = true
  inflight = (async () => {
    const results = await Promise.allSettled([
      fetchDailyDigest(),
      fetchCapitalSnapshot(),
      fetchAiCenter(),
      fetchIncomePlan(),
    ])
    if (results[0].status === 'fulfilled') digest.value = results[0].value
    if (results[1].status === 'fulfilled') capital.value = results[1].value
    if (results[2].status === 'fulfilled') ai.value = results[2].value
    if (results[3].status === 'fulfilled') incomePlan.value = results[3].value
    lastFetch.value = Date.now()
    loading.value = false
    inflight = null
  })()

  return inflight
}

// ── Composable ──

export function useOwnexState() {
  // Auto-fetch on first use
  if (!digest.value && !loading.value && lastFetch.value === 0) {
    fetchAll()
  }

  return {
    // Reactive state (shared singleton)
    digest,
    capital,
    ai,
    incomePlan,
    loading,

    // Computed shortcuts
    bestAction: computed(() => digest.value?.best_action ?? null),
    pendingDecisions: computed(() => digest.value?.decisions ?? []),
    totalPotential: computed(() => digest.value?.money.total_potential_usd ?? 0),
    readyCount: computed(() => digest.value?.money.ready_to_deliver ?? 0),
    aiAvailable: computed(() => ai.value?.config?.available ?? false),
    aiMode: computed(() => ai.value?.oar?.resilience?.mode ?? null),

    // Actions
    refresh: () => fetchAll(true),
    forceRefresh: () => fetchAll(true),
  }
}
