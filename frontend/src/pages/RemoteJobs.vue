<script setup lang="ts">
/**
 * Remote Jobs — búsqueda real de empleos remotos rankeados por remote_job_matcher.
 * Fuente: GET /api/opportunities/remote-jobs/search (Remotive/Arbeitnow/RemoteOK).
 */
import { ref } from 'vue'
import { Search } from 'lucide-vue-next'
import { api } from '@/lib/api'
import Badge from '@/components/ui/Badge.vue'
import Card from '@/components/ui/Card.vue'
import Button from '@/components/ui/Button.vue'
import LoadingState from '@/components/ui/LoadingState.vue'
import ErrorState from '@/components/shared/ErrorState.vue'

interface JobMatch {
  score: number
  eligible: boolean
  reasons_positive: string[]
  requirements_missing: string[]
  risks: string[]
}

interface RemoteJob {
  title: string
  company?: string
  url?: string
  source?: string
  salary_min?: number | null
  salary_raw?: string
  match?: JobMatch
}

const query = ref('')
const jobs = ref<RemoteJob[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const searched = ref(false)

async function search() {
  loading.value = true
  error.value = null
  searched.value = true
  try {
    const data = await api.get<{ jobs: RemoteJob[]; count: number }>(
      `/opportunities/remote-jobs/search?q=${encodeURIComponent(query.value)}&limit=50`,
    )
    jobs.value = data.jobs ?? []
  } catch (e: any) {
    error.value = e?.message || 'Error buscando empleos'
    jobs.value = []
  } finally {
    loading.value = false
  }
}

function scoreVariant(score: number) {
  if (score >= 80) return 'success' as const
  if (score >= 60) return 'warning' as const
  return 'default' as const
}
</script>

<template>
  <div class="p-6 max-w-5xl mx-auto">
    <h1 class="text-xl font-semibold mb-1">Empleos Remotos</h1>
    <p class="text-sm text-muted-foreground mb-4">
      Vacantes reales (Remotive, Arbeitnow, RemoteOK) rankeadas por compatibilidad: geografía, requisitos, idioma, modalidad, salario y método de cobro.
    </p>

    <form class="flex gap-2 mb-6" @submit.prevent="search">
      <input
        v-model="query"
        type="search"
        placeholder="Buscar: soporte, python, data…"
        class="flex-1 rounded-md border border-border bg-background px-3 py-2 text-sm"
      />
      <Button type="submit" :disabled="loading">
        <Search class="w-4 h-4 mr-1" /> Buscar
      </Button>
    </form>

    <LoadingState v-if="loading" />
    <ErrorState v-else-if="error" :message="error" />
    <div v-else-if="searched && jobs.length === 0" class="text-sm text-muted-foreground">
      Sin resultados. Probá otra búsqueda o más tarde (los feeds públicos tienen cupos).
    </div>

    <div v-else class="space-y-3">
      <Card v-for="(job, i) in jobs" :key="i" class="p-4">
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0">
            <a
              v-if="job.url"
              :href="job.url"
              target="_blank"
              rel="noopener"
              class="font-medium text-primary hover:underline"
            >{{ job.title }}</a>
            <span v-else class="font-medium">{{ job.title }}</span>
            <p class="text-xs text-muted-foreground mt-0.5">
              {{ job.company }} · {{ job.source }}
              <template v-if="job.salary_min"> · desde {{ job.salary_min }} {{ job.salary_raw && !/^\d/.test(job.salary_raw) ? job.salary_raw : '' }}</template>
            </p>
          </div>
          <div class="flex items-center gap-2 shrink-0">
            <Badge :variant="scoreVariant(job.match?.score ?? 0)">
              {{ Math.round(job.match?.score ?? 0) }}
            </Badge>
            <Badge v-if="job.match && !job.match.eligible" variant="error">No elegible</Badge>
          </div>
        </div>

        <div v-if="job.match" class="mt-3 grid gap-2 text-xs">
          <div v-if="job.match.reasons_positive.length" class="text-emerald-500">
            + {{ job.match.reasons_positive.slice(0, 3).join(' · ') }}
          </div>
          <div v-if="job.match.risks.length" class="text-red-400">
            ! {{ job.match.risks.slice(0, 3).join(' · ') }}
          </div>
          <div v-if="job.match.requirements_missing.length" class="text-muted-foreground">
            ? {{ job.match.requirements_missing.slice(0, 3).join(' · ') }}
          </div>
        </div>
      </Card>
    </div>
  </div>
</template>
