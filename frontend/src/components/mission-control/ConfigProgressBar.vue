<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { getConfigProgress } from '@/services/controlPanel'
import type { ConfigProgressResult, ConfigCheck } from '@/services/controlPanel'

const progress = ref<ConfigProgressResult | null>(null)
const loading = ref(true)
const expandedCategory = ref<string | null>(null)

async function fetchProgress() {
  try {
    progress.value = await getConfigProgress()
  } catch (e) {
    console.error('Failed to fetch config progress:', e)
  } finally {
    loading.value = false
  }
}

const getCategoryLabel = (cat: string) => {
  const labels: Record<string, string> = {
    api_keys: '🔑 API Keys',
    profile: '👤 Perfil GitHub',
    sync: '🔄 Sync & VPN',
    payout: '💰 Payout & Cobro',
    goals: '🎯 Metas & Objetivos',
  }
  return labels[cat] || cat
}

const getCategoryColor = (cat: string) => {
  const colors: Record<string, string> = {
    api_keys: 'bg-blue-600',
    profile: 'bg-purple-600',
    sync: 'bg-green-600',
    payout: 'bg-amber-600',
    goals: 'bg-slate-600',
  }
  return colors[cat] || 'bg-gray-600'
}

onMounted(() => {
  fetchProgress()
})
</script>

<template>
  <div class="w-full">
    <!-- Global Progress Bar -->
    <div class="mb-4">
      <div class="flex justify-between text-sm mb-1">
        <span class="font-medium text-white">Progreso configuración OWNEX</span>
        <span class="font-bold text-white">{{ progress?.progress_pct || 0 }}%</span>
      </div>
      <div class="h-3 bg-gray-800 rounded-full overflow-hidden">
        <div
          v-if="progress"
          :class="[
            'h-full rounded-full transition-all duration-500 ease-out',
            progress.progress_pct < 30 ? 'bg-slate-500' : progress.progress_pct < 60 ? 'bg-amber-500' : progress.progress_pct < 85 ? 'bg-blue-500' : 'bg-green-500'
          ]"
          :style="{ width: progress.progress_pct + '%' }"
        ></div>
      </div>
      <p v-if="progress" class="text-xs text-gray-400 mt-1 text-right">
        {{ progress.done }} / {{ progress.total }} checks completados
      </p>
    </div>

    <!-- Categories Accordion -->
    <div v-if="progress" class="space-y-3">
      <div
        v-for="(checks, cat) in progress.categories"
        :key="cat"
        class="bg-gray-900/50 border border-gray-700 rounded-lg overflow-hidden"
      >
        <!-- Category Header -->
        <button
          @click="expandedCategory = expandedCategory === cat ? null : cat"
          class="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-800/50 transition-colors"
        >
          <div class="flex items-center gap-3">
            <span :class="['w-2 h-2 rounded-full', getCategoryColor(cat)]"></span>
            <span class="font-medium text-white capitalize">{{ getCategoryLabel(cat) }}</span>
            <span class="text-xs text-gray-400">
              {{ checks.filter(c => c.done || (typeof c.done === 'boolean' && c.done)).length }} / {{ checks.length }}
            </span>
          </div>
          <span class="text-sm font-medium text-gray-400">
            {{ expandedCategory === cat ? '▲' : '▼' }}
          </span>
        </button>

        <!-- Category Checks -->
        <div v-show="expandedCategory === cat" class="px-4 pb-3 border-t border-gray-800 animate-slide-down">
          <div class="space-y-2 mt-3">
            <div
              v-for="check in checks"
              :key="check.id"
              class="flex items-center gap-3 p-3 bg-gray-800/50 rounded-lg hover:bg-gray-700/50 transition-colors"
            >
              <div class="flex-shrink-0 w-5 h-5 rounded border-2 flex items-center justify-center"
                   :class="[
                     'border-gray-600',
                     typeof check.done === 'boolean' && check.done ? 'bg-green-500 border-green-500' : 'bg-transparent',
                     typeof check.done === 'number' && check.done > 0 ? 'bg-blue-500 border-blue-500' : 'bg-transparent'
                   ]">
                <svg v-if="typeof check.done === 'boolean' && check.done" class="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"></path>
                </svg>
                <span v-else-if="typeof check.done === 'number' && check.done > 0" class="text-xs font-bold text-white">{{ check.done }}/{{ check.total || 1 }}</span>
              </div>
              <div class="flex-1 min-w-0">
                <p class="text-white truncate">{{ check.name }}</p>
                <p v-if="check.total && check.total > 1" class="text-xs text-gray-400">
                  {{ check.done }} de {{ check.total }} completados
                </p>
              </div>
              <span :class="[
                'text-xs px-2 py-0.5 rounded',
                check.cat === 'api_keys' ? 'bg-blue-900/50 text-blue-300' :
                check.cat === 'profile' ? 'bg-purple-900/50 text-purple-300' :
                check.cat === 'sync' ? 'bg-green-900/50 text-green-300' :
                check.cat === 'payout' ? 'bg-amber-900/50 text-amber-300' :
                check.cat === 'goals' ? 'bg-zinc-800/60 text-zinc-300' :
                'bg-gray-700 text-gray-300'
              ]">
                {{ check.cat }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-else-if="!loading" class="text-center py-8 text-gray-500">
      No se pudo cargar el progreso
    </div>

    <div v-else class="flex justify-center py-8">
      <svg class="animate-spin h-6 w-6 text-blue-500" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
      </svg>
    </div>
  </div>
</template>

<style scoped>
.animate-slide-down {
  animation: slideDown 0.2s ease-out;
}
@keyframes slideDown {
  from { opacity: 0; transform: translateY(-10px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>