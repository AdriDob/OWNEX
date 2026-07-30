<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Play, Settings, DollarSign, Shield, Code, Database, TrendingUp, Zap, ChevronRight, Crown } from '@lucide/vue'

const router = useRouter()

interface Category {
  id: string
  name: string
  icon: any
  color: string
  description: string
  count: number
  potential: number
}

const categories = ref<Category[]>([
  {
    id: 'dev-bounty',
    name: 'Dev Bounty',
    icon: Code,
    color: '#0070d1',
    description: 'Open source, contribuciones públicas',
    count: 0,
    potential: 0,
  },
  {
    id: 'bug-bounty',
    name: 'Bug Bounty',
    icon: Shield,
    color: '#00ff88',
    description: 'Vulnerabilidades, seguridad pública',
    count: 0,
    potential: 0,
  },
  {
    id: 'data-entry',
    name: 'Entrada de Datos',
    icon: Database,
    color: '#ffd700',
    description: 'IA, etiquetado, tareas simples',
    count: 0,
    potential: 0,
  },
])

const selectedCategory = ref<string | null>(null)
const userStats = ref({
  level: 1,
  xp: 0,
  completed: 0,
  earnings: 0,
})

onMounted(async () => {
  // Load real data
  try {
    const tasksRes = await fetch('/api/task-hub/dashboard')
    const tasksData = await tasksRes.json()
    if (tasksData.success) {
      userStats.value.completed = tasksData.plan?.total_tasks || 0
      userStats.value.earnings = tasksData.plan?.total_potential_reward || 0
    }
  } catch (e) {
    console.error('Failed to load stats')
  }
})

function selectCategory(categoryId: string) {
  selectedCategory.value = categoryId
  router.push(`/work/${categoryId}`)
}

function openSettings() {
  router.push('/settings')
}

function openPatrimony() {
  router.push('/capital')
}

function openMultiplication() {
  router.push('/trading')
}
</script>

<template>
  <div class="min-h-screen bg-gradient-to-br from-[#0a0a0f] via-[#0d1117] to-[#161b22] text-white">
    <!-- Header - PS5 Style -->
    <header class="fixed top-0 left-0 right-0 z-50 bg-[#0a0a0f]/90 backdrop-blur-xl border-b border-[#0070d1]/30">
      <div class="container mx-auto px-6 py-4 flex items-center justify-between">
        <div class="flex items-center gap-4">
          <div class="w-12 h-12 rounded-full bg-gradient-to-br from-[#0070d1] to-[#00aaff] flex items-center justify-center">
            <Crown class="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 class="text-2xl font-bold tracking-wider">OWNEX</h1>
            <p class="text-xs text-[#0070d1]">Nivel {{ userStats.level }} • {{ userStats.completed }} Completados</p>
          </div>
        </div>

        <div class="flex items-center gap-6">
          <div class="text-right">
            <p class="text-sm text-gray-400">Ganancias Totales</p>
            <p class="text-xl font-bold text-[#00ff88]">${{ userStats.earnings.toFixed(2) }}</p>
          </div>
          <button
            @click="openPatrimony"
            class="p-3 rounded-lg bg-[#0d1117] border border-[#0070d1]/30 hover:border-[#0070d1] transition-colors"
          >
            <DollarSign class="w-5 h-5 text-[#0070d1]" />
          </button>
          <button
            @click="openMultiplication"
            class="p-3 rounded-lg bg-[#0d1117] border border-[#0070d1]/30 hover:border-[#0070d1] transition-colors"
          >
            <TrendingUp class="w-5 h-5 text-[#0070d1]" />
          </button>
          <button
            @click="openSettings"
            class="p-3 rounded-lg bg-[#0d1117] border border-[#0070d1]/30 hover:border-[#0070d1] transition-colors"
          >
            <Settings class="w-5 h-5 text-[#0070d1]" />
          </button>
        </div>
      </div>
    </header>

    <!-- Main Content - Categories Grid -->
    <main class="container mx-auto px-6 pt-32 pb-12">
      <div class="text-center mb-12">
        <h2 class="text-4xl font-bold mb-4">Selecciona tu Categoría</h2>
        <p class="text-gray-400 text-lg">Trabajos públicos remunerados por aporte • Sin entrevista • Solo perfil</p>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-6xl mx-auto">
        <div
          v-for="category in categories"
          :key="category.id"
          @click="selectCategory(category.id)"
          class="group relative bg-gradient-to-br from-[#0d1117] to-[#161b22] border-2 border-transparent hover:border-[#0070d1] rounded-2xl p-8 cursor-pointer transition-all duration-300 hover:scale-105 hover:shadow-2xl hover:shadow-[#0070d1]/20"
        >
          <div class="absolute top-4 right-4 w-12 h-12 rounded-full opacity-20 group-hover:opacity-100 transition-opacity" :style="{ backgroundColor: category.color }" />
          
          <div class="relative z-10">
            <div class="w-20 h-20 rounded-2xl flex items-center justify-center mb-6" :style="{ backgroundColor: category.color + '20', border: `2px solid ${category.color}` }">
              <component :is="category.icon" class="w-10 h-10" :style="{ color: category.color }" />
            </div>

            <h3 class="text-2xl font-bold mb-2">{{ category.name }}</h3>
            <p class="text-gray-400 mb-6">{{ category.description }}</p>

            <div class="space-y-2 mb-6">
              <div class="flex justify-between text-sm">
                <span class="text-gray-400">Disponibles</span>
                <span class="font-bold">{{ category.count }}</span>
              </div>
              <div class="flex justify-between text-sm">
                <span class="text-gray-400">Potencial</span>
                <span class="font-bold text-[#00ff88]">${{ category.potential }}</span>
              </div>
            </div>

            <button class="w-full py-3 rounded-lg font-bold transition-all group-hover:opacity-100 opacity-80" :style="{ backgroundColor: category.color, color: '#000' }">
              <div class="flex items-center justify-center gap-2">
                <Play class="w-5 h-5" />
                Iniciar
                <ChevronRight class="w-5 h-5" />
              </div>
            </button>
          </div>
        </div>
      </div>

      <!-- Quick Stats - Jarvis Style -->
      <div class="mt-16 max-w-4xl mx-auto">
        <div class="bg-[#0d1117]/50 border border-[#0070d1]/30 rounded-2xl p-8">
          <h3 class="text-xl font-bold mb-6 flex items-center gap-2">
            <Zap class="w-5 h-5 text-[#0070d1]" />
            Estado del Sistema
          </h3>
          <div class="grid grid-cols-2 md:grid-cols-4 gap-6">
            <div class="text-center">
              <p class="text-3xl font-bold text-[#0070d1]">{{ userStats.completed }}</p>
              <p class="text-sm text-gray-400">Completados</p>
            </div>
            <div class="text-center">
              <p class="text-3xl font-bold text-[#00ff88]">${{ userStats.earnings.toFixed(2) }}</p>
              <p class="text-sm text-gray-400">Ganancias</p>
            </div>
            <div class="text-center">
              <p class="text-3xl font-bold text-[#ff00aa]">3</p>
              <p class="text-sm text-gray-400">Categorías</p>
            </div>
            <div class="text-center">
              <p class="text-3xl font-bold text-[#00aaff]">Nvl {{ userStats.level }}</p>
              <p class="text-sm text-gray-400">Nivel</p>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>
