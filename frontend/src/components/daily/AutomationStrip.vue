<script setup lang="ts">
/**
 * AutomationStrip — Fábrica 1000%: cuánto hace la máquina vs el humano.
 * Consumes GET /api/cycles/automation-metrics (SSOT cores/cycles/metrics.py).
 * Degrades silently (hidden) when the backend is unreachable or history empty.
 */
import { onMounted, ref } from 'vue'
import { Bot } from '@lucide/vue'
import { fetchAutomationMetrics } from '@/services/ownexData'

const visible = ref(false)
const ratio = ref<number | null>(null)
const saved = ref<number | null>(null)
const perHour = ref<number | null>(null)
const paid = ref(0)

async function load(): Promise<void> {
  try {
    const m = await fetchAutomationMetrics()
    if (m.automation_ratio === null && m.money_per_human_hour === null) {
      visible.value = false
      return
    }
    ratio.value = m.automation_ratio
    saved.value = m.human_time_saved_hours
    perHour.value = m.money_per_human_hour
    paid.value = m.paid_usd
    visible.value = true
  } catch {
    visible.value = false
  }
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
    <Bot class="h-5 w-5 shrink-0 text-primary" />
    <div class="min-w-44 flex-1">
      <div class="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
        <span v-if="ratio !== null">
          Automatización: <strong>{{ Math.round(ratio * 100) }}%</strong>
        </span>
        <span v-if="saved !== null" class="opacity-70">{{ saved }}h ahorradas</span>
        <span v-if="perHour !== null" class="opacity-70">${{ perHour }}/h-humana</span>
        <span v-if="paid > 0" class="opacity-70">cobrados ${{ paid }}</span>
      </div>
    </div>
  </div>
</template>
