<script setup lang="ts">
import { ref, computed, onMounted, watch, defineAsyncComponent } from 'vue'
import { cn } from '@/lib/utils'
import { getWidgetDef, getAvailableWidgets, type WidgetDef } from './WidgetRegistry'
import WidgetWrapper from './WidgetWrapper.vue'
import Modal from '@/components/ui/Modal.vue'
import Button from '@/components/ui/Button.vue'
import Badge from '@/components/ui/Badge.vue'
import {
  Plus, HeartPulse, Target, Bug, DollarSign, Clock, Activity,
  Network, Bell, TrendingUp, Sparkles, LayoutGrid,
} from '@lucide/vue'

export interface WidgetInstance {
  id: string
  type: string
  cols: number
  rows: number
}

interface Props {
  widgets?: WidgetInstance[]
  editable?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  editable: false,
})

const emit = defineEmits<{
  update: [widgets: WidgetInstance[]]
}>()

const LAYOUT_KEY = 'orion-widget-layout'

const iconMap: Record<string, any> = {
  HeartPulse, Target, Bug, DollarSign, Clock, Activity,
  Network, Bell, TrendingUp, Sparkles,
}

const defaultLayout: WidgetInstance[] = [
  { id: 'health-score', type: 'health-score', cols: 2, rows: 1 },
  { id: 'scheduler-status', type: 'scheduler-status', cols: 2, rows: 1 },
  { id: 'revenue-overview', type: 'revenue-overview', cols: 2, rows: 1 },
  { id: 'findings-summary', type: 'findings-summary', cols: 2, rows: 1 },
  { id: 'active-targets', type: 'active-targets', cols: 1, rows: 1 },
  { id: 'bounty-summary', type: 'bounty-summary', cols: 1, rows: 1 },
  { id: 'top-priorities', type: 'top-priorities', cols: 2, rows: 1 },
  { id: 'knowledge-graph-mini', type: 'knowledge-graph-mini', cols: 3, rows: 1 },
  { id: 'recent-activity', type: 'recent-activity', cols: 3, rows: 1 },
]

const internalWidgets = ref<WidgetInstance[]>([])
const showAddModal = ref(false)
const widgetData = ref<Record<string, unknown>>({})
const widgetLoading = ref<Record<string, boolean>>({})
const widgetError = ref<Record<string, string | null>>({})
const refreshTimestamps = ref<Record<string, number>>({})

const available = computed(() => getAvailableWidgets())

const currentWidgets = computed(() => {
  if (props.widgets && props.widgets.length > 0) return props.widgets
  return internalWidgets.value
})

function loadLayout() {
  try {
    const saved = localStorage.getItem(LAYOUT_KEY)
    if (saved) {
      internalWidgets.value = JSON.parse(saved)
    } else {
      internalWidgets.value = [...defaultLayout]
    }
  } catch {
    internalWidgets.value = [...defaultLayout]
  }
}

function saveLayout(widgets: WidgetInstance[]) {
  internalWidgets.value = widgets
  try {
    localStorage.setItem(LAYOUT_KEY, JSON.stringify(widgets))
  } catch { /* ignore */ }
  emit('update', widgets)
}

function removeWidget(id: string) {
  const updated = currentWidgets.value.filter(w => w.id !== id)
  saveLayout(updated)
}

function addWidget(type: string) {
  const def = getWidgetDef(type)
  if (!def) return
  const exists = currentWidgets.value.find(w => w.type === type)
  if (exists) return
  const newWidget: WidgetInstance = {
    id: type,
    type,
    cols: def.defaultSize.cols,
    rows: def.defaultSize.rows,
  }
  saveLayout([...currentWidgets.value, newWidget])
  showAddModal.value = false
  fetchWidgetData(type)
}

function moveWidget(id: string, direction: 'left' | 'right') {
  const widgets = [...currentWidgets.value]
  const idx = widgets.findIndex(w => w.id === id)
  if (idx === -1) return
  const swapIdx = direction === 'left' ? idx - 1 : idx + 1
  if (swapIdx < 0 || swapIdx >= widgets.length) return
  const temp = widgets[idx]
  widgets[idx] = widgets[swapIdx]
  widgets[swapIdx] = temp
  saveLayout(widgets)
}

