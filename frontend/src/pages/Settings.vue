<script setup lang="ts">
import Card from '@/components/ui/Card.vue'
import Button from '@/components/ui/Button.vue'
import Separator from '@/components/ui/Separator.vue'
import { Settings, Palette, Bell, Shield, Cpu, Globe } from '@lucide/vue'

const sections = [
  { icon: Palette, label: 'Apariencia', desc: 'Tema, tono, tipografía' },
  { icon: Bell, label: 'Notificaciones', desc: 'Alertas, canales, preferencias' },
  { icon: Shield, label: 'Seguridad', desc: 'Autenticación, sesiones, licencia' },
  { icon: Cpu, label: 'AI Provider', desc: 'Modelos, contexto, temperatura' },
  { icon: Globe, label: 'Plataformas', desc: 'Conexiones con HackerOne, Bugcrowd' },
]
</script>

<template>
  <div class="space-y-6">
    <div class="animate-in space-y-1">
      <p class="text-xs font-bold uppercase tracking-widest text-primary">Configuration</p>
      <h1 class="font-display text-2xl font-bold text-foreground">Settings</h1>
      <p class="text-sm text-muted-foreground">Preferencias y configuración del sistema</p>
    </div>

    <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
      <Card v-for="(s, i) in sections" :key="s.label" class="p-5 stagger-item" :style="{ '--i': i }">
        <div class="flex items-start gap-4">
          <div class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-surface text-muted-foreground">
            <component :is="s.icon" class="h-4 w-4" />
          </div>
          <div>
            <h3 class="text-sm font-semibold text-foreground">{{ s.label }}</h3>
            <p class="mt-0.5 text-xs text-muted-foreground">{{ s.desc }}</p>
          </div>
        </div>
      </Card>
    </div>
  </div>
</template>
