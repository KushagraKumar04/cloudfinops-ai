import { API_BASE_URL, buildQuery, request, USE_MOCKS, withMockDelay } from '@/lib/api/client'
import { mockAuditList } from './mocks'
import type {
  AuditExport,
  AuditExportFormat,
  AuditExportListResult,
  AuditListResult,
  AuditQueryParams,
} from './types'

function toBackendParams(q: AuditQueryParams) {
  return {
    q: q.search || undefined,
    category: q.category === 'all' ? undefined : q.category,
    severity: q.severity === 'all' ? undefined : q.severity,
    page: q.page,
    page_size: q.pageSize,
  }
}

export async function listAuditEvents(q: AuditQueryParams): Promise<AuditListResult> {
  if (USE_MOCKS) return withMockDelay(mockAuditList(q))
  return request<AuditListResult>(`/audit${buildQuery(toBackendParams(q))}`)
}

export function buildAuditExportUrl(q: AuditQueryParams, format: 'csv' | 'json'): string {
  const params = toBackendParams(q)
  const qs = new URLSearchParams()
  qs.set('format', format)
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== '') qs.set(k, String(v))
  }
  return `${API_BASE_URL}/audit/export?${qs.toString()}`
}

export async function listAuditExports(): Promise<AuditExportListResult> {
  if (USE_MOCKS) return withMockDelay({ items: [], total: 0 })
  return request<AuditExportListResult>('/audit/exports')
}

export async function createAuditExport(
  format: AuditExportFormat,
  q: AuditQueryParams,
): Promise<AuditExport> {
  if (USE_MOCKS) throw new Error('Not available in mock mode')
  const body: Record<string, unknown> = { format }
  if (q.search) body.q = q.search
  if (q.category !== 'all') body.category = q.category
  if (q.severity !== 'all') body.severity = q.severity
  return request<AuditExport>('/audit/exports', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function deleteAuditExport(id: string): Promise<void> {
  if (USE_MOCKS) return withMockDelay(undefined)
  await request<void>(`/audit/exports/${id}`, { method: 'DELETE' })
}

export async function cleanupAuditExports(): Promise<{ removed: number }> {
  if (USE_MOCKS) return withMockDelay({ removed: 0 })
  return request<{ removed: number }>('/audit/exports/cleanup', { method: 'POST' })
}