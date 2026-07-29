/**
 * OWNEX Icons - Core System Icons
 * Used by Sidebar, StatusBar, and other components
 */

import IconBase from './IconBase.vue'
import { defineComponent, h } from 'vue'

// Layout Dashboard
const LayoutDashboard = defineComponent({
  name: 'IconLayoutDashboard',
  setup() {
    return () => h(IconBase, { size: 18, strokeWidth: 2 }, {
      default: () => [
        h('rect', { x: '3', y: '3', width: '7', height: '7', rx: '1' }),
        h('rect', { x: '14', y: '3', width: '7', height: '7', rx: '1' }),
        h('rect', { x: '3', y: '14', width: '7', height: '7', rx: '1' }),
        h('rect', { x: '14', y: '14', width: '7', height: '7', rx: '1' }),
      ],
    })
  },
})

// Search
const Search = defineComponent({
  name: 'IconSearch',
  setup() {
    return () => h(IconBase, { size: 18, strokeWidth: 2 }, {
      default: () => [
        h('circle', { cx: '11', cy: '11', r: '8' }),
        h('path', { d: 'M21 21l-4.35-4.35' }),
      ],
    })
  },
})

// Flag
const Flag = defineComponent({
  name: 'IconFlag',
  setup() {
    return () => h(IconBase, { size: 18, strokeWidth: 2 }, {
      default: () => [
        h('path', { d: 'M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z' }),
        h('line', { x1: '4', y1: '22', x2: '4', y2: '15' }),
      ],
    })
  },
})

// FileText
const FileText = defineComponent({
  name: 'IconFileText',
  setup() {
    return () => h(IconBase, { size: 18, strokeWidth: 2 }, {
      default: () => [
        h('path', { d: 'M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z' }),
        h('polyline', { points: '14 2 14 8 20 8' }),
        h('line', { x1: '16', y1: '13', x2: '8', y2: '13' }),
        h('line', { x1: '16', y1: '17', x2: '8', y2: '17' }),
        h('polyline', { points: '10 9 9 9 8 9' }),
      ],
    })
  },
})

// Brain
const Brain = defineComponent({
  name: 'IconBrain',
  setup() {
    return () => h(IconBase, { size: 18, strokeWidth: 2 }, {
      default: () => [
        h('path', { d: 'M12 2a3 3 0 0 0-3 3v1a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3z' }),
        h('path', { d: 'M12 8a3 3 0 0 0-3 3v6a3 3 0 0 0 6 0v-6a3 3 0 0 0-3-3z' }),
        h('path', { d: 'M6 14a6 6 0 0 0 12 0h-12z' }),
        h('path', { d: 'M9 14a2 2 0 1 1 4 0 2 2 0 1 1-4 0z' }),
      ],
    })
  },
})

// Settings
const Settings = defineComponent({
  name: 'IconSettings',
  setup() {
    return () => h(IconBase, { size: 18, strokeWidth: 2 }, {
      default: () => [
        h('circle', { cx: '12', cy: '12', r: '3' }),
        h('path', { d: 'M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z' }),
      ],
    })
  },
})

// Shield
const Shield = defineComponent({
  name: 'IconShield',
  setup() {
    return () => h(IconBase, { size: 18, strokeWidth: 2 }, {
      default: () => [
        h('path', { d: 'M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z' }),
      ],
    })
  },
})

// Hammer
const Hammer = defineComponent({
  name: 'IconHammer',
  setup() {
    return () => h(IconBase, { size: 18, strokeWidth: 2 }, {
      default: () => [
        h('path', { d: 'M15.036 15.036a9 9 0 0 1-12.727 0l-2.829 2.828a1 1 0 0 0 1.414 1.414l2.828-2.829a9 9 0 0 1 12.727 0l1.851 1.85a1 1 0 0 0 1.414-1.414l-1.85-1.85z' }),
        h('path', { d: 'M12 12l3-3' }),
        h('path', { d: 'M15 9l3-3' }),
        h('path', { d: 'M18 6l3-3' }),
      ],
    })
  },
})

// Zap
const Zap = defineComponent({
  name: 'IconZap',
  setup() {
    return () => h(IconBase, { size: 18, strokeWidth: 2 }, {
      default: () => [
        h('polygon', { points: '13 2 3 14 12 14 11 22 21 10 12 10 13 2' }),
      ],
    })
  },
})

