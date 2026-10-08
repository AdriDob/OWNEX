<script setup lang="ts">
/**
 * PendingConfig — qué falta configurar para que el sistema esté completo.
 *
 * Responde al pedido del owner: *"todo lo que quede pendiente de
 * configuración debe aparecer en la configuración del sistema"*.
 *
 * Antes esa información estaba dispersa: 145 `os.getenv()` por el backend,
 * una tupla de 16 keys en el checklist, y docstrings que prometían
 * capacidades contingent on keys que nadie listaba. Resultado: una capacidad
 * gateada por una key invisible es una capacidad que no existe, y nadie
 * puede activarla sin leer código.
 *
 * Honestidad (regla del proyecto):
 * - `bloqueada` ≠ `degradada`. Una key opcional que falta NO bloquea nada;
 *   saying "bloqueada" cuando el sistema funciona es la misma clase de
 *   mentira que un 0 inventado.
 * - Nunca se muestran VALORES de variables, sólo si están presentes o no
 *   (el backend tampoco los manda).
 * - Una capacidad keyless se muestra como tal, no como "0 pendientes" que
 *   sugiere que le falta algo.
 */
import { computed, onMounted, ref } from 'vue'
import { CheckCircle2, CircleAlert, CircleDot, RefreshCw } from '@lucide/vue'
import { api } from '@/lib/api'

type Impact = 'bloqueada' | 'degradada' | 'ninguno'

type Requirement = {
  env: string
  present: boolean
  optional: boolean
  without: string
  where: string
}

type Capability = {
  id: string
  label: string
  category: string
  what: string
  impact: Impact
  configured: boolean
  missing_required: string[]
  missing_optional: string[]
  requirements: Requirement[]
}

type Snapshot = {
  capabilities: Capability[]
  totals: {
    capabilities: number
    configured: number
    pending_blocking: number
    envs_referenced: number
    envs_set: number
  }
  note: string
}

const snap = ref<Snapshot | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)

/** Agrupar por categoría sin inventar el orden: el backend ya agrupa. */
const byCategory = computed(() => {
  const out: Array<{ category: string; items: Capability[] }> = []
  for (const c of snap.value?.capabilities ?? []) {
    const last = out[out.length - 1]
    if (last && last.category === c.category) last.items.push(c)
    else out.push({ category: c.category, items: [c] })
  }
  return out
})

/** Sólo lo que requiere acción, ordenado por impacto real. */
const pending = computed(() =>
  (snap.value?.capabilities ?? [])
    .filter((c) => c.impact !== 'ninguno')
    .sort((a, b) => {
      const rank = (i: Impact) => (i === 'bloqueada' ? 0 : i === 'degradada' ? 1 : 2)
      return rank(a.impact) - rank(b.impact)
    }),
)

const blocked = computed(() => pending.value.filter((c) => c.impact === 'bloqueada'))
const degraded = computed(() => pending.value.filter((c) => c.impact === 'degradada'))

const IMPACT_TEXT: Record<Impact, string> = {
  bloqueada: 'no arranca sin esto',
  degradada: 'funciona, pero con menos alcance',
  ninguno: 'sin configuración pendiente',
}

function impactClass(impact: Impact): string {
  if (impact === 'bloqueada') return 'text-[var(--color-sys-blocked)]'
  if (impact === 'degradada') return 'text-[var(--color-sys-degraded)]'
  return 'text-[var(--color-sys-healthy)]'
}

