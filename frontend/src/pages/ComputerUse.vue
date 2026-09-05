<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'

const apiBase = import.meta.env.VITE_API_BASE || ''

// ── State ──────────────────────────────────────────────────────
const status = ref<any>(null)
const task = ref('')
const maxSteps = ref(20)
const model = ref('moondream')
const isRunning = ref(false)
const currentResult = ref<any>(null)
const learningStats = ref<any[]>([])
const currentScreenshot = ref<string | null>(null)
const screenshotTimestamp = ref<number>(0)
const platformFilter = ref('')
const records = ref<any[]>([])
const error = ref('')

// ── Screenshot History ─────────────────────────────────────────
interface HistorySession {
  session_id: string
  task: string
  platform: string
  success: boolean
  total_steps: number
  duration_seconds: number
  screenshot_count: number
  started_at: number
  error: string | null
}
interface HistoryScreenshot {
  id: string
  step_number: number
  path: string
  timestamp: number
  action_summary: string
  action_type: string
  success: boolean
  duration_ms: number
}
const historySessions = ref<HistorySession[]>([])
const selectedSession = ref<HistorySession | null>(null)
const sessionScreenshots = ref<HistoryScreenshot[]>([])
const currentSlide = ref(0)
const showHistory = ref(false)

// ── Live Preview ───────────────────────────────────────────────
const livePreview = ref(false)
const refreshInterval = ref(5) // seconds
let previewTimer: ReturnType<typeof setInterval> | null = null

function startPreview() {
  stopPreview()
  previewTimer = setInterval(() => {
    if (!isRunning.value) captureScreenshot()
  }, refreshInterval.value * 1000)
}

function stopPreview() {
  if (previewTimer) {
    clearInterval(previewTimer)
    previewTimer = null
  }
}

function togglePreview() {
  livePreview.value = !livePreview.value
}

// Auto-start/stop preview when toggle changes
watch(livePreview, (on) => {
  if (on) startPreview()
  else stopPreview()
})

// Auto-start preview during execution
watch(isRunning, (running) => {
  if (running && !livePreview.value) {
    livePreview.value = true
  }
})

// Cleanup on unmount
onUnmounted(() => stopPreview())

// ── API calls ──────────────────────────────────────────────────
async function fetchStatus() {
  try {
    const res = await fetch(`${apiBase}/api/copilot/computer-use/status`)
    const data = await res.json()
    status.value = data.status === 'ok' ? data.tool : null
  } catch (e: any) {
    error.value = e.message
  }
}

async function fetchLearningStats() {
  try {
    const res = await fetch(`${apiBase}/api/copilot/computer-use/learning/stats`)
    const data = await res.json()
    learningStats.value = data.platforms || []
  } catch (e: any) {
    error.value = e.message
  }
}

async function captureScreenshot() {
  try {
    const res = await fetch(`${apiBase}/api/copilot/computer-use/screenshot`, { method: 'POST' })
    const data = await res.json()
    if (data.status === 'ok' && data.analysis?.screenshot_path) {
      currentScreenshot.value = data.analysis.screenshot_path
      screenshotTimestamp.value = Date.now()
    }
  } catch (e: any) {
    // Don't show screenshot errors during live preview (noisy)
    if (!livePreview.value) error.value = e.message
  }
}

async function executeTask() {
  if (!task.value.trim() || isRunning.value) return
  isRunning.value = true
  error.value = ''
  currentResult.value = null

  try {
    const res = await fetch(`${apiBase}/api/copilot/computer-use/execute`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        task: task.value,
        max_steps: maxSteps.value,
        model: model.value,
        vision_provider: 'ollama',
      }),
    })
    const data = await res.json()
    if (data.status === 'ok') {
      currentResult.value = data.result
      if (data.result?.final_screenshot) {
        currentScreenshot.value = data.result.final_screenshot
      }
    } else {
      error.value = data.detail || 'Execution failed'
    }
  } catch (e: any) {
    error.value = e.message
  } finally {
    isRunning.value = false
  }
}

async function fetchRecords() {
  try {
    const url = platformFilter.value
      ? `${apiBase}/api/copilot/computer-use/learning/${platformFilter.value}/records`
      : `${apiBase}/api/copilot/computer-use/learning/outlier/records`
    const res = await fetch(url)
    const data = await res.json()
    records.value = data.records || []
  } catch (e: any) {
    error.value = e.message
  }
}

