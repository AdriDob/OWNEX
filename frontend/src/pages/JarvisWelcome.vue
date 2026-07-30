<template>
  <div class="jarvis-welcome">
    <!-- ═══ JARVIS HUD LAYER ═══ -->
    <div class="jarvis-hud">
      <!-- Scan lines -->
      <div class="scan-lines"></div>
      <!-- Grid overlay -->
      <div class="grid-overlay"></div>
      <!-- Particles -->
      <div class="particles-container">
        <div v-for="i in 50" :key="i" class="particle" :style="getParticleStyle(i)"></div>
      </div>
      <!-- Hexagon grid -->
      <div class="hexagon-grid">
        <div v-for="i in 20" :key="i" class="hexagon" :style="getHexagonStyle(i)"></div>
      </div>
    </div>

    <!-- ═══ JARVIS HERO ═══ -->
    <section class="jarvis-hero">
      <div class="hero-center">
        <!-- Central ring -->
        <div class="central-ring outer-ring">
          <div class="ring-segment"></div>
          <div class="ring-segment"></div>
          <div class="ring-segment"></div>
        </div>
        <div class="central-ring middle-ring">
          <div class="ring-segment"></div>
          <div class="ring-segment"></div>
          <div class="ring-segment"></div>
        </div>
        <div class="central-ring inner-ring">
          <div class="core-dot"></div>
          <div class="core-pulse"></div>
        </div>

        <!-- Text content -->
        <div class="hero-content">
          <h1 class="jarvis-title">
            <span class="title-letter" v-for="(letter, index) in 'OWNEX'" :key="index" :style="getLetterStyle(index)">
              {{ letter }}
            </span>
            <span class="title-divider">|</span>
            <span class="title-letter" v-for="(letter, index) in 'OMEGA'" :key="index + 5" :style="getLetterStyle(index + 5)">
              {{ letter }}
            </span>
          </h1>
          <p class="jarvis-subtitle">SYSTEM INITIALIZED</p>
          <div class="jarvis-status">
            <div class="status-item">
              <span class="status-label">CORE</span>
              <span class="status-value status-online">ONLINE</span>
            </div>
            <div class="status-item">
              <span class="status-label">MERLIN</span>
              <span class="status-value status-ready">READY</span>
            </div>
            <div class="status-item">
              <span class="status-label">SYSTEM</span>
              <span class="status-value status-active">ACTIVE</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Side panels -->
      <div class="side-panel left-panel">
        <div class="panel-header">DATA STREAM</div>
        <div class="panel-content">
          <div v-for="i in 8" :key="i" class="data-row">
            <span class="data-label">PACKET_{{ i.toString().padStart(3, '0') }}</span>
            <span class="data-value">{{ (Math.random() * 100).toFixed(2) }} MB/s</span>
          </div>
        </div>
      </div>
      <div class="side-panel right-panel">
        <div class="panel-header">SYSTEM METRICS</div>
        <div class="panel-content">
          <div class="metric-row">
            <span class="metric-label">CPU</span>
            <div class="metric-bar">
              <div class="metric-fill" :style="{ width: '45%' }"></div>
            </div>
            <span class="metric-value">45%</span>
          </div>
          <div class="metric-row">
            <span class="metric-label">MEMORY</span>
            <div class="metric-bar">
              <div class="metric-fill" :style="{ width: '62%' }"></div>
            </div>
            <span class="metric-value">62%</span>
          </div>
          <div class="metric-row">
            <span class="metric-label">NETWORK</span>
            <div class="metric-bar">
              <div class="metric-fill" :style="{ width: '78%' }"></div>
            </div>
            <span class="metric-value">78%</span>
          </div>
          <div class="metric-row">
            <span class="metric-label">STORAGE</span>
            <div class="metric-bar">
              <div class="metric-fill" :style="{ width: '34%' }"></div>
            </div>
            <span class="metric-value">34%</span>
          </div>
        </div>
      </div>
    </section>

    <!-- ═══ JARVIS COMMAND CENTER ═══ -->
    <section class="jarvis-commands">
      <div class="command-grid">
        <div @click="navigateTo('/merlin')" class="command-card jarvis-card">
          <div class="card-icon">🧙</div>
          <div class="card-title">MERLIN</div>
          <div class="card-desc">AI Assistant</div>
          <div class="card-status">ACTIVE</div>
          <div class="card-decoration"></div>
        </div>
        <div @click="navigateTo('/targets/discovery')" class="command-card jarvis-card">
          <div class="card-icon">🎯</div>
          <div class="card-title">DISCOVERY</div>
          <div class="card-desc">Target Analysis</div>
          <div class="card-status">SCANNING</div>
          <div class="card-decoration"></div>
        </div>
        <div @click="navigateTo('/intelligence/findings')" class="command-card jarvis-card">
          <div class="card-icon">🔍</div>
          <div class="card-title">INTEL</div>
          <div class="card-desc">Findings Database</div>
          <div class="card-status">SYNCED</div>
          <div class="card-decoration"></div>
        </div>
        <div @click="navigateTo('/reports/queue')" class="command-card jarvis-card">
          <div class="card-icon">📊</div>
          <div class="card-title">REPORTS</div>
          <div class="card-desc">Report Queue</div>
          <div class="card-status">PENDING</div>
          <div class="card-decoration"></div>
        </div>
        <div @click="navigateTo('/capital')" class="command-card jarvis-card">
          <div class="card-icon">💰</div>
          <div class="card-title">CAPITAL</div>
          <div class="card-desc">Financial Hub</div>
          <div class="card-status">ANALYZING</div>
          <div class="card-decoration"></div>
        </div>
        <div @click="navigateTo('/operations/version-backup')" class="command-card jarvis-card">
          <div class="card-icon">💾</div>
          <div class="card-title">BACKUP</div>
          <div class="card-desc">Version Control</div>
          <div class="card-status">SECURE</div>
          <div class="card-decoration"></div>
        </div>
      </div>
    </section>

    <!-- ═══ JARVIS VOICE WAVE ═══ -->
    <section class="jarvis-voice">
      <div class="voice-container">
        <div class="voice-wave">
          <div v-for="i in 20" :key="i" class="wave-bar" :style="getWaveStyle(i)"></div>
        </div>
        <div class="voice-text">VOICE INTERFACE ACTIVE</div>
      </div>
    </section>

    <!-- ═══ JARVIS TIMELINE ═══ -->
    <section class="jarvis-timeline">
      <div class="timeline-header">SYSTEM ACTIVITY</div>
      <div class="timeline-content">
        <div v-for="activity in activities" :key="activity.id" class="timeline-item">
          <div class="timeline-marker"></div>
          <div class="timeline-content">
            <div class="timeline-time">{{ activity.time }}</div>
            <div class="timeline-title">{{ activity.title }}</div>
            <div class="timeline-desc">{{ activity.desc }}</div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const activities = ref([
  { id: 1, time: '12:45:32', title: 'SYSTEM INITIALIZED', desc: 'Core services started successfully' },
  { id: 2, time: '12:45:30', title: 'MERLIN ONLINE', desc: 'AI assistant connected' },
  { id: 3, time: '12:45:28', title: 'DATABASE SYNC', desc: 'Local database synchronized' },
  { id: 4, time: '12:45:25', title: 'NETWORK ACTIVE', desc: 'Connection established' },
  { id: 5, time: '12:45:20', title: 'BOOT SEQUENCE', desc: 'System boot initiated' }
])

