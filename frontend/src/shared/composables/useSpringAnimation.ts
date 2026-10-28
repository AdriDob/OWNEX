/* ════════════════════════════════════════════════════════════
   useSpringAnimation — Wraps Motion (framer-motion/dom) for Vue components
   Provides spring-based animations with cancel support.
   ══════════════════════════════════════════════════════════ */

import { animate } from 'motion'
import { onUnmounted, type Ref, unref } from 'vue'
import { useReducedMotion } from './useReducedMotion'

export type AnimationTarget = string | Element | HTMLElement | Ref<HTMLElement | null | undefined>

interface SpringAnimOptions {
  stiffness?: number
  damping?: number
  mass?: number
  duration?: number
  delay?: number
}

interface AnimControls {
  cancel: () => void
  then: (onResolve: VoidFunction) => Promise<void>
  pause: () => void
  play: () => void
}

function resolveTarget(target: AnimationTarget): Element | null {
  const el = unref(target)
  if (typeof el === 'string') return document.querySelector(el)
  return el as Element | null
}

const noopControls: AnimControls = {
  cancel: () => {},
  then: (fn: VoidFunction) => Promise.resolve().then(fn),
  pause: () => {},
  play: () => {},
}

/**
 * Spring-based animation with automatic cleanup and reduced-motion respect.
 * Returns controls so you can pause/resume/cancel.
 */
export function useSpringAnimation() {
  const { shouldReduce } = useReducedMotion()
  const controls: AnimControls[] = []

  onUnmounted(() => {
    controls.forEach((c) => c.cancel?.())
    controls.length = 0
  })

  function animateSpring(
    target: AnimationTarget,
    keyframes: Record<string, any>,
    opts?: SpringAnimOptions,
  ): AnimControls {
    const el = resolveTarget(target)
    if (!el) {
      console.warn('[useSpringAnimation] target not found:', target)
      return noopControls
    }

    // Skip animation entirely when reduced
    if (shouldReduce()) {
      Object.assign((el as HTMLElement).style, {
        ...Object.fromEntries(
          Object.entries(keyframes).map(([k, v]) => (Array.isArray(v) ? [k, v[v.length - 1]] : [k, v])),
        ),
      })
      return noopControls
    }

    const { stiffness = 120, damping = 14, mass, duration, delay } = opts ?? {}

    const control = animate(el, keyframes, {
      type: 'spring',
      stiffness,
      damping,
      ...(mass !== undefined ? { mass } : {}),
      ...(duration !== undefined ? { duration } : {}),
      ...(delay !== undefined ? { delay } : {}),
    })
    controls.push(control)
    return control
  }

  return { animateSpring, controls }
}
