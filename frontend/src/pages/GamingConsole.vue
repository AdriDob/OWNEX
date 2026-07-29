<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import {
  Activity, Clock, RefreshCw, Shield,
  DollarSign, FileText, BarChart3, HeartPulse,
  Zap, AlertTriangle, Target, Sparkles,
  Cpu, Radio, Layers, TrendingUp, ChevronRight,
} from '@lucide/vue'
import LoadingState from '@/components/ui/LoadingState.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import { fetchOwnexDashboard } from '@/services/ownexData'
import type { OwnexDashboardData } from '@/services/ownexData'

const router = useRouter()
const dashboard = ref<OwnexDashboardData | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
let refreshInterval: ReturnType<typeof setInterval> | null = null

const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 12) return 'Good morning'
  if (h < 18) return 'Good afternoon'
  return 'Good evening'
})

const systemHealthColor = computed(() => {
  const score = dashboard.value?.systemHealth ?? 0
  if (score >= 90) return '#34D399'
  if (score >= 70) return '#FBBF24'
  return '#F87171'
})

function handleQuickAction(path: string) {
  router.push(path)
}

// Fake activity log entries — in production these come from the API
const activityLog = ref([
  { time: '14:00:32', type: 'success', msg: 'Forge Agent · Discovered 3 new bounties on Superteam' },
  { time: '13:45:10', type: 'info', msg: 'Pulse Agent · Completed Outlier task #4421 · $85 earned' },
  { time: '13:22:00', type: 'finding', msg: 'Security Agent · Validated SQLi on admin.example.com · Finding #1293 created' },
  { time: '12:58:44', type: 'warn', msg: 'Resource Manager · Cleaned 142MB of temp files · DB vacuumed' },
  { time: '12:30:15', type: 'success', msg: 'Learning Agent · Extracted 5 patterns from accepted findings' },
  { time: '12:00:00', type: 'success', msg: 'System Health Check · All 48 checks passed · Score: 95%' },
  { time: '11:15:30', type: 'finding', msg: 'Vault Agent · New payout: $350 from HackerOne accepted' },
  { time: '10:30:00', type: 'info', msg: 'Model Router · Routed research task to fcc-claude-haiku · Cost: $0.001' },
])

const activityIcon = (type: string) => {
  const map: Record<string, string> = {
    success: '\u2705', finding: '\u2B50', warn: '\u26A0\uFE0F', info: '\u2139\uFE0F'
  }
  return map[type] || '\u2139\uFE0F'
}
const activityColor = (type: string) => {
  const map: Record<string, string> = {
    success: '#34D399', finding: '#FBBF24', warn: '#F87171', info: '#60A5FA'
  }
  return map[type] || '#64748B'
}

const topOpportunities = computed(() => {
  if (!dashboard.value?.opportunities) return []
  return [...dashboard.value.opportunities]
    .sort((a: any, b: any) => (b.score?.overall || 0) - (a.score?.overall || 0))
    .slice(0, 5)
})

const totalEarnings = computed(() => {
  if (!dashboard.value) return '$0'
  return `$${(dashboard.value as any).weeklyRevenue || 0}`
})

async function load() {
  try {
    const data = await fetchOwnexDashboard()
    dashboard.value = data
    error.value = null
  } catch (e: any) {
    if (!dashboard.value) {
      error.value = e?.message || 'Error loading dashboard'
    }
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  load()
  refreshInterval = setInterval(load, 30000)
})
onUnmounted(() => {
  if (refreshInterval) clearInterval(refreshInterval)
})
</script>

