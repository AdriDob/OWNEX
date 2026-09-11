<script setup lang="ts">
/**
 * MptPendingStrip — aviso compacto de pendiente Content Factory en el command center.
 * Muestra el ítem `mpt_material_key` del setup checklist solo mientras esté pendiente
 * (la key gratis de Pexels/Coverr es lo único que bloquea el primer Short).
 * Degrada en silencio (oculto) si el backend no responde.
 */
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Clapperboard } from '@lucide/vue'
import OwnexButton from '@/components/ui/OwnexButton.vue'
import { fetchSetupChecklistStatus } from '@/services/ownexData'

const router = useRouter()
const visible = ref(false)
const title = ref('')
const howTo = ref('')

async function load(): Promise<void> {
  try {
    const status = await fetchSetupChecklistStatus()
    const item = status.pending.find((p) => p.id === 'mpt_material_key')
    if (item) {
      title.value = item.title
      howTo.value = item.how_to
      visible.value = true
    } else {
      visible.value = false
    }
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
    <Clapperboard class="h-5 w-5 shrink-0 text-warning" />
    <div class="min-w-44 flex-1">
      <div class="text-sm">
        <span class="opacity-70">⏳ Pendiente Shorts:</span> <strong>{{ title }}</strong>
      </div>
      <div class="mt-0.5 text-xs opacity-70">{{ howTo }}</div>
    </div>
    <OwnexButton size="sm" variant="outline" @click="open">Ver checklist</OwnexButton>
  </div>
</template>
