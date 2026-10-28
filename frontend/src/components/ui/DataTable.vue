<script setup lang="ts">
import { ChevronDown, ChevronUp, Search, X } from '@lucide/vue'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { cn } from '@/lib/utils'
import Skeleton from './Skeleton.vue'

export interface Column<T = any> {
  key: string
  label: string
  sortable?: boolean
  width?: string
  align?: 'left' | 'center' | 'right'
  render?: (item: T) => any
}

interface Props<T = any> {
  columns: Column<T>[]
  items: T[]
  loading?: boolean
  searchable?: boolean
  searchPlaceholder?: string
  pageSize?: number
  emptyTitle?: string
  emptyDescription?: string
  rowClick?: (item: T) => void
  class?: string
  /**
   * Virtual scrolling for large lists. The catalog has 9.922 endpoints and
   * 722 targets; rendering them all costs tens of thousands of DOM nodes.
   * Above `virtualizeOver` rows the table switches to windowing and the
   * pager is disabled (the scrollbar IS the pager).
   */
  virtualizeOver?: number
  rowHeight?: number
  dense?: boolean
  selectable?: boolean
  rowKey?: ((item: T) => string) | string
  emit?: never
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  searchable: false,
  searchPlaceholder: 'Buscar...',
  pageSize: 25,
  emptyTitle: 'Sin datos',
  emptyDescription: '',
  virtualizeOver: 200,
  rowHeight: 36,
  dense: false,
  selectable: false,
})

const selected = defineModel<Set<string>>('selected', { required: false })

const sortKey = ref<string | null>(null)
const sortDir = ref<'asc' | 'desc'>('asc')
const searchQuery = ref('')
const currentPage = ref(1)

function toggleSort(key: string) {
  if (sortKey.value === key) {
    sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortKey.value = key
    sortDir.value = 'asc'
  }
  currentPage.value = 1
}

const filtered = computed(() => {
  let result = Array.isArray(props.items) ? [...props.items] : []
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    result = result.filter((item) =>
      props.columns.some((col) => {
        const val = item[col.key]
        return val != null && String(val).toLowerCase().includes(q)
      }),
    )
  }
  if (sortKey.value) {
    result.sort((a, b) => {
      const aVal = a[sortKey.value!]
      const bVal = b[sortKey.value!]
      if (aVal == null) return 1
      if (bVal == null) return -1
      const cmp = aVal < bVal ? -1 : aVal > bVal ? 1 : 0
      return sortDir.value === 'asc' ? cmp : -cmp
    })
  }
  return result
})

// ── Virtualization ────────────────────────────────────────────────
// Above the threshold we render only the visible window plus a small
// overscan instead of every row. `transform: translateY` positions the
// spacer so the scrollbar height stays truthful.
const shouldVirtualize = computed(() => filtered.value.length > props.virtualizeOver)
const scrollTop = ref(0)
const viewportH = ref(600)
const scrollEl = ref<HTMLElement | null>(null)

const OVERSCAN = 6
const startIndex = computed(() => {
  if (!shouldVirtualize.value) return 0
  return Math.max(0, Math.floor(scrollTop.value / props.rowHeight) - OVERSCAN)
})
const visibleCount = computed(() => {
  if (!shouldVirtualize.value) return filtered.value.length
  return Math.ceil(viewportH.value / props.rowHeight) + OVERSCAN * 2
})
const windowed = computed(() =>
  shouldVirtualize.value ? filtered.value.slice(startIndex.value, startIndex.value + visibleCount.value) : filtered.value,
)
const padTop = computed(() => (shouldVirtualize.value ? startIndex.value * props.rowHeight : 0))
const padBottom = computed(() =>
  shouldVirtualize.value ? Math.max(0, filtered.value.length - visibleCount.value - startIndex.value) * props.rowHeight : 0,
)

function onScroll(e: Event) {
  const el = e.target as HTMLElement
  scrollTop.value = el.scrollTop
  viewportH.value = el.clientHeight || 600
}

function keyOf(item: any, i: number): string {
  if (typeof props.rowKey === 'function') return props.rowKey(item)
  // `row-key="id"` (string) también vale: es como se escribe en un template,
  // donde pasar una función exige :row-key y casi nadie lo hace.
  if (typeof props.rowKey === 'string' && props.rowKey) return String(item?.[props.rowKey] ?? i)
  return String(item?.id ?? i)
}

