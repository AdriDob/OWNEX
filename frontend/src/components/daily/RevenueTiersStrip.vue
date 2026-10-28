<script setup lang="ts">
/**
 * RevenueTiersStrip — compact SURVIVAL / TARGET $5K / STRETCH $15K strip.
 * Consumes /command-center/tiers (realized PAID net MTD + linear pace).
 * Degrades silently (hidden) when the backend is unreachable.
 */
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowRight, Target } from '@lucide/vue'
import OwnexButton from '@/components/ui/OwnexButton.vue'
import ProgressBar from '@/components/ui/ProgressBar.vue'
import { fetchRevenueTiers } from '@/services/ownexData'

const router = useRouter()
const visible = ref(false)
const realized = ref(0)
const pace = ref(0)
const targetPct = ref(0)
const stretchPct = ref(0)
const targetOnTrack = ref(false)
const bestTitle = ref('')

function money(n: number): string {
  return `$${n.toLocaleString('en-US', { maximumFractionDigits: 0 })}`
}

async function doLoad(): Promise<void> {
  try {
    const tiers = await fetchRevenueTiers()
    realized.value = tiers.realized_mtd_net_usd
    pace.value = tiers.projection_monthly_usd
    targetPct.value = Math.min(100, (tiers.realized_mtd_net_usd / tiers.tiers.target.target_usd) * 100)
    stretchPct.value = Math.min(100, (tiers.realized_mtd_net_usd / tiers.tiers.stretch.target_usd) * 100)
    targetOnTrack.value = tiers.tiers.target.on_track
    bestTitle.value = tiers.best_opportunity.title ?? ''
    visible.value = true
  } catch {
    visible.value = false
  }
}

const headline = computed(
  () => `${money(realized.value)} / $15K · pace ${money(pace.value)}/mes`,
)

function open(): void {
  void router.push('/operations/worker')
}

onMounted(() => {
  void doLoad()
})
</script>

<template>
  <div
    v-if="visible"
    class="flex flex-wrap items-center gap-3 rounded-lg border border-border/40 bg-surface/40 px-4 py-3"
  >
    <Target class="h-5 w-5 shrink-0 text-primary" />
    <div class="min-w-44 flex-1">
      <div class="flex items-center justify-between gap-2 text-sm">
        <span>
          Revenue: <strong>{{ headline }}</strong>
          <span class="opacity-60">({{ targetOnTrack ? 'en ritmo TARGET' : 'bajo ritmo' }})</span>
        </span>
        <span v-if="bestTitle" class="hidden opacity-70 sm:inline">{{ bestTitle }}</span>
      </div>
      <ProgressBar :value="targetPct" color="primary" size="sm" />
    </div>
    <OwnexButton variant="secondary" size="sm" @click="open">
      Ver trabajo <ArrowRight class="ml-1 h-3 w-3" />
    </OwnexButton>
  </div>
</template>