function navigateTo(path: string) {
  router.push(path)
}

function getParticleStyle(index: number) {
  const angle = (index / 50) * 360
  const distance = 200 + Math.random() * 300
  const x = Math.cos(angle * Math.PI / 180) * distance
  const y = Math.sin(angle * Math.PI / 180) * distance
  const size = 2 + Math.random() * 4
  const delay = Math.random() * 5
  const duration = 3 + Math.random() * 4

  return {
    left: `calc(50% + ${x}px)`,
    top: `calc(50% + ${y}px)`,
    width: `${size}px`,
    height: `${size}px`,
    animationDelay: `${delay}s`,
    animationDuration: `${duration}s`
  }
}

function getHexagonStyle(index: number) {
  const angle = (index / 20) * 360
  const distance = 250 + Math.random() * 150
  const x = Math.cos(angle * Math.PI / 180) * distance
  const y = Math.sin(angle * Math.PI / 180) * distance
  const size = 20 + Math.random() * 30
  const delay = Math.random() * 2

  return {
    left: `calc(50% + ${x}px)`,
    top: `calc(50% + ${y}px)`,
    width: `${size}px`,
    height: `${size}px`,
    animationDelay: `${delay}s`
  }
}

function getLetterStyle(index: number) {
  return {
    animationDelay: `${index * 0.1}s`
  }
}