// Vault
const Vault = defineComponent({
  name: 'IconVault',
  setup() {
    return () => h(IconBase, { size: 18, strokeWidth: 2 }, {
      default: () => [
        h('rect', { x: '3', y: '11', width: '18', height: '11', rx: '2', ry: '2' }),
        h('path', { d: 'M7 11V7a5 5 0 0 1 10 0v4' }),
      ],
    })
  },
})

// Globe
const Globe = defineComponent({
  name: 'IconGlobe',
  setup() {
    return () => h(IconBase, { size: 18, strokeWidth: 2 }, {
      default: () => [
        h('circle', { cx: '12', cy: '12', r: '10' }),
        h('line', { x1: '2', y1: '12', x2: '22', y2: '12' }),
        h('path', { d: 'M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z' }),
      ],
    })
  },
})

// Rocket
const Rocket = defineComponent({
  name: 'IconRocket',
  setup() {
    return () => h(IconBase, { size: 18, strokeWidth: 2 }, {
      default: () => [
        h('path', { d: 'M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c1.26-1.5 2-5 2-5s-3.74-.5-5 2c-1.26 1.5-2 5-2 5z' }),
        h('path', { d: 'M12 14.5v-9.5a3 3 0 0 0-3-3 3 3 0 0 0-3 3v5.5' }),
        h('path', { d: 'M12 14.5v-9.5a3 3 0 0 1 3-3 3 3 0 0 1 3 3v5.5' }),
        h('path', { d: 'M9 19.5c0 1.5 3 2.5 6 2.5s6-1 6-2.5' }),
      ],
    })
  },
})

// CPU
const Cpu = defineComponent({
  name: 'IconCpu',
  setup() {
    return () => h(IconBase, { size: 18, strokeWidth: 2 }, {
      default: () => [
        h('rect', { x: '4', y: '4', width: '16', height: '16', rx: '2' }),
        h('rect', { x: '9', y: '9', width: '6', height: '6' }),
        h('line', { x1: '9', y1: '1', x2: '9', y2: '4' }),
        h('line', { x1: '15', y1: '1', x2: '15', y2: '4' }),
        h('line', { x1: '9', y1: '20', x2: '9', y2: '23' }),
        h('line', { x1: '15', y1: '20', x2: '15', y2: '23' }),
        h('line', { x1: '1', y1: '9', x2: '4', y2: '9' }),
        h('line', { x1: '1', y1: '15', x2: '4', y2: '15' }),
        h('line', { x1: '20', y1: '9', x2: '23', y2: '9' }),
        h('line', { x1: '20', y1: '15', x2: '23', y2: '15' }),
      ],
    })
  },
})

// Activity
const Activity = defineComponent({
  name: 'IconActivity',
  setup() {
    return () => h(IconBase, { size: 18, strokeWidth: 2 }, {
      default: () => [
        h('polyline', { points: '22 12 18 12 15 21 9 3 6 12 2 12' }),
      ],
    })
  },
})

// CheckCircle
const CheckCircle = defineComponent({
  name: 'IconCheckCircle',
  setup() {
    return () => h(IconBase, { size: 18, strokeWidth: 2 }, {
      default: () => [
        h('path', { d: 'M22 11.08V12a10 10 0 1 1-5.93-9.14' }),
        h('polyline', { points: '22 4 12 14.01 9 11.01' }),
      ],
    })
  },
})

// AlertCircle
const AlertCircle = defineComponent({
  name: 'IconAlertCircle',
  setup() {
    return () => h(IconBase, { size: 18, strokeWidth: 2 }, {
      default: () => [
        h('circle', { cx: '12', cy: '12', r: '10' }),
        h('line', { x1: '12', y1: '8', x2: '12', y2: '12' }),
        h('line', { x1: '12', y1: '16', x2: '12.01', y2: '16' }),
      ],
    })
  },
})

// Circle (idle)
const Circle = defineComponent({
  name: 'IconCircle',
  setup() {
    return () => h(IconBase, { size: 18, strokeWidth: 2 }, {
      default: () => [
        h('circle', { cx: '12', cy: '12', r: '10' }),
      ],
    })
  },
})

