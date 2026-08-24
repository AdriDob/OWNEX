<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import {
  getVpnInfo, checkVpnOutlier, installWindscribe, connectWindscribeWindows,
  type VpnInfo, type WindscribeConnect,
} from '@/services/controlPanel'

const vpn = ref<VpnInfo | null>(null)
const loading = ref(true)
const busy = ref('')

async function load() {
  loading.value = true
  try {
    vpn.value = await getVpnInfo()
  } finally {
    loading.value = false
  }
}

async function check() {
  if (busy.value) return
  busy.value = 'check'
  try {
    const res = await checkVpnOutlier()
    if (vpn.value) vpn.value.status = res
  } finally {
    busy.value = ''
  }
}

async function doInstall() {
  if (busy.value) return
  busy.value = 'install'
  try {
    await installWindscribe()
    await load()
  } finally {
    busy.value = ''
  }
}

async function doConnect() {
  if (busy.value) return
  busy.value = 'connect'
  try {
    const res = await connectWindscribeWindows()
    if (vpn.value && res) {
      vpn.value.vpn_plan = res.next_steps || []
      vpn.value.status = { ...vpn.value.status, compatible: res.success }
    }
    await load()
  } finally {
    busy.value = ''
  }
}

const statusColor = computed(() => vpn.value?.status?.compatible ? '#16a34a' : '#00d5ff')
const statusText = computed(() => vpn.value?.status?.compatible ? 'COMPATIBLE ✅' : 'BLOQUEADO ❌')
const isWSL = computed(() => vpn.value?.is_wsl)

onMounted(load)
</script>

<template>
  <section class="vpn">
    <div class="vpn-head">
      <h3 class="vpn-title">🛡️ VPN GRATIS — Outlier / DataAnnotation</h3>
      <span class="vpn-badge" :style="{ color: statusColor }">{{ statusText }}</span>
    </div>

    <p v-if="loading" class="vpn-muted">Detectando conexión...</p>

    <template v-else>
      <!-- Status -->
      <div class="vpn-status" v-if="vpn?.status">
        <div class="vpn-status-row">
          <span class="vpn-label">IP pública</span>
          <span class="vpn-value">{{ vpn.status.public_ip || '—' }}</span>
        </div>
        <div class="vpn-status-row">
          <span class="vpn-label">País</span>
          <span class="vpn-value">{{ vpn.status.country_name }} ({{ vpn.status.country_code }})</span>
        </div>
        <div class="vpn-status-row">
          <span class="vpn-label">ISP / Proveedor</span>
          <span class="vpn-value">{{ vpn.status.isp }}</span>
        </div>
        <p class="vpn-reason">{{ vpn.status.reason || '—' }}</p>
      </div>

<!-- OS Context -->
      <div v-if="vpn" class="vpn-os">
        <span class="vpn-tag" :class="{ wsl: isWSL }">
          {{ vpn.os }} {{ isWSL ? '· WSL2' : '' }}
        </span>
        <span v-if="isWSL" class="vpn-hint">⚠️ VPN debe instalarse en WINDOWS (host), no solo en WSL. Windscribe se instala en Windows, la VPN opera en Windows.</span>
      </div>

      <!-- Action Buttons -->
      <div class="vpn-actions">
        <button class="vpn-btn check" :disabled="busy" @click="check">
          {{ busy === 'check' ? 'Chequeando...' : '🔄 Chequear ahora' }}
        </button>
        <button class="vpn-btn install" :disabled="busy" @click="doInstall">
          {{ busy === 'install' ? 'Instalando...' : '📥 Instalar Windscribe (Linux)' }}
        </button>
        <button class="vpn-btn connect" :disabled="busy" @click="doConnect">
          {{ busy === 'connect' ? 'Conectando...' : '🔗 Abrir Windscribe (Windows)' }}
        </button>
      </div>

      <!-- What you have / missing -->
      <div class="vpn-vpns" v-if="vpn?.vpns?.length">
        <h4 class="vpn-sub">Tus VPNs gratis</h4>
        <div v-for="v in vpn.vpns" :key="v.key" class="vpn-item">
          <span class="vpn-dot" :class="{ ok: v.installed }" />
          <span class="vpn-name">{{ v.name }}</span>
          <span class="vpn-free">{{ v.free }}</span>
          <span class="vpn-state" :style="{ color: v.installed ? '#16a34a' : '#94a3b8' }">
            {{ v.installed ? 'LISTA' : 'FALTA' }}
          </span>
        </div>
      </div>

      <!-- Plan -->
      <div class="vpn-plan" v-if="vpn?.vpn_plan?.length">
        <h4 class="vpn-sub">Plan de intercalado</h4>
        <ol class="vpn-steps">
          <li v-for="(s, i) in vpn.vpn_plan" :key="i">{{ s }}</li>
        </ol>
      </div>

      <!-- Quick links -->
      <div class="vpn-links">
        <a href="https://windscribe.com/download" target="_blank" class="vpn-link">Descargar Windscribe (Windows)</a>
        <a href="https://protonvpn.com/download-windows" target="_blank" class="vpn-link">Descargar ProtonVPN (Windows)</a>
      </div>
    </template>
  </section>