function getWaveStyle(index: number) {
  const height = 20 + Math.random() * 60
  const delay = index * 0.05

  return {
    height: `${height}px`,
    animationDelay: `${delay}s`
  }
}
</script>

<style scoped>
/* ═══ JARVIS — HIGH-TECH HUD DESIGN ═══ */
.jarvis-welcome {
  background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 50%, #0d1b2a 100%);
  min-height: 100vh;
  position: relative;
  overflow: hidden;
  font-family: 'Rajdhani', 'Orbitron', 'Segoe UI', sans-serif;
  color: #00f0ff;
}

/* ═══ JARVIS HUD LAYER ═══ */
.jarvis-hud {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 1;
}

.scan-lines {
  position: absolute;
  inset: 0;
  background: repeating-linear-gradient(
    0deg,
    transparent,
    transparent 2px,
    rgba(0, 240, 255, 0.03) 2px,
    rgba(0, 240, 255, 0.03) 4px
  );
  animation: scan-move 8s linear infinite;
}

@keyframes scan-move {
  0% { transform: translateY(0); }
  100% { transform: translateY(100vh); }
}

.grid-overlay {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(0, 240, 255, 0.1) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0, 240, 255, 0.1) 1px, transparent 1px);
  background-size: 50px 50px;
  animation: grid-pulse 4s ease-in-out infinite;
}

@keyframes grid-pulse {
  0%, 100% { opacity: 0.3; }
  50% { opacity: 0.6; }
}

.particles-container {
  position: absolute;
  inset: 0;
}

.particle {
  position: absolute;
  background: radial-gradient(circle, rgba(0, 240, 255, 0.8) 0%, transparent 70%);
  border-radius: 50%;
  animation: particle-float infinite ease-in-out;
}

@keyframes particle-float {
  0%, 100% {
    transform: translate(0, 0) scale(1);
    opacity: 0.3;
  }
  50% {
    transform: translate(var(--tx, 0), var(--ty, 0)) scale(1.5);
    opacity: 0.8;
  }
}

.hexagon-grid {
  position: absolute;
  inset: 0;
}

.hexagon {
  position: absolute;
  border: 1px solid rgba(0, 240, 255, 0.2);
  clip-path: polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%);
  animation: hex-rotate 20s linear infinite;
}

@keyframes hex-rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* ═══ JARVIS HERO ═══ */
.jarvis-hero {
  position: relative;
  min-height: 80vh;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2;
}

