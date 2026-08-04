<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

const props = withDefaults(defineProps<{
  text: string
  position?: 'top' | 'bottom' | 'left' | 'right'
  delay?: number
}>(), {
  position: 'top',
  delay: 400,
})

const visible = ref(false)
let timeout: ReturnType<typeof setTimeout> | null = null
const el = ref<HTMLElement | null>(null)

function show() {
  timeout = setTimeout(() => { visible.value = true }, props.delay)
}
function hide() {
  if (timeout) clearTimeout(timeout)
  visible.value = false
}

onUnmounted(() => {
  if (timeout) clearTimeout(timeout)
})
</script>

<template>
  <div ref="el" class="relative inline-flex" @mouseenter="show" @mouseleave="hide" @focus="show" @blur="hide">
    <slot />
    <Transition name="tooltip">
      <div
        v-if="visible"
        :class="[
          'absolute z-50 px-2.5 py-1.5 rounded-md bg-background/95 border border-border shadow-lg backdrop-blur-xl pointer-events-none',
          'font-mono text-[10px] text-foreground whitespace-nowrap',
          position === 'bottom' && 'top-full left-1/2 -translate-x-1/2 mt-2',
          position === 'left' && 'right-full top-1/2 -translate-y-1/2 mr-2',
          position === 'right' && 'left-full top-1/2 -translate-y-1/2 ml-2',
        ]"
      >
        {{ text }}
        <div
          :class="[
            'absolute h-1.5 w-1.5 rotate-45 bg-background/95 border-border',
            position === 'top' && 'top-full left-1/2 -translate-x-1/2 -mt-0.5 border-b border-r',
            position === 'bottom' && 'bottom-full left-1/2 -translate-x-1/2 -mb-0.5 border-t border-l',
            position === 'left' && 'left-full top-1/2 -translate-y-1/2 -ml-0.5 border-t border-r',
            position === 'right' && 'right-full top-1/2 -translate-y-1/2 -mr-0.5 border-b border-l',
          ]"
        />
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.tooltip-enter-active, .tooltip-leave-active { transition: opacity 0.15s ease, transform 0.15s ease; }
.tooltip-enter-from, .tooltip-leave-to { opacity: 0; transform: scale(0.96); }
</style>