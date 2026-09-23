import {
  LineChart,
  Line,
  ResponsiveContainer,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  BarChart,
  Bar,
} from 'recharts'
import { ArrowUpRight, ArrowDownRight, ShieldAlert } from 'lucide-react'
import { PageHeader } from '@/components/ui/PageHeader'
import { KpiCard } from '@/components/ui/KpiCard'
import { Card, CardBody, CardHeader } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { formatCurrency, formatDate, formatNumber, formatPercent } from '@/lib/format'
import { kpis, spendTrend, costByProvider, costByService, recommendations, anomalies } from '@/data/mock'

export function Dashboard() {
  const budgetPct = Math.round((kpis.projectedMonthEnd / kpis.budget) * 100)

  return (
    <>
      <PageHeader
        title="Dashboard"
        description="Current spend, anomalies, and optimization opportunities across AWS and Azure."
        action={
          <span className="text-xs text-ink-muted">
            Updated {formatDate(new Date().toISOString())}
          </span>
        }
      />

      <section className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <KpiCard
          label="Spend this month"
          value={formatCurrency(kpis.currentMonthSpend)}
          delta={formatPercent(kpis.momChangePct)}
          deltaTone="danger"
          hint="vs. last month"
        />
        <KpiCard
          label="Projected month-end"
          value={formatCurrency(kpis.projectedMonthEnd)}
          delta={`${budgetPct}% of budget`}
          deltaTone={budgetPct >= 95 ? 'danger' : budgetPct >= 80 ? 'warning' : 'success'}
          hint={formatCurrency(kpis.budget)}
        />
        <KpiCard
          label="Estimated savings"
          value={formatCurrency(kpis.estimatedSavings)}
          delta={`${formatCurrency(kpis.realizedSavings)} realized`}
          deltaTone="success"
          hint="pending approval"
        />
        <KpiCard
          label="Anomalies"
          value={formatNumber(kpis.anomalyCount)}
          delta={`${kpis.highRiskRecommendations} high-risk recs`}
          deltaTone="warning"
          hint="last 14 days"
        />
      </section>

      <section className="mt-6 grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2">
          <CardHeader
            title="Daily spend"
            subtitle="AWS vs Azure, last 14 days"
            action={<Badge tone="accent">Demo</Badge>}
          />
          <CardBody>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={spendTrend} margin={{ top: 4, right: 8, bottom: 0, left: -16 }}>
                  <CartesianGrid stroke="#EFEDE8" vertical={false} />
                  <XAxis dataKey="date" tickFormatter={(d) => d.slice(5)} stroke="#9A9A9A" fontSize={11} tickLine={false} axisLine={false} />
                  <YAxis stroke="#9A9A9A" fontSize={11} tickLine={false} axisLine={false} tickFormatter={(v) => `$${(v / 1000).toFixed(1)}k`} />
                  <Tooltip
                    contentStyle={{ border: '1px solid #E8E6E1', borderRadius: 6, fontSize: 12 }}
                    formatter={(v: number) => formatCurrency(v)}
                  />
                  <Line type="monotone" dataKey="aws" stroke="#2563EB" strokeWidth={2} dot={false} name="AWS" />
                  <Line type="monotone" dataKey="azure" stroke="#0F766E" strokeWidth={2} dot={false} name="Azure" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </CardBody>
        </Card>

        <Card>
          <CardHeader title="Cost by provider" subtitle="Month to date" />
          <CardBody>
            <ul className="space-y-4">
              {costByProvider.map((p) => {
                const total = costByProvider.reduce((s, x) => s + x.value, 0)
                const pct = Math.round((p.value / total) * 100)
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
          </CardBody>
        </Card>
      </section>

      <section className="mt-6 grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2">
          <CardHeader title="Cost by service" subtitle="Top services this month" />
          <CardBody>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={costByService} layout="vertical" margin={{ top: 0, right: 16, bottom: 0, left: 40 }}>
                  <CartesianGrid stroke="#EFEDE8" horizontal={false} />
                  <XAxis type="number" stroke="#9A9A9A" fontSize={11} tickLine={false} axisLine={false} tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} />
                  <YAxis type="category" dataKey="name" stroke="#9A9A9A" fontSize={11} tickLine={false} axisLine={false} width={90} />
                  <Tooltip
                    contentStyle={{ border: '1px solid #E8E6E1', borderRadius: 6, fontSize: 12 }}
                    formatter={(v: number) => formatCurrency(v)}
                  />
                  <Bar dataKey="value" fill="#2563EB" radius={[0, 4, 4, 0]} barSize={14} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardBody>
        </Card>

        <Card>
          <CardHeader
            title="Recent anomalies"
            subtitle="Detected by the FinOps engine"
            action={<ShieldAlert size={16} className="text-ink-subtle" />}
          />
          <CardBody className="space-y-4">
            {anomalies.map((a) => (
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
            ))}
          </CardBody>
        </Card>
      </section>

      <section className="mt-6">
        <Card>
          <CardHeader
            title="Recommendations"
            subtitle="Evidence-backed optimization candidates"
            action={<Badge tone="neutral">{recommendations.length} pending review</Badge>}
          />
          <CardBody className="p-0">
            <div className="divide-y divide-border">
              {recommendations.map((r) => (
                <div key={r.id} className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 px-5 py-3">
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-ink truncate">{r.title}</p>
                    <p className="mt-0.5 text-xs text-ink-muted truncate font-mono">{r.resource}</p>
                  </div>
                  <div className="flex items-center gap-3 shrink-0">
                    <Badge tone={r.risk === 'HIGH' ? 'danger' : r.risk === 'MEDIUM' ? 'warning' : 'success'}>
                      {r.risk}
                    </Badge>
                    <span className="text-sm font-medium text-success tabular-nums">
                      {formatCurrency(r.estimatedMonthlySavings)}
                    </span>
                    <span className="text-xs text-ink-subtle">/mo</span>
                    {r.estimatedMonthlySavings > 0 ? <ArrowUpRight size={14} className="text-ink-subtle" /> : <ArrowDownRight size={14} className="text-ink-subtle" />}
                  </div>
                </div>
              ))}
            </div>
          </CardBody>
        </Card>
      </section>
    </>
  )
}