.hero-center {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.central-ring {
  position: absolute;
  border-radius: 50%;
  border: 2px solid rgba(0, 240, 255, 0.3);
}

.outer-ring {
  width: 400px;
  height: 400px;
  animation: ring-rotate 30s linear infinite;
}

.middle-ring {
  width: 300px;
  height: 300px;
  animation: ring-rotate 20s linear infinite reverse;
}

.inner-ring {
  width: 200px;
  height: 200px;
  animation: ring-rotate 15s linear infinite;
}

@keyframes ring-rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.ring-segment {
  position: absolute;
  width: 100%;
  height: 100%;
  border-radius: 50%;
  border: 2px solid transparent;
  border-top-color: rgba(0, 240, 255, 0.6);
  border-right-color: rgba(0, 240, 255, 0.6);
  animation: segment-pulse 2s ease-in-out infinite;
}

.central-ring .ring-segment:nth-child(2) {
  transform: rotate(120deg);
  animation-delay: 0.5s;
}

.central-ring .ring-segment:nth-child(3) {
  transform: rotate(240deg);
  animation-delay: 1s;
}

@keyframes segment-pulse {
  0%, 100% { opacity: 0.3; }
  50% { opacity: 1; }
}

.core-dot {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 12px;
  height: 12px;
  background: #00f0ff;
  border-radius: 50%;
  box-shadow: 0 0 20px #00f0ff, 0 0 40px rgba(0, 240, 255, 0.5);
  animation: core-pulse 2s ease-in-out infinite;
}

@keyframes core-pulse {
  0%, 100% {
    transform: translate(-50%, -50%) scale(1);
    box-shadow: 0 0 20px #00f0ff, 0 0 40px rgba(0, 240, 255, 0.5);
  }
  50% {
    transform: translate(-50%, -50%) scale(1.2);
    box-shadow: 0 0 30px #00f0ff, 0 0 60px rgba(0, 240, 255, 0.7);
  }
}

.core-pulse {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 30px;
  height: 30px;
  background: radial-gradient(circle, rgba(0, 240, 255, 0.3) 0%, transparent 70%);
  border-radius: 50%;
  animation: core-expand 2s ease-in-out infinite;
}

@keyframes core-expand {
  0%, 100% {
    transform: translate(-50%, -50%) scale(1);
    opacity: 0.5;
  }
  50% {
    transform: translate(-50%, -50%) scale(2);
    opacity: 0;
  }
}

.hero-content {
  position: relative;
  z-index: 10;
  text-align: center;
  margin-top: 250px;
}

.jarvis-title {
  font-size: 4rem;
  font-weight: 700;
  letter-spacing: 0.2em;
  margin-bottom: 1rem;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
}

.title-letter {
  display: inline-block;
  color: #00f0ff;
  text-shadow: 0 0 10px #00f0ff, 0 0 20px rgba(0, 240, 255, 0.5);
  animation: letter-appear 0.5s ease-out forwards;
  opacity: 0;
}

@keyframes letter-appear {
  from {
    opacity: 0;
    transform: translateY(-20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.title-divider {
  color: #ff6b35;
  text-shadow: 0 0 10px #ff6b35;
  animation: divider-pulse 2s ease-in-out infinite;
}

@keyframes divider-pulse {
  0%, 100% { opacity: 0.5; }
  50% { opacity: 1; }
}

.jarvis-subtitle {
  font-size: 1.25rem;
  letter-spacing: 0.3em;
  color: #00f0ff;
  opacity: 0.8;
  margin-bottom: 2rem;
  animation: subtitle-fade 1s ease-out 1s forwards;
  opacity: 0;
}

@keyframes subtitle-fade {
  from { opacity: 0; }
  to { opacity: 0.8; }
}

.jarvis-status {
  display: flex;
  gap: 2rem;
  animation: status-fade 1s ease-out 1.5s forwards;
  opacity: 0;
}

@keyframes status-fade {
  from { opacity: 0; }
  to { opacity: 1; }
}

.status-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.25rem;
}

.status-label {
  font-size: 0.75rem;
  letter-spacing: 0.2em;
  color: rgba(0, 240, 255, 0.6);
}

.status-value {
  font-size: 1rem;
  font-weight: 700;
  letter-spacing: 0.1em;
}

.status-online {
  color: #00ff88;
  text-shadow: 0 0 10px #00ff88;
}

.status-ready {
  color: #00f0ff;
  text-shadow: 0 0 10px #00f0ff;
}

.status-active {
  color: #ff6b35;
  text-shadow: 0 0 10px #ff6b35;
}

/* ═══ SIDE PANELS ═══ */
.side-panel {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  width: 200px;
  background: rgba(10, 14, 39, 0.8);
  border: 1px solid rgba(0, 240, 255, 0.3);
  backdrop-filter: blur(10px);
  z-index: 5;
}

.left-panel {
  left: 2rem;
}

.right-panel {
  right: 2rem;
}

.panel-header {
  padding: 0.75rem;
  background: rgba(0, 240, 255, 0.1);
  border-bottom: 1px solid rgba(0, 240, 255, 0.3);
  font-size: 0.75rem;
  letter-spacing: 0.2em;
  text-align: center;
}

.panel-content {
  padding: 0.75rem;
}

.data-row {
  display: flex;
  justify-content: space-between;
  padding: 0.5rem 0;
  border-bottom: 1px solid rgba(0, 240, 255, 0.1);
  font-size: 0.7rem;
  letter-spacing: 0.1em;
}

.data-label {
  color: rgba(0, 240, 255, 0.6);
}

.data-value {
  color: #00f0ff;
}

.metric-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0;
  font-size: 0.7rem;
  letter-spacing: 0.1em;
}

.metric-label {
  width: 60px;
  color: rgba(0, 240, 255, 0.6);
}

.metric-bar {
  flex: 1;
  height: 4px;
  background: rgba(0, 240, 255, 0.1);
  border-radius: 2px;
  overflow: hidden;
}

.metric-fill {
  height: 100%;
  background: linear-gradient(90deg, #00f0ff, #00ff88);
  border-radius: 2px;
  animation: metric-pulse 2s ease-in-out infinite;
}

@keyframes metric-pulse {
  0%, 100% { opacity: 0.8; }
  50% { opacity: 1; }
}

.metric-value {
  width: 40px;
  text-align: right;
  color: #00f0ff;
}

/* ═══ JARVIS COMMANDS ═══ */
.jarvis-commands {
  position: relative;
  padding: 2rem;
  z-index: 2;
}

.command-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
  max-width: 1400px;
  margin: 0 auto;
}

.command-card {
  position: relative;
  background: rgba(10, 14, 39, 0.6);
  border: 1px solid rgba(0, 240, 255, 0.3);
  padding: 2rem;
  cursor: pointer;
  transition: all 0.3s;
  overflow: hidden;
  backdrop-filter: blur(10px);
}

.command-card::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, rgba(0, 240, 255, 0.1) 0%, transparent 50%);
  opacity: 0;
  transition: opacity 0.3s;
}

