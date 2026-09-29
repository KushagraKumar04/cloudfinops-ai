import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { ArrowRight, ArrowUpRight, ShieldAlert } from 'lucide-react'
import { PageHeader } from '@/components/ui/PageHeader'
import { KpiCard } from '@/components/ui/KpiCard'
import { Card, CardBody, CardHeader } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Skeleton } from '@/components/ui/Skeleton'
import { StateBlock } from '@/components/ui/StateBlock'
import { formatCurrency, formatDate, formatNumber, formatPercent } from '@/lib/format'
import { RiskBadge } from '@/features/recommendations/badges'
import { useRecommendationList } from '@/features/recommendations/hooks'
import { useCostAnomalies, useCostBreakdown, useCostSummary, useCostTrend } from '@/features/costs/hooks'
import { useForecastSummary } from '@/features/forecast/hooks'
import type { CostQueryParams } from '@/features/costs/types'

const COST_QUERY: CostQueryParams = {
  range: '30d',
  provider: 'all',
  accountId: 'all',
  service: 'all',
}

const REC_QUERY = {
  search: '',
  provider: 'all' as const,
  type: 'all' as const,
  risk: 'all' as const,
  status: 'pending' as const,
  sortKey: 'estimatedMonthlySavings' as const,
  sortDir: 'desc' as const,
  page: 1,
  pageSize: 20,
}

