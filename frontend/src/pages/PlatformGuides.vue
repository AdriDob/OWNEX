<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api } from '@/lib/api'
import { BookOpen, ChevronRight, ExternalLink, CheckCircle, AlertCircle, Copy, Download } from '@lucide/vue'
import Card from '@/components/ui/Card.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import CardTitle from '@/components/ui/CardTitle.vue'
import CardContent from '@/components/ui/CardContent.vue'
import Button from '@/components/ui/Button.vue'
import Badge from '@/components/ui/Badge.vue'
import LoadingState from '@/components/ui/LoadingState.vue'
import { useToast } from '@/composables/useToast'

const { toast } = useToast()

interface Step {
  title: string
  description: string
  action: string
  element: string
  value?: string
  url?: string
  screenshot_hint?: string
}

interface PlatformGuide {
  platform: string
  name: string
  url: string
  account_creation: Step[]
  work_submission: Step[]
  file_formats: Record<string, string>
  tips: string[]
  common_errors: Array<{ error: string; solution: string }>
}

const loading = ref(true)
const error = ref('')
const platforms = ref<string[]>([])
const selectedPlatform = ref<string | null>(null)
const guideType = ref<'account' | 'work'>('account')
const currentGuide = ref<PlatformGuide | null>(null)
const currentSteps = ref<Step[]>([])

onMounted(loadPlatforms)

async function loadPlatforms() {
  loading.value = true
  try {
    const res = await api.get('/platform-guides/') as any
    platforms.value = res.platforms || []
  } catch (e: any) {
    error.value = e?.message || 'Error al cargar plataformas'
  } finally {
    loading.value = false
  }
}

async function loadGuide(platform: string, type: 'account' | 'work' = 'account') {
  selectedPlatform.value = platform
  guideType.value = type
  currentGuide.value = null
  currentSteps.value = []

  try {
    const res = await api.get(`/platform-guides/${platform}?guide_type=${type}`) as any
    currentGuide.value = {
      platform,
      name: platform.charAt(0).toUpperCase() + platform.slice(1),
      url: res.url,
      account_creation: [],
      work_submission: [],
      file_formats: {},
      tips: [],
      common_errors: [],
    }
    // Parse the markdown guide to extract steps
    parseGuide(res.guide)
  } catch (e: any) {
    toast({
      title: 'Error',
      description: e?.message || 'Error al cargar guía',
      variant: 'destructive',
    })
  }
}

function parseGuide(markdown: string) {
  const lines = markdown.split('\n')
  const steps: Step[] = []
  let currentStep: Partial<Step> | null = null

  for (const line of lines) {
    if (line.startsWith('### ')) {
      if (currentStep) {
        steps.push(currentStep as Step)
      }
      currentStep = {
        title: line.replace('### ', ''),
        description: '',
        action: '',
        element: '',
      }
    } else if (currentStep) {
      if (line.startsWith('- Acción:')) {
        currentStep.action = line.replace('- Acción:', '').trim()
      } else if (line.startsWith('- Elemento:')) {
        currentStep.element = line.replace('- Elemento:', '').trim()
      } else if (line.startsWith('- Valor:')) {
        currentStep.value = line.replace('- Valor:', '').trim()
      } else if (line.startsWith('- URL:')) {
        currentStep.url = line.replace('- URL:', '').trim()
      } else if (line.startsWith('- Hint:')) {
        currentStep.screenshot_hint = line.replace('- Hint:', '').trim()
      } else if (line.trim() && !line.startsWith('-')) {
        currentStep.description += line + '\n'
      }
    }
  }

  if (currentStep) {
    steps.push(currentStep as Step)
  }

  currentSteps.value = steps
}

function copyToClipboard(text: string) {
  navigator.clipboard.writeText(text)
  toast({
    title: 'Copiado',
    description: 'Texto copiado al portapapeles',
  })
}

function openUrl(url: string) {
  window.open(url, '_blank')
}
</script>

