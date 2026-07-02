import { ref, onMounted, onUnmounted, type Ref } from 'vue'

export function useIntersectionAnimation(
  options?: IntersectionObserverInit & { once?: boolean }
) {
  const { once = true, ...observerOptions } = options || {}
  const visible = ref(false)
  const elRef = ref<HTMLElement | null>(null)
  let observer: IntersectionObserver | null = null

  onMounted(() => {
    if (!elRef.value) return
    observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        visible.value = true
        if (once) observer?.unobserve(entry.target)
      } else if (!once) {
        visible.value = false
      }
    }, { threshold: 0.1, ...observerOptions })
    observer.observe(elRef.value)
  })

  onUnmounted(() => {
    observer?.disconnect()
  })

  return { visible, elRef }
}