function toggleRow(item: any, i: number) {
  if (props.rowClick) {
    props.rowClick(item)
    return
  }
  if (!props.selectable) return
  const k = keyOf(item, i)
  const next = new Set(selected.value ?? [])
  if (next.has(k)) next.delete(k)
  else next.add(k)
  selected.value = next
}

function isSelected(item: any, i: number): boolean {
  return Boolean(selected.value?.has(keyOf(item, i)))
}

function toggleAll() {
  if (!props.selectable) return
  const keys = filtered.value.map((it, i) => keyOf(it, i))
  const allOn = keys.every((k) => selected.value?.has(k))
  selected.value = allOn ? new Set() : new Set(keys)
}

const allSelected = computed(() => {
  if (!filtered.value.length || !props.selectable) return false
  return filtered.value.every((it, i) => selected.value?.has(keyOf(it, i)))
})

const totalPages = computed(() => Math.max(1, Math.ceil(filtered.value.length / props.pageSize)))

const paginated = computed(() => {
  if (shouldVirtualize.value) return windowed.value
  const start = (currentPage.value - 1) * props.pageSize
  return filtered.value.slice(start, start + props.pageSize)
})

const skeletonRows = computed(() => Math.min(props.pageSize, 8))

watch(searchQuery, () => {
  currentPage.value = 1
  scrollTop.value = 0
  if (scrollEl.value) scrollEl.value.scrollTop = 0
})

function alignClass(align?: string) {
  if (align === 'center') return 'text-center'
  if (align === 'right') return 'text-right'
  return 'text-left'
}
</script>

