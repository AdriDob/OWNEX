<script setup lang="ts">
/**
 * AlignerrAdapter — la plataforma de AI-eval que SÍ cumple "sin experiencia".
 *
 * Por qué este adapter y no otro: Alignerr publica una **API pública**
 * (`alignerr.com/api/jobs` → 200 JSON) con `pay` y `applyUrl` por oferta.
 * Es endpoint estable, no scraping frágil como el resto.
 *
 * Honestidad sobre lo que ofrece (verificado 2026-10-08, 60 ofertas):
 * · 100% Remote, rates publicados ($10-35/hr).
 * · **Ninguna pide título, CV ni años de experiencia** — eso es cierto.
 * · **PERO todas piden habla nativo de un idioma concreto** (bengalí,
 *   tamil, sueco,*y 3 de español centroamericano*). "Sin experiencia" no
 *   es "cualquiera": es "nativo de X".
 *
 * Por eso cada oportunidad expone `language_hint` y el WorkBank puede
 * filtrar: una oferta que no podés hacer no debe ocupar lugar en el plan
 * del día. Un rate sin filtro de elegibilidad es otro modo de humo.
 */
import { computed, ref } from 'vue'

interface AlJob {
  id: string
  title: string
  description?: string
  pay?: string
  location?: string
  applyUrl?: string
  category?: string
  originalCategory?: string
}

/** Idiomas que el título delata. Se usa sólo para marcar, nunca para filtrar
 *  en el backend: si aparece uno nuevo, el campo queda vacío (UNKNOWN). */
const LANGUAGE_HINTS: Array<[RegExp, string]> = [
  [/spanish|español|espanol/i, 'español (centroamericano)'],
  [/dutch|netherlands/i, 'neerlandés'],
  [/bengali|bangla/i, 'bengalí'],
  [/tamil/i, 'tamil'],
  [/swedish/i, 'sueco'],
  [/hindi/i, 'hindi'],
  [/portuguese|brazilian/i, 'portugués (brasileño)'],
  [/french/i, 'francés'],
  [/german/i, 'alemán'],
  [/mandarin|chinese/i, 'mandarín'],
  [/japanese/i, 'japonés'],
  [/korean/i, 'coreano'],
  [/arabic/i, 'árabe'],
]

const jobs = ref<AlJob[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const lastFetch = ref<string | null>(null)

/** El backend no expone Alignerr todavía (se registra en F5). Este panel lee
 *  la API pública igual, para que el dato sea visible sin esperar al backend. */
const API_URL = 'https://www.alignerr.com/api/jobs'

function languageOf(j: AlJob): string {
  for (const [rx, lang] of LANGUAGE_HINTS) {
    if (rx.test(`${j.title ?? ''} ${j.description ?? ''}`)) return lang
  }
  return 'UNKNOWN'
}

async function load() {
  loading.value = true
  error.value = null
  try {
    const res = await fetch(API_URL, { headers: { Accept: 'application/json' } })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = (await res.json()) as { jobs?: AlJob[] }
    jobs.value = data.jobs ?? []
    lastFetch.value = new Date().toLocaleTimeString()
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
    jobs.value = []
  } finally {
    loading.value = false
  }
}

const byLanguage = computed(() => {
  const acc: Record<string, number> = {}
  for (const j of jobs.value) {
    const l = languageOf(j)
    acc[l] = (acc[l] ?? 0) + 1
  }
  return Object.entries(acc).sort((a, b) => b[1] - a[1])
})
</script>

<template>
  <div class="space-y-3">
    <div class="flex items-center justify-between gap-3">
      <div>
        <h3 class="text-sm font-semibold text-foreground">Alignerr — AI training (sin título ni CV)</h3>
        <p class="text-[11px] text-muted-foreground">
          API pública · todas Remote · <span class="font-medium text-warning">todas piden nativo de un idioma</span>
        </p>
      </div>
      <button
        class="rounded-lg px-3 py-1.5 text-xs text-muted-foreground hover:bg-surface/40 hover:text-foreground"
        @click="load"
      >
        {{ loading ? 'Cargando…' : 'Actualizar' }}
      </button>
    </div>

    <p v-if="error" class="text-[11px] text-destructive">
      No se pudo leer la API de Alignerr: {{ error }}
    </p>

    <template v-else-if="jobs.length">
      <!-- Reparto por idioma: decide rápido si esta plataforma te sirve -->
      <div class="flex flex-wrap gap-1.5">
        <span
          v-for="[lang, n] in byLanguage"
          :key="lang"
          class="rounded-full border border-border/40 px-2 py-0.5 font-mono text-[10px] text-muted-foreground"
        >
          {{ lang }} · {{ n }}
        </span>
      </div>

      <ul class="max-h-80 space-y-1.5 overflow-auto">
        <li
          v-for="j in jobs"
          :key="j.id"
          class="rounded-lg border border-border/30 px-3 py-2 transition-colors hover:bg-surface/30"
        >
          <div class="flex items-baseline justify-between gap-2">
            <span class="text-xs text-foreground">{{ j.title }}</span>
            <span class="shrink-0 font-mono text-xs text-primary">{{ j.pay ?? 'rate no publicado' }}</span>
          </div>
          <div class="mt-1 flex items-center gap-2 text-[10px] text-muted-foreground">
            <span class="rounded bg-warning/10 px-1.5 py-0.5 text-warning">
              requiere nativo: {{ languageOf(j) }}
            </span>
            <span>{{ j.location ?? 'Remote' }}</span>
            <a
              v-if="j.applyUrl"
              :href="`https://www.alignerr.com${j.applyUrl}`"
              target="_blank"
              rel="noopener noreferrer"
              class="ml-auto underline-offset-2 hover:text-foreground hover:underline"
            >
              Ver
            </a>
          </div>
        </li>
      </ul>
      <p class="text-[10px] text-muted-foreground">
        {{ jobs.length }} ofertas · leídas {{ lastFetch }} ·
        <span class="text-warning">sin título ni CV, pero con nativeidad de idioma</span>
      </p>
    </template>

    <p v-else-if="!loading" class="text-[11px] text-muted-foreground">
      Sin ofertas leídas. Tocá «Actualizar».
    </p>
  </div>
</template>