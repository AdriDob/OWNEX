import type { EntityType } from '@/composables/useContextMenu'
import { useToast } from '@/composables/useToast'
import { ApiError, api } from '@/lib/api'
import { type MicroEntity, useUIStore } from '@/stores/ui'

/** Respuestas de /micro/* — shapes tolerantes (el backend puede omitir campos). */
interface MicroOpResult {
  synced?: number
  exported?: number
  deleted?: number
  tagged?: number
  status?: string
  [key: string]: unknown
}
interface MicroDashboardState {
  sources?: Array<Record<string, unknown>>
  totals?: Record<string, number>
  [key: string]: unknown
}
interface MicroSyncHealth {
  healthy?: boolean
  sources?: Array<{ id: string; ok: boolean }>
  [key: string]: unknown
}
interface MicroAnomaly {
  id: string
  kind: string
  detail?: string
  [key: string]: unknown
}
interface MicroPendingAction {
  id: string
  label: string
  action: string
  [key: string]: unknown
}
interface MicroExposure {
  exposed_endpoints?: number
  critical?: number
  [key: string]: unknown
}

function errMessage(e: unknown, fallback: string): string {
  if (e instanceof ApiError) return e.message
  if (e instanceof Error && e.message) return e.message
  return fallback
}

export function useMicroInteractions() {
  const store = useUIStore()
  const { toast } = useToast()

  function inspect(entity: MicroEntity, type: EntityType) {
    store.openInspector(entity, type)
  }

  async function inspectByType(id: string, type: EntityType) {
    store.setLoading('inspect', true)
    try {
      const plural = type.endsWith('s') ? type : `${type}s`
      const path = `/${plural}/${id}`
      const entity = await api.get<Record<string, unknown>>(path)
      store.openInspector(entity as MicroEntity, type)
    } catch (e: unknown) {
      toast.error(errMessage(e, 'Error al cargar entidad'))
    } finally {
      store.setLoading('inspect', false)
    }
  }

  function preview(entity: MicroEntity, event: MouseEvent) {
    store.showMiniPreview(entity, event.clientX, event.clientY)
  }

  function hidePreview() {
    store.hideMiniPreview()
  }

  function showTimeline(entityId: string) {
    store.openTimeline(entityId)
  }

  function startCompare(entity: MicroEntity) {
    store.openCompare(entity, (entity.type as EntityType) || 'finding')
  }

  function addToCompare(entity: MicroEntity) {
    store.addToCompare(entity)
  }

  function clearCompare() {
    store.clearCompare()
  }

  function toggleSelect(id: string) {
    store.toggleSelection(id)
  }

  function selectAll(ids: string[]) {
    store.selectAll(ids)
  }

  function clearSelection() {
    store.clearSelection()
  }

  function getSelection(): string[] {
    return [...store.selectedIds]
  }

  async function batchAction(action: string): Promise<void> {
    const ids = getSelection()
    if (ids.length === 0) return
    // El backend expone batch/{export|sync|delete|tag} (no un /batch genérico).
    const supported = ['export', 'sync', 'delete', 'tag'] as const
    type Supported = (typeof supported)[number]
    try {
      if (!(supported as readonly string[]).includes(action)) {
        toast.error(`Acción batch no soportada: ${action}`)
        return
      }
      await api.post(`/micro/batch/${action as Supported}`, {
        ids,
        // El catálogo micro opera sobre findings; ajustar si se agregan tipos.
        type: 'finding',
        ...(action === 'export' ? { format: 'json' } : {}),
        ...(action === 'tag' ? { tag: '' } : {}),
      })
      toast.success(`Acción "${action}" ejecutada`)
    } catch (e: unknown) {
      toast.error(errMessage(e, 'Error en acción batch'))
    }
  }

  function openMoreInfo(entity: MicroEntity, type: EntityType) {
    store.openMoreInfo(entity, type)
  }

  function closeMoreInfo() {
    store.closeMoreInfo()
  }

  async function copyToClipboard(text: string, label?: string): Promise<void> {
    try {
      await navigator.clipboard.writeText(text)
      toast.success(label ? `${label} copiado` : 'Copiado')
    } catch {
      toast.error('Error al copiar')
    }
  }

  async function copyJSON(obj: unknown): Promise<void> {
    await copyToClipboard(JSON.stringify(obj, null, 2), 'JSON')
  }

  async function copyId(id: string): Promise<void> {
    await copyToClipboard(String(id), 'ID')
  }

  async function quickSync(): Promise<MicroOpResult> {
    store.setLoading('sync', true)
    try {
      const result = await api.post<MicroOpResult>('/micro/quick-sync-all')
      toast.success('Sincronización completada')
      return result
    } catch (e: unknown) {
      toast.error(errMessage(e, 'Error al sincronizar'))
      throw e
    } finally {
      store.setLoading('sync', false)
    }
  }

  async function syncSource(sourceId: string): Promise<MicroOpResult> {
    store.setLoading('sync', true)
    try {
      const result = await api.post<MicroOpResult>(`/micro/sync-source/${sourceId}`)
      toast.success('Fuente sincronizada')
      return result
    } catch (e: unknown) {
      toast.error(errMessage(e, 'Error al sincronizar fuente'))
      throw e
    } finally {
      store.setLoading('sync', false)
    }
  }

  async function getDashboardState(): Promise<MicroDashboardState> {
    return api.get<MicroDashboardState>('/micro/dashboard-state')
  }

  async function getSyncHealth(): Promise<MicroSyncHealth> {
    return api.get<MicroSyncHealth>('/micro/sync-health')
  }

  async function getAnomalies(): Promise<MicroAnomaly[]> {
    return api.get<MicroAnomaly[]>('/micro/anomalies')
  }

  async function getPendingActions(): Promise<MicroPendingAction[]> {
    return api.get<MicroPendingAction[]>('/micro/pending-actions')
  }

  async function getRealExposure(): Promise<MicroExposure> {
    return api.get<MicroExposure>('/micro/real-exposure')
  }

  return {
    inspect,
    inspectByType,
    preview,
    hidePreview,
    showTimeline,
    startCompare,
    addToCompare,
    clearCompare,
    toggleSelect,
    selectAll,
    clearSelection,
    getSelection,
    batchAction,
    openMoreInfo,
    closeMoreInfo,
    copyToClipboard,
    copyJSON,
    copyId,
    quickSync,
    syncSource,
    getDashboardState,
    getSyncHealth,
    getAnomalies,
    getPendingActions,
    getRealExposure,
  }
}
