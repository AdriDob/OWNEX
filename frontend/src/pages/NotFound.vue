<script setup lang="ts">
import { ArrowLeft, Home, Search } from '@lucide/vue'
import { useRouter } from 'vue-router'
import Button from '@/components/ui/Button.vue'

const router = useRouter()
</script>

<template>
  <div class="flex min-h-screen items-center justify-center p-4">
    <div class="relative w-full max-w-lg text-center animate-in">
      <div class="absolute inset-0 -z-10 bg-gradient-to-br from-primary/5 via-transparent to-accent/5 rounded-3xl blur-3xl" />

      <div class="relative">
        <div class="flex justify-center mb-6">
          <div class="relative">
            <div class="absolute inset-0 animate-ping rounded-full bg-primary/20" />
            <div class="relative flex h-24 w-24 items-center justify-center rounded-full bg-gradient-to-br from-primary/20 to-accent/20 backdrop-blur-sm">
              <Search class="h-10 w-10 text-primary/60" />
            </div>
          </div>
        </div>

        <h1 class="font-display text-8xl font-black text-foreground/10 select-none">404</h1>

        <div class="relative -mt-8">
          <h2 class="text-2xl font-bold text-foreground">Página no encontrada</h2>
          <p class="mt-2 text-sm text-muted-foreground max-w-sm mx-auto">
            La ruta que buscás no existe, fue movida o está fuera del alcance del radar.
          </p>
        </div>

        <div class="mt-8 flex items-center justify-center gap-3">
          <Button @click="router.push('/')">
            <Home class="h-4 w-4" /> Ir al Inicio
          </Button>
          <Button variant="outline" @click="router.back()">
            <ArrowLeft class="h-4 w-4" /> Volver
          </Button>
        </div>
      </div>
    </div>
  </div>
</template>
