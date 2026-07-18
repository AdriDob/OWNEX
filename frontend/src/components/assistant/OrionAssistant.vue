<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { assistants, type AssistantCharacter, getRandomMessage } from './assistantCharacters'
import { cn } from '@/lib/utils'
import { MessageCircle, X } from '@lucide/vue'
import PixelAvatar from './PixelAvatar.vue'

interface Props {
  context?: string
  class?: string
  overlay?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  context: 'mission-control',
  overlay: false,
})

const activeAssistant = ref<AssistantCharacter | null>(null)
const currentMessage = ref('')
const visible = ref(false)
const expanded = ref(false)
let rotationInterval: ReturnType<typeof setInterval> | null = null

const relevantAssistants = computed(() => {
  return assistants.filter(a => a.context.includes(props.context))
})

function pickRandom() {
  if (relevantAssistants.value.length === 0) return
  const idx = Math.floor(Math.random() * relevantAssistants.value.length)
  activeAssistant.value = relevantAssistants.value[idx]
  currentMessage.value = getRandomMessage(activeAssistant.value)
  visible.value = true
}

function dismiss() {
  visible.value = false
}

function toggleExpand() {
  expanded.value = !expanded.value
}

function selectAssistant(char: AssistantCharacter) {
  activeAssistant.value = char
  currentMessage.value = getRandomMessage(char)
  visible.value = true
  expanded.value = false
}

onMounted(() => {
  setTimeout(pickRandom, 2000)
  rotationInterval = setInterval(() => {
    if (!expanded.value) pickRandom()
  }, 30000)
})

onUnmounted(() => {
  if (rotationInterval) clearInterval(rotationInterval)
})

const pixelAvatarStyle = (char: AssistantCharacter) => {
  return {
    background: `linear-gradient(135deg, ${char.borderColor.replace('border-', '').replace('/30', '')}22, transparent)`,
    borderColor: char.borderColor.replace('border-', ''),
  }
}
</script>

<template>
  <div :class="cn('relative', props.class)">
    <!-- Assistant Hub Button -->
    <button
      @click="toggleExpand"
      class="flex items-center gap-2 rounded-full border border-primary/20 bg-surface/50 px-3 py-1.5 text-xs text-muted-foreground hover:border-primary/40 hover:text-foreground transition-all"
    >
      <div class="flex -space-x-1">
        <div v-for="(char, i) in relevantAssistants.slice(0, 4)" :key="char.id"
          class="h-6 w-6 rounded-full border border-background flex items-center justify-center overflow-hidden"
        >
          <PixelAvatar :character="char" :size="20" :animated="true" />
        </div>
      </div>
      <span>Assistants</span>
    </button>

    <!-- Expanded Panel -->
    <Transition name="slide">
      <div v-if="expanded"
        class="absolute bottom-full mb-2 left-0 w-72 rounded-xl border border-border/30 bg-surface/95 backdrop-blur-xl shadow-2xl overflow-hidden"
      >
        <div class="px-3 py-2 border-b border-border/20 flex items-center justify-between">
          <span class="font-mono text-[10px] font-bold tracking-wider text-muted-foreground">ORION ASSISTANTS</span>
          <button @click="expanded = false" class="text-muted-foreground hover:text-foreground">
            <X class="h-3.5 w-3.5" />
          </button>
        </div>
        <div class="p-2 space-y-1">
          <button
            v-for="char in relevantAssistants" :key="char.id"
            @click="selectAssistant(char)"
            class="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left transition-colors hover:bg-surface-hover"
            :class="{ 'bg-primary/5': activeAssistant?.id === char.id }"
          >
            <div class="h-8 w-8 rounded-lg border flex items-center justify-center overflow-hidden"
              :class="[char.borderColor]"
            >
              <PixelAvatar :character="char" :size="28" :animated="true" />
            </div>
            <div class="flex-1 min-w-0">
              <p class="text-xs font-medium text-foreground" :class="char.color">{{ char.name }}</p>
              <p class="text-[10px] text-muted-foreground truncate">{{ char.title }}</p>
            </div>
          </button>
        </div>
      </div>
    </Transition>

    <!-- Speech Bubble -->
    <Transition name="bubble">
      <div v-if="visible && activeAssistant && !expanded"
        class="mt-2 rounded-xl border p-3"
        :class="[activeAssistant.borderColor, activeAssistant.bgGradient]"
      >
        <div class="flex items-start gap-2.5">
          <div class="h-7 w-7 shrink-0 rounded-lg border flex items-center justify-center overflow-hidden"
            :class="[activeAssistant.borderColor]"
          >
            <PixelAvatar :character="activeAssistant" :size="24" :animated="true" />
          </div>
          <div class="flex-1 min-w-0">
            <div class="flex items-center justify-between gap-2 mb-0.5">
              <span class="font-mono text-[10px] font-bold" :class="activeAssistant.color">{{ activeAssistant.name }}</span>
              <button @click="dismiss" class="text-muted-foreground/40 hover:text-foreground">
                <X class="h-3 w-3" />
              </button>
            </div>
            <p class="text-[11px] text-foreground/90 leading-relaxed">{{ currentMessage }}</p>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.bubble-enter-active, .bubble-leave-active {
  transition: all 0.25s ease;
}
.bubble-enter-from, .bubble-leave-to {
  opacity: 0;
  transform: translateY(6px);
}
.slide-enter-active, .slide-leave-active {
  transition: all 0.2s ease;
}
.slide-enter-from, .slide-leave-to {
  opacity: 0;
  transform: translateY(8px);
}
</style>
