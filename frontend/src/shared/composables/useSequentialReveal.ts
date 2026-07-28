/* ════════════════════════════════════════════════════════════
   useSequentialReveal — Staggered entrance animations
   Animates children of a container with configurable delay.
   Uses IntersectionObserver to trigger only when visible.
   ══════════════════════════════════════════════════════════ */

import { ref, onMounted, onUnmounted, type Ref } from 'vue'
import { animate } from 'motion'
import { useReducedMotion } from './useReducedMotion'

interface RevealOptions {
  /** Stagger delay between each child in ms */
  stagger?: number
  /** Delay before the first animation starts (ms) */
  initialDelay?: number
  /** Duration of each animation (s) */
  duration?: number
  /** List of CSS selectors to exclude from staggering */
  exclude?: string[]
  /** IntersectionObserver threshold */
  threshold?: number
}

export function useSequentialReveal(options: RevealOptions = {}) {
  const {
    stagger = 80,
    initialDelay = 0,
    duration = 0.5,
    exclude = [],
    threshold = 0.05,
  } = options

  const { shouldReduce } = useReducedMotion()
  const containerRef = ref<HTMLElement | null>(null)
  let observer: IntersectionObserver | null = null
  let revealed = false

  function reveal() {
    if (revealed || !containerRef.value) return
    revealed = true

    const children = Array.from(containerRef.value.children).filter(
      child => !exclude.some(sel => (child as HTMLElement).matches?.(sel)),
    )

    if (shouldReduce()) {
      children.forEach(child => {
        (child as HTMLElement).style.opacity = '1'
        ;(child as HTMLElement).style.transform = 'none'
      })
      return
    }

    children.forEach((child, i) => {
      const el = child as HTMLElement
      el.style.opacity = '0'
      el.style.transform = 'translateY(24px)'

      animate(el, {
        opacity: [0, 1],
        transform: ['translateY(24px) scale(0.97)', 'translateY(0) scale(1)'],
      }, {
        delay: (initialDelay + i * stagger) / 1000,
        duration,
        type: 'spring',
        stiffness: 100,
        damping: 20,
      })
    })
  }

  onMounted(() => {
    if (!containerRef.value) return

    observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          reveal()
          observer?.unobserve(entry.target)
        }
      },
      { threshold },
    )

    observer.observe(containerRef.value)
  })

  onUnmounted(() => {
    observer?.disconnect()
  })

  return { containerRef, reveal }
}
