import type { CostQueryParams, CostRange, ProviderFilter } from './types'

const VALID_RANGES: CostRange[] = ['7d', '30d', '90d', 'mtd', 'ytd']
const VALID_PROVIDERS: ProviderFilter[] = ['all', 'AWS', 'Azure']

export function parseCostQuery(search: URLSearchParams): CostQueryParams {
  const range = search.get('range') as CostRange | null
  const provider = search.get('provider') as ProviderFilter | null
  return {
    range: range && VALID_RANGES.includes(range) ? range : '30d',
    provider: provider && VALID_PROVIDERS.includes(provider) ? provider : 'all',
    accountId: search.get('account') ?? 'all',
    service: search.get('service') ?? 'all',
  }
}

export function serializeCostQuery(q: CostQueryParams): URLSearchParams {
  const p = new URLSearchParams()
  if (q.range !== '30d') p.set('range', q.range)
  if (q.provider !== 'all') p.set('provider', q.provider)
  if (q.accountId !== 'all') p.set('account', q.accountId)
  if (q.service !== 'all') p.set('service', q.service)
  return p
}

export function resolveRange(range: CostRange): { start: string; end: string } {
  const end = new Date()
  const start = new Date()
  if (range === '7d') start.setDate(end.getDate() - 6)
  else if (range === '30d') start.setDate(end.getDate() - 29)
  else if (range === '90d') start.setDate(end.getDate() - 89)
  else if (range === 'mtd') start.setDate(1)
  else if (range === 'ytd') start.setMonth(0, 1)
  return { start: start.toISOString().slice(0, 10), end: end.toISOString().slice(0, 10) }
}

export function rangeLabel(range: CostRange): string {
  return { '7d': 'Last 7 days', '30d': 'Last 30 days', '90d': 'Last 90 days', mtd: 'Month to date', ytd: 'Year to date' }[range]
}