async function load() {
  loading.value = true
  error.value = null
  try {
    snap.value = await api.get<Snapshot>('/system/capabilities')
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'no se pudo consultar'
    snap.value = null
  } finally {
    loading.value = false
  }
}

  // ── Escribir y verificar (endpoints /system/capabilities/set y /check) ──
  const drafts = ref<Record<string, string>>({})
  const busy = ref<Record<string, boolean>>({})
  const results = ref<Record<string, { usable: boolean; detail: string }>>({})
  const whereCache = ref<Record<string, string>>({})

  function whereFor(env: string): string {
    return whereCache.value[env] ?? ''
  }

  /** Pide la instruccion real (enlace + pasos) al backend, una sola vez. */
  async function onWhereToggle(ev: Event, env: string): Promise<void> {
    if (!(ev.target as HTMLDetailsElement).open || whereCache.value[env]) return
    try {
      const r = await api.post<{ where: string }>('/system/capabilities/check', { env })
      whereCache.value = { ...whereCache.value, [env]: r.where }
    } catch {
      whereCache.value = { ...whereCache.value, [env]: 'Sin instrucciones para esta variable.' }
    }
  }

  /** Guarda y verifica en una ida: `set` ya devuelve el resultado del check. */
  async function save(env: string): Promise<void> {
    const value = (drafts.value[env] ?? '').trim()
    if (!value || busy.value[env]) return
    busy.value = { ...busy.value, [env]: true }
    try {
      const r = await api.post<{ usable: boolean; detail: string }>('/system/capabilities/set', {
        env,
        value,
      })
      results.value = { ...results.value, [env]: { usable: r.usable, detail: r.detail } }
      if (r.where) whereCache.value = { ...whereCache.value, [env]: r.where }
      drafts.value = { ...drafts.value, [env]: '' }
      await load()
    } catch (e) {
      results.value = {
        ...results.value,
        [env]: { usable: false, detail: e instanceof Error ? e.message : 'no se pudo guardar' },
      }
    } finally {
      busy.value = { ...busy.value, [env]: false }
    }
  }

  /** Sólo comprueba: sirve para variables ya puestas en el fichero. */
  async function check(env: string): Promise<void> {
    if (busy.value[env]) return
    busy.value = { ...busy.value, [env]: true }
    try {
      const r = await api.post<{ usable: boolean; detail: string }>('/system/capabilities/check', { env })
      results.value = { ...results.value, [env]: { usable: r.usable, detail: r.detail } }
      if (r.where) whereCache.value = { ...whereCache.value, [env]: r.where }
    } catch (e) {
      results.value = {
        ...results.value,
        [env]: { usable: false, detail: e instanceof Error ? e.message : 'no se pudo comprobar' },
      }
    } finally {
      busy.value = { ...busy.value, [env]: false }
    }
  }

onMounted(load)
</script>

