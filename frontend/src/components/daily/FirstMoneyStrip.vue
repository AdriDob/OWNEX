<script setup lang="ts">
/**
 * FirstMoneyStrip — compact Zero-to-Earning progress strip for the command center.
 * Consumes /first-money/progress + /first-money/next-action.
 * Degrades silently (hidden) when the backend is unreachable.
 */
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowRight, Banknote } from '@lucide/vue'
import OwnexButton from '@/components/ui/OwnexButton.vue'
import ProgressBar from '@/components/ui/ProgressBar.vue'
import { fetchFirstMoneyNextAction, fetchFirstMoneyProgress } from '@/services/ownexData'

const router = useRouter()
const visible = ref(false)
const label = ref('')
const pct = ref(0)
const done = ref(0)
const total = ref(0)
const nextTitle = ref('')
const isComplete = ref(false)

async function load(): Promise<void> {
  try {
    const [p, n] = await Promise.all([fetchFirstMoneyProgress(), fetchFirstMoneyNextAction()])
    label.value = p.current_stage_label
    pct.value = p.completion_percentage
    done.value = p.completed_count
    total.value = p.total_count
    nextTitle.value = n.title
    isComplete.value = p.is_complete
    visible.value = true
  } catch {
    visible.value = false
  }
}

function open(): void {
  void router.push('/operations/first-money')
}

onMounted(() => {
  void load()
})
</script>

<template>
  <div
    v-if="visible"
    class="flex flex-wrap items-center gap-3 rounded-lg border border-border/40 bg-surface/40 px-4 py-3"
  >
    <Banknote class="h-5 w-5 shrink-0 text-primary" />
    <div class="min-w-44 flex-1">
      <div class="flex items-center justify-between gap-2 text-sm">
        <span>
          First Money: <strong>{{ label }}</strong>
          <span class="opacity-60">({{ done }}/{{ total }})</span>
        </span>
        <span v-if="!isComplete" class="hidden opacity-70 sm:inline">{{ nextTitle }}</span>
      </div>
      <ProgressBar :value="pct" color="primary" size="sm" />
    </div>
    <OwnexButton variant="secondary" size="sm" @click="open">
      Ver funnel <ArrowRight class="ml-1 h-3 w-3" />
    </OwnexButton>
  </div>
</template>
