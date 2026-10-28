import { ref, watch } from 'vue'
import { useSettingsStore } from '@/stores/settings'

export interface AssistantHint {
  id: string
  title: string
  message: string
  page?: string
  dismissable?: boolean
}

const hints = ref<AssistantHint[]>([])
const bubbleMessage = ref<string | null>(null)
const spotlightFeature = ref<string | null>(null)
const dismissals = ref<Set<string>>(new Set())

const loaded = ref(false)

export function useAssistant() {
  const settings = useSettingsStore()

  function loadDefaults() {
    if (loaded.value) return
    loaded.value = true
    const defaultHints: AssistantHint[] = [
      {
        id: 'hint-mission',
        title: 'Mission Control',
        message: 'Acá están tus prioridades del día. OWNEX recomienda la próxima acción según los datos disponibles.',
        page: 'mission-control',
      },
      {
        id: 'hint-aegis',
        title: 'AEGIS',
        message: 'Los scans se ejecutan secuencialmente. Revisá los findings después de cada ejecución.',
        page: 'aegis',
      },
      {
        id: 'hint-health',
        title: 'Health Center',
        message: 'El score de salud se calcula sobre checks de sistema, integraciones y extensiones.',
        page: 'health-center',
      },
      {
        id: 'hint-workflows',
        title: 'Workflows',
        message: 'Las plantillas YAML definen pipelines automatizados. Podés ejecutarlas con un solo clic.',
        page: 'workflows',
      },
    ]
    hints.value = defaultHints.filter((h) => !dismissals.value.has(h.id))
  }

  function dismissHint(id: string) {
    dismissals.value.add(id)
    hints.value = hints.value.filter((h) => h.id !== id)
  }

  function showBubble(message: string, durationMs = 8000) {
    bubbleMessage.value = message
    if (durationMs > 0) {
      setTimeout(() => {
        bubbleMessage.value = null
      }, durationMs)
    }
  }

  function showSpotlight(feature: string) {
    spotlightFeature.value = feature
  }

  function hideSpotlight() {
    spotlightFeature.value = null
  }

  function getHintsForPage(page: string): AssistantHint[] {
    if (!settings.data.assistant?.hints) return []
    return hints.value.filter((h) => h.page === page)
  }

  const assistantEnabled = ref(settings.data.assistant?.enabled ?? true)
  const hintsEnabled = ref(settings.data.assistant?.hints ?? true)
  const bubbleEnabled = ref(settings.data.assistant?.bubble ?? true)
  const spotlightEnabled = ref(settings.data.assistant?.spotlight ?? false)

  watch(
    () => settings.data.assistant,
    (a) => {
      if (!a) return
      assistantEnabled.value = a.enabled ?? true
      hintsEnabled.value = a.hints ?? true
      bubbleEnabled.value = a.bubble ?? true
      spotlightEnabled.value = a.spotlight ?? false
    },
    { deep: true },
  )

  return {
    hints,
    bubbleMessage,
    spotlightFeature,
    dismissHint,
    showBubble,
    showSpotlight,
    hideSpotlight,
    getHintsForPage,
    loadDefaults,
    assistantEnabled,
    hintsEnabled,
    bubbleEnabled,
    spotlightEnabled,
  }
}