<template>
  <!-- ═══ GAMING CONSOLE HOME ═══ -->
  <div class="gaming-console">

    <!-- Loading state -->
    <template v-if="loading && !dashboard">
      <div class="flex items-center justify-center h-screen">
        <div class="text-center">
          <div class="w-16 h-16 mx-auto mb-4 rounded-full border-2 border-primary/30 border-t-primary animate-spin" />
          <p class="text-muted text-sm">Boot sequence initializing...</p>
        </div>
      </div>
    </template>

    <!-- Error state -->
    <template v-else-if="error && !dashboard">
      <div class="flex items-center justify-center h-screen">
        <ErrorState :message="error" @retry="load" />
      </div>
    </template>

    <!-- Main dashboard -->
    <template v-else>
      <!-- ═══ TOP BAR ═══ -->
      <header class="top-bar">
        <div class="flex items-center gap-3">
          <!-- Logo mark -->
          <div class="relative w-9 h-9">
            <div class="absolute inset-0 rounded-full border border-primary/40" />
            <div class="absolute inset-[3px] rounded-full border border-primary/20" />
            <div class="absolute inset-[8px] rounded-full bg-primary/20" />
            <div class="absolute inset-[11px] rounded-full bg-primary" />
          </div>
          <span class="text-lg font-bold tracking-widest text-white font-display">OWNEX</span>
          <span class="text-[10px] text-muted tracking-wider">v4.7.0</span>

          <!-- Cycle pills -->
          <div class="nav-pills">
            <span class="pill pill-forge">FORGE</span>
            <span class="pill pill-pulse">PULSE</span>
            <span class="pill pill-vault">VAULT</span>
            <span class="pill pill-atlas">ATLAS</span>
            <span class="pill pill-security">SECURITY</span>
          </div>
        </div>

        <div class="flex items-center gap-4">
          <div class="flex items-center gap-2">
            <span class="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
            <span class="text-xs text-green-400 font-semibold">ALL SYSTEMS OPERATIONAL</span>
          </div>
          <div class="live-badge">LIVE</div>
        </div>
      </header>

      <!-- ═══ HERO SECTION ═══ -->
      <section class="hero-section">
        <div class="flex items-start gap-8">
          <!-- Big 'O' mark -->
          <div class="relative w-32 h-32 flex-shrink-0 hidden lg:block">
            <div class="o-ring o-ring-outer" />
            <div class="o-ring o-ring-inner" />
            <div class="o-dot" />
            <div class="o-core" />
          </div>

          <div class="flex-1">
            <h1 class="text-3xl md:text-4xl font-bold text-white font-display tracking-wide">
              {{ greeting }}, Commander
            </h1>
            <p class="text-muted mt-2">
              All systems operational · 4 active cycles · 0 pending approvals
            </p>
            <div class="flex flex-wrap gap-3 mt-6">
              <button class="action-pill action-primary" @click="handleQuickAction('/integrations/platforms')">
                <Zap class="w-4 h-4" /> Run Forge
              </button>
              <button class="action-pill action-green" @click="handleQuickAction('/pulse')">
                <Activity class="w-4 h-4" /> Run Pulse
              </button>
              <button class="action-pill action-gold" @click="handleQuickAction('/capital')">
                <DollarSign class="w-4 h-4" /> Review Vault
              </button>
              <button class="action-pill action-red" @click="handleQuickAction('/targets')">
                <Shield class="w-4 h-4" /> Quick Scan
              </button>
            </div>
          </div>
        </div>
      </section>

      <!-- ═══ KPI CARDS GRID ═══ -->
      <section class="cards-grid">
        <!-- Revenue -->
        <div class="card">
          <div class="card-label">REVENUE THIS MONTH</div>
          <div class="card-value text-green-400">{{ totalEarnings }}</div>
          <div class="card-change positive">↑ 24% vs last month</div>
          <div class="mini-chart">
            <div class="bar" style="height: 40%" />
            <div class="bar" style="height: 50%" />
            <div class="bar" style="height: 60%" />
            <div class="bar active" style="height: 75%" />
          </div>
        </div>

        <!-- Active Opportunities -->
        <div class="card">
          <div class="card-label">ACTIVE OPPORTUNITIES</div>
          <div class="card-value text-primary">{{ dashboard?.opportunities?.length || 23 }}</div>
          <div class="card-detail">8 Forge · 5 Pulse · 4 Vault · 6 Security</div>
        </div>

        <!-- System Health -->
        <div class="card">
          <div class="card-label">SYSTEM HEALTH</div>
          <div class="flex items-center gap-6">
            <svg class="w-24 h-24 -rotate-90" viewBox="0 0 100 100">
              <circle cx="50" cy="50" r="42" fill="none" stroke="rgba(30,41,59,0.5)" stroke-width="6" />
              <circle cx="50" cy="50" r="42" fill="none" :stroke="systemHealthColor" stroke-width="6"
                stroke-dasharray="264" :stroke-dashoffset="264 - (264 * (dashboard?.systemHealth ?? 95) / 100)"
                stroke-linecap="round" class="transition-all duration-1000" />
            </svg>
            <div>
              <div class="text-2xl font-bold font-display" :style="{ color: systemHealthColor }">
                {{ dashboard?.systemHealth || 95 }}%
              </div>
              <div class="text-xs text-muted mt-2">
                <div class="flex items-center gap-2"><span class="w-1.5 h-1.5 rounded-full bg-green-400" /> API Server</div>
                <div class="flex items-center gap-2"><span class="w-1.5 h-1.5 rounded-full bg-green-400" /> Scheduler</div>
                <div class="flex items-center gap-2"><span class="w-1.5 h-1.5 rounded-full bg-red-400" /> Keys: 3/28 configured</div>
              </div>
            </div>
          </div>
        </div>

        <!-- Top Opportunities Mini -->
        <div class="card">
          <div class="card-label">TOP OPPORTUNITIES</div>
          <div class="space-y-2">
            <div v-for="(opp, i) in topOpportunities" :key="opp.id"
              class="flex items-center justify-between py-1 border-b border-white/5 last:border-0 cursor-pointer hover:bg-white/5 px-1 rounded transition-colors"
              @click="handleQuickAction('/opportunities')">
              <div class="flex items-center gap-2">
                <span class="text-xs font-bold" :class="{
                  'text-amber-400': i === 0, 'text-amber-300': i === 1,
                  'text-amber-200': i === 2, 'text-muted': i > 2
                }">
                  {{ ['\uD83E\uDD47', '\uD83E\uDD48', '\uD83E\uDD49'][i] || `${i + 1}.` }}
                </span>
                <span class="text-xs truncate max-w-[180px]">{{ opp.name }}</span>
              </div>
              <span class="text-xs font-mono font-semibold" :class="i < 3 ? 'text-green-400' : 'text-muted'">
                ${{ opp.reward?.toLocaleString() || 0 }}
              </span>
            </div>
          </div>
        </div>
      </section>

      <!-- ═══ AGENT FLEET ═══ -->
      <section class="mt-8">
        <h2 class="section-title">
          <Cpu class="w-4 h-4" /> AGENT FLEET
        </h2>
        <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4 mt-4">
          <div class="agent-card agent-forge">
            <div class="flex items-center gap-2 mb-2">
              <span class="w-2 h-2 rounded-full bg-green-400" />
              <span class="font-semibold text-sm text-cyan-400">\uD83D\uDD28 Forge Agent</span>
            </div>
            <p class="text-xs text-muted">7 bounties active · next run in 12m</p>
            <p class="text-xs text-muted">Uptime: 72h · Score: 95%</p>
          </div>

          <div class="agent-card agent-pulse">
            <div class="flex items-center gap-2 mb-2">
              <span class="w-2 h-2 rounded-full bg-green-400" />
              <span class="font-semibold text-sm text-green-400">\u26A1 Pulse Agent</span>
            </div>
            <p class="text-xs text-muted">3 tasks queued · next run in 1h</p>
            <p class="text-xs text-muted">Uptime: 48h · Score: 88%</p>
          </div>

          <div class="agent-card agent-security">
            <div class="flex items-center gap-2 mb-2">
              <span class="w-2 h-2 rounded-full bg-purple-400" />
              <span class="font-semibold text-sm text-purple-400">\uD83D\uDD10 Security Agent</span>
            </div>
            <p class="text-xs text-muted">2 pipelines running · 5 findings</p>
            <p class="text-xs text-muted">Uptime: 24h · Score: 92%</p>
          </div>

          <div class="agent-card agent-research">
            <div class="flex items-center gap-2 mb-2">
              <span class="w-2 h-2 rounded-full bg-blue-400" />
              <span class="font-semibold text-sm text-blue-400">\uD83D\uDD0D Research Agent</span>
            </div>
            <p class="text-xs text-muted">Recon in progress · 12 targets</p>
            <p class="text-xs text-muted">Uptime: 24h · Score: 85%</p>
          </div>

          <div class="agent-card agent-learning">
            <div class="flex items-center gap-2 mb-2">
              <span class="w-2 h-2 rounded-full bg-amber-400" />
              <span class="font-semibold text-sm text-amber-400">\uD83E\uDDE0 Learning Agent</span>
            </div>
            <p class="text-xs text-muted">142 patterns captured</p>
            <p class="text-xs text-muted">Signal: 78% · Noise: 22%</p>
          </div>
        </div>
      </section>

      <!-- ═══ ACTIVITY LOG ═══ -->
      <section class="mt-8">
        <h2 class="section-title">
          <Radio class="w-4 h-4" /> ACTIVITY LOG
        </h2>
        <div class="activity-log mt-4">
          <div class="activity-log-inner">
            <div v-for="(log, i) in activityLog" :key="i"
              class="activity-row"
              :style="{ animationDelay: `${i * 0.05}s` }">
              <span class="text-mono text-xs text-muted w-16 shrink-0">{{ log.time }}</span>
              <span class="text-xs w-5 text-center shrink-0" :style="{ color: activityColor(log.type) }">
                {{ activityIcon(log.type) }}
              </span>
              <span class="text-xs text-muted truncate">{{ log.msg }}</span>
            </div>
          </div>
        </div>
      </section>

      <!-- Bottom bar -->
      <footer class="bottom-bar">
        <span class="text-[10px] text-muted">OWNEX v4.7.0 · Autonomous Work OS · Built by CATEYE Research</span>
        <span class="text-[10px] text-muted">Agents: 5 online · Uptime: 72h 14m</span>
      </footer>
    </template>
  </div>
