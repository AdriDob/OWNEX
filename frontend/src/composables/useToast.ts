import { ref, type Component } from 'vue'
import { CheckCircle2, AlertTriangle, AlertOctagon, Info, X } from '@lucide/vue'

export interface Toast {
  id: string
  type: 'success' | 'error' | 'warning' | 'info'
  title: string
  message?: string
  duration?: number
}

const toasts = ref<Toast[]>([])
let counter = 0

const iconMap: Record<string, any> = {
  success: CheckCircle2,
  error: AlertOctagon,
  warning: AlertTriangle,
  info: Info,
}

const colorMap: Record<string, string> = {
  success: 'border-l-success bg-success/5',
  error: 'border-l-destructive bg-destructive/5',
  warning: 'border-l-warning bg-warning/5',
  info: 'border-l-info bg-info/5',
}

const iconColorMap: Record<string, string> = {
  success: 'text-success',
  error: 'text-destructive',
  warning: 'text-warning',
  info: 'text-info',
}

function addToast(type: Toast['type'], title: string, message?: string, duration = 4000) {
  const id = `toast-${++counter}`
  toasts.value.push({ id, type, title, message, duration })
  if (duration > 0) {
    setTimeout(() => removeToast(id), duration)
  }
}

function removeToast(id: string) {
  const idx = toasts.value.findIndex(t => t.id === id)
  if (idx >= 0) toasts.value.splice(idx, 1)
}

export function useToast() {
  return {
    toasts,
    toast: {
      success: (title: string, message?: string) => addToast('success', title, message),
      error: (title: string, message?: string) => addToast('error', title, message),
      warning: (title: string, message?: string) => addToast('warning', title, message),
      info: (title: string, message?: string) => addToast('info', title, message),
    },
    removeToast,
    iconMap,
    colorMap,
    iconColorMap,
  }
}