export function Dashboard() {
  const summary = useCostSummary(COST_QUERY)
  const trend = useCostTrend(COST_QUERY)
  const breakdown = useCostBreakdown(COST_QUERY, 'service')
  const anomalies = useCostAnomalies(COST_QUERY)
  const forecast = useForecastSummary({ provider: 'all', horizon: '30d', budget: 220000 })
  const recFeed = useRecommendationList(REC_QUERY)

  const providerTotals = useMemo(() => {
    if (!trend.data) return []
    const aws = trend.data.reduce((s, p) => s + p.aws, 0)
    const azure = trend.data.reduce((s, p) => s + p.azure, 0)
    return [
      { name: 'AWS', value: Math.round(aws) },
      { name: 'Azure', value: Math.round(azure) },
    ]
  }, [trend.data])

  const serviceRows = (breakdown.data ?? []).slice(0, 10)
  const anomalyRows = (anomalies.data ?? []).slice(0, 3)
  const recItems = recFeed.data?.items ?? []
  const feedItems = recItems.slice(0, 5)
  const highRiskCount = recItems.filter((r) => r.risk === 'HIGH').length
  const pendingSavings = recFeed.data?.totals.savingsPending ?? 0

  const budgetPct =
    forecast.data && forecast.data.budget > 0
      ? Math.round((forecast.data.monthEndProjection / forecast.data.budget) * 100)
      : 0

  return (
    <>
      <PageHeader
        title="Dashboard"
        description="Current spend, anomalies, and optimization opportunities across AWS and Azure."
        action={<span className="text-xs text-ink-muted">Updated {formatDate(new Date().toISOString())}</span>}
      />

      <section className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {summary.isLoading ? (
          Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-28 w-full" />)
        ) : summary.isError || !summary.data ? (
          <div className="col-span-full rounded-md border border-border bg-surface">
            <StateBlock
              variant="error"
              title="Could not load cost summary"
              action={
                <button
                  onClick={() => summary.refetch()}
                  className="rounded border border-border bg-surface px-3 py-1.5 text-xs font-medium hover:border-border-strong"
                >
                  Retry
                </button>
              }
            />
          </div>
        ) : (
          <>
            <KpiCard
              label="Spend last 30 days"
              value={formatCurrency(summary.data.currentSpend)}
              delta={formatPercent(summary.data.changePct)}
              deltaTone={summary.data.changePct > 0 ? 'danger' : 'success'}
              hint="vs. prior period"
            />
            <KpiCard
              label="Projected month-end"
              value={forecast.data ? formatCurrency(forecast.data.monthEndProjection) : '—'}
              delta={forecast.data ? `${budgetPct}% of budget` : undefined}
              deltaTone={budgetPct >= 95 ? 'danger' : budgetPct >= 80 ? 'warning' : 'success'}
              hint={forecast.data ? formatCurrency(forecast.data.budget) : undefined}
            />
            <KpiCard
              label="Estimated savings"
              value={formatCurrency(pendingSavings)}
              delta={`${recFeed.data?.totals.approved ?? 0} approved`}
              deltaTone="success"
              hint="pending approval"
            />
            <KpiCard
              label="Anomalies"
              value={formatNumber(anomalies.data?.length ?? 0)}
              delta={`${highRiskCount} high-risk recs`}
              deltaTone="warning"
              hint="last 14 days"
            />
          </>
        )}
      </section>

      <section className="mt-6 grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2">
          <CardHeader title="Daily spend" subtitle="AWS vs Azure, last 30 days" />
          <CardBody>
            {trend.isLoading ? (
              <Skeleton className="h-64 w-full" />
            ) : trend.isError ? (
              <StateBlock
                variant="error"
                title="Could not load trend"
                action={
                  <button
                    onClick={() => trend.refetch()}
                    className="rounded border border-border bg-surface px-3 py-1.5 text-xs font-medium hover:border-border-strong"
                  >
                    Retry
                  </button>
                }
              />
            ) : !trend.data || trend.data.length === 0 ? (
              <StateBlock variant="empty" title="No spend in the last 30 days" />
            ) : (
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={trend.data} margin={{ top: 4, right: 8, bottom: 0, left: -16 }}>
                    <CartesianGrid stroke="#EFEDE8" vertical={false} />
                    <XAxis
                      dataKey="date"
                      tickFormatter={(d: string) => d.slice(5)}
                      stroke="#9A9A9A"
                      fontSize={11}
                      tickLine={false}
                      axisLine={false}
                      minTickGap={32}
                    />
                    <YAxis
                      stroke="#9A9A9A"
                      fontSize={11}
                      tickLine={false}
                      axisLine={false}
                      tickFormatter={(v: number) => `$${(v / 1000).toFixed(1)}k`}
                    />
                    <Tooltip
                      contentStyle={{ border: '1px solid #E8E6E1', borderRadius: 6, fontSize: 12 }}
                      formatter={(v: number) => formatCurrency(v)}
                    />
                    <Line type="monotone" dataKey="aws" stroke="#2563EB" strokeWidth={2} dot={false} name="AWS" />
                    <Line type="monotone" dataKey="azure" stroke="#0F766E" strokeWidth={2} dot={false} name="Azure" />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
          </CardBody>
        </Card>

        <Card>
          <CardHeader title="Cost by provider" subtitle="Last 30 days" />
          <CardBody>
            {trend.isLoading ? (
              <div className="space-y-4">
                {Array.from({ length: 2 }).map((_, i) => <Skeleton key={i} className="h-12 w-full" />)}
              </div>
            ) : providerTotals.length === 0 ? (
              <StateBlock variant="empty" title="No provider data" />
            ) : (
              <ul className="space-y-4">
                {providerTotals.map((p) => {
                  const total = providerTotals.reduce((s, x) => s + x.value, 0)
                  const pct = total > 0 ? Math.round((p.value / total) * 100) : 0
                  return (
                    <li key={p.name}>
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-ink">{p.name}</span>
                        <span className="text-ink-muted tabular-nums">{formatCurrency(p.value)}</span>
                      </div>
                      <div className="mt-2 h-1.5 w-full rounded-full bg-surface-muted">
                        <div className="h-full rounded-full bg-accent" style={{ width: `${pct}%` }} />
                      </div>
                      <p className="mt-1 text-[11px] text-ink-subtle">{pct}% of spend</p>
                    </li>
                  )
                })}
              </ul>
            )}
          </CardBody>
        </Card>
      </section>

      <section className="mt-6 grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2">
          <CardHeader title="Cost by service" subtitle="Top services, last 30 days" />
          <CardBody>
            {breakdown.isLoading ? (
              <Skeleton className="h-72 w-full" />
            ) : breakdown.isError ? (
              <StateBlock
                variant="error"
                title="Could not load breakdown"
                action={
                  <button
                    onClick={() => breakdown.refetch()}
                    className="rounded border border-border bg-surface px-3 py-1.5 text-xs font-medium hover:border-border-strong"
                  >
                    Retry
                  </button>
                }
              />
            ) : serviceRows.length === 0 ? (
              <StateBlock variant="empty" title="No service data" />
            ) : (
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={serviceRows} layout="vertical" margin={{ top: 0, right: 16, bottom: 0, left: 40 }}>
                    <CartesianGrid stroke="#EFEDE8" horizontal={false} />
                    <XAxis
                      type="number"
                      stroke="#9A9A9A"
                      fontSize={11}
                      tickLine={false}
                      axisLine={false}
                      tickFormatter={(v: number) => `$${(v / 1000).toFixed(0)}k`}
                    />
                    <YAxis
                      type="category"
                      dataKey="name"
                      stroke="#9A9A9A"
                      fontSize={11}
                      tickLine={false}
                      axisLine={false}
                      width={90}
                    />
                    <Tooltip
                      contentStyle={{ border: '1px solid #E8E6E1', borderRadius: 6, fontSize: 12 }}
                      formatter={(v: number) => formatCurrency(v)}
                    />
                    <Bar dataKey="spend" fill="#2563EB" radius={[0, 4, 4, 0]} barSize={14} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </CardBody>
        </Card>

        <Card>
          <CardHeader
            title="Recent anomalies"
            subtitle="Detected by the FinOps engine"
            action={<ShieldAlert size={16} className="text-ink-subtle" />}
          />
          <CardBody className="space-y-4">
            {anomalies.isLoading ? (
              Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-14 w-full" />)
            ) : anomalies.isError ? (
              <StateBlock
                variant="error"
                title="Could not load anomalies"
                action={
                  <button
                    onClick={() => anomalies.refetch()}
                    className="rounded border border-border bg-surface px-3 py-1.5 text-xs font-medium hover:border-border-strong"
                  >
                    Retry
                  </button>
                }
              />
            ) : anomalyRows.length === 0 ? (
              <StateBlock variant="empty" title="No anomalies" />
            ) : (
              anomalyRows.map((a) => (
                <div key={a.id} className="border-b border-border last:border-b-0 pb-3 last:pb-0">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-ink">{a.service}</span>
                    <Badge tone={a.severity === 'high' ? 'danger' : 'warning'}>
                      {formatPercent(a.deltaPct, 0)}
                    </Badge>
                  </div>
                  <p className="mt-1 text-xs text-ink-muted leading-relaxed">{a.description}</p>
                  <p className="mt-1 text-[11px] text-ink-subtle">
                    {formatDate(a.detectedAt)} · {formatCurrency(a.deltaAmount)} impact
                  </p>
                </div>
              ))
            )}
          </CardBody>
        </Card>
      </section>

      <section className="mt-6">
        <Card>
          <CardHeader
            title="Recommendations"
            subtitle="Top pending candidates by estimated savings"
            action={
              <Link
                to="/recommendations"
                className="inline-flex items-center gap-1 text-xs font-medium text-accent hover:underline"
              >
                View all <ArrowRight size={12} />
              </Link>
            }
          />
          <CardBody className="p-0">
            {recFeed.isLoading ? (
              <div className="space-y-2 px-5 pb-5">
                {Array.from({ length: 4 }).map((_, i) => (
                  <Skeleton key={i} className="h-10 w-full" />
                ))}
              </div>
            ) : recFeed.isError ? (
              <StateBlock
                variant="error"
                title="Could not load recommendations"
                action={
                  <button
                    onClick={() => recFeed.refetch()}
                    className="rounded border border-border bg-surface px-3 py-1.5 text-xs font-medium hover:border-border-strong"
                  >
                    Retry
                  </button>
                }
              />
            ) : feedItems.length === 0 ? (
              <StateBlock
                variant="empty"
                title="No pending recommendations"
                description="The FinOps engine has not produced candidates in this window."
              />
            ) : (
              <div className="divide-y divide-border">
                {feedItems.map((r) => (
                  <Link
                    key={r.id}
                    to={`/recommendations/${r.id}`}
                    className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 px-5 py-3 hover:bg-surface-muted/40 transition-colors"
                  >
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-ink truncate">{r.title}</p>
                      <p className="mt-0.5 text-xs text-ink-muted truncate font-mono">
                        {r.resourceName} · {r.resourceType}
                      </p>
                    </div>
                    <div className="flex items-center gap-3 shrink-0">
                      <RiskBadge risk={r.risk} />
                      <span className="text-sm font-medium text-success tabular-nums">
                        {formatCurrency(r.estimatedMonthlySavings)}
                      </span>
                      <span className="text-xs text-ink-subtle">/mo</span>
                      <ArrowUpRight size={14} className="text-ink-subtle" />
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </CardBody>
        </Card>
      </section>
    </>
  )
}