async function fetchHistory() {
  try {
    const res = await fetch(`${apiBase}/api/copilot/computer-use/history?limit=10`)
    const data = await res.json()
    historySessions.value = data.sessions || []
  } catch (e: any) {
    // silent
  }
}

async function selectSession(session: HistorySession) {
  selectedSession.value = session
  currentSlide.value = 0
  try {
    const res = await fetch(`${apiBase}/api/copilot/computer-use/history/${session.session_id}/screenshots`)
    const data = await res.json()
    sessionScreenshots.value = data.screenshots || []
    if (sessionScreenshots.value.length > 0) {
      currentScreenshot.value = sessionScreenshots.value[0].path
      screenshotTimestamp.value = sessionScreenshots.value[0].timestamp * 1000
    }
  } catch (e: any) {
    error.value = e.message
  }
}

function nextSlide() {
  if (currentSlide.value < sessionScreenshots.value.length - 1) {
    currentSlide.value++
    const ss = sessionScreenshots.value[currentSlide.value]
    currentScreenshot.value = ss.path
    screenshotTimestamp.value = ss.timestamp * 1000
  }
}

function prevSlide() {
  if (currentSlide.value > 0) {
    currentSlide.value--
    const ss = sessionScreenshots.value[currentSlide.value]
    currentScreenshot.value = ss.path
    screenshotTimestamp.value = ss.timestamp * 1000
  }
}

function formatDuration(s: number): string {
  if (s < 60) return `${Math.round(s)}s`
  return `${Math.floor(s / 60)}m ${Math.round(s % 60)}s`
}

// ── Lifecycle ──────────────────────────────────────────────────
onMounted(() => {
  fetchStatus()
  fetchLearningStats()
  fetchRecords()
  fetchHistory()
})
</script>

