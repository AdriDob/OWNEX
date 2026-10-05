<script setup lang="ts">
/**
 * DiffViewer — línea a línea, original vs. actual.
 *
 * Por qué existe: el deliverable de un bounty se judgea por el diff. Editar
 * un PoC o un README sin ver qué cambió es escribir a ciegas: el riesgo es
 * tirar código de más, o —peor— perder evidencia que ya estaba.
 *
 * Diff unificado (no side-by-side): el panel es angosto y en un PR de
 * seguridad leer "qué agregué / qué borré" en una sola columna es más rápido.
 * Las estadísticas usan las cuentas reales del diff, nunca las de `+1 -1`.
 */
import { computed } from 'vue'
import { diffLines } from 'diff'
import { cn } from '@/lib/utils'

export interface DiffLine {
  kind: 'add' | 'del' | 'ctx'
  value: string
  oldNo: number | null
  newNo: number | null
}

const props = withDefaults(
  defineProps<{
    original: string
    modified: string
    /** Nombre del archivo, para el encabezado. */
    filename?: string
    /** Colapsa bloques largos sin cambios. */
    context?: number
    class?: string
  }>(),
  { filename: '', context: 3, },
)

/**
 * Normaliza el salto final antes de diffear.
 *
 * Sin esto `diffLines` parte el texto en el último límite: si el original
 * no termina en `\n` (medido: 'uno\ndos' vs 'uno\ndos\ntres\ncuatro'),
 * devuelve *removed 'dos'* + *added 'dos\ntres\ncuatro'* — o sea 4 agregadas
 * y 1 borrada por tres líneas de verdad. Es un artefacto del tokenizador, no
 * un cambio de contenido, y hacía que el diff mintiera sobre el conteo.
 */
function withTrailingNewline(s: string): string {
  const text = s ?? ''
  if (text === '' || text.endsWith('\n')) return text
  return `${text}\n`
}

const parts = computed(() => diffLines(withTrailingNewline(props.original), withTrailingNewline(props.modified)))

const lines = computed<DiffLine[]>(() => {
  const out: DiffLine[] = []
  let oldNo = 1
  let newNo = 1
  for (const part of parts.value) {
    // `diffLines` no siempre termina en \n: part.value puede traer la última
    // línea sin salto. Split preserva el texto; el último elemento vacío se
    // descarta para no inventar una línea en blanco.
    const rows = part.value.split('\n')
    if (rows[rows.length - 1] === '') rows.pop()
    for (const value of rows) {
      if (part.added) {
        out.push({ kind: 'add', value, oldNo: null, newNo: newNo++ })
      } else if (part.removed) {
        out.push({ kind: 'del', value, oldNo: oldNo++, newNo: null })
      } else {
        out.push({ kind: 'ctx', value, oldNo: oldNo++, newNo: newNo++ })
      }
    }
  }
  return out
})

const stats = computed(() => {
  let added = 0
  let removed = 0
  for (const l of lines.value) {
    if (l.kind === 'add') added++
    else if (l.kind === 'del') removed++
  }
  return { added, removed, unchanged: lines.value.length - added - removed, total: lines.value.length }
})

const isDirty = computed(() => stats.value.added > 0 || stats.value.removed > 0)

/** Colapsa runs largos de contexto y los marca como "N líneas sin cambios". */
const hunks = computed(() => {
  const keep = Math.max(0, props.context)
  const res: Array<{ type: 'hunk'; line: DiffLine } | { type: 'gap'; count: number }> = []
  const keepIdx = new Set<number>()
  lines.value.forEach((l, i) => {
    if (l.kind === 'ctx') return
    for (let j = i - keep; j <= i + keep; j++) if (j >= 0 && j < lines.value.length) keepIdx.add(j)
  })
  let gap = 0
  lines.value.forEach((l, i) => {
    if (keepIdx.has(i) || lines.value.length <= keep * 2 + 4) {
      if (gap > 0) {
        res.push({ type: 'gap', count: gap })
        gap = 0
      }
      res.push({ type: 'hunk', line: l })
    } else {
      gap++
    }
  })
  if (gap > 0) res.push({ type: 'gap', count: gap })
  return res
})

function lineClass(kind: DiffLine['kind']) {
  if (kind === 'add') return 'bg-primary/8 text-foreground'
  if (kind === 'del') return 'bg-destructive/8 text-foreground'
  return 'text-muted-foreground'
}

function marker(kind: DiffLine['kind']) {
  return kind === 'add' ? '+' : kind === 'del' ? '−' : ' '
}
</script>

<template>
  <div :class="cn('overflow-hidden rounded-lg border border-border/50', props.class)">
    <!-- Header: archivo + estadísticas reales -->
    <div class="flex items-center justify-between gap-2 border-b border-border/40 bg-surface/40 px-3 py-2">
      <span class="truncate font-mono text-[11px] text-muted-foreground">
        {{ filename || 'sin nombre' }}
      </span>
      <div class="flex items-center gap-2 text-[11px]">
        <template v-if="isDirty">
          <span data-testid="diff-added" class="font-semibold text-primary">+{{ stats.added }}</span>
          <span data-testid="diff-removed" class="font-semibold text-destructive">−{{ stats.removed }}</span>
        </template>
        <span v-else data-testid="diff-clean" class="text-muted-foreground">sin cambios</span>
      </div>
    </div>

    <!-- Diff -->
    <div v-if="lines.length === 0" class="px-4 py-6 text-center text-xs text-muted-foreground">
      Archivo vacío en ambos lados.
    </div>
    <div v-else class="max-h-96 overflow-auto font-mono text-[11px] leading-relaxed">
      <div
        v-for="(h, i) in hunks"
        :key="i"
        class="flex"
        :class="h.type === 'hunk' ? lineClass((h as any).line.kind) : 'bg-surface/20 text-muted-foreground/70'"
      >
        <template v-if="h.type === 'gap'">
          <span class="w-full px-3 py-1 text-center text-[10px]">
            ⋯ {{ (h as any).count }} líneas sin cambios ⋯
          </span>
        </template>
        <template v-else>
          <span class="w-10 shrink-0 select-none border-r border-border/20 px-1 text-right text-muted-foreground/50">
            {{ (h as any).line.oldNo ?? '' }}
          </span>
          <span class="w-10 shrink-0 select-none border-r border-border/20 px-1 text-right text-muted-foreground/50">
            {{ (h as any).line.newNo ?? '' }}
          </span>
          <span class="w-5 shrink-0 select-none text-center">{{ marker((h as any).line.kind) }}</span>
          <span class="whitespace-pre-wrap break-all px-2">{{ (h as any).line.value }}</span>
        </template>
      </div>
    </div>
  </div>
</template>
