import { computed, ref } from 'vue'

export type GuidedMode = 'guided' | 'assisted' | 'autonomous' | 'expert'

interface ModeInfo {
  title: string
  subtitle: string
  desc: string
  features: string[]
}

const MODE_INFO: Record<GuidedMode, ModeInfo> = {
  guided: {
    title: 'Modo Guiado — Máxima Asistencia',
    subtitle: 'OWNEX te explica todo paso a paso. Ideal para empezar sin experiencia.',
    desc: 'Explicación completa de cada acción',
    features: [
      'Objetivo y contexto explicados',
      'Qué hace OWNEX y qué haces tú',
      'Resultado esperado claro',
      'Confirmación en cada paso',
    ],
  },
  assisted: {
    title: 'Modo Asistido — Balance Automatización/Control',
    subtitle: 'OWNEX automatiza lo repetitivo y te pide confirmación en decisiones clave.',
    desc: 'Automatiza lo repetitivo, pregunta en decisiones',
    features: [
      'Automatiza tareas repetitivas',
      'Explica decisiones importantes',
      'Pide confirmación antes de actuar',
      'Tú decides los puntos críticos',
    ],
  },
  autonomous: {
    title: 'Modo Autónomo — Máxima Productividad',
    subtitle: 'OWNEX ejecuta flujos aprobados y solo pide confirmación en acciones críticas.',
    desc: 'Ejecuta flujos completos, reporta resultados',
    features: [
      'Ejecuta workflows completos',
      'Prepara materiales automáticamente',
      'Solo confirma acciones críticas',
      'Reporta resultados al finalizar',
    ],
  },
  expert: {
    title: 'Modo Experto — Transparencia Técnica Total',
    subtitle: 'Logs, arquitectura, APIs, decisiones, métricas — todo visible.',
    desc: 'Logs, arquitectura, APIs, decisiones, métricas',
    features: [
      'Logs y arquitectura visibles',
      'APIs y decisiones expuestas',
      'Métricas de rendimiento',
      'Errores y optimizaciones',
    ],
  },
}

const currentMode = ref<GuidedMode>('guided')

export function useGuidedMode() {
  const setMode = (mode: GuidedMode) => {
    currentMode.value = mode
    localStorage.setItem('ownex:guidedMode', mode)
  }

  const initMode = () => {
    const stored = localStorage.getItem('ownex:guidedMode') as GuidedMode | null
    if (stored && ['guided', 'assisted', 'autonomous', 'expert'].includes(stored)) {
      currentMode.value = stored
    }
  }

  const modeDescriptions = computed(() => MODE_INFO)

  return {
    currentMode,
    setMode,
    initMode,
    modeDescriptions,
  }
}
