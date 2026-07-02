<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { getAttackDecision } from '@/lib/api'
import type { HotPathItem, AttackDecisionResponse } from '@/lib/api'
import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import { Route, AlertTriangle, ArrowRight, Shield } from '@lucide/vue'
import BarChart from '@/components/charts/BarChart.vue'

const data = ref<AttackDecisionResponse | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

onMounted(async () => {
  try {
    data.value = await getAttackDecision({ limit: 20 })
  } catch (e: any) {
    error.value = e?.message || 'Error al cargar hot paths'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="space-y-6">
    <div class="animate-in space-y-1">
      <p class="text-xs font-bold uppercase tracking-widest text-primary">Attack Surface</p>
      <h1 class="font-display text-2xl font-bold text-foreground">Hot Paths</h1>
      <p class="text-sm text-muted-foreground">Rutas priorizadas con alta probabilidad de explotación</p>
    </div>

    <!-- Loading -->
    <template v-if="loading">
      <div class="space-y-3">
        <Skeleton v-for="i in 4" :key="i" class="h-28 rounded-xl" />
      </div>
    </template>

    <!-- Error -->
    <template v-else-if="error">
      <div class="flex flex-col items-center py-16 text-center">
        <Shield class="h-10 w-10 text-muted-foreground mb-4" />
        <p class="text-sm text-muted-foreground">{{ error }}</p>
      </div>
    </template>

    <!-- Summary -->
    <template v-else-if="data">
      <p v-if="data.summary" class="text-sm text-muted-foreground animate-in">{{ data.summary }}</p>

      <!-- Risk Distribution -->
      <Card class="p-4 animate-in">
        <h3 class="text-xs font-semibold text-foreground mb-3">Distribución de Riesgo</h3>
        <BarChart
          :labels="data.high_value_targets?.slice(0, 10).map(h => h.path) || []"
          :datasets="[{ label: 'Risk Score', data: data.high_value_targets?.slice(0, 10).map(h => h.risk_score) || [] }]"
          :height="200"
        />
      </Card>

      <!-- Attack Vectors Summary -->
      <div v-if="data.attack_vectors?.length" class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2 animate-in">
        <Card v-for="av in data.attack_vectors" :key="av.vector" class="p-3 text-center">
          <p class="text-xs font-semibold text-foreground truncate">{{ av.vector }}</p>
          <p class="text-xs text-muted-foreground mt-1">{{ av.count }} endpoints</p>
        </Card>
      </div>

      <!-- Hot Paths List -->
      <div class="space-y-3">
        <h2 class="text-sm font-semibold text-foreground">High-Value Targets</h2>
        <Card v-for="(hp, i) in data.high_value_targets" :key="i" class="p-4 stagger-item" :style="{ '--i': i }">
          <div class="flex items-start gap-4">
            <div class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg"
              :class="hp.risk_score >= 8 ? 'bg-destructive/15 text-destructive' : hp.risk_score >= 5 ? 'bg-warning/15 text-warning' : 'bg-accent/15 text-accent'"
            >
              <Route class="h-4 w-4" />
            </div>
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 flex-wrap">
                <Badge
                  :variant="hp.risk_score >= 8 ? 'destructive' : hp.risk_score >= 5 ? 'warning' : 'info'"
                  class="text-[10px] px-1.5 py-0"
                >
                  riesgo {{ hp.risk_score.toFixed(1) }}
                </Badge>
                <Badge v-if="hp.ownership_risk" variant="warning" class="text-[10px] px-1.5 py-0">ownership</Badge>
              </div>
              <p class="mt-1 text-sm font-mono font-semibold text-foreground">{{ hp.method }} {{ hp.path }}</p>
              <p class="mt-1 text-xs text-muted-foreground">Vector: <span class="text-foreground font-medium">{{ hp.vector }}</span></p>
              <p class="mt-1 text-xs text-muted-foreground">{{ hp.reason }}</p>
              <div v-if="hp.suggestions?.length" class="mt-2 flex flex-wrap gap-1">
                <span v-for="s in hp.suggestions.slice(0, 3)" :key="s" class="text-[10px] px-2 py-0.5 rounded-full bg-surface text-muted-foreground">{{ s }}</span>
              </div>
            </div>
            <Button variant="ghost" size="icon"><ArrowRight class="h-4 w-4" /></Button>
          </div>
        </Card>

        <div v-if="!data.high_value_targets?.length" class="py-12 text-center text-sm text-muted-foreground">
          No hay hot paths disponibles para evaluar
        </div>
      </div>

      <!-- Manual Test Suggestions -->
      <div v-if="data.manual_test_suggestions?.length" class="space-y-2">
        <h2 class="text-sm font-semibold text-foreground">Sugerencias de Prueba Manual</h2>
        <Card class="p-4">
          <ul class="space-y-2">
            <li v-for="(s, i) in data.manual_test_suggestions" :key="i" class="flex items-start gap-2 text-xs text-muted-foreground">
              <span class="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-accent/10 text-accent text-[10px] font-bold">{{ i + 1 }}</span>
              {{ s }}
            </li>
          </ul>
        </Card>
      </div>
    </template>
  </div>
</template>
