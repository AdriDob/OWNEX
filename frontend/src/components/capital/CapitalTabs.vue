<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { api, getRevenueMetrics, getEVRankedTargets, getPlatformsStatus } from '@/lib/api'
import type { RevenueMetricsData, EVTarget, PlatformStatus } from '@/lib/api'
import {
  DollarSign, TrendingUp, TrendingDown, Target, Wallet,
  Clock, CheckCircle2, XCircle, AlertCircle, Zap, Activity,
  ArrowUpRight, ArrowDownRight, CircleDot, RefreshCw, Filter,
  ChevronDown, ChevronUp, ExternalLink, Shield, Coins, PieChart,
  Zap as ZapIcon, Loader2, RotateCcw, Settings, Search, MoreHorizontal,
  Star, Flag, Crown, Gem, Zap as Zap2, Gauge, TrendingUp as TrendingUpIcon,
  ShieldCheck, PieChart, LineChart, Layers, BarChart3,
  Layers as LayersIcon, PieChart as PieChart2, LineChart as LineChartIcon,
  Target as TargetIcon, RefreshCw as RefreshCwIcon, Calendar, Flame, Shield, Coffee, TrendingUp, Gauge, ShieldCheck, PieChart, LineChart, Layers, BarChart3, Target as TargetIcon, RefreshCw as RefreshCwIcon, Calendar, Flame, Shield, Coffee, TrendingUp, Gauge, ShieldCheck, PieChart, LineChart, Layers, BarChart3, Target as TargetIcon, RefreshCw as RefreshCwIcon
} from '@lucide/vue'
import Card from '@/components/ui/Card.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import CardTitle from '@/components/ui/CardTitle.vue'
import CardContent from '@/components/ui/CardContent.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import Select from '@/components/ui/Select.vue'
import LoadingState from '@/components/ui/LoadingState.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import DataTable from '@/components/ui/DataTable.vue'
import KPIBlock from '@/components/ui/KPIBlock.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import { useToast } from '@/composables/useToast'

const { toast } = useToast()

// Props
interface Props {
  activeTab: string
  capitalData: any
  revenueData: any
  evTargets: any[]
  platforms: any[]
  runwayData: any
  riskData: any
  allocationData: any
  forecastingData: any
  diversificationData: any
  runwayLoading: boolean
  riskLoading: boolean
  allocationLoading: boolean
  forecastingLoading: boolean
  diversificationLoading: boolean
  autoRefresh: boolean
  payoutNotifications: boolean
  evLoading: boolean
  platformsLoading: boolean
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'tab-change': [tabId: string]
}>()

// Tab components - using dynamic imports for code splitting
const OverviewTab = () => import('./tabs/OverviewTab.vue')
const RunwayTab = () => import('./tabs/RunwayTab.vue')
const RiskTab = () => import('./tabs/RiskTab.vue')
const AllocationTab = () => import('./tabs/AllocationTab.vue')
const ForecastingTab = () => import('./tabs/ForecastingTab.vue')
const DiversificationTab = () => import('./tabs/DiversificationTab.vue')
const TargetsTab = () => import('./tabs/TargetsTab.vue')
const ProgramsTab = () => import('./tabs/ProgramsTab.vue')
const PipelineTab = () => import('./tabs/PipelineTab.vue')
const PlatformsTab = () => import('./tabs/PlatformsTab.vue')
const SettingsTab = () => import('./tabs/SettingsTab.vue')

const tabs = [
  { id: 'overview', label: 'Overview', component: OverviewTab },
  { id: 'runway', label: 'Runway', component: RunwayTab },
  { id: 'risk', label: 'Risk', component: RiskTab },
  { id: 'allocation', label: 'Allocation', component: AllocationTab },
  { id: 'forecasting', label: 'Forecasting', component: ForecastingTab },
  { id: 'diversification', label: 'Diversification', component: DiversificationTab },
  { id: 'progressive-scaling', label: 'Prog. Scaling', component: null },
  { id: 'targets', label: 'Targets', component: TargetsTab },
  { id: 'programs', label: 'Programs', component: ProgramsTab },
  { id: 'pipeline', label: 'Pipeline', component: PipelineTab },
  { id: 'platforms', label: 'Platforms', component: PlatformsTab },
  { id: 'settings', label: 'Settings', component: SettingsTab },
]

const tabsConfig = computed(() => tabs.map(t => ({ ...t, isDisabled: !t.component })))

const props = defineProps<{
  activeTab: string
  capitalData: any
  revenueData: any
  evTargets: any[]
  platforms: any[]
  runwayData: any
  riskData: any
  allocationData: any
  forecastingData: any
  diversificationData: any
  runwayLoading: boolean
  riskLoading: boolean
  allocationLoading: boolean
  forecastingLoading: boolean
  diversificationLoading: boolean
  autoRefresh: boolean
  payoutNotifications: boolean
  evLoading: boolean
  platformsLoading: boolean
}>()

