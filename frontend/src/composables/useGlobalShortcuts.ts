import { onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAccessibilityStore } from '@/stores/accessibility'

export type ShortcutAction =
  | { type: 'navigate'; path: string }
  | { type: 'command' }
  | { type: 'toggle'; target: 'copilot' | 'sidebar' | 'notifications' }
  | { type: 'action'; action: string }

export interface ShortcutBinding {
  key: string
  ctrl?: boolean
  meta?: boolean
  shift?: boolean
  alt?: boolean
  description: string
  action: ShortcutAction
}

const DEFAULT_SHORTCUTS: ShortcutBinding[] = [
  { key: 'k', meta: true, description: 'Paleta de comandos', action: { type: 'command' } },
  { key: 'b', meta: true, description: 'Toggle copiloto', action: { type: 'toggle', target: 'copilot' } },
  { key: '\\', meta: true, description: 'Toggle sidebar', action: { type: 'toggle', target: 'sidebar' } },
  { key: 'n', meta: true, description: 'Notificaciones', action: { type: 'toggle', target: 'notifications' } },
  { key: '1', meta: true, description: 'Dashboard', action: { type: 'navigate', path: '/' } },
  { key: '2', meta: true, description: 'Money Radar', action: { type: 'navigate', path: '/money-radar' } },
  { key: '3', meta: true, description: 'Hallazgos', action: { type: 'navigate', path: '/findings' } },
  { key: '4', meta: true, description: 'Reportes', action: { type: 'navigate', path: '/reports' } },
  { key: '5', meta: true, description: 'Radar', action: { type: 'navigate', path: '/radar' } },
  { key: '6', meta: true, description: 'Billeteras', action: { type: 'navigate', path: '/wallets' } },
  { key: 'r', meta: true, shift: true, description: 'Modo daily', action: { type: 'navigate', path: '/daily' } },
  { key: 'Escape', description: 'Cerrar modales / inspector / preview', action: { type: 'action', action: 'escape' } },
  { key: 's', ctrl: true, shift: true, description: 'Sync rápido', action: { type: 'action', action: 'quick-sync' } },
  { key: 'ArrowLeft', alt: true, description: 'Navegar atrás', action: { type: 'action', action: 'navigate-back' } },
  { key: 'ArrowRight', alt: true, description: 'Navegar adelante', action: { type: 'action', action: 'navigate-forward' } },
  { key: '/', ctrl: true, description: 'Atajos de teclado', action: { type: 'action', action: 'show-shortcuts' } },
]

export interface Callbacks {
  onCommand?: () => void
  onToggleCopilot?: () => void
  onToggleSidebar?: () => void
  onToggleNotifications?: () => void
  onCloseModal?: () => void
  onCloseInspector?: () => void
  onHideMiniPreview?: () => void
  onQuickSync?: () => void
  onNavigateBack?: () => void
  onNavigateForward?: () => void
  onShowShortcuts?: () => void
  custom?: Record<string, () => void>
}

export function useGlobalShortcuts(callbacks: Callbacks) {
  const router = useRouter()
  const a11y = useAccessibilityStore()

  function handleKeydown(e: KeyboardEvent) {
    if (!a11y.state.keyboardNavigation) return
    if (isEditingElement(e.target)) return

    const shortcut = DEFAULT_SHORTCUTS.find(s => {
      const ctrl = s.ctrl ? e.ctrlKey : !s.ctrl
      const meta = s.meta ? e.metaKey : !s.meta
      const shift = s.shift ? e.shiftKey : !s.shift
      const alt = s.alt ? e.altKey : !s.alt
      const key = e.key.toLowerCase() === s.key.toLowerCase()
      return key && ctrl && meta && shift && alt
    })

    if (!shortcut) return
    e.preventDefault()

    const { action } = shortcut
    switch (action.type) {
      case 'navigate':
        router.push(action.path)
        break
      case 'command':
        callbacks.onCommand?.()
        break
      case 'toggle':
        switch (action.target) {
          case 'copilot': callbacks.onToggleCopilot?.(); break
          case 'sidebar': callbacks.onToggleSidebar?.(); break
          case 'notifications': callbacks.onToggleNotifications?.(); break
        }
        break
      case 'action':
        if (action.action === 'close-modal' || action.action === 'escape') {
          callbacks.onCloseModal?.()
          callbacks.onCloseInspector?.()
          callbacks.onHideMiniPreview?.()
        }
        if (action.action === 'navigate-back') callbacks.onNavigateBack?.()
        if (action.action === 'navigate-forward') callbacks.onNavigateForward?.()
        if (action.action === 'quick-sync') callbacks.onQuickSync?.()
        if (action.action === 'show-shortcuts') callbacks.onShowShortcuts?.()
        callbacks.custom?.[action.action]?.()
        break
    }
  }

  onMounted(() => window.addEventListener('keydown', handleKeydown))
  onUnmounted(() => window.removeEventListener('keydown', handleKeydown))

  return { shortcuts: DEFAULT_SHORTCUTS }
}

function isEditingElement(target: EventTarget | null): boolean {
  if (!target || !(target instanceof HTMLElement)) return false
  const tag = target.tagName.toLowerCase()
  return tag === 'input' || tag === 'textarea' || tag === 'select' || target.isContentEditable
}
