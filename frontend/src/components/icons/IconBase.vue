<script setup lang="ts">
/**
 * OWNEX Icon Base Component
 */

interface Props {
  size?: number | string
  fill?: string
  strokeColor?: string
  strokeWidth?: number
  strokeLinecap?: 'butt' | 'round' | 'square'
  strokeLinejoin?: 'miter' | 'round' | 'bevel'
  viewBox?: string
  cssClass?: string
  ariaHidden?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  size: 24,
  fill: 'none',
  strokeColor: 'currentColor',
  strokeWidth: 2,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
  viewBox: '0 0 24 24',
  cssClass: '',
  ariaHidden: true,
})
</script>

<template>
  <svg
    :viewBox="viewBox"
    :width="size"
    :height="size"
    :fill="fill"
    :stroke="strokeColor"
    :stroke-width="strokeWidth"
    :stroke-linecap="strokeLinecap"
    :stroke-linejoin="strokeLinejoin"
    :aria-hidden="ariaHidden"
    :class="cssClass"
  >
    <slot />
  </svg>
</template>