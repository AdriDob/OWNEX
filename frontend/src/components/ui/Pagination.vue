<script setup lang="ts">
import { computed, type PropType } from 'vue'
import { cn } from '@/lib/utils'

interface Props {
  page: number
  totalPages: number
  siblingCount?: number
  class?: string
}
const props = withDefaults(defineProps<Props>(), {
  siblingCount: 1,
  class: '',
})
const maxPages = computed(() => {
  const { page, totalPages, siblingCount } = toRefs(props)
  if (totalPages.value <= 7) return totalPages.value
  return Math.min(totalPages.value, 7)
})
</script>

<template>
  <nav class="flex items-center gap-2" v-if="totalPages > 1">
    <button
      @click="page > 1 ? prevPage() : null"
      :disabled="page <= 1"
      class="rounded-lg border border-border/20 px-3 py-1.5 text-[10px] font-mono transition-colors hover:bg-surface/30"
    >
      <span aria-hidden="true">‹</span>
      <span class="sr-only">Página anterior</span>
    </button>

    <span v-if="totalPages <= maxPages" class="text-[10px] font-mono">
      <span v-for="n in totalPages" :key="n" class="mx-1 {{ n === page ? 'font-medium text-foreground' : 'text-muted-foreground' }}">{{ n }}</span>
    </span>

    <template v-else>
      <!-- Pages around current -->
      <PageNumber v-for="n in pageRange" :key="n" :page="n" :is-active="n === page" />
    </template>

    <button
      @click="page < totalPages ? nextPage() : null"
      :disabled="page >= totalPages"
      class="rounded-lg border border-border/20 px-3 py-1.5 text-[10px] font-mono transition-colors hover:bg-surface/30"
    >
      <span aria-hidden="true">›</span>
      <span class="sr-only">Siguiente página</span>
    </button>
  </nav>
</template>

<script>
const PAGE_NUMBERS_VISIBLE = 7

const pageNums = computed(() => {
  const total = props.totalPages
  const current = props.page
  if (total <= PAGE_NUMBERS_VISIBLE) return Array.from({ length: total }, (_, i) => i + 1)

  const maxLeft = Math.max(1, current - Math.ceil(PAGE_NUMBERS_VISIBLE / 2))
  const maxRight = Math.min(total - current, Math.floor(PAGE_NUMBERS_VISIBLE / 2))

  let start = 1
  let end = PAGE_NUMBERS_VISIBLE

  if (current <= PAGE_NUMBERS_VISIBLE - 1) {
    start = 1
    end = PAGE_NUMBERS_VISIBLE
  } else if (current >= total - PAGE_NUMBERS_VISIBLE + 2) {
    start = total - PAGE_NUMBERS_VISIBLE + 1
    end = total
  } else {
    start = current - Math.floor(PAGE_NUMBERS_VISIBLE / 2)
    end = current + Math.ceil(PAGE_NUMBERS_VISIBLE / 2)
  }

  return Array.from({ length: end - start + 1 }, (_, i) => start + i)
})

const pageRange = computed(() => pageNums.value)
</script>

<style scoped>
/* Pagination uses Tailwind built-in transitions */
</style>