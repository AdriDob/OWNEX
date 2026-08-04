<script setup lang="ts">
import { ref, computed } from 'vue'
import { api } from '@/lib/api'
import {
  Shield, Search, AlertTriangle, CheckCircle, XCircle, Brain,
  Terminal, Globe, ArrowRight, RefreshCw, Sparkles, ExternalLink,
  Bug, FileText, FlaskConical, BookOpen, Info, ChevronDown, ChevronUp,
  Lightbulb, Scan, FileSearch, Layers, Gauge,
} from '@lucide/vue'
import Card from '@/components/ui/Card.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import CardTitle from '@/components/ui/CardTitle.vue'
import CardContent from '@/components/ui/CardContent.vue'
import Button from '@/components/ui/Button.vue'
import Badge from '@/components/ui/Badge.vue'
import Input from '@/components/ui/Input.vue'
import GlassCard from '@/components/ui/GlassCard.vue'

type Tab = 'llm' | 'cve'
const activeTab = ref<Tab>('llm')

// ── LLM Scanner ──
const llmEndpoint = ref('')
const llmScanning = ref(false)
const llmResult = ref<any>(null)
const llmExpandedCheck = ref<string | null>(null)

async function runLLMScan() {
  if (!llmEndpoint.value) return
  llmScanning.value = true
  llmResult.value = null
  try {
    const res = await api.post('/api/intel/llm-scan', { endpoint: llmEndpoint.value })
    llmResult.value = res
  } catch { /* silent */ }
  finally { llmScanning.value = false }
}

const llmScoreColor = computed(() => {
  if (!llmResult.value) return ''
  const s = llmResult.value.summary.score
  if (s >= 80) return 'text-success'
  if (s >= 60) return 'text-warning'
  return 'text-destructive'
})

const remedyCount = computed(() => {
  if (!llmResult.value) return 0
  return llmResult.value.checks.filter((c: any) => !c.passed).length
})

// ── CVE Prioritizer ──
const techInput = ref('')
const techStack = ref<string[]>([])
const cveLoading = ref(false)
const cveResults = ref<any[]>([])
const cveExpanded = ref<string | null>(null)

function addTech() {
  const t = techInput.value.trim().toLowerCase()
  if (t && !techStack.value.includes(t)) techStack.value.push(t)
  techInput.value = ''
}

function removeTech(t: string) {
  techStack.value = techStack.value.filter(x => x !== t)
}

const PRESET_TECHS = ['nginx', 'python', 'node', 'postgresql', 'redis', 'docker', 'kubernetes', 'apache', 'mongodb', 'wordpress', 'git']

async function runCVE() {
  if (!techStack.value.length) return
  cveLoading.value = true
  cveResults.value = []
  try {
    const res = await api.post('/api/intel/cve-prioritize', { tech_stack: techStack.value })
    cveResults.value = res
  } catch { /* silent */ }
  finally { cveLoading.value = false }
}

const priorityBadge = (label: string) => {
  const m: Record<string, string> = {
    Critical: 'bg-destructive/15 text-destructive border-destructive/30',
    High: 'bg-warning/15 text-warning border-warning/30',
    Medium: 'bg-warning/15 text-warning border-warning/30',
    Low: 'bg-primary/15 text-primary border-primary/30',
    Info: 'bg-muted/15 text-muted-foreground border-border-light/30',
  }
  return m[label] || 'bg-muted/15 text-muted-foreground border-border-light/30'
}

const criticalCount = computed(() =>
  cveResults.value.filter((c: any) => c.priority_label === 'Critical').length
)
const highCount = computed(() =>
  cveResults.value.filter((c: any) => c.priority_label === 'High').length
)
const kevCount = computed(() =>
  cveResults.value.filter((c: any) => c.kev).length
)
</script>

