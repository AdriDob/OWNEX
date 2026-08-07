<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Sun, Moon, Sparkles } from '@lucide/vue'
import { useThemeEngine, type ThemeMode } from '@/composables/useThemeEngine'

const { themeMode, setThemeMode } = useThemeEngine()
const cycle = ref(['auto', 'light', 'dark'])
const labels: Record<ThemeMode, string> = { auto: 'Auto (sigue al sistema)', light: 'Claro', dark: 'Oscuro' }

function next() {
  const idx = cycle.value.indexOf(themeMode.value as ThemeMode)
  const nextMode = cycle.value[(idx + 1) % cycle.value.length] as ThemeMode
  setThemeMode(nextMode)
}

onMounted(() => { /* engine init handles apply */ })
</script>

<template>
  <button
    class="theme-toggle flex h-5 w-5 items-center justify-center rounded text-muted-foreground/50 hover:bg-orion-bg-elevated hover:text-foreground transition-colors"
    :title="labels[themeMode as ThemeMode] || 'Auto'"
    @click="cycle()"
  >
    <Sun v-if="themeMode === 'light'" class="h-3 w-3" />
    <Moon v-else-if="themeMode === 'dark'" class="h-3 w-3" />
    <Sparkles v-else class="h-3 w-3" />
  </button>
</template>