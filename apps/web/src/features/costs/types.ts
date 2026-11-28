export type Provider = 'AWS' | 'Azure'
export type ProviderFilter = Provider | 'all'
export type CostRange = '7d' | '30d' | '90d' | 'mtd' | 'ytd'
export type BreakdownDimension = 'service' | 'account' | 'region'
export type Severity = 'low' | 'medium' | 'high'

export interface CostQueryParams {
  range: CostRange
  provider: ProviderFilter
  accountId: string | 'all'
  service: string | 'all'
}

export interface ResolvedRange {
  start: string
  end: string
}

export interface CostSummary {
  currentSpend: number
  previousSpend: number
  changeAmount: number
  changePct: number
  topMover: {
    name: string
    deltaAmount: number
    deltaPct: number
  } | null
  currency: string
  period: ResolvedRange
}

export interface CostTrendPoint {
  date: string
  aws: number
  azure: number
  total: number
}

export interface CostBreakdownRow {
  id: string
  name: string
  provider: Provider | 'mixed'
  spend: number
  changePct: number
  share: number
}

export interface CostAnomaly {
  id: string
  service: string
  account: string
  provider: Provider
  detectedAt: string
  deltaPct: number
  deltaAmount: number
  description: string
  severity: Severity
}