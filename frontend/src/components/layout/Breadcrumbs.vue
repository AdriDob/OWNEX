<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ChevronRight, Home } from '@lucide/vue'

const route = useRoute()
const router = useRouter()

const breadcrumbs = computed(() => {
  const path = route.path
  const metaTitle = (route.meta?.title as string) || ''
  const segments = path.split('/').filter(Boolean)

  if (segments.length === 0) return [{ label: 'Panel Económico' }]

  const crumbs: { label: string; path?: string }[] = [{ label: 'Inicio', path: '/' }]
  let accumulated = ''

  for (let i = 0; i < segments.length; i++) {
    accumulated += '/' + segments[i]
    const seg = segments[i]

    // Skip numeric IDs in breadcrumbs — show meaningful parent instead
    if (/^\d+$/.test(seg) && i > 0) continue

    const label = seg
      .replace(/-/g, ' ')
      .replace(/\b\w/g, (c: string) => c.toUpperCase())

    if (i === segments.length - 1) {
      crumbs.push({ label: metaTitle || label })
    } else {
      crumbs.push({ label, path: accumulated })
    }
  }

  return crumbs
})
</script>

<template>
  <nav v-if="breadcrumbs.length > 1" class="flex items-center gap-1 text-[10px] text-muted-foreground/60 mb-4 animate-in">
    <button
      v-for="(crumb, i) in breadcrumbs"
      :key="i"
      @click="crumb.path ? router.push(crumb.path) : undefined"
      :class="[
        'flex items-center gap-1',
        i === breadcrumbs.length - 1 ? 'text-foreground/80 font-medium' : 'hover:text-foreground/60 transition-colors',
        crumb.path ? 'cursor-pointer' : 'cursor-default',
      ]"
    >
      <Home v-if="i === 0" class="h-3 w-3" />
      <ChevronRight v-else class="h-2.5 w-2.5 text-muted-foreground/30" />
      <span>{{ crumb.label }}</span>
    </button>
  </nav>
</template>

<style scoped>
.animate-in {
  animation: fadeIn 0.2s ease-out;
}
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}
</style>
