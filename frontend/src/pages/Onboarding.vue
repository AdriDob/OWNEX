<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { CheckCircle, ChevronRight, Crown, Shield, Code, Database, Globe, CreditCard, DollarSign } from '@lucide/vue'
import { api } from '@/lib/api'
import { useToast } from '@/composables/useToast'

const router = useRouter()
const { toast } = useToast()

const step = ref(1)
const totalSteps = 3

const profile = ref({
  username: '',
  email: '',
  country: 'Argentina',
  preferredPayment: 'crypto', // crypto, bank, paypal
  cryptoAddress: '',
  bankAccount: '',
  skills: [] as string[],
})

const selectedCategories = ref<string[]>([])

const skills = [
  'JavaScript', 'Python', 'React', 'Vue', 'Node.js', 'TypeScript',
  'Security', 'Web3', 'Testing', 'Docker', 'Git', 'Linux',
]

const categories = [
  { id: 'dev-bounty', name: 'Dev Bounty', icon: Code, color: '#0070d1' },
  { id: 'bug-bounty', name: 'Bug Bounty', icon: Shield, color: '#00ff88' },
  { id: 'data-entry', name: 'Entrada de Datos', icon: Database, color: '#ffd700' },
]

function nextStep() {
  if (step.value < totalSteps) {
    step.value++
  }
}

function prevStep() {
  if (step.value > 1) {
    step.value--
  }
}

function toggleSkill(skill: string) {
  const index = profile.value.skills.indexOf(skill)
  if (index > -1) {
    profile.value.skills.splice(index, 1)
  } else {
    profile.value.skills.push(skill)
  }
}

function toggleCategory(categoryId: string) {
  const index = selectedCategories.value.indexOf(categoryId)
  if (index > -1) {
    selectedCategories.value.splice(index, 1)
  } else {
    selectedCategories.value.push(categoryId)
  }
}

async function completeOnboarding() {
  try {
    // Save profile
    await api.post('/api/user/profile', profile.value)
    
    // Save selected categories
    await api.post('/api/user/categories', { categories: selectedCategories.value })
    
    toast({
      title: 'Perfil Creado',
      description: '¡Bienvenido a OWNEX! Tu perfil está listo.',
    })
    
    router.push('/ps5-hub')
  } catch (e: any) {
    toast({
      title: 'Error',
      description: e?.message || 'Error al crear perfil',
      variant: 'destructive',
    })
  }
}
</script>

