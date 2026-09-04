<script setup lang="ts">
import {
  AlertTriangle,
  Brain,
  CheckCircle2,
  Lightbulb,
  Plus,
  Search,
  Star,
  Target,
  Trash2,
  TrendingUp,
} from '@lucide/vue'
import { computed, onMounted, ref } from 'vue'
import DoughnutChart from '@/components/charts/DoughnutChart.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Card from '@/components/ui/Card.vue'
import Input from '@/components/ui/Input.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import { api } from '@/lib/api'

interface Pattern {
  id: number
  category: string
  observation: string
  context: string | null
  confidence: number
  evidence_count: number
  tags: string | null
  source_program_id: number | null
  created_at: string | null
}

const items = ref<Pattern[]>([])
const loading = ref(true)
const error = ref<string | null>(null)
const search = ref('')
const categoryFilter = ref('')
const showCreate = ref(false)
const newObservation = ref('')
const newCategory = ref('tech')
const newTags = ref('')
const creating = ref(false)

const categories = ['tech', 'platform', 'vuln_type', 'company_type', 'general']

onMounted(async () => {
  await fetchPatterns()
})

async function fetchPatterns() {
  loading.value = true
  try {
    const params: Record<string, any> = { limit: 100 }
    if (categoryFilter.value) params.category = categoryFilter.value
    if (search.value) params.search = search.value
    const res = await api.get<{ items: Pattern[]; total: number }>('/economic/patterns', params)
    items.value = res.items || []
  } catch (e: any) {
    error.value = e?.message || 'Error al cargar patrones'
    items.value = []
  } finally {
    loading.value = false
  }
}

const filtered = computed(() => {
  let list = items.value
  if (search.value) {
    const q = search.value.toLowerCase()
    list = list.filter((p) => p.observation.toLowerCase().includes(q))
  }
  return list.sort((a, b) => b.confidence - a.confidence)
})

async function createPattern() {
  if (!newObservation.value.trim()) return
  creating.value = true
  try {
    await api.post('/economic/patterns', {
      category: newCategory.value,
      observation: newObservation.value.trim(),
      tags: newTags.value ? JSON.stringify(newTags.value.split(',').map((t: string) => t.trim())) : null,
    })
    newObservation.value = ''
    newTags.value = ''
    showCreate.value = false
    await fetchPatterns()
  } catch {
    /* ignore */
  } finally {
    creating.value = false
  }
}

async function deletePattern(id: number) {
  try {
    await api.delete(`/economic/patterns/${id}`)
    items.value = items.value.filter((p) => p.id !== id)
  } catch {
    /* ignore */
  }
}

function categoryLabel(cat: string) {
  const map: Record<string, string> = {
    tech: 'Tecnología',
    platform: 'Plataforma',
    vuln_type: 'Vulnerabilidad',
    company_type: 'Tipo de empresa',
    general: 'General',
  }
  return map[cat] || cat
}

function confidenceColor(c: number) {
  if (c >= 0.7) return 'success' as const
  if (c >= 0.4) return 'warning' as const
  return 'default' as const
}
</script>

