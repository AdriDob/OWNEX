/* ════════════════════════════════════════════════════════════
   useStartupSequence — Cinematic startup timeline
   Controls the 4-phase sequence: loading → splash → transitioning → dashboard.
   Uses framer-motion/dom spring for logo reveal and crossfade.
   ══════════════════════════════════════════════════════════ */

import { animate } from 'motion'
import { type Ref, ref } from 'vue'
import { useReducedMotion } from '@/shared/composables/useReducedMotion'

export type StartupPhase = 'loading' | 'splash' | 'transitioning' | 'dashboard'

const MIN_SPLASH_MS = 1500
const TRANSITION_MS = 700
const LOGO_ENTER_MS = 600
const PRELOAD_TIMEOUT_MS = 4000

export function useStartupSequence() {
  const phase = ref<StartupPhase>('loading')
  const progress = ref(0) // 0-100 — for loading indicator
  const { shouldReduce } = useReducedMotion()

  /** Run the full startup sequence.
   *  @param onReady — async function that preloads critical data
   *  @returns the startup phase (for external waiting) */
  async function run(onReady: () => Promise<unknown>): Promise<StartupPhase> {
    phase.value = 'splash'
    progress.value = 10

    if (shouldReduce()) {
      await onReady()
      phase.value = 'dashboard'
      progress.value = 100
      return phase.value
    }

    // 1. Animate logo entrance (0 → 600ms)
    animate(
      '#logo-reveal',
      { scale: [0.8, 1], opacity: [0, 1] },
      { type: 'spring', stiffness: 120, damping: 14, duration: LOGO_ENTER_MS / 1000 },
    )
    progress.value = 30

    // 2. Preload data while animation plays
    const readyPromise = onReady().then(() => {
      progress.value = 70
    })

    // 3. Wait for minimum splash time OR preload complete (whichever is later)
    const splashTimer = new Promise<void>((resolve) => {
      setTimeout(() => {
        progress.value = 50
        resolve()
      }, MIN_SPLASH_MS)
    })

    // Safety timeout — never splash longer than this
    const safetyTimer = new Promise<void>((resolve) => {
      setTimeout(() => {
        progress.value = 60
        resolve()
      }, PRELOAD_TIMEOUT_MS)
    })

    await Promise.race([readyPromise, safetyTimer])
    await splashTimer // Always respect minimum splash time

    // 4. Transition: splash fade-out + dashboard fade-in
    phase.value = 'transitioning'
    progress.value = 85

    const transitionControl = animate(
      '#splash-layer',
      { opacity: [1, 0] },
      { duration: TRANSITION_MS / 1000, ease: [0.4, 0, 0.2, 1] },
    )

    await transitionControl

    progress.value = 100
    phase.value = 'dashboard'

    return phase.value
  }

  return { phase, progress, run }
}
