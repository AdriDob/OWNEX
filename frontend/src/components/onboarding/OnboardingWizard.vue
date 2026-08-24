<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useSettingsStore } from '@/stores/settings'
import Button from '@/components/ui/Button.vue'
import Badge from '@/components/ui/Badge.vue'
import Tooltip from '@/components/ui/Tooltip.vue'
import {
  Eye, Globe, Sparkles, Key, CheckCircle2,
  ArrowRight, ArrowLeft, Cpu, AlertTriangle,
  Star, SkipForward, Database, Wrench,
  Server, Shield, Activity,
} from '@lucide/vue'
import { api } from '@/lib/api'

const props = defineProps<{ open: boolean }>()
const emit = defineEmits<{ close: [] }>()

const router = useRouter()
const settings = useSettingsStore()

const step = ref(0)
const steps = [
  { id: 'welcome', icon: Eye, label: 'Bienvenido' },
  { id: 'verify', icon: Activity, label: 'Verificación' },
  { id: 'ai', icon: Cpu, label: 'IA' },
  { id: 'keys', icon: Key, label: 'API Keys' },
  { id: 'finish', icon: Star, label: 'Listo' },
]
const totalSteps = steps.length

const saving = ref(false)
const errorMsg = ref('')
const skipConfirm = ref(false)

const userName = ref(settings.data.general.userName)

const aiProvider = ref(settings.data.ai.provider)
const ollamaHost = ref(settings.data.ai.ollamaHost)
const ollamaModel = ref(settings.data.ai.ollamaModel)
const openaiKey = ref(settings.data.ai.openaiKey)
const geminiKey = ref(settings.data.ai.geminiKey)
const temp = ref(settings.data.ai.temperature)

const apiKeys = ref({ ...settings.data.apiKeys })

const platformKeys = ref({
  bugcrowd: settings.data.apiKeys.bugcrowd,
  hackerone: settings.data.apiKeys.hackerone,
  intigriti: settings.data.apiKeys.intigriti,
})

// ── System verification state ──
const verificationResults = ref<Record<string, { status: 'checking' | 'ok' | 'warn' | 'error'; message: string }>>({
  api: { status: 'checking', message: 'Verificando...' },
  database: { status: 'checking', message: 'Verificando...' },
  version: { status: 'checking', message: 'Verificando...' },
  uptime: { status: 'checking', message: 'Verificando...' },
})

const overallStatus = computed(() => {
  const vals = Object.values(verificationResults.value)
  if (vals.some(v => v.status === 'error')) return 'error'
  if (vals.some(v => v.status === 'checking' || v.status === 'warn')) return 'warning'
  return 'ok'
})

const progress = computed(() => Math.round(((step.value + 1) / totalSteps) * 100))

onMounted(async () => {
  if (props.open && step.value === 1) {
    await runVerification()
  }
})

watch(() => props.open, async (v) => {
  if (v) {
    step.value = 0
    errorMsg.value = ''
    // Reset verification state
    verificationResults.value = {
      api: { status: 'checking', message: 'Verificando...' },
      database: { status: 'checking', message: 'Verificando...' },
      version: { status: 'checking', message: 'Verificando...' },
      uptime: { status: 'checking', message: 'Verificando...' },
    }
    // Re-verify on every open: the backend may have become ready since the
    // wizard first mounted (Tauri sidecar cold start can take ~30 s).
    await runVerification()
  }
})

async function runVerification() {
  // API health
  try {
    const health: any = await api.get('/health')
    verificationResults.value.api = { status: 'ok', message: 'Backend respondiendo' }
  } catch {
    verificationResults.value.api = { status: 'error', message: 'Backend no responde. ¿Está corriendo?' }
  }

  // Version
  try {
    const ver: any = await api.get('/version')
    verificationResults.value.version = {
      status: ver?.version ? 'ok' : 'warn',
      message: `OWNEX ${ver?.version || 'desconocida'}`,
    }
  } catch {
    verificationResults.value.version = { status: 'error', message: 'No se pudo obtener versión' }
  }

  // Database (via system/health endpoint which queries DB)
  try {
    const sysHealth: any = await api.get('/system/health')
    const db = sysHealth?.database
    verificationResults.value.database = {
      status: 'ok',
      message: `${db?.targets || 0} targets, ${db?.endpoints || 0} endpoints`,
    }
  } catch {
    verificationResults.value.database = { status: 'warn', message: 'No se pudo consultar DB' }
  }

  // Uptime / system state (approximate via system/status or health)
  try {
    const state: any = await api.get('/system/state')
    const uptime = state?.uptime || state?.uptime_hint || 'disponible'
    verificationResults.value.uptime = {
      status: 'ok',
      message: `Sistema ${String(uptime)}`,
    }
  } catch {
    verificationResults.value.uptime = { status: 'warn', message: 'No disponible aún' }
  }
}

