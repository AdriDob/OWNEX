import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { EntityType } from '@/composables/useContextMenu'

export interface MicroEntity {
  id: string | number
  type?: string
  name?: string
  title?: string
  [key: string]: any
}

interface MoreInfoPanel {
  open: boolean
  entity: MicroEntity | null
  type: EntityType | null
}

export const useUIStore = defineStore('ui', () => {
  const inspectorOpen = ref(false)
  const inspectorEntity = ref<MicroEntity | null>(null)
  const inspectorType = ref<EntityType | null>(null)

  const miniPreviewVisible = ref(false)
  const miniPreviewEntity = ref<MicroEntity | null>(null)
  const miniPreviewPosition = ref({ x: 0, y: 0 })

  const timelineOpen = ref(false)
  const timelineEntityId = ref<string | null>(null)

  const compareOpen = ref(false)
  const compareEntities = ref<[MicroEntity | null, MicroEntity | null]>([null, null])
  const compareEntityType = ref<EntityType | null>(null)

  const selectedIds = ref<string[]>([])
  const multiSelectActive = computed(() => selectedIds.value.length > 0)

  const moreInfoPanel = ref<MoreInfoPanel>({ open: false, entity: null, type: null })

  const inspectorTab = ref<'summary' | 'metadata' | 'json' | 'activity' | 'logs'>('summary')

  interface MiniPreviewData {
    x: number
    y: number
    title: string
    subtitle?: string
    status?: string
    metrics?: Record<string, string | number>
  }
  const miniPreview = ref<MiniPreviewData | null>(null)

  const loading = ref<Record<string, boolean>>({})

  const inspectorData = computed(() => {
    if (!inspectorOpen.value || !inspectorEntity.value) return null
    return { entity: inspectorEntity.value, type: inspectorType.value }
  })

  const miniPreviewData = computed(() => {
    if (!miniPreviewVisible.value || !miniPreviewEntity.value) return null
    return { entity: miniPreviewEntity.value, position: miniPreviewPosition.value }
  })

  const timelineData = computed(() => {
    if (!timelineOpen.value || !timelineEntityId.value) return null
    return { entityId: timelineEntityId.value }
  })

  const compareData = computed(() => {
    if (!compareOpen.value) return null
    return { entities: compareEntities.value, type: compareEntityType.value }
  })

  const selectionCount = computed(() => selectedIds.value.length)
  const hasSelection = computed(() => selectedIds.value.length > 0)
  const isLoading = computed(() => Object.values(loading.value).some(Boolean))

  function openInspector(entity: MicroEntity, type: EntityType) {
    inspectorEntity.value = entity
    inspectorType.value = type
    inspectorOpen.value = true
  }

  function closeInspector() {
    inspectorOpen.value = false
    inspectorEntity.value = null
    inspectorType.value = null
  }

  function showMiniPreview(entity: MicroEntity, x: number, y: number) {
    miniPreviewEntity.value = entity
    miniPreviewPosition.value = { x, y }
    miniPreviewVisible.value = true
  }

  function hideMiniPreview() {
    miniPreviewVisible.value = false
    miniPreviewEntity.value = null
  }

  function openTimeline(entityId: string) {
    timelineEntityId.value = entityId
    timelineOpen.value = true
  }

  function closeTimeline() {
    timelineOpen.value = false
    timelineEntityId.value = null
  }

  function openCompare(entity: MicroEntity, type: EntityType) {
    compareEntities.value = [entity, null]
    compareEntityType.value = type
    compareOpen.value = true
  }

  function addToCompare(entity: MicroEntity) {
    const [a, b] = compareEntities.value
    if (!a) {
      compareEntities.value = [entity, null]
    } else if (!b) {
      compareEntities.value = [a, entity]
    } else {
      compareEntities.value = [b, entity]
    }
  }

  function clearCompare() {
    compareOpen.value = false
    compareEntities.value = [null, null]
    compareEntityType.value = null
  }

  function addToSelection(id: string) {
    if (!selectedIds.value.includes(id)) {
      selectedIds.value.push(id)
    }
  }

  function removeFromSelection(id: string) {
    selectedIds.value = selectedIds.value.filter(s => s !== id)
  }

  function toggleSelection(id: string) {
    if (selectedIds.value.includes(id)) {
      removeFromSelection(id)
    } else {
      addToSelection(id)
    }
  }

  function clearSelection() {
    selectedIds.value = []
  }

  function selectAll(ids: string[]) {
    selectedIds.value = [...ids]
  }

  function openMoreInfo(entity: MicroEntity, type: EntityType) {
    moreInfoPanel.value = { open: true, entity, type }
  }

  function closeMoreInfo() {
    moreInfoPanel.value = { open: false, entity: null, type: null }
  }

  function setLoading(key: string, value: boolean) {
    loading.value[key] = value
  }

  function handleMultiSelect(action: string) {
    console.warn(`MultiSelect action "${action}" not implemented`)
  }

  return {
    inspectorOpen, inspectorEntity, inspectorType,
    miniPreviewVisible, miniPreviewEntity, miniPreviewPosition,
    timelineOpen, timelineEntityId,
    compareOpen, compareEntities, compareEntityType,
    selectedIds, multiSelectActive,
    moreInfoPanel, loading,
    inspectorData, miniPreviewData, timelineData, compareData,
    selectionCount, hasSelection, isLoading,
    openInspector, closeInspector,
    showMiniPreview, hideMiniPreview,
    openTimeline, closeTimeline,
    openCompare, addToCompare, clearCompare,
    addToSelection, removeFromSelection, toggleSelection, clearSelection, selectAll,
    openMoreInfo, closeMoreInfo,
    setLoading, inspectorTab, miniPreview, handleMultiSelect,
  }
})