<template>
  <div class="min-h-screen bg-gradient-to-br from-[#0a0a0f] via-[#0d1117] to-[#161b22] text-white flex items-center justify-center p-6">
    <div class="max-w-2xl w-full">
      <!-- Progress Bar -->
      <div class="mb-8">
        <div class="flex justify-between text-sm mb-2">
          <span class="text-gray-400">Paso {{ step }} de {{ totalSteps }}</span>
          <span class="text-[#0070d1]">{{ Math.round((step / totalSteps) * 100) }}%</span>
        </div>
        <div class="h-2 bg-[#0d1117] rounded-full overflow-hidden">
          <div 
            class="h-full bg-gradient-to-r from-[#0070d1] to-[#00aaff] transition-all duration-500"
            :style="{ width: `${(step / totalSteps) * 100}%` }"
          />
        </div>
      </div>

      <!-- Step 1: Basic Info -->
      <div v-if="step === 1" class="bg-[#0d1117]/80 border border-[#0070d1]/30 rounded-2xl p-8">
        <div class="flex items-center gap-4 mb-6">
          <div class="w-12 h-12 rounded-full bg-[#0070d1]/20 flex items-center justify-center">
            <Crown class="w-6 h-6 text-[#0070d1]" />
          </div>
          <div>
            <h2 class="text-2xl font-bold">Crea tu Perfil</h2>
            <p class="text-gray-400">Sin entrevista, sin experiencia, solo perfil open source</p>
          </div>
        </div>

        <div class="space-y-6">
          <div>
            <label class="block text-sm text-gray-400 mb-2">Nombre de Usuario</label>
            <input
              v-model="profile.username"
              type="text"
              class="w-full bg-[#0a0a0f] border border-[#0070d1]/30 rounded-lg px-4 py-3 text-white focus:border-[#0070d1] focus:outline-none"
              placeholder="Tu nombre de usuario"
            />
          </div>

          <div>
            <label class="block text-sm text-gray-400 mb-2">Email</label>
            <input
              v-model="profile.email"
              type="email"
              class="w-full bg-[#0a0a0f] border border-[#0070d1]/30 rounded-lg px-4 py-3 text-white focus:border-[#0070d1] focus:outline-none"
              placeholder="tu@email.com"
            />
          </div>

          <div>
            <label class="block text-sm text-gray-400 mb-2">País</label>
            <select
              v-model="profile.country"
              class="w-full bg-[#0a0a0f] border border-[#0070d1]/30 rounded-lg px-4 py-3 text-white focus:border-[#0070d1] focus:outline-none"
            >
              <option value="Argentina">Argentina</option>
              <option value="Chile">Chile</option>
              <option value="México">México</option>
              <option value="Colombia">Colombia</option>
              <option value="España">España</option>
              <option value="Otro">Otro</option>
            </select>
          </div>
        </div>

        <div class="flex justify-between mt-8">
          <button
            disabled
            class="px-6 py-3 rounded-lg font-bold bg-[#0d1117] text-gray-400 cursor-not-allowed"
          >
            Atrás
          </button>
          <button
            @click="nextStep"
            class="px-6 py-3 rounded-lg font-bold bg-[#0070d1] hover:bg-[#0088ff] transition-colors flex items-center gap-2"
          >
            Siguiente
            <ChevronRight class="w-5 h-5" />
          </button>
        </div>
      </div>

      <!-- Step 2: Skills -->
      <div v-if="step === 2" class="bg-[#0d1117]/80 border border-[#0070d1]/30 rounded-2xl p-8">
        <div class="flex items-center gap-4 mb-6">
          <div class="w-12 h-12 rounded-full bg-[#0070d1]/20 flex items-center justify-center">
            <Code class="w-6 h-6 text-[#0070d1]" />
          </div>
          <div>
            <h2 class="text-2xl font-bold">Selecciona tus Skills</h2>
            <p class="text-gray-400">Skills técnicos para trabajos remunerados</p>
          </div>
        </div>

        <div class="grid grid-cols-3 md:grid-cols-4 gap-3 mb-8">
          <button
            v-for="skill in skills"
            :key="skill"
            @click="toggleSkill(skill)"
            :class="[
              'px-4 py-3 rounded-lg font-medium transition-all',
              profile.skills.includes(skill)
                ? 'bg-[#0070d1] text-white'
                : 'bg-[#0a0a0f] border border-[#0070d1]/30 text-gray-400 hover:border-[#0070d1]'
            ]"
          >
            {{ skill }}
          </button>
        </div>

        <div class="flex justify-between">
          <button
            @click="prevStep"
            class="px-6 py-3 rounded-lg font-bold bg-[#0d1117] hover:bg-[#1a1f2e] transition-colors"
          >
            Atrás
          </button>
          <button
            @click="nextStep"
            class="px-6 py-3 rounded-lg font-bold bg-[#0070d1] hover:bg-[#0088ff] transition-colors flex items-center gap-2"
          >
            Siguiente
            <ChevronRight class="w-5 h-5" />
          </button>
        </div>
      </div>

      <!-- Step 3: Categories & Payment -->
      <div v-if="step === 3" class="bg-[#0d1117]/80 border border-[#0070d1]/30 rounded-2xl p-8">
        <div class="flex items-center gap-4 mb-6">
          <div class="w-12 h-12 rounded-full bg-[#0070d1]/20 flex items-center justify-center">
            <Globe class="w-6 h-6 text-[#0070d1]" />
          </div>
          <div>
            <h2 class="text-2xl font-bold">Categorías y Pagos</h2>
            <p class="text-gray-400">Selecciona cómo quieres recibir pagos</p>
          </div>
        </div>

        <div class="mb-8">
          <h3 class="text-lg font-bold mb-4">Categorías de Trabajo</h3>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <button
              v-for="cat in categories"
              :key="cat.id"
              @click="toggleCategory(cat.id)"
              :class="[
                'p-4 rounded-xl border-2 transition-all',
                selectedCategories.includes(cat.id)
                  ? 'border-[#0070d1] bg-[#0070d1]/10'
                  : 'border-[#0070d1]/30 bg-[#0d1117] hover:border-[#0070d1]/50'
              ]"
            >
              <component :is="cat.icon" class="w-6 h-6 mb-2" :style="{ color: cat.color }" />
              <p class="font-bold">{{ cat.name }}</p>
            </button>
          </div>
        </div>

        <div class="mb-8">
          <h3 class="text-lg font-bold mb-4">Método de Pago</h3>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <button
              @click="profile.preferredPayment = 'crypto'"
              :class="[
                'p-4 rounded-xl border-2 transition-all',
                profile.preferredPayment === 'crypto'
                  ? 'border-[#0070d1] bg-[#0070d1]/10'
                  : 'border-[#0070d1]/30 bg-[#0d1117] hover:border-[#0070d1]/50'
              ]"
            >
              <DollarSign class="w-6 h-6 mb-2 text-[#0070d1]" />
              <p class="font-bold">Crypto</p>
              <p class="text-sm text-gray-400">USDT, BTC, ETH</p>
            </button>
            <button
              @click="profile.preferredPayment = 'bank'"
              :class="[
                'p-4 rounded-xl border-2 transition-all',
                profile.preferredPayment === 'bank'
                  ? 'border-[#0070d1] bg-[#0070d1]/10'
                  : 'border-[#0070d1]/30 bg-[#0d1117] hover:border-[#0070d1]/50'
              ]"
            >
              <CreditCard class="w-6 h-6 mb-2 text-[#0070d1]" />
              <p class="font-bold">Banco</p>
              <p class="text-sm text-gray-400">Transferencia local</p>
            </button>
            <button
              @click="profile.preferredPayment = 'paypal'"
              :class="[
                'p-4 rounded-xl border-2 transition-all',
                profile.preferredPayment === 'paypal'
                  ? 'border-[#0070d1] bg-[#0070d1]/10'
                  : 'border-[#0070d1]/30 bg-[#0d1117] hover:border-[#0070d1]/50'
              ]"
            >
              <Globe class="w-6 h-6 mb-2 text-[#0070d1]" />
              <p class="font-bold">PayPal</p>
              <p class="text-sm text-gray-400">Internacional</p>
            </button>
          </div>
        </div>

        <div v-if="profile.preferredPayment === 'crypto'" class="mb-8">
          <label class="block text-sm text-gray-400 mb-2">Dirección Crypto</label>
          <input
            v-model="profile.cryptoAddress"
            type="text"
            class="w-full bg-[#0a0a0f] border border-[#0070d1]/30 rounded-lg px-4 py-3 text-white focus:border-[#0070d1] focus:outline-none"
            placeholder="0x..."
          />
        </div>

        <div class="flex justify-between">
          <button
            @click="prevStep"
            class="px-6 py-3 rounded-lg font-bold bg-[#0d1117] hover:bg-[#1a1f2e] transition-colors"
          >
            Atrás
          </button>
          <button
            @click="completeOnboarding"
            class="px-6 py-3 rounded-lg font-bold bg-gradient-to-r from-[#0070d1] to-[#00aaff] hover:from-[#0088ff] hover:to-[#00bbff] transition-all flex items-center gap-2"
          >
            <CheckCircle class="w-5 h-5" />
            Comenzar
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
