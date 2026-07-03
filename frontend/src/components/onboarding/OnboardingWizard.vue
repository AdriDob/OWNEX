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
  Star, SkipForward,
} from '@lucide/vue'

const props = defineProps<{ open: boolean }>()
const emit = defineEmits<{ close: [] }>()

const router = useRouter()
const settings = useSettingsStore()

const step = ref(0)
const steps = [
  { id: 'welcome', icon: Eye, label: 'Bienvenido' },
  { id: 'ai', icon: Cpu, label: 'IA' },
  { id: 'keys', icon: Key, label: 'API Keys' },
  { id: 'platforms', icon: Globe, label: 'Plataformas' },
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

const progress = computed(() => Math.round(((step.value + 1) / totalSteps) * 100))

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
  router.push('/mission-control')
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
    router.push('/mission-control')
  } catch (e: any) {
    errorMsg.value = e?.message || 'Error al guardar configuración'
  } finally {
    saving.value = false
  }
}

function next() {
  if (step.value < totalSteps - 1) step.value++
}

function prev() {
  if (step.value > 0) step.value--
}

watch(() => props.open, (v) => {
  if (v) {
    step.value = 0
    errorMsg.value = ''
  }
})
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="open" class="fixed inset-0 z-[100] flex items-center justify-center p-4" @click.self="close">
        <div class="fixed inset-0 bg-black/70 backdrop-blur-sm" />

        <div class="relative w-full max-w-2xl animate-in">
          <div class="cyber-card rounded-2xl border border-border/50 overflow-hidden">
            <!-- Header -->
            <div class="flex items-center justify-between border-b border-border/20 px-6 py-3.5">
              <div class="flex items-center gap-2">
                <Eye class="h-4 w-4 text-primary" />
                <span class="font-mono text-[10px] font-bold tracking-widest text-primary">CATEYE SETUP</span>
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
                  <h2 class="font-display text-2xl font-bold text-foreground">Bienvenido a CATEYE</h2>
                  <p class="mt-2 text-sm text-muted-foreground max-w-md mx-auto leading-relaxed">
                    Sistema de Inteligencia de Seguridad para bug bounty. Configuración rápida en 4 pasos.
                  </p>
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

              <!-- ═══ AI ═══ -->
              <div v-if="step === 1" class="max-w-md mx-auto space-y-4">
                <h2 class="font-display text-lg font-bold text-foreground text-center">Inteligencia Artificial</h2>
                <div>
                  <label class="mb-1.5 block font-mono text-[10px] text-muted-foreground uppercase tracking-wider">Proveedor</label>
                  <select v-model="aiProvider" class="w-full rounded-lg border border-border/40 bg-surface/30 px-3.5 py-2.5 font-mono text-sm text-foreground focus:outline-none focus:border-primary/50">
                    <option value="ollama">Ollama (local)</option>
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
                </div>
              </div>

              <!-- ═══ API KEYS ═══ -->
              <div v-if="step === 2" class="max-w-lg mx-auto space-y-3">
                <h2 class="font-display text-lg font-bold text-foreground text-center">API Keys</h2>
                <p class="text-center text-xs text-muted-foreground -mt-2">Configurá tus claves de plataformas y OSINT</p>
                <div v-for="svc in [
                  { key: 'shodan', label: 'Shodan' },
                  { key: 'censys', label: 'Censys' },
                  { key: 'virustotal', label: 'VirusTotal' },
                  { key: 'securitytrails', label: 'SecurityTrails' },
                  { key: 'github', label: 'GitHub' },
                  { key: 'gitlab', label: 'GitLab' },
                ]" :key="svc.key" class="flex items-center gap-2">
                  <span class="w-28 text-right font-mono text-[10px] text-muted-foreground">{{ svc.label }}</span>
                  <input
                    v-model="apiKeys[svc.key as keyof typeof apiKeys]"
                    type="password"
                    placeholder="••••••••"
                    class="flex-1 rounded-lg border border-border/30 bg-surface/20 px-3 py-1.5 font-mono text-[11px] text-foreground placeholder:text-muted-foreground/30 focus:outline-none focus:border-primary/50 transition-colors"
                  />
                </div>
              </div>

              <!-- ═══ PLATFORMS ═══ -->
              <div v-if="step === 3" class="max-w-lg mx-auto space-y-4">
                <h2 class="font-display text-lg font-bold text-foreground text-center">Plataformas Bug Bounty</h2>
                <div v-for="p in [
                  { key: 'bugcrowd', label: 'Bugcrowd' },
                  { key: 'hackerone', label: 'HackerOne' },
                  { key: 'intigriti', label: 'Intigriti' },
                ]" :key="p.key" class="space-y-1">
                  <label class="block font-mono text-[10px] text-muted-foreground uppercase tracking-wider">{{ p.label }}</label>
                  <input
                    v-model="platformKeys[p.key as keyof typeof platformKeys]"
                    type="password"
                    placeholder="API Key"
                    class="w-full rounded-lg border border-border/40 bg-surface/30 px-3.5 py-2 font-mono text-sm text-foreground placeholder:text-muted-foreground/40 focus:outline-none focus:border-primary/50"
                  />
                </div>
              </div>

              <!-- ═══ FINISH ═══ -->
              <div v-if="step === 4" class="text-center">
                <div class="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-success/10 mb-5">
                  <Star class="h-8 w-8 text-success" />
                </div>
                <h2 class="font-display text-2xl font-bold text-foreground">Todo listo</h2>
                <p class="mt-2 text-sm text-muted-foreground max-w-md mx-auto">
                  Configuración inicial completa. Podés ajustar cualquier opción desde Settings en cualquier momento.
                </p>
                <div class="mt-6 flex items-center justify-center gap-2">
                  <Badge variant="success" class="font-mono text-[10px] px-3 py-1">
                    <Sparkles class="mr-1 h-3 w-3" /> Sistema configurado
                  </Badge>
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
                  <CheckCircle2 class="mr-1 h-4 w-4" /> Finalizar
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
