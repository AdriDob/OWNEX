// Capital Dashboard API Service - Extended CRUD Operations

import { api } from '@/lib/api'
import type { EVTarget, PlatformStatus, RevenueMetricsData } from '@/lib/api'

// ── Types ──
export interface CapitalDashboardData {
  capital: any
  revenue: any
  targets: any[]
  programs: any[]
  pipeline: any
  platform_speed: Record<string, number>
  economic_memory: any
}

export interface TargetCreateRequest {
  name: string
  domain: string
  platform?: string
  category?: string
  scope?: string
  payment_method?: string
  estimated_reward?: number
}

export interface TargetUpdateRequest {
  name?: string
  domain?: string
  platform?: string
  category?: string
  scope?: string
  status?: string
  estimated_reward?: number
}

export interface ProgramCreateRequest {
  name: string
  platform: string
  category: string
  estimated_reward?: number
  acceptance_rate?: number
}

export interface PlatformCreateRequest {
  name: string
  platform_type: string
  credentials: Record<string, string>
}

export interface PayoutCreateRequest {
  platform: string
  amount_usd: number
  currency: string
  status: 'pending' | 'confirmed' | 'paid'
  date: string
  notes?: string
}

export interface PayoutUpdateRequest {
  amount_usd?: number
  status?: 'pending' | 'confirmed' | 'paid'
  date?: string
  notes?: string
}

// ── Capital Dashboard ──
export async function getCapitalDashboard(): Promise<any> {
  return api.get('/api/revenue/capital-dashboard')
}

export async function getRevenueMetrics(): Promise<any> {
  return api.get('/api/revenue/metrics')
}

export async function getPlatformSpeed(): Promise<Record<string, number>> {
  return api.get('/api/revenue/platform-speed')
}

export async function getEVTargets(limit = 100): Promise<{ ranked: any[]; total_targets: number }> {
  return api.get(`/targets/ev-ranking?limit=${limit}`)
}

export async function getPlatformsStatus(): Promise<any[]> {
  return api.get('/platforms/status')
}

export async function getCapitalSnapshot(): Promise<any> {
  return api.get('/api/capital/snapshot')
}

export async function getRunwayEngine(): Promise<any> {
  return api.get('/api/capital/runway')
}

export async function getRiskEngine(): Promise<any> {
  return api.get('/api/capital/risk')
}

export async function getAllocationEngine(): Promise<any> {
  return api.get('/api/capital/allocation')
}

export async function getForecastingEngine(): Promise<any> {
  return api.get('/api/capital/forecasting')
}

export async function getDiversificationEngine(): Promise<any> {
  return api.get('/api/capital/diversification')
}

// ── Targets CRUD ──
export async function getTargets(params?: {
  skip?: number
  limit?: number
  sort_by?: string
  sort_order?: string
  search?: string
}) {
  return api.get<{ items: any[]; total: number }>('/targets', params as any)
}

export async function getTarget(targetId: number) {
  return api.get(`/targets/${targetId}`)
}

export async function createTarget(data: any) {
  return api.post('/targets', data)
}

export async function updateTarget(targetId: number, data: any) {
  return api.put(`/targets/${targetId}`, data)
}

export async function deleteTarget(targetId: number) {
  return api.delete(`/targets/${targetId}`)
}

export async function scanTarget(targetId: number, mode = 'quick') {
  return api.post(`/targets/${targetId}/scan`, { mode })
}

// ── Programs CRUD ──
export async function getPrograms(params?: {
  skip?: number
  limit?: number
  search?: string
}) {
  return api.get('/programs', params as any)
}

export async function getProgram(programId: number) {
  return api.get(`/programs/${programId}`)
}

export async function createProgram(data: any) {
  return api.post('/programs', data)
}

export async function updateProgram(programId: number, data: any) {
  return api.put(`/programs/${programId}`, data)
}

export async function deleteProgram(programId: number) {
  return api.delete(`/programs/${programId}`)
}

// ── Platforms CRUD ──
export async function getPlatforms() {
  return api.get('/platforms/status')
}

export async function getPlatform(platformId: number) {
  return api.get(`/platforms/${platformId}`)
}

export async function createPlatform(data: any) {
  return api.post('/platforms', data)
}

export async function updatePlatform(platformId: number, data: any) {
  return api.put(`/platforms/${platformId}`, data)
}

export async function deletePlatform(platformId: number) {
  return api.delete(`/platforms/${platformId}`)
}

export async function testPlatform(platformId: number) {
  return api.post(`/platforms/${platformId}/test`, {})
}

// ── Payouts CRUD ──
export async function getPayouts(params?: {
  skip?: number
  limit?: number
  platform?: string
  status?: string
}) {
  return api.get('/payouts', params as any)
}

export async function getPayout(payoutId: number) {
  return api.get(`/payouts/${payoutId}`)
}

export async function createPayout(data: any) {
  return api.post('/payouts', data)
}

export async function updatePayout(payoutId: number, data: any) {
  return api.put(`/payouts/${payoutId}`, data)
}

export async function deletePayout(payoutId: number) {
  return api.delete(`/payouts/${payoutId}`)
}

export async function getPayoutSummary() {
  return api.get('/payouts/summary')
}

// ── Revenue & Pipeline ──
export async function getPipeline() {
  return api.get('/pipeline')
}

export async function getReports(params?: {
  limit?: number
  offset?: number
  status?: string
  search?: string
}) {
  return api.get('/reports', params as any)
}

export async function getReportStats() {
  return api.get('/reports/stats')
}

export async function getAttackDecision(targetId?: number) {
  return api.get('/attack/decision', { target_id: targetId })
}

export async function getCapitalRunway() {
  return api.get('/capital/runway')
}

export async function getCapitalRisk() {
  return api.get('/capital/risk')
}

export async function getCapitalAllocation() {
  return api.get('/capital/allocation')
}

export async function getCapitalForecasting() {
  return api.get('/capital/forecasting')
}

export async function getCapitalDiversification() {
  return api.get('/capital/diversification')
}

export async function getEVRankedTargets(limit = 20) {
  return api.get(`/targets/ev-ranking?limit=${limit}`)
}

export async function getEVRankedTargetsFull(limit = 100) {
  return api.get(`/targets/ev-ranking?limit=${limit}`)
}

export async function getPlatformSpeedData() {
  return api.get('/api/revenue/platform-speed')
}