function close() {
  emit('close')
}

function skip() {
  if (!skipConfirm.value) {
    skipConfirm.value = true
    setTimeout(() => skipConfirm.value = false, 3000)
    return
  }
  settings.completeOnboarding(true)
  close()
  router.push({ name: 'mission-control' })
}

async function finish() {
  saving.value = true
  errorMsg.value = ''
  try {
    settings.updateGeneral({ userName: userName.value })
    settings.updateAI({
      provider: aiProvider.value as any,
      ollamaHost: ollamaHost.value,
      ollamaModel: ollamaModel.value,
      openaiKey: openaiKey.value,
      geminiKey: geminiKey.value,
      temperature: temp.value,
    })
    settings.updateApiKeys({
      bugcrowd: platformKeys.value.bugcrowd,
      hackerone: platformKeys.value.hackerone,
      intigriti: platformKeys.value.intigriti,
    })
    settings.completeOnboarding(false)
    close()
    router.push({ name: 'mission-control' })
  } catch (e: any) {
    errorMsg.value = e?.message || 'Error al guardar configuración'
  } finally {
    saving.value = false
  }
}

function next() {
  if (step.value === 1 && !verifiedOnce.value) {
    runVerification()
  }
  if (step.value < totalSteps - 1) step.value++
}

const verifiedOnce = ref(false)

