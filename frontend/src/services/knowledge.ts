import { api } from '@/lib/api'

// ── Knowledge Bridge (Obsidian vault) ──

export interface KnowledgeStatus {
  connected: boolean
  vault_path: string
  status: string
  provider: string
  last_scan: string | null
}

export interface KnowledgeIndexStats {
  notes: number
  distinct_tags: number
  links: number
  last_scan: string
}

export interface KnowledgeHealthIssue {
  from: string
  to: string
  kind: string
}

export interface KnowledgeDuplicateItem {
  paths: string[]
}

export interface KnowledgeMissingItem {
  path: string
  reason?: string
}

export interface KnowledgeVaultHealth {
  path: string
  status: string
  files: number
  markdown: number
  attachments: number
  last_scan: string
  index_healthy: boolean
}

export interface KnowledgeGitStatus {
  is_repo: boolean
  branch: string | null
  dirty_files: number
  last_commit: string | null
  details?: Record<string, unknown>
}

export interface KnowledgeSecretFinding {
  file: string
  kind: string
  line: number
  snippet: string
}

export interface KnowledgeSecurityScan {
  clean: boolean
  findings: KnowledgeSecretFinding[]
  scanned: number
}

export interface KnowledgeBackupInfo {
  name: string
  size?: number
  created_at?: string
}

export interface KnowledgeHealth {
  connected: boolean
  vault?: KnowledgeVaultHealth
  index?: KnowledgeIndexStats
  health?: {
    broken_links: number
    duplicate_notes: number
    missing_attachments: number
    broken_link_items: KnowledgeHealthIssue[]
    duplicate_items: KnowledgeDuplicateItem[]
    missing_items: KnowledgeMissingItem[]
  }
  git?: KnowledgeGitStatus
  security?: KnowledgeSecurityScan
  backups?: {
    count: number
    last: KnowledgeBackupInfo | null
  }
}

export interface KnowledgeSearchResult {
  path: string
  title: string
  snippet: string
  relevance: number
  tags: string[]
  modified: string
}

export interface KnowledgeSearchResponse {
  query: string
  results: KnowledgeSearchResult[]
  provider: string
}

export interface KnowledgeNote {
  path: string
  content: string
  frontmatter: Record<string, unknown>
  tags: string[]
  links: string[]
  modified: string
}

export interface KnowledgeContextNote {
  source: string
  title: string
  fragment: string
  relevance: number
  modified: string
  tags: string[]
  related: { path: string; score: number }[]
}

export interface KnowledgeContext {
  query: string
  generated_at: string
  note_count: number
  notes: KnowledgeContextNote[]
}

export interface KnowledgeScanResult {
  ok: boolean
  full: boolean
  added: number
  updated: number
  removed: number
  skipped?: number
  stats: KnowledgeIndexStats
}

export interface KnowledgeSyncResult {
  ok: boolean
  reason?: string
  scan?: { added: number; updated: number; removed: number }
  embeddings?: { computed: number; skipped: string | number }
  health?: Record<string, unknown>
}

export interface KnowledgeHistory {
  snapshots: Record<string, unknown>[]
}

export interface KnowledgeSnapshotList {
  snapshots: string[]
}

export interface KnowledgeSnapshotCreated {
  ok: boolean
  snapshot: string
  path?: string
}

// ── API calls ──

export async function fetchKnowledgeStatus(): Promise<KnowledgeStatus> {
  return api.get<KnowledgeStatus>('/api/knowledge/').catch(() => ({
    connected: false,
    vault_path: '',
    status: 'unknown',
    provider: 'local',
    last_scan: null,
  }))
}

export async function connectVault(path: string): Promise<KnowledgeStatus> {
  return api.post<KnowledgeStatus>('/api/knowledge/connect', { path })
}

export async function disconnectVault(): Promise<KnowledgeStatus> {
  return api.post<KnowledgeStatus>('/api/knowledge/disconnect', {})
}

export async function scanVault(full = false): Promise<KnowledgeScanResult> {
  return api.post<KnowledgeScanResult>(`/api/knowledge/scan?full=${full}`, {})
}

export async function initializeVault(): Promise<Record<string, unknown>> {
  return api.post<Record<string, unknown>>('/api/knowledge/initialize', {})
}

export async function searchKnowledge(q: string, limit = 10): Promise<KnowledgeSearchResponse> {
  return api.get<KnowledgeSearchResponse>(`/api/knowledge/search?q=${encodeURIComponent(q)}&limit=${limit}`)
}

export async function fetchNote(path: string): Promise<KnowledgeNote> {
  return api.get<KnowledgeNote>(`/api/knowledge/note?path=${encodeURIComponent(path)}`)
}

export async function fetchContext(q: string, maxNotes = 5): Promise<KnowledgeContext> {
  return api.get<KnowledgeContext>(`/api/knowledge/context?q=${encodeURIComponent(q)}&max_notes=${maxNotes}`)
}

export async function fetchKnowledgeHealth(): Promise<KnowledgeHealth> {
  return api.get<KnowledgeHealth>('/api/knowledge/health').catch(() => ({ connected: false }))
}

export async function fetchKnowledgeHistory(limit = 7): Promise<KnowledgeHistory> {
  return api.get<KnowledgeHistory>(`/api/knowledge/history?limit=${limit}`).catch(() => ({ snapshots: [] }))
}

export async function runKnowledgeSync(): Promise<KnowledgeSyncResult> {
  return api.post<KnowledgeSyncResult>('/api/knowledge/sync', {})
}

export async function fetchGitStatus(): Promise<KnowledgeGitStatus> {
  return api.get<KnowledgeGitStatus>('/api/knowledge/git/status')
}

export async function commitVault(message: string, authorized: boolean): Promise<Record<string, unknown>> {
  return api.post<Record<string, unknown>>(
    `/api/knowledge/git/commit?message=${encodeURIComponent(message)}&authorized=${authorized}`,
    {},
  )
}

export async function fetchSecurityScan(): Promise<KnowledgeSecurityScan> {
  return api.get<KnowledgeSecurityScan>('/api/knowledge/security/scan').catch(() => ({
    clean: true,
    findings: [],
    scanned: 0,
  }))
}

export async function fetchSnapshots(): Promise<KnowledgeSnapshotList> {
  return api.get<KnowledgeSnapshotList>('/api/knowledge/snapshots').catch(() => ({ snapshots: [] }))
}

export async function createSnapshot(authorized: boolean): Promise<KnowledgeSnapshotCreated> {
  return api.post<KnowledgeSnapshotCreated>(`/api/knowledge/snapshots?authorized=${authorized}`, {})
}
