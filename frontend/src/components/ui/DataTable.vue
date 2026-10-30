<script setup lang="ts">
import { ChevronDown, ChevronUp, Search, X } from '@lucide/vue'
import { computed, ref } from 'vue'
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
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  searchable: false,
  searchPlaceholder: 'Buscar...',
  pageSize: 25,
  emptyTitle: 'Sin datos',
  emptyDescription: '',
})

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

const totalPages = computed(() => Math.max(1, Math.ceil(filtered.value.length / props.pageSize)))

const paginated = computed(() => {
  const start = (currentPage.value - 1) * props.pageSize
  return filtered.value.slice(start, start + props.pageSize)
})

const skeletonRows = computed(() => Math.min(props.pageSize, 8))

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

    <!-- Table -->
    <div class="overflow-x-auto rounded-xl border border-border/20">
      <table class="w-full text-xs">
        <thead>
          <tr class="border-b border-border/20 bg-surface/30">
            <th
              v-for="col in columns"
              :key="col.key"
              @click="col.sortable ? toggleSort(col.key) : undefined"
              :class="cn(
                'px-4 py-3 font-semibold text-muted-foreground',
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
            <td :colspan="columns.length" class="p-4">
              <div class="space-y-2">
                <Skeleton v-for="i in skeletonRows" :key="i" class="h-8 w-full rounded" />
              </div>
            </td>
          </tr>

          <!-- Empty -->
          <tr v-else-if="paginated.length === 0">
            <td :colspan="columns.length" class="px-4 py-12 text-center">
              <p class="text-sm text-muted-foreground">{{ emptyTitle }}</p>
              <p v-if="emptyDescription" class="mt-1 text-xs text-muted-foreground/60">{{ emptyDescription }}</p>
            </td>
          </tr>

          <!-- Rows -->
          <template v-else>
            <tr
              v-for="(item, i) in paginated"
              :key="i"
              @click="rowClick?.(item)"
              :class="cn(
                'border-t border-border/10 transition-colors',
                rowClick ? 'cursor-pointer hover:bg-surface/30' : '',
              )"
            >
              <td
                v-for="col in columns"
                :key="col.key"
                :class="cn('px-4 py-3 text-foreground', alignClass(col.align))"
              >
                <slot :name="`cell-${col.key}`" :item="item" :value="item[col.key]">
                  <span v-if="col.render">{{ col.render(item) }}</span>
                  <span v-else>{{ item[col.key] ?? '—' }}</span>
                </slot>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>

    <!-- Pagination -->
    <div
      v-if="!loading && totalPages > 1"
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