// GitBranch (pattern)
const GitBranch = defineComponent({
  name: 'IconGitBranch',
  setup() {
    return () => h(IconBase, { size: 18, strokeWidth: 2 }, {
      default: () => [
        h('line', { x1: '6', y1: '3', x2: '6', y2: '15' }),
        h('circle', { cx: '18', cy: '6', r: '3' }),
        h('circle', { cx: '6', cy: '18', r: '3' }),
        h('path', { d: 'M18 9a9 9 0 0 1-9 9' }),
      ],
    })
  },
})

// AlertTriangle
const AlertTriangle = defineComponent({
  name: 'IconAlertTriangle',
  setup() {
    return () => h(IconBase, { size: 18, strokeWidth: 2 }, {
      default: () => [
        h('path', { d: 'M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z' }),
        h('line', { x1: '12', y1: '9', x2: '12', y2: '13' }),
        h('line', { x1: '12', y1: '17', x2: '12.01', y2: '17' }),
      ],
    })
  },
})

// Trophy
const Trophy = defineComponent({
  name: 'IconTrophy',
  setup() {
    return () => h(IconBase, { size: 18, strokeWidth: 2 }, {
      default: () => [
        h('path', { d: 'M6 9H4.5a2.5 2.5 0 0 1 0-5H6' }),
        h('path', { d: 'M18 9h1.5a2.5 2.5 0 0 0 0-5H18' }),
        h('path', { d: 'M4 22h16' }),
        h('path', { d: 'M18 9a2 2 0 0 0 0-12H6a2 2 0 0 0 0 12' }),
      ],
    })
  },
})

// Lightbulb (insight)
const Lightbulb = defineComponent({
  name: 'IconLightbulb',
  setup() {
    return () => h(IconBase, { size: 18, strokeWidth: 2 }, {
      default: () => [
        h('path', { d: 'M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z' }),
      ],
    })
  },
})

// ChevronLeft
const ChevronLeft = defineComponent({
  name: 'IconChevronLeft',
  setup() {
    return () => h(IconBase, { size: 18, strokeWidth: 2 }, {
      default: () => [
        h('path', { d: 'M15 18l-6-6 6-6' }),
      ],
    })
  },
})

// ChevronRight
const ChevronRight = defineComponent({
  name: 'IconChevronRight',
  setup() {
    return () => h(IconBase, { size: 18, strokeWidth: 2 }, {
      default: () => [
        h('path', { d: 'M9 18l6-6-6-6' }),
      ],
    })
  },
})

// X (close)
const X = defineComponent({
  name: 'IconX',
  setup() {
    return () => h(IconBase, { size: 18, strokeWidth: 2 }, {
      default: () => [
        h('line', { x1: '18', y1: '6', x2: '6', y2: '18' }),
        h('line', { x1: '6', y1: '6', x2: '18', y2: '18' }),
      ],
    })
  },
})

// Plus
const Plus = defineComponent({
  name: 'IconPlus',
  setup() {
    return () => h(IconBase, { size: 18, strokeWidth: 2 }, {
      default: () => [
        h('line', { x1: '12', y1: '5', x2: '12', y2: '19' }),
        h('line', { x1: '5', y1: '12', x2: '19', y2: '12' }),
      ],
    })
  },
})

// ExternalLink
const ExternalLink = defineComponent({
  name: 'IconExternalLink',
  setup() {
    return () => h(IconBase, { size: 18, strokeWidth: 2 }, {
      default: () => [
        h('path', { d: 'M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6' }),
        h('polyline', { points: '15 3 21 3 21 9' }),
        h('line', { x1: '10', y1: '14', x2: '21', y2: '3' }),
      ],
    })
  },
})

// Export all icons
export {
  IconBase,
  LayoutDashboard,
  Search,
  Flag,
  FileText,
  Brain,
  Settings,
  Shield,
  Hammer,
  Zap,
  Vault,
  Globe,
  Rocket,
  Cpu,
  Activity,
  CheckCircle,
  AlertCircle,
  Circle,
  GitBranch,
  AlertTriangle,
  Trophy,
  Lightbulb,
  ChevronLeft,
  ChevronRight,
  X,
  Plus,
  ExternalLink,
}