async function fetchWidgetData(type: string) {
  const def = getWidgetDef(type)
  if (!def) return
  widgetLoading.value[type] = true
  widgetError.value[type] = null
  try {
    const { api } = await import('@/lib/api')
    const data = await api.get<unknown>(def.dataSource)
    widgetData.value[type] = data
  } catch (e: any) {
    widgetError.value[type] = e?.message || 'Failed to load'
  } finally {
    widgetLoading.value[type] = false
  }
}

function refreshWidget(id: string) {
  refreshTimestamps.value[id] = Date.now()
  fetchWidgetData(id)
}

function getWidgetComponent(type: string) {
  const def = getWidgetDef(type)
  if (!def) return null
  return defineAsyncComponent(def.component)
}

onMounted(() => {
  loadLayout()
  for (const w of currentWidgets.value) {
    fetchWidgetData(w.type)
  }
})

watch(() => props.widgets, () => {
  for (const w of currentWidgets.value) {
    if (!widgetData.value[w.type]) {
      fetchWidgetData(w.type)
    }
  }
}, { deep: true })

function isWidgetAdded(type: string) {
  return currentWidgets.value.some(w => w.type === type)
}

function colsToClass(cols: number): string {
  const map: Record<number, string> = {
    1: 'col-span-1',
    2: 'col-span-2',
    3: 'col-span-3',
    4: 'col-span-4',
    6: 'col-span-6',
  }
  return map[cols] || 'col-span-1'
}
</script>

<template>
  <div class="space-y-3">
    <!-- Widget Grid -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-3 auto-rows-auto">
      <div
        v-for="widget in currentWidgets"
        :key="widget.id"
        :class="cn(colsToClass(widget.cols), 'min-h-[140px]')"
      >
        <WidgetWrapper
          :widget-id="widget.id"
          :title="getWidgetDef(widget.type)?.name || widget.type"
          :icon="getWidgetDef(widget.type)?.icon"
          :loading="widgetLoading[widget.type]"
          :error="widgetError[widget.type]"
          :removable="true"
          :configurable="false"
          :editable="editable"
          @close="removeWidget(widget.id)"
          @refresh="refreshWidget(widget.id)"
        >
          <component
            v-if="getWidgetComponent(widget.type)"
            :is="getWidgetComponent(widget.type)"
            :data="widgetData[widget.type]"
            :widget-id="widget.id"
            :refresh-key="refreshTimestamps[widget.id]"
          />
        </WidgetWrapper>
      </div>
    </div>

    <!-- Add Widget Button (edit mode) -->
    <div v-if="editable" class="flex justify-center pt-2">
      <Button variant="outline" size="sm" @click="showAddModal = true">
        <Plus class="h-3.5 w-3.5 mr-1" />
        Add Widget
      </Button>
    </div>

    <!-- Add Widget Modal -->
    <Modal :open="showAddModal" title="Add Widget" size="lg" @close="showAddModal = false">
      <div class="grid grid-cols-2 gap-2">
        <button
          v-for="widget in available"
          :key="widget.id"
          @click="addWidget(widget.id)"
          :disabled="isWidgetAdded(widget.id)"
          :class="cn(
            'flex items-start gap-3 rounded-lg border p-3 text-left transition-all',
            isWidgetAdded(widget.id)
              ? 'border-border/20 opacity-40 cursor-not-allowed'
              : 'border-border/30 hover:border-primary/30 hover:bg-surface/30 cursor-pointer',
          )"
        >
          <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-primary/8 text-primary">
            <component :is="iconMap[widget.icon] || Activity" class="h-4 w-4" />
          </div>
          <div class="min-w-0">
            <p class="text-sm font-medium text-foreground">{{ widget.name }}</p>
            <p class="text-[10px] text-muted-foreground mt-0.5">{{ widget.description }}</p>
            <div class="flex items-center gap-1.5 mt-1">
              <Badge variant="outline" class="text-[8px] px-1 py-0">{{ widget.defaultSize.cols }} cols</Badge>
              <Badge v-if="isWidgetAdded(widget.id)" variant="success" class="text-[8px] px-1 py-0">Added</Badge>
            </div>
          </div>
        </button>
      </div>
    </Modal>
  </div>
</template>
