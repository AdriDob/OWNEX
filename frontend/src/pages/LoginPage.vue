<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { Shield, Zap, Loader2, AlertCircle, Target } from '@lucide/vue'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const error = ref('')
const loading = ref(false)

function getSafeRedirect(value?: string | null): string {
  if (!value || typeof value !== 'string') return '/'
  if (!value.startsWith('/')) return '/'
  if (value.startsWith('//')) return '/'
  if (value.includes('://')) return '/'
  return value
}

async function autoLoginViaDevice() {
  loading.value = true
  error.value = ''
  try {
    const ok = await auth.autoLogin()
    if (ok) {
      router.push(getSafeRedirect(route.query.redirect as string | undefined))
    } else {
      error.value = 'No se pudo iniciar sesión automáticamente.'
    }
  } catch (e: any) {
    error.value = e?.message || 'Error de autenticación'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  if (auth.isAuthenticated) {
    router.push(getSafeRedirect(route.query.redirect as string | undefined))
  } else {
    autoLoginViaDevice()
  }
})
</script>

<template>
  <div class="flex min-h-screen w-full items-center justify-center bg-gradient-to-br from-background via-surface to-surface p-4">
    <!-- Decorative grid -->
    <div class="pointer-events-none fixed inset-0 bg-[linear-gradient(rgba(156, 163, 175,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(156, 163, 175,0.03)_1px,transparent_1px)] bg-[size:48px_48px]" />

    <div class="relative w-full max-w-sm">
      <!-- Logo -->
      <div class="mb-8 text-center stagger-item" style="--i: 0">
        <div class="mx-auto mb-4 flex items-center justify-center">
          <img src="/logo-small.svg" alt="OWNEX" class="h-12 w-auto" />
        </div>
        <p class="mt-1 text-xs text-muted-foreground">Investigación de bug bounty automatizada</p>
      </div>

      <!-- Card -->
      <div class="rounded-2xl border border-border/40 bg-surface/80 p-6 backdrop-blur-xl hover-lift stagger-item" style="--i: 1">
        <div class="mb-5 text-center">
          <h2 class="text-sm font-semibold text-foreground">Bienvenido a OWNEX</h2>
          <p class="mt-0.5 text-[10px] text-muted-foreground">
            Inicio de sesión automático por dispositivo (sin correo ni contraseña)
          </p>
        </div>

        <!-- Error -->
        <div v-if="error || auth.error" class="mb-4 flex items-start gap-2 rounded-lg bg-destructive/10 px-3 py-2 text-xs text-destructive animate-in-fast">
          <AlertCircle class="mt-0.5 h-3.5 w-3.5 shrink-0" />
          <span>{{ error || auth.error }}</span>
        </div>

        <div v-if="loading" class="flex flex-col items-center gap-3 py-6">
          <Loader2 class="h-6 w-6 animate-spin text-primary" />
          <span class="text-xs text-muted-foreground">Activando sesión del dispositivo…</span>
        </div>

        <div v-else-if="error" class="pt-1 text-center">
          <button
            @click="autoLoginViaDevice()"
            class="mx-auto flex w-full items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-xs font-semibold text-white shadow-sm hover:bg-primary/90 transition-all btn-press"
          >
            Reintentar
          </button>
        </div>
      </div>

      <!-- Footer features -->
      <div class="mt-6 flex items-center justify-center gap-4 text-[9px] text-muted-foreground/60 stagger-item" style="--i: 6">
        <span class="flex items-center gap-1"><Shield class="h-3 w-3" /> Datos seguros</span>
        <span class="flex items-center gap-1"><Zap class="h-3 w-3" /> Sin latencia</span>
        <span class="flex items-center gap-1"><Target class="h-3 w-3" /> Gestión local</span>
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
