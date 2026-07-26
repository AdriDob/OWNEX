<script setup lang="ts">
import { computed } from 'vue'
import { type AssistantCharacter } from './assistantCharacters'

const props = defineProps<{
  character: AssistantCharacter
  size?: number
  animated?: boolean
}>()

const s = computed(() => props.size ?? 32)
const h = computed(() => Math.round(s.value * 0.6))
const eyeY = computed(() => Math.round(h.value * 0.35))
const mouthY = computed(() => Math.round(h.value * 0.7))
const offset = 2

const accent = computed(() => {
  const map: Record<string, string> = {
    'text-purple-400': '#a78bfa',
    'text-blue-400': '#60a5fa',
    'text-amber-400': '#fbbf24',
    'text-cyan-400': '#22d3ee',
    'text-foreground': '#f1f5f9',
    'text-gold': '#f5a623',
    'text-green-400': '#4ade80',
    'text-orange-400': '#fb923c',
    'text-rose-500': '#f43f5e',
  }
  return map[props.character.color] ?? '#a78bfa'
})

const bg = computed(() => accent.value + '22')

const characters = {
  merlin: { hat: true, beard: true, ears: 'pointed', shape: 'circle' },
  clippy: { hat: false, beard: false, ears: 'square', shape: 'rect' },
  rover: { hat: false, beard: false, ears: 'floppy', shape: 'circle' },
  links: { hat: false, beard: true, ears: 'pointed', shape: 'circle' },
  dot: { hat: false, beard: false, ears: 'none', shape: 'circle' },
  f1: { hat: true, beard: false, ears: 'antenna', shape: 'circle' },
  pepe: { hat: false, beard: false, ears: 'none', shape: 'ellipse' },
}

const c = computed(() => (characters as any)[props.character.id] ?? characters.dot)
</script>

