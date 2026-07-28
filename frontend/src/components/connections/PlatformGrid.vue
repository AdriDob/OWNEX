<script setup lang="ts">
import { ref, computed } from 'vue'
import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import {
  Globe, CheckCircle2, XCircle, Link, RefreshCw, Plus,
  DollarSign, ChevronDown, ChevronUp
} from '@lucide/vue'

// ── Props ────────────────────────────────────────────────────────────────
interface PlatformAccount {
  provider?: string
  provider_name?: string
  email?: string
  has_credentials?: boolean
  last_sync?: string
  last_checked?: string
  session_state?: string
  health_status?: string
}

interface PlatformMeta {
  color: string
  bg: string
}

interface PlatformPayoutMethod {
  id: string
  name: string
  type: string
  kyc_level: string
  fee_percent: number
  arrival_days: string
  notes: string
}

interface PlatformPayout {
  kyc_required: string
  recommended_methods: PlatformPayoutMethod[]
  notes?: string
}

interface PlatformGridProps {
  platforms: string[]
  accounts: PlatformAccount[]
  platformMeta: Record<string, PlatformMeta>
  showConnectForm: string | null
  'onUpdate:showConnectForm': (val: string | null) => void
  connectEmail: string
  'onUpdate:connectEmail': (val: string) => void
  connectToken: string
  'onUpdate:connectToken': (val: string) => void
  connectPlatform: (provider: string) => void
  disconnectPlatform: (provider: string) => void
  syncPlatform: (provider: string) => void
  syncingPlatform: string | null
  expandedPlatformPayout: string | null
  'onUpdate:expandedPlatformPayout': (val: string | null) => void
  platformPayouts: Record<string, PlatformPayout | undefined>
  loadPlatformPayout: (platformId: string) => void
  methodTypeIcon: Record<string, string>
  methodTypeLabel: Record<string, string>
}

const props = defineProps<PlatformGridProps>()

// ── Computed ──────────────────────────────────────────────────────────────
const platformCards = computed(() => props.platforms.map(platform => {
  const meta = props.platformMeta[platform.toLowerCase()]
  const account = props.accounts.find((a: any) => 
    a.provider?.toLowerCase() === platform.toLowerCase() || 
    a.provider_name?.toLowerCase() === platform.toLowerCase()
  )
  const isConnected = account?.has_credentials
  return { platform, meta, account, isConnected }
}))

// ── Helpers ───────────────────────────────────────────────────────────────
function formatDisplayName(platform: string): string {
  const displayNames: Record<string, string> = {
    'hackerone': 'HackerOne',
    'bugcrowd': 'Bugcrowd',
    'intigriti': 'Intigriti',
    'synack': 'Synack',
    'yeswehack': 'YesWeHack',
    'immunefi': 'Immunefi',
    'code4rena': 'Code4rena',
    'cantina': 'Cantina',
    'sherlock': 'Sherlock',
    'codehawks': 'CodeHawks',
    'outlier': 'Outlier',
    'mindrift': 'Mindrift',
    'dataannotation': 'DataAnnotation',
    'remotasks': 'Remotasks',
    'freelancer_microtask': 'Freelancer Microtasks',
    'linkedin_easyapply': 'LinkedIn Easy Apply',
    'opyre_microtask': 'Opyre Microtasks',
    'opencollective': 'OpenCollective',
    'opencollective_projects': 'OpenCollective Projects',
    'opire': 'Opire',
    'algora': 'Algora',
    'superteam': 'Superteam',
    'github_sponsors': 'GitHub Sponsors',
    'freelancer': 'Freelancer.com',
    'issuehunt': 'IssueHunt',
    'issuehand': 'IssueHand',
    'opyre': 'Opyre',
  }
  return displayNames[platform] || platform
}

function getIconForPlatform(platform: string) {
  // Return appropriate icon component based on platform
  return Globe
}
</script>