<template>
  <div class="min-h-screen bg-background p-4 sm:p-6">
    <!-- Header -->
    <div class="mb-6 flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-foreground">Computer Use</h1>
        <p class="text-sm text-muted-foreground">Autonomous desktop control via screen capture + LLM vision</p>
      </div>
      <div class="flex items-center gap-2">
        <span
          class="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-mono"
          :class="status?.available ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'"
        >
          <span class="h-1.5 w-1.5 rounded-full" :class="status?.available ? 'bg-emerald-400' : 'bg-red-400'" />
          {{ status?.available ? 'Available' : 'Unavailable' }}
        </span>
      </div>
    </div>

    <!-- Error banner -->
    <div v-if="error" class="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-400">
      {{ error }}
      <button class="ml-2 underline" @click="error = ''">dismiss</button>
    </div>

    <div class="grid grid-cols-1 gap-6 lg:grid-cols-3">
      <!-- Left: Task input + execution -->
      <div class="lg:col-span-2 space-y-4">
        <!-- Task input card -->
        <div class="rounded-xl border border-border/40 bg-surface/50 p-5">
          <h2 class="mb-3 text-sm font-semibold text-foreground">Execute Task</h2>
          <textarea
            v-model="task"
            rows="3"
            class="w-full rounded-lg border border-border/40 bg-background p-3 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary/50 focus:outline-none"
            placeholder="Describe what to do on the desktop...&#10;e.g., 'Open Firefox, go to google.com, and search for ownex'"
          />
          <div class="mt-3 flex items-center gap-3">
            <div>
              <label class="text-xs text-muted-foreground">Max Steps</label>
              <input
                v-model.number="maxSteps"
                type="number"
                min="1"
                max="50"
                class="ml-2 w-16 rounded border border-border/40 bg-background px-2 py-1 text-xs text-foreground"
              />
            </div>
            <div>
              <label class="text-xs text-muted-foreground">Model</label>
              <select
                v-model="model"
                class="ml-2 rounded border border-border/40 bg-background px-2 py-1 text-xs text-foreground"
              >
                <option value="moondream">moondream</option>
                <option value="llava">llava</option>
                <option value="qwen2-vl">qwen2-vl</option>
              </select>
            </div>
            <button
              class="ml-auto flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-50"
              :disabled="!task.trim() || isRunning"
              @click="executeTask"
            >
              <svg v-if="isRunning" class="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              {{ isRunning ? 'Running...' : 'Execute' }}
            </button>
          </div>
        </div>

        <!-- Screenshot preview -->
        <div class="rounded-xl border border-border/40 bg-surface/50 p-5">
          <div class="mb-3 flex items-center justify-between">
            <div class="flex items-center gap-3">
              <h2 class="text-sm font-semibold text-foreground">Screenshot</h2>
              <button
                class="flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[10px] font-mono transition-colors"
                :class="livePreview ? 'bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20' : 'bg-surface text-muted-foreground hover:text-foreground'"
                @click="togglePreview"
              >
                <span class="h-1.5 w-1.5 rounded-full" :class="livePreview ? 'bg-emerald-400 animate-pulse' : 'bg-muted-foreground'" />
                {{ livePreview ? 'LIVE' : 'Preview OFF' }}
              </button>
              <span v-if="livePreview" class="text-[10px] font-mono text-muted-foreground/60">
                every {{ refreshInterval }}s
              </span>
            </div>
            <div class="flex items-center gap-2">
              <select
                v-if="livePreview"
                v-model.number="refreshInterval"
                class="rounded border border-border/30 bg-background px-1.5 py-0.5 text-[10px] font-mono text-muted-foreground"
                @change="startPreview"
              >
                <option :value="2">2s</option>
                <option :value="5">5s</option>
                <option :value="10">10s</option>
                <option :value="30">30s</option>
              </select>
              <button
                class="text-xs text-muted-foreground hover:text-foreground transition-colors"
                @click="captureScreenshot"
              >
                Capture Now
              </button>
            </div>
          </div>
          <div
            v-if="currentScreenshot"
            class="overflow-hidden rounded-lg border border-border/20"
          >
            <img
              :src="`file://${currentScreenshot}`"
              alt="Screenshot"
              class="w-full object-contain"
              style="max-height: 400px"
              @error="(e: any) => e.target.style.display = 'none'"
            />
          </div>
          <div v-else class="flex h-48 items-center justify-center rounded-lg border border-dashed border-border/30 text-sm text-muted-foreground">
            <div class="text-center">
              <p>No screenshot captured yet</p>
              <p class="mt-1 text-[10px] text-muted-foreground/60">Click "Capture Now" or enable LIVE preview</p>
            </div>
          </div>
          <!-- Timestamp -->
          <div v-if="screenshotTimestamp" class="mt-2 flex items-center justify-between text-[10px] font-mono text-muted-foreground/50">
            <span>Last captured: {{ new Date(screenshotTimestamp).toLocaleTimeString() }}</span>
            <span v-if="currentScreenshot" class="truncate max-w-[200px]">{{ currentScreenshot.split('/').pop() }}</span>
          </div>
        </div>

        <!-- Execution result -->
        <div v-if="currentResult" class="rounded-xl border border-border/40 bg-surface/50 p-5">
          <h2 class="mb-3 text-sm font-semibold text-foreground">Result</h2>
          <div class="flex items-center gap-4 text-xs">
            <span
              class="rounded-full px-2 py-0.5 font-mono"
              :class="currentResult.success ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'"
            >
              {{ currentResult.success ? 'SUCCESS' : 'FAILED' }}
            </span>
            <span class="text-muted-foreground">{{ currentResult.total_steps }} steps</span>
            <span class="text-muted-foreground">{{ (currentResult.total_duration_ms / 1000).toFixed(1) }}s</span>
          </div>
          <p v-if="currentResult.summary" class="mt-2 text-sm text-foreground">{{ currentResult.summary }}</p>
          <p v-if="currentResult.error" class="mt-2 text-sm text-red-400">{{ currentResult.error }}</p>

          <!-- Step details -->
          <div v-if="currentResult.steps?.length" class="mt-4 space-y-2">
            <div
              v-for="step in currentResult.steps"
              :key="step.step"
              class="rounded-lg border border-border/20 p-3 text-xs"
            >
              <div class="flex items-center gap-2">
                <span class="font-mono text-muted-foreground">Step {{ step.step }}</span>
                <span :class="step.success ? 'text-emerald-400' : 'text-red-400'">
                  {{ step.success ? 'OK' : 'FAIL' }}
                </span>
                <span class="text-muted-foreground">{{ step.duration_ms?.toFixed(0) }}ms</span>
              </div>
              <p v-if="step.analysis" class="mt-1 text-muted-foreground line-clamp-2">{{ step.analysis }}</p>
            </div>
          </div>
        </div>

        <!-- Screenshot History -->
        <div class="rounded-xl border border-border/40 bg-surface/50 p-5">
          <div class="mb-3 flex items-center justify-between">
            <h2 class="text-sm font-semibold text-foreground">Session History</h2>
            <button
              class="text-xs text-muted-foreground hover:text-foreground transition-colors"
              @click="showHistory = !showHistory"
            >
              {{ showHistory ? 'Hide' : 'Show' }}
            </button>
          </div>
          <div v-if="showHistory">
            <!-- Session list -->
            <div v-if="historySessions.length && !selectedSession" class="space-y-1.5">
              <button
                v-for="s in historySessions.slice(0, 8)"
                :key="s.session_id"
                class="flex w-full items-center justify-between rounded-lg border border-border/20 px-3 py-2 text-left text-xs transition-colors hover:border-primary/30 hover:bg-surface/30"
                @click="selectSession(s)"
              >
                <div class="min-w-0 flex-1">
                  <p class="truncate font-mono text-foreground">{{ s.task }}</p>
                  <p class="mt-0.5 font-mono text-[9px] text-muted-foreground">
                    {{ s.total_steps }} steps · {{ formatDuration(s.duration_seconds) }}
                  </p>
                </div>
                <span
                  class="ml-2 shrink-0 rounded-full px-1.5 py-0.5 font-mono text-[9px]"
                  :class="s.success ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'"
                >
                  {{ s.screenshot_count }} ss
                </span>
              </button>
            </div>

            <!-- Selected session carousel -->
            <div v-if="selectedSession">
              <button
                class="mb-2 flex items-center gap-1 text-[10px] font-mono text-muted-foreground hover:text-foreground"
                @click="selectedSession = null; sessionScreenshots = []"
              >
                ← Back to sessions
              </button>
              <p class="mb-2 truncate font-mono text-xs text-foreground">{{ selectedSession.task }}</p>
              <div v-if="sessionScreenshots.length" class="relative">
                <!-- Screenshot display -->
                <div class="overflow-hidden rounded-lg border border-border/20">
                  <img
                    :src="`file://${sessionScreenshots[currentSlide]?.path}`"
                    :alt="`Step ${sessionScreenshots[currentSlide]?.step_number}`"
                    class="w-full object-contain"
                    style="max-height: 300px"
                    @error="(e: any) => e.target.style.display = 'none'"
                  />
                </div>
                <!-- Navigation -->
                <div class="mt-2 flex items-center justify-between">
                  <button
                    :disabled="currentSlide === 0"
                    class="rounded border border-border/30 px-2 py-1 text-[10px] font-mono text-muted-foreground hover:text-foreground disabled:opacity-30"
                    @click="prevSlide"
                  >
                    ← Prev
                  </button>
                  <span class="font-mono text-[10px] text-muted-foreground">
                    {{ currentSlide + 1 }} / {{ sessionScreenshots.length }}
                  </span>
                  <button
                    :disabled="currentSlide >= sessionScreenshots.length - 1"
                    class="rounded border border-border/30 px-2 py-1 text-[10px] font-mono text-muted-foreground hover:text-foreground disabled:opacity-30"
                    @click="nextSlide"
                  >
                    Next →
                  </button>
                </div>
                <!-- Step info -->
                <div v-if="sessionScreenshots[currentSlide]" class="mt-2 rounded-lg border border-border/20 p-2">
                  <div class="flex items-center gap-2 text-[10px] font-mono">
                    <span class="text-muted-foreground">Step {{ sessionScreenshots[currentSlide].step_number }}</span>
                    <span
                      :class="sessionScreenshots[currentSlide].success ? 'text-emerald-400' : 'text-red-400'"
                    >
                      {{ sessionScreenshots[currentSlide].action_type }}
                    </span>
                  </div>
                  <p v-if="sessionScreenshots[currentSlide].action_summary" class="mt-1 text-[10px] text-muted-foreground line-clamp-2">
                    {{ sessionScreenshots[currentSlide].action_summary }}
                  </p>
                </div>
                <!-- Step dots -->
                <div class="mt-2 flex justify-center gap-1">
                  <button
                    v-for="(_, i) in sessionScreenshots.slice(0, 20)"
                    :key="i"
                    class="h-1.5 w-1.5 rounded-full transition-colors"
                    :class="i === currentSlide ? 'bg-primary' : 'bg-muted-foreground/30 hover:bg-muted-foreground/50'"
                    @click="currentSlide = i; currentScreenshot = sessionScreenshots[i].path; screenshotTimestamp = sessionScreenshots[i].timestamp * 1000"
                  />
                </div>
              </div>
              <p v-else class="text-xs text-muted-foreground">No screenshots in this session</p>
            </div>

            <!-- Empty state -->
            <div v-if="!historySessions.length && !selectedSession" class="text-center py-4">
              <p class="text-xs text-muted-foreground/60">No sessions yet. Execute a task to start recording.</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Right: Learning stats + capabilities -->
      <div class="space-y-4">
        <!-- Capabilities card -->
        <div class="rounded-xl border border-border/40 bg-surface/50 p-5">
          <h2 class="mb-3 text-sm font-semibold text-foreground">Capabilities</h2>
          <div v-if="status" class="space-y-2">
            <div class="flex items-center justify-between text-xs">
              <span class="text-muted-foreground">Screenshot</span>
              <span :class="status.capabilities?.screenshot ? 'text-emerald-400' : 'text-red-400'">
                {{ status.capabilities?.screenshot ? 'Yes' : 'No' }}
              </span>
            </div>
            <div class="flex items-center justify-between text-xs">
              <span class="text-muted-foreground">pyautogui</span>
              <span :class="status.capabilities?.pyautogui ? 'text-emerald-400' : 'text-red-400'">
                {{ status.capabilities?.pyautogui ? 'Yes' : 'No' }}
              </span>
            </div>
            <div class="flex items-center justify-between text-xs">
              <span class="text-muted-foreground">Ollama</span>
              <span :class="status.capabilities?.ollama ? 'text-emerald-400' : 'text-red-400'">
                {{ status.capabilities?.ollama ? 'Yes' : 'No' }}
              </span>
            </div>
            <div class="flex items-center justify-between text-xs">
              <span class="text-muted-foreground">Vision Provider</span>
              <span class="font-mono text-foreground">{{ status.capabilities?.vision_provider }}</span>
            </div>
          </div>
          <div v-else class="text-xs text-muted-foreground">Loading...</div>
        </div>

        <!-- Learning Stats card -->
        <div class="rounded-xl border border-border/40 bg-surface/50 p-5">
          <h2 class="mb-3 text-sm font-semibold text-foreground">Platform Learning</h2>
          <div v-if="learningStats.length" class="space-y-2">
            <div
              v-for="stat in learningStats"
              :key="stat.platform"
              class="flex items-center justify-between rounded-lg border border-border/20 px-3 py-2 text-xs"
            >
              <span class="font-medium text-foreground">{{ stat.platform }}</span>
              <div class="flex items-center gap-2">
                <span class="text-muted-foreground">{{ stat.total_attempts }} attempts</span>
                <span
                  class="rounded-full px-1.5 py-0.5 font-mono text-[10px]"
                  :class="
                    stat.success_rate >= 0.8
                      ? 'bg-emerald-500/10 text-emerald-400'
                      : stat.success_rate >= 0.5
                        ? 'bg-yellow-500/10 text-yellow-400'
                        : 'bg-red-500/10 text-red-400'
                  "
                >
                  {{ (stat.success_rate * 100).toFixed(0) }}%
                </span>
              </div>
            </div>
          </div>
          <p v-else class="text-xs text-muted-foreground">No learning data yet</p>
        </div>

        <!-- Recent records -->
        <div class="rounded-xl border border-border/40 bg-surface/50 p-5">
          <div class="mb-3 flex items-center justify-between">
            <h2 class="text-sm font-semibold text-foreground">Recent Fills</h2>
            <button class="text-xs text-muted-foreground hover:text-foreground" @click="fetchRecords">
              Refresh
            </button>
          </div>
          <div v-if="records.length" class="space-y-1.5">
            <div
              v-for="rec in records.slice(0, 5)"
              :key="rec.id"
              class="flex items-center justify-between rounded px-2 py-1.5 text-xs"
            >
              <span class="text-muted-foreground">{{ rec.platform }}</span>
              <span
                :class="rec.success ? 'text-emerald-400' : 'text-red-400'"
                class="font-mono"
              >
                {{ rec.success ? 'OK' : 'FAIL' }}
              </span>
              <span class="text-muted-foreground">{{ (rec.duration_ms / 1000).toFixed(1) }}s</span>
            </div>
          </div>
          <p v-else class="text-xs text-muted-foreground">No records yet</p>
        </div>
      </div>
    </div>
  </div>
</template>
