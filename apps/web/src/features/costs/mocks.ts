import type {
  BreakdownDimension,
  CostAnomaly,
  CostBreakdownRow,
  CostQueryParams,
  CostSummary,
  CostTrendPoint,
  Provider,
} from './types'
import { resolveRange } from './queryParams'

export const MOCK_ACCOUNTS = [
  { id: 'aws-prod', name: 'AWS Production', provider: 'AWS' as Provider },
  { id: 'aws-stg', name: 'AWS Staging', provider: 'AWS' as Provider },
  { id: 'az-prod', name: 'Azure Production', provider: 'Azure' as Provider },
]

export const MOCK_SERVICES = [
  'EC2',
  'RDS',
  'S3',
  'EKS',
  'CloudWatch',
  'Data Transfer',
  'Azure VMs',
  'Azure SQL',
  'Blob Storage',
]

export const MOCK_REGIONS = ['us-east-1', 'us-west-2', 'eu-west-1', 'centralindia']

function seedRand(seed: number): () => number {
  let s = seed
  return () => {
    s = (s * 9301 + 49297) % 233280
    return s / 233280
  }
}

function generateSeries(days: number, base: number, seed: number): { date: string; value: number }[] {
  const rand = seedRand(seed)
  const out: { date: string; value: number }[] = []
  const today = new Date()
  for (let i = days - 1; i >= 0; i--) {
    const d = new Date(today)
    d.setDate(today.getDate() - i)
    const dow = d.getDay()
    const weekend = dow === 0 || dow === 6 ? 0.82 : 1
    const trend = 1 + ((days - i) / days) * 0.18
    const noise = 1 + (rand() - 0.5) * 0.15
    out.push({ date: d.toISOString().slice(0, 10), value: Math.round(base * weekend * trend * noise) })
  }
  return out
}

const AWS_SERIES = generateSeries(120, 4200, 17)
const AZURE_SERIES = generateSeries(120, 1900, 31)


function sumInRange(series: { date: string; value: number }[], start: string, end: string): number {
  return series.filter((p) => p.date >= start && p.date <= end).reduce((s, p) => s + p.value, 0)
}

function previousRange(start: string, end: string): { start: string; end: string } {
  const s = new Date(start)
  const e = new Date(end)
  const days = Math.round((e.getTime() - s.getTime()) / 86_400_000) + 1
  const pEnd = new Date(s)
  pEnd.setDate(s.getDate() - 1)
  const pStart = new Date(pEnd)
  pStart.setDate(pEnd.getDate() - (days - 1))
  return { start: pStart.toISOString().slice(0, 10), end: pEnd.toISOString().slice(0, 10) }
}

function applyProviderFilter(summary: { aws: number; azure: number }, provider: CostQueryParams['provider']) {
  if (provider === 'AWS') return summary.aws
  if (provider === 'Azure') return summary.azure
  return summary.aws + summary.azure
}

export function mockSummary(q: CostQueryParams): CostSummary {
  const { start, end } = resolveRange(q.range)
  const { start: pStart, end: pEnd } = previousRange(start, end)
  const awsCurrent = sumInRange(AWS_SERIES, start, end)
  const awsPrevious = sumInRange(AWS_SERIES, pStart, pEnd)
  const azCurrent = sumInRange(AZURE_SERIES, start, end)
  const azPrevious = sumInRange(AZURE_SERIES, pStart, pEnd)
  const currentSpend = applyProviderFilter({ aws: awsCurrent, azure: azCurrent }, q.provider)
  const previousSpend = applyProviderFilter({ aws: awsPrevious, azure: azPrevious }, q.provider)
  const changeAmount = currentSpend - previousSpend
  const changePct = previousSpend > 0 ? (changeAmount / previousSpend) * 100 : 0
  return {
    currentSpend,
    previousSpend,
    changeAmount,
    changePct,
    topMover: { name: 'EC2', deltaAmount: Math.round(changeAmount * 0.62), deltaPct: 24.5 },
    currency: 'USD',
    period: { start, end },
  }
}

export function mockTrend(q: CostQueryParams): CostTrendPoint[] {
  const { start, end } = resolveRange(q.range)
  const aws = AWS_SERIES.filter((p) => p.date >= start && p.date <= end)
  const azure = AZURE_SERIES.filter((p) => p.date >= start && p.date <= end)
  const len = Math.min(aws.length, azure.length)
  const out: CostTrendPoint[] = []
  for (let i = 0; i < len; i++) {
    const a = q.provider === 'Azure' ? 0 : aws[i].value
    const z = q.provider === 'AWS' ? 0 : azure[i].value
    out.push({ date: aws[i].date, aws: a, azure: z, total: a + z })
  }
  return out
}

