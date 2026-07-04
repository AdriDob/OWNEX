<script setup lang="ts">
import { computed, watch } from 'vue'
import { useContextMenu } from '@/composables/useContextMenu'
import type { ContextAction, EntityType } from '@/composables/useContextMenu'

const { menuState, close } = useContextMenu()

const emit = defineEmits<{
  action: [actionId: string, entity: any]
}>()

watch(() => menuState.value.visible, (v) => {
  if (v) {
    document.documentElement.setAttribute('data-context-menu-visible', '')
  } else {
    document.documentElement.removeAttribute('data-context-menu-visible')
  }
})

const entityLabel = computed(() => {
  const labels: Record<EntityType, string> = {
    target: 'Target', program: 'Programa', endpoint: 'Endpoint',
    finding: 'Hallazgo', report: 'Reporte', session: 'Sesión',
    wallet: 'Billetera', prediction: 'Predicción',
  }
  return labels[menuState.value.entityType] || menuState.value.entityType
})

function handleAction(a: ContextAction) {
  if (a.separator) return
  a.action(menuState.value.entity)
  emit('action', a.id, menuState.value.entity)
  close()
}

function handleClickOutside() {
  if (menuState.value.visible) close()
}
</script>

<template>
  <Teleport to="body">
    <div
      v-if="menuState.visible"
      class="fixed inset-0 z-50"
      @click="handleClickOutside"
      @contextmenu.prevent="close"
    />
    <div
      v-if="menuState.visible"
      class="fixed z-50 min-w-[200px] rounded-lg border border-border bg-surface py-1 shadow-2xl"
      :style="{ left: menuState.x + 'px', top: menuState.y + 'px' }"
      role="menu"
      :aria-label="`Menú contextual: ${entityLabel}`"
    >
      <div class="px-3 py-1.5 text-[10px] font-medium text-muted-foreground uppercase tracking-wider border-b border-border/40">
        {{ entityLabel }}
        <span v-if="menuState.entity?.id" class="ml-1 text-primary">#{{ menuState.entity.id }}</span>
      </div>
      <template v-for="(action, i) in menuState.actions" :key="action.id">
        <div
          v-if="action.separator"
          class="my-1 border-t border-border/30"
        />
        <button
          v-else
          class="flex w-full items-center gap-2 px-3 py-1.5 text-xs text-foreground/80 hover:bg-primary/10 hover:text-foreground transition-colors"
          :class="{ 'text-destructive hover:text-destructive hover:bg-destructive/10': action.danger }"
          :disabled="action.disabled"
          role="menuitem"
          @click="handleAction(action)"
        >
          <span class="flex-1 text-left">{{ action.label }}</span>
          <span v-if="action.shortcut" class="text-[10px] text-muted-foreground">{{ action.shortcut }}</span>
        </button>
      </template>
    </div>
  </Teleport>
</template>
