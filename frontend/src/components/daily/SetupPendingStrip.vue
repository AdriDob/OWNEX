<script setup lang="ts">
/**
 * SetupPendingStrip — aviso genérico de configuración faltante en el command center.
 * Muestra la próxima tarea ESENCIAL pendiente del setup checklist (la que sea:
 * IA, keys, pagos, target, materiales...) + contador de esenciales restantes.
 * Se oculta solo cuando todo lo esencial está completo o el backend no responde.
 * Degrada en silencio (oculto) si el backend no responde.
 */
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Settings } from '@lucide/vue'
import OwnexButton from '@/components/ui/OwnexButton.vue'
import { fetchSetupChecklistStatus } from '@/services/ownexData'

const router = useRouter()
const visible = ref(false)
const pendingCount = ref(0)
const title = ref('')
const howTo = ref('')
const estMinutes = ref<number | null>(null)

async function load(): Promise<void> {
  try {
    const status = await fetchSetupChecklistStatus()
    const essentials = (status.pending ?? []).filter((p) => p.phase === 'essentials')
    if (essentials.length === 0) {
      visible.value = false
      return
    }
    pendingCount.value = essentials.length
    const next = status.next_task
    if (next) {
      title.value = next.title
      howTo.value = next.how_to
      estMinutes.value = next.est_minutes ?? null
    } else {
      title.value = essentials[0].title
      howTo.value = essentials[0].how_to ?? ''
      estMinutes.value = null
    }
    visible.value = true
  } catch {
    visible.value = false
  }
}

function open(): void {
  void router.push('/setup/checklist')
}

onMounted(() => {
  void load()
})
</script>

<template>
  <div
    v-if="visible"
    class="flex flex-wrap items-center gap-3 rounded-lg border border-warning/40 bg-warning/5 px-4 py-3"
  >
    <Settings class="h-5 w-5 shrink-0 text-warning" />
    <div class="min-w-44 flex-1">
      <div class="text-sm">
        <span class="opacity-70">⚙️ Config pendiente ({{ pendingCount }} esencial{{ pendingCount === 1 ? '' : 'es' }}):</span>
        <strong> {{ title }}</strong>
      </div>
      <div class="mt-0.5 text-xs opacity-70">
        {{ howTo }}<span v-if="estMinutes != null"> · ~{{ estMinutes }} min</span>
      </div>
    </div>
    <OwnexButton size="sm" variant="outline" @click="open">Configurar</OwnexButton>
  </div>
</template>
