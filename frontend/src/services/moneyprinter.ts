// MoneyPrinterTurbo API Service
import { api } from '@/lib/api'

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

const MPT_API_BASE = 'http://localhost:8080/api/v1'

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${MPT_API_BASE}${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }))
    throw new Error(error.detail || `HTTP ${response.status}`)
  }

  return response.json()
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

  return request<{ tasks: any[]; total: number; page: number; page_size: number }>(
    `/tasks${params2.toString() ? `?${params2.toString()}` : ''}`
  )
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
  return request<{ task_id: string; status: string }>('/videos', {
    method: 'POST',
    body: JSON.stringify({
      video_subject: request.video_subject,
      video_count: request.video_count || 1,
      video_duration: request.video_duration || 60,
      video_aspect: request.video_aspect || 'portrait',
      voice_name: request.voice_name || 'zh-CN-XiaoxiaoNeural-Female',
      subtitle_enabled: request.subtitle_enabled ?? true,
      material_source: request.material_source || 'pexels',
      video_clip_duration: 5,
      paragraph_number: 1,
    }),
  })
}

export async function retryMPTTask(taskId: string): Promise<void> {
  const task = await getMPTTask(taskId)
  if (!task) throw new Error('Task not found')

  await fetch('http://localhost:8080/api/v1/videos', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      video_subject: task.params?.video_subject || 'Generated Video',
      video_count: task.params?.video_count || 1,
      video_duration: task.params?.video_duration || 60,
      video_aspect: task.params?.video_aspect || 'portrait',
      voice_name: task.params?.voice_name || 'zh-CN-XiaoxiaoNeural-Female',
      subtitle_enabled: task.params?.subtitle_enabled ?? true,
      material_source: task.params?.material_source || 'pexels',
      video_clip_duration: 5,
      paragraph_number: 1,
    }),
  })
}

export async function getMPTTask(taskId: string): Promise<any | null> {
  try {
    const response = await fetch(`http://localhost:8080/api/v1/tasks/${taskId}`)
    if (response.ok) return response.json()
    return null
  } catch {
    return null
  }
}

export async function deleteMPTTask(taskId: string): Promise<void> {
  await fetch(`http://localhost:8080/api/v1/tasks/${taskId}`, { method: 'DELETE' })
}

export async function getMPTStatus(): Promise<{ status: 'healthy' | 'degraded' }> {
  try {
    const response = await fetch('http://localhost:8080/health')
    if (response.ok) {
      const data = await response.json()
      return { status: data.status === true ? 'healthy' : 'degraded' }
    }
    return { status: 'degraded' }
  } catch {
    return { status: 'degraded' }
  }
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

  return request(`/tasks${params2.toString() ? `?${params2.toString()}` : ''}`)
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
  return request<{ task_id: string; status: string }>('/videos', {
    method: 'POST',
    body: JSON.stringify({
      video_subject: request.video_subject,
      video_count: request.video_count || 1,
      video_duration: request.video_duration || 60,
      video_aspect: request.video_aspect || 'portrait',
      voice_name: request.voice_name || 'zh-CN-XiaoxiaoNeural-Female',
      subtitle_enabled: request.subtitle_enabled ?? true,
      material_source: request.material_source || 'pexels',
      video_clip_duration: 5,
      paragraph_number: 1,
    }),
  })
}

export async function retryMPTTask(taskId: string): Promise<void> {
  const task = await getMPTTask(taskId)
  if (!task) throw new Error('Task not found')

  await fetch('http://localhost:8080/api/v1/videos', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      video_subject: task.params?.video_subject || 'Generated Video',
      video_count: task.params?.video_count || 1,
      video_duration: task.params?.video_duration || 60,
      video_aspect: task.params?.video_aspect || 'portrait',
      voice_name: task.params?.voice_name || 'zh-CN-XiaoxiaoNeural-Female',
      subtitle_enabled: task.params?.subtitle_enabled ?? true,
      material_source: task.params?.material_source || 'pexels',
      video_clip_duration: 5,
      paragraph_number: 1,
    }),
  })
}

export async function getMPTTask(taskId: string): Promise<any | null> {
  try {
    const response = await fetch(`http://localhost:8080/api/v1/tasks/${taskId}`)
    if (response.ok) return response.json()
    return null
  } catch {
    return null
  }
}

export async function deleteMPTTask(taskId: string): Promise<void> {
  await fetch(`http://localhost:8080/api/v1/tasks/${taskId}`, { method: 'DELETE' })
}

export async function getMPTStatus(): Promise<{ status: 'healthy' | 'degraded' }> {
  try {
    const response = await fetch('http://localhost:8080/health')
    if (response.ok) {
      const data = await response.json()
      return { status: data.status === true ? 'healthy' : 'degraded' }
    }
    return { status: 'degraded' }
  } catch {
    return { status: 'degraded' }
  }
}