<template>
  <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
    <div
      v-for="card in platformCards" :key="card.platform"
      class="card-base rounded-xl p-4 transition-all hover:border-primary/30"
    >
      <div class="flex items-start justify-between">
        <div class="flex items-center gap-3">
          <div :class="['flex h-9 w-9 items-center justify-center rounded-lg', card.meta?.bg || 'bg-surface/50']">
            <component :is="getIconForPlatform(card.platform)" :class="['h-4 w-4', card.meta?.color || 'text-muted-foreground']" />
          </div>
          <div>
            <p class="text-sm font-semibold text-foreground">{{ formatDisplayName(card.platform) }}</p>
            <template v-if="card.isConnected">
              <p class="text-xs text-success flex items-center gap-1">
                <CheckCircle2 class="h-3 w-3" /> Conectado
              </p>
            </template>
            <template v-else>
              <p class="text-xs text-muted-foreground">No conectado</p>
            </template>
          </div>
        </div>
        <div class="flex items-center gap-2">
          <template v-if="card.isConnected">
            <Badge variant="success" class="text-[9px]">ACTIVO</Badge>
            <button
              @click="disconnectPlatform(card.platform.toLowerCase())"
              class="text-muted-foreground hover:text-destructive transition-colors"
              title="Desconectar"
            >
              <XCircle class="h-4 w-4" />
            </button>
          </template>
          <template v-else>
            <Button variant="outline" size="sm" @click="$emit('update:showConnectForm', $emit('update:showConnectForm') === card.platform ? null : card.platform)">
              <Plus class="h-3 w-3" /> Conectar
            </Button>
          </template>
        </div>
      </div>

      <!-- Connect form -->
      <div v-if="showConnectForm === card.platform" class="mt-3 space-y-2 border-t border-border/30 pt-3">
        <Input
          v-model="props.connectEmail"
          :placeholder="`Email en ${formatDisplayName(card.platform)}`"
          class="w-full"
        />
        <Input
          v-model="props.connectToken"
          placeholder="API Key o token"
          type="password"
          class="w-full"
        />
        <div class="flex gap-2">
          <Button size="sm" @click="connectPlatform(card.platform.toLowerCase())">
            <Link class="h-3 w-3" /> Vincular
          </Button>
          <Button variant="ghost" size="sm" @click="$emit('update:showConnectForm', null)">Cancelar</Button>
        </div>
      </div>

      <!-- Account data -->
      <template v-if="card.isConnected">
        <div class="mt-3 grid grid-cols-2 gap-3 border-t border-border/30 pt-3">
          <div>
            <p class="text-[9px] text-muted-foreground">Email</p>
            <p class="text-xs font-medium text-foreground">{{ card.account?.email || '—' }}</p>
          </div>
          <div>
            <p class="text-[9px] text-muted-foreground">Última sincronización</p>
            <div class="flex items-center gap-1">
              <p class="text-xs font-medium text-foreground">
                {{ card.account?.last_sync?.slice(0, 10) || card.account?.last_checked?.slice(0, 10) || '—' }}
              </p>
              <button
                @click="syncPlatform(card.platform.toLowerCase())"
                :disabled="syncingPlatform === card.platform.toLowerCase()"
                class="text-muted-foreground/50 hover:text-foreground transition-colors"
                title="Sincronizar ahora"
              >
                <RefreshCw :class="['h-3 w-3', syncingPlatform === card.platform.toLowerCase() ? 'animate-spin' : '']" />
              </button>
            </div>
          </div>
          <div>
            <p class="text-[9px] text-muted-foreground">Estado</p>
            <p class="text-xs font-medium" :class="card.account?.session_state === 'connected' ? 'text-success' : 'text-muted-foreground'">
              {{ card.account?.session_state || 'desconocido' }}
            </p>
          </div>
          <div>
            <p class="text-[9px] text-muted-foreground">Salud</p>
            <p class="text-xs font-medium text-foreground">{{ card.account?.health_status || '—' }}</p>
          </div>
        </div>
      </template>

      <!-- Payout methods for this platform -->
      <div class="mt-3 border-t border-border/30 pt-3">
        <button
          @click="$emit('update:expandedPlatformPayout', expandedPlatformPayout === card.platform.toLowerCase() ? null : card.platform.toLowerCase()); 
                  if (expandedPlatformPayout === card.platform.toLowerCase()) loadPlatformPayout(card.platform.toLowerCase())"
          class="flex w-full items-center justify-between text-[10px] text-muted-foreground hover:text-foreground transition-colors"
        >
          <span class="flex items-center gap-1">
            <DollarSign class="h-3 w-3" />
            Métodos de retiro recomendados (Argentina)
          </span>
          <ChevronDown v-if="expandedPlatformPayout !== card.platform.toLowerCase()" class="h-3 w-3" />
          <ChevronUp v-else class="h-3 w-3" />
        </button>
        <div v-if="expandedPlatformPayout === card.platform.toLowerCase() && platformPayouts[card.platform.toLowerCase()]" class="mt-2 space-y-1.5">
          <p class="text-[9px] text-muted-foreground">KYC requerido: {{ platformPayouts[card.platform.toLowerCase()].kyc_required }}</p>
          <div v-for="m in platformPayouts[card.platform.toLowerCase()].recommended_methods" :key="m.id" class="rounded-lg bg-surface/20 px-2.5 py-2">
            <div class="flex items-center justify-between">
              <div>
                <p class="text-xs font-semibold text-foreground">{{ m.name }}</p>
                <p class="text-[9px]" :class="methodTypeIcon[m.type] || 'text-muted-foreground'">{{ methodTypeLabel[m.type] || m.type }} · KYC: {{ m.kyc_level }}</p>
              </div>
              <div class="text-right text-[9px] text-muted-foreground">
                <p v-if="m.fee_percent > 0">{{ m.fee_percent }}% fee</p>
                <p v-else>0% fee</p>
                <p>{{ m.arrival_days }}</p>
              </div>
            </div>
            <p class="mt-0.5 text-[9px] text-muted-foreground">{{ m.notes }}</p>
          </div>
          <p v-if="platformPayouts[card.platform.toLowerCase()].notes" class="mt-1 text-[9px] italic text-muted-foreground">{{ platformPayouts[card.platform.toLowerCase()].notes }}</p>
        </div>
        <div v-else-if="expandedPlatformPayout === card.platform.toLowerCase()" class="mt-2 text-[9px] text-muted-foreground animate-pulse">Cargando recomendaciones...</div>
      </div>
    </div>
  </div>
</template>