import { type ComputedRef, computed, type Ref } from 'vue'
import { useToast } from '@/composables/useToast'
import { api } from '@/lib/api'
import { type MicroEntity, useUIStore } from '@/stores/ui'

export function useMultiSelect() {
  const store = useUIStore()
  const { toast } = useToast()

  const selected = computed<Set<string>>(() => new Set(store.selectedIds))

  function isSelected(id: string): boolean {
    return store.selectedIds.includes(id)
  }

  function toggle(id: string): void {
    store.toggleSelection(id)
  }

  function selectAll(ids: string[]): void {
    store.selectAll(ids)
  }

  function clear(): void {
    store.clearSelection()
  }

  const count: ComputedRef<number> = computed(() => store.selectionCount)
  const isEmpty: ComputedRef<boolean> = computed(() => store.selectedIds.length === 0)

  async function batchExport(): Promise<void> {
    if (isEmpty.value) return
    try {
      await api.post('/micro/batch/export', { ids: store.selectedIds })
      toast.success('Exportación iniciada')
    } catch (e: any) {
      toast.error(e.message || 'Error en exportación batch')
    }
  }

  async function batchSync(): Promise<void> {
    if (isEmpty.value) return
    try {
      await api.post('/micro/batch/sync', { ids: store.selectedIds })
      toast.success('Sincronización batch completada')
    } catch (e: any) {
      toast.error(e.message || 'Error en sincronización batch')
    }
  }

  async function batchDelete(): Promise<void> {
    if (isEmpty.value) return
    try {
      await api.post('/micro/batch/delete', { ids: store.selectedIds })
      store.clearSelection()
      toast.success('Elementos eliminados')
    } catch (e: any) {
      toast.error(e.message || 'Error al eliminar')
    }
  }

  async function batchTag(tag: string): Promise<void> {
    if (isEmpty.value) return
    try {
      await api.post('/micro/batch/tag', { ids: store.selectedIds, tag })
      toast.success(`Tag "${tag}" aplicado`)
    } catch (e: any) {
      toast.error(e.message || 'Error al aplicar tag')
    }
  }

  return {
    selected,
    isSelected,
    toggle,
    selectAll,
    clear,
    count,
    isEmpty,
    batchExport,
    batchSync,
    batchDelete,
    batchTag,
  }
}
