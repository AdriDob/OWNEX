// MoneyPrinterTurbo API Service — talks DIRECTLY to the MPT sidecar.
// MPT has its own API (default http://127.0.0.1:8081 — :8080 is Open WebUI
// on this host). Override with VITE_MPT_BASE_URL. No OWNEX-backend proxy.

const MPT_BASE_URL = (import.meta.env.VITE_MPT_BASE_URL as string | undefined)?.replace(/\/$/, '') || 'http://127.0.0.1:8081'

export function getMptBaseUrl(): string {
  return MPT_BASE_URL
}

export interface MPTTask {
  task_id: string
  state: 'pending' | 'processing' | 'completed' | 'failed'
  params: {
    video_subject?: string
    video_count?: number
    video_duration?: number
    video_aspect?: string
    voice_name?: string
    subtitle_enabled?: boolean
    material_source?: string
  }
  videos?: string[]
  combined_videos?: string[]
  error?: string
  created_at: string
  updated_at: string
  progress?: number
}

export interface MPTVideoRequest {
  video_subject: string
  video_count?: number
  video_duration?: number
  video_aspect?: 'portrait' | 'landscape' | 'square'
  voice_name?: string
  subtitle_enabled?: boolean
  material_source?: 'pexels' | 'pixabay' | 'coverr' | 'local'
  bgm_type?: string
}

export interface MPTTaskListResponse {
  tasks: MPTTask[]
  total: number
  page: number
  page_size: number
}

export interface MPTStatus {
  status: 'healthy' | 'degraded'
  version?: string
}

async function mptFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${MPT_BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(init.headers || {}) },
    ...init,
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: 'Request failed' }))
    throw new Error((body as { detail?: string }).detail || `HTTP ${res.status}`)
  }
  return res.json() as Promise<T>
}

export async function fetchMPTTasks(params: {
  page?: number
  page_size?: number
  state?: string
} = {}): Promise<{ tasks: any[]; total: number; page: number; page_size: number }> {
  const params2 = new URLSearchParams()
  if (params.page) params2.append('page', params.page.toString())
  if (params.page_size) params2.append('page_size', params.page_size.toString())
  if (params.state) params2.append('state', params.state)

  return mptFetch(`/api/v1/tasks${params2.toString() ? `?${params2.toString()}` : ''}`)
}

function viralDefaults() {
  return {
    video_count: 1,
    video_duration: 35,
    video_aspect: 'portrait',
    voice_name: 'en-US-GuyNeural',
    subtitle_enabled: true,
    material_source: 'pexels',
    video_clip_duration: 3,
    paragraph_number: 1,
  }
}

export async function createMPTVideo(request: {
  video_subject: string
  video_count?: number
  video_duration?: number
  video_aspect?: string
  voice_name?: string
  subtitle_enabled?: boolean
  material_source?: string
}): Promise<{ task_id: string; status: string }> {
  return mptFetch<{ task_id: string; status: string }>('/api/v1/videos', {
    method: 'POST',
    body: JSON.stringify({ ...viralDefaults(), ...request }),
  })
}

export async function retryMPTTask(taskId: string): Promise<void> {
  const task = await getMPTTask(taskId)
  if (!task) throw new Error('Task not found')

  await mptFetch('/api/v1/videos', {
    method: 'POST',
    body: JSON.stringify({
      ...viralDefaults(),
      video_subject: task.params?.video_subject || 'Generated Video',
    }),
  })
}

export async function getMPTTask(taskId: string): Promise<any | null> {
  try {
    return await mptFetch(`/api/v1/tasks/${taskId}`)
  } catch {
    return null
  }
}

export async function deleteMPTTask(taskId: string): Promise<void> {
  await mptFetch(`/api/v1/tasks/${taskId}`, { method: 'DELETE' })
}

export async function getMPTStatus(): Promise<{ status: 'healthy' | 'degraded' }> {
  try {
    const data = await mptFetch<{ status: unknown }>('/health')
    return { status: data.status === true || data.status === 'ok' ? 'healthy' : 'degraded' }
  } catch {
    return { status: 'degraded' }
  }
}
