/* ════════════════════════════════════════════════════════════
   useReducedMotion — Accessibility motion guard
   Returns boolean flags for reduced-motion and performance mode.
   ══════════════════════════════════════════════════════════ */

import { onMounted, onUnmounted, ref } from 'vue'

export function useReducedMotion() {
  const prefersReducedMotion = ref(false)
  const performanceMode = ref<'high' | 'low'>('high')

  let mq: MediaQueryList | null = null

  function onMqChange(e: MediaQueryListEvent) {
    prefersReducedMotion.value = e.matches
  }

  onMounted(() => {
    mq = window.matchMedia('(prefers-reduced-motion: reduce)')
    prefersReducedMotion.value = mq.matches
    mq.addEventListener('change', onMqChange)

    // Detect low-end hardware
    const memory = (navigator as any).deviceMemory
    const cores = navigator.hardwareConcurrency
    if ((memory && memory <= 4) || (cores && cores <= 4)) {
      performanceMode.value = 'low'
    }
  })

  onUnmounted(() => {
    mq?.removeEventListener('change', onMqChange)
  })

  return {
    prefersReducedMotion,
    performanceMode,
    /** True when animations should be disabled entirely */
    shouldReduce: () => prefersReducedMotion.value || performanceMode.value === 'low',
    /** Returns a duration-friendly value: 0 if reduce, original if not */
    safeDuration: (ms: number) => (prefersReducedMotion.value ? 0 : ms),
  }
}
