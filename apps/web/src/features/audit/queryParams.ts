import type { AuditCategory, AuditQueryParams, AuditSeverity } from './types'

const CATEGORIES: AuditCategory[] = [
  'cloud.account',
  'billing.sync',
  'resource',
  'cost.anomaly',
  'recommendation',
  'execution',
  'policy',
  'auth',
]
const SEVERITIES: AuditSeverity[] = ['info', 'warning', 'critical']

export function parseAuditQuery(search: URLSearchParams): AuditQueryParams {
  const category = search.get('category') as AuditCategory | null
  const severity = search.get('severity') as AuditSeverity | null
  const page = Number(search.get('page') ?? '1')
  const pageSize = Number(search.get('pageSize') ?? '20')
  return {
    search: search.get('q') ?? '',
    category: category && CATEGORIES.includes(category) ? category : 'all',
    severity: severity && SEVERITIES.includes(severity) ? severity : 'all',
    page: Number.isFinite(page) && page > 0 ? page : 1,
    pageSize: Number.isFinite(pageSize) && pageSize > 0 ? Math.min(100, pageSize) : 20,
  }
}

export function serializeAuditQuery(q: AuditQueryParams): URLSearchParams {
  const p = new URLSearchParams()
  if (q.search) p.set('q', q.search)
  if (q.category !== 'all') p.set('category', q.category)
  if (q.severity !== 'all') p.set('severity', q.severity)
  if (q.page !== 1) p.set('page', String(q.page))
  if (q.pageSize !== 20) p.set('pageSize', String(q.pageSize))
  return p
}

export const CATEGORY_LABEL: Record<AuditCategory, string> = {
  'cloud.account': 'Cloud account',
  'billing.sync': 'Billing sync',
  resource: 'Resource',
  'cost.anomaly': 'Cost anomaly',
  recommendation: 'Recommendation',
  execution: 'Execution',
  policy: 'Policy',
  auth: 'Auth',
}