<template>
  <div :class="cn('space-y-3', props.class)">
    <!-- Search -->
    <div v-if="searchable" class="relative max-w-xs">
      <Search class="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
      <input
        v-model="searchQuery"
        type="search"
        :placeholder="searchPlaceholder"
        class="h-9 w-full rounded-lg border border-border/60 bg-surface/50 pl-9 pr-8 text-sm text-foreground placeholder:text-muted-foreground/50 focus:border-primary/30 focus:outline-none focus:ring-1 focus:ring-primary/20"
      />
      <button
        v-if="searchQuery"
        type="button"
        @click="searchQuery = ''"
        class="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
      >
        <X class="h-3.5 w-3.5" />
      </button>
    </div>

    <!-- Count + selection summary -->
    <div v-if="!loading && filtered.length" class="flex items-center gap-3 text-xs text-muted-foreground">
      <span>{{ filtered.length }} resultados<template v-if="shouldVirtualize"> · scroll para ver más</template></span>
      <span v-if="selectable && selected?.size" class="text-primary font-semibold">
        {{ selected.size }} seleccionados
      </span>
    </div>

    <!-- Table -->
    <div
      class="overflow-x-auto rounded-xl border border-border/20"
      :class="shouldVirtualize ? 'overflow-y-auto' : ''"
      :ref="(el) => { scrollEl = el as HTMLElement | null }"
      :style="shouldVirtualize ? `max-height: ${rowHeight * 18}px` : undefined"
      @scroll="onScroll"
    >
      <table class="w-full text-xs">
        <thead class="sticky top-0 z-10">
          <tr class="border-b border-border/20 bg-surface/30">
            <th v-if="selectable" class="w-8 px-3 py-2">
              <input
                type="checkbox"
                :checked="allSelected"
                :aria-label="'Seleccionar todo'"
                class="h-3.5 w-3.5 accent-primary cursor-pointer"
                @change="toggleAll"
                @click.stop
              />
            </th>
            <th
              v-for="col in columns"
              :key="col.key"
              @click="col.sortable ? toggleSort(col.key) : undefined"
              :class="cn(
                'px-4 font-semibold text-muted-foreground',
                dense ? 'py-1.5' : 'py-3',
                alignClass(col.align),
                col.sortable ? 'cursor-pointer hover:text-foreground select-none' : '',
              )"
              :style="col.width ? { width: col.width } : undefined"
            >
              <div class="inline-flex items-center gap-1">
                {{ col.label }}
                <span v-if="col.sortable && sortKey === col.key" class="inline-flex">
                  <ChevronUp v-if="sortDir === 'asc'" class="h-3 w-3" />
                  <ChevronDown v-else class="h-3 w-3" />
                </span>
              </div>
            </th>
          </tr>
        </thead>
        <tbody>
          <!-- Loading -->
          <tr v-if="loading">
            <td :colspan="columns.length + (selectable ? 1 : 0)" class="p-4">
              <div class="space-y-2">
                <Skeleton v-for="i in skeletonRows" :key="i" class="h-8 w-full rounded" />
              </div>
            </td>
          </tr>

          <!-- Empty -->
          <tr v-else-if="paginated.length === 0">
            <td :colspan="columns.length + (selectable ? 1 : 0)" class="px-4 py-12 text-center">
              <p class="text-sm text-muted-foreground">{{ emptyTitle }}</p>
              <p v-if="emptyDescription" class="mt-1 text-xs text-muted-foreground/60">{{ emptyDescription }}</p>
            </td>
          </tr>

          <!-- Rows -->
          <template v-else>
            <tr v-if="padTop > 0" :style="{ height: `${padTop}px` }" aria-hidden="true">
              <td :colspan="columns.length + (selectable ? 1 : 0)" class="p-0" />
            </tr>
            <tr
              v-for="(item, i) in paginated"
              :key="shouldVirtualize ? keyOf(item, startIndex + i) : i"
              @click="toggleRow(item, shouldVirtualize ? startIndex + i : i)"
              :class="cn(
                'border-t border-border/10 transition-colors',
                dense ? '' : '',
                (selectable || rowClick) ? 'cursor-pointer hover:bg-surface/30' : '',
                selectable && isSelected(item, shouldVirtualize ? startIndex + i : i) ? 'bg-primary/5' : '',
              )"
              :style="dense ? {} : undefined"
            >
              <td v-if="selectable" class="px-3 py-2">
                <input
                  type="checkbox"
                  :checked="isSelected(item, shouldVirtualize ? startIndex + i : i)"
                  :aria-label="`Seleccionar fila ${i + 1}`"
                  class="h-3.5 w-3.5 accent-primary cursor-pointer"
                  @change="toggleRow(item, shouldVirtualize ? startIndex + i : i)"
                  @click.stop
                />
              </td>
              <td
                v-for="col in columns"
                :key="col.key"
                :class="cn('text-foreground', dense ? 'px-3 py-1.5' : 'px-4 py-3', alignClass(col.align))"
              >
                <slot :name="`cell-${col.key}`" :item="item" :value="item[col.key]">
                  <span v-if="col.render">{{ col.render(item) }}</span>
                  <span v-else>{{ item[col.key] ?? '—' }}</span>
                </slot>
              </td>
            </tr>
            <tr v-if="padBottom > 0" :style="{ height: `${padBottom}px` }" aria-hidden="true">
              <td :colspan="columns.length + (selectable ? 1 : 0)" class="p-0" />
            </tr>
          </template>
        </tbody>
      </table>
    </div>

    <!-- Pagination (disabled while virtualizing: the scrollbar IS the pager) -->
    <div
      v-if="!loading && totalPages > 1 && !shouldVirtualize"
      class="flex items-center justify-between text-xs text-muted-foreground"
    >
      <span>{{ filtered.length }} resultados · Pág {{ currentPage }}/{{ totalPages }}</span>
      <div class="flex items-center gap-1">
        <button
          :disabled="currentPage <= 1"
          @click="currentPage = Math.max(1, currentPage - 1)"
          class="rounded-lg px-3 py-1.5 hover:bg-surface/50 hover:text-foreground transition-colors disabled:opacity-30"
        >Anterior</button>
        <button
          v-for="p in totalPages"
          :key="p"
          @click="currentPage = p"
          :class="[
            'rounded-lg px-2.5 py-1 transition-colors',
            p === currentPage ? 'bg-primary/10 text-primary font-semibold' : 'hover:bg-surface/30 hover:text-foreground',
          ]"
          class="hidden sm:inline-block"
        >{{ p }}</button>
        <button
          :disabled="currentPage >= totalPages"
          @click="currentPage = Math.min(totalPages, currentPage + 1)"
          class="rounded-lg px-3 py-1.5 hover:bg-surface/50 hover:text-foreground transition-colors disabled:opacity-30"
        >Siguiente</button>
      </div>
    </div>
  </div>
</template>
