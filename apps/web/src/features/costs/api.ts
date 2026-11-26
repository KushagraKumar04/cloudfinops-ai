import { buildQuery, request, USE_MOCKS, withMockDelay } from '@/lib/api/client'
import { mockAnomalies, mockBreakdown, mockSummary, mockTrend } from './mocks'
import { resolveRange } from './queryParams'
import type {
  BreakdownDimension,
  CostAnomaly,
  CostBreakdownRow,
  CostQueryParams,
  CostSummary,
  CostTrendPoint,
} from './types'

function toBackendParams(q: CostQueryParams) {
  const { start, end } = resolveRange(q.range)
  return {
    start,
    end,
    provider: q.provider === 'all' ? undefined : q.provider,
    account_id: q.accountId === 'all' ? undefined : q.accountId,
    service: q.service === 'all' ? undefined : q.service,
  }
}

export async function getCostSummary(q: CostQueryParams): Promise<CostSummary> {
  if (USE_MOCKS) return withMockDelay(mockSummary(q))
  return request<CostSummary>(`/costs/summary${buildQuery(toBackendParams(q))}`)
}

export async function getCostTrend(q: CostQueryParams): Promise<CostTrendPoint[]> {
  if (USE_MOCKS) return withMockDelay(mockTrend(q))
  return request<CostTrendPoint[]>(`/costs/trends${buildQuery(toBackendParams(q))}`)
}

export async function getCostBreakdown(q: CostQueryParams, dim: BreakdownDimension): Promise<CostBreakdownRow[]> {
  if (USE_MOCKS) return withMockDelay(mockBreakdown(q, dim))
  return request<CostBreakdownRow[]>(`/costs/breakdown${buildQuery({ ...toBackendParams(q), dimension: dim })}`)
}

export async function getCostAnomalies(q: CostQueryParams): Promise<CostAnomaly[]> {
  if (USE_MOCKS) return withMockDelay(mockAnomalies(q))
  return request<CostAnomaly[]>(`/costs/anomalies${buildQuery(toBackendParams(q))}`)
}