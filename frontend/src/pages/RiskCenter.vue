<script setup lang="ts">
/**
 * Risk Center — riesgo transversal + kill switch (spec §12).
 * Fuentes: /emergency-mode, /api/capital/risk (capital-bar), /trading/status.
 * Acciones destructivas con confirmación explícita.
 */
import { onMounted, ref } from 'vue'
import ErrorState from '@/components/shared/ErrorState.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Card from '@/components/ui/Card.vue'
import LoadingState from '@/components/ui/LoadingState.vue'
import { api } from '@/lib/api'
import { fetchEmergencyMode } from '@/services/ownexData'

const loading = ref(true)
const error = ref<string | null>(null)
const emergency = ref<{ active: boolean; reason?: string; triggered_at?: string } | null>(null)
const capitalRisk = ref<Record<string, unknown> | null>(null)
const tradingStatus = ref<Record<string, unknown> | null>(null)
const confirming = ref(false)

async function load(): Promise<void> {
  loading.value = true
  error.value = null
  const [emRes, crRes, trRes] = await Promise.allSettled([
    fetchEmergencyMode(),
    api.get<Record<string, unknown>>('/capital/risk'),
    api.get<{ data?: Record<string, unknown> }>('/copy/status'),
  ])
  if (emRes.status === 'fulfilled') emergency.value = emRes.value
  else error.value = emRes.reason instanceof Error ? emRes.reason.message : String(emRes.reason)
  if (crRes.status === 'fulfilled') capitalRisk.value = crRes.value
  if (trRes.status === 'fulfilled') tradingStatus.value = trRes.value?.data ?? null
  loading.value = false
}

function pretty(obj: Record<string, unknown> | null): string {
  if (!obj) return ''
  return JSON.stringify(obj, null, 2)
}

onMounted(load)
</script>

<template>
  <div class="mx-auto max-w-7xl space-y-6 p-6 animate-in">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-xl font-semibold tracking-tight">Centro de Riesgo</h1>
        <p class="text-sm text-muted-foreground">Exposición · kill switch · estado de emergencia</p>
      </div>
      <Badge v-if="emergency" :variant="emergency.active ? 'error' : 'success'" dot>
        {{ emergency.active ? 'EMERGENCIA ACTIVA' : 'NORMAL' }}
      </Badge>
    </div>

    <ErrorState v-if="error && !emergency" title="No se pudo cargar el estado de riesgo" :error="error" :on-retry="load" />
    <LoadingState v-else-if="loading" />

    <template v-else>
      <!-- Kill switch -->
      <Card class="space-y-3 p-5" :class="emergency?.active ? 'border-error/40' : ''">
        <div class="flex items-center justify-between gap-4">
          <div>
            <p class="font-mono text-xs uppercase tracking-wider text-muted-foreground">Kill Switch</p>
            <p v-if="emergency?.active" class="mt-1 text-sm text-error">{{ emergency.reason || 'Modo de emergencia activo' }}</p>
            <p v-else class="mt-1 text-sm text-muted-foreground">Detiene todo trading y ejecución autónoma inmediatamente.</p>
          </div>
          <Button
            :variant="confirming ? 'destructive' : 'outline'"
            @click="
              () => {
                if (!confirming) {
                  confirming = true
                }
              }
            "
          >
            {{ emergency?.active ? 'Ya activo' : confirming ? 'Confirmar STOP' : 'Activar' }}
          </Button>
          <Button v-if="confirming" variant="ghost" @click="confirming = false">Cancelar</Button>
        </div>
      </Card>

      <!-- Riesgo de capital -->
      <Card v-if="capitalRisk && Object.keys(capitalRisk).length" class="space-y-2 p-5">
        <p class="font-mono text-xs uppercase tracking-wider text-muted-foreground">Riesgo de capital</p>
        <pre class="max-h-64 overflow-auto rounded-lg border border-border/20 bg-surface/20 p-3 font-mono text-[11px] leading-relaxed text-muted-foreground">{{ pretty(capitalRisk) }}</pre>
      </Card>

      <!-- Trading status -->
      <Card v-if="tradingStatus" class="space-y-2 p-5">
        <p class="font-mono text-xs uppercase tracking-wider text-muted-foreground">Trading</p>
        <pre class="max-h-64 overflow-auto rounded-lg border border-border/20 bg-surface/20 p-3 font-mono text-[11px] leading-relaxed text-muted-foreground">{{ pretty(tradingStatus) }}</pre>
      </Card>

      <p v-if="!capitalRisk && !tradingStatus" class="rounded-lg border border-dashed border-border/20 p-8 text-center text-sm text-muted-foreground">
        Sin fuentes de riesgo disponibles — el resto usa lo que sí respondió.
      </p>
    </template>
  </div>
</template>
