import { ref, type Ref } from 'vue'

export type EntityType =
  | 'target' | 'program' | 'endpoint' | 'finding'
  | 'report' | 'session' | 'wallet' | 'prediction'

export interface ContextAction {
  id: string
  label: string
  icon?: string
  shortcut?: string
  danger?: boolean
  separator?: boolean
  disabled?: boolean
  action: (payload: any) => void
}

export interface ContextMenuState {
  visible: boolean
  x: number
  y: number
  entityType: EntityType
  entity: any
  actions: ContextAction[]
}

const menuState = ref<ContextMenuState>({
  visible: false,
  x: 0,
  y: 0,
  entityType: 'finding',
  entity: null,
  actions: [],
})

export function useContextMenu() {
  function open(event: MouseEvent, entityType: EntityType, entity: any, actions: ContextAction[]) {
    event.preventDefault()
    event.stopPropagation()

    const x = Math.min(event.clientX, window.innerWidth - 240)
    const y = Math.min(event.clientY, window.innerHeight - actions.length * 36 - 16)

    menuState.value = {
      visible: true,
      x,
      y,
      entityType,
      entity,
      actions,
    }
  }

  function close() {
    menuState.value.visible = false
  }

  return { menuState, open, close }
}

export function useEntityActions(entityType: EntityType) {
  function coreActions(entity: any, callbacks: Record<string, (e: any) => void>): ContextAction[] {
    const actions: ContextAction[] = []

    if (entity?.id) {
      if (entityType === 'program') {
        actions.push({ id: 'view-plan', label: 'Ver plan de misión', action: () => callbacks.viewPlan?.(entity) })
        actions.push({ id: 'estimate-payout', label: 'Estimar payout', action: () => callbacks.estimatePayout?.(entity) })
      }
      if (entityType === 'finding') {
        actions.push({ id: 'validate', label: 'Validar vulnerabilidad', action: () => callbacks.validate?.(entity) })
        actions.push({ id: 'generate-report', label: 'Generar reporte', action: () => callbacks.generateReport?.(entity) })
        actions.push({ id: 'check-duplicate', label: 'Verificar duplicado', action: () => callbacks.checkDuplicate?.(entity) })
        actions.push({ id: 'estimate-payout', label: 'Estimar payout', action: () => callbacks.estimatePayout?.(entity) })
      }
      if (entityType === 'report') {
        actions.push({ id: 'optimize', label: 'Optimizar reporte', action: () => callbacks.optimize?.(entity) })
        actions.push({ id: 'check-acceptance', label: 'Probabilidad de aceptación', action: () => callbacks.checkAcceptance?.(entity) })
        actions.push({ id: 'submit-simulation', label: 'Simular envío', action: () => callbacks.submitSimulation?.(entity) })
      }
      if (entityType === 'endpoint') {
        actions.push({ id: 'analyze', label: 'Analizar endpoint', action: () => callbacks.analyze?.(entity) })
        actions.push({ id: 'scan-surface', label: 'Escaneo rápido', action: () => callbacks.scanSurface?.(entity) })
      }
      if (entityType === 'session') {
        actions.push({ id: 'view-roi', label: 'Ver ROI de sesión', action: () => callbacks.viewROI?.(entity) })
      }
      if (entityType === 'prediction') {
        actions.push({ id: 'compare', label: 'Comparar con reales', action: () => callbacks.compare?.(entity) })
      }
    }

    actions.push({ id: 'separator-1', label: '', separator: true, action: () => {} })

    if (entity?.id) {
      actions.push({ id: 'copy-id', label: `Copiar ID (${entity.id})`, action: () => copy(String(entity.id)) })
    }
    if (entity?.url) {
      actions.push({ id: 'copy-url', label: 'Copiar URL', action: () => copy(entity.url) })
    }
    if (entityType === 'finding' && entity?.payload) {
      actions.push({ id: 'copy-payload', label: 'Copiar payload', action: () => copy(entity.payload) })
    }

    actions.push({ id: 'separator-2', label: '', separator: true, action: () => {} })

    actions.push({ id: 'add-queue', label: 'Agregar a cola de investigación', action: () => callbacks.addToQueue?.(entity) })
    actions.push({ id: 'mark-priority', label: 'Marcar como prioritario', action: () => callbacks.markPriority?.(entity) })
    actions.push({ id: 'mark-ignore', label: 'Ignorar', danger: true, action: () => callbacks.markIgnore?.(entity) })

    return actions
  }

  return { coreActions }
}

async function copy(text: string) {
  try {
    await navigator.clipboard.writeText(text)
  } catch { /* fallback */ }
}

// Global click handler to close context menu
if (typeof window !== 'undefined') {
  window.addEventListener('click', () => {
    const state = document.querySelector('[data-context-menu-visible]')
    if (state) {
      const evt = new CustomEvent('close-context-menu')
      window.dispatchEvent(evt)
    }
  })
  window.addEventListener('contextmenu', () => {
    const evt = new CustomEvent('close-context-menu')
    window.dispatchEvent(evt)
  })
}
