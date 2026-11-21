<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useDiscoveryStore } from '@/stores/discovery'
import { useExternalConnectionManager } from '@/composables/useExternalConnectionManager'
import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import { useToast } from '@/hooks/useToast'

const props = defineProps<{
  sourceName: string
  sourceUrl: string
  category: string
}>

const auth = useAuthStore()
const discovery = useDiscoveryStore()
const { getPlatformAccounts, storePlatformCredentials, removePlatformAccount, getPlatformStatus } = useExternalConnectionManager()
const { toast } = useToast()

const sourceName = ref(props.sourceName)
const sourceUrl = ref(props.sourceUrl)
const category = ref(props.category)

// Check if source already has platform account connected
const platformStatus = ref('')
const connectionStatus = computed(() => {
  if (!sourceName.value) return ''
  return getPlatformStatus(sourceName.value) || ''
})

// Store credentials for this source
async function handleConnect() {
  // Show modal/prompt for email and token
  const email = prompt('Ingresa tu email para esta fuente:', '')
  if (!email) return
  
  // Try to get stored token or prompt
  const existing = await getPlatformAccounts()
  const alreadyConnected = existing.some((a: any) => a.provider === sourceName.value)
  
  if (alreadyConnected) {
    const confirmed = confirm('Esta fuente ya está conectada. ¿Deseas re-autorizar?')
    if (confirmed) {
      // Remove and reconnect
      await removePlatformAccount(sourceName.value)
    } else {
      return
    }
  }
  
  // For each source type, we need different auth flow
  // For now, store basic credentials
  const token = prompt('Ingresa tu token o contraseña para ' + sourceName.value + ':', '')
  if (!token) return
  
  await storePlatformCredentials(sourceName.value, email, token)
  toast({
    title: 'Conexión guardada',
    description: 'Las credenciales para ' + sourceName.value + ' se han guardado de forma segura.',
    variant: 'success'
  })
  connectionStatus.value = 'connected'
}

// Remove connection
async function handleDisconnect() {
  await removePlatformAccount(sourceName.value)
  connectionStatus.value = ''
  toast({
    title: 'Conexión removida',
    description: 'Las credenciales de ' + sourceName.value + ' han sido removidas.',
    variant: 'info'
  })
}

// Watch for status changes
watch(platformStatus, async (newStatus) => {
  connectionStatus.value = newStatus
})
</script>

<template>
<Card class="p-6 max-w-md">
  <div class="flex items-center justify-between mb-4">
    <h3 class="font-medium text-foreground">
      <Info class="h-3 w-3 text-primary me-2" /> Configurar Conexión
    </h3>
    <Button 
      variant="ghost" 
      size="sm" 
      @click="handleDisconnect"
      v-if="connectionStatus"
    >
      <XCircle class="h-3.5 w-3.5 text-destructive" /> Quitar
    </Button>
  </div>
  
  <div v-if="!connectionStatus" class="space-y-4">
    <div>
      <span class="text-xs text-muted-foreground block mb-1">Fuente</span>
      <Badge variant="outline" class="text-[8px]">{{ sourceName }}</Badge>
    </div>
    
    <div v-if="category === 'bug_bounty'">
      <p class="text-xs text-muted-foreground mb-3">
        Esta fuente requiere autenticación para acceder a programas premium.
      </p>
      <Button 
        variant="primary" 
        size="sm" 
        @click="handleConnect"
        :disabled="connectionStatus"
      >
        <RefreshCw class="h-3.5 w-3.5 me-2" /> Conectar
      </Button>
    </div>
    
    <div v-else-if="category === 'ai_evaluation'">
      <p class="text-xs text-muted-foreground mb-3">
        Acceso a proyectos de evaluación IA. Requiere registro y validación.
      </p>
      <Button 
        variant="primary" 
        size="sm" 
        @click="handleConnect"
        :disabled="connectionStatus"
      >
        <RefreshCw class="h-3.5 w-3.5 me-2" /> Conectar
      </Button>
    </div>
    
    <div v-else>
      <p class="text-xs text-muted-foreground mb-3">
        Configuración manual para esta fuente.
      </p>
      <Button 
        variant="primary" 
        size="sm" 
        @click="handleConnect"
        :disabled="connectionStatus"
      >
        <RefreshCw class="h-3.5 w-3.5 me-2" /> Configurar
      </Button>
    </div>
  </div>
  
  <div v-else class="mt-4 p-3 bg-surface/10 rounded-lg">
    <p class="text-xs text-muted-foreground mb-1">Estado</p>
    <Badge variant="outline" class="text-[8px]" :class="['text-success']">
      <CheckCircle class="h-3.5 w-3.5 me-2" /> Conectado
    </Badge>
    <p class="text-[8px] text-muted-foreground">
      {{ connectionStatus }}
    </p>
    <Button 
      variant="ghost" 
      size="sm" 
      @click="handleConnect"
    >
      <Retry class="h-3.5 w-3.5 me-2" /> Re-autenticar
    </Button>
  </div>
</Card>
</template>
