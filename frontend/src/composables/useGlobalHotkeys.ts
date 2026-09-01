/**
 * Global hotkeys for zero-friction capture inside the OWNEX webview.
 *
 *   Ctrl+Shift+O (o=r)  →  open Quick Capture
 *   Ctrl+Shift+P (p)    →  show the ONE best action (income next action)
 *
 * True OS-global hotkeys are gated to the Rust/Tauri side (system-tray +
 * global-shortcut plugins); this covers the focused desktop window, which is
 * where the hunter works. Idempotent — call once.
 */

import { onBeforeUnmount, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/lib/api'

export function useGlobalHotkeys() {
  const router = useRouter()

  async function openNextAction() {
    try {
      const next = await api.get<{ title?: string; url?: string | null } | null>('/applications/income-plan')
      const title = next?.title || 'Sin acción pendiente'
      const url = next?.url
      if (url) window.open(url, '_blank')
      else {
        window.dispatchEvent(
          new CustomEvent('ownex:toast', { detail: { message: `Next: ${title}`, level: 'info' } }),
        )
        router.push('/')
      }
    } catch {
      router.push('/')
    }
  }

  function onKeydown(e: KeyboardEvent) {
    if (!(e.ctrlKey || e.metaKey) || !e.shiftKey) return
    const k = e.key.toLowerCase()
    if (k === 'o' || k === 'r') {
      e.preventDefault()
      router.push('/quick-capture')
    } else if (k === 'p') {
      e.preventDefault()
      void openNextAction()
    } else if (k === 'u') {
      e.preventDefault()
      router.push('/copilot/computer-use')
    }
  }

  onMounted(() => document.addEventListener('keydown', onKeydown))
  onBeforeUnmount(() => document.removeEventListener('keydown', onKeydown))

  return { openQuickCapture: () => router.push('/quick-capture'), openNextAction }
}