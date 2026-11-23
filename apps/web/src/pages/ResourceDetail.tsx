import { Link, useNavigate, useParams } from 'react-router-dom'
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { ArrowLeft, Copy, ExternalLink } from 'lucide-react'
import { PageHeader } from '@/components/ui/PageHeader'
import { Card, CardBody, CardHeader } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { KpiCard } from '@/components/ui/KpiCard'
import { Skeleton } from '@/components/ui/Skeleton'
import { StateBlock } from '@/components/ui/StateBlock'
import { formatCurrency, formatDate } from '@/lib/format'
import { useResource } from '@/features/resources/hooks'
import { ResourceStatusBadge } from '@/features/resources/ResourceStatusBadge'
import { CostHistoryChart } from '@/features/resources/CostHistoryChart'

function seriesToChart(series: number[] | undefined, label: string) {
  if (!series) return []
  return series.map((v, i) => ({ day: `D-${series.length - i - 1}`, [label]: v }))
}

export function ResourceDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data, isLoading, isError, refetch } = useResource(id)

  const copy = (value: string) => {
    navigator.clipboard.writeText(value).catch(() => undefined)
  }

  if (isLoading) {
    return (
      <>
        <Skeleton className="h-6 w-32 mb-6" />
        <Skeleton className="h-32 w-full" />
        <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
          <Skeleton className="h-64" />
          <Skeleton className="h-64" />
        </div>
      </>
    )
  }

  if (isError || !data) {
    return (
      <Card>
        <StateBlock
          variant="error"
          title="Resource not found"
          description="The resource may have been removed or the ID is invalid."
          action={
            <div className="flex gap-2">
              <Button size="sm" onClick={() => refetch()}>Retry</Button>
              <Button size="sm" variant="ghost" onClick={() => navigate('/resources')}>Back to resources</Button>
            </div>
          }
        />
      </Card>
    )
  }

  const cpuSeries = seriesToChart(data.series.cpu, 'cpu')
  const memorySeries = seriesToChart(data.series.memory, 'memory')
  const combined = cpuSeries.map((p, i) => ({ ...p, memory: memorySeries[i]?.memory ?? null }))

  return (
    <>
      <div className="mb-3">
        <Link to="/resources" className="inline-flex items-center gap-1.5 text-xs text-ink-muted hover:text-ink">
          <ArrowLeft size={13} /> Resources
        </Link>
      </div>

      <PageHeader
        title={data.name}
        description={`${data.type} · ${data.region} · ${data.accountName}`}
        action={
          <div className="flex items-center gap-2">
            <ResourceStatusBadge status={data.status} />
            <Badge tone="neutral">{data.provider}</Badge>
          </div>
        }
      />

      <section className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <KpiCard
          label="Monthly cost"
          value={data.monthlyCost > 0 ? formatCurrency(data.monthlyCost) : '—'}
          hint="current run rate"
        />
        <KpiCard
          label="Avg CPU"
          value={data.utilization.cpu !== undefined ? `${data.utilization.cpu}%` : '—'}
          hint="30-day average"
        />
        <KpiCard
          label="Avg memory"
          value={data.utilization.memory !== undefined ? `${data.utilization.memory}%` : '—'}
          hint="30-day average"
        />
        <KpiCard
          label="Metric coverage"
          value={`${Math.round(data.metricCoverage * 100)}%`}
          hint={data.metricCoverage >= 0.9 ? 'sufficient' : 'below threshold'}
        />
      </section>

<section className="mt-4"> <CostHistoryChart resourceId={data.id} /> </section> <section className="mt-4 grid grid-cols-1 lg:grid-cols-3 gap-4"> <Card className="lg:col-span-2"> <CardHeader title="Utilization" subtitle="30-day CPU and memory" />
          <CardBody>
            {combined.length > 0 ? (
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={combined} margin={{ top: 4, right: 8, bottom: 0, left: -20 }}>
                    <CartesianGrid stroke="#EFEDE8" vertical={false} />
                    <XAxis dataKey="day" stroke="#9A9A9A" fontSize={11} tickLine={false} axisLine={false} minTickGap={40} />
                    <YAxis stroke="#9A9A9A" fontSize={11} tickLine={false} axisLine={false} unit="%" />
                    <Tooltip contentStyle={{ border: '1px solid #E8E6E1', borderRadius: 6, fontSize: 12 }} />
                    <Line type="monotone" dataKey="cpu" stroke="#2563EB" strokeWidth={2} dot={false} name="CPU %" />
                    <Line type="monotone" dataKey="memory" stroke="#0F766E" strokeWidth={2} dot={false} name="Memory %" />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <StateBlock
                variant="empty"
                title="No utilization metrics"
                description="This resource type does not expose standard utilization signals."
              />
            )}
          </CardBody>
        </Card>

        <Card>
          <CardHeader title="Identity" />
          <CardBody className="space-y-3 text-sm">
            <div>
              <p className="text-[11px] uppercase tracking-wide text-ink-muted font-medium">Cloud ID</p>
              <div className="mt-1 flex items-center gap-2">
                <code className="text-xs font-mono text-ink break-all">{data.cloudId}</code>
                <button
                  onClick={() => copy(data.cloudId)}
                  className="shrink-0 text-ink-subtle hover:text-ink"
                  aria-label="Copy cloud ID"
                >
                  <Copy size={13} />
                </button>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Service" value={data.service} />
              <Field label="Environment" value={data.environment} capitalize />
              <Field label="Application" value={data.application} />
              <Field label="Owner" value={data.owner} />
              <Field label="Region" value={data.region} />
              <Field label="Created" value={formatDate(data.createdAt)} />
            </div>
          </CardBody>
        </Card>
      </section>

      <section className="mt-4 grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2">
          <CardHeader title="Tags" subtitle="Provider tags associated with this resource" />
          <CardBody>
            {data.tags.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {data.tags.map((t) => (
                  <span
                    key={t.key}
                    className="inline-flex items-center gap-1.5 rounded border border-border bg-surface-muted px-2 py-1 text-xs"
                  >
                    <span className="text-ink-muted">{t.key}</span>
                    <span className="text-ink-subtle">=</span>
                    <span className="text-ink">{t.value}</span>
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-xs text-ink-muted">No tags. Untagged resources are harder to attribute and often missed by policy.</p>
            )}
          </CardBody>
        </Card>

        <Card>
          <CardHeader
            title="Related"
            action={<ExternalLink size={14} className="text-ink-subtle" />}
          />
          <CardBody className="space-y-3 text-sm">
            <p className="text-ink-muted text-xs leading-relaxed">
              Deterministic recommendations for this resource are generated by the FinOps engine and reviewed on the Recommendations page.
            </p>
            <Link
              to={`/recommendations?resource=${encodeURIComponent(data.id)}`}
              className="inline-flex items-center gap-1.5 text-xs font-medium text-accent hover:underline"
            >
              View recommendations for this resource
            </Link>
          </CardBody>
        </Card>
      </section>
    </>
  )
}

function Field({ label, value, capitalize }: { label: string; value: string; capitalize?: boolean }) {
  return (
    <div>
      <p className="text-[11px] uppercase tracking-wide text-ink-muted font-medium">{label}</p>
      <p className={`mt-0.5 text-sm text-ink ${capitalize ? 'capitalize' : ''}`}>{value}</p>
    </div>
  )
}