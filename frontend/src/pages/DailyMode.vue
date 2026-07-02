<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/lib/api'
import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import { Sun, AlertTriangle, ArrowRight } from '@lucide/vue'
import DoughnutChart from '@/components/charts/DoughnutChart.vue'

const router = useRouter()

interface Briefing {
  recommended_action: {
    action: string; label: string; reason: string; confidence: number; payload?: { route?: string }
  } | null
  opportunities: Array<{
    id?: string; name: string; category: string; estimated_payout: number
  }>
  critical_risk: { severity: string; title: string } | null
  assistant_insight: { system_state?: string; focus: string; reason: string } | null
  system_health: { status: string } | null
}

const briefing = ref<Briefing | null>(null)
const loading = ref(true)
const error = ref(false)

async function fetchBriefing() {
  loading.value = true
  error.value = false
  try {
    const res = await api.get<{ briefing: Briefing }>('/system/daily-briefing')
    briefing.value = res.briefing || null
  } catch { error.value = true }
  finally { loading.value = false }
}

onMounted(fetchBriefing)
</script>

<template>
  <div class="max-w-lg mx-auto space-y-6">
    <template v-if="loading && !briefing">
      <Skeleton class="h-32 rounded-xl" />
      <Skeleton class="h-48 rounded-xl" />
    </template>

    <template v-else-if="error && !briefing">
      <div class="animate-in space-y-1">
        <p class="text-xs font-bold uppercase tracking-widest text-primary">Daily</p>
        <h1 class="font-display text-2xl font-bold text-foreground">Today</h1>
        <p class="text-sm text-muted-foreground">System ready</p>
      </div>
      <Card class="p-6 text-center">
        <AlertTriangle class="h-8 w-8 text-warning mx-auto mb-2" />
        <p class="text-sm font-semibold text-foreground">Could not load briefing</p>
        <button @click="fetchBriefing"
          class="mt-3 rounded-lg bg-primary px-4 py-2 text-xs font-semibold text-white"
        >Retry</button>
      </Card>
    </template>

    <template v-else>
      <div class="animate-in space-y-1">
        <div class="flex items-center gap-2">
          <p class="text-xs font-bold uppercase tracking-widest text-primary">Daily</p>
          <span v-if="briefing?.system_health"
            class="h-2 w-2 rounded-full"
            :class="briefing.system_health.status === 'READY' ? 'bg-success' : briefing.system_health.status === 'DEGRADED' ? 'bg-warning' : 'bg-destructive'"
          />
        </div>
        <h1 class="font-display text-2xl font-bold text-foreground">Today</h1>
        <p class="text-sm text-muted-foreground">{{ briefing?.assistant_insight?.system_state || 'System ready' }}</p>
      </div>

      <!-- Daily Metrics -->
      <Card class="p-4 animate-in">
        <h3 class="text-xs font-semibold text-foreground mb-3">Métricas Diarias</h3>
        <DoughnutChart
          :labels="['Oportunidades', 'Riesgos', 'Insights']"
          :data="[briefing?.opportunities?.length || 0, briefing?.critical_risk ? 1 : 0, briefing?.assistant_insight ? 1 : 0]"
          :height="200"
        />
      </Card>

      <!-- Best Action -->
      <div v-if="briefing?.recommended_action" class="animate-in">
        <div class="relative">
          <div class="absolute -top-2 right-4 z-10 rounded bg-primary px-3 py-0.5 text-[9px] font-bold uppercase tracking-wider text-white">
            Best Action
          </div>
          <Card class="p-5 pt-6 border-primary/30 cursor-pointer transition-all hover:border-primary/50"
            @click="router.push(briefing!.recommended_action!.payload?.route || '/actions')"
          >
            <p class="text-[10px] font-bold uppercase tracking-wider text-primary mb-1">{{ briefing.recommended_action.action }}</p>
            <p class="text-base font-bold text-foreground mb-1">{{ briefing.recommended_action.label }}</p>
            <p class="text-xs text-muted-foreground leading-relaxed">{{ briefing.recommended_action.reason }}</p>
            <div class="flex items-center gap-3 mt-3">
              <span class="inline-flex items-center gap-1.5 rounded-md bg-primary/30 px-3 py-1 text-[10px] font-semibold text-white">
                Execute <ArrowRight class="h-3 w-3" />
              </span>
              <span class="text-[9px] text-muted-foreground">{{ (briefing.recommended_action.confidence * 100).toFixed(0) }}% confidence</span>
            </div>
          </Card>
        </div>
      </div>

      <!-- Next Actions -->
      <div v-if="briefing?.opportunities && briefing.opportunities.length > 0" class="animate-in space-y-3">
        <p class="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Next Actions</p>
        <div v-for="(o, i) in briefing.opportunities.slice(0, 2)" :key="o.id || i">
          <Card class="p-4 flex items-center justify-between transition-all hover:border-primary/30">
            <div>
              <p class="text-sm font-semibold text-foreground">{{ o.name }}</p>
              <p class="text-[11px] text-muted-foreground">{{ o.category }}</p>
            </div>
            <div class="flex items-center gap-3">
              <span class="text-sm font-bold text-success">${{ o.estimated_payout?.toLocaleString() || 0 }}</span>
              <button @click="router.push('/actions')"
                class="rounded-md bg-primary px-3 py-1.5 text-[10px] font-semibold text-white transition-all hover:bg-primary/90"
              >Execute</button>
            </div>
          </Card>
        </div>
      </div>

      <!-- Critical Risk -->
      <div v-if="briefing?.critical_risk" class="animate-in">
        <Card class="p-4 border-destructive/30 cursor-pointer transition-all hover:border-destructive/50"
          @click="router.push('/insights')"
        >
          <p class="text-[10px] font-bold uppercase tracking-wider text-destructive">{{ briefing.critical_risk.severity }} Risk</p>
          <p class="text-sm font-semibold text-foreground mt-1">{{ briefing.critical_risk.title }}</p>
        </Card>
      </div>

      <!-- System Insight -->
      <details v-if="briefing?.assistant_insight" class="animate-in cursor-pointer">
        <summary class="text-[10px] font-bold uppercase tracking-wider text-muted-foreground py-1">
          System Insight
        </summary>
        <p class="mt-2 text-xs text-muted-foreground leading-relaxed">
          {{ briefing.assistant_insight.focus }} — {{ briefing.assistant_insight.reason }}
        </p>
      </details>
    </template>
  </div>
</template>
