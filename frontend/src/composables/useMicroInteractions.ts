import { useUiStore, type MicroEntity } from '@/stores/ui'
import type { EntityType } from '@/composables/useContextMenu'
import { useToast } from '@/composables/useToast'
import { api } from '@/lib/api'

export function useMicroInteractions() {
  const store = useUiStore()
  const { toast } = useToast()

  function inspect(entity: MicroEntity, type: EntityType) {
    store.openInspector(entity, type)
  }

  async function inspectByType(id: string, type: EntityType) {
    store.setLoading('inspect', true)
    try {
      const plural = type.endsWith('s') ? type : `${type}s`
      const path = `/${plural}/${id}`
      const entity = await api.get<any>(path)
      store.openInspector(entity as MicroEntity, type)
    } catch (e: any) {
      toast.error(e.message || 'Error al cargar entidad')
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
    store.openCompare(entity, entity.type as EntityType || 'finding')
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
    try {
      await api.post('/micro/batch', { ids, action })
      toast.success(`Acción "${action}" ejecutada`)
    } catch (e: any) {
      toast.error(e.message || 'Error en acción batch')
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

  async function copyJSON(obj: any): Promise<void> {
    await copyToClipboard(JSON.stringify(obj, null, 2), 'JSON')
  }

  async function copyId(id: string): Promise<void> {
    await copyToClipboard(String(id), 'ID')
  }

  async function quickSync(): Promise<any> {
    store.setLoading('sync', true)
    try {
      const result = await api.post<any>('/micro/quick-sync-all')
      toast.success('Sincronización completada')
      return result
    } catch (e: any) {
      toast.error(e.message || 'Error al sincronizar')
      throw e
    } finally {
      store.setLoading('sync', false)
    }
  }

  async function syncSource(sourceId: string): Promise<any> {
    store.setLoading('sync', true)
    try {
      const result = await api.post<any>(`/micro/sync-source/${sourceId}`)
      toast.success('Fuente sincronizada')
      return result
    } catch (e: any) {
      toast.error(e.message || 'Error al sincronizar fuente')
      throw e
    } finally {
      store.setLoading('sync', false)
    }
  }

  async function getDashboardState(): Promise<any> {
    return api.get<any>('/micro/dashboard-state')
  }

  async function getSyncHealth(): Promise<any> {
    return api.get<any>('/micro/sync-health')
  }

  async function getAnomalies(): Promise<any> {
    return api.get<any>('/micro/anomalies')
  }

  async function getPendingActions(): Promise<any> {
    return api.get<any>('/micro/pending-actions')
  }

  async function getRealExposure(): Promise<any> {
    return api.get<any>('/micro/real-exposure')
  }

  return {
    inspect, inspectByType,
    preview, hidePreview,
    showTimeline,
    startCompare, addToCompare, clearCompare,
    toggleSelect, selectAll, clearSelection, getSelection, batchAction,
    openMoreInfo, closeMoreInfo,
    copyToClipboard, copyJSON, copyId,
    quickSync, syncSource,
    getDashboardState, getSyncHealth, getAnomalies, getPendingActions, getRealExposure,
  }
}