const emit = defineEmits<{
  'tab-change': [tabId: string]
}>()

const currentTab = computed(() => tabs.find(t => t.id === props.activeTab) || tabs[0])
const currentComponent = computed(() => currentTab.value.component)

const formattedTabs = computed(() => tabs.map(t => ({
  id: t.id,
  label: t.label,
  disabled: !t.component
}))
</script>

<template>
  <div class="space-y-6 p-6">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4 mb-2">
      <div>
        <h1 class="text-2xl font-bold tracking-tight text-foreground">Capital Dashboard</h1>
        <p class="text-muted-foreground text-sm">
          Unified view: Payouts · EV Targets · Programs · Pipeline · Platform Speed · Economic Memory
        </p>
      </div>
      <div class="flex items-center gap-2">
        <Button variant="outline" size="sm" @click="$emit('tab-change', 'overview')" :disabled="true" class="gap-1">
          Refrescar Todo
        </Button>
        <Button variant="outline" size="sm" @click="$emit('tab-change', 'targets')" class="gap-1">
          Targets EV
        </Button>
      </div>
    </div>

    <!-- Tabs -->
    <div class="flex flex-wrap gap-1 border-b border-border/40 pb-1 mb-4">
      <button
        v-for="tab in formattedTabs"
        :key="tab.id"
        @click="$emit('tab-change', tab.id)"
        :disabled="tab.disabled"
        class="px-3 py-1.5 text-sm font-medium rounded-t-md transition-colors border-b-2 border-transparent
          hover:text-foreground/80 focus:outline-none focus:ring-2 focus:ring-ring
          disabled:opacity-50 disabled:cursor-not-allowed"
        :class="[
          'transition-all duration-200',
          props.activeTab === tab.id
            ? 'text-primary border-primary bg-primary/5'
            : 'text-muted-foreground hover:bg-accent/30'
        ]"
      >
        {{ tab.label }}
      </button>
    </div>

    <!-- Tab Content -->
    <div class="space-y-6">
      <component
        v-if="currentComponent"
        :is="currentComponent"
        :capital-data="capitalData"
        :revenue-data="revenueData"
        :ev-targets="evTargets"
        :platforms="platforms"
        :runway-data="runwayData"
        :risk-data="riskData"
        :allocation-data="allocationData"
        :forecasting-data="forecastingData"
        :diversification-data="diversificationData"
        :runway-loading="runwayLoading"
        :risk-loading="riskLoading"
        :allocation-loading="allocationLoading"
        :forecasting-loading="forecastingLoading"
        :diversification-loading="diversificationLoading"
        :auto-refresh="autoRefresh"
        :payout-notifications="payoutNotifications"
        :ev-loading="evLoading"
        :platforms-loading="platformsLoading"
        @tab-change="emit('tab-change', $event)"
      />
      <div v-else class="text-center text-muted-foreground py-12">
        <p>Tab no implementado</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { api, getRevenueMetrics, getEVRankedTargets, getPlatformsStatus } from '@/lib/api'
import type { RevenueMetricsData, EVTarget, PlatformStatus } from '@/lib/api'
import {
  DollarSign, TrendingUp, TrendingDown, Target, Wallet,
  Clock, CheckCircle2, XCircle, AlertCircle, Zap, Activity,
  ArrowUpRight, ArrowDownRight, CircleDot, RefreshCw, Filter,
  ChevronDown, ChevronUp, ExternalLink, Shield, Coins, PieChart,
  Zap as ZapIcon, Loader2, RotateCcw, Settings, Search, MoreHorizontal,
  Star, Flag, Crown, Gem, Zap as Zap2, Gauge, TrendingUp as TrendingUpIcon,
  ShieldCheck, PieChart, LineChart, Layers, BarChart3,
  Layers as LayersIcon, PieChart as PieChart2, LineChart as LineChartIcon,
  Target as TargetIcon, RefreshCw as RefreshCwIcon, Calendar, Flame, Shield, Coffee, TrendingUp, Gauge, ShieldCheck, PieChart, LineChart, Layers, BarChart3, Target as TargetIcon, RefreshCw as RefreshCwIcon, Calendar, Flame, Shield, Coffee, TrendingUp, Gauge, ShieldCheck, PieChart, LineChart, Layers, BarChart3, Target as TargetIcon, RefreshCw as RefreshCwIcon
} from '@lucide/vue'
import Card from '@/components/ui/Card.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import CardTitle from '@/components/ui/CardTitle.vue'
import CardContent from '@/components/ui/CardContent.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import Select from '@/components/ui/Select.vue'
import LoadingState from '@/components/ui/LoadingState.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import DataTable from '@/components/ui/DataTable.vue'
import KPIBlock from '@/components/ui/KPIBlock.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import { useToast } from '@/composables/useToast'

const { toast } = useToast()

// ... rest of the component logic would be extracted to sub-components
</script>