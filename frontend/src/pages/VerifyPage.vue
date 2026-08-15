<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '@/lib/api'
import { MailCheck, XCircle, Loader2, ShieldCheck } from '@lucide/vue'

const route = useRoute()
const router = useRouter()

const status = ref<'loading' | 'success' | 'error'>('loading')
const errorMsg = ref('')
const username = ref('')

onMounted(async () => {
  const token = (route.query.token as string) || ''
  if (!token) {
    status.value = 'error'
    errorMsg.value = 'Falta el token de verificación en el enlace.'
    return
  }
  try {
    const res = await api.post<{ email: string; username: string }>(
      `/auth/users/verify?token=${encodeURIComponent(token)}`,
      undefined,
      true,
    )
    username.value = res?.username || ''
    status.value = 'success'
  } catch (e: any) {
    status.value = 'error'
    errorMsg.value = e?.message?.replace(/^"|"$/g, '') || 'El enlace es inválido o ha expirado.'
  }
})
</script>

<template>
  <div class="min-h-screen flex items-center justify-center bg-background px-4">
    <div class="w-full max-w-md rounded-2xl border border-border/60 bg-surface/40 p-8 text-center shadow-xl backdrop-blur">
      <template v-if="status === 'loading'">
        <Loader2 class="mx-auto h-10 w-10 animate-spin text-primary" />
        <h2 class="mt-4 text-sm font-semibold text-foreground">Verificando tu correo…</h2>
      </template>

      <template v-else-if="status === 'success'">
        <MailCheck class="mx-auto h-10 w-10 text-success" />
        <h2 class="mt-4 text-sm font-semibold text-foreground">¡Correo verificado!</h2>
        <p class="mt-1 text-xs text-muted-foreground">
          Tu cuenta<template v-if="username"> <span class="text-foreground">{{ username }}</span></template> ya está
          lista.
        </p>
        <button
          class="mt-5 w-full rounded-lg bg-primary px-3 py-2 text-xs font-medium text-primary-foreground transition-colors hover:bg-primary/90"
          @click="router.push('/')"
        >
          Ir a la aplicación
        </button>
      </template>

      <template v-else>
        <XCircle class="mx-auto h-10 w-10 text-destructive" />
        <h2 class="mt-4 text-sm font-semibold text-foreground">No se pudo verificar</h2>
        <p class="mt-1 text-xs text-muted-foreground">{{ errorMsg }}</p>
        <button
          class="mt-5 w-full rounded-lg bg-primary px-3 py-2 text-xs font-medium text-primary-foreground transition-colors hover:bg-primary/90"
          @click="router.push('/')"
        >
          Ir a la aplicación
        </button>
      </template>

      <p class="mt-6 flex items-center justify-center gap-1 text-[10px] text-muted-foreground/70">
        <ShieldCheck class="h-3 w-3" /> OWNEX OMEGA · Verificación de cuenta
      </p>
    </div>
  </div>
</template>