<template>
  <div class="max-w-6xl mx-auto px-4 py-8 space-y-8 animate-in">
    <!-- ═══ HEADER ═══ -->
    <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
      <div>
        <div class="flex items-center gap-3">
          <div class="p-2.5 rounded-xl bg-gradient-to-br from-primary/20 to-intigriti/20 border border-primary/20">
            <Brain class="w-6 h-6 text-primary" />
          </div>
          <div>
            <h1 class="text-2xl font-bold tracking-tight">OWNEX Intelligence</h1>
            <p class="text-sm text-muted-foreground">LLM security scanning + CVE threat prioritization</p>
          </div>
        </div>
      </div>
      <div class="flex gap-2 bg-card border rounded-xl p-1">
        <button
          :class="['px-4 py-2 rounded-lg text-sm font-medium transition-all', activeTab === 'llm' ? 'bg-primary text-primary-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground']"
          @click="activeTab = 'llm'"
        >
          <Shield class="w-4 h-4 inline mr-1.5" />LLM Scan
        </button>
        <button
          :class="['px-4 py-2 rounded-lg text-sm font-medium transition-all', activeTab === 'cve' ? 'bg-primary text-primary-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground']"
          @click="activeTab = 'cve'"
        >
          <Search class="w-4 h-4 inline mr-1.5" />CVE Intel
        </button>
      </div>
    </div>

    <!-- ══════════════════════════════════════════════
         LLM SECURITY SCANNER
         ══════════════════════════════════════════════ -->
    <template v-if="activeTab === 'llm'">
      <GlassCard class="p-5 sm:p-6">
        <div class="flex flex-col sm:flex-row items-start gap-4">
          <div class="p-3 rounded-xl bg-primary/10 border border-primary/20 shrink-0 hidden sm:block">
            <Terminal class="w-6 h-6 text-primary" />
          </div>
          <div class="flex-1 w-full space-y-4">
            <div>
              <h2 class="text-lg font-semibold">LLM Security Scanner</h2>
              <p class="text-sm text-muted-foreground">
                Probe your endpoint against OWASP LLM Top 10 attack categories
              </p>
            </div>
            <div class="flex flex-col sm:flex-row gap-3">
              <Input
                v-model="llmEndpoint"
                placeholder="https://api.example.com/v1/chat/completions"
                class="flex-1 font-mono text-sm"
              />
              <Button @click="runLLMScan" :disabled="llmScanning || !llmEndpoint" class="shrink-0">
                <template v-if="llmScanning">
                  <RefreshCw class="w-4 h-4 mr-2 animate-spin" />
                  Scanning…
                </template>
                <template v-else>
                  <Scan class="w-4 h-4 mr-2" />
                  Run Scan
                </template>
              </Button>
            </div>
            <div class="flex flex-wrap gap-2 text-xs text-muted-foreground">
              <span class="flex items-center gap-1">
                <Info class="w-3 h-3" />Data sources:
              </span>
              <Badge variant="outline" class="text-[10px]">OWASP LLM Top 10</Badge>
              <Badge variant="outline" class="text-[10px]">PyRIT (Microsoft)</Badge>
              <Badge variant="outline" class="text-[10px]">Garak (NVIDIA)</Badge>
            </div>
          </div>
        </div>
      </GlassCard>

      <!-- No results -->
      <div v-if="!llmResult && !llmScanning" class="flex flex-col items-center justify-center py-20 text-muted-foreground">
        <Shield class="w-16 h-16 mb-4 opacity-20" />
        <p class="text-lg font-medium">Enter an LLM endpoint and run a scan</p>
        <p class="text-sm mt-1">6 checks across injection, leak, toxicity, hallucination, and more</p>
      </div>

      <!-- Loading -->
      <div v-if="llmScanning" class="flex flex-col items-center justify-center py-20 text-muted-foreground">
        <div class="relative w-16 h-16 mb-4">
          <div class="absolute inset-0 rounded-full border-2 border-primary/20 border-t-blue-400 animate-spin" />
          <Brain class="absolute inset-0 m-auto w-6 h-6 text-primary animate-pulse" />
        </div>
        <p class="text-lg font-medium">Running security probes…</p>
        <p class="text-sm mt-1">Testing prompt injection, jailbreaks, data leakage, and more</p>
      </div>

      <!-- Results -->
      <div v-if="llmResult && !llmScanning" class="space-y-6">
        <!-- Score card -->
        <GlassCard class="p-6">
          <div class="flex flex-col sm:flex-row items-center gap-6">
            <div class="relative">
              <svg class="w-28 h-28 -rotate-90" viewBox="0 0 100 100">
                <circle cx="50" cy="50" r="42" fill="none" stroke="currentColor" stroke-width="8" class="text-muted/20" />
                <circle
                  cx="50" cy="50" r="42" fill="none" stroke="currentColor" stroke-width="8"
                  :stroke-dasharray="264"
                  :stroke-dashoffset="264 - (264 * llmResult.summary.score / 100)"
                  :class="llmScoreColor"
                  class="transition-all duration-1000"
                  stroke-linecap="round"
                />
              </svg>
              <div class="absolute inset-0 flex items-center justify-center">
                <span class="text-3xl font-bold" :class="llmScoreColor">{{ llmResult.summary.score }}</span>
              </div>
            </div>
            <div class="flex-1 text-center sm:text-left">
              <p class="text-lg font-semibold">Security Score</p>
              <p class="text-sm text-muted-foreground mt-1">
                {{ llmResult.summary.passed }} of {{ llmResult.summary.total }} checks passed
              </p>
              <div class="flex flex-wrap gap-2 mt-3 justify-center sm:justify-start">
                <Badge variant="secondary" class="text-xs">
                  {{ llmResult.summary.passed }} passed
                </Badge>
                <Badge v-if="llmResult.summary.high_severity" variant="destructive" class="text-xs">
                  {{ llmResult.summary.high_severity }} high
                </Badge>
                <Badge v-if="llmResult.summary.medium_severity" variant="warning" class="text-xs">
                  {{ llmResult.summary.medium_severity }} medium
                </Badge>
                <span class="text-[10px] text-muted-foreground self-center">
                  Scanned {{ llmResult.timestamp.slice(0, 10) }}
                </span>
              </div>
            </div>
            <div class="hidden sm:block text-right shrink-0">
              <Badge variant="outline" class="text-xs">Simulated</Badge>
              <p class="text-[10px] text-muted-foreground mt-1">PyRIT/Garak pending</p>
            </div>
          </div>
        </GlassCard>

        <!-- Remediation callout -->
        <div v-if="remedyCount > 0" class="p-4 rounded-xl border bg-warning/5 border-amber-500/20 flex items-start gap-3">
          <Lightbulb class="w-5 h-5 text-warning shrink-0 mt-0.5" />
          <div>
            <p class="font-medium text-warning">{{ remedyCount }} issues need attention</p>
            <p class="text-sm text-muted-foreground mt-0.5">
              Expand each check below for the exact probe payload, model response, and remediation steps.
            </p>
          </div>
        </div>

        <!-- Checks -->
        <div class="space-y-3">
          <h3 class="text-sm font-medium text-muted-foreground uppercase tracking-wider">Check Details</h3>
          <div
            v-for="(check, idx) in llmResult.checks"
            :key="check.name"
            class="rounded-xl border transition-all overflow-hidden"
            :class="[
              check.passed
                ? 'bg-success/[0.03] border-success/15'
                : 'bg-destructive/[0.03] border-destructive/15',
              llmExpandedCheck === check.name ? 'ring-1 ring-inset' : '',
              llmExpandedCheck === check.name && check.passed ? 'ring-green-500/30' : '',
              llmExpandedCheck === check.name && !check.passed ? 'ring-red-500/30' : '',
            ]"
          >
            <button
              class="w-full flex items-center gap-3 p-4 text-left"
              @click="llmExpandedCheck = llmExpandedCheck === check.name ? null : check.name"
            >
              <div
                class="p-1.5 rounded-lg shrink-0"
                :class="check.passed ? 'bg-success/10' : 'bg-destructive/10'"
              >
                <CheckCircle v-if="check.passed" class="w-4 h-4 text-success" />
                <XCircle v-else class="w-4 h-4 text-destructive" />
              </div>
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2">
                  <span class="font-medium text-sm">{{ check.name }}</span>
                  <Badge
                    :variant="check.passed ? 'secondary' : 'destructive'"
                    class="text-[10px]"
                  >{{ check.severity }}</Badge>
                </div>
                <p class="text-xs text-muted-foreground mt-0.5 truncate">{{ check.detail }}</p>
              </div>
              <ChevronDown
                v-if="llmExpandedCheck !== check.name"
                class="w-4 h-4 text-muted-foreground shrink-0"
              />
              <ChevronUp
                v-else
                class="w-4 h-4 text-muted-foreground shrink-0"
              />
            </button>

            <div v-if="llmExpandedCheck === check.name" class="px-4 pb-4 space-y-3 border-t pt-3"
              :class="check.passed ? 'border-success/10' : 'border-destructive/10'"
            >
              <!-- Probe payload -->
              <div v-if="check.probe" class="space-y-1">
                <div class="flex items-center gap-1.5 text-xs text-muted-foreground">
                  <FlaskConical class="w-3 h-3" /> Probe ({{ check.probe.category }})
                </div>
                <div class="p-2.5 rounded-lg bg-muted/30 border text-xs font-mono whitespace-pre-wrap break-words text-muted-foreground">
                  {{ check.probe.payload }}
                </div>
              </div>

              <!-- Model response -->
              <div v-if="check.model_response" class="space-y-1">
                <div class="flex items-center gap-1.5 text-xs text-muted-foreground">
                  <Terminal class="w-3 h-3" /> Model response
                </div>
                <div
                  class="p-2.5 rounded-lg border text-xs font-mono"
                  :class="check.passed ? 'bg-success/5 border-success/15 text-success' : 'bg-destructive/5 border-destructive/15 text-destructive'"
                >
                  {{ check.model_response }}
                </div>
              </div>

              <!-- Remediation -->
              <div v-if="check.remediation" class="space-y-1">
                <div class="flex items-center gap-1.5 text-xs text-warning">
                  <Lightbulb class="w-3 h-3" /> Remediation
                </div>
                <div class="p-2.5 rounded-lg bg-warning/5 border border-amber-500/15 text-xs">
                  {{ check.remediation }}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- ══════════════════════════════════════════════
         CVE INTELLIGENCE
         ══════════════════════════════════════════════ -->
    <template v-if="activeTab === 'cve'">
      <GlassCard class="p-5 sm:p-6">
        <div class="flex flex-col sm:flex-row items-start gap-4">
          <div class="p-3 rounded-xl bg-intigriti/10 border border-purple-500/20 shrink-0 hidden sm:block">
            <Search class="w-6 h-6 text-intigriti" />
          </div>
          <div class="flex-1 w-full space-y-4">
            <div>
              <h2 class="text-lg font-semibold">CVE Prioritizer</h2>
              <p class="text-sm text-muted-foreground">
                CVSS + EPSS + CISA KEV → composite priority score
              </p>
            </div>

            <!-- Formula -->
            <div class="p-3 rounded-lg bg-muted/20 border text-xs text-muted-foreground space-y-1">
              <div class="flex items-center gap-1 font-medium">
                <Gauge class="w-3 h-3" /> Priority formula
              </div>
              <code class="text-[11px]">score = CVSS × 0.40 + EPSS × 10 × 0.35 + KEV × 2.50</code>
              <div class="flex gap-3 mt-1 text-[10px]">
                <span>NVD: CVSS severity</span>
                <span>FIRST: EPSS exploit probability</span>
                <span>CISA: KEV active exploitation</span>
              </div>
            </div>

            <!-- Tags -->
            <div class="flex flex-wrap gap-2">
              <Badge
                v-for="tech in techStack"
                :key="tech"
                variant="secondary"
                class="cursor-pointer text-xs"
                @click="removeTech(tech)"
              >
                {{ tech }} <span class="ml-1 opacity-60">×</span>
              </Badge>
            </div>
            <div class="flex gap-2">
              <Input v-model="techInput" placeholder="nginx, python, docker…" @keyup.enter="addTech" class="flex-1 font-mono text-sm" />
              <Button variant="outline" @click="addTech" size="sm">Add</Button>
            </div>
            <div class="flex flex-wrap gap-1.5">
              <button
                v-for="tech in PRESET_TECHS"
                :key="tech"
                :disabled="techStack.includes(tech)"
                class="px-2.5 py-1 rounded-lg border text-[11px] font-mono transition-all"
                :class="techStack.includes(tech) ? 'opacity-30 cursor-not-allowed' : 'hover:bg-accent cursor-pointer'"
                @click="techStack.push(tech)"
              >
                +{{ tech }}
              </button>
            </div>
            <Button @click="runCVE" :disabled="cveLoading || !techStack.length">
              <template v-if="cveLoading">
                <RefreshCw class="w-4 h-4 mr-2 animate-spin" />
                Analyzing…
              </template>
              <template v-else>
                <FileSearch class="w-4 h-4 mr-2" />
                Prioritize CVEs
              </template>
            </Button>
          </div>
        </div>
      </GlassCard>

      <!-- No results -->
      <div v-if="!cveResults.length && !cveLoading" class="flex flex-col items-center justify-center py-20 text-muted-foreground">
        <Layers class="w-16 h-16 mb-4 opacity-20" />
        <p class="text-lg font-medium">Add your tech stack to see CVEs</p>
        <p class="text-sm mt-1">Ranked by CVSS × EPSS × KEV with fix guidance</p>
      </div>

      <!-- Loading -->
      <div v-if="cveLoading" class="flex flex-col items-center justify-center py-20 text-muted-foreground">
        <div class="relative w-16 h-16 mb-4">
          <div class="absolute inset-0 rounded-full border-2 border-purple-500/20 border-t-purple-400 animate-spin" />
          <Search class="absolute inset-0 m-auto w-6 h-6 text-intigriti animate-pulse" />
        </div>
        <p class="text-lg font-medium">Fetching CVE intelligence…</p>
        <p class="text-sm mt-1">Querying NVD + EPSS + CISA KEV databases</p>
      </div>

      <!-- Results -->
      <div v-if="cveResults.length && !cveLoading" class="space-y-4">
        <!-- Summary bar -->
        <GlassCard class="p-4">
          <div class="flex flex-wrap items-center gap-4 text-sm">
            <span class="text-muted-foreground">{{ cveResults.length }} CVEs</span>
            <span class="text-destructive font-medium" v-if="criticalCount">{{ criticalCount }} critical</span>
            <span class="text-warning font-medium" v-if="highCount">{{ highCount }} high</span>
            <span class="text-destructive font-medium" v-if="kevCount">{{ kevCount }} exploited in wild (KEV)</span>
            <span class="text-xs text-muted-foreground ml-auto">
              Data: NVD · EPSS (FIRST) · CISA KEV
            </span>
          </div>
        </GlassCard>

        <!-- CVE cards -->
        <div
          v-for="cve in cveResults"
          :key="cve.id"
          class="rounded-xl border bg-card overflow-hidden transition-all hover:border-foreground/20"
        >
          <button
            class="w-full flex items-start gap-3 p-4 text-left"
            @click="cveExpanded = cveExpanded === cve.id ? null : cve.id"
          >
            <div
              class="p-1.5 rounded-lg shrink-0 mt-0.5"
              :class="{
                'bg-destructive/10': cve.priority_label === 'Critical',
                'bg-warning/10': cve.priority_label === 'High',
                'bg-warning/10': cve.priority_label === 'Medium',
                'bg-primary/10': cve.priority_label === 'Low',
              }"
            >
              <AlertTriangle v-if="cve.priority_label === 'Critical' || cve.priority_label === 'High'" class="w-4 h-4 text-destructive" />
              <Info v-else class="w-4 h-4 text-primary" />
            </div>
            <div class="flex-1 min-w-0">
              <div class="flex flex-wrap items-center gap-2">
                <span class="font-mono text-sm font-bold">{{ cve.id }}</span>
                <Badge variant="outline" class="text-[10px]">{{ cve.tech }}</Badge>
                <span :class="['px-2 py-0.5 rounded-md text-[11px] font-medium border', priorityBadge(cve.priority_label)]">
                  {{ cve.priority_label }} · {{ cve.priority_score }}
                </span>
                <Badge v-if="cve.kev" variant="destructive" class="text-[10px]">KEV</Badge>
              </div>
              <p class="text-sm text-muted-foreground mt-1">{{ cve.description }}</p>
              <div class="flex items-center gap-3 mt-1.5 text-[11px] text-muted-foreground">
                <span>CVSS {{ cve.cvss }}</span>
                <span>EPSS {{ (cve.epss * 100).toFixed(0) }}%</span>
              </div>
            </div>
            <ChevronDown v-if="cveExpanded !== cve.id" class="w-4 h-4 text-muted-foreground shrink-0 mt-1" />
            <ChevronUp v-else class="w-4 h-4 text-muted-foreground shrink-0 mt-1" />
          </button>

          <div v-if="cveExpanded === cve.id" class="px-4 pb-4 border-t pt-3 space-y-3">
            <!-- Fix -->
            <div class="space-y-1">
              <div class="flex items-center gap-1.5 text-xs text-warning">
                <Lightbulb class="w-3 h-3" /> Recommended fix
              </div>
              <div class="p-2.5 rounded-lg bg-warning/5 border border-amber-500/15 text-xs">
                {{ cve.fix }}
              </div>
            </div>
            <!-- Link -->
            <div class="flex items-center gap-2">
              <a
                :href="cve.url"
                target="_blank"
                rel="noopener noreferrer"
                class="inline-flex items-center gap-1.5 text-xs text-primary hover:underline"
              >
                <ExternalLink class="w-3 h-3" />
                View on NVD
              </a>
              <span class="text-[10px] text-muted-foreground ml-auto">
                Sources: NVD · EPSS · CISA KEV
              </span>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- ═══ FOOTER ═══ -->
    <p class="text-center text-[11px] text-muted-foreground pt-4 border-t">
      OWNEX Intelligence · Data from NVD, FIRST EPSS, CISA KEV, OWASP LLM Top 10, PyRIT, Garak
    </p>
  </div>
</template>