<template>
  <svg
    :width="s"
    :height="s"
    :viewBox="`0 0 ${s} ${s}`"
    class="shrink-0"
    :class="{ 'animate-float': animated }"
  >
    <!-- Background circle -->
    <rect
      :x="offset" :y="offset"
      :width="s - offset * 2" :height="s - offset * 2"
      :rx="c.shape === 'circle' ? s / 2 : c.shape === 'ellipse' ? s / 3 : 4"
      :ry="c.shape === 'ellipse' ? s / 2.5 : c.shape === 'circle' ? s / 2 : 4"
      :fill="bg"
      stroke="none"
    />

    <!-- Merlin hat -->
    <template v-if="c.hat && character.id === 'merlin'">
      <polygon :points="`${s * 0.25},${s * 0.35} ${s * 0.5},${s * 0.05} ${s * 0.75},${s * 0.35}`" :fill="accent" opacity="0.8" />
      <rect :x="s * 0.2" :y="s * 0.3" :width="s * 0.6" :height="s * 0.06" :rx="1" :fill="accent" opacity="0.6" />
      <!-- Stars on hat -->
      <text :x="s * 0.42" :y="s * 0.22" font-size="6" :fill="accent" opacity="0.9">✦</text>
    </template>

    <!-- F1 antenna -->
    <template v-if="c.ears === 'antenna'">
      <line :x1="s * 0.7" :y1="s * 0.3" :x2="s * 0.82" :y2="s * 0.1" :stroke="accent" stroke-width="1.5" />
      <circle :cx="s * 0.82" :cy="s * 0.1" :r="s * 0.04" :fill="accent" opacity="0.8" />
      <line :x1="s * 0.3" :y1="s * 0.3" :x2="s * 0.18" :y2="s * 0.1" :stroke="accent" stroke-width="1.5" />
      <circle :cx="s * 0.18" :cy="s * 0.1" :r="s * 0.04" :fill="accent" opacity="0.8" />
    </template>

    <!-- Rover floppy ears -->
    <template v-if="c.ears === 'floppy'">
      <ellipse :cx="s * 0.15" :cy="s * 0.55" :rx="s * 0.07" :ry="s * 0.18" :fill="accent" opacity="0.4" />
      <ellipse :cx="s * 0.85" :cy="s * 0.55" :rx="s * 0.07" :ry="s * 0.18" :fill="accent" opacity="0.4" />
    </template>

    <!-- Face area -->
    <g class="pixel-face" :class="{ 'animate-blink': animated }">
      <!-- Left eye -->
      <circle :cx="s * 0.35" :cy="eyeY" :r="s * 0.05" :fill="accent" />
      <!-- Right eye -->
      <circle :cx="s * 0.65" :cy="eyeY" :r="s * 0.05" :fill="accent" />

      <!-- Mouth (varies by character) -->
      <template v-if="character.id === 'rover'">
        <!-- Dog tongue -->
        <ellipse :cx="s * 0.5" :cy="mouthY" :rx="s * 0.08" :ry="s * 0.06" :fill="accent" opacity="0.6" />
        <ellipse :cx="s * 0.5" :cy="mouthY + s * 0.03" :rx="s * 0.04" :ry="s * 0.04" fill="#ef4444" opacity="0.5" />
      </template>
      <template v-else-if="character.id === 'pepe'">
        <!-- Pepe smirk -->
        <path :d="`M ${s * 0.3} ${mouthY} Q ${s * 0.5} ${mouthY + s * 0.1} ${s * 0.7} ${mouthY}`" :stroke="accent" fill="none" stroke-width="1.5" stroke-linecap="round" />
      </template>
      <template v-else-if="character.id === 'dot'">
        <!-- Dot = minimalist dot mouth -->
        <circle :cx="s * 0.5" :cy="mouthY" :r="s * 0.02" :fill="accent" />
      </template>
      <template v-else-if="character.id === 'f1'">
        <!-- F1 = smile -->
        <path :d="`M ${s * 0.3} ${mouthY} Q ${s * 0.5} ${mouthY + s * 0.08} ${s * 0.7} ${mouthY}`" :stroke="accent" fill="none" stroke-width="1.5" stroke-linecap="round" />
      </template>
      <template v-else>
        <!-- Default smile -->
        <path :d="`M ${s * 0.3} ${mouthY} Q ${s * 0.5} ${mouthY + s * 0.06} ${s * 0.7} ${mouthY}`" :stroke="accent" fill="none" stroke-width="1.5" stroke-linecap="round" />
      </template>

      <!-- Merlin beard -->
      <template v-if="c.beard && character.id === 'merlin'">
        <path :d="`M ${s * 0.3} ${mouthY + s * 0.04} Q ${s * 0.5} ${s * 0.9} ${s * 0.7} ${mouthY + s * 0.04}`" :fill="accent" opacity="0.2" />
      </template>

      <!-- Links whiskers -->
      <template v-if="character.id === 'links'">
        <line :x1="s * 0.15" :y1="eyeY + s * 0.05" :x2="s * 0.3" :y2="mouthY" :stroke="accent" stroke-width="1" opacity="0.5" />
        <line :x1="s * 0.15" :y1="eyeY + s * 0.12" :x2="s * 0.3" :y2="mouthY + s * 0.02" :stroke="accent" stroke-width="1" opacity="0.5" />
        <line :x1="s * 0.85" :y1="eyeY + s * 0.05" :x2="s * 0.7" :y2="mouthY" :stroke="accent" stroke-width="1" opacity="0.5" />
        <line :x1="s * 0.85" :y1="eyeY + s * 0.12" :x2="s * 0.7" :y2="mouthY + s * 0.02" :stroke="accent" stroke-width="1" opacity="0.5" />
      </template>

      <!-- Pepe cheeks -->
      <template v-if="character.id === 'pepe'">
        <circle :cx="s * 0.2" :cy="s * 0.55" :r="s * 0.06" fill="#4ade80" opacity="0.2" />
        <circle :cx="s * 0.8" :cy="s * 0.55" :r="s * 0.06" fill="#4ade80" opacity="0.2" />
      </template>

      <!-- Clippy = glasses -->
      <template v-if="character.id === 'clippy'">
        <rect :x="s * 0.28" :y="eyeY - s * 0.04" :width="s * 0.14" :height="s * 0.1" rx="2" :stroke="accent" fill="none" stroke-width="1" opacity="0.5" />
        <rect :x="s * 0.58" :y="eyeY - s * 0.04" :width="s * 0.14" :height="s * 0.1" rx="2" :stroke="accent" fill="none" stroke-width="1" opacity="0.5" />
        <line :x1="s * 0.42" :y1="eyeY" :x2="s * 0.58" :y2="eyeY" :stroke="accent" stroke-width="1" opacity="0.5" />
      </template>
    </g>
  </svg>
</template>

<style scoped>
.animate-float {
  animation: float 3s ease-in-out infinite;
}
@keyframes float {
  0%, 100% { transform: translateY(0px); }
  50% { transform: translateY(-3px); }
}
.animate-blink {
  animation: blink 4s ease-in-out infinite;
}
@keyframes blink {
  0%, 95%, 100% { opacity: 1; }
  97% { opacity: 0.3; }
}
</style>
