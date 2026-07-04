<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import {
  Eye, EyeOff, LogIn, UserPlus, Loader2, AlertCircle,
  Target, Shield, Zap,
} from '@lucide/vue'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const isRegister = ref(false)
const email = ref('')
const password = ref('')
const displayName = ref('')
const showPassword = ref(false)
const submitting = ref(false)
const localError = ref('')

function getSafeRedirect(value?: string | null): string {
  if (!value || typeof value !== 'string') return '/'
  if (!value.startsWith('/')) return '/'
  if (value.startsWith('//')) return '/'
  if (value.includes('://')) return '/'
  return value
}

async function handleSubmit() {
  localError.value = ''
  if (!email.value.trim() || !password.value) {
    localError.value = 'Completá todos los campos'
    return
  }
  submitting.value = true
  try {
    if (isRegister.value) {
      await auth.register(email.value, password.value, displayName.value || undefined)
    } else {
      await auth.loginWithCredentials(email.value, password.value)
    }
    const redirect = getSafeRedirect(route.query.redirect as string | undefined)
    router.push(redirect)
  } catch (e: any) {
    localError.value = e?.message || 'Error de autenticación'
  } finally {
    submitting.value = false
  }
}

function toggleMode() {
  isRegister.value = !isRegister.value
  localError.value = ''
}

onMounted(async () => {
  if (auth.isAuthenticated) {
    router.push('/')
  }
})
</script>

<template>
  <div class="flex min-h-screen w-full items-center justify-center bg-gradient-to-br from-[#0a0b14] via-[#0e0f1a] to-[#11131f] p-4">
    <!-- Decorative grid -->
    <div class="pointer-events-none fixed inset-0 bg-[linear-gradient(rgba(124,58,237,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(124,58,237,0.03)_1px,transparent_1px)] bg-[size:48px_48px]" />

    <div class="relative w-full max-w-sm">
      <!-- Logo -->
      <div class="mb-8 text-center stagger-item" style="--i: 0">
        <div class="mx-auto mb-4 flex items-center justify-center">
          <img src="/logo-small.svg" alt="CATEYE" class="h-12 w-auto" />
        </div>
        <p class="mt-1 text-xs text-muted-foreground">Investigación de bug bounty automatizada</p>
      </div>

      <!-- Card -->
      <div class="rounded-2xl border border-border/40 bg-[#131524]/80 p-6 backdrop-blur-xl hover-lift stagger-item" style="--i: 1">
        <div class="mb-5 text-center">
          <h2 class="text-sm font-semibold text-foreground">
            {{ isRegister ? 'Crear cuenta' : 'Iniciar sesión' }}
          </h2>
          <p class="mt-0.5 text-[10px] text-muted-foreground">
            {{ isRegister ? 'Registrate para comenzar' : 'Ingresá tus credenciales' }}
          </p>
        </div>

        <!-- Error -->
        <div v-if="localError || auth.error" class="mb-4 flex items-start gap-2 rounded-lg bg-destructive/10 px-3 py-2 text-xs text-destructive animate-in-fast">
          <AlertCircle class="mt-0.5 h-3.5 w-3.5 shrink-0" />
          <span>{{ localError || auth.error }}</span>
        </div>

        <form @submit.prevent="handleSubmit" class="space-y-3">
          <!-- Display name (register only) -->
          <div v-if="isRegister" class="stagger-item" style="--i: 2">
            <label class="mb-1 block text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Nombre</label>
            <input
              v-model="displayName"
              type="text"
              placeholder="Tu nombre"
              class="w-full rounded-lg border border-border/60 bg-surface/30 px-3 py-2 text-xs text-foreground placeholder:text-muted-foreground/40 focus:border-primary/30 focus:outline-none focus:ring-1 focus:ring-primary/20 transition-all focus-glow"
            />
          </div>

          <!-- Email -->
          <div class="stagger-item" style="--i: isRegister ? 2 : 2">
            <label class="mb-1 block text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Email</label>
            <input
              v-model="email"
              type="email"
              placeholder="email@ejemplo.com"
              autocomplete="email"
              class="w-full rounded-lg border border-border/60 bg-surface/30 px-3 py-2 text-xs text-foreground placeholder:text-muted-foreground/40 focus:border-primary/30 focus:outline-none focus:ring-1 focus:ring-primary/20 transition-all focus-glow"
            />
          </div>

          <!-- Password -->
          <div class="stagger-item" style="--i: 3">
            <label class="mb-1 block text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Contraseña</label>
            <div class="relative">
              <input
                v-model="password"
                :type="showPassword ? 'text' : 'password'"
                placeholder="••••••••"
                autocomplete="current-password"
                class="w-full rounded-lg border border-border/60 bg-surface/30 px-3 py-2 pr-9 text-xs text-foreground placeholder:text-muted-foreground/40 focus:border-primary/30 focus:outline-none focus:ring-1 focus:ring-primary/20 transition-all focus-glow"
              />
              <button
                type="button"
                @click="showPassword = !showPassword"
                class="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors hover-scale"
              >
                <Eye v-if="!showPassword" class="h-3.5 w-3.5" />
                <EyeOff v-else class="h-3.5 w-3.5" />
              </button>
            </div>
          </div>

          <!-- Submit -->
          <button
            type="submit"
            :disabled="submitting"
            class="flex w-full items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-xs font-semibold text-white shadow-sm hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50 transition-all btn-press"
          >
            <Loader2 v-if="submitting" class="h-3.5 w-3.5 animate-spin" />
            <component :is="isRegister ? UserPlus : LogIn" v-else class="h-3.5 w-3.5" />
            {{ isRegister ? 'Crear cuenta' : 'Ingresar' }}
          </button>
        </form>

        <!-- Toggle mode -->
        <div class="mt-4 text-center stagger-item" style="--i: 5">
          <button
            @click="toggleMode"
            class="text-[10px] text-muted-foreground hover:text-primary transition-colors hover-scale"
          >
            {{ isRegister ? '¿Ya tenés cuenta? Iniciá sesión' : '¿No tenés cuenta? Registrate' }}
          </button>
        </div>
      </div>

      <!-- Footer features -->
      <div class="mt-6 flex items-center justify-center gap-4 text-[9px] text-muted-foreground/60 stagger-item" style="--i: 6">
        <span class="flex items-center gap-1"><Shield class="h-3 w-3" /> Datos seguros</span>
        <span class="flex items-center gap-1"><Zap class="h-3 w-3" /> Sin latencia</span>
        <span class="flex items-center gap-1"><Target class="h-3 w-3" /> Auto-gestión</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.animate-in {
  animation: fadeIn 0.3s ease-out;
}
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
