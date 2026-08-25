<template>
  <div class="jarvis-background">
    <div class="grid-overlay"></div>
    <div class="particles">
      <div v-for="i in 50" :key="i" class="particle" :style="particleStyle(i)"></div>
    </div>
    <div class="scanline"></div>
    <div class="vignette"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

const mousePosition = ref({ x: 0, y: 0 })

const particleStyle = (index: number) => {
  const size = Math.random() * 3 + 1
  const x = Math.random() * 100
  const y = Math.random() * 100
  const duration = Math.random() * 20 + 10
  const delay = Math.random() * 5
  const opacity = Math.random() * 0.5 + 0.1

  return {
    width: `${size}px`,
    height: `${size}px`,
    left: `${x}%`,
    top: `${y}%`,
    animationDuration: `${duration}s`,
    animationDelay: `${delay}s`,
    opacity,
  }
}

const handleMouseMove = (e: MouseEvent) => {
  mousePosition.value = {
    x: (e.clientX / window.innerWidth) * 100,
    y: (e.clientY / window.innerHeight) * 100,
  }
}

onMounted(() => {
  window.addEventListener('mousemove', handleMouseMove)
})

onUnmounted(() => {
  window.removeEventListener('mousemove', handleMouseMove)
})
</script>

<style scoped>
.jarvis-background {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 0;
  overflow: hidden;
}

.grid-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-image:
    linear-gradient(rgba(30, 64, 255, 0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(30, 64, 255, 0.04) 1px, transparent 1px);
  background-size: 50px 50px;
  animation: gridMove 20s linear infinite;
}

@keyframes gridMove {
  0% {
    transform: translate(0, 0);
  }
  100% {
    transform: translate(50px, 50px);
  }
}

.particles {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
}

.particle {
  position: absolute;
  background: rgba(30, 64, 255, 0.55);
  border-radius: 50%;
  animation: floatParticle var(--animationDuration) ease-in-out infinite;
  animation-delay: var(--animationDelay);
  box-shadow: 0 0 6px rgba(30, 64, 255, 0.45);
}

@keyframes floatParticle {
  0%, 100% {
    transform: translateY(0) translateX(0);
    opacity: var(--opacity);
  }
  25% {
    transform: translateY(-30px) translateX(10px);
  }
  50% {
    transform: translateY(-60px) translateX(-10px);
    opacity: var(--opacity) * 0.5;
  }
  75% {
    transform: translateY(-30px) translateX(10px);
  }
}

.scanline {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 2px;
  background: linear-gradient(
    90deg,
    transparent,
    rgba(30, 64, 255, 0.12),
    transparent
  );
  animation: scanline 8s linear infinite;
}

@keyframes scanline {
  0% {
    top: 0;
    opacity: 0;
  }
  10% {
    opacity: 1;
  }
  90% {
    opacity: 1;
  }
  100% {
    top: 100%;
    opacity: 0;
  }
}

.vignette {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: radial-gradient(
    ellipse at center,
    transparent 0%,
    rgba(0, 0, 0, 0.3) 100%
  );
  pointer-events: none;
}
</style>
