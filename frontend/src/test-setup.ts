import { config } from '@vue/test-utils'

config.global.stubs = {
  'router-link': true,
  'router-view': true,
  Transition: false,
}

// Stub Lucide icon components to suppress warnings in page tests
const iconStubs: Record<string, boolean> = {}
const lucideIcons = [
  'Activity', 'AlertTriangle', 'ArrowRight', 'Bell', 'BookOpen', 'Bug', 'Check',
  'ChevronDown', 'ChevronRight', 'Clock', 'Cpu', 'Crosshair', 'Download',
  'DollarSign', 'Eye', 'ExternalLink', 'Filter', 'Globe', 'GripVertical',
  'Info', 'Key', 'Loader2', 'Maximize2', 'Minimize2', 'Monitor', 'Moon',
  'Palette', 'Pause', 'Play', 'Plus', 'RefreshCw', 'Save', 'Scan',
  'Search', 'Shield', 'ShieldCheck', 'Smartphone', 'Sparkles', 'Square',
  'Sun', 'Target', 'Trash2', 'Upload', 'User', 'Wrench', 'X', 'Zap',
  'ArrowUpDown', 'Cog',
]
for (const name of lucideIcons) {
  iconStubs[name] = true
}
config.global.stubs = { ...config.global.stubs, ...iconStubs }
