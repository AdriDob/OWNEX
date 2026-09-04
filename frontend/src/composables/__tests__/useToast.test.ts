import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useToast } from '@/composables/useToast'

const toastTimerCalls = vi.hoisted(() => {
  const calls: Array<[() => void, number]> = []
  const orig = globalThis.setTimeout
  globalThis.setTimeout = ((fn: () => void, ms: number) => {
    calls.push([fn, ms])
    return 0 as any
  }) as any
  return { calls, orig }
})

beforeEach(() => {
  toastTimerCalls.calls.length = 0
  const { toasts } = useToast()
  toasts.value = []
})

describe('useToast', () => {
  it('returns toasts ref, toast helpers, and removeToast', () => {
    const { toasts, toast, removeToast } = useToast()
    expect(toasts.value).toEqual([])
    expect(typeof toast.success).toBe('function')
    expect(typeof toast.error).toBe('function')
    expect(typeof toast.warning).toBe('function')
    expect(typeof toast.info).toBe('function')
    expect(typeof removeToast).toBe('function')
  })

  it('toast.success adds a success toast', () => {
    const { toasts, toast } = useToast()
    toast.success('Done', 'Operation completed')
    expect(toasts.value).toHaveLength(1)
    expect(toasts.value[0].type).toBe('success')
    expect(toasts.value[0].title).toBe('Done')
    expect(toasts.value[0].message).toBe('Operation completed')
    expect(toasts.value[0].id).toMatch(/^toast-/)
  })

  it('toast.error adds an error toast', () => {
    const { toasts, toast } = useToast()
    toast.error('Failed', 'Something broke')
    expect(toasts.value[0].type).toBe('error')
    expect(toasts.value[0].title).toBe('Failed')
  })

  it('toast.warning adds a warning toast', () => {
    const { toasts, toast } = useToast()
    toast.warning('Caution')
    expect(toasts.value[0].type).toBe('warning')
    expect(toasts.value[0].title).toBe('Caution')
    expect(toasts.value[0].message).toBeUndefined()
  })

  it('toast.info adds an info toast', () => {
    const { toasts, toast } = useToast()
    toast.info('Note')
    expect(toasts.value[0].type).toBe('info')
    expect(toasts.value[0].title).toBe('Note')
  })

  it('removeToast removes a toast by id', () => {
    const { toasts, toast, removeToast } = useToast()
    toast.success('Test')
    const id = toasts.value[0].id
    expect(toasts.value).toHaveLength(1)
    removeToast(id)
    expect(toasts.value).toHaveLength(0)
  })

  it('removeToast does nothing for unknown id', () => {
    const { toasts, toast, removeToast } = useToast()
    toast.success('Test')
    removeToast('nonexistent')
    expect(toasts.value).toHaveLength(1)
  })

  it('auto-dismiss removes toast after default duration', () => {
    const { toasts, toast } = useToast()
    toast.success('Auto dismiss')
    expect(toasts.value).toHaveLength(1)
    const call = toastTimerCalls.calls.find(([, ms]) => ms === 4000)
    expect(call).toBeDefined()
    call![0]()
    expect(toasts.value).toHaveLength(0)
  })

  it('toast helpers do not expose custom duration', () => {
    const { toasts, toast } = useToast()
    const before = toastTimerCalls.calls.length
    toast.info('Note', 'msg')
    expect(toasts.value).toHaveLength(1)
    expect(toastTimerCalls.calls.length).toBe(before + 1)
    const lastCall = toastTimerCalls.calls[toastTimerCalls.calls.length - 1]
    expect(lastCall[1]).toBe(4000)
  })

  it('multiple toasts are added sequentially', () => {
    const { toasts, toast } = useToast()
    toast.success('First')
    toast.error('Second')
    toast.info('Third')
    expect(toasts.value).toHaveLength(3)
    expect(toasts.value[0].title).toBe('First')
    expect(toasts.value[1].title).toBe('Second')
    expect(toasts.value[2].title).toBe('Third')
  })

  it('returns iconMap, colorMap, iconColorMap', () => {
    const { iconMap, colorMap, iconColorMap } = useToast()
    expect(iconMap.success).toBeDefined()
    expect(iconMap.error).toBeDefined()
    expect(colorMap.success).toContain('border-l-success')
    expect(iconColorMap.success).toContain('text-success')
  })
})