.command-card:hover::before {
  opacity: 1;
}

.command-card:hover {
  border-color: rgba(0, 240, 255, 0.6);
  transform: translateY(-5px);
  box-shadow: 0 10px 30px rgba(0, 240, 255, 0.2);
}

.card-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
  filter: drop-shadow(0 0 10px rgba(0, 240, 255, 0.5));
}

.card-title {
  font-size: 1.25rem;
  font-weight: 700;
  letter-spacing: 0.15em;
  color: #00f0ff;
  margin-bottom: 0.5rem;
}

.card-desc {
  font-size: 0.875rem;
  color: rgba(0, 240, 255, 0.6);
  letter-spacing: 0.1em;
  margin-bottom: 1rem;
}

.card-status {
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.2em;
  color: #00ff88;
}

.card-decoration {
  position: absolute;
  bottom: 0;
  right: 0;
  width: 50px;
  height: 50px;
  border-right: 2px solid rgba(0, 240, 255, 0.3);
  border-bottom: 2px solid rgba(0, 240, 255, 0.3);
}

/* ═══ JARVIS VOICE WAVE ═══ */
.jarvis-voice {
  position: relative;
  padding: 2rem;
  z-index: 2;
}

.voice-container {
  max-width: 600px;
  margin: 0 auto;
  text-align: center;
}

.voice-wave {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.25rem;
  height: 100px;
  margin-bottom: 1rem;
}

.wave-bar {
  width: 4px;
  background: linear-gradient(to top, #00f0ff, #00ff88);
  border-radius: 2px;
  animation: wave-animation 1s ease-in-out infinite;
}

@keyframes wave-animation {
  0%, 100% {
    transform: scaleY(0.3);
  }
  50% {
    transform: scaleY(1);
  }
}

.voice-text {
  font-size: 0.875rem;
  letter-spacing: 0.3em;
  color: rgba(0, 240, 255, 0.6);
}

/* ═══ JARVIS TIMELINE ═══ */
.jarvis-timeline {
  position: relative;
  padding: 2rem;
  z-index: 2;
}

.timeline-header {
  font-size: 1rem;
  letter-spacing: 0.2em;
  color: #00f0ff;
  margin-bottom: 1.5rem;
  text-align: center;
}

.timeline-content {
  max-width: 600px;
  margin: 0 auto;
}

.timeline-item {
  display: flex;
  gap: 1rem;
  padding: 1rem;
  border-left: 2px solid rgba(0, 240, 255, 0.3);
  margin-left: 1rem;
  position: relative;
}

.timeline-item::before {
  content: '';
  position: absolute;
  left: -1px;
  top: 1rem;
  width: 8px;
  height: 8px;
  background: #00f0ff;
  border-radius: 50%;
  transform: translateX(-50%);
  box-shadow: 0 0 10px #00f0ff;
}

.timeline-time {
  font-size: 0.75rem;
  color: rgba(0, 240, 255, 0.5);
  letter-spacing: 0.1em;
  margin-bottom: 0.25rem;
}

.timeline-title {
  font-size: 0.875rem;
  font-weight: 700;
  color: #00f0ff;
  letter-spacing: 0.1em;
  margin-bottom: 0.25rem;
}

.timeline-desc {
  font-size: 0.75rem;
  color: rgba(0, 240, 255, 0.6);
  letter-spacing: 0.05em;
}
</style>