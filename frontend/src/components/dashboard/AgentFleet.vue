<script setup lang="ts">
import { Cpu } from '@lucide/vue'

interface Agent {
  name: string
  status: 'online' | 'offline' | 'limited' | 'local'
  description: string
}

interface Props {
  agents?: Agent[]
  className?: string
}

const props = withDefaults(defineProps<Props>(), {
  agents: () => [
    { name: 'Hermes', status: 'online', description: 'Orquestación' },
    { name: 'OpenCode', status: 'online', description: 'Implementación' },
    { name: 'Cline', status: 'online', description: 'Edición IDE' },
    { name: 'Ollama', status: 'local', description: 'Modelo local qwen2.5' },
    { name: 'FCC', status: 'limited', description: 'Router multi-provider' },
  ],
})

const dotClass: Record<string, string> = {
  online: 'status-dot-green',
  offline: 'status-dot-red',
  limited: 'status-dot-amber',
  local: 'status-dot-green',
}

const labelClass: Record<string, string> = {
  online: 'text-success',
  offline: 'text-destructive',
  limited: 'text-warning',
  local: 'text-success',
}

const statusLabels: Record<string, string> = {
  online: 'Online',
  offline: 'Offline',
  limited: 'Limitado',
  local: 'Local',
}
</script>

<template>
  <div :class="['panel rounded-xl p-4', className]">
    <div class="flex items-center gap-2 mb-3">
      <Cpu class="h-4 w-4 text-accent" />
      <span class="font-mono text-xs font-semibold text-foreground">Agent Fleet</span>
    </div>
    <div class="space-y-2">
      <div
        v-for="agent in agents"
        :key="agent.name"
        class="flex items-center justify-between rounded-lg px-3 py-2 hover:bg-surface/20 transition-colors"
      >
        <div class="flex items-center gap-2.5 min-w-0">
          <span class="status-dot shrink-0" :class="dotClass[agent.status]" />
          <span class="text-xs font-medium text-foreground">{{ agent.name }}</span>
          <span class="text-[9px] text-muted-foreground font-mono hidden sm:inline">{{ agent.description }}</span>
        </div>
        <span :class="['font-mono text-[9px] font-medium', labelClass[agent.status]]">
          {{ statusLabels[agent.status] }}
        </span>
      </div>
    </div>
  </div>
</template>