<template>
  <section class="rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)]">
    <header class="flex flex-wrap items-center justify-between gap-2 px-4 py-3 border-b border-[var(--color-border)]">
      <div>
        <h2 class="text-[var(--text-heading)] font-[var(--font-weight-semibold)]">Configuración pendiente</h2>
        <p class="text-[var(--text-caption)] text-[var(--color-text-muted)]">
          <template v-if="loading">consultando…</template>
          <template v-else-if="snap">
            <template v-if="blocked.length">
              <span class="text-[var(--color-sys-blocked)]">{{ blocked.length }} bloqueada(s)</span> ·
            </template>
            <template v-if="degraded.length">{{ degraded.length }} degradada(s) · </template>
            <template v-if="!blocked.length && !degraded.length">todo completo · </template>
            {{ snap.totals.envs_set }}/{{ snap.totals.envs_referenced }} variables presentes
          </template>
          <template v-else>sin datos</template>
        </p>
      </div>
      <button
        class="flex items-center gap-1 text-[var(--text-label)] text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] disabled:opacity-50"
        :disabled="loading"
        aria-label="Refrescar configuración pendiente"
        @click="load"
      >
        <RefreshCw :size="14" :class="loading ? 'animate-spin' : ''" />
        refrescar
      </button>
    </header>

    <p v-if="error" class="px-4 py-6 text-[var(--text-body)] text-[var(--color-sys-blocked)]">
      No se pudo consultar: {{ error }}
    </p>

    <p
      v-else-if="!loading && snap && !pending.length"
      class="px-4 py-6 text-[var(--text-body)] text-[var(--color-text-muted)]"
    >
      Ninguna capacidad requiere configuración. Las {{ snap.totals.capabilities }} capacidades listadas
      funcionan con lo que hay.
    </p>

    <div v-else class="divide-y divide-[var(--color-border)]">
      <div v-for="group in byCategory" :key="group.category" class="px-4 py-3">
        <h3 class="text-[var(--text-label)] uppercase tracking-wide text-[var(--color-text-muted)]">
          {{ group.category }}
        </h3>

        <div v-for="c in group.items" :key="c.id" class="mt-2">
          <div class="flex flex-wrap items-baseline gap-x-2">
            <span
              v-if="c.impact === 'bloqueada'"
              class="inline-flex items-center gap-1 text-[var(--color-sys-blocked)]"
            >
              <CircleAlert :size="12" />
            </span>
            <span
              v-else-if="c.impact === 'degradada'"
              class="inline-flex items-center gap-1 text-[var(--color-sys-degraded)]"
            >
              <CircleDot :size="12" />
            </span>
            <span v-else class="inline-flex items-center gap-1 text-[var(--color-sys-healthy)]">
              <CheckCircle2 :size="12" />
            </span>

            <span class="text-[var(--text-body)] text-[var(--color-text-primary)]">{{ c.label }}</span>
            <span class="text-[var(--text-caption)]" :class="impactClass(c.impact)">
              {{ IMPACT_TEXT[c.impact] }}
            </span>
          </div>

          <p class="mt-0.5 text-[var(--text-caption)] text-[var(--color-text-muted)]">{{ c.what }}</p>

          <!-- Variables faltantes -->
          <ul v-if="c.missing_required.length || c.missing_optional.length" class="mt-2 space-y-1.5">
              <li
                v-for="r in c.requirements.filter((x) => !x.present)"
                :key="r.env"
                class="rounded-[var(--radius-md)] border border-[var(--color-border)] px-3 py-2"
              >
                <div class="flex flex-wrap items-baseline gap-x-2">
                  <code class="font-[var(--font-numeric)] text-[var(--text-label)] text-[var(--color-text-primary)]">
                    {{ r.env }}
                  </code>
                  <span class="text-[var(--text-caption)] text-[var(--color-text-muted)]">
                    {{ r.optional ? 'opcional' : 'requerida' }}
                  </span>
                </div>
                <p class="mt-0.5 text-[var(--text-caption)] text-[var(--color-text-muted)]">{{ r.without }}</p>

                <!-- Donde conseguirla: enlace + pasos. `r.where` en el snapshot
                     es generico ("Variables de entorno"); la instruccion real
                     vive en KEY_SOURCES y llega en la respuesta de /check. -->
                <details class="mt-1.5" @toggle="onWhereToggle($event, r.env)">
                  <summary class="cursor-pointer text-[var(--text-caption)] text-[var(--color-text-primary)]">
                    Donde conseguirla
                  </summary>
                  <p
                    v-if="whereFor(r.env)"
                    class="mt-1 whitespace-pre-line text-[var(--text-caption)] text-[var(--color-text-muted)]"
                  >
                    {{ whereFor(r.env) }}
                  </p>
                  <p v-else class="mt-1 text-[var(--text-caption)] text-[var(--color-text-muted)]">
                    cargando…
                  </p>
                </details>

                <div class="mt-2 flex flex-wrap items-center gap-1.5">
                  <input
                    v-model="drafts[r.env]"
                    type="password"
                    autocomplete="off"
                    spellcheck="false"
                    :placeholder="r.env"
                    class="min-w-0 flex-1 rounded-[var(--radius-sm)] border border-[var(--color-border)] bg-transparent px-2 py-1 text-[var(--text-label)] text-[var(--color-text-primary)] outline-none focus:border-[var(--color-text-primary)]"
                  />
                  <button
                    type="button"
                    :disabled="busy[r.env] || !(drafts[r.env] ?? '').trim()"
                    @click="save(r.env)"
                    class="rounded-[var(--radius-sm)] border border-[var(--color-border)] px-2 py-1 text-[var(--text-caption)] text-[var(--color-text-primary)] disabled:opacity-40"
                  >
                    {{ busy[r.env] ? '…' : 'Guardar' }}
                  </button>
                  <button
                    type="button"
                    :disabled="busy[r.env]"
                    @click="check(r.env)"
                    class="rounded-[var(--radius-sm)] border border-[var(--color-border)] px-2 py-1 text-[var(--text-caption)] text-[var(--color-text-muted)] disabled:opacity-40"
                  >
                    {{ busy[r.env] ? '…' : 'Check' }}
                  </button>
                </div>

                <p
                  v-if="results[r.env]"
                  class="mt-1 text-[var(--text-caption)]"
                  :class="results[r.env].usable ? 'text-[var(--color-sys-healthy)]' : 'text-[var(--color-sys-degraded)]'"
                >
                  {{ results[r.env].usable ? '✓' : '✗' }} {{ results[r.env].detail }}
                </p>
              </li>
          </ul>
        </div>
      </div>
    </div>

    <p
      v-if="snap"
      class="border-t border-[var(--color-border)] px-4 py-3 text-[var(--text-caption)] text-[var(--color-text-muted)]"
    >
      {{ snap.note }}. Ponelas acá mismo: cada variable trae dónde conseguirla,
        un campo para escribirla, y un Check que dice si funciona.
    </p>
  </section>
</template>
