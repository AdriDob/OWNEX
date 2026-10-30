/* ════════════════════════════════════════════════════════════
   useInViewport — Triggers when element enters viewport
   Uses IntersectionObserver with remove-once semantics.
   ══════════════════════════════════════════════════════════ */

import { onMounted, onUnmounted, type Ref, ref } from 'vue'

interface UseInViewportOptions {
  threshold?: number
  rootMargin?: string
  /** If true, unobserve after first intersection */
  once?: boolean
}

export function useInViewport(targetRef: Ref<HTMLElement | null | undefined>, options: UseInViewportOptions = {}) {
  const isIntersecting = ref(false)
  const entry = ref<IntersectionObserverEntry | null>(null)
  let observer: IntersectionObserver | null = null

  onMounted(() => {
    const el = targetRef.value
    if (!el) return

    observer = new IntersectionObserver(
      ([e]) => {
        isIntersecting.value = e.isIntersecting
        entry.value = e
        if (e.isIntersecting && options.once) {
          observer?.unobserve(el)
        }
      },
      {
        threshold: options.threshold ?? 0.1,
        rootMargin: options.rootMargin ?? '0px',
      },
    )

    observer.observe(el)
  })

  onUnmounted(() => {
    observer?.disconnect()
  })

  return { isIntersecting, entry }
}
