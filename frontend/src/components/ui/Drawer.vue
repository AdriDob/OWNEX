<script setup lang="ts">
import { watch, onMounted, onUnmounted } from 'vue'
import { cn } from '@/lib/utils'
import { X } from '@lucide/vue'

interface Props {
  open: boolean
  title?: string
  side?: 'left' | 'right'
  width?: string
  closable?: boolean
  class?: string
}

const props = withDefaults(defineProps<Props>(), {
  side: 'right',
  width: 'w-96',
  closable: true,
})

const emit = defineEmits<{
  'close': []
  'update:open': [value: boolean]
}>()

function close() {
  if (!props.closable) return
  emit('close')
  emit('update:open', false)
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape' && props.open) close()
}

watch(() => props.open, (val) => {
  document.body.style.overflow = val ? 'hidden' : ''
})

onMounted(() => window.addEventListener('keydown', onKeydown))
onUnmounted(() => {
  window.removeEventListener('keydown', onKeydown)
  document.body.style.overflow = ''
})
</script>

<template>
  <Teleport to="body">
    <Transition name="drawer">
      <div
        v-if="open"
        class="fixed inset-0 z-50 flex"
        :class="side === 'right' ? 'justify-end' : 'justify-start'"
      >
        <div class="absolute inset-0 bg-black/40 backdrop-blur-sm" @click="close" />
        <div
          :class="cn(
            'relative h-full overflow-y-auto border-border/40 bg-background p-6 shadow-2xl',
            side === 'right' ? 'border-l' : 'border-r',
            width,
            props.class,
          )"
        >
          <div v-if="title || closable" class="mb-6 flex items-center justify-between">
            <h3 v-if="title" class="text-sm font-semibold text-foreground">{{ title }}</h3>
            <button
              v-if="closable"
              @click="close"
              class="flex h-7 w-7 items-center justify-center rounded-lg text-muted-foreground hover:bg-surface/50 hover:text-foreground transition-colors"
            >
              <X class="h-4 w-4" />
            </button>
          </div>
          <slot />
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.drawer-enter-active, .drawer-leave-active {
  transition: all 0.2s ease;
}
.drawer-enter-from, .drawer-leave-to {
  opacity: 0;
}
.drawer-enter-from > div:last-child,
.drawer-leave-to > div:last-child {
  transform: translateX(20px);
}
</style>
