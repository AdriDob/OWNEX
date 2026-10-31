<script setup lang="ts">
import { computed } from 'vue'
import { cn } from '@/lib/utils'

interface Props {
  steps: Array<{ id: string; label: string; disabled?: boolean; error?: boolean }>
  activeStep?: number
  vertical?: boolean
  class?: string
}
const props = withDefaults(defineProps<Props>(), {
  steps: [],
  activeStep: 1,
  vertical: false,
  class: '',
})
</script>

<template>
  <div class="space-y-1.5">
    <template v-if="!props.vertical">
      <!-- Horizontal stepper -->
      <div
        v-for="(step, i) in props.steps"
        :key="step.id"
        class="flex items-center gap-2"
      >
        <div
          :class="[
            'w-8 h-8 rounded-full flex items-center justify-center',
            {
              'bg-primary': i < props.activeStep - 1,
              'bg-surface/50': i === props.activeStep - 1,
              'bg-border': i > props.activeStep - 1,
            },
            'text-[10px] font-mono',
          ]"
        >
          {{ i + 1 }}
        </div>
        <span v-if="i < props.steps.length - 1" class="text-[10px] text-muted-foreground/50 arrow">
          <svg
            aria-hidden="true"
            class="h-1.5 w-1.5"
            viewBox="0 0 24 24"
            style="width: 1em; height: 1em;"
          >
            <path
              d="M5 12h14M12 5l7 7-7 7"
              stroke="currentColor"
              stroke-width="2"
              fill="none"
            />
          </svg>
        </span>
      </div>
    </template>

    <template v-else>
      <!-- Vertical stepper -->
      <div class="space-y-3">
        <div
          v-for="(step, i) in props.steps"
          :key="step.id"
          class="flex flex-col items-start gap-1"
        >
          <div
            :class="[
              'w-8 h-8 rounded-full flex items-center justify-center',
              'bg-primary': i < props.activeStep - 1,
              'bg-surface/50': i === props.activeStep - 1,
              'bg-border': i > props.activeStep - 1,
              'text-[10px] font-mono',
            ]"
          >
            {{ i + 1 }}
          </div>
          <span class="text-[10px] text-muted-foreground/50">
            <svg
              aria-hidden="true"
              class="h-2 w-2"
              viewBox="0 0 24 24"
              style="width: 1em; height: 1em;"
            >
              <path
                d="M5 12h14M12 5l7 7-7 7"
                stroke="currentColor"
                stroke-width="2"
                fill="none"
              />
            </svg>
          </span>
          <span class="text-[10px] font-mono">{{ step.label }}</span>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.arrow {
  width: 0;
  height: 0;
  border-left: 4px solid currentColor;
  border-top: 4px transparent;
  border-bottom: 4px transparent;
}
</style>