const SERVICE_BREAKDOWN: Omit<CostBreakdownRow, 'share'>[] = [
  { id: 'svc-ec2', name: 'EC2', provider: 'AWS', spend: 64200, changePct: 24.5 },
  { id: 'svc-rds', name: 'RDS', provider: 'AWS', spend: 21800, changePct: 6.2 },
  { id: 'svc-s3', name: 'S3', provider: 'AWS', spend: 12600, changePct: -3.1 },
  { id: 'svc-eks', name: 'EKS', provider: 'AWS', spend: 11200, changePct: 11.8 },
  { id: 'svc-cloudwatch', name: 'CloudWatch', provider: 'AWS', spend: 4100, changePct: 2.4 },
  { id: 'svc-dataxfer', name: 'Data Transfer', provider: 'AWS', spend: 8900, changePct: 28.0 },
  { id: 'svc-azvm', name: 'Azure VMs', provider: 'Azure', spend: 28400, changePct: 9.7 },
  { id: 'svc-azsql', name: 'Azure SQL', provider: 'Azure', spend: 14200, changePct: 19.2 },
  { id: 'svc-blob', name: 'Blob Storage', provider: 'Azure', spend: 7800, changePct: 4.6 },
]

const ACCOUNT_BREAKDOWN: Omit<CostBreakdownRow, 'share'>[] = [
  { id: 'aws-prod', name: 'AWS Production', provider: 'AWS', spend: 98200, changePct: 21.3 },
  { id: 'aws-stg', name: 'AWS Staging', provider: 'AWS', spend: 30200, changePct: 8.1 },
  { id: 'az-prod', name: 'Azure Production', provider: 'Azure', spend: 55920, changePct: 12.4 },
]

const REGION_BREAKDOWN: Omit<CostBreakdownRow, 'share'>[] = [
  { id: 'us-east-1', name: 'us-east-1', provider: 'AWS', spend: 88400, changePct: 22.1 },
  { id: 'us-west-2', name: 'us-west-2', provider: 'AWS', spend: 28400, changePct: 7.4 },
  { id: 'eu-west-1', name: 'eu-west-1', provider: 'AWS', spend: 11600, changePct: 3.2 },
  { id: 'centralindia', name: 'centralindia', provider: 'Azure', spend: 55920, changePct: 12.4 },
]

function withShares(rows: Omit<CostBreakdownRow, 'share'>[]): CostBreakdownRow[] {
  const total = rows.reduce((s, r) => s + r.spend, 0)
  return rows.map((r) => ({ ...r, share: total > 0 ? r.spend / total : 0 }))
}

export function mockBreakdown(q: CostQueryParams, dim: BreakdownDimension): CostBreakdownRow[] {
  const source = dim === 'service' ? SERVICE_BREAKDOWN : dim === 'account' ? ACCOUNT_BREAKDOWN : REGION_BREAKDOWN
  let rows = source
  if (q.provider !== 'all') rows = rows.filter((r) => r.provider === q.provider)
  if (q.accountId !== 'all') rows = rows.filter((r) => r.id === q.accountId || r.provider === (MOCK_ACCOUNTS.find((a) => a.id === q.accountId)?.provider ?? r.provider))
  if (q.service !== 'all') rows = rows.filter((r) => r.name === q.service)
  return withShares(rows).sort((a, b) => b.spend - a.spend)
}

const ALL_ANOMALIES: CostAnomaly[] = [
  {
    id: 'anom_001',
    service: 'EC2',
    account: 'AWS Production',
    provider: 'AWS',
    detectedAt: new Date(Date.now() - 2 * 86_400_000).toISOString(),
    deltaPct: 42,
    deltaAmount: 3820,
    description: 'Compute spend on us-east-1 increased 42% vs 14-day baseline.',
    severity: 'high',
  },
  {
    id: 'anom_002',
    service: 'Data Transfer',
    account: 'AWS Production',
    provider: 'AWS',
    detectedAt: new Date(Date.now() - 4 * 86_400_000).toISOString(),
    deltaPct: 28,
    deltaAmount: 640,
    description: 'Cross-region data transfer increased 28% week over week.',
    severity: 'medium',
  },
  {
    id: 'anom_003',
    service: 'Azure SQL',
    account: 'Azure Production',
    provider: 'Azure',
    detectedAt: new Date(Date.now() - 6 * 86_400_000).toISOString(),
    deltaPct: 19,
    deltaAmount: 410,
    description: 'Azure SQL compute tier utilization above expected range.',
    severity: 'medium',
  },
  {
    id: 'anom_004',
    service: 'S3',
    account: 'AWS Staging',
    provider: 'AWS',
    detectedAt: new Date(Date.now() - 9 * 86_400_000).toISOString(),
    deltaPct: 11,
    deltaAmount: 120,
    description: 'Storage growth in staging bucket exceeded baseline by 11%.',
    severity: 'low',
  },
]

export function mockAnomalies(q: CostQueryParams): CostAnomaly[] {
  let rows = ALL_ANOMALIES
  if (q.provider !== 'all') rows = rows.filter((a) => a.provider === q.provider)
  if (q.accountId !== 'all') {
    const acct = MOCK_ACCOUNTS.find((a) => a.id === q.accountId)
    if (acct) rows = rows.filter((a) => a.account === acct.name)
  }
  if (q.service !== 'all') rows = rows.filter((a) => a.service === q.service)
  return rows
}