function prev() {
  if (step.value > 0) step.value--
}
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="open" class="fixed inset-0 z-[100] flex items-center justify-center p-4" @click.self="close">
        <div class="fixed inset-0 bg-black/70 backdrop-blur-sm" />

        <div class="relative w-full max-w-2xl animate-in">
          <div class="card-base rounded-2xl border border-border/50 overflow-hidden">
            <!-- Header -->
            <div class="flex items-center justify-between border-b border-border/20 px-6 py-3.5">
              <div class="flex items-center gap-2">
                <Eye class="h-4 w-4 text-primary" />
                <span class="font-mono text-[10px] font-bold tracking-widest text-primary">OWNEX SETUP</span>
              </div>
              <div class="flex items-center gap-3">
                <span class="font-mono text-[10px] text-muted-foreground">{{ step + 1 }} / {{ totalSteps }}</span>
                <div class="h-1.5 w-28 overflow-hidden rounded-full bg-border/30">
                  <div class="h-full rounded-full bg-primary transition-all duration-500" :style="{ width: `${progress}%` }" />
                </div>
                <button class="font-mono text-xs text-muted-foreground hover:text-foreground transition-colors" @click="close">✕</button>
              </div>
            </div>

            <!-- Step indicator -->
            <div class="flex gap-0.5 px-6 pt-3 pb-2 overflow-x-auto">
              <button
                v-for="(s, i) in steps"
                :key="s.id"
                @click="step = i"
                class="flex items-center gap-1.5 rounded-lg px-2 py-1 font-mono text-[9px] transition-all whitespace-nowrap"
                :class="i === step ? 'bg-primary/15 text-primary' : i < step ? 'text-primary/50' : 'text-muted-foreground/40'"
              >
                <component :is="s.icon" class="h-3 w-3" />
                <span class="hidden sm:inline">{{ s.label }}</span>
              </button>
            </div>

            <!-- Body -->
            <div class="px-6 py-6 min-h-[320px]">
              <!-- ═══ WELCOME ═══ -->
              <div v-if="step === 0" class="max-w-md mx-auto space-y-5">
                <div class="text-center mb-2">
                  <div class="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10 mb-5">
                    <Eye class="h-8 w-8 text-primary" />
                  </div>
                  <h2 class="font-display text-2xl font-bold text-foreground">Bienvenido a OWNEX</h2>
                  <p class="mt-2 text-sm text-muted-foreground max-w-md mx-auto leading-relaxed">
                    Sistema de Inteligencia de Seguridad para bug bounty.
                  </p>
                </div>
                <div class="space-y-3 text-xs text-muted-foreground bg-surface/10 rounded-lg p-4 border border-border/20">
                  <p><strong class="text-foreground">¿Qué es?</strong> Un sistema que automatiza el ciclo completo de bug bounty: descubre programas, ejecuta reconocimiento, genera hipótesis, valida hallazgos, produce reportes y trackea pagos.</p>
                  <p><strong class="text-foreground">¿Qué hace OWNEX?</strong> OWNEX es el sistema de priorización. Aprende de tus resultados y recomienda qué target investigar, sin reemplazar tus decisiones.</p>
                  <p><strong class="text-foreground">¿Qué necesitás?</strong> Python 3.10+, Node.js 18+, y opcionalmente herramientas de recon externas (subfinder, httpx, katana, nuclei).</p>
                </div>
                <div>
                  <label class="mb-1.5 block font-mono text-[10px] text-muted-foreground uppercase tracking-wider">Tu nombre</label>
                  <input
                    v-model="userName"
                    class="w-full rounded-lg border border-border/40 bg-surface/30 px-3.5 py-2.5 font-mono text-sm text-foreground placeholder:text-muted-foreground/40 focus:outline-none focus:border-primary/50 transition-colors"
                    placeholder="Operador"
                  />
                </div>
              </div>

              <!-- ═══ SYSTEM VERIFICATION ═══ -->
              <div v-if="step === 1" class="max-w-md mx-auto space-y-4">
                <h2 class="font-display text-lg font-bold text-foreground text-center">Verificación del sistema</h2>
                <p class="text-center text-xs text-muted-foreground -mt-2">
                  OWNEX está verificando que todo funcione correctamente.
                </p>

                <div class="space-y-2.5 mt-4">
                  <div
                    v-for="(check, key) in verificationResults"
                    :key="key"
                    class="flex items-center justify-between rounded-lg border border-border/20 bg-surface/10 px-4 py-2.5"
                  >
                    <span class="font-mono text-xs capitalize text-muted-foreground">{{ key }}</span>
                    <div class="flex items-center gap-2">
                      <span class="font-mono text-[10px]" :class="{
                        'text-success': check.status === 'ok',
                        'text-warning': check.status === 'warn',
                        'text-destructive': check.status === 'error',
                        'text-muted-foreground': check.status === 'checking',
                      }">{{ check.message }}</span>
                      <span v-if="check.status === 'ok'" class="text-success"><CheckCircle2 class="h-3.5 w-3.5" /></span>
                      <span v-else-if="check.status === 'error'" class="text-destructive"><AlertTriangle class="h-3.5 w-3.5" /></span>
                      <span v-else-if="check.status === 'warn'" class="text-warning"><AlertTriangle class="h-3.5 w-3.5" /></span>
                      <span v-else class="text-muted-foreground animate-pulse"><Activity class="h-3.5 w-3.5" /></span>
                    </div>
                  </div>
                </div>

                <div v-if="overallStatus === 'error'" class="rounded-lg bg-destructive/10 border border-destructive/20 p-3">
                  <p class="font-mono text-[10px] text-destructive">
                    Hay problemas de conectividad. Verificá que el backend esté corriendo en puerto 8000.
                  </p>
                </div>
                <div v-else-if="overallStatus === 'ok'" class="rounded-lg bg-success/10 border border-success/20 p-3">
                  <p class="font-mono text-[10px] text-success flex items-center gap-1.5">
                    <CheckCircle2 class="h-3 w-3" /> Todos los sistemas responden correctamente.
                  </p>
                </div>

                <div class="flex justify-center">
                  <Button size="sm" variant="ghost" @click="runVerification">
                    <Activity class="mr-1 h-3.5 w-3.5" /> Re-verificar
                  </Button>
                </div>
              </div>

              <!-- ═══ AI ═══ -->
              <div v-if="step === 2" class="max-w-md mx-auto space-y-4">
                <h2 class="font-display text-lg font-bold text-foreground text-center">Inteligencia Artificial</h2>
                <p class="text-center text-xs text-muted-foreground -mt-1">OWNEX usa IA para análisis semántico de validaciones y generación de reportes.</p>
                <div>
                  <label class="mb-1.5 block font-mono text-[10px] text-muted-foreground uppercase tracking-wider">Proveedor</label>
                  <select v-model="aiProvider" class="w-full rounded-lg border border-border/40 bg-surface/30 px-3.5 py-2.5 font-mono text-sm text-foreground focus:outline-none focus:border-primary/50">
                    <option value="ollama">Ollama (local, recomendado)</option>
                    <option value="openai">OpenAI</option>
                    <option value="gemini">Google Gemini</option>
                    <option value="openrouter">OpenRouter</option>
                  </select>
                </div>
                <template v-if="aiProvider === 'ollama'">
                  <div>
                    <label class="mb-1.5 flex items-center gap-2 font-mono text-[10px] text-muted-foreground uppercase tracking-wider">
                      Host <Tooltip text="Dirección del servidor Ollama. Por defecto http://localhost:11434" position="right"><span class="inline-flex h-3 w-3 items-center justify-center rounded-full bg-muted-foreground/20 text-[7px] text-muted-foreground cursor-help">?</span></Tooltip>
                    </label>
                    <input v-model="ollamaHost" class="w-full rounded-lg border border-border/40 bg-surface/30 px-3.5 py-2.5 font-mono text-sm text-foreground focus:outline-none focus:border-primary/50" />
                  </div>
                  <div>
                    <label class="mb-1.5 block font-mono text-[10px] text-muted-foreground uppercase tracking-wider">Modelo</label>
                    <input v-model="ollamaModel" class="w-full rounded-lg border border-border/40 bg-surface/30 px-3.5 py-2.5 font-mono text-sm text-foreground focus:outline-none focus:border-primary/50" />
                  </div>
                </template>
                <template v-if="aiProvider === 'openai'">
                  <div>
                    <label class="mb-1.5 block font-mono text-[10px] text-muted-foreground uppercase tracking-wider">API Key</label>
                    <input v-model="openaiKey" type="password" class="w-full rounded-lg border border-border/40 bg-surface/30 px-3.5 py-2.5 font-mono text-sm text-foreground focus:outline-none focus:border-primary/50" />
                  </div>
                </template>
                <template v-if="aiProvider === 'gemini'">
                  <div>
                    <label class="mb-1.5 block font-mono text-[10px] text-muted-foreground uppercase tracking-wider">API Key</label>
                    <input v-model="geminiKey" type="password" class="w-full rounded-lg border border-border/40 bg-surface/30 px-3.5 py-2.5 font-mono text-sm text-foreground focus:outline-none focus:border-primary/50" />
                  </div>
                </template>
                <div>
                  <label class="mb-1.5 block font-mono text-[10px] text-muted-foreground uppercase tracking-wider">Temperatura</label>
                  <input v-model.number="temp" type="range" min="0" max="2" step="0.1" class="w-full accent-primary" />
                  <span class="font-mono text-[10px] text-muted-foreground">{{ temp }}</span>
                  <p class="font-mono text-[9px] text-muted-foreground/60 mt-0.5">Recomendado: 0.3 para validación precisa, 0.7 para generación creativa</p>
                </div>
              </div>

              <!-- ═══ API KEYS ═══ -->
              <div v-if="step === 3" class="max-w-lg mx-auto space-y-3">
                <h2 class="font-display text-lg font-bold text-foreground text-center">API Keys</h2>
                <p class="text-center text-xs text-muted-foreground -mt-2">Opcional. Mejoran el reconocimiento pero OWNEX funciona sin ellas.</p>
                <div v-for="svc in [
                  { key: 'shodan', label: 'Shodan', desc: 'Reconocimiento de puertos y servicios' },
                  { key: 'censys', label: 'Censys', desc: 'Inventario de dispositivos en internet' },
                  { key: 'virustotal', label: 'VirusTotal', desc: 'Análisis de malware y URLs' },
                  { key: 'securitytrails', label: 'SecurityTrails', desc: 'Historial de DNS y subdominios' },
                  { key: 'github', label: 'GitHub', desc: 'Búsqueda de credenciales expuestas' },
                  { key: 'gitlab', label: 'GitLab', desc: 'Búsqueda de credenciales expuestas' },
                ]" :key="svc.key" class="flex items-center gap-2">
                  <span class="w-24 text-right font-mono text-[10px] text-muted-foreground">{{ svc.label }}</span>
                  <input
                    v-model="apiKeys[svc.key as keyof typeof apiKeys]"
                    type="password"
                    placeholder="••••••••"
                    class="flex-1 rounded-lg border border-border/30 bg-surface/20 px-3 py-1.5 font-mono text-[11px] text-foreground placeholder:text-muted-foreground/30 focus:outline-none focus:border-primary/50 transition-colors"
                  />
                </div>
              </div>

              <!-- ═══ FINISH ═══ -->
              <div v-if="step === 4" class="text-center">
                <div class="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-success/10 mb-5">
                  <CheckCircle2 class="h-8 w-8 text-success" />
                </div>
                <h2 class="font-display text-2xl font-bold text-foreground">✅ OWNEX está configurado</h2>
                <p class="mt-2 text-sm text-muted-foreground max-w-md mx-auto">
                  El sistema está listo para uso diario. No necesitás volver a realizar esta configuración.
                </p>
                <div class="mt-6 flex flex-wrap items-center justify-center gap-2">
                  <Badge variant="success" class="font-mono text-[10px] px-3 py-1">
                    <Sparkles class="mr-1 h-3 w-3" /> Sistema configurado
                  </Badge>
                  <Badge variant="outline" class="font-mono text-[10px] px-3 py-1">
                    <Server class="mr-1 h-3 w-3" /> {{ overallStatus === 'ok' ? 'Backend OK' : 'Backend con advertencias' }}
                  </Badge>
                </div>
                <div class="mt-4 text-left text-xs text-muted-foreground bg-surface/10 rounded-lg p-3 border border-border/20 space-y-1">
                  <p><strong class="text-foreground">Primeros pasos:</strong></p>
                  <p>1. Importá programas desde Discovery o ejecutá <code>python scripts/seed_real.py</code></p>
                  <p>2. Revisá la próxima acción recomendada por OWNEX en Mission Control</p>
                  <p>3. Lanzá tu primer scan sobre un target</p>
                  <p>4. Revisá findings y confirmá/rechazá</p>
                  <p>5. Exportá reportes y enviá a plataformas</p>
                </div>
                <div v-if="errorMsg" class="mt-3 flex items-center justify-center gap-1.5 text-destructive">
                  <AlertTriangle class="h-3.5 w-3.5" />
                  <span class="font-mono text-[11px]">{{ errorMsg }}</span>
                </div>
              </div>
            </div>

            <!-- Footer -->
            <div class="flex items-center justify-between border-t border-border/20 px-6 py-3.5">
              <div class="flex gap-2">
                <Button v-if="step > 0" variant="ghost" size="sm" @click="prev">
                  <ArrowLeft class="mr-1 h-3.5 w-3.5" /> Anterior
                </Button>
              </div>
              <div class="flex items-center gap-2">
                <Button variant="ghost" size="sm" class="text-muted-foreground" @click="skip">
                  <SkipForward class="mr-1 h-3.5 w-3.5" /> {{ skipConfirm ? '¿Saltar config?' : 'Skip' }}
                </Button>
                <Button v-if="step < totalSteps - 1" size="sm" @click="next">
                  Siguiente <ArrowRight class="ml-1 h-3.5 w-3.5" />
                </Button>
                <Button v-if="step === totalSteps - 1" @click="finish" :loading="saving">
                  <CheckCircle2 class="mr-1 h-4 w-4" /> Ir al Dashboard
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
