<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from '@/composables/useToast'
import { ArrowLeft, Plus, Shield, Trash2 } from '@lucide/vue'

const router = useRouter()
const { toast } = useToast()

const newName = ref('')
const newDomain = ref('')
const targets = ref<Array<{ id: number; name: string; domain: string | null; status: string }>>([])
const loading = ref(true)

async function fetchTargets() {
  try {
    const res = await fetch('/api/aegis/targets?limit=50')
    if (res.ok) {
      const data = await res.json()
      targets.value = data.targets || []
    }
  } catch {
    toast.error('Error', 'No se pudieron cargar los targets')
  } finally {
    loading.value = false
  }
}

async function addTarget() {
  if (!newName.value.trim()) return
  try {
    const res = await fetch('/api/aegis/targets', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: newName.value.trim(), domain: newDomain.value.trim() || null }),
    })
    if (res.ok) {
      toast.success('Target creado', `${newName.value} agregado a AEGIS`)
      newName.value = ''
      newDomain.value = ''
      await fetchTargets()
    }
  } catch {
    toast.error('Error', 'No se pudo crear el target')
  }
}

onMounted(fetchTargets)
</script>

<template>
  <div class="p-6 space-y-6">
    <div class="flex items-center gap-3">
      <button @click="router.push('/aegis/')" class="flex h-8 w-8 items-center justify-center rounded-lg text-muted-foreground hover:bg-surface transition-colors">
        <ArrowLeft class="h-4 w-4" />
      </button>
      <div class="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 ring-1 ring-primary/20">
        <Shield class="h-5 w-5 text-primary" />
      </div>
      <div>
        <h1 class="text-lg font-bold tracking-tight text-foreground">Configuración AEGIS</h1>
        <p class="text-xs text-muted-foreground">Administrar targets de pentesting</p>
      </div>
    </div>

    <!-- Add Target -->
    <div class="rounded-xl border border-border/40 bg-surface/40 p-4 space-y-3">
      <h2 class="text-sm font-semibold text-foreground">Nuevo target</h2>
      <div class="flex gap-3">
        <input v-model="newName" placeholder="Nombre del target" class="flex-1 rounded-lg border border-border/60 bg-surface/50 px-3 py-2 font-mono text-sm text-foreground placeholder:text-muted-foreground/50 focus:border-primary/30 focus:outline-none focus:ring-1 focus:ring-primary/20" />
        <input v-model="newDomain" placeholder="Dominio (opcional)" class="flex-1 rounded-lg border border-border/60 bg-surface/50 px-3 py-2 font-mono text-sm text-foreground placeholder:text-muted-foreground/50 focus:border-primary/30 focus:outline-none focus:ring-1 focus:ring-primary/20" />
        <button @click="addTarget" :disabled="!newName.trim()" class="flex items-center gap-1.5 rounded-lg bg-primary/20 px-4 py-2 text-sm text-primary hover:bg-primary/30 transition-colors disabled:opacity-40">
          <Plus class="h-4 w-4" />
          Agregar
        </button>
      </div>
    </div>

    <!-- Target List -->
    <div class="rounded-xl border border-border/40 bg-surface/40 p-4">
      <h2 class="text-sm font-semibold text-foreground mb-3">Targets registrados</h2>
      <div v-if="loading" class="text-sm text-muted-foreground">Cargando...</div>
      <div v-else-if="targets.length === 0" class="text-sm text-muted-foreground">Sin targets todavía.</div>
      <div v-else class="space-y-2">
        <div v-for="t in targets" :key="t.id" class="flex items-center justify-between rounded-lg border border-border/20 bg-surface/20 px-4 py-3">
          <div>
            <p class="text-sm text-foreground">{{ t.name }}</p>
            <p class="text-xs text-muted-foreground">{{ t.domain || 'Sin dominio' }}</p>
          </div>
          <span class="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded bg-surface text-muted-foreground border border-border/30">{{ t.status }}</span>
        </div>
      </div>
    </div>
  </div>
</template>
