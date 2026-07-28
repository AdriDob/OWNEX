/* ════════════════════════════════════════════════════════════
   useAnimatedCounter — Spring-based count-up numbers
   Animates from 0 (or a start value) to the target with spring easing.
   Triggers on IntersectionObserver and re-animates when value changes.
   ══════════════════════════════════════════════════════════ */

import { ref, watch, onMounted, type Ref } from 'vue'
import { animate } from 'motion'
import { useReducedMotion } from './useReducedMotion'

interface CounterOptions {
  /** Starting value */
  from?: number
  /** Duration in seconds (ignored when spring is true) */
  duration?: number
  /** Number of decimal places */
  decimals?: number
  /** Use spring physics (smoother) */
  spring?: boolean
  /** Suffix text (e.g. "%", " GB") */
  suffix?: string
  /** Prefix text (e.g. "$") */
  prefix?: string
}

export function useAnimatedCounter(
  displayRef: Ref<HTMLElement | null | undefined>,
  valueRef: Ref<number>,
  options: CounterOptions = {},
) {
  const {
    from = 0,
    decimals = 0,
    duration = 0.6,
    spring: useSpring = true,
    suffix = '',
    prefix = '',
  } = options

  const { shouldReduce } = useReducedMotion()
  const displayedValue = ref(from)
  const isAnimating = ref(false)

  function formatValue(val: number): string {
    return `${prefix}${val.toFixed(decimals)}${suffix}`
  }

  function animateTo(target: number) {
    const el = displayRef.value
    if (!el) {
      displayedValue.value = target
      el!.textContent = formatValue(target)
      return
    }

    isAnimating.value = true

    if (shouldReduce()) {
      el.textContent = formatValue(target)
      displayedValue.value = target
      isAnimating.value = false
      return
    }

    // Animate the value binding and update DOM each frame
    const controls = animate(
      () => displayedValue.value,
      target,
      {
        ...(useSpring
          ? { type: 'spring' as const, stiffness: 100, damping: 18 }
          : { duration }
        ),
        onUpdate: (latest: number) => {
          displayedValue.value = latest
          el.textContent = formatValue(latest)
        },
      },
    )

    controls.then(() => {
      displayedValue.value = target
      isAnimating.value = false
    })
  }

  watch(valueRef, (newVal) => {
    animateTo(newVal)
  })

  onMounted(() => {
    if (valueRef.value !== from) {
      animateTo(valueRef.value)
    }
  })

  return { displayedValue, isAnimating, animateTo, formatValue }
}