<template>
  <div class="space-y-6">
    <div class="animate-in space-y-1">
      <p class="text-xs font-bold uppercase tracking-widest text-primary">Memory & Pattern Engine</p>
      <h1 class="font-display text-2xl font-bold text-foreground">Patrones Aprendidos</h1>
      <p class="text-sm text-muted-foreground">
        OWNEX aprende de tus resultados — cada patrón se fortalece con evidencia real
      </p>
    </div>

    <!-- Filters -->
    <div class="flex flex-wrap items-center gap-3 animate-in">
      <div class="relative max-w-xs">
        <Search class="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input v-model="search" placeholder="Buscar patrones..." class="pl-10" @input="fetchPatterns" />
      </div>
      <select v-model="categoryFilter" @change="fetchPatterns"
        class="rounded-lg border border-border/60 bg-surface/60 px-3 py-2 text-xs text-foreground">
        <option value="">Todas las categorías</option>
        <option v-for="c in categories" :key="c" :value="c">{{ categoryLabel(c) }}</option>
      </select>
      <Button variant="default" size="sm" @click="showCreate = !showCreate">
        <Plus class="mr-1 h-3 w-3" /> Nuevo patrón
      </Button>
    </div>

    <!-- Create form -->
    <div v-if="showCreate" class="animate-in rounded-xl border border-primary/30 bg-surface/60 p-4 space-y-3">
      <p class="text-xs font-semibold text-foreground">Registrar nuevo patrón</p>
      <Input v-model="newObservation" placeholder="Ej: Las empresas fintech pagan mejor los IDOR" />
      <div class="flex items-center gap-3">
        <select v-model="newCategory" class="rounded-lg border border-border/60 bg-surface/60 px-3 py-2 text-xs text-foreground flex-1">
          <option v-for="c in categories" :key="c" :value="c">{{ categoryLabel(c) }}</option>
        </select>
        <Input v-model="newTags" placeholder="Tags: fintech,idor (opcional)" class="flex-1" />
      </div>
      <div class="flex justify-end gap-2">
        <Button variant="ghost" size="sm" @click="showCreate = false">Cancelar</Button>
        <Button variant="default" size="sm" :disabled="creating || !newObservation.trim()" @click="createPattern">
          {{ creating ? 'Guardando...' : 'Guardar patrón' }}
        </Button>
      </div>
    </div>

    <template v-if="loading">
      <div class="space-y-3"><Skeleton v-for="i in 4" :key="i" class="h-24 rounded-xl" /></div>
    </template>

    <template v-else-if="error">
      <div class="flex flex-col items-center justify-center py-24 text-center">
        <AlertTriangle class="h-10 w-10 text-destructive mb-4" />
        <p class="text-lg font-semibold text-foreground">Error de conexión</p>
        <p class="mt-2 text-sm text-muted-foreground">{{ error }}</p>
        <Button class="mt-6" @click="fetchPatterns">Reintentar</Button>
      </div>
    </template>

    <template v-else-if="filtered.length">
      <!-- Pattern type distribution -->
      <Card class="p-4 animate-in">
        <h3 class="text-xs font-semibold text-foreground mb-3">Tipos de Patrones</h3>
        <DoughnutChart
          :labels="categories.map(c => categoryLabel(c))"
          :data="categories.map(c => items.filter(p => p.category === c).length)"
          :height="200"
        />
      </Card>

      <div class="space-y-3 animate-in">
        <Card v-for="(p, i) in filtered" :key="p.id" class="p-4 stagger-item" :style="{ '--i': i }"
          :class="p.confidence >= 0.7 ? 'border-l-2 border-l-success' : p.confidence >= 0.4 ? 'border-l-2 border-l-warning' : ''">
          <div class="flex items-start gap-3">
            <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg"
              :class="p.category === 'tech' ? 'bg-primary/15 text-primary' : p.category === 'platform' ? 'bg-accent/15 text-accent' : p.category === 'vuln_type' ? 'bg-warning/15 text-warning' : 'bg-surface/40 text-muted-foreground'">
              <Brain class="h-4 w-4" />
            </div>
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 flex-wrap">
                <Badge variant="outline" class="text-[9px]">{{ categoryLabel(p.category) }}</Badge>
                <Badge :variant="confidenceColor(p.confidence)" class="text-[9px]">
                  {{ (p.confidence * 100).toFixed(0) }}% confianza
                </Badge>
                <span class="text-[10px] text-muted-foreground">{{ p.evidence_count }} evidencia{{ p.evidence_count !== 1 ? 's' : '' }}</span>
              </div>
              <p class="mt-2 text-sm font-medium text-foreground">{{ p.observation }}</p>
              <p v-if="p.context" class="mt-1 text-xs text-muted-foreground">{{ p.context }}</p>
              <div v-if="p.tags" class="mt-2 flex flex-wrap gap-1">
                <span v-for="tag in (() => { try { return JSON.parse(p.tags!) } catch { return [p.tags] } })()" :key="tag"
                  class="rounded-full bg-surface/30 px-2 py-0.5 text-[10px] text-muted-foreground">
                  {{ tag }}
                </span>
              </div>
            </div>
            <button class="shrink-0 text-muted-foreground hover:text-destructive transition-colors" @click="deletePattern(p.id)">
              <Trash2 class="h-3.5 w-3.5" />
            </button>
          </div>
        </Card>
      </div>
    </template>

    <div v-else class="flex flex-col items-center py-20 text-center">
      <Brain class="mb-4 h-10 w-10 text-muted-foreground" />
      <p class="text-sm text-muted-foreground">No hay patrones registrados todavía</p>
      <p class="mt-1 text-xs text-muted-foreground">Los patrones se crean automáticamente o los podés agregar manualmente</p>
      <Button variant="default" size="sm" class="mt-4" @click="showCreate = true">
        <Plus class="mr-1 h-3 w-3" /> Crear primer patrón
      </Button>
    </div>
  </div>
</template>
