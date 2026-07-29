<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { checkLicense, activateLicense } from '@/lib/api'
import Card from '@/components/ui/Card.vue'
import Button from '@/components/ui/Button.vue'
import { KeyRound, CheckCircle2, AlertTriangle, Loader2 } from '@lucide/vue'

const router = useRouter()

const state = ref<'checking' | 'activated' | 'input' | 'error'>('checking')
const licenseKey = ref('')
const activating = ref(false)
const activationError = ref<string | null>(null)

onMounted(async () => {
  try {
    const res = await checkLicense()
    if (res.valid) {
      state.value = 'activated'
      setTimeout(() => router.push('/'), 2000)
    } else {
      state.value = 'input'
    }
  } catch {
    state.value = 'error'
  }
})

async function handleActivate() {
  if (!licenseKey.value.trim()) return
  activating.value = true
  activationError.value = null
  try {
    await activateLicense(licenseKey.value.trim())
    state.value = 'activated'
    setTimeout(() => router.push('/'), 2000)
  } catch (e: any) {
    activationError.value = e?.message || 'Error al activar la licencia. Verificá el código ingresado.'
  } finally {
    activating.value = false
  }
}
</script>

<template>
  <div class="flex min-h-screen items-center justify-center p-4">
    <div class="w-full max-w-md animate-in">
      <div class="mb-8 text-center">
        <img src="/logo.svg" alt="OWNEX" class="mx-auto h-24 w-24" />
      </div>
      <Card class="p-8 text-center">
        <!-- Checking state -->
        <template v-if="state === 'checking'">
          <div class="flex flex-col items-center py-8">
            <Loader2 class="h-12 w-12 text-primary animate-spin mb-4" />
            <p class="text-sm font-semibold text-foreground">Verificando licencia...</p>
            <p class="mt-1 text-xs text-muted-foreground">Un momento por favor</p>
          </div>
        </template>

        <!-- Activated state -->
        <template v-else-if="state === 'activated'">
          <div class="flex flex-col items-center py-8">
            <div class="flex h-16 w-16 items-center justify-center rounded-2xl bg-success/10 mb-4">
              <CheckCircle2 class="h-10 w-10 text-success" />
            </div>
            <p class="text-lg font-bold text-foreground">¡Licencia Activada!</p>
            <p class="mt-1 text-sm text-muted-foreground">Redirigiendo al dashboard...</p>
          </div>
        </template>

        <!-- Error state -->
        <template v-else-if="state === 'error'">
          <div class="flex flex-col items-center py-8">
            <div class="flex h-16 w-16 items-center justify-center rounded-2xl bg-destructive/10 mb-4">
              <AlertTriangle class="h-10 w-10 text-destructive" />
            </div>
            <p class="text-sm font-semibold text-foreground">Error de conexión</p>
            <p class="mt-1 text-xs text-muted-foreground">No se pudo verificar el estado de la licencia</p>
            <Button variant="outline" class="mt-4" @click="state = 'input'">
              Ingresar clave manualmente
            </Button>
          </div>
        </template>

        <!-- Input state -->
        <template v-else>
          <div class="flex flex-col items-center py-4">
            <div class="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10 mb-4">
              <KeyRound class="h-10 w-10 text-primary" />
            </div>
            <p class="text-lg font-bold text-foreground">Activar Licencia</p>
            <p class="mt-1 text-sm text-muted-foreground">Ingresá tu código de licencia para activar OWNEX</p>

            <div class="w-full mt-6 space-y-4">
              <input
                v-model="licenseKey"
                placeholder="XXXXX-XXXXX-XXXXX-XXXXX"
                class="w-full rounded-lg border border-border/60 bg-surface/50 px-4 py-3 text-center text-sm font-mono text-foreground placeholder:text-muted-foreground/30 focus:border-primary/40 focus:outline-none focus:ring-1 focus:ring-primary/30 tracking-widest uppercase"
                @keyup.enter="handleActivate"
              />
              <Button class="w-full" @click="handleActivate" :disabled="activating || !licenseKey.trim()" :loading="activating">
                <KeyRound class="h-4 w-4" />
                {{ activating ? 'Activando...' : 'Activar' }}
              </Button>

              <p v-if="activationError" class="text-xs text-destructive flex items-center justify-center gap-1">
                <AlertTriangle class="h-3 w-3" />
                {{ activationError }}
              </p>
            </div>
          </div>
        </template>
      </Card>
    </div>
  </div>
</template>