<template>
  <div class="p-6">
    <div class="mb-6">
      <h1 class="text-3xl font-bold text-white mb-2">Guías de Plataformas</h1>
      <p class="text-gray-400">Instrucciones paso a paso para crear cuentas y subir trabajos</p>
    </div>

    <LoadingState v-if="loading" />
    <div v-else-if="error" class="text-red-400">{{ error }}</div>

    <div v-else>
      <!-- Platform Selection -->
      <div v-if="!selectedPlatform" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <Card
          v-for="platform in platforms"
          :key="platform"
          class="cursor-pointer hover:border-blue-500 transition-colors"
          @click="loadGuide(platform, 'account')"
        >
          <CardContent class="p-4">
            <div class="flex items-center justify-between">
              <div>
                <h3 class="text-lg font-semibold text-white capitalize">{{ platform }}</h3>
                <p class="text-sm text-gray-400">Guía de cuenta y trabajo</p>
              </div>
              <ChevronRight class="text-gray-400" />
            </div>
          </CardContent>
        </Card>
      </div>

      <!-- Guide Display -->
      <div v-else class="space-y-6">
        <!-- Header -->
        <div class="flex items-center justify-between">
          <div>
            <Button
              variant="ghost"
              @click="selectedPlatform = null; currentGuide = null"
              class="mb-4"
            >
              ← Volver a plataformas
            </Button>
            <h2 class="text-2xl font-bold text-white capitalize">{{ selectedPlatform }}</h2>
            <p class="text-gray-400">{{ currentGuide?.url }}</p>
          </div>
          <div class="flex gap-2">
            <Button
              :variant="guideType === 'account' ? 'default' : 'outline'"
              @click="loadGuide(selectedPlatform, 'account')"
            >
              <BookOpen class="w-4 h-4 mr-2" />
              Cuenta
            </Button>
            <Button
              :variant="guideType === 'work' ? 'default' : 'outline'"
              @click="loadGuide(selectedPlatform, 'work')"
            >
              <Upload class="w-4 h-4 mr-2" />
              Subir Trabajo
            </Button>
          </div>
        </div>

        <!-- Steps -->
        <div class="space-y-4">
          <div
            v-for="(step, index) in currentSteps"
            :key="index"
            class="bg-gray-900 border border-gray-800 rounded-lg p-4"
          >
            <div class="flex items-start gap-4">
              <div class="flex-shrink-0 w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-white font-bold">
                {{ index + 1 }}
              </div>
              <div class="flex-1">
                <h3 class="text-lg font-semibold text-white mb-2">{{ step.title }}</h3>
                <p class="text-gray-300 mb-3 whitespace-pre-line">{{ step.description }}</p>

                <div class="flex flex-wrap gap-2 mb-3">
                  <Badge variant="outline">{{ step.action }}</Badge>
                  <Badge variant="outline">{{ step.element }}</Badge>
                  <Badge v-if="step.screenshot_hint" variant="secondary">
                    {{ step.screenshot_hint }}
                  </Badge>
                </div>

                <div v-if="step.value" class="bg-gray-800 rounded p-2 mb-2">
                  <code class="text-sm text-green-400">{{ step.value }}</code>
                  <Button
                    variant="ghost"
                    size="sm"
                    class="ml-2"
                    @click="copyToClipboard(step.value)"
                  >
                    <Copy class="w-4 h-4" />
                  </Button>
                </div>

                <Button
                  v-if="step.url"
                  variant="outline"
                  size="sm"
                  @click="openUrl(step.url)"
                >
                  <ExternalLink class="w-4 h-4 mr-2" />
                  Abrir enlace
                </Button>
              </div>
            </div>
          </div>
        </div>

        <!-- Tips -->
        <Card>
          <CardHeader>
            <CardTitle class="text-white">Tips Importantes</CardTitle>
          </CardHeader>
          <CardContent>
            <ul class="space-y-2">
              <li v-for="(tip, index) in currentGuide?.tips" :key="index" class="flex items-start gap-2 text-gray-300">
                <CheckCircle class="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
                <span>{{ tip }}</span>
              </li>
            </ul>
          </CardContent>
        </Card>

        <!-- Common Errors -->
        <Card>
          <CardHeader>
            <CardTitle class="text-white">Errores Comunes</CardTitle>
          </CardHeader>
          <CardContent>
            <div class="space-y-3">
              <div
                v-for="(error, index) in currentGuide?.common_errors"
                :key="index"
                class="bg-red-900/20 border border-red-800 rounded p-3"
              >
                <div class="flex items-start gap-2">
                  <AlertCircle class="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
                  <div>
                    <p class="font-semibold text-red-400">{{ error.error }}</p>
                    <p class="text-sm text-gray-300">{{ error.solution }}</p>
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  </div>
</template>