</template>

<style scoped>
.vpn { border: 1px solid var(--ownex-stroke, #2a2e37); border-radius: 12px; background: var(--ownex-surface, #111318); padding: 1rem; display: flex; flex-direction: column; gap: 0.7rem; }
.vpn-head { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 0.5rem; }
.vpn-title { margin: 0; font-size: 0.85rem; letter-spacing: 0.12em; }
.vpn-badge { font-size: 0.6rem; font-weight: 700; padding: 0.2rem 0.5rem; border-radius: 6px; border: 1px solid currentColor; }
.vpn-muted { font-size: 0.72rem; color: rgba(255,255,255,0.5); margin: 0; }
.vpn-status { display: flex; flex-direction: column; gap: 0.3rem; font-size: 0.7rem; color: rgba(255,255,255,0.8); background: rgba(255,255,255,0.02); border-radius: 8px; padding: 0.6rem; }
.vpn-status-row { display: flex; justify-content: space-between; }
.vpn-label { color: rgba(255,255,255,0.5); }
.vpn-value { font-family: monospace; font-size: 0.68rem; }
.vpn-reason { margin: 0.3rem 0 0; font-size: 0.62rem; color: rgba(255,255,255,0.6); line-height: 1.4; }
.vpn-os { display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; font-size: 0.65rem; }
.vpn-tag { background: rgba(96,165,250,0.12); border: 1px solid rgba(96,165,250,0.3); border-radius: 6px; padding: 0.15rem 0.45rem; color: #93c5fd; font-weight: 600; }
.vpn-tag.wsl { background: rgba(251,191,36,0.12); border-color: rgba(251,191,36,0.3); color: #fbbf24; }
.vpn-hint { color: #94a3b8; }
.vpn-actions { display: flex; gap: 0.4rem; flex-wrap: wrap; }
.vpn-btn { border: none; border-radius: 8px; padding: 0.45rem 0.75rem; font-size: 0.68rem; font-weight: 600; cursor: pointer; transition: all 0.15s; }
.vpn-btn.check { background: rgba(96,165,250,0.15); border: 1px solid rgba(96,165,250,0.4); color: #93c5fd; }
.vpn-btn.check:hover:not(:disabled) { background: rgba(96,165,250,0.25); }
.vpn-btn.install { background: rgba(251,191,36,0.15); border: 1px solid rgba(251,191,36,0.4); color: #fbbf24; }
.vpn-btn.install:hover:not(:disabled) { background: rgba(251,191,36,0.25); }
.vpn-btn.connect { background: rgba(22,163,74,0.15); border: 1px solid rgba(22,163,74,0.4); color: #4ade80; }
.vpn-btn.connect:hover:not(:disabled) { background: rgba(22,163,74,0.25); box-shadow: 0 0 10px 3px rgba(22,132,54,0.3); }
.vpn-btn:disabled { opacity: 0.5; cursor: wait; }
.vpn-vpns { display: flex; flex-direction: column; gap: 0.35rem; }
.vpn-sub { font-size: 0.65rem; text-transform: uppercase; letter-spacing: 0.1em; color: rgba(255,255,255,0.45); margin: 0; }
.vpn-item { display: flex; align-items: center; gap: 0.5rem; padding: 0.4rem 0.5rem; background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06); border-radius: 8px; }
.vpn-dot { width: 8px; height: 8px; border-radius: 50%; background: rgba(255,255,255,0.2); }
.vpn-dot.ok { background: #16a34a; box-shadow: 0 0 6px #16a34a; }
.vpn-name { font-size: 0.7rem; font-weight: 600; flex: 1; }
.vpn-free { font-size: 0.58rem; color: rgba(255,255,255,0.5); }
.vpn-state { font-size: 0.58rem; font-weight: 700; }
.vpn-plan { display: flex; flex-direction: column; gap: 0.25rem; }
.vpn-steps { margin: 0; padding-left: 1.2rem; font-size: 0.62rem; color: rgba(255,255,255,0.7); line-height: 1.5; }
.vpn-links { display: flex; gap: 0.6rem; flex-wrap: wrap; margin-top: 0.2rem; }
.vpn-link { font-size: 0.62rem; color: #93c5fd; text-decoration: none; border-bottom: 1px dashed transparent; transition: border-color 0.15s; }
.vpn-link:hover { border-bottom-color: #93c5fd; }
</style>