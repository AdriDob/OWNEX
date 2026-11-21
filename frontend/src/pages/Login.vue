<template>
  <div class="min-h-screen bg-gradient-to-b from-gray-900 via-gray-950 to-gray-900 text-gray-100 py-12 px-4 sm:px-6 lg:px-8">
    <div class="max-w-md mx-auto">
      <div class="bg-gray-800/50 backdrop-blur-xl rounded-2xl p-8 md:p-10 border border-white/5 shadow-2xl">
        <div class="text-center mb-8">
          <div class="w-14 h-14 mx-auto mb-6 flex items-center justify-center rounded-2xl bg-gray-700">
            <svg class="w-7 h-7 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10L7 7m3 3H8m5 3horizontal- line 3 3m0 0l3-3m-3 3h8a2 2 0 002-2v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2m7.66-7.66a2.828 2.828 0 010 4l-2.828 2.828a2.828 2.828 0 01-4 0l-2.828-2.828a2.828 2.828 0 010-4l2.828-2.828a2.828 2.828 0 014 0z"/>
            </svg>
          </div>
          <h1 class="text-3xl font-bold text-white tracking-tighter">OWNEX Intelligence</h1>
          <p class="text-gray-400 mt-2 text-sm">Sistema de bug bounty y análisis de seguridad</p>
        </div>

        <form @submit.prevent="onLogin" class="space-y-4">
          <div>
            <label for="token" class="block text-sm font-medium text-gray-300 mb-2">Token de sesión</label>
            <p class="text-xs text-gray-500">Ingresa tu token JWT para acceder al sistema</p>
            <textarea
              id="token"
              v-model="tokenInput"
              rows="3"
              cols="50"
              class="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-3 text-sm text-white focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 resize-none placeholder-gray-500"
              placeholder="Pega tu token JWT aquí..."
              :disabled="isLoggingIn"
            ></textarea>
            <template v-if="errorLogin">
              <p class="text-red-500 text-sm mt-1">{{ errorLogin }}</p>
            </template>
          </div>

          <div class="flex justify-end">
            <button
              type="submit"
              :disabled="isLoggingIn || !tokenInput.trim()"
              class="btn-primary px-6 py-3 rounded-lg font-medium text-white hover:opacity-90 transition-opacity"
            >
              <template v-if="isLoggingIn">
                <span class="flex items-center">
                  <svg class="mr-2 animate-spin w-4 h-4" viewBox="0 0 24 24">
                    <circle
                      class="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      stroke-width="4"
                    ></circle>
                    <path
                      class="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C12 0 16 4 16 4s4 4 4 4-4 4-4 4M0 4a4 4 0 004 4v12a4 4 0 00-4 4H0z"
                    ></path>
                  </svg>
                  Iniciando sesión...
                </span>
              </template>
              <template v-else>
                Iniciar sesión
              </template>
            </button>
          </div>
        </form>

        <div class="mt-6 text-center">
          <p class="text-gray-500 text-sm">¿Ya tienes una cuenta?</p>
          <router-link
            to="/"
            class="ml-2 text-primary-600 font-medium hover:underline transition-colors"
          >
            Registrarse
          </router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'

const authStore = useAuthStore()
const router = useRouter()

const tokenInput = ref('')
const isLoggingIn = ref(false)
const errorLogin = ref<string | null>(null)

const onLogin = async () => {
  if (!tokenInput?.trim()) {
    errorLogin = 'Por favor ingresa un token'
    return
  }

  isLoggingIn.value = true
  errorLogin = null

  try {
    await authStore.loginWithToken(tokenInput.trim())

    // Check if authenticated and navigate
    if (authStore.isAuthenticated) {
      // Persist the session
      authStore.persistSession()

      // Navigate to dashboard/home
      router.push('/')
    } else {
      errorLogin = 'No se pudo autenticar con el token proporcionado'
    }
  } catch (e: any) {
    errorLogin = e?.message || 'Error desconocido al iniciar sesión'
  } finally {
    isLoggingIn.value = false
  }
}
</script>

<style scoped>
.btn-primary {
  @apply bg-primary-600 hover:bg-primary-700 text-white font-medium rounded-lg transition-colors active:scale-[0.98] focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed;
}

/* Dark mode adjustments for input */
textarea {
  ::placeholder {
    color: rgba(255, 255, 255, 0.5);
  }
}
</style>