</template>

<style scoped>
/* ═══ Gaming Console Theme ═══ */

.gaming-console {
  min-height: 100vh;
  background-color: #05060A;
  color: white;
  font-family: var(--font-sans, 'Inter', ui-sans-serif, system-ui, sans-serif);
  overflow-x: hidden;
  background-image:
    radial-gradient(ellipse at 25% 50%, rgba(59,130,246,0.03) 0%, transparent 60%),
    radial-gradient(ellipse at 75% 50%, rgba(245,158,11,0.02) 0%, transparent 50%),
    repeating-linear-gradient(0deg, transparent, transparent 3px, rgba(255,255,255,0.008) 3px, rgba(255,255,255,0.008) 4px);
}

/* Top bar */
.top-bar {
  position: sticky;
  top: 0;
  z-index: 50;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1.5rem;
  background-color: rgba(5, 6, 10, 0.9);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.nav-pills {
  display: none;
  align-items: center;
  gap: 0.5rem;
  margin-left: 2rem;
}
@media (min-width: 1024px) {
  .nav-pills { display: flex; }
}

.pill {
  padding: 0.25rem 0.75rem;
  font-size: 11px;
  font-weight: 600;
  border-radius: 9999px;
  border: 1px solid;
  cursor: pointer;
  transition: all 0.15s ease;
}
.pill:hover { opacity: 0.8; }
.pill-forge { color: #22D3EE; border-color: rgba(6, 182, 212, 0.3); background-color: rgba(6, 182, 212, 0.1); }
.pill-pulse { color: #4ADE80; border-color: rgba(34, 197, 94, 0.3); background-color: rgba(34, 197, 94, 0.1); }
.pill-vault { color: #FBBF24; border-color: rgba(245, 158, 11, 0.3); background-color: rgba(245, 158, 11, 0.1); }
.pill-atlas { color: #A78BFA; border-color: rgba(168, 85, 247, 0.3); background-color: rgba(168, 85, 247, 0.1); }
.pill-security { color: #F87171; border-color: rgba(239, 68, 68, 0.3); background-color: rgba(239, 68, 68, 0.1); }

.live-badge {
  padding: 0.25rem 1rem;
  font-size: 10px;
  font-weight: 700;
  border-radius: 9999px;
  border: 1px solid #22D3EE;
  color: #22D3EE;
  background-color: rgba(34, 211, 238, 0.1);
}

/* Hero section */
.hero-section {
  padding: 2.5rem 1.5rem;
}

.o-ring {
  position: absolute;
  border-radius: 9999px;
}
.o-ring-outer {
  top: 0; right: 0; bottom: 0; left: 0;
  border: 2px solid rgba(0, 112, 209, 0.4);
}
.o-ring-inner {
  top: 16px; right: 16px; bottom: 16px; left: 16px;
  border: 1px solid rgba(0, 112, 209, 0.2);
}
.o-dot {
  position: absolute;
  top: 18px;
  right: 18px;
  width: 0.375rem;
  height: 0.375rem;
  border-radius: 9999px;
  background-color: #FBBF24;
  box-shadow: 0 10px 15px -3px rgba(251, 191, 36, 0.5);
}
.o-core {
  position: absolute;
  top: 36px; right: 36px; bottom: 36px; left: 36px;
  border-radius: 9999px;
  background-color: rgba(0, 112, 209, 0.2);
}
.o-core::after {
  content: '';
  position: absolute;
  top: 8px; right: 8px; bottom: 8px; left: 8px;
  border-radius: 9999px;
  background-color: rgba(0, 112, 209, 0.6);
}

/* Action pills */
.action-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.625rem 1.25rem;
  font-size: 0.75rem;
  font-weight: 600;
  border-radius: 9999px;
  border: 1px solid;
  transition: all 0.15s ease;
  cursor: pointer;
}
.action-pill:hover { opacity: 0.8; transform: translateY(-2px); }
.action-primary { color: #22D3EE; border-color: rgba(6, 182, 212, 0.4); background-color: rgba(6, 182, 212, 0.15); }
.action-green { color: #4ADE80; border-color: rgba(34, 197, 94, 0.4); background-color: rgba(34, 197, 94, 0.15); }
.action-gold { color: #FBBF24; border-color: rgba(245, 158, 11, 0.4); background-color: rgba(245, 158, 11, 0.15); }
.action-red { color: #F87171; border-color: rgba(239, 68, 68, 0.4); background-color: rgba(239, 68, 68, 0.15); }

/* Cards grid */
.cards-grid {
  display: grid;
  grid-template-columns: repeat(1, 1fr);
  gap: 1rem;
  padding: 0 1.5rem;
}
@media (min-width: 768px) {
  .cards-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (min-width: 1024px) {
  .cards-grid { grid-template-columns: repeat(4, 1fr); }
}

.card {
  position: relative;
  border-radius: 1rem;
  padding: 1.25rem;
  border: 1px solid rgba(255, 255, 255, 0.05);
  background-color: rgba(255, 255, 255, 0.03);
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
  overflow: hidden;
  transition: all 0.15s ease;
}
.card:hover {
  border-color: rgba(255, 255, 255, 0.1);
  background-color: rgba(255, 255, 255, 0.05);
  box-shadow: 0 0 30px rgba(59,130,246,0.05);
}

.card-label {
  font-size: 11px;
  color: var(--color-muted, #52525b);
  letter-spacing: 0.05em;
  margin-bottom: 0.75rem;
  font-weight: 500;
}

.card-value {
  font-size: 2.25rem;
  font-weight: 700;
  font-family: 'Space Grotesk', 'Inter', sans-serif;
}

.card-change {
  font-size: 0.75rem;
  margin-top: 0.25rem;
}
.card-change.positive { color: #4ADE80; }

.card-detail {
  font-size: 0.75rem;
  color: var(--color-muted, #52525b);
  margin-top: 0.5rem;
}

/* Mini chart */
.mini-chart {
  position: absolute;
  bottom: 1rem;
  right: 1.5rem;
  display: flex;
  align-items: flex-end;
  gap: 0.25rem;
  height: 4rem;
}
.mini-chart .bar {
  width: 0.75rem;
  border-radius: 2px 2px 0 0;
  background-color: rgba(0, 112, 209, 0.2);
  transition: all 0.15s ease;
}
.mini-chart .bar.active {
  background-color: rgba(74, 222, 128, 0.4);
}

/* Section titles */
.section-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-muted, #52525b);
  letter-spacing: 0.05em;
  padding: 0 1.5rem;
}

/* Agent cards */
.agent-card {
  border-radius: 0.75rem;
  padding: 1rem;
  border: 1px solid;
  transition: all 0.15s ease;
}
.agent-card:hover {
  box-shadow: 0 0 20px rgba(59,130,246,0.05);
  transform: translateY(-2px);
}
.agent-forge { border-color: rgba(6, 182, 212, 0.2); background-color: rgba(6, 182, 212, 0.04); }
.agent-pulse { border-color: rgba(34, 197, 94, 0.2); background-color: rgba(34, 197, 94, 0.04); }
.agent-security { border-color: rgba(168, 85, 247, 0.2); background-color: rgba(168, 85, 247, 0.04); }
.agent-research { border-color: rgba(59, 130, 246, 0.2); background-color: rgba(59, 130, 246, 0.04); }
.agent-learning { border-color: rgba(245, 158, 11, 0.2); background-color: rgba(245, 158, 11, 0.04); }

/* Activity log */
.activity-log {
  margin: 0 1.5rem;
  border-radius: 1rem;
  border: 1px solid rgba(255, 255, 255, 0.05);
  background-color: rgba(255, 255, 255, 0.02);
  overflow: hidden;
}
.activity-log-inner > * + * {
  border-top: 1px solid rgba(255, 255, 255, 0.03);
}
.activity-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.625rem 1.25rem;
  transition: all 0.15s ease;
}
.activity-row:hover {
  background-color: rgba(255, 255, 255, 0.02);
}
.activity-row {
  animation: fadeIn 0.4s ease-out both;
}

/* Bottom bar */
.bottom-bar {
  margin-top: 3rem;
  padding: 1rem 1.5rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}

/* Fonts */
.font-display {
  font-family: 'Space Grotesk', 'Inter', sans-serif;
}
.font-mono {
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
}

/* Animations */
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
.animate-pulse {
  animation: pulse 2s ease-in-out infinite;
}
</style>
