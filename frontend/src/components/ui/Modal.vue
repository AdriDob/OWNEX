<script setup lang="ts">
import { watch, onMounted, onUnmounted } from 'vue'
import { cn } from '@/lib/utils'
import { X } from '@lucide/vue'

interface Props {
  open: boolean
  title?: string
  size?: 'sm' | 'md' | 'lg' | 'xl' | 'full'
  closable?: boolean
  class?: string
}

const props = withDefaults(defineProps<Props>(), {
  size: 'md',
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
  if (val) {
    document.body.style.overflow = 'hidden'
  } else {
    document.body.style.overflow = ''
  }
})

onMounted(() => window.addEventListener('keydown', onKeydown))
onUnmounted(() => {
  window.removeEventListener('keydown', onKeydown)
  document.body.style.overflow = ''
})

const sizeClasses: Record<string, string> = {
  sm: 'max-w-sm',
  md: 'max-w-md',
  lg: 'max-w-lg',
  xl: 'max-w-xl',
  full: 'max-w-[90vw] max-h-[90vh]',
}
</script>

<template>
  <Teleport to="body">
    <Transition name="modal">
      <div
        v-if="open"
        class="fixed inset-0 z-50 flex items-center justify-center p-4"
        @click="close"
      >
        <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" />
        <div
          :class="cn(
            'relative w-full rounded-xl border border-border/50 bg-background p-6 shadow-2xl animate-in',
            sizeClasses[size],
            props.class,
          )"
          @click.stop
        >
          <div v-if="title || closable" class="mb-4 flex items-center justify-between">
            <h3 v-if="title" class="text-sm font-semibold text-foreground">{{ title }}</h3>
            <button
              v-if="closable"
              @click="close"
              class="ml-auto flex h-7 w-7 items-center justify-center rounded-lg text-muted-foreground hover:bg-surface/50 hover:text-foreground transition-colors"
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
.modal-enter-active, .modal-leave-active {
  transition: opacity 0.15s ease;
}
.modal-enter-from, .modal-leave-to {
  opacity: 0;
}
</style>
